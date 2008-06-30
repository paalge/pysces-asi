import datetime,threading,time

class dailyPro:
    
    def __init__(self,settings_manager):
        
        self.__settings_manager = settings_manager
        self.__stay_alive = False
        
        self.__day_thread = None 
        
        
        
    def __updateDay(self):
        
        while self.__stay_alive:
            current_day = datetime.datetime.now().day

            day = self.__settings_manager.grab('day')
            self.__settings_manager.release('day')
            
            if current_day != day:
                self.__settings_manager.set("day",current_day)
            
            time.sleep(5)
    
    def start(self):
        self.__stay_alive = True
        self.__day_thread = threading.Thread(target = self.__updateDay,args=())
        self.__day_thread.start()
            
    def exit(self):
        self.__stay_alive = False
        self.__day_thread.join()