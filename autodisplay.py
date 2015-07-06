#!/usr/bin/env python2
#
# Usage:
#   ./autodisplay.py path ext1,ext2,extn [-t time]
#
# Blocks monitoring |path| and its subdirectories for modifications on
# files ending with suffix |extk|. Tracks all images in the directory that get
# read and written and displays the input and output images
#
# Example:
#   ./autodisplay.py [/testdir [.png,.jpg [time]]]
#
# Dependencies:
#   Linux, Python 2.6, Pyinotify, opencv, tkinter
#
import time
import datetime
import copy
import sys
import threading
from pprint import pprint

from optparse import OptionParser
from collections import Counter
from collections import defaultdict
import Tkinter as tk
from PIL import ImageTk

#import numpy as np
#import cv2
import pyinotify

REFRESH_TIME = 1
RESET_SECONDS = 1
IMG_EXTS = ['jpeg', 'jpg', 'png']

def main(path='.', exts=[], timeout=1):

    # create application window
    MainApp = Application(path, exts, timeout)

    MainApp.open_files['INPUT']['/home/micahc/opensource/OpenCVPytTools/cpptest/test.png'] = datetime.datetime(1984,1,1)
    MainApp.open_files['OUTPUT']['/home/micahc/opensource/OpenCVPytTools/cpptest/output.png'] = datetime.datetime(1984,1,1)
    # runs until window closed
    try:
        MainApp.after(RESET_SECONDS*1000, MainApp.poll_check)
        MainApp.display_images()
        MainApp.mainloop()
        return 0
    except:
        MainApp._on_closed()
        return -1


class Application(tk.Frame):
    open_files = defaultdict(dict)

    def __init__(self, path, exts, timeout, master=None):
        tk.Frame.__init__(self, master)
        self.grid(sticky=tk.N+tk.S+tk.E+tk.W)
        self.createWidgets()

        # create monitoring service
        wm = pyinotify.WatchManager()
        wm.add_watch(path, pyinotify.ALL_EVENTS, rec=True, auto_add=True)
        self.handler = OnWriteHandler(cwd=path, exts=exts, timeout=timeout)
        self.notifier = pyinotify.ThreadedNotifier(wm, default_proc_fun=self.handler)
        print('==> Start monitoring %s (type c^c to exit)' % path)
        self.notifier.start()

        # all open files (across groups)
        self.open_files = defaultdict(dict)  # open_files[group][filename] = time

        self.bind_all('<Destroy>', self._on_closed)

    def _on_closed(self):
        self.notifier.stop()
        self.quit()

    def createWidgets(self):
        top=self.winfo_toplevel()

        # make topmost window stretchable
        top.columnconfigure(0, weight=1)
        top.rowconfigure(0, weight=1)

        # make main window (inside top) stretchable with image boxes
        # appropriately sized
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)  # Quit
        self.rowconfigure(1, weight=1)  # Text Box
        self.rowconfigure(2, weight=100)
        self.rowconfigure(3, weight=1)  # Text box
        self.rowconfigure(4, weight=100)

        self.quit_botton = tk.Button(self, text='Quit', command=self._on_closed)
        self.quit_botton.grid(row=0, column=0, sticky=tk.N+tk.E+tk.W)
        label_in = tk.Label(self, text='Inputs')
        self.img_window_1 = tk.Canvas(self, bg='#FFFFFF')
        label_out = tk.Label(self, text='Outputs')
        self.img_window_2 = tk.Canvas(self, bg='#FFFFFF')

        label_in.grid(          row=1, column=0, sticky=tk.N+tk.S+tk.E+tk.W)
        self.img_window_1.grid( row=2, column=0, sticky=tk.N+tk.S+tk.E+tk.W)
        label_out.grid(         row=3, column=0, sticky=tk.N+tk.S+tk.E+tk.W)
        self.img_window_2.grid( row=4, column=0, sticky=tk.N+tk.S+tk.E+tk.W)

    def display_images(self):
        print("Display Images")
        for group, filedict in self.open_files.items():
            for path in filedict.keys():
                self.handler.bump_ignore(path)

                # placeholder
                f = open(path, "r")
                print(path)

    def poll_check(self):
        """
        Maintains a window of valid image times equal to 3 polling periods. The
        window is determined based on the time the last image was added, all
        images added more than 3 periods prior to the latest image are removed
        """
        print("Checkup")

        # reset timer
        self.after(RESET_SECONDS*1000, self.poll_check)

        # pop the images and add them to the buffer, updating their time stamps
        tmp_images = self.handler.pop_images(True, True)

        if not tmp_images or item_count(tmp_images) == 0:
            return

        print(tmp_images)
        now = datetime.datetime.utcnow()
        for group, active_images in tmp_images.items():
            for filename in active_images:
                self.open_files[group][filename] = now

        # remove images that have timed out
        for group, filedict in self.open_files.items():
            for filename in list(filedict.keys()):
                if (now-filedict[filename]).total_seconds() > REFRESH_TIME:
                    print("Removing {}".format(filename))
                    del filedict[filename]

        # update images
        self.display_images()


