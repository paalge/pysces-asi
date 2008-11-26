import threading
import multiprocessing

import settings_manager,scheduler
from multitask import ThreadQueueBase,ThreadTask


class MainBox:
    
    def __init__(self):
        self.__running = False
        
        #create settings manger object)
        self.__settings_manager = settings_manager.SettingsManager()
        
        #create scheduler object
        self.__scheduler = scheduler.Scheduler(self.__settings_manager)
        
        self.__capture_thread = None
        
    ##############################################################################################  
         
    def start(self):
        if self.__capture_thread == None:
            #create task
            self.__capture_thread = threading.Thread(target=self.__scheduler.start)
            self.__capture_thread.start()    
        else:
            raise RuntimeError, "Cannont start more than one scheduler!"
        
    ############################################################################################## 
    
    def stop(self):
        
        #if a scheduler is running then kill it
        if self.__capture_thread != None:
            #kill scheduler and wait for capture thread to return
            self.__settings_manager.set({"output":"MainBox> Killing scheduler"})
            self.__scheduler.exit()
            self.__capture_thread.join()

            self.__capture_thread = None
    
    ##############################################################################################     
              
    def exit(self):
        
        self.stop()    

        #kill settings manager
        self.__settings_manager.set({"output":"MainBox> Killing settings_manager"})

        self.__settings_manager.exit()
        
    ##############################################################################################         
    
    def setVar(self,names):
        self.__settings_manager.set(names)
        
    ############################################################################################## 
        
    def register(self,name,callback,globals_):
        self.__settings_manager.register(name,callback,globals_)
           
    ############################################################################################## 
       
    def getVar(self,names):
        return self.__settings_manager.get(names)
    
    ############################################################################################## 
##############################################################################################         

#if the script is being run in non-gui mode then run it!        
if __name__ == '__main__':
    
    def output(s):
        print s["output"]
    
    main_box = MainBox()
    #signal.signal(signal.SIGINT,main_box.exit)
    
    main_box.register("output",output,["output"])
    
    #run!
    main_box.start()
    main_box._MainBox__capture_thread.join()
    
    