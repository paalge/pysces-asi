import OTFPro
import threading,datetime,time

class captureMode:
    
    def __init__(self,settings,settings_manager,camera_manager):
        self.__settings = settings
        self.__settings_manager = settings_manager
        self.__camera_manager = camera_manager
        self.__stay_alive = False
        self.__running = False
        self.__OTFPro = OTFPro.OTFPro(self.__settings_manager)
        self.__capture_thread = None

    ##############################################################################################
        
    def start(self):
        if self.__running:
            raise RunTimeError, "Capture thread is already running"
        
        self.__stay_alive = True
        self.__running = True
        
        #set global variables for this capture mode - callback functions will ensure that the camera is setup
        #self.__settings_manager.setGroup(self.__settings)
        
        #create capture thread
        self.__capture_thread = threading.Thread(target=self.__run,args=())
        
        #run capture thread
        self.__capture_thread.start()

    ##############################################################################################
    
    def __run(self):
        while self.__stay_alive:
            start_time = datetime.datetime.now()
            #capture image
            self.__camera_manager.captureImage()
            
            #run OTFPro thread
            #self.__OTFPro.start()
            
            #wait remaining delay time
            print "Entering wait loop"
            while self.__stay_alive and datetime.datetime.now() - start_time < datetime.timedelta(seconds=self.__settings["delay"]):
                time.sleep(0.5)
                
    ##############################################################################################        
    
    def name(self):
         return self.__settings['name']
        
    ##############################################################################################        
        
    def exit(self):
        self.__stay_alive = False
        if self.__capture_thread != None:
            self.__capture_thread.join()
        self.__running = False
        
    ##############################################################################################    

    def waitForOTF(self):
        self.__OTFPro.join()
        
    ##############################################################################################
##############################################################################################    