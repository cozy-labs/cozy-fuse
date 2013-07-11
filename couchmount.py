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
from time import time
try:
    import simplejson as json
except ImportError:
    import json # Python 2.6
from urllib import quote, unquote

fuse.fuse_python_api = (0, 2)

COUCHFS_DIRECTORY_PLACEHOLDER = u'.couchfs-directory-placeholder'

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

class CouchFSDocument(fuse.Fuse):
    def __init__(self, mountpoint, uri=None, *args, **kwargs):
        fuse.Fuse.__init__(self, *args, **kwargs)
        db_uri = uri
        self.db = Database(db_uri)
        #self.db["_design/file"] = {"views": {"all": {"map": "function (doc) {\n    emit(doc.id, doc) \n}"}}}

    def get_dirs(self):
        """
        Get directories
        """
        dirs = {}
        for res in self.db.view("file/all"):
            att = res.value["slug"]
            parents = [u'']
            for name in att.split('/'):
                filenames = dirs.setdefault(u'/'.join(parents[1:]), set())
                if name != COUCHFS_DIRECTORY_PLACEHOLDER:
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
            if path == '' or path in self.get_dirs().keys():
                st.st_mode = stat.S_IFDIR | 0775
                st.st_nlink = 2
            else:
                exist = "false"
                for res in self.db.view("file/all"):
                    if res.value["slug"] == path:
                        exist = "true"
                        att = self.db[res.id].get('_attachments', {})
                        data = att[path]
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
            #data = self.db.get_attachment(self.db[path], path.split('/')[-1])
            #att = self.db[path].get('_attachments', {})
            #data = att[path.split('/')[-1]]
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
        #accmode = os.O_RDONLY | os.O_WRONLY | os.O_RDWR
        #if (flags & accmode) != os.O_RDONLY:
        #    return -errno.EACCES

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
                if res.value["slug"] == path:
                    data = self.db.get_attachment(res.id, path)
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
                if res.value["slug"] == path:
                    data = self.db.get_attachment(self.db[res.id], path)
                    if data == None:
                        self.db.put_attachment(self.db[res.id], buf, filename=path)
                    else:
                        contain = data.read()
                        contain = contain[0:offset] + buf + contain[offset+len(buf):]
                        self.db.put_attachment(self.db[res.id], contain, filename=path)
                    return len(buf)
        except (KeyError, ResourceNotFound):
            pass
        return -errno.ENOENT

    def mknod(self, path, mode, dev):
        """
        Create special/ordinary file
            path {string}: file path
            mode {string}: file permissions
            dev: if the file type is S_IFCHR or S_IFBLK, dev specifies the major
                 and minor numbers of the newly created device special file
        """
        path = _normalize_path(path)
        id_doc = self.db.create({"name": path, "slug":path})
        self.db.put_attachment(self.db[id_doc], '', filename=path)

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
            if res.value["slug"] == path:
                self.db.delete(self.db[res.id])
                if filename != COUCHFS_DIRECTORY_PLACEHOLDER and len(self.get_dirs().get(dirname, [])) == 0:
                    print "putting to:", u'%s/%s' % (dirname, COUCHFS_DIRECTORY_PLACEHOLDER)
                    self.db.put_attachment(self.db[res.id], u'', filename=u'%s/%s' % (dirname, COUCHFS_DIRECTORY_PLACEHOLDER))

    def truncate(self, path, size):
        """
        Chnage size of a file
            path {string}: file path
            size {integer}: new file size
        """
        for res in self.db.view("file/all"):
            if res.value["slug"] == path:
                f = open(path)
                path = _normalize_path(path)
                self.db.put_attachment(self.db[res.id], f, filename=path)
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
        path = _normalize_path(path)
        name = '%s/%s' % (path, COUCHFS_DIRECTORY_PLACEHOLDER)
        id_doc = self.db.create({"name": name, "slug":name})
        self.db.put_attachment(self.db[id_doc], '', filename=u'%s/%s' % (path, COUCHFS_DIRECTORY_PLACEHOLDER))
        return 0

    def rmdir(self, path):
        """
        Remove directory
            path {string}: diretory path
        """
        path = _normalize_path(path)
        name = '%s/%s' % (path, COUCHFS_DIRECTORY_PLACEHOLDER)
        for res in self.db.view("file/all"):
            if res.value["slug"] == name:
                self.db.delete(self.db[res.id])
                return 0

    def rename(self, pathfrom, pathto):
        """
        Rename file
            pathfrom {string}: old path
            pathto {string}: new path
        """
        pathfrom, pathto = _normalize_path(pathfrom), _normalize_path(pathto)
        for res in self.db.view("file/all"):
            if res.value["slug"] == pathfrom:
                data = self.db.get_attachment(res.id, pathfrom)
                self.db.delete(self.db[res.id])
                id_doc = self.db.create({"name": pathto, "slug":pathto})
                self.db.put_attachment(self.db[id_doc], data, filename=pathto)
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
    if len(args) not in (2, 3):
        print "CouchDB FUSE Connector: Allows you to browse the _attachments of"
        print " any CouchDB document on your own filesystem!"
        print
        print "Usage: python couchmount.py [-d] <http://hostname:port/db> <mount-point>"
        sys.exit(-1)

    if len(args) == 2:
        fs = CouchFSDocument(args[1], args[0])
    elif len(args) == 3:
        fs = CouchFSDocument(args[2], args[1])

    fs.parse(errex=1)
    fs.main()

if __name__ == '__main__':
    main()
