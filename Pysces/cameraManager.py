from subprocess import Popen,PIPE
from threading import Lock
import string,datetime,time

class cameraManager:
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
            pass
        
        self.__settings_manager.set("camera configs", self.__getCameraConfigs())
        
        
        #set callbacks for camera configs
        self.__settings_manager.register("iso",self.updateConfigs)
        self.__settings_manager.register("f-number",self.updateConfigs)
        self.__settings_manager.register("exptime",self.updateConfigs)
        self.__settings_manager.register("imgsize",self.updateConfigs)
        self.__settings_manager.register("whitebalance",self.updateConfigs)
        self.__settings_manager.register("focusmode",self.updateConfigs)
        
        self.__settings_manager.register("unprocessed_raw",self.updateImgs)
        self.__settings_manager.register("unprocessed_jpeg",self.updateImgs)
        self.__settings_manager.register("PASKIL_png",self.updateImgs)
        self.__settings_manager.register("d_quicklook",self.updateImgs)
        self.__settings_manager.register("d_map_projection",self.updateImgs)
        self.__settings_manager.register("d_movie",self.updateImgs)
        
    ############################################################################################## 
    
    def updateImgs(self):
        get_raw = self.__settings_manager.grab("unprocessed_raw")
        jpg0 = self.__settings_manager.grab("unprocessed_jpeg")
        jpg1 = self.__settings_manager.grab("PASKIL_png")
        jpg2 = self.__settings_manager.grab("d_quicklook")
        jpg3 = self.__settings_manager.grab("d_map_projection")
        jpg4 = self.__settings_manager.grab("d_movie")
        
        if jpg0 or jpg1 or jpg2 or jpg3 or jpg4:
            get_jpg = True
        
        if get_jpg and get_raw:
            self.setConfig("imgquality", "NEF+Normal")
        elif get_raw:
            self.setConfig("imgquality", "NEF (Raw)")
        else:
            self.setConfig("imgquality", "JPEG Normal")
        
        self.__settings_manager.release("unprocessed_raw")
        self.__settings_manager.release("unprocessed_jpeg")
        self.__settings_manager.release("PASKIL_png")
        self.__settings_manager.release("d_quicklook")
        self.__settings_manager.release("d_map_projection")
        self.__settings_manager.release("d_movie")
        
    ##############################################################################################         
    
    def captureImage(self):
        self.__camera_lock.acquire()
        try:

            configs = self.__settings_manager.grab("camera configs")

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

            tmp_dir = self.__settings_manager.grab("tmp dir")
            filename_format = self.__settings_manager.grab("filename_format")
            
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
            
            if not flag:
                raise RuntimeError,"Gphoto2 Error: Unable to download image(s)"
            
            #otherwise get the images
            if get_raw or get_jpeg:
                self.__settings_manager.set("output", "cameraManager> Downloading image(s)")
                p = Popen("gphoto2 -P --folder="+active_folder+" --filename=\""+tmp_dir+"/"+time_of_capture.strftime(filename_format)+".%C\"",shell=True)
                p.wait()
            
                if p.returncode != 0:
                    raise RuntimeError,"Gphoto2 Error: Unable to download the image(s)"        
            
            #delete images from camera card
            p = Popen("gphoto2 -D --folder="+active_folder,shell=True)
            p.wait()
            
            if p.returncode != 0:
                raise RuntimeError,"Gphoto2 Error: Unable to delete the image(s) from camera card" 
            
            self.__settings_manager.release("camera configs")
        finally:
            self.__settings_manager.release("tmp dir")
            self.__camera_lock.release()
        
        if get_raw and get_jpeg:
            return tmp_dir+"/"+time_of_capture.strftime(filename_format)+".JPG",tmp_dir+"/"+time_of_capture.strftime(filename_format)+".NEF"
        elif get_raw:
            return None,tmp_dir+"/"+time_of_capture.strftime(filename_format)+".NEF"
        elif get_jpeg:
            return tmp_dir+"/"+time_of_capture.strftime(filename_format)+".JPG",None
        else:
            return None,None
    
    ############################################################################################## 
    
    def updateConfigs(self):
        camera_configs = self.__settings_manager.grab("camera configs")
        iso = self.__settings_manager.grab("iso")
        f_number = self.__settings_manager.grab("f-number")
        exptime = self.__settings_manager.grab("exptime")
        imgsize = self.__settings_manager.grab("imgsize")
        whitebalance = self.__settings_manager.grab("whitebalance")
        focusmode = self.__settings_manager.grab("focusmode")
        
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
        
        self.__settings_manager.release("camera configs")
        self.__settings_manager.release("iso")
        self.__settings_manager.release("f-number")
        self.__settings_manager.release("exptime")
        self.__settings_manager.release("imgsize")
        self.__settings_manager.release("whitebalance")
        self.__settings_manager.release("focusmode")
     
    ##############################################################################################     
    
    def setConfig(self,name,value):
        
        self.__settings_manager.set("output","cameraManager> Setting "+name+" to "+value)
        
        self.__camera_lock.acquire()
        camera_configs = self.__settings_manager.grab("camera configs")    
        
        config = camera_configs[name]
        
        value_index = config.values[value]
        
        #run gphoto function in separate process
        p = Popen("gphoto2 --set-config "+str(name)+"="+value_index,shell=True)
        
        #wait for process to finish
        p.wait()
        self.__camera_lock.release()
        
        camera_configs[name].current = value

        self.__settings_manager.set("camera configs",camera_configs)
        self.__settings_manager.release("camera configs")
        
    ##############################################################################################     
    
    def isConnected(self):
        self.__camera_lock.acquire()
        
        #run gphoto function in separate process
        p = Popen("gphoto2 --auto-detect",shell=True,stdout=PIPE,stderr=PIPE)
        
        out = string.join(p.stdout.readlines())
        outerr = string.join(p.stderr.readlines())
        
        #wait for process to finish
        p.wait()
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
        return
    
    ##############################################################################################            
    
    def __getCameraConfigs(self):
        current_configs = {}
        self.__camera_lock.acquire()
        
        #get list of possible configs for camera
        #run gphoto function in separate process
        p = Popen("gphoto2 --list-config",shell=True,stdout=PIPE)
        
        out = string.join(p.stdout.readlines())
        
        #wait for process to finish
        p.wait()
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
        values = {}
        
        #get values for particular config
        self.__camera_lock.acquire()
        
        #run gphoto function in separate process
        p = Popen("gphoto2 --get-config "+name,shell=True,stdout=PIPE)
        
        out = string.join(p.stdout.readlines()) 
        
        p.wait()
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
    def __init__(self,label,current,values):
        self.label = label
        self.current = current
        self.values = values.copy()    
    
    
    
    
        