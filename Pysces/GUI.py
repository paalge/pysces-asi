import wx,time
from threading import Thread
import threading
import main

###############################################################################

class TerminalFrame(wx.TextCtrl):
    """
    Frame to display scrolling text in different colours.
    """
    def __init__(self,parent_frame,history_length=250):
        self.history_length = history_length
        self.current_line_number = 0
        wx.TextCtrl.__init__(self,parent_frame,-1, style = wx.TE_MULTILINE)
        self.SetBackgroundColour(wx.BLACK)
        self.SetFont(wx.Font(9, wx.SWISS, wx.NORMAL, wx.NORMAL))
        self.colour_mappings = {"NetworkManager":wx.Colour(255,0,255),
                                "CameraManager":wx.Colour(255,0,0),
                                "Scheduler":wx.Colour(0,0,255),
                                "OutputTaskHandler":wx.Colour(0,255,0),
                                "SettingsManager":wx.Colour(255,255,0),
                                "HostManager":wx.Colour(0,255,255)}
        
        self.gui_thread = threading.currentThread()

    ###############################################################################
    
    def print_to_term(self,s):
        if not s.endswith('\n'):
            s = s + '\n'
            
        #determine colour of text
        origin = s.partition('>')[0]
        try:
            font_colour = self.colour_mappings[origin]
        except KeyError:
            font_colour = wx.Colour(255,255,255)
        
        if threading.currentThread() != self.gui_thread:
            print "waiting for mutex"
            wx.MutexGuiEnter()
            print "got mutex"
        if self.current_line_number >= self.history_length:
            length=frame.tw.GetLineLength(0)
            self.Remove(0, length+1)
            self.current_line_number -= 1
            
        self.SetDefaultStyle(wx.TextAttr(font_colour))
        self.WriteText(s)
        self.current_line_number += 1
        if threading.currentThread() != self.gui_thread:
            wx.MutexGuiLeave()
            
    ###############################################################################
###############################################################################

ID_START = 102
ID_STOP = 103    
class MainFrame(wx.Frame):
    """
    Main viewing window (or frame) containing the terminal and control buttons.
    """
    def __init__(self):
        #create main frame
        wx.Frame.__init__(self, None, wx.NewId(), 'pysces_asi: All-sky Camera Control for Linux',size=(800, 500))
        
        self.tw = TerminalFrame(self)
        
        #create the main pysces objects
        self.pysces = main.MainBox()
        
        #register the output 
        self.pysces.register('output', self.print_pysces_to_term, ['output'])
        
        #create the menubar
        capture_menu = wx.Menu()
        self.menuStart = capture_menu.Append(ID_START, "&Start Capture",
                    "Run the capture program defined in the settings file.")
        capture_menu.AppendSeparator()
        self.menuStop = capture_menu.Append(ID_STOP, "&End Capture", "Stop the capture program")
        self.menuStop.Enable(False)
        menuBar = wx.MenuBar()
        menuBar.Append(capture_menu, "&Capture");

        self.SetMenuBar(menuBar)
        
        #bind menu events to methods
        wx.EVT_MENU(self, ID_START, self.start_pysces)
        wx.EVT_MENU(self, ID_STOP, self.stop_pysces)
        
        self.cleanup_thread = Thread(target=self.on_close)
        wx.EVT_CLOSE(self, self.exit)
        
    ###############################################################################
        
    def start_pysces(self,event):
        try:
            self.pysces.start()
            self.menuStart.Enable(False)
            self.menuStop.Enable(True)
        except:
            self.print_to_term("An error occured. See the error terminal for details")

    ###############################################################################
        
    def stop_pysces(self,event):
        self.menuStart.Enable(True)
        self.menuStop.Enable(False)
        t=threading.Thread(target=self.pysces.stop)
        t.start()

    ###############################################################################
            
    def print_to_term(self, s):
        self.tw.print_to_term(s)
        
    ###############################################################################
        
    def print_pysces_to_term(self, d):
        self.tw.print_to_term(d['output'])
        
    ###############################################################################    
    
    def exit(self,event):
        try:
            self.cleanup_thread.start()
        except RuntimeError:
            pass
        
    ###############################################################################
    
    def on_close(self):
        self.pysces.exit()
        self.Update()
        time.sleep(5)
        self.Destroy()
        self.Refresh()
        
    ###############################################################################    
###############################################################################    
    
if __name__ == "__main__":

    #setup app
    app= wx.PySimpleApp()
    
    frame = MainFrame()
    frame.Show()
    
    app.MainLoop ()