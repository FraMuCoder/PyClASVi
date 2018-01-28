#!/usr/bin/env python2

# Python ClASVi
# Python Clang AST Viewer
# PyClASVi is distributed under the MIT License, see LICENSE

# TODO
#
# General
#   Test unter Windows
#   Test/fix Clang versions > 3.8
#   Test/fix Python 3
#   Better code documentation
#   Check coding style
#   Add documentation "How to access Clang AST"
# Input frame
#   Add input for Config.set_library_file
#   Add buttons for input language and language version
# Error frame
#   Filter for severity level
#   Colored output depends on severity
#   Add source panel to show location
# Output frame
#   Add source panel to show location
#   Add missing member outputs (see comments in class CursorOutputFrame)
#   Output Tokens
#   Output all other used class types
#   Add a history like a web browser

import sys
import ttk
import Tkinter as tk
import tkFont
import tkFileDialog
import clang.cindex
import ctypes


# Cursor objects have a hash property but no __hash__ methode
# You can use this class to make Cursor object hashable
class HashableObj:
    def __init__(self, obj):
        self.obj = obj
    
    def __eq__(self, other):
        return self.obj == other.obj
    
    def __hash__(self):
        return self.obj.hash


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
        fileFrame.grid(row=1, column=0, sticky='we')
        self.filenameEntry = ttk.Entry(fileFrame, textvariable=self.filename)
        self.filenameEntry.grid(row=0, column=0, sticky='we')
        self.selectFileButton = ttk.Button(fileFrame, text='...', command=self.on_select_file)
        self.selectFileButton.grid(row=0, column=1)
        
        ttk.Label(self, text='Arguments:').grid(row=2, sticky='w')
        buttonFrame = ttk.Frame(self)
        buttonFrame.grid(row=3, column=0, sticky='we')
        self.includeButton = ttk.Button(buttonFrame, text='+ Include', command=self.on_include)
        self.includeButton.grid()#(row=0, column=0)
        self.defineButton = ttk.Button(buttonFrame, text='+ Define', command=self.on_define)
        self.defineButton.grid(row=0, column=1)
        self.argsText = tk.Text(self)
        self.argsText.grid(row=4, sticky='nswe')

        buttonFrame = ttk.Frame(self)
        buttonFrame.grid(row=5, column=0, sticky='we')
        buttonFrame.columnconfigure(2, weight=1)

        self.parseButton = ttk.Button(buttonFrame, text='Load', command=self.on_file_load)
        self.parseButton.grid(row=0, column=0)
        
        self.parseButton = ttk.Button(buttonFrame, text='Save', command=self.on_file_save)
        self.parseButton.grid(row=0, column=1)
        
        self.parseButton = ttk.Button(buttonFrame, text='Parse', command=self.parseCmd)
        self.parseButton.grid(row=0, column=2, sticky='we')
    
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

    def create_widgets(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        
        charSize = tkFont.nametofont('TkHeadingFont').measure('#')
        
        self.errorTable = ttk.Treeview(self, columns=('category', 'severity', 'spelling', 'location'))
        
        vsb = ttk.Scrollbar(self, orient="vertical",command=self.errorTable.yview)
        self.errorTable.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky='ns')
        
        hsb = ttk.Scrollbar(self, orient="horizontal",command=self.errorTable.xview)
        self.errorTable.configure(xscrollcommand=hsb.set)
        hsb.grid(row=1, column=0, sticky='we')
        
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
        self.errorTable.grid(row=0, column=0, sticky='nswe')

    def clear_errors(self):
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
            self.errorTable.insert('', 'end', text=str(cnt), values=[
                str(err.category_number) + ' ' + err.category_name,
                serverity,
                err.spelling,
                location
                ])


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
        
        vsb = ttk.Scrollbar(self, orient="vertical",command=self.astView.yview)
        self.astView.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky='ns')
        
        hsb = ttk.Scrollbar(self, orient="horizontal",command=self.astView.xview)
        self.astView.configure(xscrollcommand=hsb.set)
        hsb.grid(row=1, column=0, sticky='we')
        
        self.astView.heading('#0', text='Kind')
        self.astView.column('#0', width=20*charSize, stretch=False)
        self.astView.heading('displayname', text='Displayname')
        self.astView.column('displayname', width=20*charSize, stretch=False)
        self.astView.grid(row=0, column=0, sticky='nswe')
    
    def on_selection(self, event):
        curItem = self.astView.focus()
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
                                        values=[childCursor.displayname])
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
                                  values=[root.displayname])
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
        
        vsb = ttk.Scrollbar(self, orient="vertical",command=self.cursorText.yview)
        self.cursorText.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky='ns')
        
        hsb = ttk.Scrollbar(self, orient="horizontal",command=self.cursorText.xview)
        self.cursorText.configure(xscrollcommand=hsb.set)
        hsb.grid(row=1, column=0, sticky='we')
        
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
        try:
            self.cursorText.insert('end', 
                                'Cursor ' + 
                                str(cursor.hash) + 
                                ' ' +
                                cursor.kind.name + 
                                ' / ' + 
                                cursor.displayname, 
                                'link')
            self.cursorList.append(cursor)
        except:
            if cursor == None:
                self.cursorText.insert('end', 'None')
            else:
                self.cursorText.insert('end', '?')
    
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
            self.cursorText.insert('end', str(attr))
        
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


