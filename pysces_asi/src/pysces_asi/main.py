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
import threading
import matplotlib

# using the Agg backend prevents threading conflicts with the GTK based GUI, it also
# allows the script to be started remotely
matplotlib.use('Agg')

from pysces_asi import settings_manager
from pysces_asi import scheduler
from pysces_asi import cron


class MainBox:

    def __init__(self):
        self.__running = False

        # create settings manger object)
        self.__settings_manager = settings_manager.SettingsManager()

        # create cron manager and run intialisation tasks
        self.__cron_manager = cron.CronManager(self.__settings_manager)
        self.__cron_manager.run_init_tasks()

        # create scheduler object
        self.__scheduler = scheduler.Scheduler(self.__settings_manager)

        self.__capture_thread = None

    ##########################################################################

    def start(self):
        if self.__capture_thread == None:
            # create task
            self.__capture_thread = threading.Thread(
                target=self.__scheduler.start)
            self.__capture_thread.start()
        else:
            raise RuntimeError("Can't start more than one scheduler!")

    ##########################################################################

    def stop(self):

        # if a scheduler is running then kill it
        if self.__capture_thread != None:
            # kill scheduler and wait for capture thread to return
            self.__settings_manager.set(
                {"output": "MainBox> Killing scheduler"})
            self.__scheduler.exit()
            self.__capture_thread.join()

            self.__capture_thread = None
            self.__settings_manager.set(
                {"output": "MainBox> Capture stopped."})

    ##########################################################################

    def exit(self):

        self.stop()

        # kill cron manager
        self.__settings_manager.set(
            {"output": "MainBox> Killing cron manager"})
        self.__cron_manager.exit()

        # kill settings manager
        self.__settings_manager.set(
            {"output": "MainBox> Killing settings_manager"})

        try:
            self.__settings_manager.exit()
        except RuntimeError as ex:
            # if the settings file has been modified while the program is running, then
            # give up updating it.
            print(ex.args[0])

    ##########################################################################

    def setVar(self, names):
        self.__settings_manager.set(names)

    ##########################################################################

    def register(self, name, callback, globals_):
        self.__settings_manager.register(name, callback, globals_)

    ##########################################################################

    def create(self, name, value, persistant=False):
        self.__settings_manager.create(name, value, persistant=persistant)

    ##########################################################################

    def getVar(self, names):
        return self.__settings_manager.get(names)

    ##########################################################################
##########################################################################

# if the script is being run in non-gui mode then run it!
if __name__ == '__main__':

    def output(s):
        print(s["output"])

    main_box = MainBox()

    main_box.register("output", output, ["output"])

    # run!
    main_box.start()
    main_box._MainBox__capture_thread.join()
