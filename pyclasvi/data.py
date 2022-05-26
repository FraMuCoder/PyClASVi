#=============================================#
# Python Clang AST Viewer - Data structures
#
# Copyright (C) 2022 Frank Mueller
# SPDX-License-Identifier: MIT
#=============================================#

import clang.cindex
import ctypes


# Cursor objects have a hash property but no __hash__ method
# You can use this class to make Cursor object hashable
class HashableObj:
    """Wrapper class to make Cursor objects hashable.
    """
    def __init__(self, obj):
        self.obj = obj

    def __eq__(self, other):
        return self.obj == other.obj

    def __hash__(self):
        return self.obj.hash
