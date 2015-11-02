"""
Setup script for pysces-asi camera control software.
Created by Nial Peters on 19th Sep. 2009

The script installs the pysces-asi package into the relevent site-packages
folder and installs an executable script probably into /usr/bin.

It also installs the settings file into $HOME/.pysces_asi/settings.txt this
should be edited before pysces_asi is run.
"""
from distutils.core import setup
import sys
import os.path
import glob

# Check that all the prerequisite packages are installed
try:
    import multiprocessing
except ImportError:
    raise ImportError(
        "Could not import multiprocessing module. Please ensure that it is correctly installed. If you are using python >= V2.6 then it should have come as part of the distribution, otherwise see http://code.google.com/p/python-multiprocessing/")

try:
    import ephem
except ImportError:
    raise ImportError(
        "Could not import pyephem module. Please ensure it is installed correctly. See http://rhodesmill.org/pyephem/")

try:
    import wx
except ImportError:
    raise ImportError(
        "Could not import wxPython. Please ensure it is installed correctly. See www.wxpython.org/")

try:
    from PASKIL import *
except ImportError:
    raise ImportError(
        "Could not import PASKIL. Please ensure it is installed correctly. See http://code.google.com/p/paskil/")

# Find out where the home folder is
home_folder = os.path.expandvars("$HOME")
pysces_rw_folder = os.path.normpath(home_folder + '/.pysces_asi')

# get list of camera plugins
camera_files = [
    "misc/cameras/" + os.path.basename(i) for i in glob.glob("misc/cameras/*.py")]

# get a list of output function files
output_function_files = [
    "misc/outputs/" + os.path.basename(i) for i in glob.glob("misc/outputs/*.py")]
output_function_files.append("README")  # add the readme file to it as well

setup(name='pysces_asi',
      version='2.0',
      description='All-sky camera control script',
      author='Nial Peters',
      author_email='nonbiostudent@hotmail.com',
      url='http://code.google.com/p/pysces-asi/',
      package_dir={'': 'src'},
      packages=['pysces_asi'],
      scripts=['misc/pysces_asi', 'pysces_asi3'],
      data_files=[(pysces_rw_folder, ['misc/template_settings.txt']),
                  (pysces_rw_folder + "/tasks.daily",
                   ["misc/tasks.daily/README"]),
                  (pysces_rw_folder + "/tasks.startup",
                   ["misc/tasks.startup/README"]),
                  (pysces_rw_folder + "/tasks.per_image",
                   ["misc/tasks.per_image/README"]),
                  (pysces_rw_folder + "/cameras", camera_files),
                  (pysces_rw_folder + "/outputs", output_function_files)]

      )

# since we install as root then the rw_folder is created with root as the owner
# and then pysces can't access it! So here we change the owner to the
# login name
if sys.argv.count('install') != 0:
    you = os.getlogin()
    print("Changing ownership of " + pysces_rw_folder + " to " + you)
    return_code = os.system(
        "chown -R " + you + ":" + you + " " + pysces_rw_folder)

    if return_code != 0:
        print("Error! Failed to change ownership of \"~/.pysces_asi\"")

    # we also need to double check that the README files don't get executable bits set - otherwise
    # the CronManager will get confused!
    print("Checking that README files have not been made executable")
    for f in [os.path.normpath(pysces_rw_folder + "/tasks.daily/README"),
              os.path.normpath(pysces_rw_folder + "/tasks.startup/README"),
              os.path.normpath(pysces_rw_folder + "/tasks.per_image/README"),
              os.path.normpath(pysces_rw_folder + "/outputs/README")]:
        return_code = os.system("chmod -x " + f)
        if return_code != 0:
            print(
                "Error! Failed to change execute permissions on \'" + f + "\'")
