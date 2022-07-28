# ============================================= #
# Python Clang AST Viewer - View Controller
#
# Copyright (C) 2022 Frank Mueller
# SPDX-License-Identifier: MIT
# ============================================= #

import sys
import clang.cindex

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
        self._view.sync_from_model(self._model, domain=('ast',))

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
        if self._model.search_result:
            self._model.search_result.set_pos_to_element(iid)

        self._view.sync_from_model(self._model, domain=('cursor', 'history', 'search',))

    def on_cursor_selection(self, selection):
        """Called if a new Cursor was selected by the view.

        Parameters:
            selection: Selected Cursor as Cursor itself or Cursor ID
        """
        if isinstance(selection, clang.cindex.Cursor):
            selection = self._model.ast.get_ids_from_cursor(selection)
            if isinstance(selection, list):  # partly multimap
                selection = selection[0]
        self.set_active_cursor_by_id(selection)

    def on_history_backward(self):
        new_id = self._model.history.go_backward()
        if new_id is not None:
            self.set_active_cursor_by_id(new_id, update_history=False)

    def on_history_forward(self):
        new_id = self._model.history.go_forward()
        if new_id is not None:
            self.set_active_cursor_by_id(new_id, update_history=False)

    def on_doubles_backward(self):
        id_list = self._model.ast.get_ids_from_cursor(self._model.cur_cursor)
        if isinstance(id_list, list):
            new_idx = (id_list.index(self._model.cur_cursor_id) - 1) % len(id_list)
            new_id = id_list[new_idx]
            self.set_active_cursor_by_id(new_id)

    def on_doubles_forward(self):
        id_list = self._model.ast.get_ids_from_cursor(self._model.cur_cursor)
        if isinstance(id_list, list):
            new_idx = (id_list.index(self._model.cur_cursor_id) + 1) % len(id_list)
            new_id = id_list[new_idx]
            self.set_active_cursor_by_id(new_id)

    def on_search(self, **kwargs):
        self._model.search_result = self._model.ast.search(**kwargs)
        new_id = self._model.search_result.get_current()
        if (new_id is not None) and (new_id != self._model.cur_cursor_id):
            self.set_active_cursor_by_id(new_id)
        else:
            self._view.sync_from_model(self._model, domain=('search',))

    def on_search_backward(self):
        new_id = self._model.search_result.go_backward()
        self.set_active_cursor_by_id(new_id)

    def on_search_forward(self):
        new_id = self._model.search_result.go_forward()
        self.set_active_cursor_by_id(new_id)

    def on_marker_store(self, index):
        self._model.marker[index] = self._model.cur_cursor_id
        self._view.sync_from_model(self._model, domain=('marker',))

    def on_marker_restore(self, index):
        self.set_active_cursor_by_id(self._model.marker[index])
        self._view.sync_from_model(self._model, domain=('marker',))

    def request_update(self, domain):
        self._view.sync_from_model(self._model, domain=domain)
