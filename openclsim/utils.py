"""Util functions for OpenCLSim."""


def subcycle_repetitions(subcycle_frequency, amount):
    if subcycle_frequency == "1/location":
        return amount
    elif subcycle_frequency == "1/cycle":
        return 1
    else:
        raise ValueError(
            "The subcycle frequency input is not one of ['1/location','1/cycle']"
        )
