"""
This module defines three classes used for passing settings stored in the 
settings file around within the program. This is more convenient than using
nested dicts.
"""

class CaptureMode:
    """
    The captureMode class contains all the data needed to run a particular capture mode, that is
    a particular setup on the camera combined with a particular set of outputs. Capture modes are
    built by the scheduler class, and then passed to the captureManager for execution. Note that 
    when they are passed to the captureManager they are treated in a similar way to task objects
    (they are put in a queue and executed sequentially) however, they are not a sub-class of the
    task class.
    """
    def __init__(self, capture_mode_settings, image_type_settings, output_type_settings):
        self.name = None
        self.delay = None
        self.outputs = []
        self.camera_settings = {}
        
        for name, value in capture_mode_settings.items():
            if name == "name":
                self.name = value
            elif name == "delay":
                self.delay = value
            elif name == "outputs":
                for output_name in value:
                    self.outputs.append(OutputType(output_type_settings[output_name], image_type_settings))
            else:
                self.camera_settings[name] = value
        #check that we got all the required fields in the settings that were passed
        if self.name == None:
            raise ValueError, "No name specified for captureMode."
        if self.delay == None:
            raise ValueError, "No delay specified for captureMode"
        if self.outputs == None:
            raise ValueError, "No outputs specified for captureMode. If there really are no outputs, then use outputs = [] in the settings file"

##############################################################################################          
        
class ImageType:
    """
    The imageType class contains all the data needed to describe a particular image type,
    that is a particular type of image that the camera can record - e.g jpeg. The attributes
    of this class are just the values specified in the settings file.
    """
    def __init__(self, settings):
        self.image_type = settings["image_type"]
        self.y_center = settings["y_center"]
        self.x_center = settings["x_center"]
        self.Radius = settings["Radius"]
        self.Wavelength = settings["Wavelength"]

##############################################################################################  

class OutputType:
    """
    The outputType class contains all the data needed to describe a particular output type,
    that is one specific output - e.g. a keogram of all the jpeg type images. The attributes
    of this class are just the values specified in the settings file.
    """
    
    def __init__(self, output_type_settings, image_type_settings):
        self.__output_type_settings = output_type_settings
        self.name = output_type_settings["name"]
        self.type = output_type_settings["type"]
        self.image_type = ImageType(image_type_settings[output_type_settings["image_type"]])
        self.folder_on_host = output_type_settings["folder_on_host"]
        self.file_on_server = output_type_settings["file_on_server"]
        self.filename_format = output_type_settings["filename_format"]
        self.pipelined = output_type_settings["pipelined"]
        
    def __getattr__(self, name):
        #any additional attributes that are defined in the settings file can be 
        #recovered using this method.
        try:
            return self.__output_type_settings[name]
        except KeyError:
            raise AttributeError, "outputType instance has no attribute called " + name + ". Check that it has been defined in the settings file"

##############################################################################################  
