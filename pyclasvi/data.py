#=============================================#
# Python Clang AST Viewer - Data structures
#
# Copyright (C) 2022 Frank Mueller
# SPDX-License-Identifier: MIT
#=============================================#

import clang.cindex
import ctypes

from pyclasvi.utils import join


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


class InputModel:
    def __init__(self, filename='', arguments=[]):
        self.filename = filename
        self.arguments = arguments

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, value):
        self._filename = value

    @property
    def arguments(self):
        return self._arguments

    @arguments.setter
    def arguments(self, value):
        self._arguments = value

    def replace_arg(self, name, new_arg):
        i = -1
        for idx, arg in enumerate(self._arguments):
            if arg.startswith(name):
                i = idx
                break;

        if i >= 0:
            if new_arg:
                self._arguments[i] = new_arg
            else:
                self._arguments.pop(i)
        elif new_arg:
            self._arguments.append(new_arg)

    def add_arg(self, new_arg):
        self._arguments.append(new_arg)

    def load_file(self, filename):
        data = []
        with open(filename, 'r') as f:
            data = f.read()
        if data:
            lines = data.split('\n')
            if len(lines) > 0:
                self.filename = lines[0]
                self.arguments = lines[1:]

    def save_file(self, filename):
        with open(filename, 'w') as f:
            f.write(join(self.filename, '\n'))
            for arg in self.arguments:
                f.write(join(arg, '\n'))
