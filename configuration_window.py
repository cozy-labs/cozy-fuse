#!/usr/bin/python
from gi.repository import Gtk
from requests import post
import requests
from couchdb import Database, Document, ResourceNotFound, Server
from couchdb.client import Row, ViewResults
import threading
import subprocess	
import time
import sys
try:
    import simplejson as json
except ImportError:
    import json # Python 2.6
database = "cozy-files"

def _replicate_to_local(self):
    target = 'http://%s:%s@localhost:5984/%s' % (self.username, self.password, database)
    url = self.url.split('/')
    source = "https://%s:%s@%s/cozy" % (self.device, self.pwdDevice, url[2])
    self.rep = self.server.replicate(source, target, continuous=True, filter="%s/filter" %self.idDevice)

def _replicate_from_local(self):
    source = 'http://%s:%s@localhost:5984/%s' % (self.username, self.password, database)
    url = self.url.split('/')
    target = "https://%s:%s@%s/cozy" % (self.device, self.pwdDevice, url[2])
    self.rep = self.server.replicate(source, target, continuous=True, filter="%s/filter" %self.idDevice)

def _create_filter(self):
    res = self.db.view("device/all")
    if not res:
        time.sleep(5)
        return _create_filter(self)
    else:
        for device in res:
            device = device.value
            # Update device
            device['password'] = self.pwdDevice
            device['folder'] = self.folder
            device['change'] = 0
            device['url'] = self.url
            self.db.save(device)
            # Generate filter
            filter = """function(doc, req) {
                    if(doc._deleted) {
                        return true; 
                    }
                    if ("""
            for docType in device["configuration"]:
                filter = filter + "(doc.docType && doc.docType === \"%s\") ||" %docType
            filter = filter[0:-3]
            filter = filter + """){
                        return true; 
                    } else { 
                        return false; 
                    }
                }"""
            doc = {
                "_id": "_design/%s" % self.idDevice,
                "views": {},
                "filters": {
                    "filter": filter
                    }
                }
            self.db.save(doc) 
            return True


class Configuration:
    def __init__(self):  
        self.builder = Gtk.Builder()
        self.builder.add_from_file('/etc/cozy-files/couchdb-fuse/config_ui.glade')

        window = self.builder.get_object("windowConf")
        window.show_all()
        self.builder.get_object("spinner").hide()
        button = self.builder.get_object("config")
        button.connect("clicked", self.on_button_clicked)
        window.connect("delete-event", Gtk.main_quit)
        self.server = Server('http://localhost:5984/')
        # Read file
        f = open('/etc/cozy-files/couchdb.login')
        lines = f.readlines()
        f.close()
        self.username = lines[0].strip()
        self.password = lines[1].strip()
        # Create database
        self.db = self.server.create(database)

        self.db["_design/device"] = {
            "views": {
                "all": {
                    "map": """function (doc) {
                                  if (doc.docType === \"Device\") {
                                      emit(doc.id, doc) 
                                  }
                              }"""
                        }
                    }
                } 

        self.db["_design/folder"] = {
            "views": {
                "all": {
                    "map": """function (doc) {
                                  if (doc.docType === \"Folder\") {
                                      emit(doc.id, doc) 
                                  }
                               }"""
                        },
                "byFolder": {
                    "map": """function (doc) {
                                  if (doc.docType === \"Folder\") {
                                      emit(doc.path, doc) 
                                  }
                              }"""
                        }
                    }
                }

        self.db["_design/file"] = {
            "views": {
                "all": {
                    "map": """function (doc) {
                                  if (doc.docType === \"File\") {
                                      emit(doc.id, doc) 
                                  }
                               }"""
                        },
                "byFolder": {
                    "map": """function (doc) {
                                  if (doc.docType === \"File\") {
                                      emit(doc.path, doc) 
                                  }
                              }"""
                        }
                    }
                }

        Gtk.main()

    def on_button_clicked(self, widget):
        #self.builder.get_object("alert").hide()
        self.spinner = self.builder.get_object("spinner")
        self.spinner.start()
        self.spinner.show()
	
        def start_replication(self):
            # Check data
            self.pwdCozy = self.builder.get_object("password").get_text()
            self.url = self.builder.get_object("cozyUrl").get_text()
            self.device = self.builder.get_object("device").get_text()
            self.folder = self.builder.get_object("folder").get_current_folder()
            if self.pwdCozy is "" or self.url is "" or self.device is "" or self.folder is "":
                self.builder.get_object("alert").set_text('Tous les champs doivent etre rempli')
                sys.exit(1)
            else:
                # Add device in cozy
                data = {'login': self.device}
                try:
                	r = post(self.url + '/device', data=data, auth=('owner', self.pwdCozy))                	
	                if r.status_code == 401:
	                    self.spinner.hide()
	                    self.builder.get_object("alert").set_text('Votre mot de passe est incorrect') 
                	    sys.exit(1)                 
	                elif r.status_code == 400:
	                    self.spinner.hide()
	                    self.builder.get_object("alert").set_text('Ce nom est deja utilise par un autre device')
                	    sys.exit(1)    
	                else:
	                    self.builder.get_object("alert").hide() 			
	                    # Call replication in one direction
	                    data =  json.loads(r.content)
	                    self.idDevice = data['id']
	                    self.pwdDevice = data['password']
	                    _replicate_to_local(self)
	                    # Update device in local database and create filter
	                    _create_filter(self)
	                    #Call replication in other direction
	                    _replicate_from_local(self)
	                    # Quit  
	                    Gtk.main_quit()
                	    sys.exit(0)
                except Exception, e:
                    self.spinner.hide()
                    self.builder.get_object("alert").set_text("Verifiez l'url de votre cozy")
                    sys.exit(1)

        t = threading.Thread(target = start_replication, args=(self,))
        t.start()
        t.join()
        self.spinner.hide()
        print t

if __name__ == "__main__":
    Configuration()	