from multitask import taskQueueBase,threadTask,processQueueBase
from outputTask import outputTaskBase
import processing,threading,time
from networkManager import networkManager

class outputTaskHandler(taskQueueBase):
    
    def __init__(self,settings_manager):
        #note that this class has multiple workers, so it will process outputTasks asyncronously!
        taskQueueBase.__init__(self,workers = 1)
        
        self.__saving_threads = []
        self.__cleanup_threads = []
        
        #create a processing pool to produce the outputs asyncronously - this has as many workers as there are CPU cores
        self._processing_pool = processQueueBase(workers = processing.cpuCount())
        
        #create a processing pool with only one process for dealing with pipelined output functions
        #this ensures that the images are processed in the order which they come in from the camera
        #at least for images of the same type
        self._pipelined_processing_pool = processQueueBase(workers = 1)
        
        #create networkManager object to handle copying outputs to the webserver
        self._network_manager = networkManager(settings_manager)        


    def _processTasks(self):
        while self._stay_alive or (not self._task_queue.empty()):
            #pull an outputTask out of the queue
            output_task = self._task_queue.get()
            
            output_task.execute(self._processing_pool,self._pipelined_processing_pool)
            
            self._task_queue.task_done()
            
            #there is the chance that this could be a threadTask object, rather than a 
            #outputTask object, and we need to be able to excute it.
            if isinstance(output_task,threadTask):
                output_task.execute()
                self._task_queue.task_done()
                
            elif isinstance(output_task,outputTaskBase):
                #get the subtasks from the outputTask and pass them over to the processing pool for either parallel or pipelined execution
                for func,args,pipelined in output_task.getSubTasks():
                    if pipelined:
                        sub_task = self._pipelined_processing_pool.createTask(func,*args)
                        self._pipelined_processing_pool.commitTask(sub_task)
                    else:
                        sub_task = self._processing_pool.createTask(func,*args)
                        self._processing_pool.commitTask(sub_task)
                    
                    #create a new thread to store the output of the sub_task when it is ready
                    t = threading.Thread(target = self.__saveOutput, args = (sub_task,))
                    self.__saving_threads.append(t)
                    t.start()
            
                #start a new thread to shutdown the output_task object when it is finished
                t = threading.Thread(target = self.__cleanUp, args = (output_task,))
                self.__cleanup_threads.append(t)
                t.start()
                
                #remove any threads in the lists that have finished (this is just to make sure that the lists don't get too big)
                self.__purgeLists()
            
                #tell the queue that execution is complete
                self._task_queue.task_done()
            
            else:
                #if this happens then something has gone seriously wrong!
                raise TypeError,str(type(output_task))+" is neither a task nor a outputTask and cannot be executed by the outputTaskHandler."
            
    
    def __purgeLists(self):
        """
        Method maintains lists of active threads, removing any threads which are no longer alive from
        the list.
        """
        for list in [self.__cleanup_threads,self.__saving_threads]:
            i = 0
            while i < len(list):
                if not list[i].isAlive():
                    list.pop(i)
                    i = i-1
                i = i+1
           
    def __cleanUp(self,output_task):
        """
        Shuts down the outputTask object when it is completed.
        """
        while True:
            if output_task.isCompleted():
                output_task.exit()
            else:
                #otherwise, give the processing pool a bit longer and then try again
                time.sleep(5)   
    
    def __saveOutput(self,sub_task):
        
        #wait for the processing pool to finish executing the sub_task
        result = sub_task.result()
        
        #if the output is None, then there is nothing more to do
        if result == None:
            return
        
        #otherwise we have to figure out where to save this output.
        
        #get the capture time from the image header
        capture_time_string = sub_task.image.getInfo()['header']['Creation Time']
        
        capture_time = datetime.datetime.strptime(capture_time_string,"%d %b %Y %H:%M:%S %Z")
        
        filename = capture_time.strftime(sub_task.output.filename_format)
        
        if sub_task.output.folder_on_host != "" and sub_task.output.folder_on_host != None:
            path_to_save_to = os.path.normpath(sub_task.folder_on_host + "/" + sub_task.output.folder_on_host + filename)
        else:
            path_to_save_to = os.path.normpath(sub_task.folder_on_host + "/" + filename)
        
        result.save(path_to_save_to)
        
        #if the output has to be copied to the web then do that now
        if sub_task.output.file_on_server != None:
            self._network_manager.copyToServer(path_to_save_to,sub_task.output.file_on_server)
    
    def exit(self):
           self._processing_pool.exit()
           self._pipelined_processing_pool.exit()

           
           taskQueueBase.exit(self)
           
           