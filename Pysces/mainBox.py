import settingsManager,scheduler
from multitask import taskQueueBase,Task
import sys,time


class mainBox(taskQueueBase):
    
    def __init__(self):
        self.__running = False
        
        #create settings manger object
        self.__settings_manager = settingsManager.settingsManager()
        
        #create scheduler object
        self.__scheduler = scheduler.scheduler(self.__settings_manager)
        
        self.__capture_task = None
        
        #start mainBox worker thread
        taskQueueBase.__init__(self)
        
    ##############################################################################################  
         
    def start(self):
        if self.__capture_task == None:
            #create task
            self.__capture_task = Task(self.__scheduler.start)
            
            #note that this task will not complete until the scheduler has exited so mainBox will not
            #pull any more tasks out of the queue until exit() is called by an external thread.
            #This is a bit different to other taskQueue classes used in the program, where most public
            #methods simply place a task into the queue. mainBox's public methods can all be executed 
            #asyncronously (since the syncronisation is done in the settingsManager) and they are therefore
            #all executed by the calling thread (except for start()).
            
            #commit task
            self.commitTask(self.__capture_task)
            
        else:
            raise RunTimeError, "Cannont start more than one scheduler!"
        
    ############################################################################################## 
    
    def stop(self):
        
        #if a scheduler is running then kill it
        if self.__capture_task != None:
            #kill scheduler and wait for capture thread to return
            self.__settings_manager.set({"output":"mainBox> Killing scheduler"})
            self.__scheduler.exit()
            self.__capture_task.result() #this blocks until the scheduler has exited
            self.__capture_task = None
    
    ##############################################################################################     
              
    def exit(self):
        
        #if a scheduler is running then kill it
        if self.__capture_task != None:
            #kill scheduler and wait for capture thread to return
            self.__settings_manager.set({"output":"mainBox> Killing scheduler"})

            self.__scheduler.exit()
            try:
                self.__capture_task.result() #this blocks until the scheduler has exited
            except:
                #ignore any exceptions that were raised due to killing the scheduler
                #they were probably caused by gphoto (which seems to also receive 
                #the keyboard interrupt signal - strange?!). It doesn't matter if that 
                #part of the program exits in a messy way - each class still gets to execute
                #its own exit method.
                pass

            self.__capture_task = None    

        #kill settings manager
        self.__settings_manager.set({"output":"mainBox> Killing settings_manager"})
        self.__settings_manager.exit()
        
        #kill the mainBox worker thread
        taskQueueBase.exit(self)
        
    ##############################################################################################         
    
    def setVar(self,names):
        self.__settings_manager.set(names)
        
    ############################################################################################## 
        
    def register(self,name,callback,globals):
           self.__settings_manager.register(name,callback,globals)
           
    ############################################################################################## 
       
    def getVar(self,names):
        return self.__settings_manager.get(names)
    
    ############################################################################################## 
##############################################################################################         


#if the script is being run in non-gui mode then run it!        
if __name__ == '__main__':
    
    def output(s):
        print s["output"]
    
    main_box = mainBox()
    main_box.register("output",output,["output"])
    
    #run!
    main_box.start()
    
    #wait to be stopped. Unfortunately, KeyboardInterrupt doesn't seem to work on a blocking join()
    #so instead we use the sleep function and keep repeating it until interrupted
    try:
        while True:
            time.sleep(3000000)
    except KeyboardInterrupt:
        print "Pysces> Closing capture thread, please wait...."
        main_box.exit()
          