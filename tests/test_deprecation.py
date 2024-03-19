import pytest

import openclsim.core


def test_identifiable(recwarn):
    with pytest.warns(DeprecationWarning):
        openclsim.core.Identifiable(ID="abc", name="abc")

    n_before = len(recwarn)
    openclsim.core.Identifiable(id="abc", name="abc")
    n_after = len(recwarn)
    # no new warnings
    assert n_before == n_after, "No new warnings expected"
