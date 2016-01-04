# Copyright (C) Nial Peters 2009
#
# This file is part of pysces_asi.
#
# pysces_asi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
# pysces_asi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pysces_asi.  If not, see <http://www.gnu.org/licenses/>.
import wx
#import wxmpl
from threading import Thread
import threading
import time
import datetime
#import matplotlib

from pysces_asi import main


class PlotPanel (wx.Panel):
    """
    PlotPanel class taken from http://www.scipy.org/Matplotlib_figure_in_a_wx_panel

    The PlotPanel has a Figure and a Canvas. OnSize events simply set a 
    flag, and the actual resizing of the figure is triggered by an Idle event."""

    def __init__(self, parent, color=None, dpi=None, **kwargs):
        from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
        from matplotlib.figure import Figure
        self.parent = parent
        # initialize Panel
        if 'id' not in list(kwargs.keys()):
            kwargs['id'] = wx.ID_ANY
        if 'style' not in list(kwargs.keys()):
            kwargs['style'] = wx.NO_FULL_REPAINT_ON_RESIZE
        wx.Panel.__init__(self, parent, **kwargs)

        # initialize matplotlib stuff
        self.figure = Figure(None, dpi)
        self.canvas = FigureCanvasWxAgg(self, -1, self.figure)
        self.SetColor(color)

        self._SetSize()
        self.draw()

        self._resizeflag = False

        self.Bind(wx.EVT_IDLE, self._onIdle)
        self.Bind(wx.EVT_SIZE, self._onSize)

    def SetColor(self, rgbtuple=None):
        """Set figure and canvas colours to be the same."""
        if rgbtuple is None:
            rgbtuple = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE).Get()
        clr = [c / 255. for c in rgbtuple]
        self.figure.set_facecolor(clr)
        self.figure.set_edgecolor(clr)
        self.canvas.SetBackgroundColour(wx.Colour(*rgbtuple))

    def _onSize(self, event):
        self._resizeflag = True

    def _onIdle(self, evt):
        if self._resizeflag:
            self._resizeflag = False
            self._SetSize()

    def _SetSize(self):
        pixels = tuple(self.parent.GetClientSize())
        self.SetSize(pixels)
        self.canvas.SetSize(pixels)
        self.figure.set_size_inches(float(pixels[0]) / self.figure.get_dpi(),
                                    float(pixels[1]) / self.figure.get_dpi())

    def draw(self):
        # abstract, to be overridden by child classes
        raise NotImplementedError(
            "Abstract method - must be defined in subclass")


# class ScheduleSummaryPanel(wxmpl.PlotPanel):
#    def __init__(self,parent):
#        wxmpl.PlotPanel.__init__(self,parent,-1)
#
#    def plot_schedule(self,data=None):
#        fig = self.get_figure()
#        axes = fig.gca()
#        axes.clear()
#        if data is not None:
#            if len(data.times) == 0:
#                return
#            #plot data
#            axes.plot(data.times,data.sun_angles)
#            axes.plot(data.times,data.moon_angles)
#
#            axes.set_xlim(min(data.times),max(data.times))
#            axes.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%H:%M"))
#        print "drawing"
#        self.draw()
#
#    def on_redraw(self, data):
#        future = data['future_schedule']
#        self.plot_schedule(future)


class TimePanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)
        self.__stay_alive = True
        self.vsizer = wx.BoxSizer(wx.VERTICAL)
        self.time = wx.StaticText(
            self, wx.ID_ANY, "\nTime (UT): " + datetime.datetime.utcnow().strftime("%H:%M:%S"))
        self.date = wx.StaticText(
            self, wx.ID_ANY, "\nDate: " + datetime.datetime.utcnow().strftime("%d/%m/%y"))

        self.vsizer.Add(self.date, 0, wx.ALIGN_LEFT)
        self.vsizer.Add(self.time, 0, wx.ALIGN_LEFT)

        self.SetSizer(self.vsizer)

        self.SetAutoLayout(1)
        self.vsizer.Fit(self)

        self.update_thread = threading.Thread(target=self.update_time)
        self.update_thread.start()

    def update_time(self):
        while self.__stay_alive:
            wx.MutexGuiEnter()
            self.time.SetLabel(
                "\nTime (UT): " + datetime.datetime.utcnow().strftime("%H:%M:%S"))
            self.date.SetLabel(
                "\nDate: " + datetime.datetime.utcnow().strftime("%d/%m/%Y"))
            wx.MutexGuiLeave()
            time.sleep(0.2)

    def exit(self):
        self.__stay_alive = False
        self.update_thread.join()


class CaptureModePanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)
        self.vsizer = wx.BoxSizer(wx.VERTICAL)
        #self.title = wx.StaticText(self,wx.ID_ANY,"Ephemeris:")
        self.caption = wx.StaticText(
            self, wx.ID_ANY, "\n\tCurrent capture mode: \'None\'")

        # self.vsizer.Add(self.title,0,wx.ALIGN_LEFT)
        self.vsizer.Add(self.caption, 0, wx.ALIGN_LEFT)

        self.SetSizer(self.vsizer)

        self.SetAutoLayout(1)
        self.vsizer.Fit(self)

    def update(self, data):
        wx.MutexGuiEnter()
        self.caption.SetLabel(
            "\n\tCurrent capture mode: \'" + str(data["current_capture_mode"]) + "\'")
        wx.MutexGuiLeave()

    def blank(self):
        # method only called by GUI thread, therefore no need to get Mutex
        self.caption.SetLabel("\n\tCurrent capture mode: \'None\'")


class EphemPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)
        self.vsizer = wx.BoxSizer(wx.VERTICAL)
        #self.title = wx.StaticText(self,wx.ID_ANY,"Ephemeris:")
        self.sun_caption = wx.StaticText(
            self, wx.ID_ANY, "\n\tSun angle:      ")
        self.moon_caption = wx.StaticText(
            self, wx.ID_ANY, "\tMoon angle:     ")
        self.phase_caption = wx.StaticText(
            self, wx.ID_ANY, "\tMoon phase:     ")

        # self.vsizer.Add(self.title,0,wx.ALIGN_LEFT)
        self.vsizer.Add(self.sun_caption, 0, wx.ALIGN_LEFT)
        self.vsizer.Add(self.moon_caption, 0, wx.ALIGN_LEFT)
        self.vsizer.Add(self.phase_caption, 0, wx.ALIGN_LEFT)

        self.SetSizer(self.vsizer)

        self.SetAutoLayout(1)
        self.vsizer.Fit(self)

    def update_ephem(self, ephem_data):
        wx.MutexGuiEnter()
        self.sun_caption.SetLabel(
            "\n\tSun angle: " + str("%0.2f" % float(ephem_data["sun_angle"])) + " deg.")
        self.moon_caption.SetLabel(
            "\tMoon angle: " + str("%0.2f" % float(ephem_data["moon_angle"])) + " deg.")
        self.phase_caption.SetLabel(
            "\tMoon phase: " + str("%0.2f" % float(ephem_data["moon_phase"])) + " %")
        wx.MutexGuiLeave()

    def blank(self):
        # method only called by GUI thread, therefore no need to get Mutex
        self.sun_caption.SetLabel("\n\tSun angle: ")
        self.moon_caption.SetLabel("\tMoon angle: ")
        self.phase_caption.SetLabel("\tMoon phase: ")


class StatusPanel(wx.Panel):
    """
    Panel to display status indications such as name of capture mode, ephemeris
    data and current time.
    """

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1, style=wx.SUNKEN_BORDER)
        self.vsizer = wx.BoxSizer(wx.VERTICAL)
        self.hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.hsizer2 = wx.BoxSizer(wx.HORIZONTAL)
        self.ephem_panel = EphemPanel(self)
        self.time_panel = TimePanel(self)
        self.capture_mode_panel = CaptureModePanel(self)
        self.caption = wx.StaticText(self, wx.ID_ANY, "\n\nTerminal:")

        self.vsizer.Add(self.hsizer, 1, wx.EXPAND)
        self.hsizer.Add(self.ephem_panel, 1, wx.ALIGN_LEFT)
        self.hsizer.Add(self.time_panel, 1, wx.ALIGN_CENTER_HORIZONTAL)
        self.hsizer.Add(self.capture_mode_panel, 1, wx.ALIGN_RIGHT)
        self.vsizer.Add(self.hsizer2, 1, wx.EXPAND)
        self.hsizer2.Add(self.caption, 0, wx.ALIGN_BOTTOM)

        self.SetSizer(self.vsizer)

        self.SetAutoLayout(1)
        self.vsizer.Fit(self)

    def exit(self):
        self.time_panel.exit()

    def blank(self):

        self.ephem_panel.blank()
        self.capture_mode_panel.blank()


