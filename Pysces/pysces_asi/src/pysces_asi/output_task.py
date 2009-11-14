#Copyright (C) Nial Peters 2009
#
#This file is part of pysces_asi.
#
#pysces_asi is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pysces_asi is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pysces_asi.  If not, see <http://www.gnu.org/licenses/>.
import os
import datetime
import threading
import traceback
import gc
import multiprocessing

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
            if (network_manager_proxy is not None):
                network_manager_proxy.start()
        
            #load the image using PASKIL
            self.image = allskyImage.new(self.image[0],self.image[1])
            
            #work out where the output should be saved
            remove_file_on_host = False
            if self.output.filename_format is not None:
                #the 'normal' case where we want the output saved on the host machine
                capture_time_string = self.image.getInfo()['header']['Creation Time']     
                capture_time = datetime.datetime.strptime(capture_time_string, "%d %b %Y %H:%M:%S %Z")     
                filename = capture_time.strftime(self.output.filename_format)
            
                if self.output.folder_on_host != "" and self.output.folder_on_host != None:
                    self.output_filename = os.path.normpath(self._folder_on_host + "/" + self.output.folder_on_host + "/" + filename)
                else:
                    self.output_filename = os.path.normpath(self._folder_on_host + "/" + filename)
            
            elif ((self.output.filename_format is None) and (self.file_on_server is not None)):
                # the case where we only want the file copied to the server
                temp_folder = settings_manager_proxy.get(['tmp dir'])['tmp dir']
                self.output_filename = os.path.normpath(temp_folder+"/"+self.file_on_server)
                remove_file_on_host = True
            else:
                # the case where we don't want any output saved
                self.output_filename = None
        
            #run the subtask execution function (this is what actually produces the output)
            output = self.function(self.image, self.output, settings_manager_proxy)
            
            #save the output on the host
            if output is not None and self.output_filename is not None:
                try:
                    output.save(self.output_filename)
                except AttributeError:
                    #this is added for compatibility with matplotlib figure objects
                    output.savefig(self.output_filename)
            
            #copy the output to the server if required
            if ((self.file_on_server is not None) and (network_manager_proxy is not None)):
                network_manager_proxy.copy_to_server(self.output_filename, self.file_on_server)
            del self.image
            
            # if we only wanted the output on the server, then remove the copy on the host
            if remove_file_on_host:
                os.remove(self.output_filename)
            
        except Exception, ex:
            traceback.print_exc()
            raise ex
        
        finally:
            #shutdown the proxies
            settings_manager_proxy.exit()
            if (network_manager_proxy is not None):
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
            
            #if we need to copy files to the web-server, then create a proxy to the NetworkManager
            if (network_manager is not None):
                network_mananger_proxy = network_manager.create_proxy()
            else:
                network_mananger_proxy = None
            
            #submit the sub_task for processing
            if output.pipelined:
                task = pipelined_processing_pool.create_task(sub_task.execute, self._settings_manager.create_proxy(), network_mananger_proxy)
                self._running_subtasks.append(task)
                pipelined_processing_pool.commit_task(task)     
                
            else:
                task = processing_pool.create_task(sub_task.execute, self._settings_manager.create_proxy(), network_mananger_proxy)
                self._running_subtasks.append(task)
                processing_pool.commit_task(task)
            
    ##############################################################################################  
    
    def wait(self):
        
        #get safe_delete option from the settings manager
        safe_delete = self._settings_manager.get(['safe_delete'])['safe_delete']
        
        self._running_subtasks_lock.acquire()
        while 0 < len(self._running_subtasks):
            self._running_subtasks[0].completed.wait()
            try:
                self._running_subtasks[0].result()
            except:
                if safe_delete:
                    self.__remove_files = False
                    self._settings_manager.set({'output':"OutputTask> Error! Processing pool failed to execute one or more sub-tasks"})
                    self._settings_manager.set({'output':"OutputTask> Leaving temporary files in place"})
                else:
                    self.__remove_files = True
                    self._settings_manager.set({'output':"OutputTask> Error! Processing pool failed to execute one or more sub-tasks"})
                    self._settings_manager.set({'output':"OutputTask> Safe delete is off, removing temporary files anyway."})
                    
            st = self._running_subtasks.pop(0)
            del st
        #force garbage collection here. This solves the memory leak problem
        gc.collect()
        
        #reap zombie processes
        try:
            multiprocessing.active_children() 
        except OSError:
            pass #if there are any syncronisation problems then just give up - it's not that important
        
        self._running_subtasks_lock.release()
   
    ##############################################################################################    
    
    def remove_temp_files(self):
        if self.__remove_files:
            os.remove(self._image_file[0])
            os.remove(self._image_file[1]) 
            
    ##############################################################################################  
##############################################################################################  
