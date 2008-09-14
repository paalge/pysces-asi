




class captureMode:
    def __init__(self,capture_mode_settings,image_type_settings,output_type_settings):
        self.name = None
        self.delay = None
        self.outputs = []
        self.camera_settings = {}
        
        for name,value in capture_mode_settings.items():
            if name == "name":
                self.name = value
            elif name == "delay":
                self.delay = value
            elif name == "outputs":
                for output_name in value:
                    self.outputs.append(outputType(output_type_settings[output_name],image_type_settings))
            else:
                self.camera_settings[name] = value
        
        #check that we got all the required fields in the settings that were passed
        if self.name == None:
            raise ValueError, "No name specified for captureMode."
        if self.delay == None:
            raise ValueError, "No delay specified for captureMode"
        if self.outputs == None:
            raise ValueError, "No outputs specified for captureMode. If there really are no outputs, then use outputs = [] in the settings file"
        
#    def toDict(self):
#        """
#        Returns a dictionary representation of the captureMode. Note that only the names of the
#        outputs are returned in the dict, not the full contents of the associated output object.
#        """
#        d = {}
#        
#        d["name"] = self.name
#        d["delay"] = self.delay
#        d["outputs"] = []
#        
#        for output in self.outputs:
#            d["outputs"].append(output.name)
#        
#        for key,value in self.camera_settings.items():
#            d[key] = value
#        
#        return d




class imageType:
    def __init__(self,settings):
        self.image_type = settings["image_type"]
        self.y_center = settings["y_center"]
        self.x_center = settings["x_center"]
        self.Radius = settings["Radius"]
        self.Wavelength = settings["Wavelength"]

#    def toDict(self):
#        """
#        Returns a dictionary representation of the imageType. 
#        """
#        d = {}
#        
#        d["image_type"] = self.image_type
#        d["y_center"] = self.y_center
#        d["x_center"] = self.x_center
#        d["Radius"] = self.Radius
#        d["Wavelength"] = self.Wavelength
#        
#        return d



class outputType:
    def __init__(self,output_type_settings,image_type_settings):
        self.name = output_type_settings["name"]
        self.type = output_type_settings["type"]
        self.image_type = imageType(image_type_settings[output_type_settings["image_type"]])
        self.save_on_host = output_type_settings["save_on_host"]
        self.filename_suffix = output_type_settings["filename_suffix"]
        self.file_on_server = output_type_settings["file_on_server"]
    
#    def toDict(self):
#        """
#        Returns a dictionary representation of the imageType. 
#        """
#        d = {}
#        
#        d["name"] = self.name
#        d["type"] = self.type
#        d["image_type"] = self.image_type.image_type
#        d["save_on_host"] = self.save_on_host
#        d["filename_suffix"] = self.filename_suffix
#        d["file_on_server"] = self.file_on_server
#        
#        return d