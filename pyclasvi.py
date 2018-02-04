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
#   Add a history like a web browser
#   Add search function

import sys

if sys.version_info.major == 2:
    import ttk
    import Tkinter as tk
    import tkFont
    import tkFileDialog
else: # python3
    import tkinter.ttk as ttk
    import tkinter as tk
    import tkinter.font as tkFont
    import tkinter.filedialog as tkFileDialog

import clang.cindex
import ctypes
import argparse


# Python3 clang binding sometimes return bytes instead of strings
# use this function to convert it
def toStr(data):
    if isinstance(data, bytes):
        return data.decode('ascii') # ASCII should be default in C/C++ but what about comments
    else:
        return str(data)


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
        self.argsText = tk.Text(self)
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
        
        charSize = tkFont.nametofont('TkHeadingFont').measure('#')
        
        self.astView = ttk.Treeview(self, 
                                    columns=('displayname'),
                                    selectmode='browse')
        self.astView.bind('<<TreeviewSelect>>', self.on_selection)
        
        make_scrollable(self, self.astView)
        
        self.astView.heading('#0', text='Kind')
        self.astView.column('#0', width=20*charSize, stretch=False)
        self.astView.heading('displayname', text='Displayname')
        self.astView.column('displayname', width=20*charSize, stretch=False)
        self.astView.grid(row=0, column=0, sticky='nswe')
    
    def on_selection(self, event):
        #curItem = self.astView.focus()
        if self.selectCmd:
            self.selectCmd()
    
    def set_select_cmd(self, cmd):
        self.selectCmd = cmd
    
    def get_current_cursor(self):
        curCursor = None
        curItem = self.astView.focus()
        if curItem:
            curCursor = self.mapIIDtoCursor[curItem]
        return curCursor
    
    def set_current_cursor(self, cursor):
        iid = self.mapCursorToIID[HashableObj(cursor)]
        self.astView.focus(iid)
        self.astView.selection_set(iid)
        self.astView.see(iid)
    
    def clear(self):
        for i in self.astView.get_children():
            self.astView.delete(i)
        self.translationunit = None
        self.mapIIDtoCursor = {}
        self.mapCursorToIID = {}
    
    def _insert_children(self, cursor, iid):
        for childCursor in cursor.get_children():
            newIID = self.astView.insert(iid,
                                        'end',
                                        text=childCursor.kind.name,
                                        values=[toStr(childCursor.displayname)])
            self.mapIIDtoCursor[newIID] = childCursor
            self.mapCursorToIID[HashableObj(childCursor)] = newIID
            self._insert_children(childCursor, newIID)
    
    def set_translationunit(self, tu):
        self.clear()
        self.translationunit = tu
        root = tu.cursor
        iid = self.astView.insert('',
                                  'end',
                                  text=root.kind.name,
                                  values=[toStr(root.displayname)])
        self.mapIIDtoCursor[iid] = root
        self.mapCursorToIID[HashableObj(root)] = iid
        self._insert_children(root, iid)


# Output nearly all members of the selected Cursor object
class CursorOutputFrame(ttk.Frame):
    def __init__(self, master=None, selectCmd=None):
        ttk.Frame.__init__(self, master)
        self.grid(sticky='nswe')
        self.create_widgets()
        self.cursor = None
        self.selectCmd = selectCmd
        self.cursorList = []
    
    # ignore member with this types
    _ignore_types = ('function',)
    
    # methodes with no parameter and simple return type
    _simple_methodes = ('is_definition', 
                        'is_const_method', 
                        'is_mutable_field', 
                        'is_pure_virtual_method', 
                        'is_static_method',
                        'is_virtual_method',
                        'get_usr',
                        'get_num_template_arguments',
                        'get_field_offsetof',
                        'is_anonymous',
                        'is_bitfield',
                        'get_bitfield_width')
    
    # methodes with no parameter and return a Cursor
    _cursor_methodes = ('get_definition')
    
    # methodes with no parameter and return an enumeration of Cursors
    _cursors_methodes = ('get_arguments',)

    def create_widgets(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        
        defFont = tkFont.Font(font="TkFixedFont")
        defFontProp = defFont.actual()
        self.cursorText = tk.Text(self)
        self.cursorText.grid(row=0, sticky='nswe')
        
        make_scrollable(self, self.cursorText)
        
        self.cursorText.tag_configure('attr_name', font=(defFontProp['family'], defFontProp['size'], 'bold'))
        self.cursorText.tag_configure('attr_type', foreground='green')
        self.cursorText.tag_configure('attr_err', foreground='red')
        self.cursorText.tag_configure('link', foreground='blue')
        self.cursorText.tag_bind('link', '<ButtonPress-1>', self.on_cursor_click)
        self.cursorText.tag_bind('link', '<Enter>', self.on_link_enter)
        self.cursorText.tag_bind('link', '<Leave>', self.on_link_leave)
        self.cursorText.config(state='disabled')

    def on_link_enter(self, event):
        self.cursorText.configure(cursor='hand1')

    def on_link_leave(self, event):
        self.cursorText.configure(cursor='arrow')

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
                                'Cursor ' + 
                                str(cursor.hash) + 
                                ' ' +
                                cursor.kind.name +
                                ' / ' + 
                                toStr(cursor.displayname),
                                'link')
            self.cursorList.append(cursor)
        else:
            self.cursorText.insert('end', str(cursor))
    
    def _add_attr(self, cursor, attr, attrName, attrType, attrOk):
        self.cursorText.insert('end', attrName, 'attr_name')
        self.cursorText.insert('end', ' (')
        if attrOk:
            self.cursorText.insert('end', attrType, 'attr_type')
        else:
            self.cursorText.insert('end', attrType, 'attr_err')
        self.cursorText.insert('end', '):\n')
        
        if attrType == 'Cursor':
            self._add_cursor(attr)
        elif attrName in CursorOutputFrame._simple_methodes:
            self.cursorText.insert('end', '= ' + str(attr()))
        elif attrName in CursorOutputFrame._cursor_methodes:
            self.cursorText.insert('end', '= ')
            self._add_cursor(attr())
        elif attrName in CursorOutputFrame._cursors_methodes:
            args = attr()
            isFirst = True
            self.cursorText.insert('end', '= [')
            for arg in args:
                if not isFirst:
                    self.cursorText.insert('end', '   ')
                isFirst = False
                self._add_cursor(arg)
                self.cursorText.insert('end', ',\n')
            if not isFirst:
                self.cursorText.delete('end - 3 chars', 'end')
            self.cursorText.insert('end', ']')
        elif attrName == 'get_template_argument_kind':
            nums = cursor.get_num_template_arguments()
            if nums > 0:
                for n in range(nums):
                    self.cursorText.insert('end', '(num='+str(n)+') = ')
                    self.cursorText.insert('end', str(cursor.get_template_argument_kind(n))+'\n')
        # TODO
        # get_template_argument_type
        # get_template_argument_value
        # get_template_argument_unsigned_value
        elif attrName == 'get_children':
            self.cursorText.insert('end', 'see tree on the left')
        # TODO
        # walk_preorder
        # get_tokens
        else:
            self.cursorText.insert('end', toStr(attr))
        
        self.cursorText.insert('end', '\n\n')

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
        if c:
            attrs = dir(c)
            for attrName in attrs:
                # ignore all starts with '_'
                if attrName[0] == '_':
                    continue
                attrType = None
                attrVal = None
                val = None
                attrOk = False
                try:
                    val = getattr(c, attrName)
                    attrType = val.__class__.__name__
                    if attrType in CursorOutputFrame._ignore_types:
                        continue
                    attrOk = True
                except BaseException as e:
                    attrType = e.__class__.__name__ + ' => do not use this'
                
                self._add_attr(c, val, attrName, attrType, attrOk)
                
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
        
        self.fileText = tk.Text(self)
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


