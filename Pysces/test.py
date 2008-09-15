"""
The test module runs all the doctests on Pysces. It is a good idea to run this after a new installation
or after any changes to the code. The modules_to_doctest variable must be updated manually.
"""

import unittest
import doctest

#list of all modules in the Pysces package to be tested 
modules_to_doctest = ["settingsManager","captureManager"]


for mod in modules_to_doctest:
    print "Running doctests for "+mod
    result = doctest.testmod(__import__(mod))
    print mod+" failed ",result[0]," out of ",result[1]," tests."

print "Done"



