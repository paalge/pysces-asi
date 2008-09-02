import threading,os
import shutil

#define a dictionary relating output types to processing functions



class OTFPro:
    
    def __init__(self,settings_manager):
        self.__settings_manager = settings_manager
        self.__worker_threads = []
        self.__settings_manager.register("most recent images", self.start)
        
        
        
    ##############################################################################################
    
    def start(self):
        #Find out what outputs are required for the current capture mode
        glob_vars = self.__settings_manager.grab(["current capture mode","capture modes","output types"])
        
        try:
            ccm = glob_vars["capture modes"][glob_vars["current capture mode"]]
            
            for output_name in ccm["outputs"]:
            required_outputs["output_name"] = ccm["outputs"]
        finally:
            self.__settings_manager.release(glob_vars)
        
        #create a list of all the settings that we need to create the outputs
        host_settings = ["output folder",]
        settings_for_PASKIL = ["latitude","longitude","magnetic_bearing","lens_projection","fov_angle","camera_rotation","Capture Time"]
        
        #create thread specific data
        local_data = threading.local()
        
        #copy variables from the settings manager
        #outputs
        #local_data['required_outputs'] = 
        
        #create thread to run on-the-fly processing operations
        otf_thread = processing.Process(target=self.__run,args=(local_data,))
        
        #add thread to list, and remove any threads that have finished
        for thread in self.__worker_threads:
            if not thread.isAlive():
                self.__worker_threads.remove(thread)
        
        self.__worker_threads.append(otf_thread)
        
        #check how many otf threads are running - shouldn't be more than one, but we'll allow up to five
        if len(self.__worker_threads) > 5:
            raise RuntimeError, "Backlog of OTF threads  - giving up on this one!"
    
        #run OTFPro thread
        otf_thread.start()
    
    ##############################################################################################
    
    def __run(self,local_data):
        """
        Creates a child process to deal with creating the outputs. This allows parallel processing of the images 
        (which is not achieveable using Python threads). The stdout from the child process is monitored and 
        passed on to the settings manager's 'output' variable. This process is perhaps slightly confusing
        since it is the OTFPro module - i.e. this one! which is spawned as a child process.
        """
        glob_vars = self.__settings_manager.grab(["most recent images","output folder"])

        try:
            self.__settings_manager.set("output","OTFPro> Copying image out of tmp dir")
            shutil.copy(glob_vars['most recent images']['jpeg'],glob_vars['output folder'] +"/Images/"+os.path.split(glob_vars['most recent images']['jpeg'])[1])
            
            for file in glob_vars['most recent images'].values():
                os.remove(file)
        finally:
            self.__settings_manager.release(glob_vars)

    ##############################################################################################

    def join(self):
        """
        Blocks until all OTFPro threads have finished
        """
        self.__settings_manager.set("output","OTFPro> Waiting for child processes to finish, this may take some time")
        for thread in self.__worker_threads:
            thread.join()
    
    ##############################################################################################
    
    def copyRawImages(self):
        glob_vars = self.__settings_manager.grab(["most recent images","output folder"])
        print "Inside new process!"
        try:
            self.__settings_manager.set("output","OTFPro> Copying image out of tmp dir")
            shutil.copy(glob_vars['most recent images']['jpeg'],glob_vars['output folder'] +"/Images/"+os.path.split(glob_vars['most recent images']['jpeg'])[1])
            
            for file in glob_vars['most recent images'].values():
                os.remove(file)
        finally:
            self.__settings_manager.release(glob_vars)
    
        return None
    
    ##############################################################################################
##############################################################################################





 
        