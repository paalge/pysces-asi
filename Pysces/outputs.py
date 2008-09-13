"""
The output module defines the different outputs that can be created using Pysces.
It provides the interface between Pysces and PASKIL
"""
from task import taskQueueBase
import processing
#List of all supported types of outputs
#TYPES = ["raw","image","quicklook","keogram","map"]

#dictionary matching processing functions to output type
#FUNCTIONS = {"raw":copyImage,"image":saveAllskyImage}

#dictionary matching types to all the settings that must be specified for them
#REQUIRED_SETTINGS = {"all":["name","type","image_type","save_on_host","filename_suffix","file_on_server"],
#                     "raw":[],
 #                    "quicklook":[],
  #                   "map":["projection_height","background_colour"]
 #                    }



class outputTaskHandler(taskQueueBase):
    
    def __init__(self):
        taskQueueBase.__init__(self)
        
        
        #create processing pool to process output requests
        self.__processing_pool = processing.Pool()
        
        #create a manager for producing shared all-sky image objects
        #self.__ASI_manager = ASIManager()
        #self.__ASI_manager.start()


    def __processTasks(self):
        while self.__stay_alive or (not self.__task_queue.empty()):
            #pull an outputTask out of the queue
            output_task = self.__task_queue.get()
            
            #if the list of sub_tasks is empty (i.e. no outputs are needed) then continue
            if len(output_task.sub_tasks) == 0:
                self.__removeTmpFiles(output_task)
                self.__task_queue.task_done()
                continue
            
            #submit loading tasks to the processing pool
            
            shared_ASIs_async = {}
            shared_ASIs = {} #dictionary of type:shared allskyImage object
            for type,image in output_task.image_files.items():
                shared_ASIs_async[type] = self.__processing_pool.apply_async(self.preProcess, args=(image[0],image[1]))
           
            #wait for preProcessing tasks to complete
            for type,async_result in shared_ASIs_async.items():
                shared_ASIs[type] = shared_ASIs_async[type].get()
            
            #submit the subtasks for processing
            for sub_task in output_task.sub_tasks:
                #only process this subtask if it hasn't been done already
                if not sub_task.completed:
                    type = sub_task.type
                    self.__processing_pool.apply_async(FUNCTIONS[type], args=(shared_ASIs[type],sub_task))
            
            #remove temporary files - note that this is only done when all the sub_tasks have been completed
            self.__removeTmpFiles(output_task)
            
            #tell the queue that execution is complete
            self.__task_queue.task_done()
            
    
    def __removeTmpFiles(self,output_task):
        
        #create a separate thread to remove the files when all the sub_tasks have been completed
        t = threading.Thread(target = self.__tmpFileRemover, args = (output_task,))
        t.start()
    
    def __tmpFileRemover(self,output_task):
        
        while True:
            flag = True
            
            #check all the sub_tasks to see if they have been completed
            for sub_task in output_task.sub_tasks:
                if not sub_task.completed:
                    flag = False
            
            if flag:
                #if all sub_tasks are complete, then delete the temp files
                for image_file,info_file in output_task.image_files.values():
                    try:
                        os.remove(image_file)
                    except:
                        pass
                    try:
                        os.remove(info_file)
                    except:
                        pass
                return
            else:
                #otherwise, give the processing pool a bit longer and then try again
                time.sleep(10)
            
    def preProcess(self,image_filename,info_filename):
        """
        Function loads an allsky image as a shared allskyImage object and performs basic pre-processing on it
        such as rotating, centering etc.
        """
        
            
            
            