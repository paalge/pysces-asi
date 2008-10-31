"""
The persist module provides a PersistantStorage class, which is used by the SettingsManager
class to store variables that are not in the settings file. Their values are loaded
again when the program is started.
"""
from __future__ import with_statement
import cPickle

##############################################################################################

class PersistantStorage():
    """
    The persistantStorage class allows for persistant storage of variables not in the settings file.
    This is useful for storing data such as realtime keogram filenames etc.
    """
      
    def __init__(self,folder,settings_manager):
        self.__settings_manager = settings_manager
        self.__persistant_file = folder +"/persistant_storage"   
      
        try:
            with open(self.__persistant_file,"r") as fp:
                self.__data = cPickle.load(fp)
        except IOError:
            self.__data = {}
    
    ##############################################################################################
    
    def add(self,name):
        """
        Adds a variable to the list of variables to be stored beyond program exit. Note that the 
        value of the variable does not have to be specified, since this is read from the settingsManager
        on exit.
        """       
        self.__data[name] = None
               
    ##############################################################################################
        
    def get_persistant_data(self):
        """
        Returns a dict of name:value pairs containing the current values of the variables in 
        persistant storage.
        """
        
        #first we have to syncronise with the settingsManager's values in case a new variable 
        #has been added since the file was loaded (otherwise it would return its value as None
        
        for name in self.__data.keys():
            try:
                self.__data[name] = self.__settings_manager.get([name])[name]
            except KeyError:
                #ignore any values that haven't been loaded into the settings manager yet
                pass
            
        return self.__data.copy()

    ##############################################################################################
    
    def exit(self):
        """
        Store the persistant values in a file and return.
        """
        #get up to date values of persistant variables from the settings manager
        updated_data = self.__settings_manager.get(self.__data.keys())

        #save data
        with open(self.__persistant_file,"w") as fp:
            cPickle.dump(updated_data,fp)
           
    ##############################################################################################
##############################################################################################