class OnWriteHandler(pyinotify.ProcessEvent):
    cwd = ""
    exts = []
    timeout = 1

    ignore = Counter()
    ignore_lock = threading.Lock()

    active = defaultdict(set)
    active_lock = threading.Lock()

    def __init__(self, cwd, exts, timeout):
        self.cwd = cwd
        self.exts = exts
        self.timeout = timeout

        # set of files to ignore, temporarily
        self.ignore = Counter()
        self.ignore_lock = threading.Lock()

        # set of active image filenames, keyed by group
        self.active = defaultdict(set)
        self.active_lock = threading.Lock()


    def pop_images(self, block=False, return_copy=True):
        """
        Clear all images from the set of active images, potentially returning
        the value just prior to deletion. Uses the appropriate lock to prevent
        race conditions. If block=True then wait for the lock to release before
        returning otherwise if the lock is used elsewhere it will return None.

        :param bool block: Block while waiting for the lock
        :param bool return_copy: Return a copy
        :return dict or None: Dictionary containing images just prior to
        deletion, keyed by type or - if the lock could not be acquired and
        block=False - None
        """
        if not self.active_lock.acquire(block):
            return None

        try:
            # get copy for return
            if return_copy:
                tmp = copy.deepcopy(self.active)
            else:
                tmp = None

            # pop off the list of images
            for k in self.active.keys():
                del self.active[k]
        except Exception as e:
            print(e)
            tmp = None

        self.active_lock.release()
        return tmp

    def get_images(self, block=False):
        """
        Get the current active images, and use the appropriate lock to prevent
        race conditions. Will wait for lock if block=True,
        otherwise if the lock is used elsewhere it will return None.

        :param bool block: Block while waiting for the lock
        :return dict or None: Dictionary containing images, keyed by type or -
        if the lock could not be acquired and block=False - None
        """
        if not self.active_lock.acquire(block):
            return None

        try:
            tmp = copy.deepcopy(self.active)
        except copy.error as e:
            print(e)
            tmp = None

        self.active_lock.release()
        return tmp

    def process_IN_CLOSE_NOWRITE(self, event):
        print("close read", event)
        self.ignore_lock.acquire()
        if self.ignore[event.pathname] == 0:
            self.ignore_lock.release()
            self.update_active(event.pathname, 'OUTPUTS')
        else:
            self.ignore[event.pathname] -= 1
            self.ignore_lock.release()

    def process_IN_CLOSE_WRITE(self, event):
        print("close write", event)
        self.ignore_lock.acquire()
        if self.ignore[event.pathname] == 0:
            self.ignore_lock.release()
            self.update_active(event.pathname, 'OUTPUTS')
        else:
            self.ignore[event.pathname] -= 1
            self.ignore_lock.release()

    def update_active(self, path, group):
        lower_path = path.lower()
        for ext in IMG_EXTS:
            if lower_path.endswith(ext):
                # set as active
                self.active_lock.acquire()
                self.active[group].add(path)
                self.active_lock.release()

    def bump_ignore(self, path, count=1):
        self.ignore_lock.acquire()
        self.ignore[path] += count
        self.ignore_lock.release()

def item_count(dictval):
    count = 0
    for val in dictval.values():
        if isinstance(val, str):
            count += 1
        else:
            count += len(val)
    return count


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-d", "--dir", default='.',
                      help="Directory to watch", metavar="DIR")
    parser.add_option("-e", "--exts", default=IMG_EXTS,
                      help="List of extensions, separated by commas")
    parser.add_option("-t", "--timeout", default=3,
                      help="Timeout for keeping images. Consider image rebuilt "
                      "when timeout has expired.")

    (options, args) = parser.parse_args()

    exit_status = main(options.dir, options.exts, options.timeout)

    sys.exit(exit_status)
