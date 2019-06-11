import simpy

from digital_twin.core import ReservationContainer


class DummyShip:
    def __init__(self, env, name, capacity, relay_container, stop_event):
        self.env = env
        self.print_tag = name + ":"
        self.capacity = capacity
        self.relay_container = relay_container
        self.stop_event = stop_event

    def print(self, *args):
        print(self.env.now, "-", self.print_tag, *args)


class DeliveryShip(DummyShip):
    def __init__(self, delivery_time, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.delivery_time = delivery_time
        self.env.process(self.delivery_process())
        self.total_delivered = 0

    def delivery_process(self):
        while not self.stop_event.processed:
            self.print("determining amount to load")
            amount = min(
                self.capacity,
                self.relay_container.capacity - self.relay_container.expected_level,
            )
            if amount > 0:
                self.print("reserving", amount, "space")
                self.relay_container.reserve_put(amount)
                self.print("performing delivery of", amount)
                yield self.env.timeout(self.delivery_time)
                self.print("arriving at container for delivery, putting", amount)
                yield self.relay_container.put(amount)
                self.print("delivery completed")
                self.total_delivered += amount
            else:
                self.print("no space available for reservation, start waiting")
                yield self.env.any_of(
                    events=[
                        (self.relay_container.reserve_put_available),
                        self.stop_event,
                    ]
                )
                self.print("waiting stop")
        self.print("Stop event triggered!")


class CollectionShip(DummyShip):
    def __init__(self, collection_time, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.collection_time = collection_time
        self.env.process(self.collection_process())
        self.total_dumped = 0

    def collection_process(self):
        while not self.stop_event.processed:
            self.print("determining amount to load")
            amount = min(self.capacity, self.relay_container.expected_level)
            if amount > 0:
                self.print("reserving", amount, "content")
                self.relay_container.reserve_get(amount)
                self.print("arriving at container for collection, getting", amount)
                yield self.relay_container.get(amount)
                self.print("content collected, delivering to dump")
                yield self.env.timeout(self.collection_time)
                self.print("contents dumped, collection completed")
                self.total_dumped += amount
            else:
                self.print("no content available for reservation, start waiting")
                yield self.env.any_of(
                    events=[
                        (self.relay_container.reserve_get_available),
                        self.stop_event,
                    ]
                )
                self.print("waiting stop")
        self.print("Stop event triggered!")


def test_relay_container():
    """Tests the concept of the RelayContainer where ships first reserve space or content, and yield from the
    get / put to wait for the content/space needed to actually become available."""
    env = simpy.Environment()
    container = ReservationContainer(env=env, capacity=1000)
    stop_event = env.timeout(5000)
    delivery_ship = DeliveryShip(
        env=env,
        name="delivery",
        capacity=1000,
        relay_container=container,
        stop_event=stop_event,
        delivery_time=2000,
    )
    collection_ship = CollectionShip(
        env=env,
        name="collection",
        capacity=500,
        relay_container=container,
        stop_event=stop_event,
        collection_time=300,
    )
    env.run()

    assert (
        delivery_ship.total_delivered == container.level + collection_ship.total_dumped
    )
    assert delivery_ship.total_delivered == 2500
    # the ships only check the timeout (stop_event) after completing a collection / delivery, so the simulation keeps
    # running a while after it has reached the timeout.
    assert env.now == 6300


def test_relay_container_reversed_init():
    """Exactly the same as test_relay_container, but the order of initialization of the delivery and collection ships
    is reversed. This causes the process for the collection ship to run first, at a point where there is no content
    available in the container, nor any space reserved (and therefore no new content expected). This means it will use
    the content_available event to wait for a new reservation to be possible."""
    env = simpy.Environment()
    container = ReservationContainer(env=env, capacity=1000)
    stop_event = env.timeout(5000)
    collection_ship = CollectionShip(
        env=env,
        name="collection",
        capacity=500,
        relay_container=container,
        stop_event=stop_event,
        collection_time=300,
    )
    delivery_ship = DeliveryShip(
        env=env,
        name="delivery",
        capacity=1000,
        relay_container=container,
        stop_event=stop_event,
        delivery_time=2000,
    )
    env.run()

    assert (
        delivery_ship.total_delivered == container.level + collection_ship.total_dumped
    )
    assert delivery_ship.total_delivered == 2500
    # the ships only check the timeout (stop_event) after completing a collection / delivery, so the simulation keeps
    # running a while after it has reached the timeout.
    assert env.now == 6300


def test_relay_container_several_collectors():
    """Test which uses several collection ships, to test the interaction between these ships."""
    env = simpy.Environment()
    container = ReservationContainer(env=env, capacity=1000)
    stop_event = env.timeout(5000)
    delivery_ship = DeliveryShip(
        env=env,
        name="delivery",
        capacity=1000,
        relay_container=container,
        stop_event=stop_event,
        delivery_time=3000,
    )
    collection_ships = []
    for i in range(4):
        collection_ships.append(
            CollectionShip(
                env=env,
                name="collection {}".format(i),
                capacity=50 * (i + 2),
                relay_container=container,
                stop_event=stop_event,
                collection_time=100 * (i + 1),
            )
        )
    env.run()

    total_dumped = sum(
        collection_ship.total_dumped for collection_ship in collection_ships
    )
    assert delivery_ship.total_delivered == total_dumped + container.level
    assert delivery_ship.total_delivered == 1700
    assert collection_ships[0].total_dumped == 300
    assert collection_ships[1].total_dumped == 450
    assert collection_ships[2].total_dumped == 400
    assert collection_ships[3].total_dumped == 500
    assert env.now == 6400


# Notice how in test_relay_container_several_collectors, the delivery ship only takes 700 units on its second run, this
# is because it first reserves content, then "sails to its collection point, loads content, sails to the delivery point
# then delivers its content" (simulated by a single yield to a timeout for delivery_time). In Activity we could be a bit
# smarter about this and review the amount we wish to load once we've arrived at the loading site,
# if at that point more content is available, we could reserve any additional content and take this as well (provided
# there is more space in the ship and destination)