# Output frame shows the AST on the left and the selected Cursor on the right
class OutputFrame(ttk.Frame):
    def __init__(self, master=None):
        ttk.Frame.__init__(self, master)
        self.grid(sticky='nswe')
        self.create_widgets()

    def create_widgets(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        
        # ttk version of PanedWindow do not support all options
        pw1 = tk.PanedWindow(self, orient='horizontal',
                             showhandle=1, handlepad=1, handlesize=8, 
                             sashwidth=2, opaqueresize=1, sashrelief='sunken')
        pw1.grid(row=0, column=0, sticky='nswe')
        
        self.astOutputFrame = ASTOutputFrame(pw1, selectCmd=self.on_cursor_selection)
        pw1.add(self.astOutputFrame)
        
        self.cursorOutputFrame = CursorOutputFrame(pw1, 
                                                   selectCmd=self.astOutputFrame.set_current_cursor)
        pw1.add(self.cursorOutputFrame)
    
    def on_cursor_selection(self):
        cur = self.astOutputFrame.get_current_cursor()
        self.cursorOutputFrame.set_cursor(cur)
    
    def clear(self):
        self.astOutputFrame.clear();
        self.cursorOutputFrame.clear();
        
    def set_translationunit(self, tu):
        self.clear()
        self.astOutputFrame.set_translationunit(tu)


# Main window combine all frames in tabs an contains glue logic between these frames
class Application(ttk.Frame):
    def __init__(self, master=None, args=[]):
        ttk.Frame.__init__(self, master)
        self.grid(sticky='nswe')
        self.create_widgets()
        
        self.index = clang.cindex.Index.create()
        
        if len(args) > 0:
            self.inputFrame.load_filename(args[0])
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
        
        self.note = ttk.Notebook(self)
        
        self.inputFrame = InputFrame(self.note, parseCmd=self.on_parse)
        
        self.errorFrame = ErrorFrame(self.note)
        self.outputFrame = OutputFrame(self.note)
        
        self.note.add(self.inputFrame, text='Input')
        self.note.add(self.errorFrame, text='Errors')
        self.note.add(self.outputFrame, text='Output')
        self.note.grid(row=0, column=0, sticky='nswe')
        
        self.quitButton = ttk.Button(self, text='Quit',
            command=self.quit)
        self.quitButton.grid(row=1, column=0, sticky='we')
    
    def on_parse(self):
        fileName = self.inputFrame.get_filename()
        args = self.inputFrame.get_args()
        tu = self.index.parse(fileName, args=args)
        
        self.errorFrame.set_errors(tu.diagnostics)
        self.outputFrame.set_translationunit(tu)


app = Application(args=sys.argv[1:])
app.master.title('PyClASVi')
app.mainloop()
