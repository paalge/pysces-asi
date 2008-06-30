import ephem
import datetime,time,math
import captureMode,dailyPro

#define the functions used in the settings file
def Time(time_string):
    d=datetime.datetime.strptime(time_string,"%H:%M:%S")
    return d.time()

def Date(date_string):
    d=datetime.datetime.strptime(time_string,"%d:%m:%y")
    return d.date()



class scheduler:
    
    def __init__(self,settings_manager,camera_manager):
        self.__camera_manager = camera_manager
        self.__settings_manager = settings_manager
        self.__running = False
        self.__current_capture_mode = None
    
        #create a daily processing object
        self.__dailyPro = dailyPro.dailyPro(self.__settings_manager)
        
        #create an observatory object for use with the Ephemeris library
        try:
            self.__settings_manager.create("observatory",None)
        except ValueError:
            pass
        
        self.__createObservatory()
        
        self.__settings_manager.register("latitude",self.__createObservatory)
        self.__settings_manager.register("longitude",self.__createObservatory)
        self.__settings_manager.register("altitude",self.__createObservatory)    

        
   
    def start(self):
        if self.__running:
            raise RunTimeError,"Scheduler is already running!"
            
        self.__running = True
        
        #start running daily processing thread (this also updates the 'day' variable)
        self.__dailyPro.start()
        
        #create sun and moon objects
        sun,moon = ephem.Sun(),ephem.Moon()
        
        #work out which capture mode should be running now
        while self.__running:
            
            #set date, time and sun,moon angles
            now = datetime.datetime.now()
            DATE = now.date()
            TIME = now.time()
            obs = self.__settings_manager.grab("observatory")
            obs.date = now.strftime("%Y/%m/%d %H:%M:%S")
            sun.compute(obs)
            moon.compute(obs)
            SUN_ANGLE = math.degrees(sun.alt)
            MOON_ANGLE = math.degrees(moon.alt)
            MOON_PHASE = float(moon.moon_phase * 100.0)

            if self.__current_capture_mode != None:
                mode_name = self.__current_capture_mode.name()
            else:
                mode_name = None
                
            schedule = self.__settings_manager.grab("schedule")
            for test,capture_mode in schedule.items():
                if eval(test) and capture_mode != mode_name:
                    if mode_name != None:
                        self.__current_capture_mode.exit()
                    capture_settings = self.__settings_manager.grab("capture modes")[capture_mode]
                    self.__settings_manager.release("capture modes")
                    self.__current_capture_mode = captureMode.captureMode(capture_settings,self.__settings_manager,self.__camera_manager)
                    self.__current_capture_mode.start()
   
                elif capture_mode == mode_name and not eval(test):
                    self.__current_capture_mode.exit()
                    self.__current_capture_mode = None
            
            
                
            self.__settings_manager.release("observatory")
            self.__settings_manager.release("schedule")    
            time.sleep(5)
        
        
    def exit(self):
        self.__running = False
        if self.__current_capture_mode != None:
            self.__current_capture_mode.exit()
            self.__current_capture_mode.waitForOTF()
        self.__dailyPro.exit()
    
    
    def __createObservatory(self):
        #get globals
        obs = ephem.Observer()
        lat = self.__settings_manager.grab("latitude")
        long = self.__settings_manager.grab("longitude")
        alt = self.__settings_manager.grab("altitude")
        
        #create observer object
        obs.lat = lat
        obs.long = long
        obs.elevation = alt
        
        self.__settings_manager.set("observatory",obs)
        
        #release globals
        self.__settings_manager.release("latitude")
        self.__settings_manager.release("longitude")
        self.__settings_manager.release("altitude")
        
        
        
        
        
        
        