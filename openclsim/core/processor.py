"""Component to process with the simulation objecs."""
import logging

from .log import Log, LogState
from .resource import HasResource
from .simpy_object import SimpyObject

logger = logging.getLogger(__name__)


class Processor(SimpyObject):
    """
    Processor class.

    Adds the loading and unloading components and checks for possible downtime.

    If the processor class is used to allow "loading" or "unloading" the mixins "LoadingFunction" and "UnloadingFunction" should be added as well.
    If no functions are used a subcycle should be used, which is possible with the mixins "LoadingSubcycle" and "UnloadingSubcycle".
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

    def process(
        self,
        origin,
        amount,
        destination,
        id_="default",
        rate=None,
        duration=None,
        activity_name=None,
    ):
        """
        Move content from ship to the site or from the site to the ship.

        This to ensure that the ship's container reaches the desired level.
        Yields the time it takes to process.
        """

        # assert isinstance(origin, HasContainer) or isinstance(origin, HasContainer)
        # assert isinstance(destination, HasContainer) or isinstance(
        #     destination, HasContainer
        # )
        assert isinstance(origin, HasResource)
        assert isinstance(destination, HasResource)
        assert isinstance(self, Log)
        assert isinstance(origin, Log)
        assert isinstance(destination, Log)
        assert self.is_at(origin)
        assert destination.is_at(origin)

        # Log the process for all parts
        for location in [origin, destination]:
            location.log_entry(
                t=location.env.now,
                activity_id=self.activity_id,
                activity_state=LogState.START,
            )

        if rate is not None:
            duration, new_amount = rate(origin, destination, amount)
            amount = min(amount, new_amount)

        yield from self.check_possible_shift(origin, destination, amount, "get", id_)

        # Checkout single event
        self.log_entry(
            self.env.now,
            self.activity_id,
            LogState.START,
        )

        yield self.env.timeout(duration)

        # Put the amount in the destination
        yield from self.check_possible_shift(origin, destination, amount, "put", id_)

        self.log_entry(self.env.now, self.activity_id, LogState.STOP)

        # Log the process for all parts
        for location in [origin, destination]:
            location.log_entry(
                t=location.env.now,
                activity_id=self.activity_id,
                activity_state=LogState.STOP,
            )

        logger.debug("  process:        " + "%4.2f" % (duration / 3600) + " hrs")

    def check_possible_shift(
        self, origin, destination, amount, activity, id_="default"
    ):
        """
        Check if all the material is available.

        If the amount is not available in the origin or in the destination
        yield a put or get. Time will move forward until the amount can be
        retrieved from the origin or placed into the destination.
        """

        if activity == "get":

            # Shift amounts in containers
            start_time = self.env.now
            yield origin.container.get(amount, id_)
            end_time = self.env.now

            # If the amount is not available in the origin, log waiting
            if start_time != end_time:
                self.log_entry(
                    message="waiting origin content",
                    t=start_time,
                    activity_id=self.activity_id,
                    activity_state=LogState.WAIT_START,
                )
                self.log_entry(
                    message="waiting origin content",
                    t=end_time,
                    activity_id=self.activity_id,
                    activity_state=LogState.WAIT_STOP,
                )

        elif activity == "put":

            # Shift amounts in containers
            start_time = self.env.now
            yield destination.container.put(amount, id_=id_)
            end_time = self.env.now

            # If the amount is cannot be put in the destination, log waiting
            if start_time != end_time:
                self.log_entry(
                    message="waiting destination content",
                    t=start_time,
                    activity_id=self.activity_id,
                    activity_state=LogState.START,
                )
                self.log_entry(
                    message="waiting destination content",
                    t=end_time,
                    activity_id=self.activity_id,
                    activity_state=LogState.STOP,
                )

    def determine_processor_amount(
        self,
        origins,
        destination,
        amount=None,
        id_="default",
        loader=None,
        unloader=None,
        filling=1,
    ):
        """Determine the maximum amount that can be carried."""

        # Determine the basic amount that should be transported
        all_amounts = {}
        all_amounts.update(
            {
                "origin." + origin.id: origin.container.get_level(id_)
                for origin in origins
            }
        )
        all_amounts[
            "destination." + destination.id
        ] = destination.container.get_capacity(id_) - destination.container.get_level(
            id_
        )

        origin_requested = 0
        destination_requested = 0

        for key in all_amounts.keys():
            if "origin." in key:
                origin_requested += all_amounts[key]
            else:
                destination_requested += all_amounts[key]

        amount_ = min(origin_requested, destination_requested)
        if amount is not None:
            amount_ = min(amount_, amount)

        return amount_, all_amounts


class LoadingFunction:
    """
    Create a loading function and add it a processor.

    This is a generic and easy to read function, you can create your own LoadingFunction class and add this as a mixin.

    Parameters
    ----------
    loading_rate : amount / second
        The rate at which units are loaded per second
    load_manoeuvring : seconds
        The time it takes to manoeuvring in minutes
    """

    def __init__(
        self, loading_rate: float, load_manoeuvring: float = 0, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.loading_rate = loading_rate
        self.load_manoeuvring = load_manoeuvring

    def loading(self, origin, destination, amount, id_="default"):
        """
        Determine the duration based on an amount that is given as input with processing.

        The origin an destination are also part of the input, because other functions might be dependent on the location.
        """
        if not hasattr(self.loading_rate, "__call__"):
            duration = amount / self.loading_rate + self.load_manoeuvring * 60
            return duration, amount
        else:
            loading_time = self.loading_rate(
                destination.container.get_level(id_),
                destination.container.get_level(id_) + amount,
            )
            duration = loading_time + self.load_manoeuvring * 60
            return duration, amount


class UnloadingFunction:
    """
    Create an unloading function and add it a processor.

    This is a generic and easy to read function, you can create your own LoadingFunction class and add this as a mixin.

    Parameters
    ----------
    unloading_rate : volume / second
        the rate at which units are loaded per second
    unload_manoeuvring : minutes
        the time it takes to manoeuvring in minutes
    """

    def __init__(
        self, unloading_rate: float, unload_manoeuvring: float = 0, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.unloading_rate = unloading_rate
        self.unload_manoeuvring = unload_manoeuvring

    def unloading(self, origin, destination, amount, id_="default"):
        """
        Determine the duration based on an amount that is given as input with processing.

        The origin an destination are also part of the input, because other functions might be dependent on the location.
        """

        if not hasattr(self.unloading_rate, "__call__"):
            duration = amount / self.unloading_rate + self.unload_manoeuvring * 60
            return duration, amount
        else:
            unloading_time = self.unloading_rate(
                origin.container.get_level(id_) + amount,
                origin.container.get_level(id_),
            )
            duration = unloading_time + self.unload_manoeuvring * 60
            return duration, amount
