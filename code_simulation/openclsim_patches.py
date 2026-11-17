"""Run-time patches to OpenCLSim that this model relies on.

They are applied when ``simulation.py`` is imported (``apply()`` below) and
replace methods on OpenCLSim classes for the whole Python session.

1. ``WeatherPluginActivity.process_data``
   OpenCLSim only returns an "always workable" window when the criterion
   column stays *strictly* below the limit (``max < maximum``). The violation
   columns in the metocean file are 0/1 flags checked with ``maximum=0``, so a
   column that is never violated (``max == 0``) falls through to the window
   search, finds no transitions and raises an IndexError. The patch uses
   ``<=`` / ``>=`` instead. It only changes behaviour for criteria that are
   never exceeded in the data set.

2. ``Processor.determine_processor_amount``
   OpenCLSim raises a ValueError when a ShiftAmountActivity starts while the
   origin is empty or the destination is full. In this model several
   processes compete for the same staging slots, so the patch changes this to

   * origin empty      -> return the requested amount, so the activity waits
                          (blocks) until the origin holds that amount;
   * destination full  -> return 0, so the activity completes without
                          moving anything.

   The model guards every shift with an explicit "wait for space" activity or
   a token reservation, so the second case should never occur. Each
   occurrence is counted in ``ZERO_SHIFT_EVENTS`` and reported by
   ``simulation.run_simulation`` so that this can be verified per run.

3. Speed: OpenCLSim recomputes all workable windows of the whole metocean
   series at every weather check. The windows depend only on the series and
   the criterion, so they are computed once per series and criterion and
   reused. Results are identical; runs are about ten times faster.
"""

from openclsim.core.processor import Processor
from openclsim.plugins.weather import WeatherPluginActivity

ZERO_SHIFT_EVENTS = []

_WINDOW_CACHE = {}
_WINDOW_CACHE_MAX_SERIES = 8


def _safe_process_data(self, criterion):
    df = self.metocean_df
    key = (criterion.condition, criterion.maximum, criterion.minimum,
           criterion.window_length, criterion.window_delay)
    entry = _WINDOW_CACHE.get(id(df))
    if entry is None or entry[0] is not df:
        if len(_WINDOW_CACHE) >= _WINDOW_CACHE_MAX_SERIES:
            _WINDOW_CACHE.clear()
        entry = (df, {})
        _WINDOW_CACHE[id(df)] = entry
    windows = entry[1]
    if key not in windows:
        windows[key] = _process_data_uncached(self, criterion)
    return windows[key]


def _process_data_uncached(self, criterion):
    col = criterion.condition
    orig_data = self.metocean_df
    ts_start = min(orig_data["ts"])
    ts_stop = max(orig_data["ts"])
    always_ok = {
        "dataset_start": ts_start,
        "dataset_stop": ts_stop,
        "windows": [[ts_start, ts_stop]],
    }
    if criterion.maximum is not None and orig_data[col].max() <= criterion.maximum:
        return always_ok
    if criterion.minimum is not None and orig_data[col].min() >= criterion.minimum:
        return always_ok
    return _ORIGINAL_PROCESS_DATA(self, criterion)


def _safe_determine_processor_amount(self, origin, destination, amount=None,
                                     id_="default"):
    dest_cont = destination.container
    destination_max = dest_cont.get_capacity(id_) - dest_cont.get_level(id_)
    if destination_max <= 0:
        ZERO_SHIFT_EVENTS.append((origin.name, destination.name))
        return 0

    org_cont = origin.container
    origin_level = org_cont.get_level(id_)
    if origin_level <= 0:
        return amount if amount is not None else destination_max

    new_amount = min(origin_level, destination_max)
    if amount is not None:
        new_amount = min(amount, new_amount)
    return new_amount


_ORIGINAL_PROCESS_DATA = WeatherPluginActivity.process_data
_safe_process_data._is_safe_patch = True


def apply():
    """Install the patches (idempotent)."""
    global _ORIGINAL_PROCESS_DATA
    current = WeatherPluginActivity.process_data
    if not getattr(current, "_is_safe_patch", False):
        _ORIGINAL_PROCESS_DATA = current
        WeatherPluginActivity.process_data = _safe_process_data
    Processor.determine_processor_amount = _safe_determine_processor_amount
