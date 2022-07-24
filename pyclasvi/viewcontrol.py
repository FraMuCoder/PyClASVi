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
        self._view.sync_from_model(self._model)

    def get_cursor_id(self):
        return self._model.cur_cursor_id

    def set_cursor_id(self, iid):
        self._model.cur_cursor_id = iid

    def get_cursor(self):
        return self._model.cur_cursor

    def set_cursor(self, cursor):
        self._model.cur_cursor = cursor

    def set_active_cursor_by_id(self, iid):
        if iid == self._model.cur_cursor_id:
            return

        self._model.cur_cursor_id = iid
        cursor = self._model.ast_model.get_cursor_from_id(iid)

        # ToDo: use MVC concept
        self._view._set_active_cursor(cursor)
        self._view._add_history(iid)
        self._view.curIID = iid
        # ToDo:
        self._view._update_doubles()
        self._view._update_search()

    def on_ast_selection(self, selected_id):
        self.set_active_cursor_by_id(selected_id)
