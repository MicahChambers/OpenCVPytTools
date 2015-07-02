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
#GROUPS = ['INPUTS', 'OUTPUTS']
GROUPS = ['OUTPUTS']
MainApp = None

def main(path='.', exts=[], timeout=1):
    global MainApp

    # create monitoring service
    wm = pyinotify.WatchManager()
    wm.add_watch(path, pyinotify.ALL_EVENTS, rec=True, auto_add=True)
    handler = OnWriteHandler(cwd=path, exts=exts, timeout=timeout)
    notifier = pyinotify.ThreadedNotifier(wm, default_proc_fun=handler)
    #import ipdb; ipdb.set_trace()
    print '==> Start monitoring %s (type c^c to exit)' % path
    notifier.start()

    # create application window
    MainApp = Application()
    MainApp.master.title('Sample application')

    # runs until window closed
    try:
        MainApp.after(2000, MainApp.checkup)
        MainApp.mainloop()
        notifier.stop()
    except:
        notifier.stop()
    sys.exit(0)


class Application(tk.Frame):
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.grid(sticky=tk.N+tk.S+tk.E+tk.W)
        self.createWidgets()

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

    def checkup(self):
        print("Checkup")
        self.after(2000, MainApp.checkup)

    def change_images(self, inputs, outputs):
        print("Configuration updated!")
#        self.img = tk.PhotoImage(file='cpptest/test.ppm')
#        id1 = self.img_window_1.create_oval(10, 10, 100, 100)
#        id2 = self.img_window_1.create_image(100, 100, image=self.img)
#        id3 = self.img_window_2.create_image(100, 100, image=self.img)

class OnWriteHandler(pyinotify.ProcessEvent):
    def __init__(self, cwd, exts, timeout):
        self.cwd = cwd
        self.exts = exts
        self.timeout = timeout

        # all open files (across groups)
        self.open_files = {}

        # set of files to ignore, temporarily
        self.ignore = Counter()

        # set of active images, keyed by group
        self.active = defaultdict(set)

        # if, during update the last update was too long ago, remove all
        self.last_update = datetime.datetime.utcnow()

#    def tile(self, group):
#        # make sure all the files in the file list have been read
#        tmp = None
#        pprint(self.active)
#        for f in self.active[group]:
#            print(f)
#            if f not in self.open_files:
#                # re-read file (and ignore in the interim)
#                import ipdb; ipdb.set_trace()
#                self.ignore[f] += 3
#                self.open_files[f] = Image.open(f)
#                tmp = f
#
#        pprint(self.open_files)
#        # tile the images, by factoring
#        # TODO, for now just show the latest image
#        #buf = self.group_buffers[group]
#        #cv2.resize(self.open_files[tmp], buf.shape, buf)
#        #print('imshow', group, buf)
#        #cv2.imshow(group, buf)
#        # will just open up lots of images! need to modify in place?
#        self.open_files[tmp].show()

    def check_show(self, path, group):
        now = datetime.datetime.utcnow()
        if (now - self.last_update).total_seconds() > RESET_SECONDS:
            self.active = defaultdict(set)
            self.last_update = now

        is_image = False
        path = path.lower()
        for ext in IMG_EXTS:
            if path.endswith(ext):
                is_image = True

                # set as active
                self.active[group].add(path)
                print('make active {}'.format(self.active))
                # remove from buffered files since there was a change
                if path in self.open_files:
                    del self.open_files[path]

        # update buffer with new image
        if is_image:
            pprint(self.active)
            #self.tile(group)

    def process_IN_CLOSE_NOWRITE(self, event):
        if self.ignore[event.pathname] == 0:
            self.check_show(event.pathname, 'OUTPUTS')
        else:
            self.ignore[event.pathname] -= 1

    def process_IN_CLOSE_WRITE(self, event):
        if self.ignore[event.pathname] == 0:
            self.check_show(event.pathname, 'OUTPUTS')
        else:
            self.ignore[event.pathname] -= 1


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
