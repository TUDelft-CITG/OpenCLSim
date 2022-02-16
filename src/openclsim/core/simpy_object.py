"""General object which can be extended by any class requiring a simpy environment."""


class SimpyObject:
    """
    General object which can be extended by any class requiring a simpy environment.

    Parameters
    ----------
    env
        A simpy Environment
    """

    def __init__(self, env, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.env = env
