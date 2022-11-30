import pytest

import openclsim.core


def test_identifiable():
    with pytest.warns(DeprecationWarning):
        openclsim.core.Identifiable(ID="abc", name="abc")
    with pytest.warns(None):
        openclsim.core.Identifiable(id="abc", name="abc")
