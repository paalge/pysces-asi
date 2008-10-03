"""
The settingsManager module provides the settingsManager class for managing all the settings (global
variables) for Pysces. 
"""
import os
import persist,settingsFileParser
from multitask import taskQueueBase,remoteTask
from processing import Manager
from threading import Thread
import cPickle

class settingsManagerProxy(taskQueueBase):
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
        
    def get(self,name):
        assert self.started
        #create task
        task = self.createTask(self._get,name)
    
        #submit task
        self.commitTask(task)
    
        #return result when task has been completed
        return task.result()

    ##############################################################################################
    
    def create(self,name,value,persistant=False):
        assert self.started
        
        #create task
        task = self.createTask(self._create,name,value,persistant=persistant)
    
        #submit task
        self.commitTask(task)
    
        #return result when task has been completed
        return task.result()
    
    ##############################################################################################         
    
    def operate(self,name,func,*args,**kwargs):
          
        #create task
        task = self.createTask(self.__operate,name,func,*args,**kwargs)
        
        #submit task
        self.commitTask(task)
        
        #return result when task has been completed
        return task.result()
            
    ##############################################################################################     
     
    def register(self,name,callback, variables):
        
        #create task
        task = self.createTask(self.__register,name,callback,variables)
        
        #submit task
        self.commitTask(task)
        
        #return result when task has been completed
        return task.result()   
             
    ############################################################################################## 
    
    def set(self,variables):
        
        #check that variables is a list or tuple
        if type(variables) != type(dict()):
            raise TypeError,"Expecting dictionary containing name:value pairs"
        
        #create task
        task = self.createTask(self.__set,variables)
        
        #submit task
        self.commitTask(task)
        
        #return result when task has been completed
        return task.result()
    
    ############################################################################################## 
    
    def unregister(self,id):

        #create task
        task = self.createTask(self.__unregister,id)
        
         #submit task
        self.commitTask(task)
        
        #return result when task has been completed
        return task.result()
    
    ##############################################################################################    
                
    def __get(self,name):
        task = remoteTask(self.id,"get",name)
        
        self.output_queue.put(task)
        
        result = self.input_queue.get()
        
        return result
    
    ##############################################################################################    
    
    def __set(self,variables):
        task = remoteTask(self.id,"set",variables)
        
        self.output_queue.put(task)
        result = self.input_queue.get()
        
        return result
    
    ##############################################################################################        
    
    def __create(self,name,value,persistant=False):
        task = remoteTask(self.id,"create",name,value,persistant=persistant)
        
        self.output_queue.put(task)
        
        result = self.input_queue.get()
        
        return result

    ##############################################################################################        
    
    def __operate(self,name,func,*args,**kwargs):
        
        #pickle the function into a string ready to be sent to remote object
        pickled_func = func
        task = remoteTask(self.id,"operate",pickled_func,*args,**kwargs)
        
        self.output_queue.put(task)
        
        result = self.input_queue.get()
        
        return result
    
    ##############################################################################################        
    
    def __register(self,name,callback, variables):    
        
        #pickle the function into a string ready to be sent to remote object
        pickled_callback = cPickle.dumps(callback)
        
        task = remoteTask(self.id,"register",pickled_callback,variables)
        
        self.output_queue.put(task)
        
        result = self.input_queue.get()
        
        return result
    
    ##############################################################################################        
        
    def __unregister(self,id):
        task = remoteTask(self.id,"unregister",id)
        
        self.output_queue.put(task)
        
        result = self.input_queue.get()
        
        return result 
    
    ##############################################################################################        
##############################################################################################            
           
