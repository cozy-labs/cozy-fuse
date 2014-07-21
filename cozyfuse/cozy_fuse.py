#!/usr/bin/env python

import couchmount
import subprocess
import time
import sys
import requests
import appindicator
import gtk
import download_binary
import json
import replication
import logging

from multiprocessing import Process
from couchdb import Server
from couchdb.http import ResourceNotFound


DATABASE = "cozy-files"
PATH_COZY = "/usr/local/cozy/cozy-files/couchdb-fuse/src"


def database_connection():
    try:
        server = Server('http://localhost:5984/')
        server.version()
        return server
    except Exception:
        print('Cannot connect to the database')

server = Server('http://localhost:5984/')

# Get DB credentials from config file.
credentials_file = open('/etc/cozy/cozy-files/couchdb.login')
lines = credentials_file.readlines()
credentials_file.close()
USERNAME = lines[0].strip()
PASSWORD = lines[1].strip()

# Add credentials to database.
server.resource.credentials = (USERNAME, PASSWORD)


### Replication utils ###

LOCAL_DB_URL = 'http://%s:%s@localhost:5984/%s' % (USERNAME, PASSWORD,
                                                   DATABASE)


def _get_remote_url(name, pwd, url):
    '''
    Return remote url built from username, password and remote url.
    '''
    url = url.split('/')[2]
    return "https://%s:%s@%s/cozy" % (name, pwd, url)


### Widget ###


class Menu():
    def __init__(self, fuse, repli):
        db = server[DATABASE]

        self.ind = appindicator.Indicator(
            "cozy-files",
            "%s/icon/icon.png" % PATH_COZY,
            appindicator.CATEGORY_APPLICATION_STATUS)
        self.ind.set_status(appindicator.STATUS_ACTIVE)
        self.ind.set_attention_icon("%s/icon/icon.png" % PATH_COZY)

        # create a menu
        self.menu = gtk.Menu()

        # Add line to open cozy-files folder
        folder = gtk.MenuItem("Ouvrir le fichier cozy-files")
        self.menu.append(folder)
        folder.show()

        # Add line to start synchronisation
        sync = gtk.MenuItem("Forcer une synchronisation")
        self.menu.append(sync)
        sync.show()

        # Add line to stop automatic synchronisation
        stop = gtk.MenuItem("Stopper la synchronisation automatique")
        self.menu.append(stop)
        stop.show()

        # Add line to start autmotic synchronisation
        autoSync = gtk.MenuItem("Redemarrer la synchronisation automatique")
        self.menu.append(autoSync)
        #autoSync.show()

        # Add line for preferences
        preferences = gtk.MenuItem("Preferences...")
        self.menu.append(preferences)
        preferences.show()

        # Add line to quit cozy-files
        quit = gtk.MenuItem("Quitter cozy-files")
        self.menu.append(quit)
        quit.show()

        # Display menu
        self.menu.show()
        self.ind.set_menu(self.menu)

        def _recover_path():
            res = db.view("device/all")
            if not res:
                time.sleep(5)
                return _recover_path()
            else:
                try:
                    for device in res:
                        if not device.value["folder"]:
                            time.sleep(5)
                            return _recover_path()
                        else:
                            return device.value['folder']
                except ResourceNotFound:
                    print 'No connected device found'

        def openFolder(item):
            path = _recover_path()
            subprocess.Popen(["xdg-open", path])

        def stopSync(item):

            # Stop binary synchronisation
            repli.terminate()

            # Stop database replication
            r = requests.get('http://localhost:5984/_active_tasks')
            replications = json.loads(r.content)
            for rep in replications:
                idRep = str(rep["replication_id"])
                data = {"replication_id": "%s" % idRep, "cancel": True}
                r = requests.post("http://localhost:5984/_replicate",
                                  data=json.dumps(data),
                                  headers={'Content-Type': 'application/json'})
            stop.hide()
            autoSync.show()

        def startSync(item):
           # Start metadata replication
            res = db.view("device/all")
            for device in res:
                device = device.value
                url = device['url']
                pwd = device['password']
                name = device['login']
                idDevice = device['_id']
                replication.replicate_to_local_one_shot(
                    url, name, pwd, idDevice)
                replication.replicate_from_local_one_shot(
                    url, name, pwd, idDevice)

        def startAutoSync(item):

            # Start metadata replication
            res = db.view("device/all")
            for device in res:
                device = device.value
                url = device['url']
                pwd = device['password']
                name = device['login']
                idDevice = device['_id']
                replication.replicate_to_local(url, name, pwd, idDevice)
                replication.replicate_from_local(url, name, pwd, idDevice)

            # Start binaries synchronisation
            download = Process(target=download_binary.main)
            download.start()
            stop.show()
            autoSync.hide()

        def pref(item):
            subprocess.call([
                'python',
                '%s/windows/preferences_window.py' % PATH_COZY
            ])

        def exit(item):
            # Stop fuse and replication
            fuse.terminate()
            download.terminate()
            path = _recover_path()
            # Unmount cozy-files folder
            subprocess.call(["fusermount", "-u", path])
            # Remove icon
            gtk.main_quit()
            sys.exit(1)

        # Add connection between menu and function
        folder.connect('activate', openFolder)
        stop.connect('activate', stopSync)
        sync.connect('activate', startSync)
        autoSync.connect('activate', startAutoSync)
        preferences.connect('activate', pref)
        quit.connect('activate', exit)


def start_prog():
    # Start fuse
    print 'Start Cozy FUSE'
    fuse = Process(target=couchmount.main)
    fuse.start()

    # Start menu
    print 'Start Cozy Fuse Menu'
    #Menu(fuse, download)
    #gtk.main()

    #fuse.join()
    ##icon.join()
    #download.join()


try:

    server = database_connection()
    server = Server('http://localhost:5984/')
    db = server[DATABASE]
    request = requests.get('http://localhost:5984/_active_tasks')
    replications = json.loads(request.content)

    if len(replications) is 0:
        res = db.view("device/all")

        try:
            for device in res:
                device = device.value
                url = device['url']
                pwd = device['password']
                name = device['login']
                print "Start replication for device located at %s" % url

                idDevice = device['_id']
                replication.replicate_to_local(url, name, pwd, idDevice)
                replication.replicate_from_local(url, name, pwd, idDevice)

        except ResourceNotFound:
            print 'No connected device found'
            print 'Check that a device is registered in your local CouchDB' \
                  'instance'
            sys.exit(1)

    # Start binaries synchronisation
    download = Process(target=download_binary.main)
    download.start()

    start_prog()


except Exception, e:
    logging.exception("An error happened while starting cozy-fuse:")
