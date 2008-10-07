import PASKIL_jpg_plugin
from outputs import TYPES
import os,datetime,threading,traceback
from PASKIL import allskyImage

##############################################################################################  

def createOutputTasks(capture_mode,image_files,folder_on_host,settings_manager):
    """
    Returns a list of outputTask objects, one for each image type. 
    """
    output_tasks = []
    
    for image_type in image_files.keys():
        outputs = []
        for output in capture_mode.outputs:
            if output.image_type.image_type == image_type:
                outputs.append(output)
    
        #creates different sub-classes of outputTaskBase, depending on what preprocessing is needed
        output_types = set([])
        for output in outputs:
            output_types.add(output.type)
    
        output_types = list(output_types)
    
        if len(output_types) == 1 and output_types[0] == "raw":
            #no preprocessing required, just copying images
            output_tasks.append(outputTaskBase(outputs,image_files[image_type],folder_on_host,settings_manager))
        else:
            output_tasks.append(outputTaskLoad(outputs,image_files[image_type],folder_on_host,settings_manager))
                                
    return output_tasks  

##############################################################################################  

def _processSubTask(sub_task, settings_manager_proxy, network_manager_proxy):
    """
    This is the function that is run by the worker process in the pool. It starts the 
    proxies (this has to be done in the process where the proxies are going to be 
    used), processes the sub task and saves the output (both on the host and on the 
    server).
    """
    try:
        #start the proxies
        settings_manager_proxy.start()
        network_manager_proxy.start()
        
        #run the subtask execution function (this is what actually produces the output)
        output = sub_task.execute(settings_manager_proxy)
        
        #save the output on the host
        if output != None:
            output.save(sub_task.output_filename)
        
        #copy the output to the server if required
        if sub_task.file_on_server != None:
            network_manager_proxy.copyToServer(sub_task.output_filename,sub_task.file_on_server)
               
        #shutdown the proxies
        settings_manager_proxy.exit()
        network_manager_proxy.exit()
        
    except Exception,ex:
        traceback.print_exc()
        raise ex
        
##############################################################################################          
        
class subTask:
    def __init__(self, function, image, output_type, output_filename):
        self.function = function
        self.output_filename = output_filename
        self.output = output_type
        self.image = image
        self.file_on_server = output_type.file_on_server
        
    ##############################################################################################          
    
    def execute(self,settings_manager_proxy):
        """
        Runs the function defined in the outputs.py file for this output type
        """
        return self.function(self.image,self.output,settings_manager_proxy)
    
    ##############################################################################################      
##############################################################################################  
           
class outputTaskBase:
    """
    Base class for outputTask classes. outputTasks objects are passed to the outputTaskHandler
    which uses them to produce a list of tasks that need to be completed regarding output
    from the current capture mode. The outputTask object is then used to create a shared 
    image object which can be accessed by all the tasks when they are run in separate 
    processes. This avoids both having to load the image from file more than once and also
    having to pass large amounts of image data between processes.
    """
    def __init__(self, outputs, image_file, folder_on_host, settings_manager):
        self._image_file = image_file[0]
        self._image_info_file = image_file[1]
        self._outputs = outputs
        self.shared_image = None
        self._folder_on_host = folder_on_host
        self._settings_manager = settings_manager
        self._removal_thread = None
         
        self._running_subtasks = []
            
    ##############################################################################################  
        
    def isCompleted(self):
        """
        Returns false unless all the subtasks have been completed.
        """
        return (not self._removal_thread.isAlive())
        
        for sub_task_result in self._running_subtasks:
            if not sub_task_result.ready():
                return False
        
        return True
    
    ##############################################################################################     
     
    def preProcess(self, manager):
        """
        In the base class, there is no need to actually load the image data, since the only sub-tasks
        are direct copies of the files. 
        """
        #self.shared_image = manager.ASI(self._image_file, self._image_info_file)        
        self.shared_image = allskyImage.new(self._image_file, self._image_info_file)
        
    ##############################################################################################  
    
    def runSubTasks(self, processing_pool, pipelined_processing_pool, network_manager, manager):
        """
        Runs the pre-processing functions and then submits the sub-tasks to the processing
        pools for execution.
        """
        
        #run the pre-processing
        self.preProcess(manager)
        
        #build the subtask objects
        for output in self._outputs:
            
            #get the function that the sub-task needs to run
            function = TYPES[output.type]
    
            #figure out where to save this output.
        
            #get the capture time from the image header
            capture_time_string = self.shared_image.getInfo()['header']['Creation Time']
            
            capture_time = datetime.datetime.strptime(capture_time_string, "%d %b %Y %H:%M:%S %Z")
            
            filename = capture_time.strftime(output.filename_format)
            
            if output.folder_on_host != "" and output.folder_on_host != None:
                path_to_save_to = os.path.normpath(self._folder_on_host + "/" + output.folder_on_host + "/" + filename)
            else:
                path_to_save_to = os.path.normpath(output.folder_on_host + "/" + filename)
            
            
            #create the subTask object
            sub_task = subTask(function, self.shared_image, output, path_to_save_to)
            
            #submit the sub_task for processing
            if output.pipelined:
                task = pipelined_processing_pool.createTask(_processSubTask, sub_task, self._settings_manager.createProxy(), network_manager.createProxy())
                self._running_subtasks.append(task)
                pipelined_processing_pool.commitTask(task)
            else:
                task = processing_pool.createTask(_processSubTask, sub_task, self._settings_manager.createProxy(), network_manager.createProxy())
                self._running_subtasks.append(task)
                processing_pool.commitTask(task)
            
            #start a new thread to remove the temporary image files when all sub_tasks are complete
            self._removal_thread = threading.Thread(target = self._exit)
            self._removal_thread.start()
            
    ##############################################################################################  
    
    def exit(self):
        """
        Blocks until all sub-tasks have been completed and temporary files have been removed.
        """
        self._removal_thread.join()
     
    ##############################################################################################  
    
    def _exit(self):
        """
        Method run by removal thread. Waits until all subtasks have completed successfully, and then removes
        the temporary image files. If any of the sub-tasks fail to complete, then the temporary image files
        are left in place.
        """
        
        #wait for all the sub_tasks to complete
        for sub_task_result in self._running_subtasks:
            
            try:
                sub_task_result.result()
            
            #if the sub_task did not complete successfully, then don't delete the temp files
            except Exception,ex:
                self._settings_manager.set({'output':"outputTask> Error! Processing pool failed to execute one or more sub-tasks"})
                self._settings_manager.set({'output':"outputTask> Leaving temporary files in place"})
                
                raise ex
        
                
        #remove the temporary files associated with this outputTask
        os.remove(self._image_file)
        os.remove(self._image_info_file)                

    ##############################################################################################  
##############################################################################################  

class outputTaskLoad(outputTaskBase):
    """
    Sub-class of outputTaskBase which loads the image data into the shared allskyImage object.
    """
    ##############################################################################################  
        
    def preProcess(self,manager):
        """
        Load the image data as a shared object, accessible by all processes.
        """
        outputTaskBase.preProcess(self,manager)
        self.shared_image.load()

    ##############################################################################################           
##############################################################################################  