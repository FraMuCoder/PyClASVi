// warnings

#warning "Warning message 1"
#warning "Warning message 2"
#warning "Warning message 3"

// errors

#error "Error message 1"
#error "Error message 2"
#error "Error message 3"

#pragma GCC warning "More warning"
#pragma GCC error   "More errors"

#if abc

#endif abc

noReturn()
{
    a = b;
}

void func()
{
    func2();
}

// fatal

#include "file_not_found.h"