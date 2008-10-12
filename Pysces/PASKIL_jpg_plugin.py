from __future__ import with_statement

import cPickle
import Image

from PASKIL import allskyImage, allskyImagePlugins


class Pysces_DSLR_LYR_JPG:

    def __init__(self):
        self.name = "Jeff and Nial's DSLR camera at KHO, being run by the Pysces software"
        
    ###################################################################################    
    
    def test(self, image_filename, info_filename):
        
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
        
        image = Image.open(image_filename)
        
        with open(info_filename,"rb") as fp:
                info = cPickle.load(fp)
     
        #return new allskyImage object
        return allskyImage.allskyImage(image,image.filename,info)
        
    ###################################################################################
###################################################################################

allskyImagePlugins.register(Pysces_DSLR_LYR_JPG())