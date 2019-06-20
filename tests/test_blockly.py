#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `openclsim` package."""

import types

import pytest

import numpy as np


@pytest.fixture
def code():
    """sample code"""

    code = """
def callback():
    return 'callback called'
"""
    return code


def test_blockly_callback(code):
    """test if we can parse and execute a callback from blockly"""
    #
    module = types.ModuleType("module")
    # compile into ast (use <string> as a filename)
    ast = compile(code, filename="<string>", mode="exec")
    # execute the code in the context of the module
    exec(ast, module.__dict__)
    # call the function
    result = module.callback()
    assert result == "callback called"
