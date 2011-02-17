from __future__ import with_statement

import time
import random
#import cPickle
from pysces_asi import PASKIL_jpg_plugin #import the plugin needed to open the image files in PASKIL

from pysces_asi.camera import CameraManagerBase, GphotoError

class D80Simulator(CameraManagerBase):
    def __init__(self,settings_manager):
        self.settings_manager =  settings_manager
    def set_capture_mode(self,capture_mode):
        #print "Camera is being set to "+capture_mode.name
        #set camera configs based on capture mode settings
        #for name,value in capture_mode.camera_settings.items():
        #    if self.camera_configs[name].current != value:
        #        self.camera_configs[name].current = value
        i = random.randint(0,20)
        #if i==20:
        #    raise GphotoError, "Failed to set capture mode"
        time.sleep(0.5)
        return
   
    ##############################################################################################
   
    def capture_images(self):
        print "capturing images"
#        self.settings_manager.set({'output':"CameraManager> Capturing Image"})
        time.sleep(2)
        raise GphotoError, "Failed to capture image"
        #i = random.randint(0,20)
        #if i==20:
        #    raise GphotoError, "Failed to capture image"
        #if self.camera_configs["imgquality"].current == "JPEG Normal":
        #return {"jpeg":("/home/nialp/tmp/testimage.JPG","/home/nialp/tmp/testimage_JPG.info")}
        #elif self.camera_configs["imgquality"].current == "NEF (Raw)":
        #    return {"NEF":("test_image.NEF","test_image_NEF.info")}
        #elif self.camera_configs["imgquality"].current == "NEF+Normal":
        #    return {"NEF":("test_image.NEF","test_image_NEF.info"),"jpeg":("test_image.JPG","test_image_JPG.info")}
     
    ##############################################################################################
     
    def _getCameraConfigs(self):
        #with open("test_camera_configs","rb") as fp:
        #    configs = cPickle.load(fp)
       
        return None    
     
    ##############################################################################################

    def _is_connected(self):
        time.sleep(1)
        return True
     
    ##############################################################################################
    def _download_configs(self):
        #time.sleep(10)
        #with open("Pysces/test_camera_configs","rb") as fp:
        #    configs = cPickle.load(fp)
       
        return None
     
     

