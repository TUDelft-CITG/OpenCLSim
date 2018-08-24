import digital_twin.core as core
import simpy


class Installation(core.Identifiable, core.SimpyObject):
    """The Installation Class forms a specific class of activities with associated methods that can
    initiate and suspend processes according to a number of specified conditions. This class deals
    with transport and installation/placement of discrete and continuous objects.

    condition: expression that states when to initiate or to suspend activity
    origin: object inheriting from HasContainer, HasResource, Locatable, Identifiable and Log
    destination: object inheriting from HasContainer, HasResource, Locatable and Log
    loader: object which will get units from 'origin' Container and put them into 'mover' Container
            should inherit from Processor, HasResource, Identifiable and Log
    mover: is loaded, then moves from 'origin' to 'destination' and is unloaded, then moves back to 'origin'
            should inherit from Movable, HasContainer, HasResource, Identifiable and Log
    unloader: gets amount from 'mover' Container and puts it into 'destination' Container
            should inherit from Processor, HasResource, Identifiable and Log

            #todo check this after implementation is done
    """

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

        self.standing_by_proc = self.env.process(
            self.standing_by(condition, destination))
        self.installation_proc = self.env.process(
            self.installation_process_control(condition,
                                              origin, destination,
                                              loader, mover, unloader))
        self.installation_reactivate = self.env.event()

    def standing_by(self, condition, destination, ):
        # todo why have a separate standing by? Why not just have a single method controlling the flow?
        # todo separate conditions into start condition and stop condition? no need to check start again after it was satisfied once?
        """Standing by"""
        shown = False

        while not eval(condition):
            if not shown:
                print(
                    'T=' + '{:06.2f}'.format(self.env.now) + ' ' + self.name + ' to ' + destination.name + ' suspended')
                shown = True
            yield self.env.timeout(3600)  # step 3600 time units ahead

        print('T=' + '{:06.2f}'.format(self.env.now) + ' ' + 'Condition: ' + condition + ' is satisfied')

        self.installation_reactivate.succeed()  # "reactivate"
        self.installation_reactivate = self.env.event()

    def installation_process_control(self, condition,
                                     origin, destination,
                                     loader, mover, unloader):
        """Installation process control"""
        while not eval(condition):
            yield self.installation_reactivate

        print('T=' + '{:06.2f}'.format(self.env.now) + ' ' + self.name + ' to ' + destination.name + ' started')
        while eval(condition):
            yield from self.installation_process(origin, destination,
                                                 loader, mover, unloader)

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
            if id(loader) == id(mover):
                # this is the case when a hopper is used
                print('Using Hopper to process ' + str(amount))
                with mover.resource.request() as my_mover_turn:
                    yield my_mover_turn

                    # request access to the load_resource
                    mover.log_entry('loading start', self.env.now, mover.container.level)
                    yield from loader.process(origin, mover, amount, destination_resource_request=my_mover_turn)
                    mover.log_entry('loading stop', self.env.now, mover.container.level)

                    print('Loaded:')
                    print('  from:           ' + origin.name + ' contains: ' + str(origin.container.level))
                    print('  by:             ' + mover.name + ' contains: ' + str(mover.container.level))
                    print('  to:             ' + destination.name + ' contains: ' + str(destination.container.level))

                    old_location = mover.geometry

                    mover.log_entry('sailing full start', self.env.now, mover.container.level)
                    yield from mover.move(destination)
                    mover.log_entry('sailing full stop', self.env.now, mover.container.level)

                    print('Moved:')
                    print(
                        '  from:            ' + format(old_location.x, '02.0f') + ' ' + format(old_location.x, '02.0f'))
                    print('  to:              ' + format(mover.geometry.x, '02.0f') + ' ' + format(mover.geometry.y,
                                                                                                   '02.0f'))

                    # request access to the placement_resource
                    mover.log_entry('unloading start', self.env.now, mover.container.level)
                    yield from unloader.process(mover, destination, amount, origin_resource_request=my_mover_turn)
                    mover.log_entry('unloading stop', self.env.now, mover.container.level)

                    print('Unloaded:')
                    print('  from:           ' + destination.name + ' contains: ' + str(destination.container.level))
                    print('  by:             ' + mover.name + ' contains: ' + str(mover.container.level))
                    print('  to:             ' + origin.name + ' contains: ' + str(origin.container.level))

                    old_location = mover.geometry

                    mover.log_entry('sailing full start', self.env.now, mover.container.level)
                    yield from mover.move(origin)
                    mover.log_entry('sailing full stop', self.env.now, mover.container.level)

                    print('Moved:')
                    print(
                        '  from:            ' + format(old_location.x, '02.0f') + ' ' + format(old_location.x, '02.0f'))
                    print('  to:              ' + format(mover.geometry.x, '02.0f') + ' ' + format(mover.geometry.y,
                                                                                                   '02.0f'))

                    # once a mover is assigned to an Activity it completes a full cycle
                    mover.resource.release(my_mover_turn)
            else:
                # if not a hopper is used we have to handle resource requests differently
                print('Using Transport to process ' + str(amount))
                with mover.resource.request() as my_mover_turn:
                    yield my_mover_turn

                    # request access to the load_resource
                    with loader.resource.request() as my_load_resource_turn:
                        yield my_load_resource_turn

                        mover.log_entry('loading start', self.env.now, mover.container.level)
                        yield from loader.process(origin, mover, amount, destination_resource_request=my_mover_turn)
                        mover.log_entry('loading stop', self.env.now, mover.container.level)

                        print('Loaded:')
                        print('  from:           ' + origin.name + ' contains: ' + str(origin.container.level))
                        print('  by:             ' + mover.name + ' contains: ' + str(mover.container.level))
                        print(
                            '  to:             ' + destination.name + ' contains: ' + str(destination.container.level))

                    old_location = mover.geometry

                    mover.log_entry('sailing full start', self.env.now, mover.container.level)
                    yield from mover.move(destination)
                    mover.log_entry('sailing full stop', self.env.now, mover.container.level)

                    print('Moved:')
                    print(
                        '  from:            ' + format(old_location.x, '02.0f') + ' ' + format(old_location.x, '02.0f'))
                    print('  to:              ' + format(mover.geometry.x, '02.0f') + ' ' + format(mover.geometry.y,
                                                                                                   '02.0f'))

                    # request access to the placement_resource
                    with unloader.resource.request() as my_unloader_turn:
                        yield my_unloader_turn

                        print('unloading')

                        mover.log_entry('unloading start', self.env.now, mover.container.level)
                        yield from unloader.process(mover, destination, amount, origin_resource_request=my_mover_turn)
                        mover.log_entry('unloading stop', self.env.now, mover.container.level)

                        print('Unloaded:')
                        print(
                            '  from:           ' + destination.name + ' contains: ' + str(destination.container.level))
                        print('  by:             ' + mover.name + ' contains: ' + str(mover.container.level))
                        print('  to:             ' + origin.name + ' contains: ' + str(origin.container.level))

                        unloader.resource.release(my_unloader_turn)

                    old_location = mover.geometry

                    mover.log_entry('sailing full start', self.env.now, mover.container.level)
                    yield from mover.move(origin)
                    mover.log_entry('sailing full stop', self.env.now, mover.container.level)

                    print('Moved:')
                    print(
                        '  from:            ' + format(old_location.x, '02.0f') + ' ' + format(old_location.x, '02.0f'))
                    print('  to:              ' + format(mover.geometry.x, '02.0f') + ' ' + format(mover.geometry.y,
                                                                                                   '02.0f'))

                    # once a mover is assigned to an Activity it completes a full cycle
                    mover.resource.release(my_mover_turn)
        else:
            print('Nothing to move')
            yield self.env.timeout(3600)
