import settingsManager,cameraManager,hostManager,scheduler
import threading,sys


class mainBox:
    
    def __init__(self):
        self.__running = False
        
        #create settings manger
        manager = settingsManager.sharedSettings()
        manager.start()
        self.__settings_manager = manager.sharedSettingsManager()
        
        #create camera manager
        self.__camera_manager = cameraManager.cameraManager(self.__settings_manager)
        
        #create host manager
        self.__host_manager = hostManager.hostManager(self.__settings_manager)
        
        #create scheduler
        self.__scheduler = scheduler.scheduler(self.__settings_manager,self.__camera_manager)
        
    ##############################################################################################  
         
    def start(self):
        if not self.__running:
            self.__host_manager.start()
            
            #create new thread to run script
            self.__capture_thread = threading.Thread(target=self.__scheduler.start,args=())
            
            #run it!
            self.__capture_thread.start()
            
            self.__running = True
        
        else:
            raise RunTimeError, "Cannont start more than one capture thread!"
        
    ############################################################################################## 
              
    def exit(self):
        
        #kill scheduler and wait for capture thread to return
        self.__settings_manager.set("output", "mainBox> Killing scheduler")
        self.__scheduler.exit()
        self.__capture_thread.join()

        #kill host manager
        self.__settings_manager.set("output","mainBox> Killing host_manager")
        self.__host_manager.exit()
        
        #kill camera manager
        self.__settings_manager.set("output","mainBox> Killing camera_manager")
        self.__camera_manager.exit()
        
        #kill settings manager
        self.__settings_manager.set("output","mainBox> Killing settings_manager")
        self.__settings_manager.exit()
        
        self.__running = False
        
    ##############################################################################################         
    
    def setVar(self,name,value):
        self.__settings_manager.set(name,value)
        
    ############################################################################################## 
        
    def register(self,name,callback):
           self.__settings_manager.register(name,callback)
           
    ############################################################################################## 
       
    def grabVar(self,names):
        return self.__settings_manager.grab(names)
    
    ############################################################################################## 
        
    def releaseVar(self,name):
        self.__settings_manager.release(name)
        
    ##############################################################################################         
        
        
        


#if the script is being run in non-gui mode then run it!        
if __name__ == '__main__':
    
    def output(s):
        print s
    
    main_box = mainBox()
    main_box.register("output",output)
    
    #run!
    main_box.start()
    
    #wait to be stopped
    try:
        while (True):
            pass
    except KeyboardInterrupt:
        print "Pysces> Closing capture thread, please wait...."
        main_box.exit()
        
        sys.exit()
        