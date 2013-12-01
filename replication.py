import sys
import traceback

from couchdb import Server

DATABASE = "cozy-files"
CREDENTIALS_FILE_PATH = '/etc/cozy/cozy-files/couchdb.login'


class Replication():
    '''
    Class that allows to run replications on local database
    '''

    def __init__(self, *args, **kwargs):
        self.set_credentials()
        self.set_db_server()
        self.replicate_file_changes()

    def set_credentials(self):
        '''
        Get credentials from file located at *CREDENTIALS_FILE_PATH*.
        Credentials are sperated by a carriage return.
        '''
        credentials_file = open(CREDENTIALS_FILE_PATH)
        lines = credentials_file.readlines()
        credentials_file.close()
        self.username = lines[0].strip()
        self.password = lines[1].strip()

    def set_db_server(self):
        '''
        Configure CouchDB connectors (location + credentials).
        '''
        self.server = Server('http://localhost:5984/')
        self.server.resource.credentials = (self.username, self.password)
        self.db = self.server[DATABASE]

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
        return line['doc']['_rev'][0] is "1" and line['doc']['_rev'][1] is '-'

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

        except Exception, e:
            print 'An error occured while replicating creation for:'
            print 'doc %s' %line['doc']['_id']
            traceback.print_stack()

    def _delete_file(self, line):
        '''
        Remove binary document if a file has been deleted.
        '''
        try:
            id_doc = self.ids.get(line['doc']['_id'])
            if id_doc is not None :
                binary = self.ids[line['doc']['_id']][0]
                if self.db[binary]:
                    self.db.delete(self.db[binary])
                    self._replicate_to_local([binary])
        except Exception, e:
            print 'An error occured while replicating deletion for:'
            print 'doc %s' %line['doc']['_id']
            traceback.print_stack()

    def _update_file(self, line):
        '''
        If a file document has been modified the linked binary is replicated.
        '''
        try:
            id_doc = line['doc']['_id']
            doc = self.db[id_doc]
            if doc['docType'] == 'File':
                binary = doc['binary']['file']
                if binary['rev'] != self.ids[id_doc][1]:
                    self.ids[id_doc] = [binary['id'], binary['rev']]
                    self._replicate_to_local([binary['id']])
        except Exception, e:
            print 'An error occured while replicating update for:'
            print 'doc %s' %line['doc']['_id']
            traceback.print_stack()

    def _replicate_to_local(self, ids):
        '''
        Replicate given documents from Cozy database to local database.
        '''
        url = self.urlCozy.split('/')
        target = 'http://%s:%s@localhost:5984/%s' % (self.username,
                                                     self.password,
                                                     DATABASE)
        source = "https://%s:%s@%s/cozy" % (self.loginCozy,
                                            self.passwordCozy,
                                            url[2])
        self.rep = self.server.replicate(source, target, doc_ids=ids)


def main():
    '''
    Start replication when file is executed.
    '''
    try:
        Replication()
    except Exception:
        print('Something wrong occured while creating replicator')
        traceback.print_exc(file=sys.stdout)


if __name__ == '__main__':
    main()
