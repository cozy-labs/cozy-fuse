import json
import requests
import logging
import time

import dbutils
import local_config

from couchdb import Server, http

logger = logging.getLogger(__name__)
local_config.configure_logger(logger)


def replicate(database, url, device, device_password, device_id,
              db_login, db_password,
              to_local=False, continuous=True, deleted=True, seq=None,
              ids=None):
    '''
    Run a replication from a CouchDB database to a remote Cozy instance.

    Args:

    * *database*: Name of the local datbase.
    * *url*: Url of the remote Cozy.
    * *device*: name of the current device (that should be regitered to the
      remote Cozy).
    * *device_password*: password of the current device to connect to the
      Remote Cozy.
    * *device_id*: ID of the device.
    * *db_login*:
    * *db_password*:

    Optionl args:

    * *to_local*: if True, data go from remote Cozy to local Couch.
    * *continuous*: if False, it's a single shot replication.
    * *deleted*: if false deleted documents are not replicated.
    * *seq*: sequence number from where to start the replication.
    * *ids*: Document ids to replicate.
    '''
    url = url.split('/')
    local = 'http://%s:%s@localhost:5984/%s' % \
            (db_login, db_password, database)
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

    if seq is None and ids is None:
        server.replicate(source, target, continuous=continuous,
                         filter=filter_name)
    elif seq is None:
        server.replicate(source, target, continuous=continuous, ids=ids)
    else:
        server.replicate(source, target, continuous=continuous,
                         filter=filter_name, since_seq=seq)

    if continuous and to_local:
        logger.info(
            '[Replication] Continous replication to local database started.')
    elif continuous and not to_local:
        logger.info(
            '[Replication] Continous replication to remote Cozy started.')
    elif not continuous and to_local:
        logger.info(
            '[Replication] One shot replication to local database started.')
    elif not continuous and not to_local:
        logger.info(
            '[Replication] One shot replication to remote Cozy started.')


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
        device = dbutils.get_device(self.db_name)
        self.urlCozy = device['url']
        self.loginCozy = device['login']
        self.passwordCozy = device['password']

        # Initialize sequence number to avoid full replication
        # every time.
        if 'seq' not in device:
            device['seq'] = 0
        new_seq = device['seq']

        # We create an infinite loop which will get file changes
        # every 10 seconds, and fetch related binaries if needed.
        while True:
            changes = self.db.changes(since=device['seq'],
                                      filter='file/all')

            binary_ids = []

            # Iterate over changes
            for line in changes['results']:

                # Save last sequence number
                new_seq = line['seq']

                try:
                    # Find related binary and add its ID to the list
                    # of files to replicate.
                    doc = self.db[line['id']]
                    if self._is_new(line):
                        logger.info("Creating file %s..." % doc['name'])
                    else:
                        logger.info("Updating file %s..." % doc['name'])
                    if 'binary' in doc:
                        binary_ids.append(doc['binary']['file']['id'])

                except http.ResourceNotFound:
                    if self._is_deleted(line):
                        logger.info("Deleting file %s..." % line['id'])
                        #TODO: Find document's attachments for previous
                        # revisions.
                        continue

            # Replicate related binaries
            if len(binary_ids) > 0:
                try:
                    self._replicate_to_local(binary_ids)
                except http.ResourceConflict:
                    #TODO: Handle comparison
                    pass
                except:
                    logging.exception(
                        'An error occured while replicating doc %s'
                        % line['id']
                    )

            # Save last sequence number along with the device
            if new_seq != device['seq']:
                device = dbutils.get_device(self.db_name)
                device['seq'] = new_seq
                self.db.save(device)

            # Wait until further potential changes
            time.sleep(10)

    def _is_new(self, line):
        '''
        Document is considered as new if its revision starts by "1-"
        '''
        return line['changes'][0]['rev'][0:2] == "1-"

    def _is_deleted(self, line):
        '''
        Document is considered as deleted if deleted key has for value true.
        '''
        return 'deleted' in line and line['deleted'] and \
               line['deleted'] is True

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
