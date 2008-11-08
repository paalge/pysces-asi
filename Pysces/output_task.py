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
    
            output_tasks.append(OutputTask(outputs, image_files[image_type], folder_on_host, settings_manager))
                                
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
            network_manager_proxy.copy_to_server(sub_task.output_filename, sub_task.file_on_server)
        
    except Exception, ex:
        traceback.print_exc()
        raise ex
    
    finally:
        #shutdown the proxies
        settings_manager_proxy.exit()
        network_manager_proxy.exit()
        
##############################################################################################          
        
class SubTask:
    """
    The subTask class is used to represent a single output that must be created for a particular
    image type. It holds information on what function to run to create the output and also where
    the output should be saved when it has been created. The execute method runs the function
    to create the output, but does not save it.
    """
    def __init__(self, function, image, output_type, folder_on_host):
        self.function = function
        self.output_filename = None
        self._folder_on_host = folder_on_host
        self.output = output_type
        self.image = image
        self.file_on_server = output_type.file_on_server
        
    ##############################################################################################          
    
    def execute(self, settings_manager_proxy, network_manager_proxy):
        """
        Runs the function defined in the outputs.py file for this output type
        """
        
        try:
            #start the proxies
            settings_manager_proxy.start()
            network_manager_proxy.start()
        
            #load the image
            image = allskyImage.new(self.image[0],self.image[1])
            
            #work out where the output should be saved
            #get the capture time from the image header
            capture_time_string = image.getInfo()['header']['Creation Time']
            
            capture_time = datetime.datetime.strptime(capture_time_string, "%d %b %Y %H:%M:%S %Z")
            
            filename = capture_time.strftime(self.output.filename_format)
            
            if self.output.folder_on_host != "" and self.output.folder_on_host != None:
                self.output_filename = os.path.normpath(self._folder_on_host + "/" + self.output.folder_on_host + "/" + filename)
            else:
                self.output_filename = os.path.normpath(self._folder_on_host + "/" + filename)
            
        
            #run the subtask execution function (this is what actually produces the output)
            output = self.function(image, self.output, settings_manager_proxy)
            
            #save the output on the host
            if output != None:
                try:
                    output.save(self.output_filename)
                except AttributeError:
                    #this is added for compatibility with matplotlib figure objects
                    output.savefig(self.output_filename)
            
            #copy the output to the server if required
            if self.file_on_server != None:
                network_manager_proxy.copy_to_server(self.output_filename, self.file_on_server)
        
        except Exception, ex:
            traceback.print_exc()
            raise ex
        
        finally:
            #shutdown the proxies
            settings_manager_proxy.exit()
            network_manager_proxy.exit()
    
    ##############################################################################################      
##############################################################################################  
           
class OutputTask:
    """
    Base class for OutputTask classes. outputTasks objects are passed to the OutputTaskHandler
    which uses them to produce a list of tasks that need to be completed regarding output
    from the current capture mode.
    
    OutputTaskBase objects (and objects inheriting from OutputTaskBase) represent a set of 
    outputs that must be produced for a single image file. When the output task is completed
    then the temporary image files can be removed.
    """
    def __init__(self, outputs, image_file, folder_on_host, settings_manager):
        self._image_file = image_file
        self._outputs = outputs
        self._folder_on_host = folder_on_host
        self._settings_manager = settings_manager
        self._running_subtasks = []
        self._running_subtasks_lock = threading.Lock()
        self.__remove_files = True
                 
    ##############################################################################################  
    
    def run_subtasks(self, processing_pool, pipelined_processing_pool, network_manager):
        """
        Runs the pre-processing functions and then submits the sub-tasks to the processing
        pools for execution.
        """
        
        #build the subtask objects
        for output in self._outputs:
            
            #get the function that the sub-task needs to run
            function = TYPES[output.type]
            
            #create the subTask object
            sub_task = SubTask(function, self._image_file, output, self._folder_on_host)
            
            #submit the sub_task for processing
            if output.pipelined:
                task = pipelined_processing_pool.create_task(sub_task.execute, self._settings_manager.create_proxy(), network_manager.create_proxy())
                self._running_subtasks.append(task)
                pipelined_processing_pool.commit_task(task)     
                
            else:
                task = processing_pool.create_task(sub_task.execute, self._settings_manager.create_proxy(), network_manager.create_proxy())
                self._running_subtasks.append(task)
                processing_pool.commit_task(task)
            
    ##############################################################################################  
    
    def wait(self):
        self._running_subtasks_lock.acquire()
        while 0 < len(self._running_subtasks):
            self._running_subtasks[0].completed.wait()
            try:
               self._running_subtasks[0].result()
            except:
               self.__remove_files = False
               self._settings_manager.set({'output':"outputTask> Error! Processing pool failed to execute one or more sub-tasks"})
               self._settings_manager.set({'output':"outputTask> Leaving temporary files in place"})
               
            self._running_subtasks.pop(0)
        self._running_subtasks_lock.release()
            
    ##############################################################################################    
    
    def remove_temp_files(self):
        return
        if self.__remove_files:
            os.remove(self._image_file[0])
            os.remove(self._image_file[1]) 
            
    ##############################################################################################  
##############################################################################################  
