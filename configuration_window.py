#!/usr/bin/python
from gi.repository import Gtk
from requests import post
import requests
import gobject
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

def _recover_progression(self):
    url = 'http://localhost:5984/_active_tasks'
    r = requests.get(url)
    replications = json.loads(r.content)
    progress = 0
    for rep in replications:
        progress = progress + rep["progress"]
    return progress/200.

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
                        },
                "byUrl": {
                    "map": """function (doc) {
                                  if (doc.docType === \"Device\") {
                                      emit(doc.url, doc) 
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
                        },
                "byFullPath": {
                    "map": """function (doc) {
                                  if (doc.docType === \"Folder\") {
                                      emit(doc.path + '/' + doc.name, doc) 
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
                        },
                "byFullPath": {
                    "map": """function (doc) {
                                  if (doc.docType === \"File\") {
                                      emit(doc.path + '/' + doc.name, doc) 
                                  }
                              }"""
                        }
                    }
                }

        self.db["_design/binary"] = {
            "views": {
                "all": {
                    "map": """function (doc) {
                                  if (doc.docType === \"Binary\") {
                                      emit(doc.id, doc) 
                                  }
                               }"""
                        }
                    }
                }


        Gtk.main()

    def on_button_clicked(self, widget):

        def start_replication(self):
            # Check data
            self.pwdCozy = self.builder.get_object("password").get_text()
            self.url = self.builder.get_object("cozyUrl").get_text()
            self.device = self.builder.get_object("device").get_text()
            self.folder = self.builder.get_object("folder").get_current_folder()
            progressbar = self.builder.get_object("progressbar")
            if self.pwdCozy is "" or self.url is "" or self.device is "" or self.folder is "":
                self.builder.get_object("alert").set_text('Tous les champs doivent etre rempli')
                progressbar.set_fraction(0) 
                yield False
            else:
                # Add device in cozy
                progressbar.set_fraction(0.10)
                yield True
                data = {'login': self.device}
                try:
                    r = post(self.url + '/device/', data=data, auth=('owner', self.pwdCozy))                 
                    if r.status_code == 401:
                        self.builder.get_object("alert").set_text('Votre mot de passe est incorrect') 
                        progressbar.set_fraction(0) 
                        yield False                 
                    elif r.status_code == 400:
                        self.builder.get_object("alert").set_text('Ce nom est deja utilise par un autre device')
                        progressbar.set_fraction(0) 
                        yield False 

                    else: 
                        progressbar.set_fraction(0.20)
                        yield True
                        self.builder.get_object("alert").hide()             
                        # Call replication in one direction
                        data =  json.loads(r.content)
                        self.idDevice = data['id']
                        self.pwdDevice = data['password']
                        _replicate_to_local(self)
                        progressbar.set_fraction(0.25)
                        yield True
                        # Update device in local database and create filter
                        _create_filter(self)
                        #Call replication in other direction
                        _replicate_from_local(self)      
                        yield True
                        # Quit 
                        progress = _recover_progression(self)
                        progress = progress*0.75 + 0.25
                        while progress < 0.99:
                            progressbar.set_fraction(progress)               
                            yield True
                            progress = _recover_progression(self)
                            progress = progress*0.75 + 0.25
                        Gtk.main_quit()
                        sys.exit(0)  
                        yield False

                except Exception, e:
                    self.builder.get_object("alert").set_text("Verifiez l'url de votre cozy")
                    yield False

        task = start_replication(self)
        gobject.idle_add(task.next)

if __name__ == "__main__":
    Configuration()	