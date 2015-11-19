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
"""
The cron module provides the CronManager class which is reponsible for running
the user's own scripts at specified times during pysces_asi operation. Scripts
can be run at program startup (e.g. to mount servers etc) and each time a new 
output folder is generated on the host (e.g. for running daily processing tasks).
"""
import traceback
import os
import logging
import subprocess
import threading


from pysces_asi.multitask import ThreadQueueBase

log = logging.getLogger("cron")


def remove_from_dict(d, k):
    d.pop(k)
    return d


def add_to_dict(d, k, v):
    d[k] = v
    return d


def wait_for_per_image_tasks(filename, settings_manager):
    """
    Function blocks until all pending per_image tasks have been completed on 
    the image specified by filename.
    """

    lock_dict = settings_manager.get(
        ["cron_per_image_locks"])["cron_per_image_locks"]

    lock_dict[filename].acquire()

    settings_manager.operate(
        "cron_per_image_locks", remove_from_dict, filename)


def submit_image_for_cron(filename, settings_manager):
    lock = threading.Lock()
    lock.acquire()
    settings_manager.operate(
        "cron_per_image_locks", add_to_dict, filename, lock)
    settings_manager.set({"cron_image_to_process": filename})


class CronManager(ThreadQueueBase):
    """
    The CronManager class controls the execution of user's own scripts 
    during the execution of pysces_asi. It runs all executables in the 
    ~/.pysces_asi/tasks.startup folder when it is instanciated. Each
    time the variable "output folder" is updated, it runs all 
    executables in ~/.pysces_asi/tasks.daily via a callback registered
    with the settings_manager.
    """

    def __init__(self, settings_manager):
        ThreadQueueBase.__init__(self, workers=3, name="CronManager")
        # need multiple worker threads to allow per_image jobs to run while
        # daily tasks are running.

        try:
            self._settings_manager = settings_manager

            try:
                self._settings_manager.create(
                    "cron_folder_to_process", None, persistant=True)
            except ValueError:
                pass
            try:
                self._settings_manager.create("cron_per_image_locks", {})
            except ValueError:
                pass

            home = os.path.expanduser("~")

            self.init_scripts_dir = home + "/.pysces_asi/tasks.startup"
            self.per_image_scripts_dir = home + "/.pysces_asi/tasks.per_image"
            self.daily_scripts_dir = home + "/.pysces_asi/tasks.daily"

            # it is possible that the "output folder" variable doesn't exist
            # yet (normally it is created when the HostManager is instanciated.
            # so just in case, we create it here - otherwise we might have problems
            # when we try to register a callback for it
            try:
                self._settings_manager.create("output folder", "")
            except ValueError:
                pass

            try:
                self._settings_manager.create("cron_image_to_process", "")
            except ValueError:
                pass

            # register the callback for the daily scripts
            self._settings_manager.register(
                "output folder", self.run_daily_tasks, ["output folder", "cron_folder_to_process"])
            self._settings_manager.register(
                "cron_image_to_process", self.run_per_image_tasks, ["cron_image_to_process"])

        except Exception as ex:
            traceback.print_exc()
            self.exit()
            raise ex

    ##########################################################################

    def get_scripts(self, folder):
        """
        Returns a list of executable files in the specified folder.
        If the folder does not exist, returns an empty list
        """
        if not os.path.isdir(folder):
            return []

        file_list = os.listdir(folder)
        executables = []

        for file in file_list:
            file_path = os.path.normpath(folder + "/" + file)
            if os.access(file_path, os.X_OK):
                executables.append(file_path)

        return executables

    ##########################################################################

    def __run_init_tasks(self):
        self.__run_scripts(self.init_scripts_dir)

    ##########################################################################

    def __run_daily_tasks(self, arg_dict):
        # get the new value of the output_folder
        new_output_folder = arg_dict["output folder"]
        old_output_folder = arg_dict["cron_folder_to_process"]

        # if this is the first time this function has been run
        # then just copy the value
        if old_output_folder is None:
            self._settings_manager.set(
                {"cron_folder_to_process": new_output_folder})

        elif old_output_folder == new_output_folder:
            return
        else:
            self._settings_manager.set(
                {"cron_folder_to_process": new_output_folder, "output": "CronManager> Running daily tasks for " + old_output_folder})
            self.__run_scripts(
                self.daily_scripts_dir, script_args="\"" + old_output_folder + "\"")

    ##########################################################################

    def __run_per_image_tasks(self, arg_dict):
        # get the name of the image to process
        filename = arg_dict["cron_image_to_process"]
        self._settings_manager.set(
            {"output": "CronManager> Running per-image tasks for " + filename})
        self.__run_scripts(
            self.per_image_scripts_dir, script_args="\"" + filename + "\"")
        lock = self._settings_manager.get(
            ["cron_per_image_locks"])["cron_per_image_locks"][filename]
        lock.release()

    ##########################################################################

    def __run_scripts(self, folder, script_args=""):
        scripts_list = self.get_scripts(folder)

        # run the scripts one by one
        for script in scripts_list:
            not_started = True
            while not_started:
                try:
                    p = subprocess.Popen(
                        script + " " + script_args, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    not_started = False
                except OSError:
                    continue

            p.wait()
            print(p.stdout.read())

            outerr = p.stderr.read()
            print(outerr)

            if p.returncode != 0:
                self._settings_manager.set(
                    {"output": "CronManager> Error! The script \"" + script + "\" returned exit code " + str(p.returncode)})
                self._settings_manager.set(
                    {"output": "CronManager> The stderr from the script reads: " + outerr})

    ##########################################################################

    def run_init_tasks(self):
        """
        Runs all executable files in the ~/.pysces_asi/tasks.startup folder. 
        No arguments are passed to the scripts.
        """

        # create task
        task = self.create_task(self.__run_init_tasks)

        # submit task
        self.commit_task(task)

        # return result when task has been completed
        return task.result()

    ##########################################################################

    def run_daily_tasks(self, arg_dict):
        """
        Runs all executable files in the ~/.pysces_asi/tasks.daily folder. 
        The scripts are passed the name of the last "output folder" - i.e.
        the folder that they should process.
        """
        # create task
        task = self.create_task(self.__run_daily_tasks, arg_dict)

        # submit task
        self.commit_task(task)

        # don't wait for the task to complete before returning, otherwise
        # we are holding up the whole program
        return

    ##########################################################################

    def run_per_image_tasks(self, arg_dict):
        # create task
        task = self.create_task(self.__run_per_image_tasks, arg_dict)

        # submit task
        self.commit_task(task)

        # return result when task has been completed
        return

    ##########################################################################