# Output frame shows the AST on the left and the selected Cursor on the right
class OutputFrame(ttk.Frame):
    def __init__(self, master=None):
        ttk.Frame.__init__(self, master)
        self.grid(sticky='nswe')
        self.create_widgets()
        self.clear()

    def create_widgets(self):
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        
        toolbar = ttk.Frame(self)
        toolbar.grid(row=0, column=0, sticky='we')
        
        self.historyForwardBtn = tk.Button(toolbar, text='<', relief='flat', command=None)
        self.historyForwardBtn.grid(row=0, column=0)
        self.historyBackwardBtn = tk.Button(toolbar, text='>', relief='flat', command=None)
        self.historyBackwardBtn.grid(row=0, column=1)
        
        sep = ttk.Separator(toolbar, orient='vertical')
        sep.grid(row=0, column=2, sticky="ns", padx=5, pady=5)

        self.searchBtn = tk.Button(toolbar, text='Search', relief='flat', command=None)
        self.searchBtn.grid(row=0, column=3)
        self.searchForwardBtn = tk.Button(toolbar, text='<', relief='flat', command=None)
        self.searchForwardBtn.grid(row=0, column=4)
        self.serachLabel = tk.Label(toolbar, text='0/0')
        self.serachLabel.grid(row=0, column=5)
        self.searchBackwardBtn = tk.Button(toolbar, text='>', relief='flat', command=None)
        self.searchBackwardBtn.grid(row=0, column=6)

        
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
        cur = self.astOutputFrame.get_current_cursor()
        self.cursorOutputFrame.set_cursor(cur)
        self.fileOutputFrame.set_location(cur.extent, cur.location)
    
    def clear_history(self):
        self.historyForwardBtn.config(state='disabled')
        self.historyBackwardBtn.config(state='disabled')
    
    def clear_search(self):
        self.searchForwardBtn.config(state='disabled')
        self.searchBackwardBtn.config(state='disabled')
    
    def clear(self):
        self.clear_history()
        self.clear_search()
        self.searchBtn.config(state='disabled')
        self.serachLabel.config(state='disabled')
        self.astOutputFrame.clear()
        self.cursorOutputFrame.clear()
        self.fileOutputFrame.clear()
        
    def set_translationunit(self, tu):
        self.clear()
        self.astOutputFrame.set_translationunit(tu)


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
        
        note = ttk.Notebook(self)
        
        self.inputFrame = InputFrame(note, parseCmd=self.on_parse)
        
        self.errorFrame = ErrorFrame(note)
        self.outputFrame = OutputFrame(note)
        
        note.add(self.inputFrame, text='Input')
        note.add(self.errorFrame, text='Errors')
        note.add(self.outputFrame, text='Output')
        note.grid(row=0, column=0, sticky='nswe')
        
        quitButton = ttk.Button(self, text='Quit',
            command=self.quit)
        quitButton.grid(row=1, column=0, sticky='we')
    
    def on_parse(self):
        fileName = self.inputFrame.get_filename()
        args = self.inputFrame.get_args()
        tu = self.index.parse(fileName, args=args)
        
        self.errorFrame.set_errors(tu.diagnostics)
        self.outputFrame.set_translationunit(tu)


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
