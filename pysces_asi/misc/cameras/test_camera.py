from __future__ import with_statement

import time
import random
import Image
import datetime
import cPickle
from pysces_asi import PASKIL_jpg_plugin #import the plugin needed to open the image files in PASKIL

from pysces_asi.camera import CameraManagerBase, GphotoError, register

class CameraSimulator(CameraManagerBase):
    def __init__(self,settings_manager):
        CameraManagerBase.__init__(self, settings_manager)
        self.settings_manager =  settings_manager
        
           
    def set_capture_mode(self,capture_mode):
        self.files=[]
        self.image_sizes = {}
        self.capture_mode = capture_mode
        for output in capture_mode.outputs:
            image_name = output.image_type.image_type
            image_width = 2*int(output.image_type.x_center)
            image_height = 2*int(output.image_type.y_center)
            self.files.append(image_name)
            self.image_sizes[image_name] = (image_width,image_height)
            
        
        self.files = list(set(self.files))
        
        for name,value in capture_mode.camera_settings.items():
            self.settings_manager.set({'output':"Setting "+name+" to "+str(value)})
        #print "Camera is being set to "+capture_mode.name
        #set camera configs based on capture mode settings
        #for name,value in capture_mode.camera_settings.items():
        #    if self.camera_configs[name].current != value:
        #        self.camera_configs[name].current = value
        i = random.randint(0,20)
        if i==20:
            raise GphotoError, "Failed to set capture mode"
        time.sleep(0.5)
        return
   
    ##############################################################################################
    def _clear_camera(self):
        pass
    
    def capture_images(self):
        self.settings_manager.set({'output':"CameraManager> Capturing Image"})
        glob_vars = self.settings_manager.get(['tmp dir', 'camera_rotation', 'fov_angle', 'lens_projection', 'latitude', 'longitude', 'magnetic_bearing'])
        time_of_capture = datetime.datetime.utcnow()
        time.sleep(2)
        i = random.randint(0,20)
        if i==20:
            raise GphotoError, "Failed to capture image"
        
        tmp_dir = glob_vars['tmp dir']
        
        new_images = {}
        for filetype in self.files:
            im = Image.new("RGB", self.image_sizes[filetype], (150,150,150))
            
        
            info = self._build_PASKIL_info(filetype, time_of_capture, glob_vars)
            
            info_filename = glob_vars['tmp dir'] +"/"+time_of_capture.strftime("%Y%m%d_%H%M%S")+"_"+filetype+".info"
            image_filename = glob_vars['tmp dir'] +"/"+time_of_capture.strftime("%Y%m%d_%H%M%S")+"."+filetype
            
            #open file to pickle info dict into 
            with open(info_filename, "wb") as fp:
                cPickle.dump(info, fp)
            
            im.save(image_filename,format="jpeg")
            
            new_images[filetype] = (image_filename, info_filename)
                
        return new_images
    
  
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
    
    def _build_PASKIL_info(self, image_type, capture_time, glob_vars):
        """
        Creates a dict containing all the information required by PASKIL, in the 
        correct format. See docs for PASKIL.allskyImagePlugins.
        """
        info = {'camera':{}, 'header':{}, 'processing':{}}
        #search through outputs to find the image object corresponding to this type of image
        image = None
        
        for output in self.capture_mode.outputs:
            if output.image_type.image_type == image_type:
                image = output.image_type
                break
        assert image != None #make sure that we actually found the image
        
        info['camera']['y_center'] = image.y_center
        info['camera']['x_center'] = image.x_center
        info['camera']['Radius'] = image.Radius
        info['header']['Wavelength'] = image.Wavelength
        info['header']['Creation Time'] = capture_time.strftime("%d %b %Y %H:%M:%S")+" GMT"
        
        info['camera']['lat'] = glob_vars['latitude']
        info['camera']['lon'] = glob_vars['longitude']
        info['camera']['Magn. Bearing'] = glob_vars['magnetic_bearing']
        info['camera']['lens_projection'] = glob_vars['lens_projection']
        info['camera']['cam_rot'] = glob_vars['camera_rotation']
        info['camera']['fov_angle'] = glob_vars['fov_angle']
                
        return info     
register("Camera Simulator",CameraSimulator)     

