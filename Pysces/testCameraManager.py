from __future__ import with_statement

import time
import cPickle

from cameraManager import cameraManagerBase

class D80Simulator(cameraManagerBase):
       
    def _setCaptureMode(self,capture_mode):
        print "Camera is being set to "+capture_mode.name
        #set camera configs based on capture mode settings
        for name,value in capture_mode.camera_settings.items():
            if self.camera_configs[name].current != value:
                self.camera_configs[name].current = value
               
        time.sleep(5)
   
    ############################################################################################## 
    
    def _captureImages(self):
        print "capturing images"
        time.sleep(10)
        if self.camera_configs["imgquality"].current == "JPEG Normal":
            return {"jpeg":("test_image.JPG","test_image_JPG.info")}
        elif self.camera_configs["imgquality"].current == "NEF (Raw)":
            return {"NEF":("test_image.NEF","test_image_NEF.info")}
        elif self.camera_configs["imgquality"].current == "NEF+Normal":
            return {"NEF":("test_image.NEF","test_image_NEF.info"),"jpeg":("test_image.JPG","test_image_JPG.info")}
     
    ##############################################################################################
     
    def _getCameraConfigs(self):
        with open("test_camera_configs","rb") as fp:
            configs = cPickle.load(fp)
        
        return configs    
     
    ############################################################################################## 

    def _isConnected(self):
        time.sleep(1)
        return True
     
    ##############################################################################################
    def _downloadConfigs(self):
        time.sleep(10)
        with open("Pysces/test_camera_configs","rb") as fp:
            configs = cPickle.load(fp)
        
        return configs
     
     

