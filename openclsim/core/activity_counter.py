"""Activity counter function for vessels to support the learing curve."""


class ActivityCounter:
    """Activity counter function for vessels to support the learing curve."""

    def __init__(self, *args, **kwargs):
        """Spin up of the class."""
        super().__init__(*args, **kwargs)

        self.activity_count = {}

    def count_activity(self, activity_name):
        if activity_name in self.activity_count.keys():
            self.activity_count[activity_name] += 1
        else:
            self.activity_count[activity_name] = 1

        return self.activity_count[activity_name]

    def get_activity_count(self, activity_name):
        return self.activity_count.get(activity_name, 0)
