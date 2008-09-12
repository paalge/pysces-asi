import ephem
import datetime,time,math
import captureMode,dailyPro
import OTFPro

#define the functions used in the settings file
##############################################################################################

def Time(time_string):
    """
    Returns a time object built from a string of format "%H:%M:%S". This is a macro-type function
    which is run when the schedule tests are evaluated.
    """
    
    d=datetime.datetime.strptime(time_string,"%H:%M:%S")
    return d.time()

##############################################################################################

def Date(date_string):
    """
    Returns a date object built from a string of format "%d:%m:%y". This is a macro-type function
    which is run when the schedule tests are evaluated.
    """
    d=datetime.datetime.strptime(time_string,"%d:%m:%y")
    return d.date()

##############################################################################################

class scheduler:
    """
    The scheduler class is responsible for selecting and then running the correct capture mode.
    The selection is made by evaluating the tests defined in the schedule (in the settings file).
    """
    def __init__(self,settings_manager):

        self.__settings_manager = settings_manager
        self.__running = False
        self.__current_capture_mode = None
        
        #create an pyephem observer object for calculating sun and moon angles
        self.__createObservatory(self.__settings_manager.get(["latitude","longitude","altitude"]))
        
        #register callback functions for observatory parameters
        self.__settings_manager.register("latitude",self.__createObservatory,["latitude","longitude","altitude"])
        self.__settings_manager.register("longitude",self.__createObservatory,["latitude","longitude","altitude"])
        self.__settings_manager.register("altitude",self.__createObservatory,["latitude","longitude","altitude"])    

    ##############################################################################################        
   
    def start(self):
        """
        Starts the scheduler running. Basically it enters an infinte loop of checking the schedule
        to see which capture mode should be run. 
        """
        
        if self.__running:
            raise RunTimeError,"Scheduler is already running!"
            
        self.__running = True
        
        #create sun and moon objects
        self.__sun,self.__moon = ephem.Sun(),ephem.Moon()
        
        #work out which capture mode should be running now
        while self.__running:
            
            #find out which capture mode should be running now
            capture_mode_to_run = self.__evaluateSchedule()
            
            if capture_mode_to_run != self.__current_capture_mode:
                #the capture mode has changed and should be updated
                if eval(test) and capture_mode != current_mode_name:
                    
                    if current_mode_name != None:
                        self.__current_capture_mode.exit()
                        
                    capture_settings = glob_vars["capture modes"][capture_mode]
                    
                    self.__current_capture_mode = captureMode.captureMode(capture_settings,self.__camera_manager)
                    self.__settings_manager.set("current capture mode",self.__current_capture_mode.name())
                    self.__settings_manager.set("output","scheduler> Starting \""+self.__current_capture_mode.name()+"\" capture mode")
                    self.__current_capture_mode.start()
                    flag = True
                    break
                
                elif eval(test) and capture_mode == current_mode_name:
                    #current mode is still valid so break out of checking loop
                    flag = True
                    break
                
            if (not flag) and self.__current_capture_mode != None:
                self.__current_capture_mode.exit()
                self.__current_capture_mode = None
                self.__settings_manager.set("output","scheduler> Set capture mode to None")
                self.__settings_manager.set("output","scheduler> Waiting.....")
  
            time.sleep(5)
        
    ##############################################################################################          
      
    def exit(self):
        """
        Terminates the current capture mode, the on-the-fly processing thread and the daily processing
        thread and returns.
        """
        self.__running = False
        if self.__current_capture_mode != None:
            self.__current_capture_mode.exit()

    ##############################################################################################    
    
    def __createObservatory(self,glob_vars):
        """
        Creates a pyephem observer object based on the observatory data provided in the settings 
        file.
        """
        obs = ephem.Observer()

        #create observer object
        obs.lat = glob_vars["latitude"]
        obs.long = glob_vars["longitude"]
        obs.elevation = glob_vars["altitude"]

        self.__observatory = obs
        
    ############################################################################################## 
    
    def __evaluateSchedule(self):
        """
        Evaluates the schedule and returns the name of the capture mode that should be currently
        being run. If no capture mode should be run then it returns None.
        """
        
        #set date and time to the time now (in UT)
        now = datetime.datetime.utcnow()
        DATE = now.date()
        TIME = now.time()       
        
        #compute sun and moon parameters
        self.__observatory.date = now.strftime("%Y/%m/%d %H:%M:%S")
        self.__sun.compute(self.__observatory)
        self.__moon.compute(self.__observatory)
        
        #set sun and moon angles
        SUN_ANGLE = math.degrees(sun.alt)
        MOON_ANGLE = math.degrees(moon.alt)
        MOON_PHASE = float(moon.moon_phase * 100.0)
        
        #get the schedule from the global variables
        schedule = self.__settings_manager.get(["schedule"])["schedule"]

        #evaluate each test in the schedule and return the name of the capture mode that should be run
        for test,capture_mode_name in schedule.items():
            if eval(test):
                return capture_mode_name
        #otherwise return None
        return None
    
    ############################################################################################## 
    
    def __updateDay(self):
        """
        Updates the day global variable, causing the directory structure to be updated
        by the host manager via a callback function
        """            
        if self.__settings_manager.get(['day'])['day'] != now.strftime("%j"):
            self.__settings_manager.set({'day':now.strftime("%j")})
        
##############################################################################################       
       
        
        