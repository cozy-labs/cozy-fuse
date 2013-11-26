#!/usr/bin/python
from gi.repository import Gtk
from couchdb import Database, Document, ResourceNotFound, Server
from couchdb.client import Row, ViewResults
import gobject
import sys
import time
path = '/usr/local/cozy/cozy-files/couchdb-fuse/interface'

server = Server('http://localhost:5984/')
# Read file
f = open('/etc/cozy/cozy-files/couchdb.login')
lines = f.readlines()
f.close()
username = lines[0].strip()
password = lines[1].strip()
db = server['cozy-files']


class Download:
    def __init__(self):  
        def start_download():
            binaries = len(db.view('binary/all'))
            files = len(db.view('file/all'))
            if files is 0:
                Gtk.main_quit()
                sys.exit(0)  
                yield False
            else:
                while binaries/float(files) < 1: 
                    progressbar.set_fraction(binaries/float(files))
                    yield True
                    binaries = len(db.view('binary/all'))
                    files = len(db.view('file/all'))
                Gtk.main_quit()
                sys.exit(0)  
                yield False


        self.builder = Gtk.Builder()
        self.builder.add_from_file('%s/binaries_download_ui.glade' % path)
        window = self.builder.get_object("window")
        window.connect('destroy', self.quit)
        progressbar = self.builder.get_object("progressbar")
        window.show_all()

        task = start_download()
        gobject.idle_add(task.next)
        Gtk.main()

    def quit(self, widget):
        Gtk.main_quit()
        sys.exit(0)

if __name__ == "__main__":
    Download()	