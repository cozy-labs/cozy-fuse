#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 Jason Davies
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.


from couchdb import Database, Document, ResourceNotFound, Server
from couchdb.client import Row, ViewResults
import errno
import fuse
import os
import stat
import sys
import time
import base64
import replication
#try:
#    import _thread # Python 3
#except ImportError:
#    import thread
#from threading import Thread
from urllib import quote, unquote    

fuse.fuse_python_api = (0, 2)
database = "cozy-files"


class CouchStat(fuse.Stat):
    def __init__(self):
        self.st_mode = 0
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 0
        self.st_uid = os.getuid()
        self.st_gid = os.getgid()
        self.st_size = 4096
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0

def _normalize_path(path):
    return u'/'.join([part for part in path.split(u'/') if part != u''])

def _recover_path(db): 
    res = db.view("device/all")
    if not res:
        time.sleep(5)
        return _recover_path(db)
    else:
        for device in res:
            if not device.value["folder"]:
                time.sleep(5)
                return _recover_path(db)
            else:
                return device.value['folder']

def _replicate_from_local(self, ids):
    source = 'http://%s:%s@localhost:5984/%s' % (self.username, self.password, database)
    url = self.urlCozy.split('/')
    target = "https://%s:%s@%s/cozy" % (self.loginCozy, self.passwordCozy, url[2])
    self.rep = self.server.replicate(source, target, doc_ids=ids)  


