from threading import Event,Thread,currentThread
import traceback
import processing
from processing.managers import SyncManager,CreatorMethod
from Queue import Queue


class remoteTask:
    def __init__(self,id,method,*args,**kwargs):
        self.id = id
        self.method_name = method
        self.args = args
        self.kwargs = kwargs


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
            print "\nException in thread: ",currentThread()
            traceback.print_exc()

    
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
            traceback.print_exc()
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
        
class processQueueBase:

    def __init__(self,workers = 1):
        #create a manager for creating shared objects
        self._manager = processing.Manager()
        
        #create an input queue
        self._input_queue = Queue()
        
        self._process_count = 0
        self._max_process_count = workers
        self._active_processes = []
        
        self._stay_alive = True
        
        
        #create a thread to read from the input queue and start tasks in their own process
        self._input_thread = Thread(target = self._processTasks)
        self._input_thread.start()
    
    def _processTasks(self):
        while self._stay_alive or (not self._input_queue.empty()):
            task = self._input_queue.get()
            
            #if task is None, then it means we should exit - go back to beginning of loop
            if task == None:
                continue    
            
            #otherwise wait for active process count to fall below max count
            while self._process_count >= self._max_process_count:
                i = 0
                while i < len(self._active_processes):
                    if not self._active_processes[i].isAlive():
                        self._active_processes.pop(i)
                        i = i - 1
                        self._process_count = self._process_count - 1
                    i = i + 1
            
            #create a new process to run the task
            p = processing.Process(target = task.execute)
            self._active_processes.append(p)
            self._process_count = self._process_count +1
            p.start()

    
    def createTask(self,func,*args,**kwargs):
        n = self._manager.Namespace()
        e = self._manager.Event()
        task = processTask(n,e,func,*args,**kwargs)
        return task
    
    def commitTask(self,task):
        self._input_queue.put(task)
    
    def exit(self):
        self._stay_alive = False
        self._input_queue.put(None)
        self._input_thread.join()
        
        for process in self._active_processes:
            process.join()
        
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
