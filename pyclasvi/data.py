# ============================================= #
# Python Clang AST Viewer - Data structures
#
# Copyright (C) 2022 Frank Mueller
# SPDX-License-Identifier: MIT
# ============================================= #

import clang.cindex
import ctypes
import re

from pyclasvi.utils import toStr
from pyclasvi.utils import join
from pyclasvi.algorithm import traverse_cursor


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
                break

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


class ASTModel:
    def __init__(self):
        self._root = None
        self._map_id_to_cursor = {}
        self._map_cursor_to_ID = {}
        # statistics
        self._cnt_cursors = 0
        self._cnt_doubles = 0
        self._cnt_max_doubles = 0
        self._cnt_max_children = 0
        self._cnt_max_deep = 0

    def clear(self):
        self.clear_structures()
        self._root = None

    def clear_structures(self):
        self._map_id_to_cursor = {}
        self._map_cursor_to_ID = {}
        self._cnt_cursors = 0
        self._cnt_doubles = 0
        self._cnt_max_doubles = 0
        self._cnt_max_children = 0
        self._cnt_max_deep = 0

    def set_root(self, root):
        self.clear_structures()
        self._root = root

    def traverse(self, callback):
        if self._root is None:
            return
        self.clear_structures()

        forward_arg = {
            'callback': callback,
            'last_id': 0,
        }

        traverse_cursor(self._root,
                        callback_pre=self._traversal_preorder_call,
                        callback_post=self._traversal_postorder_call,
                        forward_arg=forward_arg)

        # some statistics
        print('AST has {0} cursors including {1} doubles.'.format(self._cnt_cursors, self._cnt_doubles))
        print('max doubles: {0}, max children {1}, max deep {2}'.format(
            self._cnt_max_doubles, self._cnt_max_children, self._cnt_max_deep))

    def _traversal_preorder_call(self, **kwargs):
        cursor = kwargs['cursor']
        parent_id = kwargs['parent_arg']
        forward_arg = kwargs['forward_arg']
        last_id = forward_arg['last_id']
        callback = forward_arg['callback']

        if parent_id is None:
            parent_id = ''
        new_id = last_id + 1
        forward_arg['last_id'] = new_id
        # Maybe it is a good idea to use strings as ID as TK Treeview use it,
        # but this is just the data model and may be used for other than TK Treeview.
        new_id = str(new_id)

        callback(cursor=cursor, parent_id=parent_id, cursor_id=new_id)

        self._map_id_to_cursor[new_id] = cursor
        hcursor = HashableObj(cursor)

        if hcursor in self._map_cursor_to_ID:  # already in map, make a partly multimap
            self._cnt_doubles += 1
            data = self._map_cursor_to_ID[hcursor]

            # if this is the fist double map to a list of IDs instead of a single ID
            if isinstance(data, str) or isinstance(data, int):
                data = [data]
                self._map_cursor_to_ID[hcursor] = data

            data.append(new_id)

            if len(data) > self._cnt_max_doubles:
                self._cnt_max_doubles = len(data)
        else:  # not jet in map
            self._map_cursor_to_ID[hcursor] = new_id

        self._cnt_cursors += 1

        return new_id

    def _traversal_postorder_call(self, **kwargs):
        cnt_children = kwargs['child_cnt']
        if cnt_children > self._cnt_max_children:
            self._cnt_max_children = cnt_children

        deep = kwargs['deep']
        if deep > self._cnt_max_deep:
            self._cnt_max_deep = deep

    def get_cursor_from_id(self, iid):
        if iid in self._map_id_to_cursor:
            return self._map_id_to_cursor[iid]
        else:
            return None

    def get_ids_from_cursor(self, cursor):
        hcursor = HashableObj(cursor)
        return self._map_cursor_to_ID[hcursor]

    def search(self, **kwargs):
        result = []
        use_cursor_kind = kwargs['use_CursorKind']
        cursor_kind = kwargs['CursorKind']
        spelling = kwargs['spelling']
        case_insensitive = kwargs['caseInsensitive']
        use_regex = kwargs['use_RexEx']
        if use_regex:
            re_flags = 0
            if case_insensitive:
                re_flags = re.IGNORECASE
            try:
                re_obj = re.compile(spelling, re_flags)
            except re.error as e:
                # ToDo: Error message ('Search RegEx', str(e))
                return result
        elif case_insensitive:
            spelling = spelling.lower()

        for iid, cursor in self._map_id_to_cursor.items():
            found = True
            if use_cursor_kind:
                found = cursor_kind == cursor.kind.name
            if found:
                if use_regex:
                    if not re_obj.match(toStr(cursor.spelling)):
                        found = False
                elif case_insensitive:
                    found = spelling == toStr(cursor.spelling).lower()
                else:
                    found = spelling == toStr(cursor.spelling)
            if found:
                result.append(iid)

        return WalkableList(result)


