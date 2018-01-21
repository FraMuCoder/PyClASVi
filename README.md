# PyClASVi - Python Clang AST Viewer

**Python Clang AST Viewer is a simple GUI program helping you to understand the Clang Abstract Syntax Tree**

The goal is to make this program runable on all systems supported by Clang and Python
independent of Clang and Python version or support at least as many different versions a possible.
Currently PyClASVi is developed and tested under Ubuntu 14.04 with Python 2.7 and Clang 3.8.
It will not yet run with Python 3 and not all Clang versions.

## Getting Started

First you need to install Clang and Clang Indexing Library Bindings for Python.
The last line is necessary for the Python module to find the library.

    apt-get install clang-3.8 python-pip
    pip install clang==3.8
    ln -s /usr/lib/x86_64-linux-gnu/libclang-3.8.so.1 /usr/lib/libclang.so

Instead of using PIP you can install Ubuntu's package of Python Clang binding.

    apt-get install python-clang-3.8

To run PyClASVi just call `pyclasvi.py`.

You will see a tabbed window. The first tab is the Input frame.
Select an file to parse and add some arguments for the Clang parser.
There must be only one argument per line.
It looks like you need also the standard includes like `-I/usr/include` and `-I/usr/include/clang/3.8/include`.

Press [Parse] to start the parser.

If all works fine there is no warning or error on the Error tab and the Output tab shows the AST on the left.
Select one entry (Clang calls it Cursor) to find more information on the right.

## License

PyClASVi is distributed under the [MIT License](LICENSE).
