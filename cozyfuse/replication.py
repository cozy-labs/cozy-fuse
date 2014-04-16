import dbutils

from couchdb import Server
from couchdb.http import PreconditionFailed, ResourceConflict

try:
    import simplejson as json
except ImportError:
    import json  # Python 2.6
import requests
import os

SERVER = Server('http://localhost:5984/')


def replicate(database, url, device, device_password, device_id,
              db_login, db_password,
              to_local=False, continuous=True, deleted=True, seq=None):
    '''
    Run a replication from a CouchDB database to a remote Cozy instance.

    Args:

    * *to_local*: if True, data go from remote Cozy to local Couch.
    * *continuous*: if False, it's a single shot replication.
    * *deleted*: if false deleted documents are not replicated.
    * *seq*: sequence number from where to start the replication.
    '''
    url = url.split('/')
    local = 'http://%s:%s@localhost:5984/%s' % (db_login, db_password, database)
    remote = "https://%s:%s@%s/cozy" % (device, device_password, url[2])

    if to_local:
        target = local
        source = remote
    else:
        target = remote
        source = local

    if deleted:
        filter_name = "%s/filter" % device_id
    else:
        filter_name = "%s/filterDocType" % device_id

    if seq is None:
        SERVER.replicate(source, target, continuous=continuous,
                         filter=filter_name)
    else:
        SERVER.replicate(source, target, continuous=continuous,
                         filter=filter_name, since_seq=seq)


def recover_progression():
    '''
    Recover progression of metadata replication
    '''
    url = 'http://localhost:5984/_active_tasks'
    response = requests.get(url)
    replications = json.loads(response.content)
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
        print '[DB] Database %s created' % database
    except PreconditionFailed:
        db = SERVER[database]
        print '[DB] Database %s already exists.' % database

    try:
        add_view('Folder', db)
        print '[DB] Folder design document created'
    except ResourceConflict:
        print '[DB] Folder design document already exists'

    try:
        add_view('File', db)
        print '[DB] File design document created'
    except ResourceConflict:
        print '[DB] File design document already exists'

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
        print '[DB] Device design document created'
    except ResourceConflict:
        print '[DB] Device design document already exists'

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
        print '[DB] Binary design document created'
    except ResourceConflict:
        print '[DB] Binary design document already exists'


def init_device(database, url, pwdDevice, idDevice):
    '''
    Initialize device
        url {string}: cozy url
        pwdDevice {string}: device password
        idDevice {Number}: device id
    '''
    db = dbutils.get_db(database)
    res = db.view("device/all")

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
            print '[DB] Device filter document already exists'
    return False
