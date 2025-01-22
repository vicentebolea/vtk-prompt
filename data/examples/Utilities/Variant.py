#!/usr/bin/env python3

import sys

# These are templated functions in C++.
from vtkmodules.all import (
    vtkVariantCast,
    vtkVariantCreate,
    vtkVariantExtract,
    vtkVariantEqual,
    vtkVariantLessThan,
    vtkVariantStrictEquality,
    vtkVariantStrictWeakOrder
)
from vtkmodules.util.vtkVariant import vtkVariantStrictWeakOrderKey
from vtkmodules.vtkCommonCore import (
    VTK_UNSIGNED_SHORT,
    vtkStringArray,
    vtkVariant,
    vtkVariantArray,
)

# Unicode string for demonstration (etre with circumflex i.e. être)
if sys.hexversion >= 0x03000000:
    unicodeEtre = '\xeatre'  # unicode in Python 3
else:
    unicodeEtre = unicode('\xeatre', 'latin1')  # noqa: F821

#
# Basic vtkVariant usage
#

# Default constructor
v = vtkVariant()
print(f"Invalid variant: {repr(v)}, '{v.GetTypeAsString()}'")

# Copy constructor
v = vtkVariant(vtkVariant("variant"))
print(f"Copied variant: {repr(v)}, '{v.GetTypeAsString()}'")

# Conversion constructors
v = vtkVariant(1)
print(f"Integer variant: {repr(v)}, '{v.GetTypeAsString()}'")
v = vtkVariant(1.0)
print(f"Float variant: {repr(v)}, '{v.GetTypeAsString()}'")
v = vtkVariant("hello")
print(f"String variant: {repr(v)}, '{v.GetTypeAsString()}'")
v = vtkVariant(unicodeEtre)
print(f"Unicode variant: {repr(v)}, '{v.GetTypeAsString()}'")
v = vtkVariant(vtkStringArray())
print(f"Object variant: {repr(v)}, '{v.GetTypeAsString()}'")

# Explicit type constructor
v1 = vtkVariant(1, VTK_UNSIGNED_SHORT)
v2 = vtkVariant(2, v1.GetType())
print(f"UShort variant: {repr(v1)}, '{v1.GetTypeAsString()}'")

# Type checking
if v2.IsUnsignedShort():
    print("v2 is UnsignedShort")
else:
    print("v2 is not UnsignedShort, it is", v2.GetTypeAsString())

# Explicit value extraction
s = v2.ToString()
print("String value: %s, %s" % (s, type(s)))
i = v2.ToInt()
print("Int value: %i, %s" % (i, type(i)))

# Automatic argument conversion
a = vtkVariantArray()
a.InsertNextValue(vtkVariant())
a.InsertNextValue(1)
a.InsertNextValue(2.0)
a.InsertNextValue("hello")
a.InsertNextValue(unicodeEtre)
a.InsertNextValue(vtkVariantArray())
print("Variant array:")
for i in range(a.GetNumberOfValues()):
    v = a.GetValue(i)
    print(f"{i}: {repr(v)}, '{v.GetTypeAsString()}'")

# Comparison
if v2 == vtkVariant(2):
    print("v2 is equal to 2")
if v2 > vtkVariant(1):
    print("v2 is greater than 1")
if v2 < vtkVariant(3):
    print("v2 is less than 3")
if v2 == vtkVariant("2"):
    print("v2 is equal to '2'")

# Use as a dict key (hashed as a string)
d = {vtkVariant(1): 0, vtkVariant('1'): 1, vtkVariant(): 3}
print("Index is %i" % d[vtkVariant(1.0)])

#
# Extra functionality from vtk.util.vtkVariant
#
# These are templated functions in C++, but in Python
# they take the template arg as a string instead,
# e.g. vtkVariantCreate<unsigned int>(1) becomes
#      vtkVariantCreate(1, 'unsigned int')

# Creation
v = vtkVariantCreate(1, 'unsigned int')

# Value extraction
v = vtkVariant(6.0)
f = vtkVariantExtract(v)

# Value extraction with type specified
f = vtkVariantExtract(v, 'double')

# Casting a variant
v = vtkVariant("10")
i = vtkVariantCast(v, 'int')
print(f"Valid cast result: {repr(i)}")

# A failed cast returns None
v = vtkVariant("hello")
i = vtkVariantCast(v, 'int')
print(f"Invalid cast result: {repr(i)}")

#
# Comparisons and sorting: See VTK docs for more info
#

# Special function vtk.vtkVariantStrictWeakOrder:
# Compare variants by type first, and then by value.  For Python 2, the
# return values are -1, 0, 1 like the Python 2 "cmp()" method.  This is
# in contrast with the Python 3 and C++ versions of this function, which
# check if (v1 < v2) and return True or False.
v1 = vtkVariant(10)
v2 = vtkVariant("10")
r = vtkVariantStrictWeakOrder(v1, v2)
print("Strict weak order (10, '10') ->", r)

# Sorting by strict weak order, using a key function:
unsorted = [1, 2.5, vtkVariant(), "0", unicodeEtre]
l = [vtkVariant(x) for x in unsorted]
l.sort(key=vtkVariantStrictWeakOrderKey)
print("Sort by weak order ->", l)

# Check two variants for strict equality of type and value.
b = vtkVariantStrictEquality(v1, v2)
print(f"Strict equality (10, '10') -> {b}")

# Two special-purpose methods.
# First is identical to (v1 < v2)
b = vtkVariantLessThan(v1, v2)
# Second is identical to (v1 == v2)
b = vtkVariantEqual(v1, v2)
