"""
The settings file parser module provides a settingsFileParser class for reading
and writing to the settings file.
"""
from __future__ import with_statement
import dataStorageClasses
import os

class settingsFileParser:
    
    def __init__(self,filename):
        self.filename = filename
        
    ##############################################################################################
        
    def getSettings(self):
        
        #read the settings from the file
        settings_in_file = self.__loadSettingsFile()
        
        #build the imageType objects
        for image_type_name in settings_in_file["image types"].keys():
            #overwrite the dict description of the image type with an imageType object
            settings_in_file["image types"][image_type_name] = dataStorageClasses.imageType(settings_in_file["image types"][image_type_name])
        
        #build the outputType object
        for name,output_type in settings_in_file["output types"].items():
            #first we overwrite the name of the image type with the correct imageType object
            output_type["image_type"] = settings_in_file["image types"][output_type["image_type"]]
            
            #then we overwrite the dict description of the output type with an outputType object
            settings_in_file["output types"][name] = dataStorageClasses.outputType(output_type)
        
        #build captureMode objects
        for cm_name in settings_in_file["capture modes"].keys():
            #first we replace the output names with their respective outputType objects
            output_type_objects = []
            for output_name in settings_in_file["capture modes"][cm_name]["outputs"]:
                output_type_objects.append(settings_in_file["output types"][output_name])
                
            settings_in_file["capture modes"][cm_name]["outputs"] = output_type_objects
            
            #then we overwrite the dict description of the output type with an outputType object
            settings_in_file["capture modes"][cm_name] = dataStorageClasses.captureMode(settings_in_file["capture modes"][cm_name])
        
        
        #remove the ouputs and images entries from the settings dict and return it
        #settings_in_file.pop("image types")
        #settings_in_file.pop("output types")
        
        return settings_in_file
            
    ##############################################################################################       
                
    def __loadSettingsFile(self):
        """
        Reads the settings file and returns a dictionary containing the name,value pairs contained 
        in the file.
        """
        settings = {"capture modes":{},"image types":{},"output types":{}}
        schedule_found = False
        
        with open(self.filename,"r") as fp: 
        
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
                    variables,i = self.__readVariables(fp,i)
                    
                    #append variables to settings
                    for key,value in variables.items():
                        if settings.has_key(key):
                            raise ValueError, "Redeclaration of "+str(key)+" on line "+str(i)
                        settings[key] = value
                           
                elif line.lstrip().startswith("<capture mode>"):
                    #capture mode definition
                    capture_mode,i = self.__readVariables(fp,i)
                    try:
                        capture_mode_name = capture_mode["name"]
                    except KeyError:
                        raise ValueError, "No name specified for capture mode on line "+str(i)
                    
                    settings["capture modes"][capture_mode_name] = capture_mode
                    
                elif line.lstrip().startswith("<schedule>"):
                    if schedule_found:
                        raise ValueError, "Second schedule definition on line "+str(i) 
                    #schedule definition
                    schedule,i = self.__readVariables(fp,i)
                    
                    settings["schedule"] = schedule
                    schedule_found = True
                
                elif line.lstrip().startswith("<image>"):
                    #image type definition
                    image,i = self.__readVariables(fp,i)
                    
                    settings["image types"][image["image_type"]] = image
                    
                elif line.lstrip().startswith("<output>"):
                    #output type definition
                    output,i = self.__readVariables(fp,i)
                    
                    settings["output types"][output["name"]] = output
                
                else:
                    raise ValueError, "Error reading settings file. Illegal value on line "+str(i)
    
        return settings
    
    ############################################################################################## 
     
    def __readVariables(self,fp,line_no):
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
    
    def updateSettingsFile(self,settings):    
        """
        Method writes a new settings file with the settings values stored in memory (within the 
        settingsManager class). The new file can then be copied across to the old file thus preventing
        errors in the update process from destroying the original settings file.
        """
        #open current settings file for reading
        with open(self.filename,'r') as fp:
        
           #open temporary file to write to
            with open(self.filename + "-temp",'w') as ofp:
                
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
                        i=self.__updateVariables(fp,ofp,i,settings)
                        
                    elif line.lstrip().startswith("<capture mode>"):
                        ofp.write(line)
                        #record position in file of declaration
                        dec_start = fp.tell()
                        
                        #read declaration to see which capture mode this is, j is not used (unwanted line number)
                        capture_mode,j = self.__readVariables(fp,i)
                        
                        #go back to start of declaration
                        fp.seek(dec_start)
                        
                        #update file converting the captureMode object into a dict
                        self.__updateVariables(fp,ofp,i,settings["capture modes"][capture_mode["name"]].toDict())
                        
                    elif line.lstrip().startswith("<schedule>"):
                        ofp.write(line)
                        self.__updateVariables(fp,ofp,i,settings["schedule"])
                    
                    elif line.lstrip().startswith("<output>"):
                        ofp.write(line)
                        #record position in file of declaration
                        dec_start = fp.tell()
                        
                        #read declaration to see which output this is, j is not used (unwanted line number)
                        output,j = self.__readVariables(fp, i)
                        
                        #go back to start of declaration
                        fp.seek(dec_start)
                        
                        #update file converting the outputType object to a dict
                        self.__updateVariables(fp, ofp, i, settings["output types"][output["name"]].toDict())
                    
                    elif line.lstrip().startswith("<image>"):
                        ofp.write(line)
                        #record position in file of declaration
                        dec_start = fp.tell()
                        
                        #read declaration to see which image this is, j is not used (unwanted line number)
                        image,j = self.__readVariables(fp,i)
                        
                        #go back to start of declaration
                        fp.seek(dec_start)
                        
                        #update file converting the imageType object back to a dict
                        self.__updateVariables(fp,ofp,i,settings["image types"][image["image_type"]].toDict())
                        
                    else:
                        raise ValueError,"Unable to update settings file. Error on line "+str(i)    

        #move teporary file to settings file
        os.rename(self.filename + "-temp", self.filename)
                   
    ##############################################################################################
  
    def __updateVariables(self,fp,ofp,line_no,settings):
        """
        Method updates a single declaration block in the settings file with the settings values stored 
        in memory (within the settingsManager class). The fp and ofp 
        arguments should be file objects for the original settings file (read) and the new settings file
        (write) respectively. line_no should be the current line number in the settings file, and settings 
        should be a dictionary of name:value pairs representing the variables contained in one declaration
        block.
        """
        
        #read file line by line
        line = "not an empty string"
        while line != "":
            line = fp.readline()
            line_no += 1 #incremement line count
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
