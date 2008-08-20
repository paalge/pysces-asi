import threading,os
import shutil
#from PASKIL import allskyImage

#define a dictionary relating output types to processing functions



class OTFPro:
    
    def __init__(self,settings_manager):
        self.__settings_manager = settings_manager
        self.__worker_threads = []
        self.__settings_manager.register("most recent images", self.start)
        
    ##############################################################################################
    
    def start(self):
        #create thread specific data
        local_data = threading.local()
        
        #copy variables from the settings manager
        #outputs
        
        
        #create thread to run on-the-fly processing operations
        otf_thread = threading.Thread(target=self.__run,args=(local_data,))
        
        #add thread to list, and remove any threads that have finished
        for thread in self.__worker_threads:
            if not thread.isAlive():
                self.__worker_threads.remove(thread)
        
        self.__worker_threads.append(otf_thread)
    
        #run OTFPro thread
        otf_thread.start()
    
    ##############################################################################################
    
    def __run(self,local_data):
        glob_vars = self.__settings_manager.grab(["most recent images","output folder"])

        try:
            shutil.copy(glob_vars['most recent images']['JPEG'],glob_vars['output folder'] +"/Images/"+os.path.split(glob_vars['most recent images']['JPEG'])[1])
            
            for file in glob_vars['most recent images'].values():
                os.remove(file)
        finally:
            self.__settings_manager.release(glob_vars)

    ##############################################################################################

    def join(self):
        """
        Blocks until all OTFPro threads have finished
        """
        for thread in self.__worker_threads:
            thread.join()
    
    ##############################################################################################
        