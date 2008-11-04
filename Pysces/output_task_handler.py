"""
This module provides the OutputTaskHandler class, which is responsible
for post-processing the images to produce the desired outputs. 
Multiple processes are used to produce the outputs in parallel and the 
degree of parallelism will scale automatically with the number of available
CPUs.
"""
import multiprocessing
import datetime

import network
from multitask import ThreadQueueBase, ThreadTask, ProcessQueueBase
from output_task import OutputTaskBase

##############################################################################################  

class OutputTaskHandler(ThreadQueueBase):
    """
    The OutputTaskHandler class manages two processing pools for post-
    processing the images. One pool uses as many processes as there are
    CPUs to parallel process the outputs. The other uses a single process
    to produce outputs that require images to be processed in order (for 
    example keogram creation). The 'pipelined' parameter in the output 
    declaration in the settings file controls which pool is used for which
    output.
    
    The OutputTaskHandler inherits from ThreadQueueBase, but redefines the
    _process_tasks() method so that it can deal with OutputTask objects in the
    queue as well as ThreadTask objects.
    """
    def __init__(self, settings_manager):
        ThreadQueueBase.__init__(self,name="OutputTaskHandler")
        
        self._running_output_tasks = []
        
        #create a processing pool to produce the outputs asyncronously - this has as many workers as there are CPU cores
        self._processing_pool = ProcessQueueBase(workers=multiprocessing.cpu_count())
        
        #create a processing pool to produce outputs in the order that their respective image types
        #are recieved from the camera (useful for creating keograms for example)
        self._pipelined_processing_pool = ProcessQueueBase(workers=1)
        
        #create NetworkManager object to handle copying outputs to the webserver
        self._network_manager = network.NetworkManager(settings_manager)        

    ##############################################################################################  

    def _process_tasks(self):
        """
        Here we redefine the _process_tasks method (inherited from ThreadQueueBase)
        so that OutputTask objects can be placed into the input queue as well as
        ThreadTask objects. The OutputTask objects are recieved from the CaptureManager
        class.
        """
        while self._stay_alive or (not self._task_queue.empty()):
            print "OutputTaskHandler> "+str(self._task_queue.qsize)+" tasks in queue at "+str(datetime.datetime.utcnow())
            
            #pull an outputTask out of the queue
            output_task = self._task_queue.get()
            
            #there is the chance that this could be a ThreadTask object, rather than a 
            #OutputTask object, and we need to be able to excute it.
            if isinstance(output_task, ThreadTask):
                output_task.execute()
                self._task_queue.task_done()
                
            elif isinstance(output_task, OutputTaskBase):
                #add to the list of running tasks
                self._running_output_tasks.append(output_task)
                
                #run all the sub tasks in separate processes
                output_task.run_subtasks(self._processing_pool, self._pipelined_processing_pool, self._network_manager)
            
                #tell the queue that execution is complete
                self._task_queue.task_done()
            
            else:
                #if this happens then something has gone seriously wrong!
                raise(TypeError, str(type(output_task))+
                      " is neither a ThreadTask nor an OutputTask and cannot be executed" +
                      " by the OutputTaskHandler.")
            
            #tidy up the list of tasks currently being run, remove the ones that have finished
            i = 0
            while i < len(self._running_output_tasks):
                if self._running_output_tasks[i].is_completed():
                    self._running_output_tasks.pop(i)
                    i = i -1
                i = i + 1            
            
    ##############################################################################################              
     
    def exit(self):
        """
        Waits for all the outstanding OutputTasks to be completed then shuts down the 
        processing pools and the internal worker thread.
        """
        #wait for all the output_tasks to be completed
        for output_task in self._running_output_tasks:
            output_task.exit()
        
        #shutdown the processing pools
        self._processing_pool.exit()
        self._pipelined_processing_pool.exit()
        
        #kill own worker thread
        ThreadQueueBase.exit(self)

    ##############################################################################################  
##############################################################################################             
           