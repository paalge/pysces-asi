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
The persist module provides a PersistantStorage class, which is used by the SettingsManager
class to store variables that are not in the settings file. Their values are loaded
again when the program is started.
"""

import pickle

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
                self.__data = pickle.load(fp)
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
        
        for name in list(self.__data.keys()):
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
        updated_data = self.__settings_manager.get(list(self.__data.keys()))

        #save data
        with open(self.__persistant_file,"w") as fp:
            pickle.dump(updated_data,fp)
           
    ##############################################################################################
##############################################################################################