from couchdb import Server
from couchdb.http import PreconditionFailed, ResourceConflict

try:
    import simplejson as json
except ImportError:
    import json  # Python 2.6
import requests
import os

SERVER = Server('http://localhost:5984/')


def replicate_to_local(database, url, device, pwdDevice, idDevice):
    '''
    Replicate metadata from cozy to local.
    '''
    (username, password) = _get_credentials()
    target = 'http://%s:%s@localhost:5984/%s' % (username, password, database)
    url = url.split('/')
    source = "https://%s:%s@%s/cozy" % (device, pwdDevice, url[2])
    SERVER.replicate(source, target,
                     continuous=True, filter="%s/filter" % idDevice)


def replicate_from_local(database, url, device, pwdDevice, idDevice):
    '''
    Replicate metadata from local to cozy.
    '''
    (username, password) = _get_credentials()
    source = 'http://%s:%s@localhost:5984/%s' % (username, password, database)
    url = url.split('/')
    target = "https://%s:%s@%s/cozy" % (device, pwdDevice, url[2])
    SERVER.replicate(source, target,
                     continuous=True, filter="%s/filter" % idDevice)


def replicate_to_local_start_seq(database, url,
                                 device, pwdDevice, idDevice, seq):
    '''
    Replicate metadata from cozy to local
    '''
    (username, password) = _get_credentials()
    target = 'http://%s:%s@localhost:5984/%s' % (username, password, database)
    url = url.split('/')
    source = "https://%s:%s@%s/cozy" % (device, pwdDevice, url[2])
    SERVER.replicate(source, target,
                     continuous=True, filter="%s/filter" % idDevice,
                     since_seq=seq)


def replicate_from_local_start_seq(database, url,
                                   device, pwdDevice, idDevice, seq):
    '''
    Replicate metadata from local to cozy
    '''
    (username, password) = _get_credentials()
    source = 'http://%s:%s@localhost:5984/%s' % (username, password, database)
    url = url.split('/')
    target = "https://%s:%s@%s/cozy" % (device, pwdDevice, url[2])
    SERVER.replicate(source, target,
                     continuous=True, filter="%s/filter" % idDevice,
                     since_seq=seq)


def replicate_to_local_one_shot(database, url, device, pwdDevice, idDevice):
    '''
    Replicate metadata from cozy to local with a one-shot replication
    '''
    (username, password) = _get_credentials()
    #target = 'http://%s:%s@localhost:5984/%s' % (username, password, database)
    target = 'http://localhost:5984/%s' % database

    url = url.split('/')
    source = "https://%s:%s@%s/cozy" % (device, pwdDevice, url[2])
    SERVER.replicate(source, target, filter="%s/filter" % idDevice)


def replicate_from_local_one_shot(database, url, device, pwdDevice, idDevice):
    '''
    Replicate metadata from local to cozy with a one-shot replication
    '''
    (username, password) = _get_credentials()
    source = 'http://%s:%s@localhost:5984/%s' % (username, password, database)
    url = url.split('/')
    target = "https://%s:%s@%s/cozy" % (device, pwdDevice, url[2])
    SERVER.replicate(source, target, filter="%s/filter" % idDevice)


def replicate_to_local_one_shot_without_deleted(database, url, device,
                                                pwdDevice, idDevice):
    '''
    Replicate metadata from cozy to local with a one-shot replication
    '''
    (username, password) = _get_credentials()
    #target = 'http://%s:%s@localhost:5984/%s' % (username, password, database)
    target = 'http://localhost:5984/%s' % database
    url = url.split('/')
    source = "https://%s:%s@%s/cozy" % (device, pwdDevice, url[2])
    filter_name = "%s/filterDocType" % idDevice

    SERVER.replicate(source, target, filter=filter_name)


def replicate_from_local_one_shot_without_deleted(database, url, device,
                                                  pwdDevice, idDevice):
    '''
    Replicate metadata from local to cozy with a one-shot replication
    '''
    (username, password) = _get_credentials()
    source = 'http://%s:%s@localhost:5984/%s' % (username, password, database)
    url = url.split('/')
    target = "https://%s:%s@%s/cozy" % (device, pwdDevice, url[2])
    return SERVER.replicate(source, target,
                            filter="%s/filterDocType" % idDevice)


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


def recover_progression_binary(database):
    '''
    Recover progression of binaries download
    '''
    db = SERVER[database]
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
    db["_design/%s" % docType.lower()] = {
        "views": {
            "all": {
                "map": """function (doc) {
                              if (doc.docType === \"%s\") {
                                  emit(doc._id, doc)
                              }
                           }""" % docType
            },
            "byFolder": {
                "map": """function (doc) {
                              if (doc.docType === \"%s\") {
                                  emit(doc.path, doc)
                              }
                          }""" % docType
            },
            "byFullPath": {
                "map": """function (doc) {
                              if (doc.docType === \"%s\") {
                                  emit(doc.path + '/' + doc.name, doc)
                              }
                          }""" % docType
            }
        }
    }


def init_database(database):
    '''
    Initialize database:
        * Create database
        * Initialize folder, file, binary and device views
    '''
    # Create database
    try:
        db = SERVER.create(database)
        print 'Database created'
    except PreconditionFailed:
        db = SERVER[database]
        print 'Database already exists'

    try:
        add_view('Folder', db)
        print 'Folder design document created'
    except ResourceConflict:
        print 'Folder design document already exists'

    try:
        add_view('File', db)
        print 'File design document created'
    except ResourceConflict:
        print 'File design document already exists'

    try:
        db["_design/device"] = {
            "views": {
                "all": {
                    "map": """function (doc) {
                                  if (doc.docType === \"Device\") {
                                      emit(doc.login, doc)
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
        print 'Device design document created'
    except ResourceConflict:
        print 'Device design document already exists'

    try:
        db["_design/binary"] = {
            "views": {
                "all": {
                    "map": """function (doc) {
                                  if (doc.docType === \"Binary\") {
                                      emit(doc._id, doc)
                                  }
                               }"""
                }
            }
        }
        print 'Binary design document created'
    except ResourceConflict:
        print 'Binary design document already exists'


def init_device(database, url, pwdDevice, idDevice):
    '''
    Initialize device
        url {string}: cozy url
        pwdDevice {string}: device password
        idDevice {Number}: device id
    '''
    db = SERVER[database]
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
            filter2 = """function(doc, req) {
                    if ("""
            for docType in device["configuration"]:
                filter = filter + "(doc.docType &&"
                filter = filter + "doc.docType === \"%s\") ||" % docType
                filter2 = filter2 + "(doc.docType &&"
                filter2 = filter2 + "doc.docType === \"%s\") ||" % docType
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
            try:
                db.save(doc)
            except ResourceConflict:
                print 'Device filter document already exists'
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
