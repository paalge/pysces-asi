from __future__ import with_statement
import cPickle

##############################################################################################

class persistantStorage():
    
    def __init__(self,settings_manager):
        
        self.__settings = settings_manager
        
        #get globals
        glob_vars = self.__settings.get(["persist filename"])
        
      
        try:
            with open(glob_vars["persist filename"],"r") as fp:
                self.__data = cPickle.load(fp)
        except IOError:
            self.__data = {}
        
    ##############################################################################################
        
    def getPersistantData(self):
        return self.__data.copy()

    ##############################################################################################
    
    def exit(self):
        #get globals
        initial_glob_vars = self.__settings.get(["persist names","persist filename"])
        
        #get more global variables based on value of persist names
        glob_vars = self.__settings.get(["persist names","persist filename"]+initial_glob_vars["persist names"])
 
        

        #syncronise data with settings manager
        for key in glob_vars["persist names"]:
            self.__data[key] = glob_vars[key]

        #save data
        with open(glob_vars["persist filename"],"w") as fp:
            cPickle.dump(self.__data,fp)

            
    ##############################################################################################
##############################################################################################