class settingsManager(taskQueueBase):
    """
    The settingsManager class is in charge of all global variables used in Pysces. It allows 
    thread-safe access and modification to the global variables by pipelining requests from
    multiple threads/processes and executing them sequentially. It allows callback functions
    to be registered to particular variables and executes them each time the variable is set.
    It also deals with updating the settings file when the program exits.
    
    The settingsManager inherits from taskQueueBase, meaning that requests from external threads
    are queued and processed sequentially by an internal worker thread. It is very important
    therefore that external threads only call public methods (methods with names that do not
    start with an underscore). It is equally important that internal methods (those called by 
    the worker thread) do not call the public methods.
        
    """
    def __init__(self):
        
        taskQueueBase.__init__(self)
        
        #define method to string mappings - notice that these should be the thread safe public methods!
        self._methods = {"get":self.get,"set":self.set,"create":self.create,"register":self.register,"unregister":self.unregister,"operate":self.operate,"destroy proxy":self._commitDestroyProxy}
        
        self._manager = Manager()
        self._remote_input_queue = self._manager.Queue()
        #create thread to handle remote tasks
        self.remote_task_thread = Thread(target = self._processRemoteTasks)
        self.remote_task_thread.start()
        
        try:
            #define private attributes
            self.__variables = {}
            self.__callbacks = {}
            self.__callback_ids = {}
            self._output_queues = {}
            
            #hard code settings file location and create a parser
            home = os.path.expanduser("~")
            self.__settings_file_parser = settingsFileParser.settingsFileParser(home+"/.Pysces/settings.txt")
            
            #create an output variable - this is used instead of printing to stdout, making it easier
            #for a top layer application (e.g. a GUI) to access this data
            self.__create("output","")      
            
            #load settings file
            settings = self.__settings_file_parser.getSettings()
                 
            #store settings in variables
            for key in settings.keys():
                self.__create(key,settings[key])
                        
            #create persistant storage class
            self.__persistant_storage = persist.persistantStorage(home+"/.Pysces",self)
            
            #load persistant values into variables
            persistant_data = self.__persistant_storage.getPersistantData()
            
            for key in persistant_data.keys():
                self.__create(key,persistant_data[key],persistant=True)
        
        except Exception,ex:
            #if an exception occurs then we need to shut down the threads and manager before exiting
            taskQueueBase.exit(self)
            self._remote_input_queue.put(None)
            self.remote_task_thread.join()
            self._manager.shutdown()
            raise ex
               
    ##############################################################################################
    ##############################################################################################    
    #define public methods - note that the settingsManager worker thread does not have ownership of these
    #methods, and so private methods MUST NOT call them - this will lead to thread lock
    ##############################################################################################
    ##############################################################################################
    
    def create(self,name,value,persistant=False):
        """
        Creates a new global variable called name and initialises it to value. 
        
        New global values can be created either as persistant (their value on program exit will be stored
        and loaded on program re-start), or as non-persistant (they will be destroyed on exit). Note that 
        if you create a variable as persistant, then you will need to enclose your create() statement in a
        try/except block since the variable will be created automatically the next time the program is run
        and attempting to create a variable that already exists causes a ValueError exception.
        
        >>> s = settingsManager()
        >>> s.create("new_var","initial value")
        >>> print s.get(["new_var"])
        {'new_var': 'initial value'}
        >>> s.create("new_var","new_value2")
        Traceback (most recent call last):
        ...
        ValueError: A variable called new_var already exists.
        >>> s.exit()
        """
        
        #create task
        task = self.createTask(self.__create,name,value,persistant=persistant)
        
         #submit task
        self.commitTask(task)
        
        #return result when task has been completed
        return task.result()
              
    ##############################################################################################
    
    def exit(self):
        """
        Updates the settings file and kills the persistant storage class. This must be called when 
        you are finished with the settingsManager in order to clean up and stop the worker thread.
        
        Some doctests:
        
        >>> import threading
        >>> print threading.activeCount()
        1
        >>> s = settingsManager()
        >>> print threading.activeCount()
        2
        >>> s.exit()
        >>> print threading.activeCount()
        1

        """
        try:
            #kill the persistant storage
            self.__persistant_storage.exit()
        
            #update the settings file
            self.set({"output": "settingsManager> Updating settings file"})
            self.__settings_file_parser.updateSettingsFile(self.__variables)
        finally:
            taskQueueBase.exit(self)
            self._remote_input_queue.put(None)
            self.remote_task_thread.join()
            self._manager.shutdown()
    
    ##############################################################################################    
    
    def get(self,names):
        """
        Returns a dictionary of name:value pairs for all the names in the names list. Attempting
        to get a name which doesn't exist will result in a KeyError.
        
        >>> s = settingsManager()
        >>> s.create("new_var",1)
        >>> s.create("new_var2",2)
        >>> globs = s.get(["new_var","new_var2"])
        >>> print globs["new_var2"]
        2
        >>> globs = s.get(["some variable that doesn't exist"])
        Traceback (most recent call last):
        ...
        KeyError: "some variable that doesn't exist"
        >>> import os
        >>> s.create("home","${HOME}")
        >>> print s.get(["home"])["home"] == os.path.expanduser("~")
        True
        >>> s.exit()
        
        """
                
        #create task
        task = self.createTask(self.__get,names)
        
        #submit task
        self.commitTask(task)
        
        #return result when task has been completed
        return task.result()
    
    ##############################################################################################      
    
    def operate(self,name,func,*args,**kwargs):
        """
        The operate() method provides a way to apply functions to global variables in a thread-safe
        way. For example if we want to increment a value, we might do:
        
        >>> s = settingsManager()
        >>> s.create("new_var",1)
        >>> s.set({'new_var':s.get(['new_var'])['new_var']+1})
        >>> print s.get(["new_var"])['new_var']
        2
        
        However, this is a bad idea! It is possible that between s.get() returning and s.set() being
        executed that another thread may have re-set the variable to a different value. This change
        will then be overwritten by the increment to the old value. Instead, we should use the 
        operate() method to increment our value     
        
        >>> def increment(value):
        ...    return value + 1
        >>> s.operate("new_var",increment)
        >>> print s.get(["new_var"])['new_var']
        3
        
        This ensures that the entire increment operation is completed before any other threads/processes
        are given access to the variable.
        
        The name argument should be the name of a global variable. The func argument should be a callable
        object that takes the current value of the variable as its first argument and returns the new value.
        Additional arguments for the function can be specified using *args and **kwargs. For example, they 
        can be used to perform list operations:
        
        >>> def appendToList(list,value_to_append):
        ...     list.append(value_to_append)
        ...     return list
        >>> s.create("new_list",[])
        >>> s.operate("new_list",appendToList,42)
        >>> print s.get(["new_list"])['new_list']
        [42]
        >>> s.exit()
        
        
        """
          
        #create task
        task = self.createTask(self.__operate,name,func,*args,**kwargs)
        
        #submit task
        self.commitTask(task)
        
        #return result when task has been completed
        return task.result()
            
    ##############################################################################################     
     
    def register(self,name,callback, variables):
        """
        Registers a callback function to a variable and returns a callback id. The callback function will
        be run each time the variable is set. The name argument should be the name of the variable that the
        callback is associated with, callback is a callable object which should take a dict as its only 
        argument, variables should be a list of names of variables that should be put into the dict passed
        to the callback.
        >>> s = settingsManager()
        >>> s.create("new","value")
        >>> print s.get(["new"])
        {'new': 'value'}
        >>> def f(s):
        ...    print s
        >>> id = s.register("new",f,["new"])
        >>> print id
        0
        >>> s.set({"new":"hello!"})
        {'new': 'hello!'}
        
        The output produced is generated by the callback function f. However, if we register f() with a 
        different variable as well and then set both, f is only called once:
        >>> s.create("new2","value2")
        >>> id2 = s.register("new2",f,["new"])
        >>> s.set({"new": "hello!", "new2": "hello again!"})
        {'new': 'hello!'}
        
        The id returned by register() can be used to unregister the callback
        >>> s.unregister(id)
        >>> s.set({"new":"hello again!"})
        
        No output is produced, because no callback was run
        >>> s.exit()
        """
        
        #create task
        task = self.createTask(self.__register,name,callback,variables)
        
        #submit task
        self.commitTask(task)
        
        #return result when task has been completed
        return task.result()   
             
    ############################################################################################## 
    
    def set(self,variables):
        """
        Sets the values of a group of global variables. The variables argument should be a dict
        of name:value pairs to be set.
        
        >>> s = settingsManager()
        >>> s.create("new_var","initial value")
        >>> s.create("another_new_var","another new value")
        >>> print s.get(["new_var"])["new_var"]
        initial value
        >>> s.set({"new_var":"Hello","another_new_var":"world!"})
        >>> print s.get(["new_var"])["new_var"]
        Hello
        >>> print s.get(["another_new_var"])["another_new_var"]
        world!
        >>> s.exit()
        
        """
        
        #check that variables is a list or tuple
        if type(variables) != type(dict()):
            raise TypeError,"Expecting dictionary containing name:value pairs"
        
        #create task
        task = self.createTask(self.__set,variables)
        
        #submit task
        self.commitTask(task)
        
        #return result when task has been completed
        return task.result()
    
    ############################################################################################## 
    
    def unregister(self,id):
        """
        Unregisters the callback specified by the id argument - see register()
        """
        #create task
        task = self.createTask(self.__unregister,id)
        
         #submit task
        self.commitTask(task)
        
        #return result when task has been completed
        return task.result()
    
    ##############################################################################################     
    
    def createProxy(self):
        """
        Returns a proxy object for the settingsManager. This can be passed to other processes
        allowing them to access and modify the global variables, i.e. it allows the global
        variables to be shared across multiple processes. The proxy object is thread safe 
        (it is also sub-classed from taskQueueBase). The proxy cannot be used to generate 
        further proxies, so the child process cannot spawn its own child process and use its
        proxy to generate a proxy to pass to it.
        """
        #create task
        task = self.createTask(self._createProxy)
        
         #submit task
        self.commitTask(task)
        
        #return result when task has been completed
        return task.result()   
    
    ##############################################################################################     
    ##############################################################################################   
    #define private methods - these are only executed by the settingsManager worker thread and the 
    #thread that calls __init__
    ##############################################################################################
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
        
        return settingsManagerProxy(id,proxy_input_queue,self._remote_input_queue)
        
