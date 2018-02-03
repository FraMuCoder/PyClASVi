# PyClASVi - Python Clang AST Viewer

**Python Clang AST Viewer is a simple GUI program helping you to understand the Clang Abstract Syntax Tree**

The goal is to make this program runable on all systems supported by Clang and Python
independent of Clang and Python version or support at least as many different versions a possible.
Currently PyClASVi is developed and tested under Ubuntu 14.04 with Python 2.7, Python 3.4 and Clang 3.8.
It may not yet work with all Clang versions.

## Getting Started

First you need to install Clang, Clang Indexing Library Bindings for Python and tk for Python.
For Python 2 you can run this:

    sudo apt-get install clang-3.8 python-clang-3.8 python-tk

For Python 3 you can run this:

    sudo apt-get install clang-3.8 python3-pip python3-tk
    sudo pip3 install libclang-py3==3.8

Clang Python binding is looking for `libclang.so` or `libclang-<version>.so`
but there is no such file installed by Ubuntu 14.04.
You can create symbolic links to solve this problem.
    
    sudo ln -s x86_64-linux-gnu/libclang-3.8.so.1 /usr/lib/libclang-3.8.so
    sudo ln -s libclang-3.8.so /usr/lib/libclang.so

To run PyClASVi just call `pyclasvi.py`.

You will see a tabbed window. The first tab is the Input frame.
Select a file to parse and add some arguments for the Clang parser.
There must be only one argument per line.
It looks like you need also the standard includes like `-I/usr/include` and `-I/usr/include/clang/3.8/include`.

Press [Parse] to start the parser.

If all works fine there is no warning or error on the Error tab and the Output tab shows the AST on the left.
Select one entry (Clang calls it Cursor) to find more information on the right.

## License

PyClASVi is distributed under the [MIT License](LICENSE).