###############################################################################

class TerminalFrame(wx.TextCtrl):
    """
    Frame to display scrolling text in different colours.
    """

    def __init__(self, parent_frame, history_length=50, show_time=False, show_date=False):
        self.show_time = show_time
        self.show_date = show_date

        # number of lines that are stored by the terminal
        self.history_length = history_length
        self.current_line_number = 0
        wx.TextCtrl.__init__(self, parent_frame, -1, style=wx.TE_MULTILINE)
        self.SetBackgroundColour(wx.BLACK)
        self.SetFont(wx.Font(9, wx.SWISS, wx.NORMAL, wx.NORMAL))
        self.colour_mappings = {"NetworkManager": wx.Colour(255, 0, 255),
                                "CameraManager": wx.Colour(255, 0, 0),
                                "Scheduler": wx.Colour(0, 0, 255),
                                "OutputTaskHandler": wx.Colour(0, 255, 0),
                                "SettingsManager": wx.Colour(255, 255, 0),
                                "HostManager": wx.Colour(0, 255, 255)}

        self.gui_thread = threading.currentThread()

    ##########################################################################

    def print_to_term(self, s):
        if not s.endswith('\n'):
            s = s + '\n'

        # determine colour of text
        origin = s.partition('>')[0]
        try:
            font_colour = self.colour_mappings[origin]
        except KeyError:
            font_colour = wx.Colour(255, 255, 255)

        # if it is not the main GUI thread that is writing to the terminal then we have to
        # get the GUI mutex before priting to the term - wx is not threadsafe
        # otherwise
        if threading.currentThread() != self.gui_thread:
            wx.MutexGuiEnter()

        # if the history length has been exceeded then start deleting lines
        if self.current_line_number >= self.history_length:
            length = self.GetLineLength(0)
            self.Remove(0, length + 1)
            self.current_line_number -= 1

        # add date and time information if required
        if self.show_time:
            s = datetime.datetime.utcnow().strftime("%H:%M:%S ") + s
        if self.show_date:
            s = datetime.datetime.utcnow().strftime("%d/%m/%y ") + s

        # print the text to the terminal window
        self.SetDefaultStyle(wx.TextAttr(font_colour))
        self.SetInsertionPointEnd()
        self.WriteText(s)
        self.current_line_number += 1
        if threading.currentThread() != self.gui_thread:
            wx.MutexGuiLeave()

    ##########################################################################

    def on_show_time(self, e):
        self.show_time = e.Checked()

    ##########################################################################

    def on_show_date(self, e):
        self.show_date = e.Checked()

    ##########################################################################
###############################################################################


