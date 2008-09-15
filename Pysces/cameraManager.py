"""
The cameraManager module provides a cameraManager and cameraConfig classes for the complete control of the 
camera. This includes image capture, image download and settings updates.

"""

from subprocess import Popen,PIPE
import string,datetime,time
from task import taskQueueBase,Task


class cameraManagerBase(taskQueueBase):
    """
    Base class for camera managers.
    """
    def __init__(self):
        taskQueueBase.__init__(self)
        
        try:
            #check that camera is connected
            if not self.isConnected():
                raise RuntimeError,"No camera detected"
        
            #get the camera configs
            self.camera_configs = self.downloadConfigs()
            self.capture_mode = None
        except Exception,ex:
            self.exit()
            raise ex
    
    ############################################################################################## 
                
    #define public methods
    def setCaptureMode(self,capture_mode):
        #create task
        task = Task(self._setCaptureMode,capture_mode)

        #submit task
        self.commitTask(task)

        #return result when task has been completed
        return task.result()
    
    ############################################################################################## 
    
    def captureImages(self):
        #create task
        task = Task(self._captureImages)
        
        #submit task
        self.commitTask(task)
        
        #return result when task has been completed
        return task.result()
    
    ############################################################################################## 
        
    def getCameraConfigs(self):
        """
        Returns the camera configs stored in the camera manager - these should be the up-to-date
        configs.
        """
        
        task = Task(self.camera_configs.copy)
        
        #submit task
        self.commitTask(task)
        
        #return result when task has been completed
        return task.result()
   
    ############################################################################################## 
    
    def isConnected(self):
        task = Task(self._isConnected)
        
        #submit task
        self.commitTask(task)
        
        #return result when task has been completed
        return task.result()
    
    ##############################################################################################   
     
    def downloadConfigs(self):
        task = Task(self._downloadConfigs)
        
        #submit task
        self.commitTask(task)
        
        #return result when task has been completed
        return task.result()
    
    ############################################################################################## 
    
    def _setCaptureMode(self,capture_mode):
        raise AttributeError, "cameraManagerBase must be sub-classed"
   
    ############################################################################################## 
    
    def _captureImages(self):
        raise AttributeError, "cameraManagerBase must be sub-classed"
     
     ##############################################################################################
##############################################################################################

