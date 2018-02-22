#!/usr/bin/env python

# Python ClASVi
# Python Clang AST Viewer
# PyClASVi is distributed under the MIT License, see LICENSE

# TODO
#
# General
#   Test unter Windows
#   Test/fix Clang versions > 3.8
#   Better code documentation
#   Check coding style
#   Add documentation "How to access Clang AST"
# Input frame
#   Add buttons for input language and language version
# Error frame
#   Filter for severity level
#   Colored output depends on severity
# Output frame
#   Add missing member outputs (see comments in class CursorOutputFrame)
#   Output Tokens
#   Output all other used class types

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

import clang.cindex
import ctypes
import argparse
import inspect
import re


# Python3 clang binding sometimes return bytes instead of strings
# use this function to convert it
def toStr(data):
    if isinstance(data, bytes):
        return data.decode('ascii') # ASCII should be default in C/C++ but what about comments
    elif isinstance(data, clang.cindex.Cursor):
        return '{0} ({1: #011x}) {2}'.format(data.kind.name,
                                             data.hash,
                                             data.displayname)
    elif isinstance(data, clang.cindex.SourceLocation):
        return 'file:   {0}\nline:   {1}\ncolumn: {2}\noffset: {3}'.format(
            data.file, data.line, data.column, data.offset)
    else:
        return str(data)


# check if m is an instance methode
def is_instance_methode(m):
    return inspect.ismethod(m)


# has this instance methode only the self parameter?
def is_simple_instance_methode(m):
    argSpec = inspect.getargspec(m)
    return len(argSpec.args) == 1 # only self


# get methode definition like "(arg1, arg2)" as string
def get_methode_prototype(m):
    argSpec = inspect.getargspec(m)
    return inspect.formatargspec(*argSpec)


# check if obj is in list
def is_obj_in_stack(obj, objStack):
    for o in objStack:
        if o.__class__ == obj.__class__: # some compare function trow exception if types are not equal
            if o == obj:
                return True
    return False

# Cursor objects have a hash property but no __hash__ methode
# You can use this class to make Cursor object hashable
class HashableObj:
    def __init__(self, obj):
        self.obj = obj
    
    def __eq__(self, other):
        return self.obj == other.obj
    
    def __hash__(self):
        return self.obj.hash


# need parent widget and widget witch should be make_scrollable
# Ther should be only this one widget in the parent
def make_scrollable(parent, widget, widgetRow=0, widgetColumn=0):
        vsb = ttk.Scrollbar(parent, orient="vertical",command=widget.yview)
        widget.configure(yscrollcommand=vsb.set)
        vsb.grid(row=widgetRow, column=widgetColumn+1, sticky='ns')
        
        hsb = ttk.Scrollbar(parent, orient="horizontal",command=widget.xview)
        widget.configure(xscrollcommand=hsb.set)
        hsb.grid(row=widgetRow+1, column=widgetColumn, sticky='we')


# Handle all inputs (file name and parameters)
# Contain [Parse] Button to start parsing and fill result in output frames
class InputFrame(ttk.Frame):
    def __init__(self, master=None, parseCmd=None):
        ttk.Frame.__init__(self, master)
        self.grid(sticky='nswe')
        self.parseCmd = parseCmd
        self.filename = tk.StringVar(value="")
        self.create_widgets()

    _filetypes = [
        ("Text files", "*.txt", "TEXT"),
        ("All files", "*"),
        ]

    def create_widgets(self):
        self.rowconfigure(4, weight=1)
        self.columnconfigure(0, weight=1)
        
        ttk.Label(self, text='Input file:').grid(row=0, sticky='w')
        fileFrame = ttk.Frame(self)
        fileFrame.columnconfigure(0, weight=1)
        fileFrame.grid(row=1, column=0, columnspan=2, sticky='we')
        filenameEntry = ttk.Entry(fileFrame, textvariable=self.filename)
        filenameEntry.grid(row=0, column=0, sticky='we')
        button = ttk.Button(fileFrame, text='...', command=self.on_select_file)
        button.grid(row=0, column=1)
        
        ttk.Label(self, text='Arguments:').grid(row=2, sticky='w')
        buttonFrame = ttk.Frame(self)
        buttonFrame.grid(row=3, column=0, columnspan=2, sticky='we')
        button = ttk.Button(buttonFrame, text='+ Include', command=self.on_include)
        button.grid()
        button = ttk.Button(buttonFrame, text='+ Define', command=self.on_define)
        button.grid(row=0, column=1)
        self.argsText = tk.Text(self, wrap="none")
        self.argsText.grid(row=4, sticky='nswe')
        make_scrollable(self, self.argsText, widgetRow=4, widgetColumn=0)

        buttonFrame = ttk.Frame(self)
        buttonFrame.grid(row=6, column=0, columnspan=2, sticky='we')
        buttonFrame.columnconfigure(2, weight=1)

        button = ttk.Button(buttonFrame, text='Load', command=self.on_file_load)
        button.grid(row=0, column=0)
        
        button = ttk.Button(buttonFrame, text='Save', command=self.on_file_save)
        button.grid(row=0, column=1)
        
        button = ttk.Button(buttonFrame, text='Parse', command=self.parseCmd)
        button.grid(row=0, column=2, sticky='we')
    
    def load_filename(self, filename):
        f = open(filename, 'r')
        if f:
            data = f.read()
            f.close()
            lines = data.split("\n")
            if len(lines) > 0:
                self.set_filename(lines[0])
            self.set_args(lines[1:])
    
    def on_file_load(self):
        fn = tkFileDialog.askopenfilename(filetypes=self._filetypes)
        self.load_filename(fn)
    
    def on_file_save(self):
        f = tkFileDialog.asksaveasfile(defaultextension=".txt", filetypes=self._filetypes)
        if f:
            f.write(self.get_filename() + '\n')
            for arg in self.get_args():
                f.write(arg + '\n')
            f.close()
    
    def on_select_file(self):
        fn = tkFileDialog.askopenfilename()
        if fn:
            self.set_filename(fn)
    
    def on_include(self):
        dir = tkFileDialog.askdirectory()
        if dir:
            self.add_arg("-I"+dir)
    
    def on_define(self):
        self.add_arg("-D<name>=<value>")

    def set_parse_cmd(self, parseCmd):
        self.parseCmd = parseCmd
    
    def set_filename(self, fn):
        self.filename.set(fn)

    def get_filename(self):
        return self.filename.get()
    
    def set_args(self, args):
        self.argsText.delete('1.0', 'end')
        for arg in args:
            self.add_arg(arg)
    
    def add_arg(self, arg):
        txt = self.argsText.get('1.0', 'end')
        if len(txt) > 1: # looks like there is always a trailing newline
            prefix = "\n"
        else:
            prefix = ""
        self.argsText.insert('end', prefix + arg)
    
    def get_args(self):
        args = []
        
        argStr = self.argsText.get('1.0', 'end')
        argStrList = argStr.split("\n")
        for arg in argStrList:
            if len(arg) > 0:
                args.append(arg)
        
        return args