class WalkableList:
    def __init__(self, data):
        if data:
            self._data = data
        else:
            self._data = []
        self._pos = 0

    def clear(self):
        self._data = []
        self._pos = 0

    def get_current(self):
        if self.length >= 0:
            return self._data[self._pos]
        else:
            return None

    @property
    def length(self):
        return len(self._data)

    def __len__(self):
        return len(self._data)

    def __contains__(self, value):
        return value in self._data

    def __getitem__(self, index):
        return self._data[index]

    def __iter__(self):
        return iter(self._data)

    @property
    def pos(self):
        return self._pos

    def set_pos_to_element(self, element):
        if element in self._data:
            self._pos = self._data.index(element)

    def can_go_backward(self):
        return self.pos > 0

    def can_go_forward(self):
        return (self.length > 1) and ((self.pos + 1) < self.length)

    def go_backward(self):
        self._pos = (self._pos - 1) % self.length
        return self.get_current()

    def go_forward(self):
        self._pos = (self._pos + 1) % self.length
        return self.get_current()


class HistoryModel:
    def __init__(self, max=25):
        self._history = []
        self._pos = -1
        self._MAX_HISTORY = max

    def clear(self):
        self._history = []
        self._pos = -1

    @property
    def length(self):
        return len(self._history)

    @property
    def pos(self):
        return self._pos

    def can_go_backward(self):
        return self.pos > 0

    def can_go_forward(self):
        return (self.length > 1) and ((self.pos + 1) < self.length)

    def insert(self, new_elem):
        if self._pos < len(self._history):
            # we travel backward in time and change the history,
            # so we change the timeline and the future
            # therefore erase the old future
            self._history = self._history[:(self._pos + 1)]
            # now the future is an empty sheet of paper

        if len(self._history) >= self._MAX_HISTORY:  # history to long?
            self._history = self._history[1:]
        else:
            self._pos = self._pos + 1

        self._history.append(new_elem)

    def get(self):
        if self._pos >= 0:
            return self._history[self._pos]
        else:
            return None

    def go_backward(self):
        if self._pos > 0:
            self._pos -= 1
        return self.get()

    def go_forward(self):
        if (self._pos + 1) < len(self._history):
            self._pos += 1
        return self.get()


class OutputModel:
    def __init__(self):
        self._translation_unit = None
        self._ast = ASTModel()
        self._cur_cursor_id = ''
        self._cur_cursor = None
        self._history = HistoryModel()
        self._search_result = None

    @property
    def ast(self):
        return self._ast

    @property
    def history(self):
        return self._history

    @property
    def cur_cursor_id(self):
        return self._cur_cursor_id

    @cur_cursor_id.setter
    def cur_cursor_id(self, value):
        self._cur_cursor_id = value
        self._cur_cursor = self.ast.get_cursor_from_id(value)

    @property
    def cur_cursor(self):
        return self._cur_cursor

    @cur_cursor.setter
    def cur_cursor(self, value):
        self._cur_cursor = value

    @property
    def search_result(self):
        return self._search_result

    @search_result.setter
    def search_result(self, value):
        self._search_result = value

    def clear(self):
        self._ast.clear()
        self._history.clear()

    def set_translation_unit(self, tu):
        self.clear()
        self._translation_unit = tu
        self._ast.set_root(tu.cursor)
