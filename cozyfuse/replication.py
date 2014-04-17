import json
import requests
import logging

import dbutils
import local_config

from couchdb import Server


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



class BinaryReplication():
    '''
    Class that allows to run replications on local database
    '''

    def __init__(self, db_name, *args, **kwargs):
        '''
        Set database connetors on current instance.
        Run binary replication.
        '''
        (self.username, self.password) = \
            local_config.get_db_credentials(db_name)
        (self.db, self.server) = dbutils.get_db_and_server(db_name)
        self.db_name = db_name
        self.replicate_file_changes()

    def replicate_file_changes(self):
        '''
        Replicate all changes related to files and binaries to stored devices.
        '''
        for res in self.db.view("device/all"):
            device = res.value
            self.urlCozy = device['url']
            self.loginCozy = device['login']
            self.passwordCozy = device['password']

            self.ids = {}
            for res in self.db.view("file/all"):
                if 'binary' in res.value and 'file' in res.value['binary']:
                    id_binary = res.value['binary']['file']['id']
                    if id_binary in self.db:
                        binary = self.db[id_binary]
                        self.ids[res.id] = [id_binary, binary.rev]
                    else:
                        self.ids[res.id] = [id_binary, ""]

            changes = self.db.changes(feed='continuous',
                                      heartbeat='1000',
                                      since=device['change'],
                                      include_docs=True)

            for line in changes:
                if not self._is_device(line):
                    device['change'] = line['seq']
                    self.db.save(device)

                    if self._is_deleted(line):
                        self._delete_file(line)
                    elif self._is_new(line):
                        self._add_file(line)
                    else:
                        self._update_file(line)

    def _is_device(self, line):
        '''
        Return true if *line* is a document and its doctype is "Device".
        '''
        try:
            return str(line['doc']['docType']) == "Device"
        except:
            return False

    def _is_new(self, line):
        '''
        Document is considered as new if its revision starts by "1-"
        '''
        return line['doc']['_rev'][0:1] == "1-"

    def _is_deleted(self, line):
        '''
        Document is considered as deleted if deleted key has for value true.
        '''
        return 'deleted' in line and line['deleted'] and \
               line['deleted'] is True

    def _add_file(self, line):
        '''
        If line is a document of which document type is 'File', then the
        binary document linked to this document is replicated
        '''
        try:
            id_doc = line['doc']['_id']
            doc = self.db[id_doc]
            if 'docType' in doc:
                if doc['docType'] == 'File':
                    if 'binary' in doc:
                        binary = doc['binary']['file']
                        self.ids[id_doc] = [binary['id'], binary['rev']]
                        self._replicate_to_local([binary['id']])
                    elif not id_doc in self.ids:
                        self.ids[id_doc] = ["", ""]

        except Exception:
            logging.exception(
                'An error occured while replicating creation for:' \
                'doc %s' % line['doc']['_id']
            )


    def _delete_file(self, line):
        '''
        Remove binary document if a file has been deleted.
        '''
        try:
            id_doc = self.ids.get(line['doc']['_id'])
            if id_doc is not None:
                binary = self.ids[line['doc']['_id']][0]
                if self.db[binary]:
                    self.db.delete(self.db[binary])
                    self._replicate_to_local([binary])
        except Exception:
            logging.exception(
                'An error occured while replicating deletion for:'
                'doc %s' % line['doc']['_id']
            )

    def _update_file(self, line):
        '''
        If a file document has been modified the linked binary is replicated.
        '''
        try:
            id_doc = line['doc']['_id']
            doc = self.db[id_doc]
            if 'docType' in doc:
                if doc['docType'] == 'File':
                    binary = doc['binary']['file']
                    if binary['rev'] != self.ids[id_doc][1]:
                        self.ids[id_doc] = [binary['id'], binary['rev']]
                        self._replicate_to_local([binary['id']])

        except Exception:
            logging.exception(
                'An error occured while replicating update for:'
                'doc %s' % line['doc']['_id']
            )

    def _replicate_to_local(self, ids):
        '''
        Replicate given documents from Cozy database to local database.
        '''
        url = self.urlCozy.split('/')
        target = 'http://%s:%s@localhost:5984/%s' % (self.username,
                                                     self.password,
                                                     self.db_name)
        source = "https://%s:%s@%s/cozy" % (self.loginCozy,
                                            self.passwordCozy,
                                            url[2])
        self.rep = self.server.replicate(source, target, doc_ids=ids)
