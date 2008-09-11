"""
The test module runs all the doctests on Pysces. It is a good idea to run this after a new installation
or after any changes to the code. The modules_to_doctest variable must be updated manually.
"""

import unittest
import doctest

#list of all modules in the Pysces package to be tested 
modules_to_doctest = ["settingsManager"]

suite = unittest.TestSuite()
for mod in modules_to_doctest:
    suite.addTest(doctest.DocTestSuite(__import__(mod)))
runner = unittest.TextTestRunner()
runner.run(suite)


