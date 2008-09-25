from processing.managers import SyncManager,CreatorMethod
from PASKIL import allskyImage
import PASKIL_jpg_plugin
from outputs import TYPES
from multitask import processTask
import os,datetime

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

class subTask:
    def __init__(self,task,output_filename,file_on_server,network_manager):
        self.task = task
        self.output_filename = output_filename
        self.file_on_server = file_on_server
        self.network_manager = network_manager
        self.completed = False
        
    ##############################################################################################          
    
    def execute(self):
        """
        Note that this method is included so that a subTask object can pose as a processTask
        object, i.e. subTask objects are designed to be passed to a processQueueBase instance
        for processing.
        """
        
        #first of all we do the same stuff that the processQueueBase class does on a processTask
        #object, only this time we are doing it on the task attribute of the subTask, then we 
        #save the output and pass it to the network manager (if required)
        
        #execute the task - any exceptions will be raised in this process when we call result.
        self.task.execute()
        
        result = self.task.result()
        
        #save the result in the correct place on the host machine
        result.save(self.output_filename)
        
        #copy the result to the server (if required)
        if file_on_server != None:
            self.network_manager.copyToServer(self.output_filename,self.file_on_server)
        
        
        self.completed.set()
        
    ##############################################################################################  
    
    def isCompleted(self):
        return self.completed
    
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
    def __init__(self,outputs,image_file,folder_on_host,settings_manager):
         self._image_file = image_file[0]
         self._image_info_file = image_file[1]
         self._outputs = outputs
         self.shared_image = None
         self._folder_on_host = folder_on_host
         self._settings_manager = settings_manager
         
         self._subtasks = []
            
    ##############################################################################################  
        
    def isCompleted(self):
        """
        Returns false unless all the subtasks have been completed.
        """
        completed = True
        for subtask in self._subtasks:
            if not subtask.isCompleted():
                completed = False
        return completed
    
    ##############################################################################################     
     
    def preProcess(self,manager):
        """
        In the base class, there is no need to actually load the image data, since the only sub-tasks
        are direct copies of the files. 
        """
        self.shared_image = manager.ASI(self._image_file,self._image_info_file)        
        
    ##############################################################################################  
   
    def getSubTasks(self,manager,processing_pool,network_manager):
        """
        Runs any preprocessing functions required (typically just loading the image as a shared object)
        and returns a list of subTask objects that need to be executed. Note that subTask objects are
        a sub-class of processTask and are therefore designed to be passed to a processQueueBase object
        for execution.
        """
        self.preProcess(manager)
       
        #build the subtask objects
        for output in self._outputs:
            function = TYPES[output.type]
            args = (self.shared_image,output,self._settings_manager)
             
            task = processing_pool.createTask(function,*args)
             
            #figure out where to save this output.
        
            #get the capture time from the image header
            capture_time_string = self.shared_image.getInfo()['header']['Creation Time']
            
            capture_time = datetime.datetime.strptime(capture_time_string,"%d %b %Y %H:%M:%S %Z")
            
            filename = capture_time.strftime(output.filename_format)
            
            if output.folder_on_host != "" and output.folder_on_host != None:
                path_to_save_to = os.path.normpath(output.folder_on_host + "/" + output.folder_on_host + filename)
            else:
                path_to_save_to = os.path.normpath(output.folder_on_host + "/" + filename)
            
            self._subtasks.append(subTask(task,path_to_save_to,output.file_on_server,network_manager))
             
        return self._subtasks

    ##############################################################################################  
    
    def exit(self):        
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
        #load image as a shared object
        outputTaskBase.preProcess(self,manager)
        self.shared_image.load()

    ##############################################################################################           
##############################################################################################  