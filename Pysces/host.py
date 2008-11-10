"""
The host module provides a HostManager class responsible for maintaining the 
folder structure on the host machine.
"""
import os
import datetime
import time
import threading


class HostManager:
    """
    The host manager class provides a sinlge method for creating and updating the
    folder structure on the host machine. This also takes care of creating temporary
    folders and then removing again when they are empty.
    """
    def __init__(self, settings_manager):
        
        self.__old_tmp_dir = None
        self.__removal_thread = None
        self.__settings_manager = settings_manager
        
        self.__stay_alive = True
        
        #create variables
        try:
            settings_manager.create("output folder", "")
        except ValueError:
            pass
        try:
            settings_manager.create("tmp dir", None, persistant=True)
        except ValueError:
            pass
        
        try:
            settings_manager.create("HostManager dirs to remove", [], persistant=True)
        except ValueError:
            pass 
        
        #create a new thread to remove empty temporary directories
        self.__removal_thread = threading.Thread(target=self.__remove_dir)
        self.__removal_thread.start()
        
    ############################################################################################## 
             
    def update_folders(self, capture_mode):
        """
        Creates the folder structure required by the specified CaptureMode object.
        The structure changes between CaptureModes since they may require different 
        outputs. It also changes with time, as the day, month, year folders change.
        """
        #get required global variables
        glob_vars = self.__settings_manager.get(["folder_on_host", "year_folder_format", "month_folder_format", "day_folder_format"])

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
        
        #create tmp dir
        self._create_tmp_dir()
        
    ##############################################################################################                        

    def _create_tmp_dir(self):
        """
        Creates a new temporary directory, and adds it to the list of directories to be
        removed, so that it is deleted when it is empty.
        """
        self.__settings_manager.set({"tmp dir":"/home/nialp/tmp"})
        glob_vars = self.__settings_manager.get(["tmp dir", "output folder"])

        #if the new tmp dir is the same as the old one and still exists then return
        if glob_vars['tmp dir'] == glob_vars['output folder']+"/tmp" and os.path.exists(glob_vars['output folder']+"/tmp"):
            return
        
        #create the new tmp directory
        if not os.path.exists(glob_vars['output folder']+"/tmp"):
            os.makedirs(glob_vars['output folder']+"/tmp")
        
        self.__settings_manager.set({"tmp dir":glob_vars['output folder']+"/tmp"})
        
        #add the old tmp dir to the list of directories to be removed (it will be removed when it is empty)
        if glob_vars['tmp dir'] != None and os.path.exists(glob_vars['tmp dir']) and glob_vars['tmp dir'] != glob_vars['output folder']+"/tmp":
            def append_to_list(l, value_to_append):
                l.append(value_to_append)
                return l
                      
            self.__settings_manager.operate("HostManager dirs to remove", append_to_list, glob_vars['tmp dir'])
 
    ##############################################################################################                                   
     
    def __remove_dir(self):
        """
        Removes old temporary directories when they are empty. This is run in a separate
        thread, and sits in a loop checking to see if any of the directories are empty,
        and then removing them.
        """
        #define a function for removing items from the list
        
        def remove_from_list(l, value_to_remove):
            l.remove(value_to_remove)
            return l
        
        while self.__stay_alive:
        
            dirs_to_rm = self.__settings_manager.get(["HostManager dirs to remove"])["HostManager dirs to remove"]
            i=0
            while i < len(dirs_to_rm):
                dir_ = dirs_to_rm[i]
                
                if not os.path.isdir(dir_):
                    #the directory no longer exists so we can remove it from the list
                    self.__settings_manager.operate("HostManager dirs to remove", remove_from_list, dir)
                    i = i-1
                elif (len(os.listdir(dir_)) == 0):
                    #the directory is empty so we can delete it and remove it from the list
                    os.rmdir(dir_)
                    self.__settings_manager.operate("HostManager dirs to remove", remove_from_list, dir)
                    i = i-1
                i = i+1
            
            #the directories don't have to be deleted immediately, so sleep for a bit
            time.sleep(5)
        
    ##############################################################################################                     
    
    def exit(self):
        """
        Waits for the temporary directory thread to finish and then returns.
        """
        #wait for directory removal threads to finish
        if self.__removal_thread != None:
            self.__stay_alive = False
            self.__removal_thread.join() #wait for thread to finish

    ##############################################################################################            
##############################################################################################    