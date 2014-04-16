import dbutils

from couchdb import Server

import json
import requests


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
    server = Server('http://localhost:5984/')

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
        server.replicate(source, target, continuous=continuous,
                         filter=filter_name)
    else:
        server.replicate(source, target, continuous=continuous,
                         filter=filter_name, since_seq=seq)


def get_progression():
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


def get_binary_progression(database):
    '''
    Recover progression of binary downloads.
    '''
    db = dbutils.get_db(database)
    files = db.view("file/all")
    binaries = db.view('binary/all')
    if len(files) is 0:
        return 1
    else:
        return len(binaries)/float(len(files))
