import ephem
import datetime,time,math
from threading import Event
from dataStorageClasses import captureMode
import captureManager

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
    d=datetime.datetime.strptime(date_string,"%d/%m/%y")
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
        self.__current_capture_mode_name = None
        
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
        
        
        self.__capture_manager = captureManager.captureManager(self.__settings_manager)

        
        #create sun and moon objects
        self.__sun,self.__moon = ephem.Sun(),ephem.Moon()
        
        self.__settings_manager.set({"output":"scheduler> Waiting....."})
        
        #work out which capture mode should be running now
        while self.__running:
            
            #find out which capture mode should be running now
            capture_mode_to_run_name = self.__evaluateSchedule()
            
            
            if capture_mode_to_run_name != self.__current_capture_mode_name:
                #the capture mode has changed and should be updated
                
                
                
                if capture_mode_to_run_name == None:
                    #no capture mode should be running - pass this information to the captureManager
                    self.__capture_manager.commitTask(None)
                    
                    self.__settings_manager.set({"output":"scheduler> Set capture mode to None"})
                    self.__settings_manager.set({"output":"scheduler> Waiting....."})
                    self.__current_capture_mode_name = capture_mode_to_run_name
                    
                else:
                
                    #build a captureMode object from the data stored in the settings manager 
                    #note that the captureMode constructor takes care of building outputTypes,
                    #and the outputTypes constructor takes care of building imageTypes
                    glob_vars = self.__settings_manager.get(["capture modes","image types","output types"])
                    capture_mode_to_run = captureMode(glob_vars["capture modes"][capture_mode_to_run_name],glob_vars["image types"],glob_vars["output types"])

                    #pass capture mode to captureManager
                    self.__capture_manager.commitTask(capture_mode_to_run)
                    self.__settings_manager.set({"output":"scheduler> Starting \""+capture_mode_to_run_name+"\" capture mode"})
                
                    self.__current_capture_mode_name = capture_mode_to_run_name
            
            #wait for a short while before re-evaluating the schedule
            time.sleep(5)
        
    ##############################################################################################          
      
    def exit(self):
        """
        Terminates the captureManager and returns
        """
        self.__running = False
        try:
            self.__capture_manager.exit()
        except AttributeError:
            pass

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
        SUN_ANGLE = math.degrees(self.__sun.alt)
        MOON_ANGLE = math.degrees(self.__moon.alt)
        MOON_PHASE = float(self.__moon.moon_phase * 100.0)
        
        #get the schedule from the global variables
        schedule = self.__settings_manager.get(["schedule"])["schedule"]

        #evaluate each test in the schedule and return the name of the capture mode that should be run
        for test,capture_mode_name in schedule.items():
            if eval(test):
                return capture_mode_name
        #otherwise return None
        return None
    
    ##############################################################################################     
##############################################################################################       
       
        
        