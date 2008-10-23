import os
import datetime
import threading
import traceback

from outputs import TYPES
from PASKIL import allskyImage

##############################################################################################  

def create_output_tasks(capture_mode, image_files, folder_on_host, settings_manager):
    """
    Returns a list of OutputTask objects, one for each image type. The capture_mode 
    argument should be a CaptureMode object, image_files should be a dict of 
    {type,(image file, info file)} as returned by the CameraManager.capture_images()
    method, folder_on_host should be a string containing the folder on the host machine
    where the outputs should be stored and settings_manager should be an instance of
    the SettingsManager class.
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
            output_tasks.append(OutputTaskBase(outputs, image_files[image_type], folder_on_host, settings_manager))
        else:
            output_tasks.append(OutputTaskLoad(outputs, image_files[image_type], folder_on_host, settings_manager))
                                
    return output_tasks  

##############################################################################################  

def _process_subtask(sub_task, settings_manager_proxy, network_manager_proxy):
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
            try:
                output.save(sub_task.output_filename)
            except AttributeError:
                #this is added for compatibility with matplotlib figure objects
                output.savefig(sub_task.output_filename)
        
        #copy the output to the server if required
        if sub_task.file_on_server != None:
            network_manager_proxy.copyToServer(sub_task.output_filename, sub_task.file_on_server)
               
        #shutdown the proxies
        settings_manager_proxy.exit()
        network_manager_proxy.exit()
        
    except Exception, ex:
        traceback.print_exc()
        raise ex
        
##############################################################################################          
        
class SubTask:
    """
    The subTask class is used to represent a single output that must be created for a particular
    image type. It holds information on what function to run to create the output and also where
    the output should be saved when it has been created. The execute method runs the function
    to create the output, but does not save it.
    """
    def __init__(self, function, image, output_type, output_filename):
        self.function = function
        self.output_filename = output_filename
        self.output = output_type
        self.image = image
        self.file_on_server = output_type.file_on_server
        
    ##############################################################################################          
    
    def execute(self, settings_manager_proxy):
        """
        Runs the function defined in the outputs.py file for this output type
        """
        return self.function(self.image, self.output, settings_manager_proxy)
    
    ##############################################################################################      
##############################################################################################  
           
class OutputTaskBase:
    """
    Base class for OutputTask classes. outputTasks objects are passed to the OutputTaskHandler
    which uses them to produce a list of tasks that need to be completed regarding output
    from the current capture mode.
    
    OutputTaskBase objects (and objects inheriting from OutputTaskBase) represent a set of 
    outputs that must be produced for a single image file. When the output task is completed
    then the temporary image files can be removed.
    """
    def __init__(self, outputs, image_file, folder_on_host, settings_manager):
        self._image_file = image_file[0]
        self._image_info_file = image_file[1]
        self._outputs = outputs
        self.image = None
        self._folder_on_host = folder_on_host
        self._settings_manager = settings_manager
        self._removal_thread = None
        self._running_subtasks = []
            
    ##############################################################################################  
        
    def is_completed(self):
        """
        Returns false unless all the subtasks have been completed.
        """
        return (not self._removal_thread.isAlive())
    
    ##############################################################################################     
     
    def preprocess(self):
        """
        In the base class, there is no need to actually load the image data, since the only sub-tasks
        are direct copies of the files. 
        """
        #self.shared_image = manager.ASI(self._image_file, self._image_info_file)        
        self.image = allskyImage.new(self._image_file, self._image_info_file)
        
    ##############################################################################################  
    
    def run_subtasks(self, processing_pool, pipelined_processing_pool, network_manager, manager):
        """
        Runs the pre-processing functions and then submits the sub-tasks to the processing
        pools for execution.
        """
        
        #run the pre-processing
        self.preprocess(manager)
        
        #build the subtask objects
        for output in self._outputs:
            
            #get the function that the sub-task needs to run
            function = TYPES[output.type]
    
            #figure out where to save this output.
        
            #get the capture time from the image header
            capture_time_string = self.image.getInfo()['header']['Creation Time']
            
            capture_time = datetime.datetime.strptime(capture_time_string, "%d %b %Y %H:%M:%S %Z")
            
            filename = capture_time.strftime(output.filename_format)
            
            if output.folder_on_host != "" and output.folder_on_host != None:
                path_to_save_to = os.path.normpath(self._folder_on_host + "/" + output.folder_on_host + "/" + filename)
            else:
                path_to_save_to = os.path.normpath(output.folder_on_host + "/" + filename)
            
            
            #create the subTask object
            sub_task = SubTask(function, self.image, output, path_to_save_to)
            
            #submit the sub_task for processing
            if output.pipelined:
                task = pipelined_processing_pool.createTask(_process_subtask, sub_task, self._settings_manager.createProxy(), network_manager.createProxy())
                self._running_subtasks.append(task)
                pipelined_processing_pool.commitTask(task)
            else:
                task = processing_pool.createTask(_process_subtask, sub_task, self._settings_manager.createProxy(), network_manager.createProxy())
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
            except Exception, ex:
                self._settings_manager.set({'output':"outputTask> Error! Processing pool failed to execute one or more sub-tasks"})
                self._settings_manager.set({'output':"outputTask> Leaving temporary files in place"})
                
                raise ex
        
                
        #remove the temporary files associated with this outputTask
        os.remove(self._image_file)
        os.remove(self._image_info_file)                

    ##############################################################################################  
##############################################################################################  

class OutputTaskLoad(OutputTaskBase):
    """
    Sub-class of OutputTaskBase which loads the image data into the allskyImage object.
    """
    ##############################################################################################  
        
    def preprocess(self):
        """
        Load the image data.
        """
        OutputTaskBase.preprocess(self)
        self.image.load()

    ##############################################################################################           
##############################################################################################  