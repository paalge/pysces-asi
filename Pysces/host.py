"""
The host module provides a HostManager class responsible for maintaining the 
folder structure on the host machine.
"""
import os
import datetime

class HostManager:
    """
    The host manager class provides a single method for creating and updating the
    folder structure on the host machine. This also takes care of creating temporary
    folders and then removing again when they are empty.
    """
    def __init__(self, settings_manager):
        
        self.__old_tmp_dir = None
        self.__settings_manager = settings_manager
        
        #create variables
        try:
            settings_manager.create("output folder", "")
        except ValueError:
            pass
        
    ############################################################################################## 
             
    def update_folders(self, capture_mode):
        """
        Creates the folder structure required by the specified CaptureMode object.
        The structure changes between CaptureModes since they may require different 
        outputs. It also changes with time, as the day, month, year folders change.
        """
        #get required global variables
        glob_vars = self.__settings_manager.get(["folder_on_host", "year_folder_format", "month_folder_format", "day_folder_format", "tmp dir"])

        today = datetime.datetime.utcnow()
        folders=[glob_vars['folder_on_host']]
        
        for format in [glob_vars['year_folder_format'], glob_vars['month_folder_format'], glob_vars['day_folder_format']]: 
            if format != None:
                folders.append(today.strftime(format))
        
        current_folder = ""
        
        #create the folder structure
        for folder in folders:
            current_folder += folder+"/"
        
        #remove trailing /
        if current_folder.endswith("/"):
            current_folder = current_folder.rstrip("/")
            
        #see if it exists and if not then create it
        if not os.path.exists(current_folder):
            os.makedirs(current_folder)     

        #create sub_directories for the different outputs
        output_folders = set([])
        
        #look at which folders are needed in the outputs for this capture mode
        if capture_mode != None:
            for output in capture_mode.outputs:
                output_folders.add(output.folder_on_host)
            
            #create the folders
            for sub_folder in output_folders:
                #skip blank folder names
                if ((sub_folder == None) or (sub_folder == "")):
                    continue
                
                if not os.path.exists(os.path.normpath(current_folder + "/" + sub_folder)):
                    os.mkdir(os.path.normpath(current_folder + "/" + sub_folder))
           
        #update output folder variable
        self.__settings_manager.set({"output folder":current_folder})
        
        #create tmp dir if it doesn't exist already
        if not os.path.exists(glob_vars['tmp dir']):
            os.makedirs(glob_vars['tmp dir'])
            
    ##############################################################################################                     
##############################################################################################    