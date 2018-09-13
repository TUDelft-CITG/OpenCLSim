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
                yield from self.__load_mover__(amount, loader, mover, my_mover_turn, origin)

                # move the mover to the destination
                yield from self.__move_mover__(mover, destination)

                # unload the mover
                yield from self.__unload_mover__(amount, unloader, mover, my_mover_turn, destination)
        else:
            print('Nothing to move')
            yield self.env.timeout(3600)

    # todo __load_mover__ and __unload_mover__ are very similar, turn them into a single method __shift_amount__

    def __load_mover__(self, amount, loader, mover, my_mover_turn, origin):
        if id(loader) == id(mover):
            yield from loader.process(origin, mover, amount, destination_resource_request=my_mover_turn)
        else:
            with loader.resource.request() as my_loader_turn:
                yield my_loader_turn

                loader.log_entry('processing start', self.env.now, amount)
                yield from loader.process(origin, mover, amount, destination_resource_request=my_mover_turn)
                loader.log_entry('processing stop', self.env.now, amount)

        print('Loaded:')
        print('  from:        ' + origin.name + ' contains: ' + str(origin.container.level))
        print('  by:          ' + loader.name)
        print('  to:          ' + mover.name + ' contains: ' + str(mover.container.level))

    def __unload_mover__(self, amount, unloader, mover, my_mover_turn, destination):
        if id(unloader) == id(mover):
            yield from unloader.process(mover, destination, amount, origin_resource_request=my_mover_turn)
        else:
            with unloader.resource.request() as my_unloader_turn:
                yield my_unloader_turn

                unloader.log_entry('processing start', self.env.now, amount)
                yield from unloader.process(mover, destination, amount, origin_resource_request=my_mover_turn)
                unloader.log_entry('processing stop', self.env.now, amount)

        print('Unloaded')
        print('  from:        ' + mover.name + ' contains: ' + str(mover.container.level))
        print('  by:          ' + unloader.name)
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
