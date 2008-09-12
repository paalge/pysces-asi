"""
The settingsManager module provides classes and functions for managing all the settings (global
variables) for Pysces. Functions for reading and writing to the ascii settings file are provided
in addition to the settingsManager class.
"""


from __future__ import with_statement
import os,time
import persist
from multitask import Task,taskQueueBase

        
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
        
        #define private attributes
        self.__variables = {}
        self.__callbacks = {}
        self.__callback_ids = {}
        
        #hard code file locations and create variables
        home = os.path.expanduser("~")
        self.__create("Settings File",home+"/.Pysces/settings.txt")
        self.__create("persist filename",home+"/.Pysces/persistant")
        self.__create("current capture mode","")
        self.__create("most recent images","")
        self.__create("output","")
        self.__create("persist names",[])
        self.__create("day","")
        self.__create("Capture Time","")       
        
        #load settings file
        settings = loadSettingsFile(home+"/.Pysces/settings.txt")
             
        #store settings in variables
        for key in settings.keys():
            self.__create(key,settings[key])
                    
        #create persistant storage class
        self.__persistant_storage = persist.persistantStorage(self)
        
        #load persistant values into variables
        persistant_data = self.__persistant_storage.getPersistantData()
        
        for key in persistant_data.keys():
            self.__create(key,persistant_data[key],persistant=True)
            
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
        task = Task(self.__create,name,value,persistant=persistant)
        
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
        >>> threading.activeCount()
        1
        >>> s = settingsManager()
        >>> threading.activeCount()
        2
        >>> s.exit()
        >>> threading.activeCount()
        1

        """
        #kill the persistant storage
        self.__persistant_storage.exit()
        
        #update the settings file
        self.set({"output": "settingsManager> Updating settings file"})
        self.__updateSettingsFile()
        taskQueueBase.exit(self)
    
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
        >>> s.exit()
        
        """
                
        #create task
        task = Task(self.__get,names)
        
        #submit task
        self.commitTask(task)
        
        #return result when task has been completed
        return task.result()
    
    ##############################################################################################      
    
    def operate(self,name,func):
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
        >>> s.exit()
        
        This ensures that the entire increment operation is completed before any other threads/processes
        are given access to the variable.
        
        The name argument should be the name of a global variable. The func argument should be a callable
        object that takes the current value of the variable as it's only argument and returns the new value.
        """
          
        #create task
        task = Task(self.__operate,name,func)
        
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
        task = Task(self.__register,name,callback,variables)
        
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
        task = Task(self.__set,variables)
        
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
        task = Task(self.__unregister,id)
        
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
        
    def __create(self,name,value,persistant=False):

        if self.__variables.has_key(name):
            raise ValueError,"A variable called "+name+" already exists."
        
        self.__variables[name] = value
        self.__callbacks[name] = []
        
        if persistant:
            self.__variables["persist names"].append(name)
          
    ##############################################################################################

    def __get(self,names):
        
        result={}
        for name in names:
            result[name] = self.__variables[name]
        
        return result
    
    ##############################################################################################           
    
    def __operate(self,name,func):

        variable = self.__get([name])
        
        new_value = func(variable[name])
        
        self.__set({name:new_value})
    
    ##############################################################################################
    
    def __register(self,name, callback, variables):

        #check that 'name' actually exists
        if not self.__variables.has_key(name):
            raise KeyError, "Cannot register callback for "+str(name)+". Variable does not exist"
        
        #create a unique id for this callback registration. This is used to unregister callbacks
        try:
            new_callback_id = max(self.__callback_ids.keys()) + 1
        except ValueError:
            new_callback_id = 0
        
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
            function(arg_values)
            
    ##############################################################################################     
    
    def __unregister(self,id):

        for list_of_ids in self.__callbacks.values():
            if list_of_ids.count(id) != 0:
                list_of_ids.remove(id)
        
        self.__callback_ids.pop(id)
           
    ##############################################################################################     
    
    def __updateSettingsFile(self):
        """
        Writes any changes to the settings file.
        """
        glob_vars = self.get(["Settings File"])
        
        #open current settings file for reading
        with open(glob_vars["Settings File"],'r') as fp:
        
           #open temporary file to write to
            with open(glob_vars["Settings File"]+"-temp",'w') as ofp:
                
                #read file line by line
                i=0
                line = "not an empty string"
                while line != "":
                    line = fp.readline()
                    i+=1 #incremement line count
                    if line.isspace():
                        #write blank lines
                        ofp.write(line)
                        continue
                    
                    elif line == "":
                        #skip end of file
                        continue
                    
                    elif line.lstrip().startswith("#"):
                        #write comment lines
                        ofp.write(line)
                        continue
                    
                    elif line.lstrip().startswith("<variables>"):
                        ofp.write(line)
                        i=updateVariables(fp,ofp,i,self.__variables)
                        
                    elif line.lstrip().startswith("<capture mode>"):
                        ofp.write(line)
                        #record position in file of declaration
                        dec_start = fp.tell()
                        
                        #read declaration to see which capture mode this is, j is not used (unwanted line number)
                        capture_mode,j = readVariables(fp,i)
                        
                        #go back to start of declaration
                        fp.seek(dec_start)
                        
                        #update file
                        updateVariables(fp,ofp,i,self.__variables["capture modes"][capture_mode["name"]])
                        
                    elif line.lstrip().startswith("<schedule>"):
                        ofp.write(line)
                        updateVariables(fp,ofp,i,self.__variables["schedule"])
                    
                    elif line.lstrip().startswith("<output>"):
                        ofp.write(line)
                        #record position in file of declaration
                        dec_start = fp.tell()
                        
                        #read declaration to see which output this is, j is not used (unwanted line number)
                        output,j = readVariables(fp,i)
                        
                        #go back to start of declaration
                        fp.seek(dec_start)
                        
                        #update file
                        updateVariables(fp,ofp,i,self.__variables["output types"][output["name"]])
                    
                    elif line.lstrip().startswith("<image>"):
                        ofp.write(line)
                        #record position in file of declaration
                        dec_start = fp.tell()
                        
                        #read declaration to see which image this is, j is not used (unwanted line number)
                        image,j = readVariables(fp,i)
                        
                        #go back to start of declaration
                        fp.seek(dec_start)
                        
                        #update file
                        updateVariables(fp,ofp,i,self.__variables["image types"][image["image_type"]])
                        
                    else:
                        raise ValueError,"Unable to update settings file. Error on line "+str(i)    

        #move teporary file to settings file
        os.rename(glob_vars["Settings File"]+"-temp", glob_vars["Settings File"])
                   
    ##############################################################################################           
##############################################################################################           

def updateVariables(fp,ofp,line_no,settings):
    """
    Function writes a new settings file with the settings values stored in memory (within the 
    settingsManager class). The new file can then be copied across to the old file thus preventing
    errors in the update process from destroying the original settings file. The fp and ofp 
    arguments should be file objects for the original settings file (read) and the new settings file
    (write) respectively. line_no should be the current line number in the settings file, and settings 
    should be a dictionary of name:value pairs representing the variables contained in one declaration
    block.
    """
    
    #read file line by line
    line = "not an empty string"
    while line != "":
        line = fp.readline()
        line_no+=1 #incremement line count
        if line.isspace():
            #write blank lines
            ofp.write(line)
            continue
        elif line == "":
            #skip end of file
            continue
        elif line.lstrip().startswith("#"):
            #write comment lines
            ofp.write(line)
            continue
        elif line.lstrip().startswith("<end>"):
            ofp.write(line)
            return line_no
        elif line.count("#") == 0 and line.count("=") > 0:
            #life is easy and there is no embedded comments
            key,sep,value = line.partition("=")
            
        elif line.count("=") > 0:
            #life is harder as there are embedded comments
            line_no_comment = line
            
            #here we need to ignore escaped hashes, including escaped hashes that appear within comments
            while line_no_comment.count(r"\#") < line_no_comment.count("#"):
                line_no_comment = line_no_comment.rpartition("#")[0]
                
            key,sep,value = line_no_comment.partition("=")
        
        else:
            raise IOError, "Failed to read settings file, invalid entry on line "+str(i)
        
        #remove spaces from value and key
        value = value.lstrip().rstrip()
        key = key.lstrip().rstrip()
        
        value = eval(value)
        
        #see if the value stored in memory is different
        try:
            new_value = settings[key]
        except KeyError:
            raise RuntimeError, "Settings file has been changed. The update attempt has been aborted"
        
        if new_value != value:    
            #change value in line
            new_value = str(new_value).replace("#","\\#")
            line = line.replace(str(value),new_value,1)
            
        ofp.write(line)
    
    #return the current line number - useful to know for error messages
    return line_no
        
##############################################################################################

def readVariables(fp,line_no):
    """
    Returns a tuple (settings,line_no). Where settings is a dictionary of name:value pairs for the 
    variables within a declaration block and line_no is the line number of the end of the declaration 
    block. The fp argument should be a file object for the settings file opened for reading. line_no 
    should be the current line number in the file (the beginning of the declaration block).
    """
    
    variables = {}

    #read file line by line
    i=line_no
    line ="string"
    while line != "":
        line = fp.readline()
        line_no+=1 #incremement line count
        if line.isspace():
            #skip blank lines
            continue
        elif line == "":
            #skip the end of file
            continue
        elif line.lstrip().startswith("#"):
            #skip comment lines
            continue
        elif line.lstrip().startswith("<end>"):
            #skip rest of file on encountering <end> statement
            return variables,line_no   
        elif line.count("#") == 0 and line.count("=") > 0:
            #life is easy and there is no embedded comments
            key,sep,value = line.partition("=")
            
        elif line.count("=") > 0:
            #life is harder as there are embedded comments
            while line.count(r"\#") < line.count("#"):
                line = line.rpartition("#")[0]
                
            key,sep,value = line.partition("=")
        
        else:
            raise IOError, "Failed to read settings file, invalid entry on line "+str(i)
        
        #don't allow empty values
        if value.isspace():
            raise ValueError, "Failed to read settings file. Unintialised value on line "+str(i)
            
        #remove spaces from value and key
        value = value.lstrip().rstrip()
        key = key.lstrip().rstrip()
        
        #replace escaped hashes with hashes
        while value.count(r"\#") > 0:
            value=value.replace(r"\#","#")
        
        try:    
            variables[key] = eval(value)
        except SyntaxError:
            raise SyntaxError, "Failed to read settings file. Cannot evaluate value on line "+str(i)
        except NameError:
            raise NameError, "Failed to read settings file. Illegal value on line "+str(i)+" Should it be a string?"

    return variables,line_no

##############################################################################################

def loadSettingsFile(filename):
    """
    Reads the settings file and returns a dictionary containing the name,value pairs contained 
    in the file.
    """
    settings = {"capture modes":{},"image types":{},"output types":{}}
    
    with open(filename,"r") as fp: 
    
        #read file line by line
        i=0
        line ="string"
        while line != "":
            line = fp.readline()
            i+=1 #incremement line count
            if line.isspace():
                #skip blank lines
                continue
            
            elif line == "":
                #skip end of file
                continue
            
            elif line.lstrip().startswith("#"):
                #skip comment lines
                continue
            
            elif line.lstrip().startswith("<variables>"):
                #read variable definitions
                variables,i = readVariables(fp,i)
                
                #append variables to settings
                for key,value in variables.items():
                    if settings.has_key(key):
                        raise ValueError, "Redeclaration of "+str(key)+" on line "+str(i)
                    settings[key] = value
                       
            elif line.lstrip().startswith("<capture mode>"):
                #capture mode definition
                capture_mode,i = readVariables(fp,i)
                try:
                    capture_mode_name = capture_mode["name"]
                except KeyError:
                    raise ValueError, "No name specified for capture mode on line "+str(i)
                
                settings["capture modes"][capture_mode_name]=capture_mode
                
            elif line.lstrip().startswith("<schedule>"):
                #schedule definition
                schedule,i = readVariables(fp,i)
                
                settings["schedule"] = schedule
            
            elif line.lstrip().startswith("<image>"):
                #image type definition
                image,i = readVariables(fp,i)
                
                settings["image types"][image["image_type"]] = image
                
            elif line.lstrip().startswith("<output>"):
                #output type definition
                output,i = readVariables(fp,i)
                
                settings["output types"][output["name"]] = output
            
            else:
                raise ValueError, "Error reading settings file. Illegal value on line "+str(i)

    return settings

##############################################################################################        
           