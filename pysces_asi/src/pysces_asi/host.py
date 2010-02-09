#Copyright (C) Nial Peters 2009
#
#This file is part of pysces_asi.
#
#pysces_asi is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pysces_asi is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pysces_asi.  If not, see <http://www.gnu.org/licenses/>.
"""
The host module provides a HostManager class responsible for maintaining the 
folder structure on the host machine.
"""
from __future__ import with_statement
import os
import datetime
import time
import threading

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
            try:
               os.makedirs(current_folder)
            except OSError:
            #for some reason the  check
            #sometimes fails resulting in an OSError when we try to create the folder.
            #Maybe due to network latency or something? 
                pass 

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
                    try:
                        os.mkdir(os.path.normpath(current_folder + "/" + sub_folder))
                    except OSError:
                        pass
        #update output folder variable
        self.__settings_manager.set({"output folder":current_folder})
        
        #create tmp dir if it doesn't exist already
        if not os.path.exists(glob_vars['tmp dir']):
            try:
                os.makedirs(glob_vars['tmp dir'])
            except OSError:
                pass
        
            
    ##############################################################################################                     
##############################################################################################    