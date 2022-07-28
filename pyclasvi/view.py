#=============================================#
# Python Clang AST Viewer - View classes
#
# Copyright (C) 2022 Frank Mueller
# SPDX-License-Identifier: MIT
#=============================================#

import sys

if sys.version_info.major == 2:
    import ttk
    import Tkinter as tk
    import tkFont
    import tkFileDialog
    import tkMessageBox
else: # python3
    import tkinter.ttk as ttk
    import tkinter as tk
    import tkinter.font as tkFont
    import tkinter.filedialog as tkFileDialog
    import tkinter.messagebox as tkMessageBox

from pyclasvi.utils import toStr
from pyclasvi.utils import join


# Make widget scrollable by adding scrollbars to the right and below it.
# Of course parent is the parent widget of widget.
# If there are more than one widget inside the parent use widgetRow and widgetColumn
# to specify witch widget should be scrollable.
def make_scrollable(parent, widget, widgetRow=0, widgetColumn=0):
        vsb = ttk.Scrollbar(parent, orient='vertical',command=widget.yview)
        widget.configure(yscrollcommand=vsb.set)
        vsb.grid(row=widgetRow, column=widgetColumn+1, sticky='ns')

        hsb = ttk.Scrollbar(parent, orient='horizontal',command=widget.xview)
        widget.configure(xscrollcommand=hsb.set)
        hsb.grid(row=widgetRow+1, column=widgetColumn, sticky='we')


# Widget to handle all inputs (file name and parameters).
# Contain [Parse] Button to start parsing and fill result in output frames
class InputFrame(ttk.Frame):
    def __init__(self, master=None):
        ttk.Frame.__init__(self, master)
        self._controller = None
        self.grid(sticky='nswe')
        self._filename = tk.StringVar(value='')
        self._xValue = tk.StringVar(value=InputFrame._X_OPTIONS[0])       # Option starting with "-x"
        self._stdValue = tk.StringVar(value=InputFrame._STD_OPTIONS[0])   # Option starting with "-std"
        self._create_widgets()

    _SOURCEFILETYPES = (
        ('All source files', '.h', 'TEXT'),
        ('All source files', '.c', 'TEXT'),
        ('All source files', '.hh', 'TEXT'),
        ('All source files', '.hpp', 'TEXT'),
        ('All source files', '.hxx', 'TEXT'),
        ('All source files', '.h++', 'TEXT'),
        ('All source files', '.C', 'TEXT'),
        ('All source files', '.cc', 'TEXT'),
        ('All source files', '.cpp', 'TEXT'),
        ('All source files', '.cxx', 'TEXT'),
        ('All source files', '.c++', 'TEXT'),
        ('All files', '*'),
        )

    _FILETYPES = (
        ('Text files', '.txt', 'TEXT'),
        ('All files', '*'),
        )
    _X_OPTIONS = (
        'no -x',
        '-xc',
        '-xc++'
        )
    _STD_OPTIONS = (
        'no -std',
        '-std=c89',
        '-std=c90',
        '-std=iso9899:1990',
        '-std=iso9899:199409',
        '-std=gnu89',
        '-std=gnu90',
        '-std=c99',
        '-std=iso9899:1999',
        '-std=gnu99',
        '-std=c11',
        '-std=iso9899:2011',
        '-std=gnu11',
        '-std=c17',
        '-std=iso9899:2017',
        '-std=gnu17',
        '-std=c++98',
        '-std=c++03',
        '-std=gnu++98',
        '-std=gnu++03',
        '-std=c++11',
        '-std=gnu++11',
        '-std=c++14',
        '-std=gnu++14',
        '-std=c++17',
        '-std=gnu++17',
        '-std=c++2a',
        '-std=gnu++2a'
        )

    def _create_widgets(self):
        self.rowconfigure(4, weight=1)
        self.columnconfigure(0, weight=1)

        ttk.Label(self, text='Input file:').grid(row=0, sticky='w')
        fileFrame = ttk.Frame(self)
        fileFrame.columnconfigure(0, weight=1)
        fileFrame.grid(row=1, column=0, columnspan=2, sticky='we')
        filenameEntry = ttk.Entry(fileFrame, textvariable=self._filename)
        filenameEntry.grid(row=0, column=0, sticky='we')
        button = ttk.Button(fileFrame, text='...', command=self._on_select_file)
        button.grid(row=0, column=1)

        ttk.Label(self, text='Arguments:').grid(row=2, sticky='w')
        buttonFrame = ttk.Frame(self)
        buttonFrame.grid(row=3, column=0, columnspan=2, sticky='we')
        button = ttk.Button(buttonFrame, text='+ Include', command=self._on_include)
        button.grid()
        button = ttk.Button(buttonFrame, text='+ Define', command=self._on_define)
        button.grid(row=0, column=1)

        xCBox = ttk.Combobox(buttonFrame, textvariable=self._xValue, 
                values=InputFrame._X_OPTIONS)
        xCBox.bind('<<ComboboxSelected>>', self._on_select_x)
        xCBox.grid(row=0, column=2)

        stdCBox = ttk.Combobox(buttonFrame, textvariable=self._stdValue, 
                values=InputFrame._STD_OPTIONS)
        stdCBox.bind('<<ComboboxSelected>>', self._on_select_std)
        stdCBox.grid(row=0, column=3)

        self._argsText = tk.Text(self, wrap='none')
        self._argsText.grid(row=4, sticky='nswe')
        make_scrollable(self, self._argsText, widgetRow=4, widgetColumn=0)

        buttonFrame = ttk.Frame(self)
        buttonFrame.grid(row=6, column=0, columnspan=2, sticky='we')
        buttonFrame.columnconfigure(2, weight=1)

        button = ttk.Button(buttonFrame, text='Load', command=self._on_load)
        button.grid(row=0, column=0)

        button = ttk.Button(buttonFrame, text='Save', command=self._on_save)
        button.grid(row=0, column=1)

        button = ttk.Button(buttonFrame, text='Parse', command=self._on_parse)
        button.grid(row=0, column=2, sticky='we')

    def set_controller(self, controller):
        self._controller = controller

    def sync_from_model(self, model):
        self._filename.set(model.filename)
        self._set_args(model.arguments)

    def sync_to_model(self, model):
        model.filename = self._filename.get()
        model.arguments = self._get_args()

    def _on_load(self):
        if self._controller:
            fn = tkFileDialog.askopenfilename(filetypes=InputFrame._FILETYPES)
            if fn:
                self._controller.on_load(fn)

    def _on_save(self):
        if self._controller:
            fn = tkFileDialog.asksaveasfilename(defaultextension='.txt', filetypes=InputFrame._FILETYPES)
            if fn:
                self._controller.on_save(fn)

    def _on_select_file(self):
        fn = tkFileDialog.askopenfilename(filetypes=self._SOURCEFILETYPES)
        if fn:
            self._filename.set(fn)

    def _on_include(self):
        dir = tkFileDialog.askdirectory()
        if dir:
            self._add_arg(join('-I', dir))

    def _on_define(self):
        self._add_arg('-D<name>=<value>')

    def _on_select_x(self, e):
        arg = self._xValue.get()
        if arg == InputFrame._X_OPTIONS[0]:
            arg = None
        self._set_arg('-x', arg)

    def _on_select_std(self, e):
        arg = self._stdValue.get()
        if arg == InputFrame._STD_OPTIONS[0]:
            arg = None
        self._set_arg('-std', arg)

    def _on_parse(self):
        if self._controller:
            self._controller.on_parse()

    # Set a single arg starting with name.
    # Replace or erase the first arg if there is still one starting with name.
    # total is full argument string starting with name for replacement or None or empty string for erase.
    def _set_arg(self, name, total):
        args = self._get_args()
        i = 0
        for arg in args:
            if arg.startswith(name):
                break;
            i += 1

        newArgs = args[:i]
        if total:
            newArgs.append(total)
        if i < len(args):
            newArgs.extend(args[i+1:])

        self._set_args(newArgs)

    # Set/replace all args
    def _set_args(self, args):
        self._argsText.delete('1.0', 'end')
        for arg in args:
            self._add_arg(arg)

    def _add_arg(self, arg):
        txt = self._argsText.get('1.0', 'end')
        if len(txt) > 1: # looks like there is always a trailing newline
            prefix = '\n'
        else:
            prefix = ''
        self._argsText.insert('end', join(prefix, arg))

    def _get_args(self):
        args = []

        argStr = self._argsText.get('1.0', 'end')
        argStrList = argStr.split('\n')
        for arg in argStrList:
            if len(arg) > 0:
                args.append(arg)

        return args