##############################################################################################         
    
    def _commitDestroyProxy(self,id):
        #create task
        task = self.createTask(self._destroyProxy,id)
        
         #submit task
        self.commitTask(task)
        
        #return result when task has been completed
        return task.result()
        
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
        queue object (shared between the master=this class, and all the proxys) and commits the
        task to the internal task queue (by calling one of the public methods of the master class.
        The result is returned to the proxy via another shared queue (only shared between one proxy
        and the master).
        """
        while self._stay_alive:
            remote_task = self._remote_input_queue.get()
            
            if remote_task == None:
                continue
            
            result = self._methods[remote_task.method_name](*remote_task.args,**remote_task.kwargs)
            
            
            if remote_task.method_name != "destroy proxy":
                #if the proxy has been destroyed then this queue won't exist any more!
                self._output_queues[remote_task.id].put(result)
            
    ##############################################################################################                
    
    def __create(self,name,value,persistant=False):

        if self.__variables.has_key(name):
            raise ValueError,"A variable called "+name+" already exists."
        
        self.__variables[name] = value
        self.__callbacks[name] = []
        
        if persistant:
            self.__persistant_storage.add(name)
          
    ##############################################################################################

    def __get(self,names):
               
        #build a dictionary of the variables
        variables = {}
        
        for name in names:
            #resolve any shell variables
            if type(self.__variables[name]) == type(str()) and self.__variables[name].count("$") != 0:
                variables[name] = os.path.expandvars(self.__variables[name])
            else:
                variables[name] = self.__variables[name]

        return variables
    
    ##############################################################################################           
    
    def __operate(self,name,sfunc,*args,**kwargs):
        
        #check if function has been pickled
        if type(sfunc) == type(str()):
            #if it has then unpickle it!
            func = cPickle.loads(sfunc)
        else:
            func = sfunc
        
        variable = self.__get([name])
        
        new_value = func(variable[name],*args,**kwargs)
        
        self.__set({name:new_value})
    
    ##############################################################################################
    
    def __register(self,name, scallback, variables):

        #check that 'name' actually exists
        if not self.__variables.has_key(name):
            raise KeyError, "Cannot register callback for "+str(name)+". Variable does not exist"
        
        #create a unique id for this callback registration. This is used to unregister callbacks
        try:
            new_callback_id = max(self.__callback_ids.keys()) + 1
        except ValueError:
            new_callback_id = 0
        
        #check if callback function has been pickled
        if type(scallback) == type(str()):
            #if it has then unpickle it!
            callback = cPickle.loads(scallback)
        else:
            callback = scallback
        
        #callback_ids dict maps callabck ids to callback functions
        self.__callback_ids[new_callback_id] = (callback,variables)
        
        #callbacks dict maps names to a list of ids 
        self.__callbacks[name].append(new_callback_id)
        
        return new_callback_id
        
    ##############################################################################################                      
           
    def __set(self,group):
        
        #check there are no duplicate entries in the group
        keys = group.keys()
        for key in keys:
            if keys.count(key) > 1:
                raise ValueError,"Group cannot contain duplicate entries"

        #set all the values and build a list of unique callbacks (the uniqueness criteria is based on the
        #function object)
        unique_callbacks = []
        unique_callback_functions = []
        for key in keys:
            self.__variables[key] = group[key]
             
            for id in self.__callbacks[key]:
                function,arguments = self.__callback_ids[id]
                if function != None:
                    if unique_callback_functions.count(function) == 0:
                        unique_callbacks.append((function,arguments))
                        unique_callback_functions.append(function)
        
        #run unique callbacks
        for function,arguments in unique_callbacks:
            #get globals variables for callback
            arg_values = self.__get(arguments)
            if len(arg_values) == 0:
                function()
            else:
                function(arg_values)
            
    ##############################################################################################     
    
    def __unregister(self,id):

        for list_of_ids in self.__callbacks.values():
            if list_of_ids.count(id) != 0:
                list_of_ids.remove(id)
        
        self.__callback_ids.pop(id)
           
    ##############################################################################################     
##############################################################################################           
           