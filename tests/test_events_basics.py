import simpy


class School:
    def __init__(self, env):
        self.env = env
        self.class_ends = env.event()
        self.pupil_procs = [env.process(self.pupil()) for i in range(3)]
        self.bell_proc = env.process(self.bell())
        print('init done')

    def bell(self):
        for i in range(2):
            print('timeout')
            yield self.env.timeout(45)
            print('ringing bell')
            self.class_ends.succeed()
            self.class_ends = self.env.event()
            print()

    def pupil(self):
        for i in range(2):
            print(r' \o/')
            yield self.class_ends
            print('I heard a bell')


def test_tutorial_example():
    env = simpy.Environment()
    school = School(env)
    env.run()


class DummyStartActivity:
    def __init__(self, env, start_event):
        self.env = env
        self.start_event = start_event
        self.process = env.process(self.process_control())
        self.done = False

    def process_control(self):
        print('process has started, time =', self.env.now)
        print('we should wait for our start event to trigger')
        yield self.start_event
        print('yay, it triggered so we can get started! time =', self.env.now)
        yield self.env.timeout(60)
        print('work is done, time =', self.env.now)
        self.done = True


def test_start_event_idea():
    env = simpy.Environment()
    event = env.event()  # create a start event
    activity = DummyStartActivity(env, event)
    env.run(until=20)  # run the simulation for the first twenty seconds
    event.succeed()  # trigger the start event
    env.run()  # complete the remainder of the implementation

    assert activity.done
    assert env.now == 80  # 20 seconds of waiting for start condition, 60 seconds of work


def test_start_event_with_timeout():
    env = simpy.Environment()
    # a Timeout is a special type of event which will trigger after the given delay has passed
    start_event = env.timeout(delay=20)
    activity = DummyStartActivity(env, start_event)
    env.run()

    assert activity.done
    assert env.now == 80


class DummyStopActivity:
    def __init__(self, env, stop_event):
        self.env = env
        self.stop_event = stop_event
        self.process = env.process(self.process_control())
        stop_event.callbacks.append(self.stop_event_callback)
        self.completed_count = 0
        self.task_count = 5
        self.stop_time = None

    def stop_event_callback(self, event):
        self.process.interrupt()

    def process_control(self):
        print('process has started, time =', self.env.now)
        try:
            # do the work
            for i in range(self.task_count):
                print('starting execution of task', i + 1)
                yield self.env.timeout(20)
                print('completed task', i + 1)
                self.completed_count += 1
                print('tasks completed =', self.completed_count, 'time =', self.env.now)
        except simpy.Interrupt:
            # stop event occurred, so our work was interrupted
            print('I should stop! time =', self.env.now)
            self.stop_time = self.env.now

    @property
    def done(self):
        return self.completed_count == self.task_count


def test_stop_event_idea():
    env = simpy.Environment()
    stop_event = env.timeout(50)  # all work should stop after 50 seconds
    activity = DummyStopActivity(env, stop_event)
    env.run()

    assert not activity.done
    assert activity.completed_count == 2

    # process control of activity stops after 50 seconds, but its yield to timeout causes the environment to continue
    # running until the timeout triggers, thus env.now is 60 after simulation completion
    assert env.now == 60
    assert activity.stop_time == 50


class ImprovedDummyStopActivity:
    def __init__(self, env, stop_event):
        self.env = env
        self.stop_event = stop_event
        self.process = env.process(self.process_control())
        stop_event.callbacks.append(self.stop_event_callback)
        self.completed_count = 0
        self.task_count = 5
        self.stop_time = None
        self.task_start_time = None

    def stop_event_callback(self, event):
        self.process.interrupt()

    def process_control(self):
        print('process has started, time =', self.env.now)
        try:
            # do the work
            for i in range(self.task_count):
                print('starting execution of task', i + 1)
                yield from self.perform_task()
                print('completed task', i + 1)
                self.completed_count += 1
                print('tasks completed =', self.completed_count, 'time =', self.env.now)
        except simpy.Interrupt:
            # stop event occurred, so our work was interrupted
            print('I should stop! time =', self.env.now)
            self.stop_time = self.env.now

            # we were interrupted while performing a task, so this task was only partially completed
            if self.task_start_time is not None:
                current_time = self.env.now
                task_completion_rate = (current_time - self.task_start_time) / 20
                self.completed_count += task_completion_rate
                print('completed interrupted task for', task_completion_rate * 100, 'percent')

    def perform_task(self):
        self.task_start_time = self.env.now
        yield self.env.timeout(20)
        self.task_start_time = None

    @property
    def done(self):
        return self.completed_count == self.task_count


def test_improved_stop_idea():
    env = simpy.Environment()
    stop_event = env.timeout(50)  # all work should stop after 50 seconds
    activity = ImprovedDummyStopActivity(env, stop_event)
    env.run()

    assert not activity.done
    assert activity.completed_count == 2.5

    # process control of activity stops after 50 seconds, but its yield to timeout causes the environment to continue
    # running until the timeout triggers, thus env.now is 60 after simulation completion
    assert env.now == 60
    assert activity.stop_time == 50
