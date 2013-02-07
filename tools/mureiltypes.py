#
#
# Copyright (C) University of Melbourne 2012
#
#
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#SOFTWARE.
#
#

from tools import mureilexception
import numpy

"""Module providing helper functions for type-checking of arrays.
"""

def check_ndarray_float(array):
    """Return only if the array is of type numpy.ndarray, with a float dtype.
    If not, raise a mureilexception.ArrayDataTypeException
    """
    
    if type(array) is not numpy.ndarray:
        msg = ('Expected array to be numpy array, but found ' + array.dtype.name + 
            ' in ' + mureilexception.find_caller(1))
        raise mureilexception.ArrayDataTypeException(msg, __file__, {})
    
    if not(array.dtype.name.startswith('float')):
        msg = ('Expected array to be float dtype, but found ' + array.dtype.name + 
            ' in ' + mureilexception.find_caller(1))
        raise mureilexception.ArrayDataTypeException(msg, __file__, {})


def check_ndarray_int(array):
    """Return only if the array is of type numpy.ndarray, with int dtype.
    If not, raise a mureilexception.ArrayDataTypeException
    """
    
    if type(array) is not numpy.ndarray:
        msg = ('Expected array to be numpy array, but found ' + array.dtype.name + 
            ' in ' + mureilexception.find_caller(1))
        raise mureilexception.ArrayDataTypeException(msg, __file__, {})
    
    if not(array.dtype.name.startswith('int')):
        msg = ('Expected array to be int dtype, but found ' + array.dtype.name + 
            ' in ' + mureilexception.find_caller(1))
        raise mureilexception.ArrayDataTypeException(msg, __file__, {})

