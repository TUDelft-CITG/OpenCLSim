import digital_twin.core as core


class Activity(core.Identifiable, core.SimpyObject):
    """The Activity Class forms a specific class for a single activity within a simulation.
    It deals with a single origin container, destination container and a single combination of equipment
    to move substances from the origin to the destination. It will initiate and suspend processes
    according to a number of specified conditions. To run an activity after it has been initialized call env.run()
    on the Simpy environment with which it was initialized.

    By default an activity will start immediately upon the start of the simulation and run until either the origin
    container is empty or the destination container is full. The start level parameters can be used to make the activity
    wait for a certain level in the origin or destination container before starting. The stop level parameters can be
    used to make the activity stop when the origin or destination container has reached a certain level.

    condition: expression that states when the activity is allowed to run,
               i.e., when moving substances from the origin to the destination is allowed
               this condition will only be checked after at least one of the start levels is satisfied
               and as long as none of the stop levels have not been reached
               by default no additional condition is used
    origin: object inheriting from HasContainer, HasResource, Locatable, Identifiable and Log
    origin_start_level: the maximum amount of content the origin container is allowed to have for the activity to start
                        set to the capacity of the origin container by default
    origin_stop_level: the minimum amount of content the origin container must have for the activity to run, i.e.,
                       the activity will be terminated if this level is reached
                       set to 0 by default
    destination: object inheriting from HasContainer, HasResource, Locatable, Identifiable and Log
    destination_start_level: the minimum amount of content the destination container must contain
                             for the activity to start
                             set to 0 by default
    destination_stop_level: the maximum amount of content the destination container is allowed to contain for the
                            activity to run, i.e., the activity will be terminated if this level is reached
                            set to the capacity of the destination container by default
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
                 condition='True',
                 origin_start_level=None, origin_stop_level=None,
                 destination_start_level=None, destination_stop_level=None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.condition = condition
        self.origin = origin
        self.destination = destination
        self.loader = loader
        self.mover = mover
        self.unloader = unloader

        self.origin_start_level = origin_start_level if origin_start_level is not None else origin.container.capacity
        self.origin_stop_level = origin_stop_level if origin_stop_level is not None else 0
        self.destination_start_level = destination_start_level if destination_start_level is not None else 0
        self.destination_stop_level = destination_stop_level if destination_stop_level is not None else destination.container.capacity

        self.__validate_start_and_stop_levels__()

        self.installation_proc = self.env.process(
            self.installation_process_control(self.condition, self.origin, self.origin_start_level, self.origin_stop_level,
                                              self.destination, self.destination_start_level, self.destination_stop_level,
                                              self.loader, self.mover, self.unloader)
        )

    def installation_process_control(self, condition,
                                     origin, origin_start_level, origin_stop_level,
                                     destination, destination_start_level, destination_stop_level,
                                     loader, mover, unloader):
        """Installation process control"""

        # stand by until at least one of the start levels is satisfied
        shown = False
        while origin.container.level > origin_start_level and destination.container.level < destination_start_level:
            if not shown:
                print('T=' + '{:06.2f}'.format(self.env.now) + ' ' + self.name +
                      ' to ' + destination.name + ' suspended')
                shown=True
            yield self.env.timeout(3600)

        if origin.container.level <= origin_start_level:
            start_condition = 'contents of origin {} lower than {}'.format(origin.name, origin_start_level)
        else:
            start_condition = 'contents of destination {} greater than {}'.format(destination.name, destination_start_level)
        print('T=' + '{:06.2f}'.format(self.env.now) + '. Start condition: "' + start_condition + '" is satisfied. '
              + self.name + ' transporting from ' + origin.name + ' to ' + destination.name + ' started.')

        # while none of the stop levels are reached,
        # keep checking the (optional) condition and processing content while it is satisfied
        while origin.container.level > origin_stop_level and destination.container.level < destination_stop_level:
            # todo change implementation of conditions, no longer use eval
            if eval(condition):
                yield from self.installation_process(origin, origin_stop_level, destination,
                                                     destination_stop_level, loader, mover, unloader)
            else:
                yield self.env.timeout(3600)

        if origin.container.level <= origin_stop_level:
            stop_condition = 'contents of origin {} lower than {}'.format(origin.name, origin_stop_level)
        else:
            stop_condition = 'contents of destination {} greater than {}'.format(destination.name, destination_stop_level)
        print('T=' + '{:06.2f}'.format(self.env.now) + '. Stop condition "' + stop_condition + '" is satisfied. '
              + self.name + ' transporting from ' + origin.name + ' to ' + destination.name + ' completed.')

    def installation_process(self, origin, origin_stop_level,
                             destination, destination_stop_level,
                             loader, mover, unloader):
        """Installation process"""
        # estimate amount that should be transported
        amount = min(
            mover.container.capacity - mover.container.level,
            origin.container.level - origin_stop_level,
            origin.container.capacity - origin.total_requested,
            destination_stop_level - destination.container.level,
            destination_stop_level - destination.total_requested)

        if amount > 0:
            # request access to the transport_resource
            origin.total_requested += amount
            destination.total_requested += amount

            print('Using ' + mover.name + ' to transport ' + str(amount) + ' from ' + origin.name + ' to ' + destination.name)

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

    def __move_mover__(self, mover, destination):
        old_location = mover.geometry

        mover.log_entry('sailing full start', self.env.now, mover.container.level)
        yield from mover.move(destination)
        mover.log_entry('sailing full stop', self.env.now, mover.container.level)

        print('Moved:')
        print('  object:      ' + mover.name + ' contains: ' + str(mover.container.level))
        print('  from:        ' + format(old_location.x, '02.5f') + ' ' + format(old_location.y, '02.5f'))
        print('  to:          ' + format(mover.geometry.x, '02.5f') + ' ' + format(mover.geometry.y, '02.5f')
              + '(' + destination.name + ')')

    def __validate_start_and_stop_levels__(self):
        if self.origin_start_level < 0 or self.origin_stop_level < 0:
            raise ValueError('origin_start_level ({}) and origin_stop_level ({}) must be greater than or equal to 0'
                             .format(self.origin_start_level, self.origin_stop_level))
        if self.origin_start_level > self.origin.container.capacity or self.origin_stop_level > self.origin.container.capacity:
            raise ValueError('origin_start_level ({}) and origin_stop_level ({}) must '
                             'be smaller or equal to the origin {} container capacity of {}'
                             .format(self.origin_start_level, self.origin_stop_level,
                                     self.origin.name, self.origin.container.capacity))
        if self.origin_start_level <= self.origin_stop_level:
            raise ValueError('origin_start_level ({}) should be strictly greater than origin_stop_level ({}), '
                             'otherwise the activity will complete immediately after starting without any effect.'
                             .format(self.origin_start_level, self.origin_stop_level))

        if self.destination_start_level < 0 or self.destination_stop_level < 0:
            raise ValueError('destination_start_level ({}) and destination_stop_level ({}) must be greater than or equal to 0'
                             .format(self.destination_start_level, self.destination_stop_level))
        if self.destination_start_level > self.destination.container.capacity or self.destination_stop_level > self.destination.container.capacity:
            raise ValueError('destination_start_level ({}) and destination_stop_level ({}) must '
                             'be smaller or equal to the destination {} container capacity of {}'
                             .format(self.destination_start_level, self.destination_stop_level,
                                     self.destination.name, self.destination.container.capacity))
        if self.destination_start_level >= self.destination_stop_level:
            raise ValueError('destination_start_level ({}) should be strictly greater than destination_stop_level ({}), '
                             'otherwise the activity will complete immediately after starting without any effect.'
                             .format(self.destination_start_level, self.destination_stop_level))


class Simulation(core.Identifiable, core.SimpyObject):
    """The Simulation class can be used to quickly instantiate several Activity instances which together would form a
    complete simulation. It will create activities for each combination of origin, destination and equipment set. To run
    the simulation after it has been initialized call env.run() on the Simpy environment with which it was initialized.

    origins: a list of origin locations
    destinations: a list of destination locations
    equipment: a list of dicts where each dict contains a 'loader', 'mover' and 'unloader' key-value pair representing
               a valid combination of equipment which can be used to move substances from the origin to the destination
    condition: the condition that should be passed to the Activity instances
    #todo complete docs
    """

    #todo add support for layered origin or layered destination locations using start and stop levels
    #todo should this also contain support for "line locations" or should these just be passed separately?
    def __init__(self, origins, destinations, equipment, condition='True', *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.origins = origins
        self.destinations = destinations
        self.equipment = equipment
        self.condition = condition

        # fill the origin containers
        for origin in origins:
            origin.container.put(origin.container.capacity)

        # initialize all activities
        self.activities = []
        i = 0
        for origin in origins:
            for destination in destinations:
                for eq in equipment:
                    activity = Activity(env=self.env, name='{}_ACT_{}'.format(self.name, i),
                                        origin=origin, destination=destination,
                                        loader=eq['loader'], mover=eq['mover'], unloader=eq['unloader'],
                                        condition=condition)
                    self.activities.append(activity)
                    i += 1
