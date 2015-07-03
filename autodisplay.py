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
import datetime
import sys
import threading
from pprint import pprint

from optparse import OptionParser
from collections import Counter
from collections import defaultdict
import Tkinter as tk
from PIL import ImageTk

import numpy as np
import cv2
import pyinotify

RESET_SECONDS = 1
IMG_EXTS = ['jpeg' ,'jpg', 'png']

def main(path='.', exts=[], timeout=1):

    # create application window
     MainApp = Application('Auto Display')

    # runs until window closed
    try:
        MainApp.after(RESET_SECONDS*1000, MainApp.poll_check)
        MainApp.mainloop()

        sys.exit(0)
    except:
        sys.exit(-1)


class Application(tk.Frame):
    open_files = {}

    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.grid(sticky=tk.N+tk.S+tk.E+tk.W)
        self.createWidgets()

        # create monitoring service
        wm = pyinotify.WatchManager()
        wm.add_watch(path, pyinotify.ALL_EVENTS, rec=True, auto_add=True)
        self.handler = OnWriteHandler(cwd=path, exts=exts, timeout=timeout)
        notifier = pyinotify.ThreadedNotifier(wm, default_proc_fun=self.handler)
        print('==> Start monitoring %s (type c^c to exit)' % path)
        notifier.start()

        # all open files (across groups)
        self.open_files = {}

    def __del__(self):
        notifier.stop()

    def createWidgets(self):
        top=self.winfo_toplevel()

        # make topmost window stretchable
        top.columnconfigure(0, weight=1)
        top.rowconfigure(0, weight=1)

        # make main window (inside top) stretchable with image boxes
        # appropriately sized
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1) # Quit
        self.rowconfigure(1, weight=1) # Text Box
        self.rowconfigure(2, weight=100)
        self.rowconfigure(3, weight=1) # Text box
        self.rowconfigure(4, weight=100)

        self.quit = tk.Button(self, text='Quit', command=self.quit)
        self.quit.grid(row=0, column=0, sticky=tk.N+tk.E+tk.W)
        label_in = tk.Label(self, text='Inputs')
        self.img_window_1 = tk.Canvas(self, bg='#FFFFFF')
        label_out = tk.Label(self, text='Outputs')
        self.img_window_2 = tk.Canvas(self, bg='#FFFFFF')

        label_in.grid(          row=1, column=0, sticky=tk.N+tk.S+tk.E+tk.W)
        self.img_window_1.grid( row=2, column=0, sticky=tk.N+tk.S+tk.E+tk.W)
        label_out.grid(         row=3, column=0, sticky=tk.N+tk.S+tk.E+tk.W)
        self.img_window_2.grid( row=4, column=0, sticky=tk.N+tk.S+tk.E+tk.W)

    def poll_check(self):
        """
        Maintains a window of valid image times equal to 3 polling periods. The
        window is determined based on the time the last image was added, all
        images added more than 3 periods prior to the latest image are removed
        """

        print("Checkup")
        # pop the images and add them to the buffer, updating their time stamps

        #
        # remove images that have timed out

        # reset timer
        self.after(RESET_SECONDS*1000, MainApp.poll_check)

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


    def pop_images(self, block=False, copy=True):
        """
        Clear all images from the set of active images, potentially returning
        the value just prior to deletion. Uses the appropriate lock to prevent
        race conditions. If block=True then wait for the lock to release before
        returning otherwise if the lock is used elsewhere it will return None.

        :param bool block: Block while waiting for the lock
        :param bool copy: Return a copy
        :return dict or None: Dictionary containing images just prior to
        deletion, keyed by type or - if the lock could not be acquired and
        block=False - None
        """
        if not self.active_lock.acquire(block):
            return None

        try:
            tmp = copy.deepcopy(self.active)
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
        self.ignore_lock.acquire()
        if self.ignore[event.pathname] == 0:
            self.ignore_lock.release()
            self.check_show(event.pathname, 'OUTPUTS')
        else:
            self.ignore[event.pathname] -= 1
            self.ignore_lock.release()

    def process_IN_CLOSE_WRITE(self, event):
        self.ignore_lock.acquire()
        if self.ignore[event.pathname] == 0:
            self.ignore_lock.release()
            self.update_active(event.pathname, 'OUTPUTS')
        else:
            self.ignore[event.pathname] -= 1
            self.ignore_lock.release()

    def update_active(self, path, group):
        now = datetime.datetime.utcnow()

        path = path.lower()
        for ext in IMG_EXTS:
            if path.endswith(ext):
                # set as active
                self.active_lock.acquire()
                self.active[group].add(path)
                self.active_lock.release()

    def bump_ignore(path, count=1):
        self.ignore_lock.acquire()
        self.ignore[path] += count
        self.ignore_lock.release()

#def cvShowManyImages(title, *args):
#
#    for imname in args:
#        print(imname)
#        img = cv2.imread(imnmae)
#        print(img)
#
##        x = img->width;
##        y = img->height;
##
##        // Find whether height or width is greater in order to resize the image
##        max = (x > y)? x: y;
##
##        // Find the scaling factor to resize the image
##        scale = (float) ( (float) max / size );
##
##        // Used to Align the images
##        if( i % w == 0 && m!= 20) {
##            m = 20;
##            n+= 20 + size;
##        }
##
##        // Set the image ROI to display the current image
##        cvSetImageROI(DispImage, cvRect(m, n, (int)( x/scale ), (int)( y/scale )));
##
##        // Resize the input image and copy the it to the Single Big Image
##        cvResize(img, DispImage);
##
##        // Reset the ROI in order to display the next image
##        cvResetImageROI(DispImage);

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

    main(options.dir, options.exts, options.timeout)
