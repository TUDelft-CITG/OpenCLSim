import pathlib

import openclsim


def find_src_path():
    """Lookup the path where the package are located. Returns a pathlib.Path object."""
    openclsim_path = pathlib.Path(openclsim.__file__)
    # check if the path looks normal
    assert "openclsim" in str(
        openclsim_path
    ), "we can't find the openclsim path: {openclsim_path} (openclsim not in path name)"
    # src_dir/openclsim/__init__.py -> ../.. -> src_dir
    src_path = openclsim_path.parent.parent
    return src_path


def find_notebook_path():
    """Lookup the path where the notebooks are located. Returns a pathlib.Path object."""
    src_path = find_src_path()
    notebook_path = src_path / "notebooks"
    return notebook_path