# Output all parse warnings and errors
class ErrorFrame(ttk.Frame):
    def __init__(self, master=None):
        ttk.Frame.__init__(self, master)
        self.grid(sticky='nswe')
        self.create_widgets()
        self.errorMap = {}

    def create_widgets(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        
        charSize = tkFont.nametofont('TkHeadingFont').measure('#')
        
        pw = tk.PanedWindow(self, orient='vertical')
        pw.grid(row=0, column=0, sticky='nswe')
        
        frame = ttk.Frame(pw)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.errorTable = ttk.Treeview(frame, columns=('category', 'severity', 'spelling', 'location'))
        self.errorTable.bind('<<TreeviewSelect>>', self.on_selection)
        self.errorTable.grid(row=0, column=0, sticky='nswe')
        make_scrollable(frame, self.errorTable)
        pw.add(frame, stretch="always")
        
        self.errorTable.heading('#0', text='#')
        self.errorTable.column('#0', width=4*charSize, anchor='e', stretch=False)
        self.errorTable.heading('category', text='Category')
        self.errorTable.column('category', width=20*charSize, stretch=False)
        self.errorTable.heading('severity', text='Severity')
        self.errorTable.column('severity', width=8*charSize, stretch=False)
        self.errorTable.heading('spelling', text='Text')
        self.errorTable.column('spelling', width=40*charSize, stretch=False)
        self.errorTable.heading('location', text='Location')
        self.errorTable.column('location', width=40*charSize, stretch=False)
        
        self.fileOutputFrame = FileOutputFrame(pw)
        pw.add(self.fileOutputFrame, stretch="always")

    def on_selection(self, event):
        curItem = self.errorTable.focus()
        err = self.errorMap[curItem]
        range1 = None
        for r in err.ranges:
            range1 = r
            break
        self.fileOutputFrame.set_location(range1, err.location)
    
    def clear_errors(self):
        self.errorMap = {}
        for i in self.errorTable.get_children():
            self.errorTable.delete(i)
    
    def set_errors(self, errors):
        self.clear_errors()
        cnt = 0
        for err in errors:
            cnt = cnt + 1
            serverityTab = {clang.cindex.Diagnostic.Ignored:"Ignored", 
                            clang.cindex.Diagnostic.Note:"Note",
                            clang.cindex.Diagnostic.Warning:"Warning",
                            clang.cindex.Diagnostic.Error:"Error",
                            clang.cindex.Diagnostic.Fatal:"Fatal"}
            
            if err.severity in serverityTab:
                serverity = str(err.severity) + ' ' + serverityTab[err.severity]
            else:
                serverity = str(err.severity)
            if err.location.file:
                location = err.location.file.name + ' ' + str(err.location.line) + ':' + str(err.location.offset)
            else:
                location = None
            iid = self.errorTable.insert('', 'end', text=str(cnt), values=[
                str(err.category_number) + ' ' + toStr(err.category_name),
                serverity,
                err.spelling,
                location
                ])
            self.errorMap[iid] = err
        
        return cnt


# Output the AST in a Treeview like folders in a file browser
class ASTOutputFrame(ttk.Frame):
    def __init__(self, master=None, selectCmd=None):
        ttk.Frame.__init__(self, master)
        self.grid(sticky='nswe')
        self.create_widgets()
        self.translationunit = None
        self.mapIIDtoCursor = {}
        self.mapCursorToIID = {}
        self.selectCmd = selectCmd

    def create_widgets(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        charSize = tkFont.nametofont('TkFixedFont').measure('#')

        self.astView = ttk.Treeview(self, selectmode='browse')
        self.astView.tag_configure('default', font='TkFixedFont')
        self.astView.bind('<<TreeviewSelect>>', self.on_selection)

        make_scrollable(self, self.astView)

        self.astView.heading('#0', text='Cursor')
        self.astView.grid(row=0, column=0, sticky='nswe')

    def on_selection(self, event):
        if self.selectCmd:
            self.selectCmd()

    def set_select_cmd(self, cmd):
        self.selectCmd = cmd

    def get_current_iid(self):
        return self.astView.focus()

    def get_current_iids(self):
        cursor = self.get_current_cursor()
        if cursor:
            return self.mapCursorToIID[HashableObj(cursor)]
        else:
            return None

    def get_current_cursor(self):
        curCursor = None
        curItem = self.astView.focus()
        if curItem:
            curCursor = self.mapIIDtoCursor[curItem]
        return curCursor

    def set_current_iid(self, iid):
        self.astView.focus(iid)
        self.astView.selection_set(iid)
        self.astView.see(iid)

    def set_current_cursor(self, cursor):
        iid = self.mapCursorToIID[HashableObj(cursor)]
        if isinstance(iid, list): # partly multimap
            iid = iid[0]
        self.set_current_iid(iid)

    def clear(self):
        for i in self.astView.get_children():
            self.astView.delete(i)
        self.translationunit = None
        self.mapIIDtoCursor = {}
        self.mapCursorToIID = {}

    def _insert_children(self, cursor, iid, deep=1):
        cntChildren = 0
        for childCursor in cursor.get_children():
            cntChildren = cntChildren + 1
            newIID = self.astView.insert(iid,
                                        'end',
                                        text=toStr(childCursor),
                                        tags=['default'])
            self.mapIIDtoCursor[newIID] = childCursor
            hCursor = HashableObj(childCursor)
            if hCursor in self.mapCursorToIID: # already in map, make a partly multimap
                self.cntDouble = self.cntDouble + 1
                data = self.mapCursorToIID[hCursor]
                if isinstance(data, str):
                    data = [data]
                    self.mapCursorToIID[hCursor] = data
                data.append(newIID)
                if len(data) > self.cntMaxDoubles:
                    self.cntMaxDoubles = len(data)
            else:
                self.mapCursorToIID[hCursor] = newIID
            self._insert_children(childCursor, newIID, deep+1)
            self.cntCursors = self.cntCursors + 1

        if cntChildren > 0:
            if cntChildren > self.cntMaxChildren:
                self.cntMaxChildren = cntChildren
            if deep > self.cntMaxDeep:
                self.cntMaxDeep = deep

    def set_translationunit(self, tu):
        self.cntCursors = 1
        self.cntDouble = 0
        self.cntMaxDoubles = 0
        self.cntMaxChildren = 0
        self.cntMaxDeep = 0
        self.clear()
        self.translationunit = tu
        root = tu.cursor
        iid = self.astView.insert('',
                                  'end',
                                  text=toStr(root),
                                  tags=['default'])
        self.mapIIDtoCursor[iid] = root
        self.mapCursorToIID[HashableObj(root)] = iid
        self._insert_children(root, iid)

        # some statistics
        print('AST has {0} cursors including {1} doubles.'.format(self.cntCursors, self.cntDouble))
        print('max doubles: {0}, max children {1}, max deep {2}'.format(
            self.cntMaxDoubles, self.cntMaxChildren, self.cntMaxDeep))

    def search(self, **kwargs):
        result = []
        useCursorKind = kwargs['use_CursorKind']
        cursorKind = kwargs['CursorKind']
        spelling = kwargs['spelling']
        caseInsensitive = kwargs['caseInsensitive']
        useRegEx = kwargs['use_RexEx']
        if useRegEx:
            reFlags = 0
            if caseInsensitive:
                reFlags = re.IGNORECASE
            try:
                reObj = re.compile(spelling, reFlags)
            except Exception as e:
                tkMessageBox.showerror("Search RegEx", str(e))
                return result
        elif caseInsensitive:
            spelling = spelling.lower()

        for iid in self.mapIIDtoCursor:
            cursor = self.mapIIDtoCursor[iid]
            found = True
            if useCursorKind:
                found = cursorKind == cursor.kind.name
            if found:
                if useRegEx:
                    if not reObj.match(toStr(cursor.spelling)):
                        found = False

                elif caseInsensitive:
                    found = spelling == toStr(cursor.spelling).lower()
                else:
                    found = spelling == toStr(cursor.spelling)
            if found:
                result.append(iid)

        result.sort()

        return result


# Output nearly all members of the selected Cursor object
class CursorOutputFrame(ttk.Frame):
    def __init__(self, master=None, selectCmd=None):
        ttk.Frame.__init__(self, master)
        self.grid(sticky='nswe')
        self.create_widgets()
        self.cursor = None
        self.selectCmd = selectCmd
        self.cursorList = []

    _MAX_DEEP = 5
    _MAX_ITER_OUT = 10
    _DATA_INDENT = '      '

    # ignore member with this types
    _ignore_types = ('function',)

    def create_widgets(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        defFont = tkFont.Font(font="TkFixedFont")
        defFontProp = defFont.actual()
        self.cursorText = tk.Text(self, wrap="none")
        self.cursorText.grid(row=0, sticky='nswe')

        make_scrollable(self, self.cursorText)

        self.cursorText.tag_configure('attr_name', font=(defFontProp['family'], defFontProp['size'], 'bold'))
        self.cursorText.tag_configure('attr_type', foreground='green')
        self.cursorText.tag_configure('attr_err', foreground='red')
        self.cursorText.tag_configure('link', foreground='blue')
        self.cursorText.tag_bind('link', '<ButtonPress-1>', self.on_cursor_click)
        self.cursorText.tag_bind('link', '<Enter>', self.on_link_enter)
        self.cursorText.tag_bind('link', '<Leave>', self.on_link_leave)
        self.cursorText.tag_configure('special', font=(defFontProp['family'], defFontProp['size'], 'italic'))

        for n in range(CursorOutputFrame._MAX_DEEP):
            self.cursorText.tag_configure('section_header_' + str(n), foreground='gray')
            self.cursorText.tag_bind('section_header_' + str(n), "<ButtonPress-1>", self.on_section_click)
            self.cursorText.tag_bind('section_header_' + str(n), '<Enter>', self.on_section_enter)
            self.cursorText.tag_bind('section_header_' + str(n), '<Leave>', self.on_section_leave)
            self.cursorText.tag_configure('section_hidden_' + str(n), elide=True)
            self.cursorText.tag_configure('section_' + str(n))

        self.cursorText.config(state='disabled')

    def on_link_enter(self, event):
        self.cursorText.configure(cursor='hand1')

    def on_link_leave(self, event):
        self.cursorText.configure(cursor='xterm')

    def on_cursor_click(self, event):
        if self.selectCmd == None:
            return

        curIdx = self.cursorText.index("@{0},{1}".format(event.x, event.y))
        linkIdxs = list(self.cursorText.tag_ranges('link'))
        listIdx = 0

        for start, end in zip(linkIdxs[0::2], linkIdxs[1::2]):
            if (self.cursorText.compare(curIdx, '>=', start) and
                self.cursorText.compare(curIdx, '<', end)):
                cursor = self.cursorList[listIdx]
                self.selectCmd(cursor)
                break
            listIdx += 1

    def on_section_enter(self, event):
        self.cursorText.configure(cursor='arrow')

    def on_section_leave(self, event):
        self.cursorText.configure(cursor='xterm')

    def on_section_click(self, event):
        curIdx = self.cursorText.index("@{0},{1}".format(event.x, event.y))

        next_section = None
        curLev = 0
        for n in range(CursorOutputFrame._MAX_DEEP):
            new_next_section = self.cursorText.tag_nextrange('section_'+str(n), curIdx)
            if next_section:
                if new_next_section:
                    if self.cursorText.compare(new_next_section[0], '<', next_section[0]):
                        next_section = new_next_section
                        curLev = n
            elif new_next_section:
                next_section = new_next_section
                curLev = n

        if next_section:
            self.cursorText.config(state='normal')
            cur_header = self.cursorText.tag_prevrange('section_header_'+str(curLev), next_section[0])
            next_hidden = self.cursorText.tag_nextrange('section_hidden_'+str(curLev), curIdx)
            self.cursorText.delete(cur_header[0]+' +1c', cur_header[0]+' +2c')
            if next_hidden and (next_hidden == next_section):
                self.cursorText.tag_remove('section_hidden_'+str(curLev), next_section[0], next_section[1])
                self.cursorText.insert(cur_header[0]+' +1c', '-')
            else:
                self.cursorText.tag_add('section_hidden_'+str(curLev), next_section[0], next_section[1])
                self.cursorText.insert(cur_header[0]+' +1c', '+')
            self.cursorText.config(state='disabled')

    def clear(self):
        self.cursorText.config(state='normal')
        self.cursorText.delete('1.0', 'end')
        self.cursorText.config(state='disabled')
        self.cursor = None
        self.cursorList = []

    def _add_cursor(self, cursor):
        # we got an exception if we compare a Cursor object with an other none Cursor object like None
        # Therfore Cursor == None will not work so we use a try
        if isinstance(cursor, clang.cindex.Cursor):
            self.cursorText.insert('end', 
                                toStr(cursor),
                                'link')
            self.cursorList.append(cursor)
        else:
            self.cursorText.insert('end', str(cursor))

    def _add_attr(self, objStack, attrName):
        obj = objStack[-1]
        deep = len(objStack) - 1
        prefix = '\t' * deep

        # set default values
        attrData = None
        attrDataTag = None
        attrTypeTag = 'attr_type'

        try:
            attrData = getattr(obj, attrName)
            attrType = attrData.__class__.__name__
            if attrType in CursorOutputFrame._ignore_types:
                return
        except BaseException as e:
            attrType = e.__class__.__name__ + ' => do not use this'
            attrTypeTag = 'attr_err'

        if is_instance_methode(attrData):
            attrType = attrType + ' ' + get_methode_prototype(attrData)
            if is_simple_instance_methode(attrData):
                try:
                    attrData = attrData()
                    attrType = attrType + ' => ' + attrData.__class__.__name__
                except BaseException as e:
                    attrData = e.__class__.__name__ + ' => do not use this'
                    attrDataTag = 'attr_err'
                if attrName == 'get_children':
                    cnt = 0
                    for c in attrData:
                        cnt = cnt+1
                    attrData = str(cnt) + ' children, see tree on the left'
                    attrDataTag = 'special'
            else:
                if attrName == 'get_template_argument_kind':
                    nums = obj.get_num_template_arguments()
                    attrData = ''
                    if nums > 0:
                        for n in range(nums):
                            attrData = attrData + '(num='+str(n)+') = '
                            attrData = attrData + str(obj.get_template_argument_kind(n)) + '\n'
                # TODO
                # get_template_argument_type
                # get_template_argument_value
                # get_template_argument_unsigned_value

        self.cursorText.insert('end', prefix)
        self.cursorText.insert('end', '[-] ', 'section_header_'+str(deep))
        self.cursorText.insert('end', attrName, 'attr_name')
        self.cursorText.insert('end', ' (')
        self.cursorText.insert('end', attrType, attrTypeTag)
        self.cursorText.insert('end', '):\n')

        startIdx = self.cursorText.index('end -1c')

        nested = False
        if hasattr(attrData, "__iter__") and not isinstance(attrData, (str, bytes)):
            self.cursorText.insert('end', prefix+CursorOutputFrame._DATA_INDENT+'[\n')
            cnt = 0
            for d in attrData:
                cnt = cnt+1
                if cnt <= CursorOutputFrame._MAX_ITER_OUT:
                    self._add_attr_data(objStack, prefix+'   ', d, attrDataTag)
                    self.cursorText.delete('end -1c', 'end')
                    self.cursorText.insert('end', ',\n')
                else:
                    self.cursorText.insert('end',
                                           prefix+'   '+CursorOutputFrame._DATA_INDENT+'and some more...\n',
                                           'special')
                    break
            self.cursorText.insert('end', prefix+CursorOutputFrame._DATA_INDENT+']\n')
            nested = True
        else:
            nested = self._add_attr_data(objStack, prefix, attrData, attrDataTag)

        #self.cursorText.insert('end', '\n') # use this if you want an extra line witch can be hidden
        endIdx = self.cursorText.index('end -1c')
        #self.cursorText.insert('end', '\n') # use this if you want an extra line witch can't be hidden

        self.cursorText.tag_add('section_'+str(deep), startIdx, endIdx)
        if nested:
            cur_header = self.cursorText.tag_prevrange('section_header_'+str(deep), 'end')
            self.cursorText.delete(cur_header[0]+' +1c', cur_header[0]+' +2c')
            self.cursorText.insert(cur_header[0]+' +1c', '+')
            self.cursorText.tag_add('section_hidden_'+str(deep), startIdx, endIdx)

    def _add_attr_data(self, objStack, prefix, attrData, attrDataTag):
        nested = False
        deep = len(objStack) - 1

        if isinstance(attrData, clang.cindex.Cursor):
            self.cursorText.insert('end', prefix+CursorOutputFrame._DATA_INDENT)
            self._add_cursor(attrData)
            self.cursorText.insert('end', '\n')
        elif (isinstance(attrData, clang.cindex.Type) 
              or isinstance(attrData, clang.cindex.SourceRange)):
            if not is_obj_in_stack(attrData, objStack): #attrData not in objStack:
                if (deep+1) < CursorOutputFrame._MAX_DEEP:
                    objStack.append(attrData)
                    self._add_obj(objStack)
                    objStack.pop()
                else:
                    self.cursorText.insert('end', prefix+CursorOutputFrame._DATA_INDENT)
                    self.cursorText.insert('end',
                                          'To deep to show ' + toStr(attrData),
                                          'special')
                    self.cursorText.insert('end', '\n')
            else:
                self.cursorText.insert('end', prefix+CursorOutputFrame._DATA_INDENT)
                self.cursorText.insert('end',
                                       toStr(attrData) + ' already shown!',
                                       'special')
                self.cursorText.insert('end', '\n')
            nested = True
        elif attrData.__class__ == int: # not bool
            self.cursorText.insert('end', prefix+CursorOutputFrame._DATA_INDENT)
            self.cursorText.insert('end', '{0} ({0: #011x})'.format(attrData), attrDataTag)
            self.cursorText.insert('end', '\n')
        elif (sys.version_info.major) == 2 and isinstance(attrData, long):
            self.cursorText.insert('end', prefix+CursorOutputFrame._DATA_INDENT)
            self.cursorText.insert('end', '{0} ({0: #019x})'.format(attrData), attrDataTag)
            self.cursorText.insert('end', '\n')
        else:
            lines = toStr(attrData).split('\n')
            for line in lines:
                self.cursorText.insert('end', prefix+CursorOutputFrame._DATA_INDENT)
                self.cursorText.insert('end', line, attrDataTag)
                self.cursorText.insert('end', '\n')

        return nested

    def _add_obj(self, objStack):
        if objStack and (len(objStack) > 0):
            obj = objStack[-1]
            attrs = dir(obj)
            for attrName in attrs:
                # ignore all starts with '_'
                if attrName[0] == '_':
                    continue
                self._add_attr(objStack, attrName)

    def set_cursor(self, c):
        if not isinstance(c, clang.cindex.Cursor):
            self.clear()
            return
        if isinstance(self.cursor, clang.cindex.Cursor):
            if self.cursor == c:
                return
        self.cursorList = []
        self.cursor = c
        self.cursorText.config(state='normal')
        self.cursorText.delete('1.0', 'end')
        self._add_obj([c])

        self.cursorText.config(state='disabled')


class FileOutputFrame(ttk.Frame):
    def __init__(self, master=None):
        ttk.Frame.__init__(self, master)
        self.grid(sticky='nswe')
        self.create_widgets()
        self.fileName = None

    def create_widgets(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        
        self.fileText = tk.Text(self, wrap="none")
        self.fileText.grid(row=0, sticky='nswe')
        self.fileText.tag_configure('range', background='gray')
        self.fileText.tag_configure('location', background='yellow')
        
        make_scrollable(self, self.fileText)
        
        self.fileText.config(state='disabled')
    
    def clear(self):
        self.fileText.config(state='normal')
        self.fileText.delete('1.0', 'end')
        self.fileText.config(state='disabled')
        self.fileName = None
    
    def set_location(self, srcRange, srcLocation):
        self.fileText.config(state='normal')
        self.fileText.tag_remove('range', '1.0', 'end')
        self.fileText.tag_remove('location', '1.0', 'end')

        newFileName = None
        if isinstance(srcRange, clang.cindex.SourceRange):
            newFileName = srcRange.start.file.name
        elif (isinstance(srcLocation, clang.cindex.SourceLocation) and
              srcLocation.file):
            newFileName = srcLocation.file.name
        else:
            self.fileText.delete('1.0', 'end')
        
        if newFileName and (self.fileName != newFileName):
            self.fileText.delete('1.0', 'end')
            f = open(newFileName, 'r')
            if f:
                data = f.read()
                f.close()
                self.fileText.insert('end', data)
        
        self.fileName = newFileName
        
        if isinstance(srcRange, clang.cindex.SourceRange):
            srcFrom =  '{0}.{1}'.format(srcRange.start.line, srcRange.start.column-1)
            srcTo =  '{0}.{1}'.format(srcRange.end.line, srcRange.end.column)
            self.fileText.tag_add('range', srcFrom, srcTo)
            self.fileText.see(srcFrom)
        
        if isinstance(srcLocation, clang.cindex.SourceLocation):
            if srcLocation.file:
                locFrom =  '{0}.{1}'.format(srcLocation.line, srcLocation.column-1)
                locTo =  '{0}.{1}'.format(srcLocation.line, srcLocation.column)
                self.fileText.tag_add('location', locFrom, locTo)
                self.fileText.see(locFrom)
        
        self.fileText.config(state='disabled')


# separat dialog window for search
class SearchDialog(tk.Toplevel):
    
    _old_data = None
    
    def __init__(self, master=None):
        tk.Toplevel.__init__(self, master)
        self.transient(master)
        
        self.result = False
        self.kindOptions = []
        for kind in clang.cindex.CursorKind.get_all_kinds():
            self.kindOptions.append(kind.name)
        self.kindOptions.sort()
        self.kindState = tk.IntVar(value=0)
        self.kindValue = tk.StringVar(value=self.kindOptions[0])
        self.searchtext = tk.StringVar(value="")
        self.caseInsensitive = tk.IntVar(value=0)
        self.useRegEx = tk.IntVar(value=0)
        
        if SearchDialog._old_data:
            self.set_data(**SearchDialog._old_data)
        
        self.title('Search')
        self.create_widgets()
        self.on_check_kind()
        
        self.grab_set()
        
        self.bind("<Return>", self.on_ok)
        self.bind("<Escape>", self.on_cancel)
        
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        
        self.wait_window(self)
    
    def create_widgets(self):
        self.columnconfigure(0, weight=1)
        
        frame = ttk.Frame(self)
        frame.grid(row=0, column=0, sticky='nesw')
        frame.columnconfigure(1, weight=1)
        
        cb=ttk.Checkbutton(frame, text="Kind:", variable=self.kindState, command=self.on_check_kind)
        cb.grid(row=0, column=0)
        self.kindCBox = ttk.Combobox(frame, textvariable=self.kindValue, values=self.kindOptions)
        self.kindCBox.grid(row=0, column=1, sticky='we')
        
        label = tk.Label(frame, text='Spelling:')
        label.grid(row=1, column=0)
        searchEntry = ttk.Entry(frame, textvariable=self.searchtext, width=25)
        searchEntry.grid(row=1, column=1, sticky='we')
        
        cb=ttk.Checkbutton(frame, text="Ignore case", variable=self.caseInsensitive)
        cb.grid(row=2, column=1, sticky='w')
        cb=ttk.Checkbutton(frame, text="Use RegEx", variable=self.useRegEx)
        cb.grid(row=3, column=1, sticky='w')
        
        frame = ttk.Frame(self)
        frame.grid(row=1, column=0, sticky='e')
        
        btn = tk.Button(frame, text='OK', width=8, command=self.on_ok)
        btn.grid(row=0, column=0, sticky='e')
        
        btn = tk.Button(frame, text='Cancel', width=8, command=self.on_cancel)
        btn.grid(row=0, column=1, sticky='e')
    
    def get_data(self):
        data = {}
        data['use_CursorKind'] = self.kindState.get()
        data['CursorKind'] = self.kindValue.get()
        data['spelling'] = self.searchtext.get()
        data['caseInsensitive'] = self.caseInsensitive.get()
        data['use_RexEx'] = self.useRegEx.get()
        return data
    
    def set_data(self, **kwargs):
        self.kindState.set(kwargs['use_CursorKind'])
        self.kindValue.set(kwargs['CursorKind'])
        self.searchtext.set(kwargs['spelling'])
        self.caseInsensitive.set(kwargs['caseInsensitive'])
        self.useRegEx.set(kwargs['use_RexEx'])
    
    def on_check_kind(self):
        if self.kindState.get():
            self.kindCBox.config(state='normal')
        else:
            self.kindCBox.config(state='disable')
    
    def on_ok(self, event=None):
        self.result = True
        SearchDialog._old_data = self.get_data()
        self.destroy()
    
    def on_cancel(self, event=None):
        self.destroy()


# Output frame shows the AST on the left and the selected Cursor on the right
class OutputFrame(ttk.Frame):
    def __init__(self, master=None):
        ttk.Frame.__init__(self, master)
        self.grid(sticky='nswe')
        self.create_widgets()
        self.clear()
        self.curIID = ''
        self.history = []
        self.historyPos = -1
        self.searchResult = []
        self.searchPos = -1

    _max_history = 25
    
    def create_widgets(self):
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        
        toolbar = ttk.Frame(self)
        toolbar.grid(row=0, column=0, sticky='we')
        
        self.historyBackwardBtn = tk.Button(toolbar, text='<', relief='flat',
                                            command=self.go_history_backward)
        self.historyBackwardBtn.grid(row=0, column=0)
        self.historyForwardBtn = tk.Button(toolbar, text='>', relief='flat',
                                           command=self.go_history_forward)
        self.historyForwardBtn.grid(row=0, column=1)
        
        sep = ttk.Separator(toolbar, orient='vertical')
        sep.grid(row=0, column=2, sticky="ns", padx=5, pady=5)

        label = tk.Label(toolbar, text='Doubles:')
        label.grid(row=0, column=3)

        self.doublesBackwardBtn = tk.Button(toolbar, text='<', relief='flat',
                                            command=self.go_doubles_backward)
        self.doublesBackwardBtn.grid(row=0, column=4)
        self.doublesLabel = tk.Label(toolbar, text='-/-', width=5)
        self.doublesLabel.grid(row=0, column=5)
        self.doublesForwardBtn = tk.Button(toolbar, text='>', relief='flat',
                                           command=self.go_doubles_forward)
        self.doublesForwardBtn.grid(row=0, column=6)
        
        sep = ttk.Separator(toolbar, orient='vertical')
        sep.grid(row=0, column=7, sticky="ns", padx=5, pady=5)
        
        self.searchBtn = tk.Button(toolbar, text='Search', relief='flat',
                                   command=self.on_search)
        self.searchBtn.grid(row=0, column=8)
        self.searchBackwardBtn = tk.Button(toolbar, text='<', relief='flat',
                                           command=self.go_search_backward)
        self.searchBackwardBtn.grid(row=0, column=9)
        self.serachLabel = tk.Label(toolbar, text='-/-', width=5)
        self.serachLabel.grid(row=0, column=10)
        self.searchForwardBtn = tk.Button(toolbar, text='>', relief='flat',
                                          command=self.go_search_forward)
        self.searchForwardBtn.grid(row=0, column=11)

        
        # ttk version of PanedWindow do not support all options
        pw1 = tk.PanedWindow(self, orient='horizontal')
        pw1.grid(row=1, column=0, sticky='nswe')
        
        self.astOutputFrame = ASTOutputFrame(pw1, selectCmd=self.on_cursor_selection)
        pw1.add(self.astOutputFrame, stretch="always")
        
        pw2 = tk.PanedWindow(pw1, orient='vertical')
        
        self.cursorOutputFrame = CursorOutputFrame(pw2, 
                                                   selectCmd=self.astOutputFrame.set_current_cursor)
        pw2.add(self.cursorOutputFrame, stretch="always")
        
        self.fileOutputFrame = FileOutputFrame(pw2)
        pw2.add(self.fileOutputFrame, stretch="always")
        
        pw1.add(pw2, stretch="always")
    
    def on_cursor_selection(self):
        curIID = self.astOutputFrame.get_current_iid()
        curCursor = self.astOutputFrame.get_current_cursor()
        if curIID != self.curIID:
            self.set_active_cursor(curCursor)
            self.add_history(curIID)
            self.curIID = curIID
        self.update_doubles()
    
    def set_active_cursor(self, cursor):
        self.cursorOutputFrame.set_cursor(cursor)
        self.fileOutputFrame.set_location(cursor.extent, cursor.location)
    
    def clear_history(self):
        self.history = []
        self.historyPos = -1
        self.update_history_buttons()
    
    def add_history(self, iid):
        if self.historyPos < len(self.history):
            # we travel backward in time and change the history
            # so we change the time line and the future
            # therefore erase the old future
            self.history = self.history[:(self.historyPos+1)]
            # now the future is an empty sheet of paper
        
        if len(self.history) >= OutputFrame._max_history: # history to long?
            self.history = self.history[1:]
        else:
            self.historyPos = self.historyPos + 1
        
        self.history.append(iid)
        self.update_history_buttons()
    
    def go_history_backward(self):
        if self.historyPos > 0:
            self.historyPos = self.historyPos - 1
            self.update_history()
        self.update_history_buttons()
    
    def go_history_forward(self):
        if (self.historyPos+1) < len(self.history):
            self.historyPos = self.historyPos + 1
            self.update_history()
        self.update_history_buttons()
    
    def update_history(self):
        newIID = self.history[self.historyPos]
        self.curIID = newIID # set this before on_cursor_selection() is called
        self.astOutputFrame.set_current_iid(newIID) # this will cause call of on_cursor_selection()
        self.set_active_cursor(self.astOutputFrame.get_current_cursor())

    def update_history_buttons(self):
        hLen = len(self.history)
        hPos = self.historyPos
        
        if hPos > 0: # we can go backward
            self.historyBackwardBtn.config(state='normal')
        else:
            self.historyBackwardBtn.config(state='disabled')
        
        if (hLen > 1) and ((hPos+1) < hLen): # we can go forward
            self.historyForwardBtn.config(state='normal')
        else:
            self.historyForwardBtn.config(state='disabled')
    
    def clear_doubles(self):
        self.doublesForwardBtn.config(state='disabled')
        self.doublesLabel.config(state='disabled')
        self.doublesLabel.config(text='-/-')
        self.doublesBackwardBtn.config(state='disabled')
    
    def go_doubles_backward(self):
        iids = self.astOutputFrame.get_current_iids()
        if isinstance(iids, list):
            newIdx = (iids.index(self.curIID) - 1) % len(iids)
            newIID = iids[newIdx]
            self.astOutputFrame.set_current_iid(newIID)
    
    def go_doubles_forward(self):
        iids = self.astOutputFrame.get_current_iids()
        if isinstance(iids, list):
            newIdx = (iids.index(self.curIID) + 1) % len(iids)
            newIID = iids[newIdx]
            self.astOutputFrame.set_current_iid(newIID)

    def update_doubles(self):
        iids = self.astOutputFrame.get_current_iids()
        if isinstance(iids, list):
            self.doublesForwardBtn.config(state='normal')
            self.doublesLabel.config(state='normal')
            self.doublesLabel.config(text='{0}/{1}'.format(iids.index(self.curIID)+1, len(iids)))
            self.doublesBackwardBtn.config(state='normal')
        else:
            self.clear_doubles()
    
    def clear_search(self):
        self.searchResult = []
        self.update_search()
    
    def on_search(self):
        search = SearchDialog(self.winfo_toplevel())
        if search.result:
            data = search.get_data()
            self.searchResult = self.astOutputFrame.search(**data)
            self.searchPos = 0
            self.update_search()
            if len(self.searchResult) > 0:
                self.astOutputFrame.set_current_iid(self.searchResult[self.searchPos])
    
    def go_search_backward(self):
        self.searchPos = (self.searchPos - 1) % len(self.searchResult)
        self.astOutputFrame.set_current_iid(self.searchResult[self.searchPos])
        self.update_search()
    
    def go_search_forward(self):
        self.searchPos = (self.searchPos + 1) % len(self.searchResult)
        self.astOutputFrame.set_current_iid(self.searchResult[self.searchPos])
        self.update_search()
    
    def update_search(self):
        cnt = len(self.searchResult)
        if cnt > 0:
            self.searchForwardBtn.config(state='normal')
            self.serachLabel.config(state='normal')
            self.serachLabel.config(text='{0}/{1}'.format(self.searchPos+1, cnt))
            self.searchBackwardBtn.config(state='normal')
        else:
            self.searchForwardBtn.config(state='disabled')
            self.serachLabel.config(state='disabled')
            self.serachLabel.config(text='-/-')
            self.searchBackwardBtn.config(state='disabled')
    
    def clear(self):
        self.curIID = ''
        self.clear_history()
        self.clear_doubles()
        self.clear_search()
        self.searchBtn.config(state='disabled')
        self.astOutputFrame.clear()
        self.cursorOutputFrame.clear()
        self.fileOutputFrame.clear()
        
    def set_translationunit(self, tu):
        self.clear()
        self.astOutputFrame.set_translationunit(tu)
        self.searchBtn.config(state='normal')


# Main window combine all frames in tabs an contains glue logic between these frames
class Application(ttk.Frame):
    def __init__(self, master=None, file=None):
        ttk.Frame.__init__(self, master)
        self.grid(sticky='nswe')
        self.create_widgets()
        
        self.index = clang.cindex.Index.create()
        
        if file:
            self.inputFrame.load_filename(file)
        else:
            self.inputFrame.set_filename("select file to parse =>")
            self.inputFrame.set_args(["-xc++",
                                      "-std=c++14",
                                      "-I/your/include/path",
                                      "-I/more/include/path"])


    def create_widgets(self):
        top=self.winfo_toplevel()
        top.rowconfigure(0, weight=1)
        top.columnconfigure(0, weight=1)
        
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        
        self.notebook = ttk.Notebook(self)
        
        self.inputFrame = InputFrame(self.notebook, parseCmd=self.on_parse)
        
        self.errorFrame = ErrorFrame(self.notebook)
        self.outputFrame = OutputFrame(self.notebook)
        
        self.notebook.add(self.inputFrame, text='Input')
        self.notebook.add(self.errorFrame, text='Errors')
        self.notebook.add(self.outputFrame, text='Output')
        self.notebook.grid(row=0, column=0, sticky='nswe')
        
        quitButton = ttk.Button(self, text='Quit',
            command=self.quit)
        quitButton.grid(row=1, column=0, sticky='we')
    
    def on_parse(self):
        fileName = self.inputFrame.get_filename()
        args = self.inputFrame.get_args()
        tu = self.index.parse(fileName, args=args)
        
        cntErr = self.errorFrame.set_errors(tu.diagnostics)
        self.outputFrame.set_translationunit(tu)
        
        if cntErr > 0:
            self.notebook.select(self.errorFrame)
        else:
            self.notebook.select(self.outputFrame)


parser = argparse.ArgumentParser(description='Python Clang AST Viewer')
parser.add_argument('-l', '--libfile', help='select Clang library file', nargs=1, dest='libFile')
parser.add_argument('file', help='''Text file containing input data,
                    1st line = file to parse,
                    next lines = Clang arguments, one argument per line''',
                    nargs='?')
args = parser.parse_args()

if args.libFile:
    clang.cindex.Config.set_library_file(args.libFile[0])

app = Application(file=args.file)
app.master.title('PyClASVi')
app.mainloop()
