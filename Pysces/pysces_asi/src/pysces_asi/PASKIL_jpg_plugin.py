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
This module defines the plugin class needed to allow PASKIL to load the D80's 
jpeg images. See the documentation for the PASKIL.allskyImagePlugins module
for details about plugin classes.
"""
from __future__ import with_statement
import cPickle
import Image

from PASKIL import allskyImage, allskyImagePlugins


class Pysces_DSLR_LYR_JPG:
    """
    Plugin class for D80 jpeg images produced using pysces_asi (using a pickled
    dict as a site info file.
    """
    def __init__(self):
        self.name = "Jeff and Nial's DSLR camera at KHO, being run by the pysces_asi software"
        
    ###################################################################################    
    
    def test(self, image_filename, info_filename):
        """
        Returns True if the image can be opened using this plugin, False otherwise.
        """
        print "testing with plugin"
        try:
            with open(info_filename,"rb") as fp:
                info = cPickle.load(fp)
        except Exception,ex:
            print "failed to open site info file"
            raise ex
            return False
        
        try:
            image = Image.open(image_filename)
        except:
            print "failed to open image"
            return False
        
        return True
            
    ###################################################################################
        
    def open(self,image_filename, info_filename):
        """
        Returns a PASKIL allskyImage object containing the image data and its
        associated meta-data.
        """
        image = Image.open(image_filename)
        
        with open(info_filename,"rb") as fp:
                info = cPickle.load(fp)
     
        #return new allskyImage object
        return allskyImage.allskyImage(image,image.filename,info)
        
    ###################################################################################
###################################################################################

#register this plugin with PASKIL
allskyImagePlugins.register(Pysces_DSLR_LYR_JPG())