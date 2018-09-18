import digital_twin.core as core


class LevelCondition:
    """The LevelCondition class can be used to specify the start level and stop level conditions for an Activity.

    container: an object which extends HasContainer, the container whose level needs to be >= or <= a certain value
    min_level: the minimum level the container is required to have
    max_level: the maximum level the container is required to have
    """

    def __init__(self, container, min_level=None, max_level=None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.container = container
        self.min_level = min_level if min_level is not None else 0
        self.max_level = max_level if max_level is not None else container.container.capacity

    def satisfied(self):
        current_level = self.container.container.level
        return self.min_level <= current_level <= self.max_level


class AndCondition:
    """The AndCondition class can be used to combine several different conditions into a single condition for an Activity.

    conditions: a list of condition objects that need to all be satisfied for the condition to be satisfied
                each object should have a satisfied method that returns whether the condition is satisfied or not
    """

    def __init__(self, conditions, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.conditions = conditions

    def satisfied(self):
        for condition in self.conditions:
            if not condition.satisfied():
                return False
        return True


class OrCondition:
    """The AndCondition class can be used to combine several different conditions into a single condition for an Activity.

    conditions: a list of condition objects, one of which needs to be satisfied for the condition to be satisfied
                each object should have a satisfied method that returns whether the condition is satisfied or not
    """

    def __init__(self, conditions, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.conditions = conditions

    def satisfied(self):
        for condition in self.conditions:
            if condition.satisfied():
                return True
        return False


class TrueCondition:
    """The TrueCondition class defines a condition which is always satisfied."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

    def satisfied(self):
        return True


class Activity(core.Identifiable, core.SimpyObject):
    """The Activity Class forms a specific class for a single activity within a simulation.
    It deals with a single origin container, destination container and a single combination of equipment
    to move substances from the origin to the destination. It will initiate and suspend processes
    according to a number of specified conditions. To run an activity after it has been initialized call env.run()
    on the Simpy environment with which it was initialized.

    To check when a transportation of substances can take place, the Activity class uses three different condition
    arguments: start_condition, stop_condition and condition. These condition arguments should all be given a condition
    object which has a satisfied method returning a boolean value. True if the condition is satisfied, False otherwise.

    start_condition: the activity will start as soon as this condition is satisfied
                     by default will always be True
    stop_condition: the activity will stop (terminate) as soon as this condition is no longer satisfied after
                    the activity has started
                    by default will always be for the destination container to be full or the source container to be empty
    condition: after the activity has started (start_condition was satisfied), this condition will be checked as long
               as the stop_condition is not satisfied, if the condition returns True, the activity will complete exactly
               one transportation of substances, of the condition is False the activity will wait for the condition to
               be satisfied again
               by default will always be True
    origin: object inheriting from HasContainer, HasResource, Locatable, Identifiable and Log
    destination: object inheriting from HasContainer, HasResource, Locatable, Identifiable and Log
    loader: object which will get units from 'origin' Container and put them into 'mover' Container
            should inherit from Processor, HasResource, Identifiable and Log
            after the simulation is complete, its log will contain entries for each time it
            started loading and stopped loading
    mover: moves to 'origin' if it is not already there, is loaded, then moves to 'destination' and is unloaded
           should inherit from Movable, HasContainer, HasResource, Identifiable and Log
           after the simulation is complete, its log will contain entries for each time it started moving,
           stopped moving, started loading / unloading and stopped loading / unloading
    unloader: gets amount from 'mover' Container and puts it into 'destination' Container
              should inherit from Processor, HasResource, Identifiable and Log
              after the simulation is complete, its log will contain entries for each time it
              started unloading and stopped unloading
    """

    # todo should loader and unloader also inherit from Locatable and Activity include checks if the loader / unloader is at the correct location?

    def __init__(self,
                 origin, destination,
                 loader, mover, unloader,
                 start_condition=None, stop_condition=None, condition=None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.start_condition = start_condition if start_condition is not None else TrueCondition()
        self.stop_condition = stop_condition if stop_condition is not None else OrCondition(
            [LevelCondition(origin, max_level=0),
             LevelCondition(destination, min_level=destination.container.capacity)])
        self.condition = condition if condition is not None else TrueCondition()
        self.origin = origin
        self.destination = destination
        self.loader = loader
        self.mover = mover
        self.unloader = unloader

        self.installation_proc = self.env.process(
            self.process_control(self.start_condition, self.stop_condition, self.condition,
                                 self.origin, self.destination, self.loader, self.mover, self.unloader)
        )

    def process_control(self, start_condition, stop_condition, condition,
                        origin, destination,
                        loader, mover, unloader):
        """Installation process control"""

        # wait for the start condition to be satisfied
        # checking the general condition and move

        # stand by until the start condition is satisfied
        shown = False
        while not start_condition.satisfied():
            if not shown:
                print('T=' + '{:06.2f}'.format(self.env.now) + ' ' + self.name +
                      ' to ' + destination.name + ' suspended')
                shown = True
            yield self.env.timeout(3600)  # step 3600 time units ahead

        # todo add nice printing to the conditions, then print them here
        print('T=' + '{:06.2f}'.format(self.env.now) + ' Start condition is satisfied, '
              + self.name + ' transporting from ' + origin.name + ' to ' + destination.name + ' started')

        # keep moving substances until the stop condition is satisfied
        while not stop_condition.satisfied():
            if condition.satisfied():
                yield from self.installation_process(origin, destination, loader, mover, unloader)
            else:
                yield self.env.timeout(3600)

        print('T=' + '{:06.2f}'.format(self.env.now) + ' Stop condition is satisfied, '
              + self.name + ' transporting from ' + origin.name + ' to ' + destination.name + ' complete')

    def installation_process(self, origin, destination,
                             loader, mover, unloader):
        """Installation process"""
        # estimate amount that should be transported
        amount = min(
            mover.container.capacity - mover.container.level,
            origin.container.level,
            origin.container.capacity - origin.total_requested,
            destination.container.capacity - destination.container.level,
            destination.container.capacity - destination.total_requested)

        if amount > 0:
            # request access to the transport_resource
            origin.total_requested += amount
            destination.total_requested += amount

            print('Using ' + mover.name + ' to process ' + str(amount))

            with mover.resource.request() as my_mover_turn:
                yield my_mover_turn

                # move to the origin if necessary
                if not mover.is_at(origin):
                    yield from self.__move_mover__(mover, origin)

                # load the mover
                yield from self.__shift_amount__(amount, loader, origin, mover, destination_resource_request=my_mover_turn)

                # move the mover to the destination
                yield from self.__move_mover__(mover, destination)

                # unload the mover
                yield from self.__shift_amount__(amount, unloader, mover, destination, origin_resource_request=my_mover_turn)
        else:
            print('Nothing to move')
            yield self.env.timeout(3600)

    def __shift_amount__(self, amount, processor, origin, destination,
                         origin_resource_request=None, destination_resource_request=None):
        if id(origin) == id(processor) and origin_resource_request is not None or \
                id(destination) == id(processor) and destination_resource_request is not None:

            yield from processor.process(origin, destination, amount, origin_resource_request=origin_resource_request,
                                         destination_resource_request=destination_resource_request)
        else:
            with processor.resource.request() as my_processor_turn:
                yield my_processor_turn

                processor.log_entry('processing start', self.env.now, amount)
                yield from processor.process(origin, destination, amount,
                                             origin_resource_request=origin_resource_request,
                                             destination_resource_request=destination_resource_request)
                processor.log_entry('processing start', self.env.now, amount)

        print('Processed {}:'.format(amount))
        print('  from:        ' + origin.name + ' contains: ' + str(origin.container.level))
        print('  by:          ' + processor.name)
        print('  to:          ' + destination.name + ' contains: ' + str(destination.container.level))

    def __move_mover__(self, mover, origin):
        old_location = mover.geometry

        mover.log_entry('sailing full start', self.env.now, mover.container.level)
        yield from mover.move(origin)
        mover.log_entry('sailing full stop', self.env.now, mover.container.level)

        print('Moved:')
        print('  object:      ' + mover.name + ' contains: ' + str(mover.container.level))
        print('  from:        ' + format(old_location.x, '02.5f') + ' ' + format(old_location.y, '02.5f'))
        print('  to:          ' + format(mover.geometry.x, '02.5f') + ' ' + format(mover.geometry.y, '02.5f'))
