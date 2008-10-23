"""
The settings file parser module provides a settingsFileParser class for reading
and writing to the settings file.
"""
import os

class SettingsFileParser:
    """
    This is a helper class for the SettingsManager, providing methods for reading
    and writing to the settings file. This allows the settings file format to be
    changed without having to modify the SettingsManager.
    """
    def __init__(self,filename):
        self.filename = filename
        
    ###########################################################################
                
    def get_settings(self):
        """
        Reads the settings file and returns a dictionary containing the name,
        value pairs contained in the file.
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
                    variables,i = self.__read_variables(fp,i)
                    
                    #append variables to settings
                    for key,value in variables.items():
                        if settings.has_key(key):
                            raise ValueError("Redeclaration of "+str(key)+
                                             " on line "+str(i))
                        settings[key] = value
                           
                elif line.lstrip().startswith("<capture mode>"):
                    #capture mode definition
                    capture_mode,i = self.__read_variables(fp,i)
                    try:
                        capture_mode_name = capture_mode["name"]
                    except KeyError:
                        raise ValueError("No name specified for capture mode on line "+str(i))
                    
                    settings["capture modes"][capture_mode_name] = capture_mode
                    
                elif line.lstrip().startswith("<schedule>"):
                    if schedule_found:
                        raise ValueError, "Second schedule definition on line "+str(i) 
                    #schedule definition
                    schedule,i = self.__read_variables(fp,i)
                    
                    settings["schedule"] = schedule
                    schedule_found = True
                
                elif line.lstrip().startswith("<image>"):
                    #image type definition
                    image,i = self.__read_variables(fp,i)
                    
                    settings["image types"][image["image_type"]] = image
                    
                elif line.lstrip().startswith("<output>"):
                    #output type definition
                    output,i = self.__read_variables(fp,i)
                    
                    settings["output types"][output["name"]] = output
                
                else:
                    raise ValueError, "Error reading settings file. Illegal value on line "+str(i)
    
        return settings
    
    ############################################################################################## 
     
    def __read_variables(self,fp,line_no):
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
    
    def update_settings_file(self,settings):    
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
                        i=self.__update_variables(fp,ofp,i,settings)
                        
                    elif line.lstrip().startswith("<capture mode>"):
                        ofp.write(line)
                        #record position in file of declaration
                        dec_start = fp.tell()
                        
                        #read declaration to see which capture mode this is, j is not used (unwanted line number)
                        capture_mode,j = self.__read_variables(fp,i)
                        
                        #go back to start of declaration
                        fp.seek(dec_start)
                        
                        #update file
                        self.__update_variables(fp,ofp,i,settings["capture modes"][capture_mode["name"]])
                        
                    elif line.lstrip().startswith("<schedule>"):
                        ofp.write(line)
                        self.__update_variables(fp,ofp,i,settings["schedule"])
                    
                    elif line.lstrip().startswith("<output>"):
                        ofp.write(line)
                        #record position in file of declaration
                        dec_start = fp.tell()
                        
                        #read declaration to see which output this is, j is not used (unwanted line number)
                        output,j = self.__read_variables(fp, i)
                        
                        #go back to start of declaration
                        fp.seek(dec_start)
                        
                        #update file
                        self.__update_variables(fp, ofp, i, settings["output types"][output["name"]])
                    
                    elif line.lstrip().startswith("<image>"):
                        ofp.write(line)
                        #record position in file of declaration
                        dec_start = fp.tell()
                        
                        #read declaration to see which image this is, j is not used (unwanted line number)
                        image,j = self.__read_variables(fp,i)
                        
                        #go back to start of declaration
                        fp.seek(dec_start)
                        
                        #update file converting the imageType object back to a dict
                        self.__update_variables(fp,ofp,i,settings["image types"][image["image_type"]])
                        
                    else:
                        raise ValueError,"Unable to update settings file. Error on line "+str(i)    

        #move teporary file to settings file
        os.rename(self.filename + "-temp", self.filename)
                   
    ##############################################################################################
  
    def __update_variables(self,fp,ofp,line_no,settings):
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
