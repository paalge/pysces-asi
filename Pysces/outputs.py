"""
This module defines all the functions used to create outputs by Pysces. It provides a layer
of abstraction between the user and the inner workings of Pysces, allowing them to easily
define new outputs without having to worry about the complexities of object orientation.

To create a new output type you must add a function to this file and then include it in the 
TYPES dictionary at the bottom of this file. The new output type is then available to use in 
the settings file.

All functions should accept an allskyImage object, an outputType object and a settingsManager
object as their only three arguments.

All output functions should return an object which has a save(filename) or a savefig(filename) method, in which case
Pysces will take care of saving the output on the filesystem and copying it to the webserver.
These operations are based on the information given in the output declaration in the settings file.
If there is no output to be saved (for example if the output is a direct copy of the image), then
the output function may return None. An example of  a suitable return object is a PASKIL allskyImage
object.
"""

import os
import shutil
import datetime

from PASKIL import allskyKeo

##############################################################################################

def copy_image(image, output, settings_manager):
    source_path = image.getFilename()
    source_filename = os.path.basename(source_path)
    file_, extension = os.path.splitext(source_filename)
    
    day_folder = settings_manager.get(["output folder"])["output folder"]
    
    dest_path = os.path.normpath(day_folder + "/" +  output.folder_on_host + "/" + file_ + extension)
    
    #copy the image
    settings_manager.set({"output":"OutputTaskHandler> Copying "+source_path+" to "+dest_path})
    shutil.copyfile(source_path, dest_path)
    
    return None

##############################################################################################

def create_quicklook(image, output, settings_manager):   
    im = image.binaryMask(output.fov_angle)
    im = im.centerImage()
    im = im.alignNorth(north="geomagnetic", orientation='NWSE')
    ql = im.createQuicklook()
    return ql

##############################################################################################

def centered_image(image, output, settings_manager):
    im = image.binaryMask(output.fov_angle)
    im = im.centerImage()
    im = im.alignNorth(north="geomagnetic", orientation='NWSE')
    return im 

##############################################################################################

def realtime_keogram(image, output, settings_manager):
    
    #see if a realtime keogram has been created yet
    try:
        filename = settings_manager.get(['user_rt_keo_name'])['user_rt_keo_name']
    except KeyError:
        filename = None
    image = image.resize((500, 500))
    image = image.binaryMask(output.fov_angle)
    
    if filename == None:
        
        #work out the start and end times for the keogram based on the setting in the settings file
        end_time = datetime.datetime.utcnow()
        time_span = datetime.timedelta(hours = output.time_range)
        start_time = end_time - time_span
             
        keo = allskyKeo.new([image], output.angle, start_time, end_time, strip_width=output.strip_width, data_spacing=output.data_spacing)      
        keo.save(os.path.expanduser('~')+"/realtime_keogram")
        
        settings_manager.create('user_rt_keo_name', os.path.expanduser('~')+"/realtime_keogram", persistant=True)
        
    else:
        keo = allskyKeo.load(filename)
        keo = keo.roll([image])
        keo.save(filename)

    return allskyKeo.plotKeograms([keo], size=(9, 3.7))

##############################################################################################    
 
#dict to map output types to output functions.
TYPES = {"raw":copy_image, 
         "quicklook":create_quicklook, 
         "paskil_png":centered_image, 
         "realtimeKeo":realtime_keogram}