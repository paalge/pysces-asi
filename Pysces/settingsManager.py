"""
The settingsManager module provides classes and functions for managing all the settings (global
variables) for Pysces. Functions for reading and writing to the ascii settings file are provided
in addition to the settingsManager class.
"""


from __future__ import with_statement
import threading,os
import persist


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
        new_value = settings[key]
        
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
        
class settingsManager:
    """
    The settingsManager class is in charge of all global variables used in Pysces. It allocates
    locks for threadsafe variable access, and runs callback functions when variables are changed.
    It also deals with updating the settings file when the program exits.
    """
    def __init__(self):
        
        #define private attributes
        self.__variables = {}
        self.__callbacks = {}
        self.__locks = {}
        
        #hard code file locations
        home = os.path.expanduser("~")
        self.create("Settings File",home+"/.Pysces/settings.txt")
        self.create("persist filename",home+"/.Pysces/persistant")
        self.create("current capture mode","")
        self.create("most recent images","")
        self.create("output","")
        self.create("persist names",[])
        self.create("day","")       
        
        #load settings file 
        settings_file=self.grab('Settings File')
        settings = loadSettingsFile(settings_file)
        self.release('Settings File')       
        
        #store settings in variables
        for key in settings.keys():
            self.create(key,settings[key])
                    
        #create persistant storage class
        self.__persistant_storage = persist.persistantStorage(self)
        
        #load persistant values into variables
        persistant_data = self.__persistant_storage.getPersistantData()
        
        for key in persistant_data.keys():
            self.create(key,persistant_data[key],persistant=True)
            
    ##############################################################################################            
            
    def grab(self,name):
        """
        Acquires the lock on the variable and then returns a copy of its value. Each call to this 
        method should be followed by a call to release when you are finished with the variable.
        """
        #acquire lock
        self.__locks[name].acquire()
        
        #resolve any shell variables
        if type(self.__variables[name]) == type(str()) and self.__variables[name].count("$") != 0:
            return(os.path.expandvars(self.__variables[name]))
        
        #attempt to create a hard copy of the variable
        try:
            return self.__variables[name].copy()
        except AttributeError:
            return self.__variables[name]
        
    ##############################################################################################  
          
    def release(self,name):
        """
        Releases the lock on the specified variable.
        """   
        #release lock
        self.__locks[name].release()
        
    ##############################################################################################  
          
    def set(self,name,value):
        """
        Sets the value of a variable and runs all callback functions associated with it. The variable
        remains locked whilst the callbacks are run.
        """
        
        #get the lock
        self.__locks[name].acquire()
        
        #set the new value
        self.__variables[name] = value
        
        #run the callback functions
        for function in self.__callbacks[name]:
            if function != None and name != "output":
                function()
            elif name == "output":
                function(value)
        
        #release lock
        self.release(name)
        
    ##############################################################################################         
    
    def setGroup(self,group):
        """
        Sets a group of variables. If a callback is registered for more than one variable in the 
        group it is only executed once. The group argument should be a dictionary of name:value 
        pairs.
        """
        
        #check there are no duplicate entries in the group
        keys = group.keys()
        for key in keys:
            if keys.count(key) > 1:
                raise ValueError,"Group cannot contain duplicate entries"
            
        #get the locks on all the variables in the group
        for key in keys:
            self.__locks[key].acquire()
        
        #set all the values and build a set of the callbacks
        unique_callbacks = set([])
        for key in keys:
            self.__variables[key] = group[key]
            
            for function in self.__callbacks[key]:
                if function != None:
                    unique_callbacks.add(function)
        
        #run unique callbacks
        for function in unique_callbacks:
            function()
        
        #release the locks
        for key in keys:
            self.release(key)
            
    ##############################################################################################                 
     
    def exit(self):
        """
        Updates the settings file and kills the persistant storage class.
        """
        #kill the persistant storage
        self.__persistant_storage.exit()
        
        #update the settings file
        self.set("output", "settingsManager> Updating settings file")
        self.__updateSettingsFile()
        self.set("output", "Pysces> Stopped!")
            
    ##############################################################################################     
    
    def register(self,name, callback):
        """
        Registers a callback function for a variable. This will be called whenever the variable is set.
        The function will be called without any arguments, unless name = "output" in which case the 
        function will be called with the new value of "output" as an argument.
        """
        self.__callbacks[name].append(callback)
        
    ##############################################################################################                      
    
    def create(self,name,value,persistant=False):
        """
        Creates a new variable. If persistant=True, then the variable value will survive program restart
        even if it is not in the settings file. Variables which are in the settings file should not be
        created as persistant.
        """
        if self.__variables.has_key(name):
            raise ValueError,"A variable called "+name+" already exists."
        
        self.__variables[name] = value
        self.__locks[name] = threading.RLock()
        self.__callbacks[name] = []
        
        if persistant:
            self.__locks["persist names"].acquire()
            self.__variables["persist names"].append(name)
            self.__locks["persist names"].release()
            
    ##############################################################################################
    
    def __updateSettingsFile(self):
        """
        Writes any changes to the settings file.
        """
        #open current settings file for reading
        with open(self.grab("Settings File"),'r') as fp:
            self.release("Settings File")
        
           #open temporary file to write to
            with open(self.grab("Settings File")+"-temp",'w') as ofp:
                self.release("Settings File")
                
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
                        
                        #read declaration to see which capture mode this is
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
                        
                        #read declaration to see which output this is
                        output,j = readVariables(fp,i)
                        
                        #go back to start of declaration
                        fp.seek(dec_start)
                        
                        #update file
                        updateVariables(fp,ofp,i,self.__variables["output types"][output["name"]])
                    
                    elif line.lstrip().startswith("<image>"):
                        ofp.write(line)
                        #record position in file of declaration
                        dec_start = fp.tell()
                        
                        #read declaration to see which image this is
                        image,j = readVariables(fp,i)
                        
                        #go back to start of declaration
                        fp.seek(dec_start)
                        
                        #update file
                        updateVariables(fp,ofp,i,self.__variables["image types"][image["image_type"]])
                        
                    else:
                        raise ValueError,"Unable to update settings file. Error on line "+str(i)    

        #move teporary file to settings file
        filename = self.grab("Settings File")
        os.rename(filename+"-temp", filename)
        self.release("Settings File")
                   
    ##############################################################################################           
##############################################################################################           
        
        
           