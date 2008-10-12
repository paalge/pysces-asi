import multiprocessing

from multitask import taskQueueBase, threadTask,processQueueBase
from PASKIL import allskyImage
from outputTask import outputTaskBase
import networkManager


class ShrdObjManager(multiprocessing.managers.SyncManager):
    """
    Manager class for creating shared allskyImage objects. Note that it inherits from SyncManager
    rather than BaseManager, so it can also be used for creating other shared objects such as
    Events, Namespaces etc...
    """
    ASI = multiprocessing.managers.CreatorMethod(allskyImage.new)


##############################################################################################  

class outputTaskHandler(taskQueueBase):
    
    def __init__(self,settings_manager):
        taskQueueBase.__init__(self)
        
        self._running_output_tasks = []
        
        #create a manager to be used for managing shared ASI objects
        self._manager = ShrdObjManager()
        self._manager.start()
        
        #create a processing pool to produce the outputs asyncronously - this has as many workers as there are CPU cores
        self._processing_pool = processQueueBase(workers=multiprocessing.cpuCount())
        
        #create a processing pool to produce outputs in the order that their respective image types
        #are recieved from the camera (useful for creating keograms for example)
        self._pipelined_processing_pool = processQueueBase(workers=1)
        
        #create networkManager object to handle copying outputs to the webserver
        self._network_manager = networkManager.networkManager(settings_manager)        

    ##############################################################################################  

    def _processTasks(self):
        while self._stay_alive or (not self._task_queue.empty()):
            #pull an outputTask out of the queue
            output_task = self._task_queue.get()
            
            #there is the chance that this could be a threadTask object, rather than a 
            #outputTask object, and we need to be able to excute it.
            if isinstance(output_task, threadTask):
                output_task.execute()
                self._task_queue.task_done()
                
            elif isinstance(output_task, outputTaskBase):
                #add to the list of running tasks
                self._running_output_tasks.append(output_task)
                
                #run all the sub tasks in separate processes
                output_task.runSubTasks(self._processing_pool, self._pipelined_processing_pool, self._network_manager, self._manager)
            
                #tell the queue that execution is complete
                self._task_queue.task_done()
            
            else:
                #if this happens then something has gone seriously wrong!
                raise TypeError, str(type(output_task))+" is neither a task nor\
                an outputTask and cannot be executed by the outputTaskHandler."
            
            #tidy up the list of tasks currently being run, remove the ones that have finished
            i = 0
            while i < len(self._running_output_tasks):
                if self._running_output_tasks[i].isCompleted():
                    self._running_output_tasks.pop(i)
                    i = i -1
                i = i + 1            
            
    ##############################################################################################              
     
    def exit(self):
        #wait for all the output_tasks to be completed
        for output_task in self._running_output_tasks:
            output_task.exit()
        
        #shutdown the processing pools
        self._processing_pool.exit()
        self._pipelined_processing_pool.exit()
        
        #kill own worker thread
        taskQueueBase.exit(self)
        
        #shutdown the shared image object manager
        self._manager.shutdown()

    ##############################################################################################  
##############################################################################################             
           