#!/usr/bin/python
from gi.repository import Gtk
import sys
from couchdb import Server
path = '/usr/local/cozy/cozy-files/couchdb-fuse/interface'

database = "cozy-files"
server = Server('http://localhost:5984/')
# Read file
f = open('/etc/cozy/cozy-files/couchdb.login')
lines = f.readlines()
f.close()
username = lines[0].strip()
password = lines[1].strip()

# Add credentials
server.resource.credentials = (username, password)

db = server[database]


class Preferences:
    def __init__(self):  
        self.builder = Gtk.Builder()
        self.builder.add_from_file('%s/preferences_ui.glade' % path)

        window = self.builder.get_object("window")
        window.connect('destroy', self.quit)
        button = self.builder.get_object("save")
        button.connect("clicked", self.on_button_clicked)
        res = db.view("device/all")
        for device in res:
            device = device.value
            self.builder.get_object("deviceName").set_text(device['login'])
            data = ""
            for docType in device['configuration']:
                data = """%s
                """ % data  
                data = data + docType  
            self.builder.get_object("data").set_text(data)
        window.show_all()

        Gtk.main()

    def on_button_clicked(self, widget):        
        Gtk.main_quit()
        sys.exit(0)

    def quit(self, widget):
        Gtk.main_quit()
        sys.exit(0)

if __name__ == "__main__":
    Preferences()	