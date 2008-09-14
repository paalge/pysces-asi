from threading import Event,Thread
from Queue import Queue


class task:
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
    
def Task(func,*args,**kwargs):
    return task(func,*args,**kwargs)

class taskQueueBase:
    """
    Base class for classes running in a separate thread and using a task queue for input
    """
    def __init__(self):
        self._task_queue = Queue()
        self._worker_thread = Thread(target = self._processTasks)
        self._stay_alive = True
        self._worker_thread.start()
        self._running = False
        
    def _processTasks(self):
        while self._stay_alive or (not self._task_queue.empty()):
            #pull a task out of the queue
            task = self._task_queue.get()
            
            #execute the task
            task.execute()
            
            #tell the queue that execution is complete
            self._task_queue.task_done()
    
    def commitTask(self,task):

        #only queue task if should be alive - tasks submitted after exit is encountered will be ignored
        if self._stay_alive:
            self._task_queue.put(task)
       
    def exit(self):
        task = Task(self._exit)
        self.commitTask(task)
        
        #block until outstanding tasks have been completed
        self._worker_thread.join()
        
        self._running = False
    
    def _exit(self):
        self._stay_alive = False