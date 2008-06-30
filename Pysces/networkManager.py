from __future__ import with_statement
from subprocess import Popen,PIPE
import os,string,stat

class networkManager:
    
    def __init__(self,settings_manager):
        
        self.__settings_manager = settings_manager
        self.__awaiting_password = False
        
    
    def isMounted(self):
        web_server = self.__settings_manager.grab("web_server")
        
        self.__settings_manager.release("web_server")
        
        home = os.path.expanduser("~")
        mount_point = home+"/.Pysces/servers/web"

        p = Popen("mount -l",shell=True,stdout=PIPE,stderr=PIPE)
        mounted_list = string.join(p.stdout.readlines())
        outerr = string.join(p.stderr.readlines())

        if mounted_list.count(web_server+" on "+mount_point) != 0:
            return True
        else:
            return False
    
    def mountServer(self):
        if not self.isMounted() and not self.__awaiting_password:
            self.__awaiting_password = True
            home = os.path.expanduser("~")
            web_server = self.__settings_manager.grab("web_server")
            #mount_point = self.__settings_manager.grab("mount_point")
            web_username = self.__settings_manager.grab("web_username") 
            mount_point = home+"/.Pysces/servers/web"
            
            #build mounting script
            with open(home+"/.Pysces/mount-script.sh","w") as fp:
                
                fp.write("#!/bin/sh\n")
                fp.write("echo \"### Password required to mount web server ###\"\n")
                fp.write("sudo mount.cifs \""+web_server+"\" \""+mount_point+"\" -o user=\""+web_username+"\"\n")
            
            #make mount script executable
            os.chmod(home+"/.Pysces/mount-script.sh",stat.S_IRWXU+stat.S_IRWXO+stat.S_IRWXG)
            
            #run script in xterm window
            p = Popen("xterm -e "+home+"/.Pysces/mount-script.sh",shell=True,stdout=PIPE,stderr=PIPE)
            
            #wait for process to finish
            p.wait()
            
            #remove script file
            os.remove(home+"/.Pysces/mount-script.sh")
            
            self.__awaiting_password = False
    
        
                
    def exit(self):
        return