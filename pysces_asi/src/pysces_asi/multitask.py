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
The multitask module provides classes to ease parallel processing, both 
multi-thread and multi-process. The two main classes are ThreadQueueBase and 
ProcessQueueBase, these use the same interface, and to some extent are 
interchangable. They have two main purposes. Syncronisation: by setting the 
number of workers to 1, method calls from multiple threads/processes are queued
and executed sequentially. Parallelisation: by setting the number of workers to
>1, method calls are processed concurrently by multiple threads or processes.
"""
import time
import traceback
import multiprocessing
import logging

from Queue import Queue
from threading import Event, Thread, currentThread

log = logging.getLogger()


class RemoteTask:
    """
    Represents a task created by a proxy object that must be executed by the
    master class (which may be running in a separate process).
    """

    def __init__(self, id_, method, *args, **kwargs):
        self.id = id_
        self.method_name = method
        self.args = args
        self.kwargs = kwargs

    ###########################################################################
###########################################################################


class ThreadTask:
    """
    Represents a task to be executed by a ThreadQueueBase instance. The 
    ThreadTask object provides a method to execute the task, and a method to 
    retrieve the result when it is ready.
    """

    def __init__(self, func, *args, **kwargs):
        self._function = func
        self._args = args
        self._kwargs = kwargs
        self._return_value = None
        self.completed = Event()
        self._exception = None
        self._traceback = None

    ###########################################################################

    def execute(self):
        """
        Executes the task.
        """
        # try to run the function. If it fails then store the exception object
        # to pass to outside thread
        try:
            log.info("Executing task: " + str(currentThread()))
            self._return_value = self._function(*self._args, **self._kwargs)

        # catch any exceptions that were raised during execution so that they
        # can be raised in the calling thread, rather than the worker thread.
        except Exception as xxx_todo_changeme:
            self._exception = xxx_todo_changeme
            log.warning("\nException in thread: " + str(currentThread()))
            traceback.print_exc()

        # set the event to true, to show that the task is finished
        self.completed.set()

    ###########################################################################

    def result(self):
        """
        Blocks until the task is executed and then returns the result. If the
        target function has no return value then None is returned when the 
        task is completed. If the target function raised an exception when it
        was executed, then calling result() will raise the same exception.
        """
        self.completed.wait()
        if self._exception is None:
            return self._return_value
        else:
            traceback.print_exc()
            raise self._exception

    ###########################################################################
###########################################################################


class ThreadQueueBase:
    """
    Base class for classes running in separate threads and using a task queue
    for input.
    """

    def __init__(self, workers=1, maxsize=0, name="Un-named"):
        self._task_queue = Queue(maxsize=maxsize)
        self._workers = []
        self._stay_alive = True
        self.name = name
        self._exit_event = Event()
        for i in range(workers):
            self._workers.append(Thread(target=self._process_tasks))
            self._workers[i].setName(self.name + " thread " + str(i))
            self._workers[i].start()

    ###########################################################################

    def _process_tasks(self):
        """
        Run by the internal worker thread(s), this method pulls tasks out of
        the input queue and executes them.
        """
        while self._stay_alive or (not self._task_queue.empty()):
            # pull a task out of the queue

            task = self._task_queue.get()

            log.info(
                "Executing worker task (in ThreadQueueBase): ")
            # execute the task
            task.execute()

            # tell the queue that execution is complete
            self._task_queue.task_done()

            del task
        self._exit_event.set()

    ###########################################################################

    def create_task(self, func, *args, **kwargs):
        """
        Creates a new task object which can be submitted for execution using 
        the commit_task() method.
        """
        return ThreadTask(func, *args, **kwargs)

    ###########################################################################

    def commit_task(self, task, timeout=None):
        """
        Puts the specified task into the input queue where it will be executed
        by one of the internal worker threads. The task's result() method be
        used for syncronising with task completion.
        """
        # only queue task if should be alive - tasks submitted after exit is
        # encountered will be ignored
        for thread in self._workers:
            if not thread.isAlive():
                print(
                    "### Error! ### Worker thread in " + self.name + " has died!")
                raise RuntimeError(
                    "### Error! ### Worker thread in " + self.name + " has died!")

        if self._stay_alive:
            self._task_queue.put(task, block=False, timeout=timeout)

    ###########################################################################

    def exit(self):
        """
        Waits for all remaining tasks in the input queue to finish and then
        kills the worker threads.
        """
        num_alive = 0
        for t in self._workers:
            if t.is_alive():
                num_alive += 1

        # submit one exit task for each thread that is still alive
        while num_alive > 0:
            task = self.create_task(self._exit)
            self._task_queue.put(task)
            self._exit_event.wait()
            self._exit_event.clear()
            num_alive -= 1

        # block until outstanding tasks have been completed
        for thread in self._workers:
            thread.join()

    ###########################################################################

    def _exit(self):
        """
        Method run by the worker threads in order to break out of the 
        _process_tasks() loop.
        """
        self._stay_alive = False

    ###########################################################################
###########################################################################


class ProcessQueueBase:
    """
    Base class for running task in separate processes and using a task queue
    for input.
    """

    def __init__(self, workers=1, maxsize=0, name="Un-named"):
        # create a manager for creating shared objects
        #self._manager = multiprocessing.Manager()
        self.name = name
        # create an input queue
        self._input_queue = Queue(maxsize=maxsize)

        self._process_count = 0
        self._max_process_count = workers
        self._active_processes = []
        self._stay_alive = True

        # create a thread to read from the input queue and start tasks in their
        # own process
        self._input_thread = Thread(target=self._process_tasks)
        self._input_thread.setName(self.name + " input thread")
        self._input_thread.start()

    ###########################################################################

    def _process_tasks(self):
        """
        Run by the internal worker thread, this method pulls tasks out of
        the input queue and creates child processes to execute them. A maximum
        of 'workers' number of child processes will be allowed to run at any
        one time.
        """
        while self._stay_alive or (not self._input_queue.empty()):

            task = self._input_queue.get()

            # if task is None, then it means we should exit - go back to
            # beginning of loop
            if task is None:
                continue

            # Python's popen system is not thread safe, so occasionally it will throw up
            # a OSError "No child processes" during the following bit of code. This *might*
            # have been fixed in python2.6, but nobody seems sure, so just in case we wrap it
            # in a try except block
            log.info(
                "Executing worker task (in ProcessQueueBase): ")
            try:
                # otherwise wait for active process count to fall below max
                # count
                while self._process_count >= self._max_process_count:
                    i = 0
                    while i < len(self._active_processes):
                        if not self._active_processes[i].is_alive():
                            self._active_processes[i].join()
                            self._active_processes.pop(i)
                            self._input_queue.task_done()
                            i = i - 1
                            self._process_count = self._process_count - 1
                        i = i + 1
                    time.sleep(0.001)
            except OSError:
                log.warning(
                    "Syncronisation error in ProcessQueueBase! Task has been re-submitted.: ")
                print(
                    "Syncronisation error in ProcessQueueBase! Task has been re-submitted.")
                self._input_queue.put(task)
                continue

            not_started = True
            while not_started:
                try:
                    # create a new process to run the task
                    p = multiprocessing.Process(target=task.execute)
                    self._active_processes.append(p)
                    self._process_count = self._process_count + 1
                    p.start()
                    not_started = False
                except OSError:
                    self._active_processes.remove(p)
                    self._process_count = self._process_count - 1

    ###########################################################################

    def create_task(self, func, *args, **kwargs):
        """
        Creates a new task object which can be submitted for execution using 
        the commit_task() method.
        """
        #n = self._manager.Namespace()
        q = multiprocessing.Queue()
        e = multiprocessing.Event()
        task = ProcessTask(q, e, func, *args, **kwargs)
        return task

    ###########################################################################

    def commit_task(self, task):
        """
        Puts the specified task into the input queue where it will be executed
        in its own process. The task's result() method be used for syncronising 
        with task completion.
        """
        if not self._input_thread.isAlive():
            print(
                "### Error! ### Worker thread in " + self.name + " has died!")
            raise RuntimeError(
                "### Error! ### Worker thread in " + self.name + " has died!")
        self._input_queue.put(task)

    ###########################################################################

    def exit(self):
        """
        Waits for all the tasks in the input queue to be completed then kills 
        the internal worker thread and the manager process.
        """
        self._stay_alive = False
        self._input_queue.put(None)
        self._input_thread.join()

        for process in self._active_processes:
            process.join()

    ###########################################################################
###########################################################################


class ProcessTask:
    """
    Represents a task to be executed by a ProcessQueueBase instance. The 
    ProcessTask object provides a method to execute the task, and a method to 
    retrieve the result when it is ready.
    """

    def __init__(self, return_queue, shared_event, func, *args, **kwargs):

        self._function = func
        self._args = args
        self._kwargs = kwargs
        self.return_queue = return_queue
        #self.namespace.exception = None
        self.completed = shared_event

    ###########################################################################

    def execute(self):
        """
        Executes the task.
        """
        # try to run the function. If it fails then store the exception object
        # to pass to outside thread
        try:
            log.info("Excecute task in ProcessTask")
            self.return_queue.put(self._function(*self._args,
                                                 **self._kwargs))

        # catch any exceptions that were raised during execution so that they can
        # be raised in the calling thread, rather than the internal worker
        # thread
        except Exception as ex:
            self.return_queue.put(ex)

        finally:
            self.completed.set()

    ###########################################################################

    def result(self):
        """
        Blocks until the task is executed and then returns the result. If the 
        target function has no return value then None is returned when the 
        task is completed. If the target function raised an exception when it
        was executed, then calling result() will raise the same exception.
        """
        log.info("Waiting for result in ProcessTask")
        self.completed.wait()
        return_value = self.return_queue.get()
        log.info("Got result in ProcessTask")
        if isinstance(return_value, Exception):
            raise return_value
        else:
            return return_value

    ###########################################################################
###########################################################################
