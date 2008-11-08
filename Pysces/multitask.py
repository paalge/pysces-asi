"""
The multitask module provides classes to ease parallel processing, both 
multi-thread and multi-process. The two main classes are ThreadQueueBase and 
ProcessQueueBase, these use the same interface, and to some extent are 
interchangable. They have two main purposes. Syncronisation: by setting the 
number of workers to 1, method calls from multiple threads/processes are queued
and executed sequentially. Parallelisation: by setting the number of workers to
>1, method calls are processed concurrently by multiple threads or processes.
"""
import time
import traceback
import multiprocessing
import datetime

from Queue import Queue
from threading import Event, Thread, currentThread


class RemoteTask:
    """
    Represents a task created by a proxy object that must be executed by the
    master class (which may be running in a separate process).
    """
    def __init__(self, id_, method, *args, **kwargs):
        self.id = id_
        self.method_name = method
        self.args = args
        self.kwargs = kwargs
        
    ###########################################################################
###########################################################################

class ThreadTask:
    """
    Represents a task to be executed by a ThreadQueueBase instance. The 
    ThreadTask object provides a method to execute the task, and a method to 
    retrieve the result when it is ready.
    """
    def __init__(self, func, *args, **kwargs):
        self._function = func
        self._args = args
        self._kwargs = kwargs
        self._return_value = None
        self.completed = Event()
        self._exception = None
        self._traceback = None

    ###########################################################################
        
    def execute(self):
        """
        Executes the task.
        """
        #try to run the function. If it fails then store the exception object 
        #to pass to outside thread
        try:
            self._return_value = self._function(*self._args, **self._kwargs)
        
        #catch any exceptions that were raised during execution so that they 
        #can be raised in the calling thread, rather than the worker thread.
        except Exception, self._exception:
            print "\nException in thread: ", currentThread()
            traceback.print_exc()

    
        #set the event to true, to show that the task is finished
        self.completed.set()

    ###########################################################################
        
    def result(self):
        """
        Blocks until the task is executed and then returns the result. If the
        target function has no return value then None is returned when the 
        task is completed. If the target function raised an exception when it
        was executed, then calling result() will raise the same exception.
        """
        self.completed.wait()
        if self._exception is None:
            return self._return_value
        else:
            traceback.print_exc()
            raise self._exception
        
    ###########################################################################
###########################################################################

class ThreadQueueBase:
    """
    Base class for classes running in separate threads and using a task queue
    for input.
    """
    def __init__(self, workers=1, maxsize=0,name="Un-named"):
        self._task_queue = Queue(maxsize=maxsize)
        self._workers = []
        self._stay_alive = True
        self.name = name
        self._exit_event = Event()
        for i in range(workers):
            self._workers.append(Thread(target = self._process_tasks))
            self._workers[i].setName(self.name + " thread "+str(i))
            self._workers[i].start()

    ###########################################################################
        
    def _process_tasks(self):
        """
        Run by the internal worker thread(s), this method pulls tasks out of
        the input queue and executes them.
        """
        while self._stay_alive or (not self._task_queue.empty()):
            #pull a task out of the queue
            task = self._task_queue.get()
            
            #execute the task
            task.execute()
            
            #tell the queue that execution is complete
            self._task_queue.task_done()
        
        self._exit_event.set()
        
    ###########################################################################
    
    def create_task(self, func, *args, **kwargs):
        """
        Creates a new task object which can be submitted for execution using 
        the commit_task() method.
        """
        return ThreadTask(func, *args, **kwargs)

    ###########################################################################
    
    def commit_task(self, task):
        """
        Puts the specified task into the input queue where it will be executed
        by one of the internal worker threads. The task's result() method be
        used for syncronising with task completion.
        """
        #only queue task if should be alive - tasks submitted after exit is 
        #encountered will be ignored
        for thread in self._workers:
            if not thread.isAlive():
                print "### Error! ### Worker thread in "+self.name+ " has died!"
                raise RuntimeError, "### Error! ### Worker thread in "+self.name+ " has died!"
        
        if self._stay_alive:
            self._task_queue.put(task)

    ###########################################################################
       
    def exit(self):
        """
        Waits for all remaining tasks in the input queue to finish and then
        kills the worker threads.
        """
        #submit one exit task for each thread 
        for i in xrange(len(self._workers)):
            task = self.create_task(self._exit)
            self._task_queue.put(task)
            self._exit_event.wait()
            self._exit_event.clear()
        
        #block until outstanding tasks have been completed
        for thread in self._workers:
            thread.join()

    ###########################################################################
    
    def _exit(self):
        """
        Method run by the worker threads in order to break out of the 
        _process_tasks() loop.
        """
        self._stay_alive = False

    ###########################################################################
