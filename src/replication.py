from couchdb import Server
from couchdb.client import Row, ViewResults

try:
    import simplejson as json
except ImportError:
    import json # Python 2.6
import requests
import os

DATABASE = "cozy-files"
SERVER = Server('http://localhost:5984/')

def replicate_to_local(url, device, pwdDevice, idDevice):
    '''
    Replicate metadata from cozy to local
    '''
    (username, password) = _get_credentials()
    target = 'http://%s:%s@localhost:5984/%s' % (username, password, DATABASE)
    url = url.split('/')
    source = "https://%s:%s@%s/cozy" % (device, pwdDevice, url[2])
    SERVER.replicate(source, target, continuous=True, filter="%s/filter" %idDevice)


def replicate_from_local(url, device, pwdDevice, idDevice):
    '''
    Replicate metadata from local to cozy
    '''
    (username, password) = _get_credentials()
    source = 'http://%s:%s@localhost:5984/%s' % (username, password, DATABASE)
    url = url.split('/')
    target = "https://%s:%s@%s/cozy" % (device, pwdDevice, url[2])
    SERVER.replicate(source, target, continuous=True, filter="%s/filter" %idDevice)


def replicate_to_local_start_seq(url, device, pwdDevice, idDevice, seq):
    '''
    Replicate metadata from cozy to local
    '''
    (username, password) = _get_credentials()
    target = 'http://%s:%s@localhost:5984/%s' % (username, password, DATABASE)
    url = url.split('/')
    source = "https://%s:%s@%s/cozy" % (device, pwdDevice, url[2])
    SERVER.replicate(source, target, continuous=True, filter="%s/filter" %idDevice, since_seq=seq)


def replicate_from_local_start_seq(url, device, pwdDevice, idDevice, seq):
    '''
    Replicate metadata from local to cozy
    '''
    (username, password) = _get_credentials()
    source = 'http://%s:%s@localhost:5984/%s' % (username, password, DATABASE)
    url = url.split('/')
    target = "https://%s:%s@%s/cozy" % (device, pwdDevice, url[2])
    SERVER.replicate(source, target, continuous=True, filter="%s/filter" %idDevice, since_seq=seq)


def replicate_to_local_one_shot(url, device, pwdDevice, idDevice):
    '''
    Replicate metadata from cozy to local with a one-shot replication
    '''
    (username, password) = _get_credentials()
    target = 'http://%s:%s@localhost:5984/%s' % (username, password, DATABASE)
    url = url.split('/')
    source = "https://%s:%s@%s/cozy" % (device, pwdDevice, url[2])
    SERVER.replicate(source, target, filter="%s/filter" %idDevice)


def replicate_from_local_one_shot(url, device, pwdDevice, idDevice):
    '''
    Replicate metadata from local to cozy with a one-shot replication
    '''
    (username, password) = _get_credentials()
    source = 'http://%s:%s@localhost:5984/%s' % (username, password, DATABASE)
    url = url.split('/')
    target = "https://%s:%s@%s/cozy" % (device, pwdDevice, url[2])
    SERVER.replicate(source, target, filter="%s/filter" %idDevice)


def replicate_to_local_one_shot_without_deleted(url, device, pwdDevice, idDevice):
    '''
    Replicate metadata from cozy to local with a one-shot replication
    '''
    (username, password) = _get_credentials()
    target = 'http://%s:%s@localhost:5984/%s' % (username, password, DATABASE)
    url = url.split('/')
    source = "https://%s:%s@%s/cozy" % (device, pwdDevice, url[2])
    return SERVER.replicate(source, target, filter="%s/filterDocType" %idDevice)


def replicate_from_local_one_shot_without_deleted(url, device, pwdDevice, idDevice):
    '''
    Replicate metadata from local to cozy with a one-shot replication
    '''
    (username, password) = _get_credentials()
    source = 'http://%s:%s@localhost:5984/%s' % (username, password, DATABASE)
    url = url.split('/')
    target = "https://%s:%s@%s/cozy" % (device, pwdDevice, url[2])
    return SERVER.replicate(source, target, filter="%s/filterDocType" %idDevice)


def recover_progression():
    '''
    Recover progression of metadata replication
    '''
    url = 'http://localhost:5984/_active_tasks'
    r = requests.get(url)
    replications = json.loads(r.content)
    prog = 0   
    for rep in replications:
        if 'replication_id' in rep:
            if rep['replication_id'].find('continuous') is not -1:
                prog = prog + rep["progress"]
    return prog/200.


def recover_progression_binary():
    '''
    Recover progression of binaries download
    '''    
    db = SERVER[DATABASE]
    files = db.view("file/all")
    binaries = db.view('binary/all')
    if len(files) is 0:
        return 1
    else:
        return len(binaries)/float(len(files))


def add_view(docType, db):
    '''
    Add view in database
        docType {string}: docType of view
        db {Object}: database
    '''
    db["_design/%s" %docType.lower()] = {
    "views": {
        "all": {
            "map": """function (doc) {
                          if (doc.docType === \"%s\") {
                              emit(doc.id, doc) 
                          }
                       }""" %docType
                },
        "byFolder": {
            "map": """function (doc) {
                          if (doc.docType === \"%s\") {
                              emit(doc.path, doc) 
                          }
                      }""" %docType
                },
        "byFullPath": {
            "map": """function (doc) {
                          if (doc.docType === \"%s\") {
                              emit(doc.path + '/' + doc.name, doc) 
                          }
                      }""" %docType
                }
            }
        }

def init_database():
    '''
    Initialize database:
        * Create database
        * Initialize folder, file, binary and device views
    '''
    # Create database
    db = SERVER.create(DATABASE)

    add_view('Folder', db)
    add_view('File', db)

    db["_design/device"] = {
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

    db["_design/binary"] = {
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

def init_device(url, pwdDevice, idDevice):
    '''
    Initialize device
        url {string}: cozy url
        pwdDevice {string}: device password
        idDevice {Number}: device id
    '''
    db = SERVER[DATABASE]
    res = db.view("device/all")
    if not res:
        init_device(url, pwdDevice, idDevice)
    else:
        for device in res:
            device = device.value
            # Update device
            folder = "%s/cozy-files" % os.environ['HOME']
            device['password'] = pwdDevice
            device['change'] = 0
            device['url'] = url
            device['folder'] = folder
            db.save(device)
            # Generate filter
            filter = """function(doc, req) {
                    if(doc._deleted) {
                        return true; 
                    }
                    if ("""
            filter2 ="""function(doc, req) {
                    if ("""
            for docType in device["configuration"]:
                filter = filter + "(doc.docType && doc.docType === \"%s\") ||" %docType
                filter2 = filter2 + "(doc.docType && doc.docType === \"%s\") ||" %docType
            filter = filter[0:-3]
            filter2 = filter2[0:-3]
            filter = filter + """){
                        return true; 
                    } else { 
                        return false; 
                    }
                }"""
            filter2 = filter2 + """){
                        return true; 
                    } else { 
                        return false; 
                    }
                }"""
            doc = {
                "_id": "_design/%s" % idDevice,
                "views": {},
                "filters": {
                    "filter": filter,
                    "filterDocType": filter2
                    }
                }
            db.save(doc) 
            return False


def _get_credentials():
    '''
    Get credentials from config file.
    '''
    credentials_file = open('/etc/cozy/cozy-files/couchdb.login')
    lines = credentials_file.readlines()
    credentials_file.close()
    username = lines[0].strip()
    password = lines[1].strip()
    return (username, password)
