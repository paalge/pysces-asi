from threading import Event,Thread
import processing
from processing.managers import SyncManager,CreatorMethod
from Queue import Queue

##############################################################################################

class threadTask:
    def __init__(self,func,*args,**kwargs):
        self._function = func
        self._args = args
        self._kwargs = kwargs
        self._return_value = None
        self._completed = Event()
        self._exception = None
        
    def execute(self):
        """
        Executes the task.
        """
        #try to run the function. If it fails then store the exception object to pass to outside thread
        try:
            self._return_value = self._function(*self._args,**self._kwargs)
        
        except Exception,self._exception:
            pass
    
        #set the event to true, to show that the task is finished
        self._completed.set()
        
    def result(self):
        """
        Blocks until the task is executed and then returns the result. If the target function has no return value 
        then None is returned when the task is completed.
        """
        self._completed.wait()
        if self._exception == None:
            return self._return_value
        else:
            raise self._exception

##############################################################################################

class taskQueueBase:
    """
    Base class for classes running in a separate thread and using a task queue for input
    """
    def __init__(self,workers=1):
        self._task_queue = Queue()
        self._workers = []
        self._stay_alive = True
        for i in range(workers):
            self._workers.append(Thread(target = self._processTasks))
            self._workers[i].start()
        
    def _processTasks(self):
        while self._stay_alive or (not self._task_queue.empty()):
            #pull a task out of the queue
            task = self._task_queue.get()
            
            #execute the task
            task.execute()
            
            #tell the queue that execution is complete
            self._task_queue.task_done()
    
    def createTask(self,func,*args,**kwargs):
        return threadTask(func,*args,**kwargs)
    
    def commitTask(self,task):
        #only queue task if should be alive - tasks submitted after exit is encountered will be ignored
        if self._stay_alive:
            self._task_queue.put(task)
       
    def exit(self):
        
        #submit one exit task for each thread 
        for i in range(len(self._workers)):
            task = self.createTask(self._exit)
            self.commitTask(task)
        
        #block until outstanding tasks have been completed
        for thread in self._workers:
            thread.join()
    
    def _exit(self):
        self._stay_alive = False

##############################################################################################       
        
class processQueueBase():
    def __init__(self,workers = 1):
        #create a manager for creating shared objects
        self._manager = processing.Manager()
        
        #create a pool of processes for handling tasks
        self._processing_pool = processing.Pool(processes=workers)

    
    def createTask(self,func,*args,**kwargs):
        n = self._manager.Namespace()
        e = self._manager.Event()
        task = processTask(n,e,func,*args,**kwargs)
        return task
    
    def commitTask(self,task):
        self._processing_pool.apply_async(task.execute)
    
    def exit(self):
        
        self._processing_pool.close()
        self._processing_pool.join()
        
        #kill the manager
        self._manager.shutdown()
        
        
##############################################################################################               
               
class processTask:
    def __init__(self,shared_namespace,shared_event,func,*args,**kwargs):
        
        self._function = func
        self._args = args
        self._kwargs = kwargs
        self.namespace = shared_namespace
        self.namespace.exception = None
        self.completed = shared_event
        
    def execute(self,*args):
        """
        Executes the task.
        """
        #try to run the function. If it fails then store the exception object to pass to outside thread
        try:
            self.namespace.return_value = self._function(*self._args,**self._kwargs)
        
        except Exception,self.namespace.exception:
            pass
        
        self.completed.set()
        
    def result(self):
        """
        Blocks until the task is executed and then returns the result. If the target function has no return value 
        then None is returned when the task is completed.
        """
        self.completed.wait()
        if self.namespace.exception == None:
            return self.namespace.return_value
        else:
            raise self.namespace.exception

##############################################################################################