class MainFrame(wx.Frame):
    """
    Main viewing window (or frame) containing the terminal and control menu.
    """

    def __init__(self):
        # create main frame
        wx.Frame.__init__(self, None, wx.NewId(
        ), 'pysces_asi: All-sky Camera Control for Linux', size=(800, 500))

        # create the main pysces objects
        self.pysces = main.MainBox()

        # create terminal frame settings if they don't already exist
        try:
            self.pysces.create("gui_term_viewtime", False, persistant=True)
        except ValueError:
            pass  # it already exists
        try:
            self.pysces.create("gui_term_viewdate", False, persistant=True)
        except ValueError:
            pass  # it already exists

        term_settings = self.pysces.getVar(
            ["gui_term_viewtime", "gui_term_viewdate"])

        self.tw = TerminalFrame(self, show_time=term_settings[
                                "gui_term_viewtime"], show_date=term_settings["gui_term_viewdate"])
        self.tw.SetEditable(False)

        self.status_panel = StatusPanel(self)

        #self.schedule_parent_panel = wx.Panel(self,-1)
        #self.schedule_panel = ScheduleSummaryPanel(self)
        self.vsizer = wx.BoxSizer(wx.VERTICAL)
        # self.vsizer.Add(self.schedule_panel,1,wx.EXPAND)
        self.vsizer.Add(self.status_panel, 0, wx.EXPAND)
        self.vsizer.Add(self.tw, 1, wx.EXPAND)
        self.SetSizer(self.vsizer)

        self.SetAutoLayout(1)
        self.vsizer.Fit(self)

        self.SetSize((800, 500))

        # register the output
        self.pysces.register('output', self.print_pysces_to_term, ['output'])

        # register the status callbacks
        self.pysces.register('sun_angle', self.status_panel.ephem_panel.update_ephem, [
                             'sun_angle', 'moon_angle', 'moon_phase'])
        self.pysces.register('current_capture_mode', self.status_panel.capture_mode_panel.update, [
                             'current_capture_mode'])
        # register for future schedule callbacks
        # self.pysces.register('future_schedule',self.schedule_panel.on_redraw,['future_schedule'])

        # create capture menu
        capture_menu = wx.Menu()
        self.menuStart = capture_menu.Append(-1, "&Start Capture",
                                             "Run the capture program defined in the settings file.")
        capture_menu.AppendSeparator()
        self.menuStop = capture_menu.Append(-1,
                                            "&End Capture", "Stop the capture program")
        self.menuStop.Enable(False)

        # register capture menu callbacks
        wx.EVT_MENU(self, self.menuStart.GetId(), self.start_pysces)
        wx.EVT_MENU(self, self.menuStop.GetId(), self.stop_pysces)

        # create View menu
        view_menu = wx.Menu()
        terminal_view_submenu = wx.Menu()
        term_showtime_checkbox = terminal_view_submenu.AppendCheckItem(
            -1, "Time")
        term_showdate_checkbox = terminal_view_submenu.AppendCheckItem(
            -1, "Date")
        term_showtime_checkbox.Check(self.tw.show_time)
        term_showdate_checkbox.Check(self.tw.show_date)
        wx.EVT_MENU(self, term_showtime_checkbox.GetId(), self.tw.on_show_time)
        wx.EVT_MENU(self, term_showdate_checkbox.GetId(), self.tw.on_show_date)
        view_menu.AppendSubMenu(terminal_view_submenu, "Terminal")

        # create the menubar
        menuBar = wx.MenuBar()
        menuBar.Append(capture_menu, "&Capture")
        menuBar.Append(view_menu, "&View")

        self.SetMenuBar(menuBar)

        self.cleanup_thread = Thread(target=self.on_close)
        self.__stopping_thread = None
        wx.EVT_CLOSE(self, self.exit)

    ##########################################################################

    def start_pysces(self, event):
        try:
            self.pysces.start()
            self.menuStart.Enable(False)
            self.menuStop.Enable(True)
        except:
            self.print_to_term(
                "An error occured. See the error terminal for details")

    ##########################################################################

    def stop_pysces(self, event):
        self.menuStart.Enable(True)
        self.menuStop.Enable(False)
        self.status_panel.blank()
        self.__stopping_thread = threading.Thread(target=self.pysces.stop)
        self.__stopping_thread.start()

    ##########################################################################

    def print_to_term(self, s):
        self.tw.print_to_term(s)

    ##########################################################################

    def print_pysces_to_term(self, d):
        self.tw.print_to_term(d['output'])

    ##########################################################################

    def exit(self, event):
        try:
            self.cleanup_thread.start()
        except RuntimeError:
            pass

    ##########################################################################

    def on_close(self):
        if self.__stopping_thread is not None:
            self.__stopping_thread.join()
        self.pysces.setVar({"gui_term_viewtime": self.tw.show_time,
                            "gui_term_viewdate": self.tw.show_date})
        self.pysces.exit()
        wx.MutexGuiEnter()
        self.status_panel.exit()
        self.Update()
        self.Destroy()
        self.Refresh()
        wx.MutexGuiLeave()

    ##########################################################################
###############################################################################

if __name__ == "__main__":

    # setup app
    app = wx.PySimpleApp()

    frame = MainFrame()
    frame.Show()

    app.MainLoop()
