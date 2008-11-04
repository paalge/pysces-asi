"""
The camera module provides base classes for controlling the camera, these are
unusable by themselves and must be sub-classed. It also provides the 
CameraConfig class, which is a data storage class used to represent a gphoto2
style camera config.

Since camera control is a pipelined process, the CameraManager class inherits
from ThreadQueueBase, ensuring that only one thread accesses the camera.
"""
import datetime
import time
from subprocess import Popen, PIPE

from multitask import ThreadQueueBase, ThreadTask


class GphotoError(Exception):
    """
    Exception for gphoto2 errors. Since gphoto2 often throws up exceptions for
    no obvious reason, exceptions of this type should usually be caught and 
    ignored (unless they are recurring).
    """
    pass


class CameraManagerBase(ThreadQueueBase):
    """
    Base class for camera managers. Classes inheriting from this base class 
    must define all the protected methods of this class (the ones beginning
    with an underscore). They must also call ThreadQueueBase.exit() when 
    they exit in order to kill the internal worker thread. See the docs
    on the methods themselves for details of what they have to do.
    """
    def __init__(self):
        ThreadQueueBase.__init__(self,name="CameraManager")
        
        try:
            #check that camera is connected
            if not self.is_connected():
                raise GphotoError, "No camera detected"
        
            #get the camera configs
            self.camera_configs = self.download_configs()
            self.capture_mode = None
        except Exception, ex:
            self.exit()
            raise ex
    
    ############################################################################################## 
                
    #define public methods - these just queue protected methods for exectuion by 
    #the internal worker thread.
    def set_capture_mode(self, capture_mode):
        #create task
        task = ThreadTask(self._set_capture_mode, capture_mode)

        #submit task
        self.commit_task(task)

        #return result when task has been completed
        return task.result()
    
    ############################################################################################## 
    
    def capture_images(self):
        #create task
        task = ThreadTask(self._capture_images)
        
        #submit task
        self.commit_task(task)
        
        #return result when task has been completed
        return task.result()
    
    ############################################################################################## 
        
    def get_camera_configs(self):
        """
        Returns the camera configs stored in the camera manager - these should be the up-to-date
        configs.
        """
        
        task = ThreadTask(self.camera_configs.copy)
        
        #submit task
        self.commit_task(task)
        
        #return result when task has been completed
        return task.result()
   
    ############################################################################################## 
    
    def is_connected(self):
        task = ThreadTask(self._is_connected)
        
        #submit task
        self.commit_task(task)
        
        #return result when task has been completed
        return task.result()
    
    ##############################################################################################   
     
    def download_configs(self):
        task = ThreadTask(self._download_configs)
        
        #submit task
        self.commit_task(task)
        
        #return result when task has been completed
        return task.result()
    
    ############################################################################################## 
    
    def _set_capture_mode(self, capture_mode):
        """
        Given a CaptureMode object (see the data_storage_classes module) this method
        must update all the camera configs, both on the camera and in the 
        camera_configs attribute of this class. Note that this may also involve 
        setting the camera to capture all the different image types required by the
        outputs defined for the capture mode.
        """
        raise AttributeError, "cameraManagerBase must be sub-classed"
   
    ############################################################################################## 
    
    def _capture_images(self):
        """
        This method must return a dict: {type:(image_file,info_file)}, where type
        is a string describing the image type (this should be the same as the 
        image_type defined in the settings file), image_file is the complete path to
        the image file and info_file is the complete path to the site information
        file used to load the image into PASKIL. Note that the format of this file
        is entirely up to you, provided that you write a PASKIL plugin to read it
        (see the PASKIL.allskyImagePlugins module for details).
        """
        raise AttributeError, "cameraManagerBase must be sub-classed"
      
    ############################################################################################## 

    def _is_connected(self):
        """
        Method should return True if the camera is connected, False otherwise.
        """
        raise AttributeError, "cameraManagerBase must be sub-classed"
     
    ##############################################################################################
    def _download_configs(self):
        """
        This method should return a dict of CameraConfig objects, one for each 
        possible camera config. The keys in the dict should be a short name for
        the configs, and must be identical to the names used in the settings file
        for the configs.
        """
        raise AttributeError, "cameraManagerBase must be sub-classed"
     
    ##############################################################################################
##############################################################################################

