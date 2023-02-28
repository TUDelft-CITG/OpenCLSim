class Priority:
    def __init__(self, env, priority=0, *args, **kwargs):
        super().__init__(env, *args, **kwargs)
        self.priority = priority

    def can_sail(self, location):
        """Determine if the vessel can sail through the given location."""
        priority_level = location.priority_level
        return self.priority >= priority_level

    def enter_location(self, location):
        """Request permission to enter the location based on priority."""
        with location.request(priority=self.priority) as req:
            yield req

class Location:
    def __init__(self, env, priority_level=0):
        self.env = env
        self.priority_level = priority_level
        self.queue = []

    def request(self, priority=0):
        """Request permission to enter the location."""
        req = self.env.event()
        self.queue.append((priority, req))
        self.queue.sort(reverse=True)
        return req

    def allow_next(self):
        """Allow the next vessel in the queue to enter the location."""
        if len(self.queue) > 0:
            _, req = self.queue.pop(0)
            req.succeed()
