import digital_twin.core as core


class Activity(core.Identifiable, core.SimpyObject):
    """The Activity Class forms a specific class for a single activity within a simulation.
    It deals with a single origin container, destination container and a single combination of equipment
    to move substances from the origin to the destination. It will initiate and suspend processes
    according to a number of specified conditions. To run an activity after it has been initialized call env.run()
    on the Simpy environment with which it was initialized.

    condition: expression that states when to initiate the activity,
               i.e., when moving substances from the origin to the destination is allowed
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
                 condition,
                 origin, destination,
                 loader, mover, unloader,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.condition = condition
        self.origin = origin
        self.destination = destination
        self.loader = loader
        self.mover = mover
        self.unloader = unloader

        self.installation_proc = self.env.process(
            self.installation_process_control(condition, origin, destination, loader, mover, unloader)
        )

    def installation_process_control(self, condition,
                                     origin, destination,
                                     loader, mover, unloader):
        """Installation process control"""

        # stand by until the condition is satisfied
        shown = False
        # todo separate conditions into start condition and stop condition? no need to check start again after it was satisfied once?
        # todo change implementation of conditions, no longer use eval
        while not eval(condition):
            if not shown:
                print('T=' + '{:06.2f}'.format(self.env.now) + ' ' + self.name +
                      ' to ' + destination.name + ' suspended')
                shown = True
            yield self.env.timeout(3600)  # step 3600 time units ahead

        print('T=' + '{:06.2f}'.format(self.env.now) + ' ' + 'Condition: ' + condition + ' is satisfied, '
              + self.name + ' to ' + destination.name + ' started')

        # keep moving substances until the condition is no longer satisfied
        while eval(condition):
            yield from self.installation_process(origin, destination, loader, mover, unloader)

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
