#!/usr/bin/env python2
#
# Blocks monitoring |path| and its subdirectories for modifications on
# files ending with suffix |extk|. Run |cmd| each time a modification
# is detected. |cmd| is optional and defaults to 'make'.
#
# Example:
#   ./autocompile.py -d /my-latex-document-dir -e .tex,.bib -c "make pdf"
#
# Dependencies:
#   Linux, Python 2.6, Pyinotify
#
import datetime
import subprocess
import sys
import pyinotify
from optparse import OptionParser

class OnWriteHandler(pyinotify.ProcessEvent):
    def __init__(self, cwd, exts, cmd):
        self.cwd = cwd
        self.extensions = exts
        self.cmd = cmd

        # if, during update the last update was too long ago, remove all
        self.last_update = datetime.datetime.utcnow()

    def check_recompile(self, path):
        for ext in self.extensions:
            if path.endswith(ext):
                print '==> Modification detected'
                subprocess.call(self.cmd.split(' '), cwd=self.cwd)
                return

    def process_IN_MODIFY(self, event):
        self.check_recompile(event.pathname)

def main(path, exts, cmd):
    # Blocks monitoring
    wm = pyinotify.WatchManager()
    handler = OnWriteHandler(cwd=path, exts=exts, cmd=cmd)
    notifier = pyinotify.Notifier(wm, default_proc_fun=handler)
    wm.add_watch(path, pyinotify.ALL_EVENTS, rec=True, auto_add=True)
    print '==> Start monitoring %s (type c^c to exit)' % path
    notifier.loop()

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-d", "--dir", default='.',
                      help="Directory to watch", metavar="DIR")
    parser.add_option("-e", "--exts", default='.cxx,.c,.cpp,.h',
                      help="List of extensions, separated by commas")
    parser.add_option("-c", "--cmd", default='make',
                      help="Command (default make).")

    (options, args) = parser.parse_args()

    main(options.dir, options.exts, options.cmd)
