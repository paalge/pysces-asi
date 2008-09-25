from multitask import taskQueueBase,processQueueBase,threadTask
from outputTask import outputTaskBase
import processing,time
from networkManager import networkManager

class ShrdObjManager(SyncManager):
    """
    Manager class for creating shared allskyImage objects. Note that it inherits from SyncManager
    rather than BaseManager, so it can also be used for creating other shared objects such as
    Events, Namespaces etc...
    """
    ASI = CreatorMethod(allskyImage.new)
    networkManger = CreatorMethod(networkManager)

##############################################################################################  

class outputTaskHandler(taskQueueBase):
    
    def __init__(self,settings_manager):
        taskQueueBase.__init__(self,workers = 2)
        self._manager = ShrdObjManager()
        self._manager.start()
        
        self.__saving_threads = []
        self.__cleanup_threads = []
        
        #create a processing pool to produce the outputs asyncronously - this has as many workers as there are CPU cores
        self._processing_pool = processQueueBase(workers = processing.cpuCount())
        
        #create networkManager object to handle copying outputs to the webserver
        self._network_manager = self._manager.networkManager(settings_manager)        

    ##############################################################################################  

    def _processTasks(self):
        while self._stay_alive or (not self._task_queue.empty()):
            #pull an outputTask out of the queue
            output_task = self._task_queue.get()
            
            #there is the chance that this could be a threadTask object, rather than a 
            #outputTask object, and we need to be able to excute it.
            if isinstance(output_task,threadTask):
                output_task.execute()
                self._task_queue.task_done()
                
            elif isinstance(output_task,outputTaskBase):
                #get the subtasks from the outputTask and pass them over to the processing pool for either parallel or pipelined execution
                for sub_task in output_task.getSubTasks():
                    self._processing_pool.commitTask(sub_task)
                    
                while not output_task.isCompleted():
                    time.sleep(1)
                
                #remove the temporary files associated with this output task
                output_task.exit()
            
                #tell the queue that execution is complete
                self._task_queue.task_done()
            
            else:
                #if this happens then something has gone seriously wrong!
                raise TypeError,str(type(output_task))+" is neither a task nor a outputTask and cannot be executed by the outputTaskHandler."

    ##############################################################################################              

    def exit(self):
           self._processing_pool.exit()
           taskQueueBase.exit(self)
           self._manager.shutdown()

    ##############################################################################################  
##############################################################################################             
           