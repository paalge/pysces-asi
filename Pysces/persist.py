from __future__ import with_statement
import cPickle


class persistantStorage():
    
    def __init__(self,settings_manager):
        
        self.__settings = settings_manager
        
        filename = self.__settings.grab("persist filename")
        self.__settings.release("persist filename")
        
        try:
            with open(filename,"r") as fp:
                self.__data = cPickle.load(fp)
        except IOError:
            self.__data = {}
        
        
    def getPersistantData(self):
        return self.__data.copy()
    
    def exit(self):
        #syncronise data with settings manager
        for key in self.__settings.grab("persist names"):
            value = self.__settings.grab(key)
            self.__data[key] = value
            self.__settings.release(key)

        self.__settings.release("persist names")
        
        #save data
        filename = self.__settings.grab("persist filename")
        self.__settings.release("persist filename")
        with open(filename,"w") as fp:
            cPickle.dump(self.__data,fp)