# Widget to show the AST in a Treeview like folders in a file browser
class ASTOutputFrame(ttk.Frame):
    def __init__(self, master=None, select_cmd=None):
        ttk.Frame.__init__(self, master)
        self.grid(sticky='nswe')
        self._create_widgets()
        self._select_cmd = select_cmd

    def _create_widgets(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self._ast_view = ttk.Treeview(self, selectmode='browse')
        self._ast_view.tag_configure('default', font='TkFixedFont')
        self._ast_view.bind('<<TreeviewSelect>>', self._on_selection)

        make_scrollable(self, self._ast_view)

        self._ast_view.heading('#0', text='Cursor')
        self._ast_view.grid(row=0, column=0, sticky='nswe')

    def set_select_cmd(self, select_cmd):
        self._select_cmd = select_cmd

    def sync_from_model(self, model):
        self.clear()
        model.traverse(self._insert_children)

    def _on_selection(self, event):
        if self._select_cmd is not None:
            iid = self._ast_view.focus()
            self._select_cmd(iid)

    def get_current_id(self):
        return self._ast_view.focus()

    def set_current_id(self, iid):
        self._ast_view.focus(iid)
        self._ast_view.selection_set(iid)
        self._ast_view.see(iid)

    def clear(self):
        for i in self._ast_view.get_children():
            self._ast_view.delete(i)

    def _insert_children(self, **kwargs):
        cursor = kwargs['cursor']
        p_id = kwargs['parent_id']
        c_id = kwargs['cursor_id']

        self._ast_view.insert(p_id,
                              'end',
                              iid=c_id,
                              text=toStr(cursor),
                              tags=['default'])
