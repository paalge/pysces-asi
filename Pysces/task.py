from threading import Event,Thread
from Queue import Queue


class task:
    def __init__(self,func,*args,**kwargs):
        self.__function = func
        self.__args = args
        self.__kwargs = kwargs
        self.__return_value = None
        self.__completed = Event()
        self.__exception = None
        
    def execute(self):
        """
        Executes the task.
        """
        #try to run the function. If it fails then store the exception object to pass to outside thread
        try:
            self.__return_value = self.__function(*self.__args,**self.__kwargs)
        except Exception,self.__exception:
            pass
            
        #set the event to true, to show that the task is finished
        self.__completed.set()
        
    def result(self):
        """
        Blocks until the task is executed and then returns the result. If the target function has no return value 
        then None is returned when the task is completed.
        """
        self.__completed.wait()
        if self.__exception == None:
            return self.__return_value
        else:
            raise self.__exception
    
def Task(func,*args,**kwargs):
    return task(func,*args,**kwargs)

class taskQueueBase:
    """
    Base class for classes running in a separate thread and using a task queue for input
    """
    def __init__(self):
        self.__task_queue = Queue()
        self.__worker_thread = Thread(target = self.__processTasks)
        self.__stay_alive = True
        self.__worker_thread.start()
        self.__running = False
        
    def __processTasks(self):
        while self.__stay_alive or (not self.__task_queue.empty()):
            #pull a task out of the queue
            task = self.__task_queue.get()
            
            #execute the task
            task.execute()
            
            #tell the queue that execution is complete
            self.__task_queue.task_done()
    
    def commitTask(self,task):

        #only queue task if should be alive - tasks submitted after exit is encountered will be ignored
        if self.__stay_alive:
            self.__task_queue.put(task)
       
    def exit(self):
        task = Task(self.__exit)
        self.commitTask(task)
        
        #block until outstanding tasks have been completed
        self.__worker_thread.join()
        
        self.__running = False
    
    def __exit(self):
        self.__stay_alive = False