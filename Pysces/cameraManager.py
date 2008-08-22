"""
The cameraManager module provides a cameraManager and cameraConfig classes for the complete control of the 
camera. This includes image capture, image download and settings updates.

This module could really do with more development work - it is far too specialised at the moment.
"""

from subprocess import Popen,PIPE
from threading import Lock
import string,datetime,time

class cameraManager:
    """
    Class responsible for controlling the camera. This class is restricted to gphoto2 compatible cameras
    which can capture "NEF" and "jpeg" type images.
    
    It would be much better if this was re-written to make it more flexible - sub-classing is required here!
    
    """
    
    def __init__(self,settings_manager):
        self.__settings_manager = settings_manager
        self.__camera_lock = Lock()
        
        #check that camera is connected
        if not self.isConnected():
            raise RuntimeError,"No camera detected"
        
        #create global variable for camera configs
        try:
            self.__settings_manager.create("camera configs",{})
        except ValueError:
            #if the camera configs variable already exists then we will just overwrite it
            pass
        
        self.__settings_manager.set("output","cameraManager> Downloading settings from camera - please wait")
        self.__settings_manager.set("camera configs", self.__getCameraConfigs())
        
        
        #set callbacks for camera configs
        self.__settings_manager.register("current capture mode",self.updateConfigs)        
        self.__settings_manager.register("current capture mode",self.updateImgs)
        
        
    ############################################################################################## 
    
    def updateImgs(self):
        """
        Function updates the imgquality camera config, controlling whether it records JPEG, NEF
        or JPEG+NEF images.
        """
        #grab global variables
        glob_vars = self.__settings_manager.grab(["capture modes","output types","current capture mode"])
        
        try:
            capture_modes = glob_vars["capture modes"]
            output_types = glob_vars["output types"]
            ccm = glob_vars["current capture mode"]
            files = []
            get_raw = False
            get_jpg = False
            
            #look at which files are needed in the outputs for this capture mode
            if ccm != "" and ccm != None:
                for output in capture_modes[ccm]["outputs"]:
                    files.append(output_types[output]["image_type"])
            
            if files.count("NEF") != 0:
                get_raw = True
            
            if files.count("jpeg") != 0:
                get_jpg = True
            
            if get_jpg and get_raw:
                self.setConfig("imgquality", "NEF+Normal")
            elif get_raw:
                self.setConfig("imgquality", "NEF (Raw)")
            else:
                self.setConfig("imgquality", "JPEG Normal")
        finally:
            self.__settings_manager.release(glob_vars)
        
    ##############################################################################################         
    
    def captureImage(self):
        """
        Takes a photo, downloads it to the tmp directory with a filename as specified in the settings
        file and then wipes the camera card. It is also responsible for updating the "most recent images"
        variable. This must be set to dictionary {image type : image filename} containing all the images
        captured. Note that setting this variable causes the on-the-fly processing to be run (via a callback)
        """
        
        #grab globals
        glob_vars = self.__settings_manager.grab(["camera configs","tmp dir","filename_format"])
        
        try:
            configs = glob_vars["camera configs"]
            
            self.__camera_lock.acquire()
            
            try:
                get_raw = False
                get_jpeg = False
                
                #see if we need to download a raw file
                if configs["imgquality"].current.count("NEF") != 0:
                    get_raw = True
                
                if configs["imgquality"].current.count("Normal") != 0:
                    get_jpeg = True
                
                #get list of files on camera
                #run gphoto function in separate process
                p = Popen("gphoto2 -L ",shell=True,stdout=PIPE)
                pre_image_out = string.join(p.stdout.readlines())
                
                #wait for process to finish
                p.wait()
        
                pre_image_list = pre_image_out.split("\n")
                
                time_of_capture = datetime.datetime.now()
                self.__settings_manager.set("output", "cameraManager> Capturing image.")
                p = Popen("gphoto2 --capture-image ",shell=True)
                p.wait()
                
                if p.returncode != 0:
                    raise RuntimeError, "Gphoto2 Error: Failed to capture image"
                
                #wait for the image to be stored for up to one minute
                flag=False
                while time_of_capture + datetime.timedelta(minutes=1) > datetime.datetime.now() and not flag:
                    time.sleep(10)
                    #get list of files on camera
                    #run gphoto function in separate process
                    p = Popen("gphoto2 -L ",shell=True,stdout=PIPE)
                    post_image_out = string.join(p.stdout.readlines())
                    
                    #wait for process to finish
                    p.wait()
                    
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
                        if folder_filecount == 0 and (get_raw or get_jpeg):
                            continue
                        elif get_raw and get_jpeg and folder_filecount == 2:
                            flag = True
                            continue
                        elif (get_raw or get_jpeg) and folder_filecount == 1:
                            flag = True
                            continue
                        elif not get_jpeg and not get_raw:
                            flag = True
                            continue
                        elif (get_raw and get_jpeg) and (folder_filecount > 2):
                            #this means that the camera card probably wasn't blank to start with - which is a tricky problem!
                            #The easiest way around this is to wipe the card and accept that we will lose the photo(s)
                            #that have just been taken
                            self.__settings_manager.set("output","cameraManager> Error! Camera card was not blank!")
                            self.__settings_manager.set("output","cameraManager> Deleting all images from camera.")
                            p = Popen("gphoto2 -D --folder="+active_folder,shell=True)
                            p.wait()
                            return
                        elif (get_raw or get_jpeg) and folder_filecount > 1:
                            #as above but when we are only taking one type of image
                            self.__settings_manager.set("output","cameraManager> Error! Camera card was not blank!")
                            self.__settings_manager.set("output","cameraManager> Deleting all images from camera.")
                            p = Popen("gphoto2 -D --folder="+active_folder,shell=True)
                            p.wait()
                            return
                
                if not flag:
                    raise RuntimeError,"Gphoto2 Error: Unable to download image(s)"
                
                #otherwise get the images
                if get_raw or get_jpeg:
                    self.__settings_manager.set("output", "cameraManager> Downloading image(s)")
                    p = Popen("gphoto2 -P --folder="+active_folder+" --filename=\""+glob_vars['tmp dir']+"/"+time_of_capture.strftime(glob_vars['filename_format'])+".%C\"",shell=True)
                    p.wait()
                
                    if p.returncode != 0:
                        raise RuntimeError,"Gphoto2 Error: Unable to download the image(s)"        
                
                #delete images from camera card
                self.__settings_manager.set("output", "cameraManager> Deleting images from camera.")
                p = Popen("gphoto2 -D --folder="+active_folder,shell=True)
                p.wait()
                
                if p.returncode != 0:
                    raise RuntimeError,"Gphoto2 Error: Unable to delete the image(s) from camera card" 
                
            finally:
                self.__camera_lock.release()
            
            new_images = {}
            if get_raw:
                new_images["NEF"] = glob_vars['tmp dir'] +"/"+time_of_capture.strftime(glob_vars['filename_format'])+".NEF"
            if get_jpeg:
                new_images["jpeg"] = glob_vars['tmp dir'] +"/"+time_of_capture.strftime(glob_vars['filename_format'])+".JPG"
            
            self.__settings_manager.set("most recent images",new_images)
            
        finally:
            self.__settings_manager.release(glob_vars)
    
    ############################################################################################## 
    
    def updateConfigs(self):
        #grab globals
        glob_vars = self.__settings_manager.grab(["camera configs","capture modes","current capture mode"])
        
        try:
            #rename for clarity
            camera_configs = glob_vars["camera configs"]
            capture_modes = glob_vars["capture modes"]
            ccm = capture_modes[glob_vars["current capture mode"]]
            
            
            iso = ccm["iso"]
            f_number = ccm["f-number"]
            exptime = ccm["exptime"]
            imgsize = ccm["imgsize"]
            whitebalance = ccm["whitebalance"]
            focusmode = ccm["focusmode"]
            
            if iso != camera_configs['iso'].current:
                self.setConfig('iso', str(iso))
            
            if f_number != camera_configs['f-number'].current:
                self.setConfig('f-number',str(f_number))
         
            if exptime != camera_configs['exptime'].current:
                self.setConfig('exptime',str(exptime ))
            
            if imgsize != camera_configs['imgsize'].current:
                self.setConfig('imgsize', str(imgsize))
                
            if whitebalance != camera_configs['whitebalance'].current:
                self.setConfig('whitebalance',str(whitebalance))
            
            if focusmode != camera_configs['focusmode'].current:
                self.setConfig('focusmode', str(focusmode))
        finally:
            self.__settings_manager.release(glob_vars)
        
    ##############################################################################################     
    
    def setConfig(self,name,value):
        
        self.__settings_manager.set("output","cameraManager> Setting "+name+" to "+value)
        
        #grab globals
        glob_vars = self.__settings_manager.grab(["camera configs"])
        
        try:
            self.__camera_lock.acquire()
            
            try:
                camera_configs = glob_vars["camera configs"]    
                
                config = camera_configs[name]
                
                value_index = config.values[value]
                
                #run gphoto function in separate process
                p = Popen("gphoto2 --set-config "+str(name)+"="+value_index,shell=True)
                
                #wait for process to finish
                p.wait()
                
            finally:
                self.__camera_lock.release()
            
            camera_configs[name].current = value
    
            self.__settings_manager.set("camera configs",camera_configs)
        
        finally:
            self.__settings_manager.release(glob_vars)
        
    ##############################################################################################     
    
    def isConnected(self):
        self.__camera_lock.acquire()
        
        try:
            #run gphoto function in separate process
            p = Popen("gphoto2 --auto-detect",shell=True,stdout=PIPE,stderr=PIPE)
            
            out = string.join(p.stdout.readlines())
            outerr = string.join(p.stderr.readlines())
            
            #wait for process to finish
            p.wait()
            
        finally:
            self.__camera_lock.release()
        
        if p.returncode != 0:
            raise RuntimeError,"GPhoto2 Error: failed to auto detect\n"+outerr
 
        #split output into lines
        lines = out.split("\n")
        
        if len(lines) <=3:
            return False
        else:
            return True
        
    ##############################################################################################            
    
    def exit(self):
        """
        Runs any tidy-up processes associated with the cameraManager and returns.
        """
        return
    
    ##############################################################################################            
    
    def __getCameraConfigs(self):
        """
        Returns a dictionary containing cameraConfig objects for all of the possible camera configs.
        The keys are the short names of the configs.
        """
        current_configs = {}
        self.__camera_lock.acquire()
        
        try:
            #get list of possible configs for camera
            #run gphoto function in separate process
            p = Popen("gphoto2 --list-config",shell=True,stdout=PIPE)
            
            out = string.join(p.stdout.readlines())
            
            #wait for process to finish
            p.wait()
        
        finally:
            self.__camera_lock.release()
        
        #split output into lines
        lines = out.split("\n")
        
        for config in lines:
            #skip blank lines
            if config.isspace() or config == "":
                continue
            
            #get short name of config
            split = config.split("/")
            name = split[len(split)-1].lstrip().rstrip()
            
            current_configs[name] = self.getConfig(config)
                    
        return current_configs
            
    ############################################################################################## 
    
    def getConfig(self,name):
        """
        Wrapper function for gphoto2's --get-config function. Returns a cameraConfig object.
        The name argument should be a string specifying the name of the config, e.g. "exptime"
        """
        
        
        values = {}
        
        #get values for particular config
        self.__camera_lock.acquire()
        
        try:
            #run gphoto function in separate process
            p = Popen("gphoto2 --get-config "+name,shell=True,stdout=PIPE)
            
            out = string.join(p.stdout.readlines()) 
            
            p.wait()
            
        finally:
            self.__camera_lock.release()
        
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
    
    
    
    
        