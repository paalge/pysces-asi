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
The network module provides a NetworkManager class which can be used for 
copying files to a CIFS filesystem on a remote server. It also provides
a proxy for the NetworkManager, which can be used to share a single network
manager object between multiple processses.
"""

import os
import string
import stat
import shutil

import multiprocessing
import logging
from threading import Thread
from subprocess import Popen, PIPE

from pysces_asi.multitask import ThreadQueueBase, RemoteTask

log = logging.getLogger("Network")


class _NetworkManagerProxy(ThreadQueueBase):
    """
    Proxy class for the NetworkManager class. Proxy objects can be passed to child processes
    where (once started) they can be used in the same way as their master class. Method calls 
    made on the proxy are executed by the master. Proxies are a way to share a single object 
    between multiple processes. The proxy is thread safe and so can be accessed by multiple 
    threads within the child process without problems.

    Note that you cannot create a proxy for a proxy. Only the master class has a createProxy()
    method. If the child process needs to spawn a child process of its own, then multiple
    proxies must be created in the parent process and passed on to the child's child process.
    """

    def __init__(self, id, input_queue, output_queue):
        self.id = id
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.started = False

    ##########################################################################

    def start(self):
        """
        Starts the proxy running. This must be called from within the process where the proxy is 
        going to be used.
        """
        ThreadQueueBase.__init__(self, name="NetworkManagerProxy")
        self.started = True

    ##########################################################################

    def exit(self):
        """
        Note that the exit method only kills the proxy, not the master. However, it does
        remove the proxy from the master, closing the shared queue between them.
        """
        task = RemoteTask(self.id, "destroy proxy", self.id)

        self.output_queue.put(task)

        ThreadQueueBase.exit(self)

    ##########################################################################

    def copy_to_server(self, source, destination):
        """
        Copies a source file to a destination on the server. The source argument should be 
        the complete path to the source file. The destination argument should be the filename
        of the destination, the folder on the server will be read from the settings file and 
        prepended to the filename.
        """
        assert self.started
        # create task
        task = self.create_task(self.__copy_to_server, source, destination)

        # submit task
        self.commit_task(task, timeout=30)

        # return result when task has been completed
        return task.result()

    ##########################################################################

    def __copy_to_server(self, source, destination):
        task = RemoteTask(self.id, "copyToServer", source, destination)

        self.output_queue.put(task)

        result = self.input_queue.get()

        if isinstance(result, Exception):
            raise result

        return result

    ##########################################################################
##########################################################################


class NetworkManager(ThreadQueueBase):
    """
    Class to handle copying files to a CIFS filesystem on a remote server. Provides
    methods for mounting the filesystem and copying files to the filesystem. The 
    NetworkManager class inherits from ThreadQueueBase, requests to copy files made
    by multiple threads will be processed sycronously.
    """

    def __init__(self, settings_manager):
        self.__settings_manager = settings_manager
        self.__awaiting_password = False
        home = os.path.expanduser('~')
        self._mount_point = home + "/.pysces_asi/servers/web"

        # create the mount point folder if it doesn't already exist
        if not os.path.isdir(self._mount_point):
            os.makedirs(self._mount_point)

        ThreadQueueBase.__init__(self, name="NetworkManager")

        # define method to string mappings - notice that these should be the
        # thread safe public methods!
        self._methods = {"copyToServer": self.copy_to_server,
                         "destroy proxy": self._commit_destroy_proxy}

        # self._manager.Queue()

        self._remote_input_queue = multiprocessing.Queue()
        self._output_queues = {}

        # create thread to handle remote tasks
        self.remote_task_thread = Thread(target=self._process_remote_tasks)
        self.remote_task_thread.start()

        self._mount_server()

    ##########################################################################

    def _commit_destroy_proxy(self, id):
        """
        Method called as a remote task by a proxy. Puts a 'destroy proxy' task 
        into the internal queue of the master class.
        """
        # create task
        task = self.create_task(self._destroy_proxy, id)

        # submit task
        self.commit_task(task)

        # return result when task has been completed
        return task.result()

    ##########################################################################

    def _is_mounted(self):
        glob_vars = self.__settings_manager.get(["web_server"])

        # read the list of mounted filesystems from the proc/mounts file. It needs
        # to come from here rather then mtab, since cifs does not always update
        # mtab.
        with open("/proc/mounts", "r") as fp:
            mounted_list = fp.read()

        if mounted_list.count(glob_vars['web_server'] + " " + self._mount_point) != 0:
            return True
        else:
            return False

    ##########################################################################

    def _mount_server(self):
        """
        Creates and executes a shell script to mount the server, given the 
        parameters in the settings file. The script is run in a seperate 
        terminal window where prompts for any required passwords will be 
        given.
        """
        if ((not self._is_mounted()) and (not self.__awaiting_password)):
            self.__awaiting_password = True
            home = os.path.expanduser('~')
            glob_vars = self.__settings_manager.get(
                ["web_server", "web_username"])

            # build mounting script
            with open(home + "/.pysces_asi/mount-script.sh", "w") as fp:

                fp.write("#!/bin/sh\n")
                fp.write(
                    "echo \"### Password required to mount web server ###\"\n")
                fp.write("sudo mount -t cifs \"" + glob_vars[
                         'web_server'] + "\" \"" + self._mount_point + "\" -o uid=1000,gid=1000,user=\"" + glob_vars['web_username'] + "\"\n")

                fp.write("read -p \"Press any key to continue....\"")

            # make mount script executable
            os.chmod(home + "/.pysces_asi/mount-script.sh",
                     stat.S_IRWXU + stat.S_IRWXO + stat.S_IRWXG)

            # run script in xterm window
            p = Popen("xterm -e " + home + "/.pysces_asi/mount-script.sh",
                      shell=True, stdout=PIPE, stderr=PIPE)

            # wait for process to finish
            p.wait()

            # remove script file
            os.remove(home + "/.pysces_asi/mount-script.sh")

            self.__awaiting_password = False

    ##########################################################################

    def copy_to_server(self, source, dest):
        """
        Copies the source file to the destination. The source argument should
        be the complete path of the source file. The dest argument should be 
        the path to the destination file relative to the server folder specified
        in the settings file.
        """
        # create task
        task = self.create_task(self._copy_to_server, source, dest)

        # submit task
        self.commit_task(task, timeout=30)

        # return result when task has been completed
        return task.result()

    ##########################################################################

    def _copy_to_server(self, source, dest):
        log.info("Copying to server")
        folder_on_server = self.__settings_manager.get(["web_dir"])["web_dir"]
        os.chmod(source, stat.S_IRWXU + stat.S_IRWXO + stat.S_IRWXG)
        shutil.copyfile(source, os.path.normpath(
            self._mount_point + "/" + folder_on_server + "/" + dest))
        self.__settings_manager.set(
            {"output": "NetworkManager> Copied \"" + source + "\" to server"})

    ##########################################################################

    def exit(self):
        """
        Kills the internal worker thread, the remote task reading thread and the 
        manager process.
        """
        self._stay_alive = False
        self._remote_input_queue.put(None)
        self.remote_task_thread.join()
        self._remote_input_queue.close()
        ThreadQueueBase.exit(self)

    ##########################################################################

    def _destroy_proxy(self, id):
        """
        Removes the queue shared with the specified proxy.
        """
        q = self._output_queues.pop(id)
        q.close()

    ##########################################################################

    def _process_remote_tasks(self):
        """
        This method is run in a separate thread. It pulls remote task objects out of the shared
        queue object (shared between the master(=this class), and all the proxies) and commits the
        task to the internal task queue (by calling one of the public methods of the master class.
        The result is returned to the proxy via another shared queue (only shared between one proxy
        and the master).
        """
        while self._stay_alive or (not self._remote_input_queue.empty()):
            try:
                remote_task = self._remote_input_queue.get()
            except Empty:
                log.warn("Process get timed out")
                continue    

            if remote_task == None:
                continue

            try:
                result = self._methods[remote_task.method_name](
                    *remote_task.args, **remote_task.kwargs)
                if remote_task.method_name != "destroy proxy":
                    # if the proxy has been destroyed then this queue won't
                    # exist any more!
                    self._output_queues[remote_task.id].put(result)

            except Exception as ex:

                if remote_task.method_name != "destroy proxy":
                    # if the proxy has been destroyed then this queue won't
                    # exist any more!
                    self._output_queues[remote_task.id].put(ex)

    ##########################################################################

    def create_proxy(self):
        """
        Returns a proxy for the network manager object, this can be used to share the
        object between multiple processes.
        """
        # create task
        task = self.create_task(self._create_proxy)

        # submit task
        self.commit_task(task)

        # return result when task has been completed
        return task.result()

    ##########################################################################

    def _create_proxy(self):
        # create a unique ID for the new proxy
        current_ids = list(self._output_queues.keys())

        if len(current_ids) > 0:
            id = max(current_ids) + 1
        else:
            id = 0

        # create the shared queue object for the proxy's input queue
        proxy_input_queue = multiprocessing.Queue()  # self._manager.Queue()
        self._output_queues[id] = proxy_input_queue

        return _NetworkManagerProxy(id, proxy_input_queue, self._remote_input_queue)

    ##########################################################################
##########################################################################
