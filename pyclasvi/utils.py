#=============================================#
# Python Clang AST Viewer - Helper functions
#
# Copyright (C) 2022 Frank Mueller
# SPDX-License-Identifier: MIT
#=============================================#

import sys
import clang.cindex
import inspect


# Convert objects to a string.
# Some object have no suitable standard string conversation, so use this.
def toStr(data):
    """Convert any object to a string for output.
    
    For most objects just str(obj) is called but some kinds of object
    have no suitable standard string conversation.
    This function will give all objects a human readable output string.
    """
    if isinstance(data, bytes):     # Python3 clang binding sometimes return bytes instead of strings
        return data.decode('ascii') # ASCII should be default in C/C++ but what about comments?
    elif ((data.__class__ == int)   # int but not bool, show decimal and hex
          or (sys.version_info.major) == 2 and isinstance(data, long)):
        if data < 0:                    # no negative hex values
            return str(data)
        else:
            return '{0} ({0:#010x})'.format(data)
    elif isinstance(data, clang.cindex.Cursor): # default output for cursors
        return '{0} ({1:#010x}) {2}'.format(data.kind.name,
                                             data.hash,
                                             data.displayname)
    elif isinstance(data, clang.cindex.SourceLocation):
        return 'file:   {0}\nline:   {1}\ncolumn: {2}\noffset: {3}'.format(
            data.file, data.line, data.column, data.offset)
    else:
        return str(data)


def join(*args):
    """Join strings without separator.
    """
    return ''.join(args)


def xjoin(*args):
    """Join objects to a string without separator.
    """
    return ''.join((str(a) for a in args))


def is_instance_method(m):
    """Check if Cursor is an instance method.
    """
    return inspect.ismethod(m)


def is_simple_instance_method(m):
    """Check if instance method has only self parameter.
    
    Parameters:
        m (Cursor): m should be a Cursor of an instance method.
    """
    argSpec = inspect.getargspec(m)
    return len(argSpec.args) == 1 # only self


def get_method_prototype(m):
    """Get method definition as as string.
    
    Returns:
        string: Method definition like "(arg1, arg2)"
    """
    argSpec = inspect.getargspec(m)
    return inspect.formatargspec(*argSpec)


def is_obj_in_stack(obj, objStack):
    """Check if an object is in a list.
    """
    for o in objStack:
        if o.__class__ == obj.__class__: # some compare function trow exception if types are not equal
            if o == obj:
                return True
    return False