class gphotoCameraManager(cameraManagerBase):
    """
    Class responsible for controlling the camera. This class is restricted to gphoto2 compatible cameras
    which can capture "NEF" and "jpeg" type images. 
    """
    
    def __init__(self,settings_manager):
        self._settings_manager = settings_manager
        
        self._settings_manager.set({"output":"cameraManager> Downloading settings from camera - please wait"})
        
        cameraManagerBase.__init__(self)       
               
    ############################################################################################## 
    
    def _setConfig(self,name,value):
        
        self._settings_manager.set({"output":"cameraManager> Setting "+name+" to "+value})    
        
        config = self.camera_configs[name]
        
        value_index = config.values[value]
        
        #run gphoto function in separate process
        p = Popen("gphoto2 --set-config "+str(name)+"="+value_index,shell=True,stdout=PIPE)
        
        out = string.join(p.stdout.readlines())
        
        #wait for process to finish
        p.wait()
        
        if p.returncode != 0:

                raise RuntimeError,"GPhoto2 Error: failed to set config"+name
            
        self.camera_configs[name].current = value
        
    ##############################################################################################     
    
    def _isConnected(self):

        #run gphoto function in separate process
        p = Popen("gphoto2 --auto-detect",shell=True,stdout=PIPE,stderr=PIPE)
        
        out = string.join(p.stdout.readlines())
        outerr = string.join(p.stderr.readlines())
        
        #wait for process to finish
        p.wait()

        if p.returncode != 0:

                raise RuntimeError,"GPhoto2 Error: failed to auto detect\n"+outerr
 
        #split output into lines
        lines = out.split("\n")
        
        if len(lines) <=3:
            return False
        else:
            return True
        
    ##############################################################################################     
    
    def _deletePhotos(self,active_folder):
        #run gphoto command in separate process
        p = Popen("gphoto2 -D --folder="+active_folder,shell=True,stdout=PIPE)
        out = string.join(p.stdout.readlines())
        p.wait()
        
        if p.returncode != 0:

                raise RuntimeError,"Gphoto2 Error: Unable to delete the image(s) from camera card"
    
    ##############################################################################################    
    
    def _takePhoto(self,number_of_images):
        #get list of files on camera
        #run gphoto function in separate process
        p = Popen("gphoto2 -L ",shell=True,stdout=PIPE)
        pre_image_out = string.join(p.stdout.readlines())
        
        #wait for process to finish
        p.wait()
        
        if p.returncode != 0:

                raise RuntimeError,"Gphoto2 Error: Unable to list of files on camera card"
        
        pre_image_list = pre_image_out.split("\n")
        
        time_of_capture = datetime.datetime.utcnow()
        self._settings_manager.set({"output": "cameraManager> Capturing image."})
        
        p = Popen("gphoto2 --capture-image ",shell=True,stdout=PIPE)
        out = string.join(p.stdout.readlines())
        p.wait()
       
        if p.returncode != 0:

                raise RuntimeError, "Gphoto2 Error: Failed to capture image"
       
        #wait for the image to be stored for up to one minute
        flag=False
        while (time_of_capture + datetime.timedelta(minutes=1) > datetime.datetime.utcnow()) and (not flag):
           
            time.sleep(10)
            #get list of files on camera
            #run gphoto function in separate process
            p = Popen("gphoto2 -L ",shell=True,stdout=PIPE)
            post_image_out = string.join(p.stdout.readlines())
            
            #wait for process to finish
            p.wait()
            if p.returncode != 0:

                    raise RuntimeError,"Gphoto2 Error: Unable to list of files on camera card"
                
            if post_image_out == pre_image_out:
                continue
            else:
                post_image_list = post_image_out.split("\n")
                
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
   
                #if image has not been stored yet, then wait longer
                if folder_filecount < number_of_images:
                    continue
                elif folder_filecount == number_of_images:
                    flag = True
                    continue
                elif folder_filecount > number_of_images:
                    #this means that the camera card probably wasn't blank to start with - which is a tricky problem!
                    #The easiest way around this is to wipe the card and accept that we will lose the photo(s)
                    #that have just been taken
                    self._settings_manager.set({"output":"cameraManager> Error! Camera card was not blank!"})
                    self._settings_manager.set({"output":"cameraManager> Deleting all images from camera."})
                    self._deletePhotos(active_folder)
                    return None,None

        if not flag:
            raise RuntimeError,"Gphoto2 Error: Unable to download image(s)"
        else:
            return active_folder,time_of_capture
    
    ##############################################################################################    
    
    def _copyPhotos(self,folder_on_camera,time_of_capture):
        glob_vars = self._settings_manager.get(['tmp dir','filename_format'])
        
        self._settings_manager.set({"output": "cameraManager> Downloading image(s)"})
        p = Popen("gphoto2 -P --folder="+folder_on_camera+" --filename=\""+glob_vars['tmp dir']+"/"+time_of_capture.strftime(glob_vars['filename_format'])+".%C\"",shell=True,stdout=PIPE)
        out = string.join(p.stdout.readlines())
        p.wait()
        
        if p.returncode != 0:

                raise RuntimeError,"Gphoto2 Error: Unable to copy the photos from the camera card"
        
        
    ##############################################################################################            
    
    def _downloadConfigs(self):
        """
        Returns a dictionary containing cameraConfig objects for all of the possible camera configs.
        The keys are the short names of the configs.
        """

        current_configs = {}      

        #get list of possible configs for camera
        #run gphoto function in separate process
        p = Popen("gphoto2 --list-config",shell=True,stdout=PIPE)
        
        out = string.join(p.stdout.readlines())
        
        #wait for process to finish
        p.wait()
        if p.returncode != 0:

                raise RuntimeError,"Gphoto2 Error: Unable to download the list of configs"
            
        #split output into lines
        lines = out.split("\n")
        
        for config in lines:
            #skip blank lines
            if config.isspace() or config == "":
                continue
            
            #get short name of config
            split = config.split("/")
            name = split[len(split)-1].lstrip().rstrip()
            
            current_configs[name] = self._getConfig(config)
          
        return current_configs
   
    ############################################################################################## 
    
    def _setCaptureMode(self,capture_mode):
        raise AttributeError, "gphotoCameraManager must be sub-classed"
    
    ############################################################################################## 
    
    def _captureImages(self):
        raise AttributeError, "gphotoCameraManager must be sub-classed"
    
    ############################################################################################## 
     
    def _getConfig(self,name):
        """
        Wrapper function for gphoto2's --get-config function. Returns a cameraConfig object.
        The name argument should be a string specifying the name of the config, e.g. "exptime"
        """

        values = {}
        
        #get values for particular config
        
        #run gphoto function in separate process
        p = Popen("gphoto2 --get-config "+name,shell=True,stdout=PIPE,stderr=PIPE)
        
        out = string.join(p.stdout.readlines()) 

        p.wait()
  
        if p.returncode != 0:

                raise RuntimeError,"GPhoto2 Error: failed to download config"+name
            
        #split config values into lines
        config_lines = out.split("\n")
        
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

        return cameraConfig(label,current,values)
    
     ##############################################################################################
##############################################################################################

class cameraConfig:
    """
    Storage class for camera configs. These relate to the information returned by Gphoto2 --get-config.
    label = short name of config
    current = current setting on camera
    values = list of possible values for the config
    """
    def __init__(self,label,current,values):
        self.label = label
        self.current = current
        self.values = values.copy()    
    
    
    
    
        