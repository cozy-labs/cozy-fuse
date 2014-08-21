import unittest
import os
from couchdb import Database, Document, ResourceNotFound, Server
from subprocess import check_output
from couchdb.client import Row, ViewResults
import sys
sys.path.insert(0, '..')

import couchmount
import string
import random
def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))


class test_couch_fuse(unittest.TestCase):

    def _test_initialisation(self):
        print "Test initialisation ->"
        os.system("python ../couchmount.py http://localhost:5984/test_couch_fuse " + self.directory)
        stdout = check_output(['ls', self.directory], shell=False)
        files = stdout.split('\n')
        assert files[0] == 'file1.txt'
        assert files[1] == 'file2.txt'
        assert files[2] == ''
        print "OK"

    def _test_read_file(self, filename):
        print "Test read file ->"
    	stdout = check_output(['cat', self.directory + '/' + filename], shell=False)
        assert stdout == "File1 :"
        print "OK"

    def _test_add_empty_file(self, filename):
        print "Test add empty file ->"
    	os.system("touch " + self.directory + '/' + filename)
        exist = "false"
        for res in self.db.view("file/all"):
            if res.value["slug"] == filename:
                exist = "true"
        assert exist == "true"
        print "OK"

    def _test_modify_file(self, filename):
        print "Test modify file ->"
    	os.system("echo 'changes' >> " + self.directory + '/' + filename)
        exist = "false"
        for res in self.db.view("file/all"):
            if res.value["slug"] == filename:
                exist = "true"
                att = self.db.get_attachment(res.id, filename)
                content = att.read()
                assert content == "changes\n"
        assert exist == "true"
        print "OK"

    def _test_create_directory(self, directoryname):
        print "Test create directory ->"
        os.system("mkdir " + self.directory + '/' + directoryname)
        exist = "false"
        for res in self.db.view("file/all"):
            if res.value["slug"] == directoryname + "/.couchfs-directory-placeholder":
                exist = "true"
        assert exist == "true"
        print "OK"

    def _test_copy_file(self):
        print "Test copy file ->"
        os.system("cp " + "file_test.txt " + self.directory)
        exist = "false"
        for res in self.db.view("file/all"):
            if res.value["slug"] == "file_test.txt":
                exist = "true"
                att = self.db.get_attachment(res.id, "file_test.txt")
                content = att.read()
                assert content == "success_test\n"
        assert exist == "true"
        print "OK"

    def _test_remove_file_fs(self, filename):
        print "Test remove file in file system->"
        os.system("rm " + self.directory + '/' + filename)
        exist = "false"
        for res in self.db.view("file/all"):
            if res.value["slug"] == filename:
                exist = "true"
        assert exist == "false"
        print "OK"

    def _test_remove_file_db(self, filename):
        print "Test remove file in database->"
        exist = "false"
        for res in self.db.view("file/all"):
            if res.value["slug"] == filename:
                exist = "true"
                self.db.delete(self.db[res.id])
        assert exist == "true"
        stdout = check_output(['ls', self.directory], shell=False)
        files = stdout.split('\n')
        assert files[0] == 'file3.txt'
        assert files[1] == 'file_test.txt'
        assert files[2] == 'foo'
        assert files[3] == ''
        print "OK"

    def _test_add_file_db(self, filename):
        print "Test remove file in database->"
        doc_id = self.db.create({"name": filename, "slug": filename})
        self.db.put_attachment(self.db[doc_id], "new file", filename=filename)
        stdout = check_output(['cat', self.directory + '/' + filename], shell=False)
        assert stdout == "new file"
        print "OK"


def buildup_test(self=test_couch_fuse):
    # Initialize database
    server = Server()
    del server['test_couch_fuse']
    db = server.create('test_couch_fuse')
    self.db = db
    self.db["_design/file"] = {"views": {"all": {"map": "function (doc) {\n    emit(doc.id, doc) \n}"}}}

    # Add directory to test fuse
    self.directory = id_generator()
    os.system("mkdir " + self.directory)
    print "directory : %s" %self.directory

    # Add files in database
    doc1 = {"name": "file1.txt", "slug": "file1.txt"}
    doc_id = self.db.create(doc1)
    self.db.put_attachment(self.db[doc_id], "File1 :", filename="file1.txt")

    doc2 = {"name": "file2.txt", "slug": "file2.txt"}
    doc_id = self.db.create(doc2)
    self.db.put_attachment(self.db[doc_id], "File2 :", filename="file2.txt")

    # Run tests
    mname = 'test_Initialisation'
    def doTest(self):
        self._test_initialisation()
        self._test_read_file("file1.txt")
        self._test_add_empty_file("file3.txt")
        self._test_modify_file("file3.txt")
        self._test_create_directory("foo")
        self._test_add_empty_file("foo/test.txt")
        self._test_copy_file()
        self._test_remove_file_fs("file1.txt")
        self._test_remove_file_db("file2.txt")
        self._test_add_file_db("file_db.txt")
    setattr(self, mname, doTest)


if __name__ == '__main__':
	buildup_test();
	unittest.main()