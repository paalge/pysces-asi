"""
The D80 module provides a single camera manager class for controlling a Nikon
D80 camera.
"""
import cPickle

import PASKIL_jpg_plugin #import the plugin needed to open the image files in PASKIL
from camera import GphotoCameraManager

##############################################################################################  

class D80CameraManager(GphotoCameraManager):
    """
    Class for controlling a Nikon D80 camera. 
    """
    def __init__(self, settings_manager):
        GphotoCameraManager.__init__(self, settings_manager)
        
        #ensure that the camera is set to capture to the card, rather than the RAM
        if self.camera_configs['capturetarget'].current != "Memory card":
            self._set_config('capturetarget', 'Memory card')

    ##############################################################################################      
    
    def _set_capture_mode(self, capture_mode):
        """
        Sets the camera configs to those specified in the CaptureMode object
        passed as the argument. Note that the _set_config() method (which is
        inherited from the GphotoCameraManager class) takes care of updating
        the camera_configs attribute (which is inherited from the 
        CameraManagerBase class).
        """
        #set camera configs based on capture mode settings
        for name, value in capture_mode.camera_settings.items():
            if self.camera_configs[name].current != value:
                self._set_config(name, value)

        #work out what the imgquality config should be set to based on the image types in the outputs
        files=[]
        for output in capture_mode.outputs:
            files.append(output.image_type.image_type)
        
        get_raw = False
        get_jpeg = False
        
        if files.count("NEF") != 0:
            get_raw = True
            
        if files.count("jpeg") != 0:
            get_jpeg = True
        
        if get_jpeg and get_raw:
            if self.camera_configs["imgquality"].current != "NEF+Normal":
                self._set_config("imgquality", "NEF+Normal")
        elif get_raw:
            if self.camera_configs["imgquality"].current != "NEF (Raw)":
                self._set_config("imgquality", "NEF (Raw)")
        else:
            if self.camera_configs["imgquality"].current != "JPEG Normal":
                self._set_config("imgquality", "JPEG Normal")
        
        self.capture_mode = capture_mode
        
    ##############################################################################################         
    
    def _capture_images(self):
        """
        Captures the images and creates the site info files needed to open them with 
        PASKIL.
        """
        glob_vars = self._settings_manager.get(['tmp dir', 'filename_format', 'camera_rotation', 'fov_angle', 'lens_projection', 'latitude', 'longitude', 'magnetic_bearing'])

        get_raw = False
        get_jpeg = False
        
        number_of_images = 0
        
        #see if we need to download a raw file
        if self.camera_configs["imgquality"].current.count("NEF") != 0:
            get_raw = True
            number_of_images += 1
            
        if self.camera_configs["imgquality"].current.count("Normal") != 0:
            get_jpeg = True
            number_of_images += 1 
                
        #capture the image and find which folder the camera puts it in    
        active_folder, time_of_capture = self._take_photo(number_of_images)
        
        if active_folder == None:
            #the folder wasn't empty to start with so we need to empty it first
            return None
        
        #otherwise copy the images from the camera into the current tmp dir
        self._copy_photos(active_folder, time_of_capture)       
        
        #delete images from camera card
        self._delete_photos(active_folder)
        
        new_images = {}
        
        #create PASKIL allskyImage objects from the image files - rather than write a text based site info file,
        #we create the info dictionary here and then pickle it. The PASKIL plugin can then read the pickled dict
        if get_raw:
            info = self._build_PASKIL_info("NEF", time_of_capture, glob_vars)
            
            info_filename = glob_vars['tmp dir'] +"/"+time_of_capture.strftime(glob_vars['filename_format'])+"_NEF.info"
            image_filename = glob_vars['tmp dir'] +"/"+time_of_capture.strftime(glob_vars['filename_format'])+".NEF"
            
            #open file to pickle info dict into 
            with open(info_filename, "wb") as fp:
                cPickle.dump(info, fp)

            new_images["NEF"] = (image_filename, info_filename)
        
        if get_jpeg:
            info = self._build_PASKIL_info("jpeg", time_of_capture, glob_vars)
            
            info_filename = glob_vars['tmp dir'] +"/"+time_of_capture.strftime(glob_vars['filename_format'])+"_JPG.info"
            image_filename = glob_vars['tmp dir'] +"/"+time_of_capture.strftime(glob_vars['filename_format'])+".JPG"
            
            #open file to pickle info dict into 
            with open(info_filename, "wb") as fp:
                cPickle.dump(info, fp)

            new_images["jpeg"] = (image_filename, info_filename)
            
        return new_images
    
    ##############################################################################################         
    
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
        
        #copy camera settings into image header
        for name in self.camera_configs.keys():
            info['header'][name] = self.camera_configs[name].current
            
        #TODO
        #add metadata about the software used etc.
                
        return info
    
    ##############################################################################################             
############################################################################################## 