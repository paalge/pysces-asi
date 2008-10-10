from __future__ import with_statement

import os
import string
import stat
import shutil

from processing import Manager
from threading import Thread
from subprocess import Popen, PIPE

from multitask import taskQueueBase, remoteTask


class networkManagerProxy(taskQueueBase):
    
    def __init__(self,id,input_queue,output_queue):
        self.id = id
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.started = False

    ##############################################################################################
    
    def start(self):
        taskQueueBase.__init__(self)
        self.started = True
        
    ##############################################################################################    
    
    def exit(self):
        """
        Note that the exit method only kills the proxy, not the master. However, it does
        remove the proxy from the master, closing the shared queue between them.
        """
        task = remoteTask(self.id,"destroy proxy",self.id)
        
        self.output_queue.put(task)
        
        taskQueueBase.exit(self)
        
    ##############################################################################################
        
    def copyToServer(self,source,destination):
        assert self.started
        #create task
        task = self.createTask(self.__copyToServer,source,destination)
    
        #submit task
        self.commitTask(task)
    
        #return result when task has been completed
        return task.result()

    ##############################################################################################
    
    def __copyToServer(self,source,destination):
        task = remoteTask(self.id,"copyToServer",source,destination)
        
        self.output_queue.put(task)
        
        result = self.input_queue.get()
        
        if isinstance(result,Exception):
            raise result
        
        return result

    ##############################################################################################
##############################################################################################


class networkManager(taskQueueBase):
    
    def __init__(self,settings_manager):
        self.__settings_manager = settings_manager
        self.__awaiting_password = False
        home = os.path.expanduser('~')
        self._mount_point = home+"/.Pysces/servers/web"
        
        taskQueueBase.__init__(self)
        
        #define method to string mappings - notice that these should be the thread safe public methods!
        self._methods = {"copyToServer":self.copyToServer,"destroy proxy":self._commitDestroyProxy}
        
        self._manager = Manager()
        self._remote_input_queue = self._manager.Queue()
        self._output_queues = {}
        #create thread to handle remote tasks
        self.remote_task_thread = Thread(target = self._processRemoteTasks)
        self.remote_task_thread.start()
        
        self._mountServer()

    ##############################################################################################                 
            
    def _commitDestroyProxy(self,id):
        #create task
        task = self.createTask(self._destroyProxy,id)
        
         #submit task
        self.commitTask(task)
        
        #return result when task has been completed
        return task.result()

    ##############################################################################################
      
    def _isMounted(self):
        glob_vars = self.__settings_manager.get(["web_server"])
        
        #read the list of mounted filesystems from the proc/mounts file. It needs
        #to come from here rather then mtab, since cifs does not always update mtab.
        with open("/proc/mounts","r") as fp:
            mounted_list = fp.read()

        if mounted_list.count(glob_vars['web_server']+" "+self._mount_point) != 0:
            return True
        else:
            return False

    ##############################################################################################         
    
    def _mountServer(self):
        if ((not self._isMounted()) and (not self.__awaiting_password)):
            self.__awaiting_password = True
            home = os.path.expanduser('~')
            glob_vars = self.__settings_manager.get(["web_server","web_username"])
            
            
            #build mounting script
            with open(home+"/.Pysces/mount-script.sh","w") as fp:
                
                fp.write("#!/bin/sh\n")
                fp.write("echo \"### Password required to mount web server ###\"\n")
                fp.write("sudo mount.cifs \""+glob_vars['web_server']+"\" \""+self._mount_point+"\" -o user=\""+glob_vars['web_username'] +"\", rw,\n")
                fp.write("sleep \"15\"")
                
            #make mount script executable
            os.chmod(home+"/.Pysces/mount-script.sh",stat.S_IRWXU+stat.S_IRWXO+stat.S_IRWXG)
            
            #run script in xterm window
            p = Popen("xterm -e "+home+"/.Pysces/mount-script.sh",shell=True,stdout=PIPE,stderr=PIPE)
            
            #wait for process to finish
            p.wait()
            
            #remove script file
            os.remove(home+"/.Pysces/mount-script.sh")
            
            self.__awaiting_password = False
            
    ##############################################################################################
    
    def copyToServer(self,source,dest):
        #create task
        task = self.createTask(self._copyToServer,source,dest)
        
        #submit task
        self.commitTask(task)
        
        #return result when task has been completed
        return task.result()
                    
    ##############################################################################################            
    
    def _copyToServer(self,source,dest):
        folder_on_server = self.__settings_manager.get(["web_dir"])["web_dir"]
        os.chmod(source,stat.S_IRWXU+stat.S_IRWXO+stat.S_IRWXG)
        shutil.copyfile(source,os.path.normpath(self._mount_point + "/" + folder_on_server + "/" + dest))
        self.__settings_manager.set({"output": "networkManager> Copied file to server"}) 
    
    ##############################################################################################                 
                
    def exit(self):
        taskQueueBase.exit(self)
        self._remote_input_queue.put(None)
        self.remote_task_thread.join()
        self._manager.shutdown()
    
    ##############################################################################################         
    
    def _destroyProxy(self,id):
        """
        Removes the queue shared with the specified proxy.
        """
        self._output_queues.pop(id)

    ##############################################################################################         

    def _processRemoteTasks(self):
        """
        This method is run in a separate thread. It pulls remote task objects out of the shared
        queue object (shared between the master(=this class), and all the proxies) and commits the
        task to the internal task queue (by calling one of the public methods of the master class.
        The result is returned to the proxy via another shared queue (only shared between one proxy
        and the master).
        """
        while self._stay_alive:
            remote_task = self._remote_input_queue.get()
            
            if remote_task == None:
                continue
            
            try:
                result = self._methods[remote_task.method_name](*remote_task.args,**remote_task.kwargs)
                if remote_task.method_name != "destroy proxy":
                    #if the proxy has been destroyed then this queue won't exist any more!
                    self._output_queues[remote_task.id].put(result)
            
            except Exception,ex:
            
                if remote_task.method_name != "destroy proxy":
                    #if the proxy has been destroyed then this queue won't exist any more!
                    self._output_queues[remote_task.id].put(ex)
            
    ############################################################################################## 
   
    def createProxy(self):

        #create task
        task = self.createTask(self._createProxy)
        
         #submit task
        self.commitTask(task)
        
        #return result when task has been completed
        return task.result()   

    ##############################################################################################
    
    def _createProxy(self):
        #create a unique ID for the proxy
        current_ids = self._output_queues.keys()
        
        if len(current_ids) > 0:
            id = max(current_ids) + 1
        else:
            id = 0
        
        proxy_input_queue = self._manager.Queue()
        
        self._output_queues[id] = proxy_input_queue
        
        return networkManagerProxy(id,proxy_input_queue,self._remote_input_queue)

    ##############################################################################################
##############################################################################################    
               