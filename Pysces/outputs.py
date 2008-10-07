"""
This module defines all the functions used to create outputs by Pysces. It is provides a layer
of abstraction between the developer and the inner workings of Pysces, allowing them to easily
define new outputs without having to worry about the complexities of object orientation.

To create a new output type you must add a function to this file and then include it in the 
TYPES dictionary at the bottom of this file. The new output type is then available to use in 
the settings file.

All functions should accept an allskyImage object, an outputType object and a settingsManager
object as their only three arguments.

All output functions should return an object which has a save(filename) method, in which case
Pysces will take care of saving the output on the filesystem and copying it to the webserver.
These operations are based on the information given in the output declaration in the settings file.
If there is no output to be saved (for example if the output is a direct copy of the image), then
the output function may return None. An example of  a suitable return object is a PASKIL allskyImage
object.
"""

import os
import shutil

##############################################################################################

def copyImage(image,output,settings_manager):
    source_path = image.getFilename()
    source_filename = os.path.basename(source_path)
    file_,extension = os.path.splitext(source_filename)
    
    day_folder = settings_manager.get(["output folder"])["output folder"]
    
    dest_path = os.path.normpath(day_folder + "/" +  output.folder_on_host + "/" + file_ + extension)
    
    #copy the image
    settings_manager.set({"output":"outputTaskHandler> Copying "+source_path+" to "+dest_path})
    shutil.copyfile(source_path,dest_path)
    
    return None

##############################################################################################

def createQuicklook(image,output,settings_manager):   
    im = image.binaryMask(75)
    im = im.centerImage()
    im = im.alignNorth(north="geomagnetic")
    ql = im.createQuicklook()
    return ql

##############################################################################################

def centeredImage(image,output,settings_manager):
    im = image.binaryMask(75)
    im = im.centerImage()
    im = im.alignNorth(north="geomagnetic")
    return im 


#dict to map output types to output functions.
TYPES = {"raw":copyImage,"quicklook":createQuicklook,"paskil_png":centeredImage}