# How to use Python Clang

# Basics

A simple script to parse a file and output the root cursors kind and name (spelling).

```python
import clang.cindex

# use this if libclang could not be found
#libfile = '/usr/lib/llvm-3.8/lib/libclang.so.1'
#clang.cindex.Config.set_library_file(libfile)

index = clang.cindex.Index.create()
filename = 'test_all.cpp'
args=()
tu = index.parse(filename, args=args)

root = tu.cursor

print(root.kind, root.spelling)
```

Nearly the same.

```python
import clang.cindex

# use this if libclang could not be found
#libfile = '/usr/lib/llvm-3.8/lib/libclang.so.1'
#clang.cindex.Config.set_library_file(libfile)

filename = 'test_all.cpp'
args=()

tu = clang.cindex.TranslationUnit.from_source(filename, args=args)

root = tu.cursor

print(root.kind, root.spelling)
```

# Browse AST

We have a tree so we want to see the child nodes.

```python
for cursor in root.get_children():
    print(cursor.kind, cursor.spelling)
```

Remark clang will never return a list but something you can iterate.

```python
children = root.get_children()
#print(children[0].spelling) # do not work
children = list(children)
print(children[0].spelling) # work
```

Print the whole AST.

```python
def print_ast(cursor, deep=0):
    print(' '.join((deep*'    ', str(cursor.kind), str(cursor.spelling))))
    for child in cursor.get_children():
        print_ast(child, deep+1)

print_ast(root)
```