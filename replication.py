import sys
from couchdb import Database, Document, ResourceNotFound, Server
from couchdb.client import Row, ViewResults
import time
database = "cozy-files"


def _replicate_to_local(self, ids):
    target = 'http://%s:%s@localhost:5984/%s' % (self.username, self.password, database)
    url = self.urlCozy.split('/')
    source = "https://%s:%s@%s/cozy" % (self.loginCozy, self.passwordCozy, url[2])
    self.rep = self.server.replicate(source, target, doc_ids=ids)

def _deleteFile(line, self):
    try:
        # Remove binary if a file has been deleted
        if line['deleted'] and line['deleted'] is True:
            try:
                binary = self.ids[line['doc']['_id']][0]
                if self.db[binary]:
                    self.db.delete(self.db[binary])
                    _replicate_to_local(self, [binary])
                return True
            except (Exception):
                return True
    except (KeyError):
        return False

def _addFile(line, self):  
    try:
        # Add binary if File has been added
        if line['doc']['_rev'][0] is "1" and line['doc']['_rev'][1] is '-':
            id_doc = line['doc']['_id']
            doc = self.db[id_doc]
            if doc['docType'] == 'File':
                try:
                    if self.ids[id_doc]:
                        return True
                except (KeyError):
                    self.ids[id_doc] = ["", ""]
                    return True
        else:
            return False
    except (Exception):
        return True

def _updateFile(line, self): 
    try: 
        id_doc = line['doc']['_id']
        doc = self.db[id_doc]
        if doc['docType'] == 'File':
            binary = doc['binary']['file']
            if binary['rev'] != self.ids[id_doc][1]:
                self.ids[id_doc] = [binary['id'], binary['rev']]
                _replicate_to_local(self, [binary['id']])
                return True
    except (Exception):
        return False   

def _isDevice(line):
    try:
        if line['doc']['docType'] != "Device":                    
            return False
        else:
            return True
    except (Exception):
        return False

class Replication():
    def __init__(self, *args, **kwargs): 
    	self.server = Server('http://localhost:5984/')
        # Read file
        f = open('/etc/cozy-files/couchdb.login')
        lines = f.readlines()
        f.close()
        self.username = lines[0].strip()
        self.password = lines[1].strip()
        # Add credentials
        self.server.resource.credentials = (self.username, self.password)
        self.db = self.server[database]
    	self.changeFile()

    def changeFile(self):
        for res in self.db.view("device/all"):
            device = res.value
            self.urlCozy = device['url']
            self.passwordCozy = device['password']
            self.loginCozy = device['login']
            files = self.db.view("file/all")
            self.ids = {}
            for res in files:
                self.ids[res.id] = ["", ""]
            changes = self.db.changes(feed='continuous', heartbeat='1000', since=device['change'], include_docs=True)
            for line in changes:
                if not _isDevice(line):
                    device['change'] = line['seq'] + 1
                    self.db.save(device)
                    id_doc = line['doc']
                    if not _deleteFile(line, self):
                        if not _addFile(line, self):  
                            _updateFile(line, self)     

def _init():
    try:
        Replication()
    except Exception, e: 
        time.sleep(5)
        _init()

def main():
    args = sys.argv[1:]
    _init()   

if __name__ == '__main__':
    main()