class GphotoCameraManager(CameraManagerBase):
    """
    The GphotoCameraManager class must also be sub-classed in order to be used.
    It provides methods that are general to gphoto2 compatible cameras.
    """
    
    def __init__(self, settings_manager):
        self._settings_manager = settings_manager
        
        self._settings_manager.set({"output":"cameraManager> Downloading settings from camera - please wait"})
        
        CameraManagerBase.__init__(self)       
               
    ############################################################################################## 
    
    def _set_config(self, name, value):
        """
        Sets a single camera config. The name argument should be the short name
        of the config. The value argument should be the descriptive value of the
        config (i.e. not the 0,1,2,3... index) and should be a string.
        """
        self._settings_manager.set({"output":"cameraManager> Setting "+name+" to "+value})    
        
        #convert the descriptive value to its index value using the list of 
        #camera configs
        config = self.camera_configs[name]        
        value_index = config.values[value]
        
        #run gphoto function in separate process
        p = Popen("gphoto2 --set-config "+str(name)+"="+value_index, shell=True)
        p.wait()
        
        if p.returncode != 0:
            raise GphotoError, "GPhoto2 Error: failed to set config"+name
        
        #update the camera_configs attribute to reflect the change.    
        self.camera_configs[name].current = value
        
    ##############################################################################################     
    
    def _is_connected(self):
        """
        Returns True if the camera is connected, False otherwise. This method
        works by reading the length of the output from the gphoto2 auto-detect
        function. This makes it somewhat unreliable since USB devices other
        than the camera often appear in the list and this method cannot tell them
        apart.
        """
        
        #run gphoto function in separate process and record any output
        p = Popen("gphoto2 --auto-detect", shell=True, stdout=PIPE, stderr=PIPE)
        
        #wait for process to finish and read the output from the pipes
        p.wait()
        out = p.stdout.readlines()
        outerr = p.stderr.read()

        if p.returncode != 0:
            raise GphotoError, "GPhoto2 Error: failed to auto detect\n"+outerr
 
        #split output into lines and see how many lines there were in the list
        #to determine if the camera was present or not.
        if len(out) < 3:
            return False
        else:
            return True
        
    ##############################################################################################     
    
    def _delete_photos(self, active_folder):
        """
        Removes all the images from the specified folder on the camera.
        """
        #run gphoto command in separate process
        p = Popen("gphoto2 -D --folder="+active_folder, shell=True)
        p.wait()
        
        if p.returncode != 0:
            raise GphotoError, "Gphoto2 Error: Unable to delete the image(s) from camera card"
    
    ##############################################################################################    
    
    def _take_photo(self, number_of_images):
        """
        Captures an image and returns a tuple (active folder, capture time), where
        active folder is the folder on the camera where the image was stored (note 
        that on many cameras this changes since the images and folders are numbered
        sequentially), and capture time is a datetime object of the capture time in 
        UT. The number_of_images argument should be the number of image files that
        the camera is expected to produce. For example if the camera is capturing
        both a jpeg and a raw image, then it will be 2. This method works by reading
        the output from the gphoto2 --list-files function both before and after image
        capture. It compares the two to work out what folder on the camera the image 
        has been stored in. However, since the gphoto2 --capture-image function 
        returns before the image has been stored on the camera card, it also has to use
        the list function to work out if the camera has finished storing the image(s) or
        not. To do this it needs to know how many images to expect.
        
        To be able to download the correct images, the camera card needs to be blank.
        If it is not, then this method deletes all the photos on it and returns a
        (None, None) tuple.
        
        Note: The time of capture recorded and used to name the files is the time
        just before the shutter is opened, i.e. before the call to gphoto2 --capture-image.
        """
        #get list of files on camera before capture
        #run gphoto function in separate process and wait for it to finish
        p = Popen("gphoto2 -L ", shell=True, stdout=PIPE)
        p.wait()
        if p.returncode != 0:
            raise GphotoError, "Gphoto2 Error: Unable to list of files on camera card"
        
        #read the lines of output from the gphoto command
        pre_image_list = p.stdout.readlines()
        
        #take the picture!
        time_of_capture = datetime.datetime.utcnow()
        self._settings_manager.set({"output": "cameraManager> Capturing image."})
        
        p = Popen("gphoto2 --capture-image ", shell=True)
        p.wait()
        if p.returncode != 0:
            raise GphotoError, "Gphoto2 Error: Failed to capture image"
        
        #wait for the image to be stored for up to one minute
        flag = False
        while (time_of_capture + datetime.timedelta(minutes=1) > datetime.datetime.utcnow()) and (not flag):
            #give the camera some time to store the image before we start pestering it
            time.sleep(10)
            
            #get list of files on camera
            p = Popen("gphoto2 -L ", shell=True, stdout=PIPE)
            p.wait()
            if p.returncode != 0:
                raise GphotoError, "Gphoto2 Error: Unable to list of files on camera card"
            
            post_image_list = p.stdout.readlines()
            #compare the new list of files to the one recorded before taking a picture
            #and work out how many new files have appeared and what folder they have
            #appeared in    
            if post_image_list == pre_image_list:
                continue
            else:              
                #remove entries which existed before the image
                for line in pre_image_list:
                    try:
                        post_image_list.remove(line)
                    except ValueError:
                        continue
               
                #get number of files in active folder
                folder_filecount = 0
                for line in post_image_list:
                    if line.lstrip().startswith("There"):
                        words = line.split()
                        active_folder = eval(words[len(words)-1].rstrip("."))
                        try:
                            folder_filecount = eval(words[2])
                        except NameError:
                            pass
             
                if folder_filecount < number_of_images:
                    #if image has not been stored yet, then wait longer
                    continue
                elif folder_filecount == number_of_images:
                    #the image(s) have been stored, so break out of the loop
                    flag = True
                    continue
                elif folder_filecount > number_of_images:
                    #this means that the camera card probably wasn't blank to start with - which is a tricky problem!
                    #The easiest way around this is to wipe the card and accept that we will lose the photo(s)
                    #that have just been taken
                    self._settings_manager.set({"output":"cameraManager> Error! Camera card was not blank!"})
                    self._settings_manager.set({"output":"cameraManager> Deleting all images from camera."})
                    self._delete_photos(active_folder)
                    return None, None

        if not flag:
            #it has taken more than one minute to store the image - something
            #has probably gone wrong!
            raise GphotoError, "Gphoto2 Error: Unable to download image(s)"
        else:
            return active_folder, time_of_capture
    
    ##############################################################################################    
    
    def _copy_photos(self, folder_on_camera, time_of_capture):
        """
        Downloads all the images in the folder_on_camera into the temporary folder on
        the host. The image files are named using the filename format specified in the
        settings file and the time of capture. This method should take the values
        returned by the _take_photo method as its arguments.
        """
        glob_vars = self._settings_manager.get(['tmp dir', 'filename_format'])
        
        self._settings_manager.set({"output": "cameraManager> Downloading image(s)"})
        p = Popen("gphoto2 -P --folder="+folder_on_camera+" --filename=\""+glob_vars['tmp dir']+"/"+time_of_capture.strftime(glob_vars['filename_format'])+".%C\"", shell=True)
        p.wait()
        if p.returncode != 0:
            raise GphotoError, "Gphoto2 Error: Unable to copy the photos from the camera card"
             
    ##############################################################################################            
    
    def _download_configs(self):
        """
        Returns a dictionary containing CameraConfig objects for all of the possible camera configs.
        The keys are the short names of the configs.
        """
        current_configs = {}      

        #get list of possible configs for camera
        #run gphoto function in separate process
        p = Popen("gphoto2 --list-config", shell=True, stdout=PIPE)       
        p.wait()
        if p.returncode != 0:
            raise GphotoError, "Gphoto2 Error: Unable to download the list of configs"
            
        #read output lines from pipe
        lines = p.stdout.readlines()
        
        #get the current and possible values for all the different configs
        for config in lines:
            #skip blank lines
            if config.isspace() or config == "":
                continue
            
            #get short name of config
            split = config.split("/")
            name = split[len(split)-1].lstrip().rstrip()
            
            current_configs[name] = self._get_config(config)
          
        return current_configs
   
    ############################################################################################## 
    
    def _set_capture_mode(self, capture_mode):
        raise AttributeError, "gphotoCameraManager must be sub-classed"
    
    ############################################################################################## 
    
    def _capture_images(self):
        raise AttributeError, "gphotoCameraManager must be sub-classed"
    
    ############################################################################################## 
     
    def _get_config(self, name):
        """
        Wrapper function for gphoto2's --get-config function. Returns a CameraConfig object.
        The name argument should be a string specifying the name of the config, e.g. "exptime"
        """

        values = {}
        
        #get values for particular config
        
        #run gphoto function in separate process
        p = Popen("gphoto2 --get-config "+name, shell=True, stdout=PIPE, stderr=PIPE)
        p.wait()
        if p.returncode != 0:
            raise GphotoError, "GPhoto2 Error: failed to download config"+name
            
        #read config value lines from pipe
        config_lines = p.stdout.readlines()
        
        #read the values of the config from the output of the gphoto function
        for line in config_lines:
            if line.isspace() or line == "":
                continue
            
            elif line.lstrip().startswith("Label:"):
                label = line.lstrip().lstrip("Label:").lstrip().rstrip()
            
            elif line.lstrip().startswith("Type:"):
                continue
            
            elif line.lstrip().startswith("Current:"):
                current = line.lstrip().lstrip("Current:").lstrip().rstrip()
                
            elif line.lstrip().startswith("Choice:"):
                choice = line.lstrip().lstrip("Choice:").lstrip().rstrip()
                
                choice_words = choice.split()
                name = ""
                
                for word in choice_words[1:]:
                    name += " "+word

                values[name.lstrip().rstrip()] = choice_words[0].lstrip().rstrip()

        return CameraConfig(label, current, values)
    
     ##############################################################################################
##############################################################################################

class CameraConfig:
    """
    Storage class for camera configs. These relate to the information returned by Gphoto2 --get-config.
    label = short name of config
    current = current setting on camera
    values = list of possible values for the config
    """
    def __init__(self, label, current, values):
        self.label = label
        self.current = current
        self.values = values.copy()    
    
##############################################################################################    
    
    
        