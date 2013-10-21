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
try:
    import simplejson as json
except ImportError:
    import json # Python 2.6
from urllib import quote, unquote    

fuse.fuse_python_api = (0, 2)


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
    res = db.view("remote/all")
    if not res:
        time.sleep(1)
        return _recover_path(db)
    else:
        for res in db.view("remote/all"):
            if not res.value["folder"]:
                time.sleep(1)
                return _recover_path(db)
            else:
                return res.value['folder']




class CouchFSDocument(fuse.Fuse):
    def __init__(self, mountpoint, uri=None, *args, **kwargs):
        fuse.Fuse.__init__(self, *args, **kwargs)        
        self.fuse_args.mountpoint = mountpoint
        db_uri = uri
        self.db = Database(db_uri)
        self.currentFile = ""

       
    def get_dirs(self):
        """
        Get directories
        """
        dirs = {}
        for res in self.db.view("folder/all"):
            att = res.value["slug"]
            path = att[1:]
            parents = [u'']
            for name in att.split('/'):
                if name != '':
                    filenames = dirs.setdefault(u'/'.join(parents[1:]), set())
                    filenames.add(name)
                    parents.append(name)
                    dirs.setdefault(u''+path, set())
        for res in self.db.view("file/all"):
            att = res.value["slug"]
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
        path = _normalize_path(path)
        try:
            st = CouchStat()
            if path == '' or path in self.get_dirs().keys() :
                st.st_mode = stat.S_IFDIR | 0775
                st.st_nlink = 2
            else:
                exist = "false"
                for res in self.db.view("file/all"):
                    if res.value["slug"] == '/' + path:
                        exist = "true"
                        att = self.db[res.id].get('_attachments', {})
                        data = att["thumb"]
                        st.st_mode = stat.S_IFREG | 0664
                        st.st_nlink = 1
                        st.st_size = data['length']
                if exist == "false":
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
        path = _normalize_path(path)
        try:
            for res in self.db.view("file/all"):
                if res.value["slug"] == '/' + path:
                    data = self.db.get_attachment(res.id, "thumb")
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
        path = _normalize_path(path)
        try:
            for res in self.db.view("file/all"):
                if res.value["slug"] == '/' + path:   
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
        print fuse_file_info
        if self.currentFile != "": 
            for res in self.db.view("file/all"):
                if res.value["slug"] == path:   
                    self.db.put_attachment(self.db[res.id], self.currentFile, filename="thumb")
            self.currentFile = ""

    def mknod(self, path, mode, dev):
        """
        Create special/ordinary file
            path {string}: file path
            mode {string}: file permissions
            dev: if the file type is S_IFCHR or S_IFBLK, dev specifies the major
                 and minor numbers of the newly created device special file
        """
        #path = _normalize_path(path)
        partialPaths = path.split('/')
        name = partialPaths[len(partialPaths) -1]
        filePath = path.replace('/' + name, '')
        newFile = {"name": name, "path": filePath, "slug":path, "docType": "File"}
        id_doc = self.db.create(newFile)
        self.db.put_attachment(self.db[id_doc], '', filename="thumb")

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
        for res in self.db.view("file/all"):
            if res.value["slug"] == '/' + path:
                self.db.delete(self.db[res.id])

    def truncate(self, path, size):
        """
        Change size of a file
            path {string}: file path
            size {integer}: new file size
        """
        for res in self.db.view("file/all"):
            if res.value["slug"] == path:
                f = open(path)
                path = _normalize_path(path)
                self.db.put_attachment(self.db[res.id], f, filename="thumb")
                f.close()
        return 0

    def utime(self, path, times):
        """
        Change the access and/or modification times of a file
            path {string}: file path
            times: times of file
        """

        return 0

    def mkdir(self, path, mode):
        """
        Create directory
            path {string}: diretory path
            mode {string}: directory permissions
        """
        #path = _normalize_path(path)
        partialPaths = path.split('/')
        name = partialPaths[len(partialPaths) -1]
        folderPath = path.replace('/' + name, '')
        id_doc = self.db.create({"name": name, "path": folderPath, "slug": path, "docType": "Folder"})
        return 0

    def rmdir(self, path):
        """
        Remove directory
            path {string}: diretory path
        """
        for res in self.db.view("folder/all"):
            if res.value["slug"] == path:
                self.db.delete(self.db[res.id])
                return 0

    def rename(self, pathfrom, pathto):
        """
        Rename file
            pathfrom {string}: old path
            pathto {string}: new path
        """
        for res in self.db.view("file/all"):
            if res.value["slug"] == pathfrom:
                doc = res.value
                partialPaths = pathto.split('/')
                name = partialPaths[len(partialPaths) -1]
                filePath = pathto.replace('/' + name, '')
                doc.update({"slug": pathto, "name": name, "path": filePath})
                self.db.save(doc)        
        for res in self.db.view("folder/all"):
            if res.value["slug"] == pathfrom:
                doc = res.value
                partialPaths = pathto.split('/')
                name = partialPaths[len(partialPaths) -1]
                filePath = pathto.replace('/' + name, '')
                doc.update({"slug": pathto, "name": name, "path": filePath})
                self.db.save(doc)
                return 0

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


def main():
    args = sys.argv[1:]
    if len(args) not in (0,1):
        print "CouchDB FUSE Connector: Allows you to browse the _attachments of"
        print " any CouchDB document on your own filesystem!"
        print
        print "Usage: python couchmount.py [-d]"
        print
        print "Unmount with : fusermount -u <mount-point>"
        sys.exit(-1)
    server = Server('http://localhost:5984/')
    try:
        db = server['cozy']
    except Exception, e:
        db = server.create('cozy')
    if '_design/remote' not in db:
       db["_design/remote"] = {"views": {"all": {"map": "function (doc) {\n    if (doc.docType === \"Remote\") {\n        emit(doc.id, doc) \n    }\n}"}}} 
    if '_design/file' not in db:
        db["_design/file"] = {"views": {"all": {"map": "function (doc) {\n    if (doc.docType === \"File\") {\n        emit(doc.id, doc) \n    }\n}"}}}
    if '_design/folder' not in db:
        db["_design/folder"] = {"views": {"all": {"map": "function (doc) {\n    if (doc.docType === \"Folder\") {\n        emit(doc.id, doc) \n    }\n}"}}}
    folder = _recover_path(db)
    fs = CouchFSDocument(folder, 'http://localhost:5984/cozy')
    fs.parse(errex=1)
    fs.main()

if __name__ == '__main__':
    main()
