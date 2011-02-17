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
"""
The capture module provides a single class, the CaptureManager. This recieves
CaptureMode objects from the Scheduler class, sets the camera configs, and 
then takes images continuously until it recieves a different CaptureMode. It 
creates OutputTasks for each image captured, and passes these to the 
OutputTaskHandler for processing.

The CaptureManager also creates a HostManager object and uses this to update the
folder structure on the host before each image is captured.
"""
import traceback
import Queue
import datetime
import time
import os

import host
import output_task_handler

from multitask import ThreadQueueBase, ThreadTask
from data_storage_classes import CaptureMode
from output_task import create_output_tasks
from camera import GphotoError
import camera

##############################################################################################  

class CaptureManager(ThreadQueueBase):
    """
    The CaptureManager class is sub-classed from ThreadQueueBase, allowing
    it to run in its own thread. The _process_tasks() method is overwritten
    to allow it to accept CaptureMode objects in addition to task objects.
    """
    def __init__(self, settings_manager):
        ThreadQueueBase.__init__(self,name="CaptureManager")
        
        try:
            self._settings_manager = settings_manager
            self._host_manager = host.HostManager(settings_manager)
            
            #get the correct plugin for the camera
            home = os.path.expanduser("~")
            cameras_folder = home + "/.pysces_asi/cameras"           
            camera_plugin_name = self._settings_manager.get(["camera"])['camera']
            camera.load_camera_plugins(cameras_folder)          
            self._camera_manager = camera.cameras[camera_plugin_name](settings_manager)
            
            self._output_task_handler = output_task_handler.OutputTaskHandler(settings_manager)

        except Exception, ex:
            traceback.print_exc()
            self._settings_manager.set({"output":"CameraManager> ** ERROR! **  "+ex.message})
            self.exit()
            raise ex

    ##############################################################################################  
            
    def _process_tasks(self):
        """
        Here we overwrite the _process_tasks method, so that the CaptureManager can deal with a queue of 
        CaptureMode objects rather than ThreadTask objects. This is a bit messy, since the object put into the
        queue could be a task object or a CaptureMode object, and each has to be dealt with separately.
        
        The CaptureManager MUST still support receiving task objects, since the exit() method relies on
        this.
        """
        #pull the first capture mode out of the queue
        capture_mode = self._task_queue.get()   
        
        while self._stay_alive or (not self._task_queue.empty()):
            
            #the object from the queue could be a task object, so we should try executing it first
            #before we assume that it is a capture mode - this is a bit of a hack, but is needed to 
            #make sure that the exit() method works correctly
            if isinstance(capture_mode, ThreadTask):
                capture_mode.execute()
                self._task_queue.task_done()
            elif capture_mode == None:
                #nothing to do - wait for a real capture mode to come through the queue
                self._task_queue.task_done()
            elif isinstance(capture_mode, CaptureMode):
                #The somewhat unstable nature of gphoto makes this loop prone to failure
                #if the gphoto call fails then we just skip this image and carry on with
                # the next one
                
                try:
                    #set the camera settings to those required by the capture mode
                    self._camera_manager.set_capture_mode(capture_mode)
                    
                    #record the time before we try to take an image
                    start_time = datetime.datetime.utcnow()
                    
                    #update the folders on the host
                    self._host_manager.update_folders(capture_mode)
                    
                    #get the current folder on the host
                    folder_on_host = self._settings_manager.get(["output folder"])["output folder"]
                    
                    #capture images and produce output tasks
                    images = self._camera_manager.capture_images()
                
                except GphotoError: #RuntimeError is rasied when gphoto fails in the cameraManager
                    self._settings_manager.set({"output": "CaptureManager> Error! Failed to capture/download image."})
                    images = None
                
                if images != None:
                    #create an outputTask obejct for each image type and pass them to the ouputTaskHandler
                    output_tasks = create_output_tasks(capture_mode, images, folder_on_host, self._settings_manager)
                    i = 0
                    while i < len(output_tasks):
                        try:
                            self._output_task_handler.commit_task(output_tasks[i])
                            i += 1
                        except Queue.Full:
                            #the outputTaskHandler is busy, wait for a bit and then retry
                            print "waiting for output_task_handler"
                            time.sleep(1)                
            
                #wait remaining delay time, unless a new capture mode comes into the queue
                try:
                    #if the delay time has already been exceeded then set remaining delay to 0
                    #otherwise it will be negative and cause problems
                    if (datetime.datetime.utcnow() - start_time) > datetime.timedelta(seconds=capture_mode.delay):
                        remaining_delay_time = 0
                    else:
                        remaining_delay_time = (datetime.timedelta(seconds=capture_mode.delay) - (datetime.datetime.utcnow() - start_time)).seconds
                    if remaining_delay_time < 0:
                        remaining_delay_time = 0
                    
                    capture_mode = self._task_queue.get(timeout=remaining_delay_time)
                    self._task_queue.task_done()
                    continue
                except Queue.Empty:
                    #no new capture modes have come in, so we just continue with the one we have got
                    continue
            
            else:
                #if this happens then something has gone seriously wrong!
                raise TypeError, str(type(capture_mode))+" is neither a task nor a captureMode and cannot be executed by the CaptureManager."
            
            #check if we have met the exit condition before attempting to get the next task/captureMode
            if not self._stay_alive:
                break
            
            #sit and wait for the next task or captureMode
            capture_mode = self._task_queue.get()

        self._exit_event.set()
        
    ##############################################################################################  
    
    def exit(self):
        """
        Shuts down all the objects that this class created, and then kills its own
        internal worker thread.
        """
        #kill own worker thread
        ThreadQueueBase.exit(self)
        
        #clear the plugins list
        camera.clear_plugins_list()
        
        try:
            self._camera_manager.exit()
        except AttributeError:
            pass
        
        try:
            self._output_task_handler.exit()
        except AttributeError:
            pass  
     
    ##############################################################################################
##############################################################################################             