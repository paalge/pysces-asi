import os,datetime,time,threading

class hostManager:
    
    def __init__(self,settings_manager):
        
        self.__old_tmp_dir = None
        self.__removal_thread = None
        self.__settings_manager = settings_manager
        
        self.__stay_alive = True
        
        #create variables
        settings_manager.create("output folder","")
        try:
            settings_manager.create("tmp dir",None,persistant=True)
        except ValueError:
            pass
        
        try:
            settings_manager.create("hostManager dirs to remove",[],persistant=True)
        except ValueError:
            pass 
        
        #create a new thread to remove empty temporary directories
        self.__removal_thread = threading.Thread(target=self.__removeDir)
        self.__removal_thread.start()
        
    ############################################################################################## 
             
    def updateFolders(self,capture_mode):

        #get required global variables
        glob_vars = self.__settings_manager.get(["folder_on_host","year_folder_format","month_folder_format","day_folder_format"])

        today = datetime.datetime.utcnow()
        folders=[glob_vars['folder_on_host']]
        
        for format in [glob_vars['year_folder_format'],glob_vars['month_folder_format'],glob_vars['day_folder_format']]: 
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

        
        #create Pysces sub_directories
        outputs = []
        
        #look at which files are needed in the outputs for this capture mode
        if capture_mode != None:
            for output in capture_mode.outputs:
                outputs.append(output.type)

        if outputs.count("quicklook") != 0 and not os.path.exists(current_folder + "/Quicklooks"):
            os.mkdir(current_folder + "/Quicklooks")
        
        if outputs.count("raw") != 0 and not os.path.exists(current_folder + "/Raw"):
            os.mkdir(current_folder + "/Raw")        

        if outputs.count("image") != 0 and not os.path.exists(current_folder + "/Images"):
            os.mkdir(current_folder + "/Images")

        if outputs.count("map") != 0 and not os.path.exists(current_folder + "/Maps"):
            os.mkdir(current_folder + "/Maps")
           
        #update output folder variable
        self.__settings_manager.set({"output folder":current_folder})
        
        #create tmp dir
        self.createTmpDir()
        
    ##############################################################################################                        

    def createTmpDir(self):
        
        glob_vars = self.__settings_manager.get(["tmp dir","output folder"])

        
        #if the new tmp dir is the same as the old one and still exists then return
        if glob_vars['tmp dir'] == glob_vars['output folder']+"/tmp" and os.path.exists(glob_vars['output folder']+"/tmp"):
            return
        
        #create the new tmp directory
        if not os.path.exists(glob_vars['output folder']+"/tmp"):
            os.makedirs(glob_vars['output folder']+"/tmp")
        
        self.__settings_manager.set({"tmp dir":glob_vars['output folder']+"/tmp"})
        
        #add the old tmp dir to the list of directories to be removed (it will be removed when it is empty)
        if glob_vars['tmp dir'] != None and os.path.exists(glob_vars['tmp dir']) and glob_vars['tmp dir'] != glob_vars['output folder']+"/tmp":
            def appendToList(list,value_to_append):
                list.append(value_to_append)
                return list
                      
            self.__settings_manager.operate("hostManager dirs to remove",appendToList,glob_vars['tmp dir'])
 
    ##############################################################################################                                   
     
    def __removeDir(self):
        """
        Removes old temporary directories when they are empty
        """
        #define a function for removing items from the list
        
        def removeFromList(list,value_to_remove):
            list.remove(value_to_remove)
            return list
        
        while self.__stay_alive:
        
            dirs_to_rm = self.__settings_manager.get(["hostManager dirs to remove"])["hostManager dirs to remove"]
            i=0
            while i < len(dirs_to_rm):
                dir = dirs_to_rm[i]
                
                if not os.path.isdir(dir):
                    #the directory no longer exists so we can remove it from the list
                    self.__settings_manager.operate("hostManager dirs to remove",removeFromList,dir)
                    i = i-1
                elif (len(os.listdir(dir)) == 0):
                    #the directory is empty so we can delete it and remove it from the list
                    os.rmdir(dir)
                    self.__settings_manager.operate("hostManager dirs to remove",removeFromList,dir)
                    i = i-1
                i = i+1
            
            #the directories don't have to be deleted immediately, so sleep for a bit
            time.sleep(3)
        
    ##############################################################################################                     
    
    def exit(self):
        """
        Waits for the temporary directory thread to finish and then returns.
        """
        
        #wait for directory removal threads to finish
        if self.__removal_thread != None:
            self.__stay_alive = False
            self.__removal_thread.join() #wait for thread to finish
    