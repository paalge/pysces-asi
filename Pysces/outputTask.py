from processing.managers import SyncManager,CreatorMethod
from PASKIL import allskyImage
import PASKIL_jpg_plugin
from outputs import TYPES
from multitask import processTask
import os


def createSubTask(shared_namespace,shared_event,folder_on_host,shared_image,output,settings_manager):
    function = TYPES[output.type]
    #return the subtask object 
    return subTask(shared_namespace,shared_event,folder_on_host,function,shared_image,output,settings_manager)

##############################################################################################  

class subTask(processTask):
    def __init__(self,shared_namespace,shared_event,folder_on_host,func,shared_image,output,settings_manager):
        self.folder_on_host = folder_on_host
        processTask.__init__(self,shared_namespace,shared_event,func,shared_image,output,settings_manager)
        self.output = output
        self.image = shared_image
    
    def isCompleted(self):
        return self.completed.isSet()
    
##############################################################################################  

class ImageManager(SyncManager):
    """
    Manager class for creating shared allskyImage objects. Note that it inherits from SyncManager
    rather than BaseManager, so it can also be used for creating other shared objects such as
    Events, Namespaces etc...
    """
    ASI = CreatorMethod(allskyImage.new)

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
         self._manager = ImageManager()
         self._manager.start()
         
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
     
    def preProcess(self):
        """
        In the base class, there is no need to actually load the image data, since the only sub-tasks
        are direct copies of the files. 
        """
        self.shared_image = self._manager.ASI(self._image_file,self._image_info_file)        
        
    ##############################################################################################  
   
    def getSubTasks(self):
        """
        Runs any preprocessing functions required (typically just loading the image as a shared object)
        and returns a list of subTask objects that need to be executed. Note that subTask objects are
        a sub-class of processTask and are therefore designed to be passed to a processQueueBase object
        for execution.
        """
        self.preProcess()
       
        #build the subtask objects
        for output in self._outputs:
             function = TYPES[output.type]
             args = (self.shared_image,output,None)
             self._subtasks.append((function,args,output.pipelined))
             
        return self._subtasks

    ##############################################################################################  
    
    def exit(self):
        #kill off the manager process
        self._manager.shutdown()
        
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
        
    def preProcess(self):
        #load image as a shared object
        outputTaskBase.preProcess(self)
        self.shared_image.load()

    ##############################################################################################           
##############################################################################################  