class CouchFSDocument(fuse.Fuse):
    def __init__(self, mountpoint, uri=None, *args, **kwargs):
        fuse.Fuse.__init__(self, *args, **kwargs)        
        self.fuse_args.mountpoint = mountpoint
        self.fuse_args.add('allow_other')
        db_uri = uri
        self.server = Server('http://localhost:5984/')
        # Add local credentials
        f = open('/etc/cozy-files/couchdb.login')
        lines = f.readlines()
        f.close()
        self.username = lines[0].strip()
        self.password = lines[1].strip()
        self.server.resource.credentials = (self.username, self.password)
        self.db = self.server[database]
        self.currentFile = ""
        res = self.db.view("device/all")
        for device in res:
            # Add cozy credentials
            self.urlCozy = device.value['url']
            self.passwordCozy = device.value['password']
            self.loginCozy = device.value['login']
       
    def get_dirs(self):
        """
        Get directories
        """
        dirs={}
        for res in self.db.view("folder/all"):
            att = res.value["path"] + '/' + res.value["name"]
            if len(att) != 0:
                att = att[1:]
            parents = [u'']
            for name in att.split('/'):
                if name != '':
                    filenames = dirs.setdefault(u'/'.join(parents[1:]), set())
                    filenames.add(name)
                    parents.append(name)
                    dirs.setdefault(u''+ att, set())
        for res in self.db.view("file/all"):
            att = res.value["path"] + '/' + res.value["name"]
            parents = [u'']
            for name in att.split('/'):
                if name != '':
                    filenames = dirs.setdefault(u'/'.join(parents[1:]), set())
                    filenames.add(name)
                    parents.append(name)
        return dirs

    def readdir(self, path, offset):
        """
        Read directory
            path {string}: directory path
            offset {integer}: used if buffer is full
        """
        path = _normalize_path(path)
        for r in '.', '..':
            yield fuse.Direntry(r)
        for name in self.get_dirs().get(path, []):
            yield fuse.Direntry(name.encode('utf-8'))

    def getattr(self, path):
        """
        Get Attr :
            path {string}: file path
        """
        exist = False
        st = CouchStat()
        try:
            if path is "/":
                exist = True
                st.st_mode = stat.S_IFDIR | 0775
                st.st_nlink = 2                
            for res in self.db.view("folder/byFullPath", key=path):
                exist = True
                st.st_mode = stat.S_IFDIR | 0775
                st.st_nlink = 2
            if not exist:
                for res in self.db.view("file/byFullPath", key=path):
                    res = res.value
                    exist = True
                    bin = res["binary"]["file"]["id"]
                    att = self.db[bin].get('_attachments', {})
                    data = att["file"]
                    st.st_mode = stat.S_IFREG | 0664
                    st.st_nlink = 1
                    st.st_size = data['length']
                if not exist:
                    return -errno.ENOENT
            return st     
        except (KeyError, ResourceNotFound):
            return -errno.ENOENT

    def open(self, path, flags):
        """
        Open file
            path {string}: file path
            flags {string}: opening mode
        """
        path = _normalize_path(path)
        try:
            parts = path.rsplit(u'/', 1)
            if len(parts) == 1:
                dirname, filename = u'', parts[0]
            else:
                dirname, filename = parts
            if filename in self.get_dirs()[dirname]:
                return 0
            return -errno.ENOENT
        except (KeyError, ResourceNotFound):
            return -errno.ENOENT

    def read(self, path, size, offset):
        """
        Read file
            path {string}: file path
            size {integer}: size of file part to read
            offset {integer}: beginning of file part to read
        """
        try:
            for res in self.db.view("file/byFullPath", key=path):
                res = res.value
                bin = res["binary"]["file"]["id"]
                data = self.db.get_attachment(bin, "file")
                if data == None:
                    return ''
                else:
                    contain = data.read()
                    slen = len(contain)
                    if offset < slen:
                        if offset + size > slen:
                            size = slen - offset
                        buf = contain[offset:offset+size]
                    else:
                        buf = ''
                    return buf
        except (KeyError, ResourceNotFound):
            pass
        return -errno.ENOENT

    def write(self, path, buf, offset):
        """
        Write data in file
            path {string}: file path
            buf {buffer}: data to write
            offset {integer}: beginning of file part to read
        """
        try:
            for res in self.db.view("file/byFullPath", key=path): 
                self.currentFile = self.currentFile + buf
                return len(buf)
        except (KeyError, ResourceNotFound):
            pass
        return -errno.ENOENT
    
    def release(self, path, fuse_file_info):
        """
        Release an open file
            path {string}: file path
            fuse_file_info {struct}: information about open file
            
            Release is called when there are no more references 
            to an open file: all file descriptors are closed and 
            all memory mappings are unmapped.
        """
        if self.currentFile != "": 
            for res in self.db.view("file/byFullPath", key=path):
                res = res.value
                bin = res["binary"]["file"]["id"]
                self.db.put_attachment(self.db[bin], self.currentFile, filename="file")
                _replicate_from_local(self, [bin])
            self.currentFile = ""

    def mknod(self, path, mode, dev):
        """
        Create special/ordinary file
            path {string}: file path
            mode {string}: file permissions
            dev: if the file type is S_IFCHR or S_IFBLK, dev specifies the major
                 and minor numbers of the newly created device special file
        """
        partialPaths = path.split('/')
        name = partialPaths[len(partialPaths) -1]
        filePath = path[:-(len(name)+1)]
        newBin = {"docType": "Binary"}
        id_bin = self.db.create(newBin)
        self.db.put_attachment(self.db[id_bin], '', filename="file")
        rev = self.db[id_bin]["_rev"]
        newFile = {"name": name, "path": filePath, "binary":{"file": {"id": id_bin, "rev": rev}}, "docType": "File"}
        id_doc = self.db.create(newFile)
        _replicate_from_local(self, [id_bin])

    def unlink(self, path):
        """
        Remove file
            path {string}: file path
        """
        path = _normalize_path(path)
        parts = path.rsplit(u'/', 1)
        if len(parts) == 1:
            dirname, filename = u'', parts[0]
        else:
            dirname, filename = parts
        for res in self.db.view("file/byFullPath", key='/' + path):
            res = res.value
            bin = res["binary"]["file"]["id"]
            self.db.delete(self.db[bin])
            self.db.delete(self.db[res["_id"]])
            _replicate_from_local(self, [bin])

    def truncate(self, path, size):
        """
        Change size of a file
            path {string}: file path
            size {integer}: new file size
        """
        return 0

    def utime(self, path, times):
        """
        Change the access and/or modification times of a file
            path {string}: file path
            times: times of file
        """
        return 0


    def chmod ( self, path, mode ):
        return 0

    def chown ( self, path, uid, gid ):
        return 0

    def mkdir(self, path, mode):
        """
        Create directory
            path {string}: diretory path
            mode {string}: directory permissions
        """
        partialPaths = path.split('/')
        name = partialPaths[len(partialPaths) -1]
        folderPath = path[:-(len(name)+1)]
        id_doc = self.db.create({"name": name, "path": folderPath, "docType": "Folder"})
        return 0

    def rmdir(self, path):
        """
        Remove directory
            path {string}: diretory path
        """
        for res in self.db.view("folder/byFullPath", key=path):
            res = res.value
            self.db.delete(self.db[res['_id']])
            return 0

    def rename(self, pathfrom, pathto):
        """
        Rename file
            pathfrom {string}: old path
            pathto {string}: new path
        """
        for doc in self.db.view("file/byFullPath", key=pathfrom):
            doc = doc.value
            partialPaths = pathto.split('/')
            name = partialPaths[len(partialPaths) -1]
            filePath = pathto[:-(len(name)+1)]
            doc.update({"name": name, "path": filePath})
            self.db.save(doc) 
        for doc in self.db.view("folder/byFullPath", key=pathfrom):
            doc = doc.value
            partialPaths = pathto.split('/')
            name = partialPaths[len(partialPaths) -1]
            filePath = pathto[:-(len(name)+1)]
            doc.update({"name": name, "path": filePath})
            # Rename all subfiles
            for res in self.db.view("file/byFolder", key=pathfrom):
                pathfrom = res.value['path'] + '/' + res.value['name']
                pathto = filePath + '/' + name + '/' + res.value['name']
                self.rename(pathfrom, pathto)
            for res in self.db.view("folder/byFolder", key=pathfrom):
                pathfrom = res.value['path'] + '/' + res.value['name']
                pathto = filePath + '/' + name + '/' + res.value['name']
                self.rename(pathfrom, pathto)
            self.db.save(doc)
            return 0

    """def chown(self, path, user, group):
        print("chown %s %s %s" % (path,user,group))
        return os.chown(self.p(path), user, group)

    def chmod(self, path, mode):
        print("chmod %s %s" % (path,mode))
        return os.chmod(self.p(path), mode)
    """


    def fsync(self, path, isfsyncfile):
        """
        Synchronize file contents
            path {string}: file path
            isfsyncfile {boolean}: display if files are synchronized
        """

        return 0

    def statfs(self):
        """
        Should return a tuple with the following 6 elements:
            - blocksize - size of file blocks, in bytes
            - totalblocks - total number of blocks in the filesystem
            - freeblocks - number of free blocks
            - availblocks - number of blocks available to non-superuser
            - totalfiles - total number of file inodes
            - freefiles - nunber of free file inodes

        Feel free to set any of the above values to 0, which tells
        the kernel that the info is not available.
        """
        st = fuse.StatVfs()
        block_size = 1024
        blocks = 1024 * 1024
        blocks_free = blocks
        blocks_avail = blocks_free
        files = 0
        files_free = 0
        st.f_bsize = block_size
        st.f_frsize = block_size
        st.f_blocks = blocks
        st.f_bfree = blocks_free
        st.f_bavail = blocks_avail
        st.f_files = files
        st.f_ffree = files_free
        return st


def _init():
    try:
        server = Server('http://localhost:5984/')
        # Read file
        f = open('/etc/cozy-files/couchdb.login')
        lines = f.readlines()
        f.close()
        username = lines[0].strip()
        password = lines[1].strip()
        
        # Add credentials
        server.resource.credentials = (username, password)
        try:
            db = server[database]
        except Exception, e:
            db = server.create(database)
            # add user
        if '_design/device' not in db:
           db["_design/device"] = {"views": {"all": {"map": "function (doc) {\n" + 
                "    if (doc.docType === \"Device\") {\n        emit(doc.id, doc) \n    }\n}"}}} 
        folder = _recover_path(db)
        db = 'http://localhost:5984/%s' % database
        fs = CouchFSDocument(folder, db)
        #replication.Replication()
        fs.parse(errex=1)
        fs.main()
    except Exception, e:
        time.sleep(5)
        _init()

def main():
    args = sys.argv[1:]
    _init()   

if __name__ == '__main__':
    main()
