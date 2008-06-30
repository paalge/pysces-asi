import os,datetime,time,threading
import networkManager

class hostManager:
    
    def __init__(self,settings_manager):
        
        self.__old_tmp_dir = None
        self.__removal_thread=None
        self.__settings_manager = settings_manager
        self.__running = False
        self.__network_manager = networkManager.networkManager(self.__settings_manager)
        
        #create variables
        settings_manager.create("output folder","")
        try:
            settings_manager.create("tmp dir",None,persistant=True)
        except ValueError:
            pass
        
        #register callback functions
        settings_manager.register("folder_on_host",self.updateFolders)
        settings_manager.register("output folder",self.createTmpDir)
        settings_manager.register("year_folder_format",self.updateFolders)
        settings_manager.register("month_folder_format",self.updateFolders)
        settings_manager.register("day_folder_format",self.updateFolders)
        settings_manager.register("day",self.updateFolders)
        
    ############################################################################################## 
             
    def updateFolders(self):
        if not self.__running:
            return
        
        #get required global variables
        folder_on_host =  self.__settings_manager.grab("folder_on_host")
        year_folder_format = self.__settings_manager.grab("year_folder_format")
        month_folder_format = self.__settings_manager.grab("month_folder_format")
        day_folder_format = self.__settings_manager.grab("day_folder_format")

        today = datetime.datetime.now()
        folders=[folder_on_host]
        
        for format in [year_folder_format,month_folder_format,day_folder_format]: 
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
        d_quicklook = self.__settings_manager.grab("d_quicklook")
        if d_quicklook and not os.path.exists(current_folder + "/Quicklooks"):
            os.mkdir(current_folder + "/Quicklooks")
        self.__settings_manager.release("d_quicklook")
        
        unprocessed_raw = self.__settings_manager.grab("unprocessed_raw")
        if unprocessed_raw and not os.path.exists(current_folder + "/Raw"):
            os.mkdir(current_folder + "/Raw")
        self.__settings_manager.release("unprocessed_raw")
        
        
        unprocessed_jpeg = self.__settings_manager.grab("unprocessed_jpeg")
        PASKIL_png = self.__settings_manager.grab("PASKIL_png")
        if (unprocessed_jpeg or PASKIL_png) and not os.path.exists(current_folder + "/Images"):
            os.mkdir(current_folder + "/Images")
        
        self.__settings_manager.release("unprocessed_jpeg")
        self.__settings_manager.release("PASKIL_png")
        
        d_map_projection = self.__settings_manager.grab("d_map_projection")
        if d_map_projection and not os.path.exists(current_folder + "/Maps"):
            os.mkdir(current_folder + "/Maps")
        self.__settings_manager.release("d_map_projection")
        
        #update output folder variable
        self.__settings_manager.set("output folder",current_folder)
        
        #release global variables
        self.__settings_manager.release("folder_on_host")
        self.__settings_manager.release("year_folder_format")
        self.__settings_manager.release("month_folder_format")
        self.__settings_manager.release("day_folder_format")

        
    ##############################################################################################                        

    def createTmpDir(self):
        if not self.__running:
            return
        old_tmp_dir = self.__settings_manager.grab("tmp dir")
        output_folder = self.__settings_manager.grab("output folder")
        self.__settings_manager.release("tmp dir")
        
        #if the new tmp dir is the same as the old one then return
        if old_tmp_dir == output_folder+"/tmp":
            self.__settings_manager.release("output folder")
            return
        
        #create the new tmp directory
        if not os.path.exists(output_folder+"/tmp"):
            os.makedirs(output_folder+"/tmp")
        
        self.__settings_manager.set("tmp dir",output_folder+"/tmp")
        
        #remove the old tmp dir when it is empty
        if old_tmp_dir != None and os.path.exists(old_tmp_dir):
            t=threading.Thread(target=self.__removeDir,args=(old_tmp_dir,))
            self.__removal_threads=t #this variable is set to the last thread to be started
            t.start()
            
        self.__settings_manager.release("output folder")
        
            
    ##############################################################################################                                   
     
    def __removeDir(self,dir):
        """
        Blocks until the directory is empty and then removes it.
        """

        while (len(os.listdir(dir)) != 0):
               time.sleep(0.5)
       
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
    