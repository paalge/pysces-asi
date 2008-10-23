"""
This module defines the plugin class needed to allow PASKIL to load the D80's 
jpeg images. See the documentation for the PASKIL.allskyImagePlugins module
for details about plugin classes.
"""

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
        try:
            with open(info_filename,"rb") as fp:
                info = cPickle.load(fp)
        except:
            return False
        
        try:
            image = Image.open(image_filename)
        except:
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