###########################################################################      
        
class ProcessQueueBase:
    """
    Base class for running task in separate processes and using a task queue
    for input.
    """
    def __init__(self, workers=1, maxsize=0,name = "Un-named"):
        #create a manager for creating shared objects
        #self._manager = multiprocessing.Manager()
        self.name = name
        #create an input queue
        self._input_queue = Queue(maxsize=maxsize)
        
        self._process_count = 0
        self._max_process_count = workers
        self._active_processes = []        
        self._stay_alive = True
               
        #create a thread to read from the input queue and start tasks in their 
        #own process
        self._input_thread = Thread(target = self._process_tasks)
        self._input_thread.setName(self.name+" input thread")
        self._input_thread.start()

    ###########################################################################
    
    def _process_tasks(self):
        """
        Run by the internal worker thread, this method pulls tasks out of
        the input queue and creates child processes to execute them. A maximum
        of 'workers' number of child processes will be allowed to run at any
        one time.
        """
        while self._stay_alive or (not self._input_queue.empty()):
            task = self._input_queue.get()
            
            #if task is None, then it means we should exit - go back to 
            #beginning of loop
            if task is None:
                continue    
            
            #Python's popen system is not thread safe, so occasionally it will throw up
            #a OSError "No child processes" during the following bit of code. This *might*
            #have been fixed in python2.6, but nobody seems sure, so just in case we wrap it
            #in a try except block
            
            try:
                #otherwise wait for active process count to fall below max count
                while self._process_count >= self._max_process_count:
                    i = 0
                    while i < len(self._active_processes):
                        if not self._active_processes[i].is_alive():
                            self._active_processes[i].join()
                            self._active_processes.pop(i)
                            self._input_queue.task_done()
                            i = i - 1
                            self._process_count = self._process_count - 1
                        i = i + 1
                    time.sleep(0.001)
            except OSError:
                print "Syncronisation error in ProcessQueueBase! Task has been re-submitted."
                self._input_queue.put(task)
                continue
            
            #create a new process to run the task
            p = multiprocessing.Process(target = task.execute)
            self._active_processes.append(p)
            self._process_count = self._process_count +1
            p.start()

    ###########################################################################
  
    def create_task(self, func, *args, **kwargs):
        """
        Creates a new task object which can be submitted for execution using 
        the commit_task() method.
        """
        #n = self._manager.Namespace()
        q = multiprocessing.Queue()
        e = multiprocessing.Event()
        task = ProcessTask(q, e, func, *args, **kwargs)
        return task

    ###########################################################################
    
    def commit_task(self, task):
        """
        Puts the specified task into the input queue where it will be executed
        in its own process. The task's result() method be used for syncronising 
        with task completion.
        """
        if not self._input_thread.isAlive():
            print "### Error! ### Worker thread in "+self.name+ " has died!"
            raise RuntimeError, "### Error! ### Worker thread in "+self.name+ " has died!"
        self._input_queue.put(task)

    ###########################################################################
    
    def exit(self):
        """
        Waits for all the tasks in the input queue to be completed then kills 
        the internal worker thread and the manager process.
        """
        self._stay_alive = False
        self._input_queue.put(None)
        self._input_thread.join()
        
        for process in self._active_processes:
            process.join()
        
        #kill the manager
        #self._manager.shutdown()
        
    ###########################################################################        
###########################################################################              
               
class ProcessTask:
    """
    Represents a task to be executed by a ProcessQueueBase instance. The 
    ProcessTask object provides a method to execute the task, and a method to 
    retrieve the result when it is ready.
    """
    def __init__(self, return_queue, shared_event, func, *args, **kwargs):
        
        self._function = func
        self._args = args
        self._kwargs = kwargs
        self.return_queue = return_queue
        #self.namespace.exception = None
        self.completed = shared_event

    ###########################################################################
        
    def execute(self):
        """
        Executes the task.
        """
        #try to run the function. If it fails then store the exception object 
        #to pass to outside thread
        try:
            self.return_queue.put(self._function(*self._args, 
                                                         **self._kwargs))
       
       #catch any exceptions that were raised during execution so that they can
       #be raised in the calling thread, rather than the internal worker thread 
        except Exception, ex:
            self.return_queue.put(ex)
        
        self.completed.set()

    ###########################################################################
        
    def result(self):
        """
        Blocks until the task is executed and then returns the result. If the 
        target function has no return value then None is returned when the 
        task is completed. If the target function raised an exception when it
        was executed, then calling result() will raise the same exception.
        """
        self.completed.wait()
        return_value = self.return_queue.get()
        
        if isinstance(return_value,Exception):
            raise return_value
        else:
            return return_value
        
    ###########################################################################
###########################################################################
