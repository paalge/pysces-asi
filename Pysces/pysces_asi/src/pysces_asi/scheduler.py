#Copyright (C) Nial Peters 2009
#
#This file is part of pysces_asi.
#
#pysces_asi is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pysces_asi is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pysces_asi.  If not, see <http://www.gnu.org/licenses/>.
"""
The scheduler module provides a Scheduler class which is responsible for evaluating
the schedule defined in the settings file and selecting the capture mode that should
be running. The module also defines some 'macro-like' functions which are used by the
eval() function to resolve dates and times specified in the schedule in the settings
file. 
"""

import datetime
import time
import math

import ephem

import capture
from data_storage_classes import CaptureMode

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

class Scheduler:
    """
    The scheduler class is responsible for selecting the correct capture mode. The
    selection is made by evaluating the tests defined in the schedule (in the 
    settings file). Each time the capture mode changes, a new CaptureMode object is
    passed to the capture manager. If no test evaluate true (i.e. no capture mode
    should be running) then None is passed to the capture manager.
    """
    def __init__(self,settings_manager):

        self.__settings_manager = settings_manager
        
        self.__sun = None
        self.__moon = None
        self.__observatory = None
        
        self.__running = False
        self.__current_capture_mode_name = None
        self.__capture_manager = None
        
        #create an pyephem observer object for calculating sun and moon angles
        self.__create_observatory(self.__settings_manager.get(["latitude","longitude","altitude"]))
        
        #register callback functions for observatory parameters
        self.__settings_manager.register("latitude",self.__create_observatory,["latitude","longitude","altitude"])
        self.__settings_manager.register("longitude",self.__create_observatory,["latitude","longitude","altitude"])
        self.__settings_manager.register("altitude",self.__create_observatory,["latitude","longitude","altitude"])    
        
    ##############################################################################################        
   
    def start(self):
        """
        Starts the scheduler running. Basically it enters an infinte loop of checking the schedule
        to see which capture mode should be run. 
        """
        try:
            if self.__running:
                raise RuntimeError,"Scheduler is already running!"
            self.__running = True
            
            try:        
                self.__capture_manager = capture.CaptureManager(self.__settings_manager)
            except Exception,ex:
                raise ex
            #create sun and moon objects
            self.__sun = ephem.Sun()
            self.__moon = ephem.Moon()
            
            self.__settings_manager.set({"output":"Scheduler> Waiting....."})
            
            #work out which capture mode should be running now
            while self.__running:
                
                #find out which capture mode should be running now
                capture_mode_to_run_name = self.__evaluate_schedule()
                            
                if capture_mode_to_run_name != self.__current_capture_mode_name:
                    #the capture mode has changed and should be updated               
                    if capture_mode_to_run_name == None:
                        #no capture mode should be running - pass this information to the captureManager
                        self.__capture_manager.commit_task(None)
                        
                        #print status messages
                        self.__settings_manager.set({"output":"Scheduler> Set capture mode to None"})
                        self.__settings_manager.set({"output":"Scheduler> Waiting....."})
                        self.__current_capture_mode_name = capture_mode_to_run_name
                        
                    else:
                        #build a captureMode object from the data stored in the settings manager 
                        #note that the captureMode constructor takes care of building outputTypes,
                        #and the outputTypes constructor takes care of building imageTypes
                        glob_vars = self.__settings_manager.get(["capture modes","image types","output types"])
                        capture_mode_to_run = CaptureMode(glob_vars["capture modes"][capture_mode_to_run_name],glob_vars["image types"],glob_vars["output types"])
    
                        #pass capture mode to captureManager
                        self.__capture_manager.commit_task(capture_mode_to_run)
                        self.__settings_manager.set({"output":"Scheduler> Starting \""+capture_mode_to_run_name+"\" capture mode"})
                    
                        self.__current_capture_mode_name = capture_mode_to_run_name
                
                #wait for a short while before re-evaluating the schedule
                time.sleep(5)
        finally:
            self.exit()
    ##############################################################################################          
      
    def exit(self):
        """
        Terminates the CaptureManager and returns
        """
        if not self.__running:
            return
        
        self.__running = False
        try:
            self.__capture_manager.exit()
        except AttributeError:
            pass
        
        self.__current_capture_mode_name = None
        
    ##############################################################################################    
    
    def __create_observatory(self,glob_vars):
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
    
    def __evaluate_schedule(self):
        """
        Evaluates the schedule and returns the name of the capture mode that should be currently
        being run. If no capture mode should be run then it returns None.
        """
        
        #set date and time to the time now (in UT)
        now = datetime.datetime.utcnow()
        DATE = now.date() #used in eval() call below
        TIME = now.time() #used in eval() call below      
        
        #compute sun and moon parameters
        self.__observatory.date = now.strftime("%Y/%m/%d %H:%M:%S")
        self.__sun.compute(self.__observatory)
        self.__moon.compute(self.__observatory)
        
        #set sun and moon angles - these are used in the eval() call below
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
       
        
        