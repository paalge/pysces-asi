from __future__ import with_statement
import cPickle
from cameraManager import gphotoCameraManager

#import the plugins required to open the camera's images using PASKIL
#import PASKIL_D80_Jpeg_Plugin
#import PASKIL_D80_NEF_Plugin

#from PASKIL import allskyImage

class D80CameraManager(gphotoCameraManager):
    
    def _setCaptureMode(self,capture_mode):
        #set camera configs based on capture mode settings
        for name,value in capture_mode.camera_settings:
            if self.camera_configs[name].current != value:
                self._setConfig(name, value)

        #work out what the imgquality config should be set to based on the image types in the outputs
        files=[]
        for output in capture_mode.outputs:
            files.append(output.image_type)
        get_raw = False
        get_jpeg = True
        
        if files.count("NEF") != 0:
            get_raw = True
            
        if files.count("jpeg") != 0:
            get_jpg = True
        
        if get_jpg and get_raw:
            if self.camera_configs["imgquality"].current != "NEF+Normal":
                self._setConfig("imgquality", "NEF+Normal")
        elif get_raw:
            if self.camera_configs["imgquality"].current != "NEF (Raw)":
                self._setConfig("imgquality", "NEF (Raw)")
        else:
            if self.camera_configs["imgquality"].current != "JPEG Normal":
                self._setConfig("imgquality", "JPEG Normal")
        
        self.capture_mode = capture_mode
        
    ##############################################################################################         
    
    def _captureImage(self):
        """
        
        """
        glob_vars = self.__settings_manager.get(['tmp dir','filename_format','camera_rotation','fov_angle','lens_projection','latitude','longitude','magnetic_bearing'])

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
        active_folder,time_of_capture = self._takePhoto(number_of_images)
        
        if active_folder == None:
            #the folder wasn't empty to start with so we need to empty it first
            self._deletePhotos(active_folder)
            
            return None
        
        #otherwise copy the images from the camera into the current tmp dir
        self._copyPhotos(active_folder)       
        
        #delete images from camera card
        self._deletePhotos(active_folder)
        
        new_images = {}
        
        #create PASKIL allskyImage objects from the image files - rather than write a text based site info file,
        #we create the info dictionary here and then pickle it. The PASKIL plugin can then read the pickled dict
        if get_raw:
            info = self._buildPASKILInfo("NEF", capture_time, glob_vars)
            
            info_filename = glob_vars['tmp dir'] +"/"+time_of_capture.strftime(glob_vars['filename_format'])+"_NEF.info"
            image_filename = glob_vars['tmp dir'] +"/"+time_of_capture.strftime(glob_vars['filename_format'])+".NEF"
            
            #open file to pickle info dict into 
            with open(info_filename,"wb") as fp:
                cPickle.dump(info,fp)

            new_images["NEF"] = allskyImage.new(image_filename,site_info_file = info_filename)
        
        if get_jpeg:
            info = self._buildPASKILInfo("jpeg", capture_time, glob_vars)
            
            info_filename = glob_vars['tmp dir'] +"/"+time_of_capture.strftime(glob_vars['filename_format'])+"_JPG.info"
            image_filename = glob_vars['tmp dir'] +"/"+time_of_capture.strftime(glob_vars['filename_format'])+".JPG"
            
            #open file to pickle info dict into 
            with open(info_filename,"wb") as fp:
                cPickle.dump(info,fp)

            new_images["jpeg"] = allskyImage.new(image_filename,site_info_file = info_filename)
            
        return new_images
    
    ##############################################################################################         
    
    def _buildPASKILInfo(self,image_type,capture_time,glob_vars):
        info = {'camera':{},'header':{},'processing':{}}
        #search through outputs to find the image object corresponding to this type of image
        image = None
        for output in self.capture_mode.outputs:
            if output.image.image_type == image_type:
                image = output.image
                break
        assert image != None #make sure that we actually found the image
        
        info['camera']['y_center'] = image.y_center
        info['camera']['x_center'] = image.x_center
        info['camera']['Radius'] = image.Radius
        info['header']['Wavelength'] = image.Wavelength
        info['header']['Creation Time'] = capture_time.strftime("%d %b %Y %H:%M:%S %Z")
        
        info['camera']['lat'] = glob_vars['latitude']
        info['camera']['lon'] = glob_vars['longitude']
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