from multitask import taskQueueBase,task
import Queue
from dataStorageClasses import captureMode
import hostManager,D80
from outputs import outputTaskHandler

class captureManager(taskQueueBase):
    
    def __init__(self,settings_manager):
        
        self._settings_manager = settings_manager
        self._host_manager = hostManager.hostManager(settings_manager)
        self._camera_manager = D80.D80CameraManager(settings_manager)
        self._output_task_handler = outputTaskHandler()
        
        taskQueueBase.__init__(self)
    
    def _processTasks(self):
        """
        Here we overwrite the _processTasks method, so that the captureManager can deal with a queue of 
        capture mode objects rather than task objects. This is a bit messy, since the object put into the
        queue could be a task object or a captureMode object, and each has to be dealt with separately.
        
        The captureManager MUST still support receiving task objects, since the exit() method relies on
        this.
        
        >>> #doc tests to ensure that the class still supports task objects
        >>> from settingsManager import settingsManager
        >>> s = settingsManager()
        >>> from multitask import Task
        >>> def output(s):
        ...    print s
        >>> t = Task(output,"Must still support tasks!")
        >>> c = captureManager(s)
        >>> c.commitTask(t)
        >>> t.result()
        Must still support tasks!
        >>> c.exit()
        
        """
        #pull the first capture mode out of the queue
        capture_mode = self._task_queue.get()   
        
        while True:
            
            #the object from the queue could be a task object, so we should try executing it first
            #before we assume that it is a capture mode - this is a bit of a hack, but is needed to 
            #make sure that the exit() method works correctly
            if isinstance(capture_mode,task):
                capture_mode.execute()
                self._task_queue.task_done()
            elif capture_mode == None:
                #nothing to do - wait for a real capture mode to come through the queue
                self._task_queue.task_done()
            elif isinstance(capture_mode,captureMode):
                #set the camera settings to those required by the capture mode
                self._camera_manager.setCaptureMode(capture_mode)
                
                #record the time before we try to take an image
                start_time = datetime.datetime.now()
                
                #update the folders on the host
                self._host_manager.updateFolders()
            
                #capture images and produce output tasks
                images = self._camera_manager.captureImage()
                self._submitOutputTasks(capture_mode,images)
            
                #wait remaining delay time, unless a new capture mode comes into the queue
                try:
                    capture_mode = self._task_queue.get(timeout=(datetime.datetime.now() - start_time < datetime.timedelta(seconds=capture_mode.delay)))
                    self._task_queue.task_done()
                except Queue.Empty:
                    #no new capture modes have come in, so we just continue with the one we have got
                    continue
            
            else:
                #if this happens then something has gone seriously wrong!
                raise TypeError,str(type(capture_mode))+" is neither a task nor a captureMode and cannot be executed by the captureManager."
            
            #check if we have met the exit condition before attempting to get the next task/captureMode
            if not self._stay_alive or (self._task_queue.empty()):
                break
            
            #sit and wait for the next task or captureMode
            capture_mode = self._task_queue.get()
            
    ##############################################################################################  
     
    def _submitOutputTasks(self,capture_mode,images):
        """
        Method produces all the output sub-tasks required by the capture mode, wraps them in an output
        task object and passes it on to the outputTaskHandler.
        """
        
        
        
    ##############################################################################################
    
    #def exit(self):
        #TODO - kill outputTaskHandler,cameraManager and host manager
    #    return
##############################################################################################             