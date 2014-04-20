#!/usr/bin/env python

# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 Jason Davies
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

import os
import errno
import fuse
import stat
import subprocess

import dbutils

from couchdb import ResourceNotFound

fuse.fuse_python_api = (0, 2)


class CouchStat(fuse.Stat):
    '''
    Default file descriptor.
    '''
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


class CouchFSDocument(fuse.Fuse):
    '''
    Fuse implementation behavior: handles synchronisation with database when a
    change occurs or when users want to access to his/her file system.
    '''

    def __init__(self, database, mountpoint, uri=None, *args, **kwargs):
        '''
        Configure file system, database and store remote Cozy informations.
        '''

        # Configure fuse
        fuse.Fuse.__init__(self, *args, **kwargs)
        self.fuse_args.mountpoint = mountpoint
        self.fuse_args.add('allow_other')
        self.currentFile = ""

        # Configure database
        self.database = database
        (self.db, self.server) = dbutils.get_db_and_server(database)

        # Configure Cozy
        device = dbutils.get_device(database)
        self.urlCozy = device['url']
        self.passwordCozy = device['password']
        self.loginCozy = device['login']

    def get_dirs(self):
        """
        Get directories
        """
        # TODO: cache result
        dirs = {}

        for folder in self.db.view("folder/all"):
            folder_path = os.path.join(folder.value["path"],
                                       folder.value["name"])
            if len(folder_path) != 0:
                folder_path = folder_path[1:]

            parents = [u'']
            for name in folder_path.split('/'):
                if name != '':
                    filenames = dirs.setdefault(u'/'.join(parents[1:]), set())
                    filenames.add(name)
                    parents.append(name)
                    dirs.setdefault(u'' + folder_path, set())

        for file_doc in self.db.view("file/all"):
            file_path = file_doc.value["path"] + '/' + file_doc.value["name"]
            parents = [u'']
            for name in file_path.split('/'):
                if name != '':
                    filenames = dirs.setdefault(u'/'.join(parents[1:]), set())
                    filenames.add(name)
                    parents.append(name)

        return dirs

    def readdir(self, path, offset):
        """
        Generator: list files for given path and yield each file result when
        it arrives.
        """
        path = _normalize_path(path)
        for directory in '.', '..':  # why ?
            yield fuse.Direntry(directory)
        for name in self.get_dirs().get(path, set()):
            yield fuse.Direntry(name.encode('utf-8'))

    def getattr(self, path):
        """
        Return file descriptor for given_path
        """
        exist = False
        st = CouchStat()
        try:

            # Path is root
            if path is "/":
                exist = True
                st.st_mode = stat.S_IFDIR | 0775
                st.st_nlink = 2

            # Folder exists in DB.
            for res in self.db.view("folder/byFullPath", key=path):
                exist = True
                st.st_mode = stat.S_IFDIR | 0775
                st.st_nlink = 2

            if not exist:
                # File exists in DB.
                for res in self.db.view("file/byFullPath", key=path):
                    exist = True
                    res = res.value

                    binary_id = res["binary"]["file"]["id"]
                    binary_attachment = \
                        self.db[binary_id].get('_attachments', {})
                    data = binary_attachment["file"]
                    st.st_mode = stat.S_IFREG | 0664
                    st.st_nlink = 1
                    st.st_size = data['length']

                # File does not exist.
                if not exist:
                    print 'File does not exist: %s' % path
                    return -errno.ENOENT

            return st

        except (KeyError, ResourceNotFound):
            print 'Something went wrong getting infos for %s' % path
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
            else:
                print 'Something went wrong while opening %s' % path
                return -errno.ENOENT

        except (KeyError, ResourceNotFound):
            print 'Something went wrong while opening %s' % path
            return -errno.ENOENT

    def read(self, path, size, offset):
        """
        Return content of file located at given path.
            path {string}: file path
            size {integer}: size of file part to read
            offset {integer}: beginning of file part to read
        """
        # TODO: do not load the file for each chunk.
        try:
            for res in self.db.view("file/byFullPath", key=path):
                res = res.value
                binary_id = res["binary"]["file"]["id"]
                binary_attachment = self.db.get_attachment(binary_id, "file")

                if binary_attachment is None:
                    return ''

                else:
                    content = binary_attachment.read()
                    content_length = len(content)

                    if offset < content_length:
                        if offset + size > content_length:
                            size = content_length - offset
                        buf = content[offset:offset+size]

                    else:
                        buf = ''

                    return buf

        except (KeyError, ResourceNotFound):
            pass

        print 'Something went wrong while reading %s' % path
        return -errno.ENOENT

    def write(self, path, buf, offset):
        """
        Write data in file located at given path.
            path {string}: file path
            buf {buffer}: data to write
            offset {integer}: beginning of file part to read
        """
        # TODO rewrite that one.
        try:
            for res in self.db.view("file/byFullPath", key=path):
                self.currentFile = self.currentFile + buf
                return len(buf)

        except (KeyError, ResourceNotFound):
            pass

        print 'Something went wrong while writing %s' % path
        return -errno.ENOENT

    def release(self, path, fuse_file_info):
        """
        Save file to database and launch replication to remote Cozy.
            path {string}: file path
            fuse_file_info {struct}: information about open file

            Release is called when there are no more references
            to an open file: all file descriptors are closed and
            all memory mappings are unmapped.
        """
        if self.currentFile != "":

            for res in self.db.view("file/byFullPath", key=path):
                res = res.value
                binary_id = res["binary"]["file"]["id"]

                # TODO put binary copy in a micro thread?
                self.db.put_attachment(self.db[binary_id],
                                       self.currentFile,
                                       filename="file")

                binary = self.db[binary_id]
                res['binary']['file']['rev'] = binary['_rev']
                self.db.save(res)
                # TODO put replication in a micro thread?
                self._replicate_from_local([binary_id])

            self.currentFile = ""

    def mknod(self, path, mode, dev):
        """
        Create special/ordinary file. Since it's a new file, the file and
        and the binary metadata are created in the database. Then file is saved
        as an attachment to the database.
            path {string}: file path
            mode {string}: file permissions
            dev: if the file type is S_IFCHR or S_IFBLK, dev specifies the
                 major and minor numbers of the newly created device special
                 file
        """
        (file_path, name) = _path_split(path)

        new_binary = {"docType": "Binary"}
        binary_id = self.db.create(new_binary)
        # TODO put binary copy in a micro thread?
        self.db.put_attachment(self.db[binary_id], '', filename="file")

        rev = self.db[binary_id]["_rev"]
        newFile = {
            "name": name,
            "path": file_path,
            "binary": {
                "file": {
                    "id": binary_id,
                    "rev": rev
                }
            },
            "docType": "File"
        }
        self.db.create(newFile)

        # TODO put replication in a micro thread?
        self._replicate_from_local([binary_id])

    def unlink(self, path):
        """
        Remove file from database.
        """
        path = _normalize_path(path)
        parts = path.rsplit(u'/', 1)
        if len(parts) == 1:
            dirname, filename = u'', parts[0]
        else:
            dirname, filename = parts

        for res in self.db.view("file/byFullPath", key='/' + path):
            file_doc = res.value
            binary_id = file_doc["binary"]["file"]["id"]
            self.db.delete(self.db[binary_id])
            self.db.delete(self.db[file_doc["_id"]])
            # TODO put replication in a micro thread?
            self._replicate_from_local([binary_id])

    def truncate(self, path, size):
        """ TODO: look if something should be done there.
        Change size of a file.
        """
        return 0

    def utime(self, path, times):
        """ TODO: look if something should be done there.
        Change the access and/or modification times of a file
        """
        return 0

    def mkdir(self, path, mode):
        """
        Create folder in the database.
            path {string}: diretory path
            mode {string}: directory permissions
        """
        (folder_path, name) = _path_split(path)

        self.db.create({
            "name": name,
            "path": folder_path,
            "docType": "Folder"
        })

        return 0

    def rmdir(self, path):
        """
        Delete folder from database.
            path {string}: diretory path
        """
        for res in self.db.view("folder/byFullPath", key=path):
            folder = res.value
            self.db.delete(self.db[folder['_id']])

            # TODO Delete subfolders and sub files
            return 0

    def rename(self, pathfrom, pathto):
        """
        Rename file and subfiles (if it's a folder) in database.
        """
        # TODO Make sure that everything is replicated.
        for doc in self.db.view("file/byFullPath", key=pathfrom):
            doc = doc.value
            (file_path, name) = _path_split(pathto)
            doc.update({"name": name, "path": file_path})
            self.db.save(doc)
            return 0

        for doc in self.db.view("folder/byFullPath", key=pathfrom):
            doc = doc.value
            (file_path, name) = _path_split(pathto)
            doc.update({"name": name, "path": file_path})

            # Rename all subfiles
            for res in self.db.view("file/byFolder", key=pathfrom):
                pathfrom = os.path.join(res.value['path'], res.value['name'])
                pathto = os.path.join(file_path, name, res.value['name'])
                self.rename(pathfrom, pathto)

            for res in self.db.view("folder/byFolder", key=pathfrom):
                pathfrom = os.path.join(res.value['path'], res.value['name'])
                pathto = os.path.join(file_path, name, res.value['name'])
                self.rename(pathfrom, pathto)

            self.db.save(doc)
            return 0

    def fsync(self, path, isfsyncfile):
        """ TODO: look if something should be done there. """
        return 0

    def chmod(self, path, mode):
        """ TODO: look if something should be done there. """
        return 0

    def chown(self, path, uid, gid):
        """ TODO: look if something should be done there. """
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

        blocks = 1024 * 1024
        block_size = 1024
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

    def _replicate_from_local(self, ids):
        '''
        Replicate file modifications to remote Cozy.
        '''
        # TODO: use replication module instead.
        (username, password) = ('', '')
        source = 'http://%s:%s@localhost:5984/%s' % (username,
                                                     password,
                                                     self.database)
        url = self.urlCozy.split('/')
        target = "https://%s:%s@%s/cozy" % (self.loginCozy,
                                            self.passwordCozy,
                                            url[2])
        self.rep = self.server.replicate(source, target, doc_ids=ids)


def _normalize_path(path):
    '''
    Remove trailing slash and/or empty path part.
    ex: /home//user/ becomes /home/user
    '''
    return u'/'.join([part for part in path.split(u'/') if part != u''])


def _path_split(path):
    '''
    '''
    _normalize_path(path)
    (folder_path, name) = os.path.split(path)
    if folder_path[-1:] == '/':
        folder_path = folder_path[:-(len(name)+1)]
    return (folder_path, name)


def unmount(path):
    subprocess.call(["fusermount", "-u", path])


def mount(name, path):
    fs = CouchFSDocument(name, path, 'http://localhost:5984/%s' % name)
    fs.main()
