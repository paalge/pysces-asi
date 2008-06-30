import threading

class OTFPro:
    
    def __init__(self,settings_manager):
        self.__settings_manager = settings_manager
        self.__worker_threads = []
    
    def start(self):
        #create thread specific data
        local_data = threading.local()
        
        #TODO
        
        
        #create thread to run on-the-fly processing operations
        otf_thread = threading.Thread(target=self.__run,args=(local_data,))
        
        #add thread to list, and remove any threads that have finished
        for thread in self.__worker_threads:
            if not thread.isAlive():
                self.__worker_threads.remove(thread)
        
        self.__worker_threads.append(otf_thread)
    
        #run OTFPro thread
        otf_thread.start()
    
    def __run(self,local_data):
        return
    
    def join(self):
        """
        Blocks until all OTFPro threads have finished
        """
        for thread in self.__worker_threads:
            thread.join()
            