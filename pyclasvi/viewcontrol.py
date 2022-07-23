#=============================================#
# Python Clang AST Viewer - View Controller
#
# Copyright (C) 2022 Frank Mueller
# SPDX-License-Identifier: MIT
#=============================================#

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
        self._view.set_translation_unit(tu)
