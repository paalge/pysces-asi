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
from Queue import Empty
"""
This module provides the OutputTaskHandler class, which is responsible
for post-processing the images to produce the desired outputs. 
Multiple processes are used to produce the outputs in parallel and the 
degree of parallelism will scale automatically with the number of available
CPUs.
"""
import multiprocessing
import logging
import threading
import os.path
import imp
import glob

from pysces_asi import network
from pysces_asi.multitask import ThreadQueueBase, ThreadTask, ProcessQueueBase
from pysces_asi.output_task import OutputTask, output_functions
# from pysces_asi.cron import wait_for_per_image_tasks, submit_image_for_cron

log = logging.getLogger("task_handler")


def register(name, plugin):

    if name in output_functions:
        raise ValueError("A plugin called \'" + name + "\' already exists.")
    output_functions[name] = plugin


def load_output_functions(outputs_folder):
    """
    Imports all the files in .pysces_asi/outputs, causing all the functions
    to be registered.
    """
    # get list of plugin files
    plugins = glob.glob(outputs_folder + "/*.py")

    for p in plugins:
        imp.load_source(os.path.basename(p).rstrip(".py"), p)


def clear_plugins_list():
    """
    Clears the output functions  dict.
    """
    output_functions.clear()


##########################################################################

class OutputTaskHandler(ThreadQueueBase):
    """
    The OutputTaskHandler class manages two processing pools for post-
    processing the images. One pool uses as many processes as there are
    CPUs to parallel process the outputs. The other uses a single process
    to produce outputs that require images to be processed in order (for 
    example keogram creation). The 'pipelined' parameter in the output 
    declaration in the settings file controls which pool is used for which
    output.

    The OutputTaskHandler inherits from ThreadQueueBase, but redefines the
    _process_tasks() method so that it can deal with OutputTask objects in the
    queue as well as ThreadTask objects.
    """

    def __init__(self, settings_manager):

        self.__pipelined_lock = threading.Lock()

        ThreadQueueBase.__init__(self, name="OutputTaskHandler", workers=multiprocessing.cpu_count(
        ), maxsize=multiprocessing.cpu_count() + 2)

        # create a processing pool to produce the outputs asyncronously - this
        # has as many workers as there are CPU cores
        self._processing_pool = ProcessQueueBase(
            workers=multiprocessing.cpu_count(), name="Processing Pool")  # multiprocessing.cpu_count()

        # create a processing pool to produce outputs in the order that their respective image types
        # are recieved from the camera (useful for creating keograms for
        # example)
        self._pipelined_processing_pool = ProcessQueueBase(
            workers=1, name="Pipelined Processing Pool")

        # load the output creation functions
        home = os.path.expanduser("~")
        clear_plugins_list()
        load_output_functions(os.path.normpath(home + "/.pysces_asi/outputs"))

        # check to see if we need a web-server mounted
        try:
            web_server = settings_manager.get(["web_server"])['web_server']
        except KeyError:
            web_server = None

        if (web_server is None):
            self._network_manager = None
        else:
            # create NetworkManager object to handle copying outputs to the
            # webserver
            self._network_manager = network.NetworkManager(settings_manager)

        self._settings_manager = settings_manager

    ##########################################################################

    def _process_tasks(self):
        """
        Here we redefine the _process_tasks method (inherited from ThreadQueueBase)
        so that OutputTask objects can be placed into the input queue as well as
        ThreadTask objects. The OutputTask objects are recieved from the CaptureManager
        class.
        """
        while self._stay_alive or (not self._task_queue.empty()):

            # grab the pipelined lock - this ensures that pipelined subtasks are put into the
            # pipelined processing queue in the same order as they are taken out
            # of this queue
            log.info("locking pipeline")
            self.__pipelined_lock.acquire()

            # pull an outputTask out of the queue
            output_task = self._task_queue.get()

            # there is the chance that this could be a ThreadTask object, rather than a
            # OutputTask object, and we need to be able to execute it.
            if isinstance(output_task, ThreadTask):
                self.__pipelined_lock.release()
                print("output task handler: recieved exit command")
                output_task.execute()
                self._task_queue.task_done()

            elif isinstance(output_task, OutputTask):

                #                 # submit the image file for cron processing
                #                 log.info("Submitting  image for cron")
                #                 submit_image_for_cron(
                # output_task.get_image_filename(), self._settings_manager)

                # run all the sub tasks in separate processes
                output_task.run_subtasks(
                    self._processing_pool, self._pipelined_processing_pool, self._network_manager)
                self.__pipelined_lock.release()
                timeout = 5
                # wait for all the subtasks to be executed
                try:

                    output_task.wait(timeout)
                except Empty:
                    log.warn("Out_task wait timed out")

                log.info("Waiting over")
                # wait for the CronManager to finish with the image files
                #==============================================================
                # try:
                #     wait_for_per_image_tasks(
                #     output_task.get_image_filename(), self._settings_manager,
                #     timeout=timeout)
                # except Empty:
                #     log.warn("Out_task image timed out")
                # log.info("Per image wait over")
                #==============================================================
                # remove the temporary files
                output_task.remove_temp_files()
                del output_task

                # tell the queue that execution is complete
                self._task_queue.task_done()
                log.info("Task done")

            else:
                self.__pipelined_lock.release()
                # if this happens then something has gone seriously wrong!
                print("**error**" + str(type(output_task)) +
                      " is neither a ThreadTask nor an OutputTask and cannot be executed" + " by the OutputTaskHandler.")
                print("output_task = ", output_task)
                print(
                    "comparison = ", isinstance(output_task, type(OutputTask)))
                print(
                    "type comparison = ", (type(output_task) is type(OutputTask)))
                print(dir(output_task))
                raise TypeError
        self._exit_event.set()

    ##########################################################################

    def commit_task(self, task):
        """
        Puts the specified task into the input queue where it will be executed
        by one of the internal worker threads. The task's result() method be
        used for syncronising with task completion. If there are more tasks
        currently being executed than there are CPUs, then Queue.Full is
        raised.
        """
        # only queue task if should be alive - tasks submitted after exit is
        # encountered will be ignored
        flag = False
        for thread in self._workers:
            if thread.isAlive():
                flag = True
            if not flag:
                print(
                    "### Error! ### Worker thread in " + self.name + " has died!")
#                 raise RuntimeError(
#                     "### Error! ### Worker thread in " + self.name + " has died!")

        if self._stay_alive:
            self._task_queue.put_nowait(task)

    ##########################################################################

    def exit(self):
        """
        Waits for all the outstanding OutputTasks to be completed then shuts down the 
        processing pools and the internal worker thread.
        """
        # kill own worker thread

        ThreadQueueBase.exit(self)
        print("OutputTaskHandler: Killed self")

        # shutdown the processing pools
        self._processing_pool.exit()
        self._pipelined_processing_pool.exit()
        print("OutputTaskHandler: Joined processing pools")

        # kill the network manager
        if (self._network_manager is not None):
            self._network_manager.exit()
            print("OutputTaskHandler: Killed network manager")

    ##########################################################################
##########################################################################
