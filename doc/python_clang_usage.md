# How to use Python Clang

A simple script to parse a file an output the root cursors kind and name (spelling).
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

index = clang.cindex.Index.create()
filename = 'test_all.cpp'
args=()

tu = clang.cindex.TranslationUnit.from_source(filename, args=args)

root = tu.cursor

print(root.kind, root.spelling)
```
