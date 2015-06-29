#!/usr/bin/env python2
#
# Usage:
#   ./autocompile.py path ext1,ext2,extn cmd
#
# Blocks monitoring |path| and its subdirectories for modifications on
# files ending with suffix |extk|. Run |cmd| each time a modification
# is detected. |cmd| is optional and defaults to 'make'.
#
# Example:
#   ./autocompile.py /my-latex-document-dir .tex,.bib "make pdf"
#
# Dependencies:
#   Linux, Python 2.6, Pyinotify
#
import time
import numpy as np
import datetime
from collections import defaultdict
from collections import Counter
from pprint import pprint
import subprocess
import sys
import pyinotify
import cv2

RESET_SECONDS = 1
IMG_EXTS = ['jpeg' ,'jpg', 'png']
#GROUPS = ['INPUTS', 'OUTPUTS']
GROUPS = ['OUTPUTS']

class OnWriteHandler(pyinotify.ProcessEvent):
    def __init__(self, cwd, extension, cmd):
        self.cwd = cwd
        self.extensions = extension.split(',')
        self.cmd = cmd

        # all open files (across groups)
        self.open_files = {}

        # set of files to ignore, temporarily
        self.ignore = Counter()

        # Open Window and create display buffer for each group
        self.group_buffers = {}
        for g in GROUPS:
            self.group_buffers[g] = np.empty([1000, 1000], np.uint8)
#            cv2.namedWindow(g)
#            cv2.imshow(g, self.group_buffers[g])

        # set of active images, keyed by group
        self.active = defaultdict(set)

        # if, during update the last update was too long ago, remove all
        self.last_update = datetime.datetime.utcnow()

    def tile(self, group):
        # make sure all the files in the file list have been read
        tmp = None
        pprint(self.active)
        for f in self.active[group]:
            print(f)
            if f not in self.open_files:
                # re-read file (and ignore in the interim)
                import ipdb; ipdb.set_trace()
                self.ignore[f] += 3
                self.open_files[f] = cv2.imread(f)
                tmp = f

        pprint(self.open_files)
        # tile the images, by factoring
        # TODO, for now just show the latest image
        buf = self.group_buffers[group]
        cv2.resize(self.open_files[tmp], buf.shape, buf)
        print('imshow', group, buf)
        cv2.imshow(group, buf)

    def check_show(self, path, group):
        now = datetime.datetime.utcnow()
        if (now - self.last_update).total_seconds() > RESET_SECONDS:
            self.active = defaultdict(set)
            self.last_update = now

        is_image = False
        print(path)
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
            self.tile(group)

    def check_recompile(self, path):
        for ext in self.extensions:
            if path.endswith(ext):
                print '==> Modification detected'
                subprocess.call(self.cmd.split(' '), cwd=self.cwd)
                return


    def process_IN_MODIFY(self, event):
        if self.ignore[event.pathname] == 0:
            self.check_recompile(event.pathname)
        else:
            self.ignore[event.pathname] -= 1


#    def process_IN_CLOSE_NOWRITE(self, event):
#        if self.ignore[event.pathname] == 0:
#            self.check_show(event.pathname, 'OUTPUTS')
#        else:
#            self.ignore[event.pathname] -= 1

    def process_IN_CLOSE_WRITE(self, event):
        if self.ignore[event.pathname] == 0:
            self.check_show(event.pathname, 'OUTPUTS')
        else:
            self.ignore[event.pathname] -= 1

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print >> sys.stderr, "Command line error: missing argument(s)."
        sys.exit(1)

    # Required arguments
    path = sys.argv[1]
    extension = sys.argv[2]

    # Optional argument
    cmd = 'make'
    if len(sys.argv) == 4:
        cmd = sys.argv[3]

    # Blocks monitoring
    wm = pyinotify.WatchManager()
    handler = OnWriteHandler(cwd=path, extension=extension, cmd=cmd)
    notifier = pyinotify.Notifier(wm, default_proc_fun=handler)
    wm.add_watch(path, pyinotify.ALL_EVENTS, rec=True, auto_add=True)
    print '==> Start monitoring %s (type c^c to exit)' % path
    notifier.loop()


def cvShowManyImages(title, *args):

    for imname in args:
        print(imname)
        img = cv2.imread(imnmae)
        print(img)

#        x = img->width;
#        y = img->height;
#
#        // Find whether height or width is greater in order to resize the image
#        max = (x > y)? x: y;
#
#        // Find the scaling factor to resize the image
#        scale = (float) ( (float) max / size );
#
#        // Used to Align the images
#        if( i % w == 0 && m!= 20) {
#            m = 20;
#            n+= 20 + size;
#        }
#
#        // Set the image ROI to display the current image
#        cvSetImageROI(DispImage, cvRect(m, n, (int)( x/scale ), (int)( y/scale )));
#
#        // Resize the input image and copy the it to the Single Big Image
#        cvResize(img, DispImage);
#
#        // Reset the ROI in order to display the next image
#        cvResetImageROI(DispImage);

