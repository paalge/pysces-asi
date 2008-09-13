from __future__ import with_statement
import cPickle

##############################################################################################

class persistantStorage():
    
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
        self.__data[name] = None
               
    ##############################################################################################
        
    def getPersistantData(self):
        return self.__data.copy()

    ##############################################################################################
    
    def exit(self):
        #get up to date values of persistant variables from the settings manager
        updated_data = self.__settings_manager.get(self.__data.keys())

        #save data
        with open(self.__persistant_file,"w") as fp:
            cPickle.dump(updated_data,fp)

            
    ##############################################################################################
##############################################################################################