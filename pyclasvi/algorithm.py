# ============================================= #
# Python Clang AST Viewer - Algorithm
#
# Copyright (C) 2022 Frank Mueller
# SPDX-License-Identifier: MIT
# ============================================= #


def traverse_cursor(cursor, 
                    callback_pre=None, callback_post=None, 
                    parent=None, 
                    parent_arg=None, forward_arg=None,
                    deep=0, child_index=-1):
    """Traverse Clang AST starting at a Cursor.
    
    You can use this function to traverse AST in preorder, post order
    or both at same time.
    
    Arguments:
        cursor          Clang Cursor to start traversal.
        callback_pre    Callback function to call in preorder.
                        This can evaluate the following **kwargs:
                            cursor          The current Cursor.
                            parent          The parent Cursor.
                            parent_arg      Value returned form
                                            callback_pre while
                                            traversing the parent.
                            forward_arg     See forward_arg as argument
                                            of traverse_cursor().
                            deep            Current deep, for root/start
                                            Cursor this is 0.
                            child_index     Nummer of child from parent
                                            (starting at 0) or -1 for
                                            root/start Cursor.
                        Returns:
                            Any value which should be forwarded as
                            parent_arg to all direct children.
        callback_post   Callback function to call in post order.
                        This can evaluate the following **kwargs:
                            cursor          The current Cursor.
                            parent          The parent Cursor.
                            parent_arg      Value returned form
                                            callback_pre while
                                            traversing the parent.
                            forward_arg     See forward_arg as argument
                                            of traverse_cursor().
                            deep            Current deep, for root/start
                                            Cursor this is 0.
                            child_index     Nummer of child from parent
                                            (starting at 0) or -1 for
                                            root/start Cursor.
                            child_cnt       Count of children.
        forward_arg     Arguments to be forwarded to callback functions.
                        It is a goog idea to use an array or dictionary,
                        so you can change the value inside a callback
                        function and use it in next call of a callback.
                        
    """
    if callback_pre:
        new_parent_arg = callback_pre(cursor=cursor,
                                      parent=parent,
                                      parent_arg=parent_arg,
                                      forward_arg=forward_arg,
                                      deep=deep, child_index=child_index)
    else:
        new_parent_arg = parent_arg
    
    child_cnt = 0
    for child in cursor.get_children():
        traverse_cursor(child,
                        callback_pre=callback_pre, callback_post=callback_post,
                        parent=cursor,
                        parent_arg=new_parent_arg, forward_arg=forward_arg,
                        deep=deep+1, child_index=child_cnt)
        child_cnt += 1

    if callback_post:
        callback_post(cursor=cursor,
                      parent=parent,
                      parent_arg=parent_arg, forward_arg=forward_arg,
                      deep=deep, child_index=child_index, child_cnt=child_cnt)
