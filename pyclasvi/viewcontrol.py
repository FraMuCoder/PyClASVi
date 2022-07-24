# ============================================= #
# Python Clang AST Viewer - View Controller
#
# Copyright (C) 2022 Frank Mueller
# SPDX-License-Identifier: MIT
# ============================================= #

import sys

if sys.version_info.major == 2:
    import tkMessageBox
else: # python3
    import tkinter.messagebox as tkMessageBox


class InputFrameController:
    def __init__(self, model, view, parse_cmd=None):
        self._model = model
        self._view = view
        self._parse_cmd = parse_cmd
        self._view.sync_from_model(self._model)

    def on_load(self, filename):
        try:
            self._model.load_file(filename)
        except IOError as e:
            tkMessageBox.showerror(title='Error on load', message=str(e))
        else:
            self._view.sync_from_model(self._model)

    def on_save(self, filename):
        self._view.sync_to_model(self._model)
        try:
            self._model.save_file(filename)
        except IOError as e:
            tkMessageBox.showerror(title='Error on save', message=str(e))

    def set_parse_cmd(self, parse_cmd):
        self._parse_cmd = parse_cmd

    def on_parse(self):
        if self._parse_cmd:
            self._view.sync_to_model(self._model)
            self._parse_cmd()


class OutputFrameController:
    def __init__(self, model, view):
        self._model = model
        self._view = view

    def set_translation_unit(self, tu):
        self._model.set_translation_unit(tu)
        self._view.sync_from_model(self._model, domain=('ast', 'cursor', 'history',))

    def get_cursor_id(self):
        return self._model.cur_cursor_id

    def set_cursor_id(self, iid):
        self._model.cur_cursor_id = iid

    def get_cursor(self):
        return self._model.cur_cursor

    def set_cursor(self, cursor):
        self._model.cur_cursor = cursor

    def set_active_cursor_by_id(self, iid, update_history=True):
        if iid == self._model.cur_cursor_id:
            return

        self._model.cur_cursor_id = iid

        if update_history:
            self._model.history.insert(iid)
        # ToDo:
        self._view._update_doubles()
        self._view._update_search()

        self._view.sync_from_model(self._model, domain=('cursor', 'history',))

    def on_ast_selection(self, selected_id):
        self.set_active_cursor_by_id(selected_id)

    def on_history_backward(self):
        new_id = self._model.history.go_backward()
        if new_id is not None:
            self.set_active_cursor_by_id(new_id, update_history=False)

    def on_history_forward(self):
        new_id = self._model.history.go_forward()
        if new_id is not None:
            self.set_active_cursor_by_id(new_id, update_history=False)
