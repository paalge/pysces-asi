import os,datetime,time,threading
import networkManager

class hostManager:
    
    def __init__(self,settings_manager):
        
        self.__old_tmp_dir = None
        self.__removal_thread=None
        self.__settings_manager = settings_manager
        
        #create variables
        settings_manager.create("output folder","")
        try:
            settings_manager.create("tmp dir",None,persistant=True)
        except ValueError:
            pass
     
    ############################################################################################## 
             
    def updateFolders(self):

        #get required global variables
        glob_vars = self.__settings_manager.get(["folder_on_host","year_folder_format","month_folder_format","day_folder_format","capture modes","output types","current capture mode"])

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
        
        #rename globals for clarity
        capture_modes = glob_vars["capture modes"]
        output_types = glob_vars["output types"]
        ccm = glob_vars["current capture mode"]
        
        #create Pysces sub_directories
        outputs = []
        
        #look at which files are needed in the outputs for this capture mode
        if ccm != "" and ccm != None:
            for output in capture_modes[ccm]["outputs"]:
                outputs.append(output_types[output]["type"])

        if outputs.count("quicklook") != 0 and not os.path.exists(current_folder + "/Quicklooks"):
            os.mkdir(current_folder + "/Quicklooks")
        
        if outputs.count("raw") != 0 and not os.path.exists(current_folder + "/Raw"):
            os.mkdir(current_folder + "/Raw")        

        if outputs.count("image") != 0 and not os.path.exists(current_folder + "/Images"):
            os.mkdir(current_folder + "/Images")

        if outputs.count("map") != 0 and not os.path.exists(current_folder + "/Maps"):
            os.mkdir(current_folder + "/Maps")
           
        #update output folder variable
        self.__settings_manager.set("output folder",current_folder)

        
    ##############################################################################################                        

    def createTmpDir(self):
        #if not in active state then don't create tmp directory
        if not self.__running:
            return
        
        glob_vars = self.__settings_manager.grab(["tmp dir","output folder"])

        
        try:
            #if the new tmp dir is the same as the old one and still exists then return
            if glob_vars['tmp dir'] == glob_vars['output folder']+"/tmp" and os.path.exists(glob_vars['output folder']+"/tmp"):
                #globals are released in finally: block
                return
            
            #create the new tmp directory
            if not os.path.exists(glob_vars['output folder']+"/tmp"):
                os.makedirs(glob_vars['output folder']+"/tmp")
            
            self.__settings_manager.set("tmp dir",glob_vars['output folder']+"/tmp")
            
            #remove the old tmp dir when it is empty
            if glob_vars['tmp dir'] != None and os.path.exists(glob_vars['tmp dir']) and glob_vars['tmp dir'] != glob_vars['output folder']+"/tmp":
                t=threading.Thread(target=self.__removeDir,args=(glob_vars['tmp dir'],))
                self.__removal_threads=t #this variable is set to the last thread to be started
                t.start()
        finally:
            self.__settings_manager.release(glob_vars)
 
    ##############################################################################################                                   
     
    def __removeDir(self,dir):
        """
        Blocks until the directory is empty and then removes it.
        """

        while (len(os.listdir(dir)) != 0):
               time.sleep(1)
       
        os.rmdir(dir)
         
    ##############################################################################################                  
    
    def start(self):
        self.__running = True
        self.__network_manager.mountServer()
    
    ##############################################################################################                     
    
    def exit(self):
        self.__running = False
        
        self.__network_manager.exit()
        
        #wait for directory removal threads to finish
        if self.__removal_thread != None:
            self.__removal_thread.join(10.0) #wait up to 10 seconds for thread to finish
    