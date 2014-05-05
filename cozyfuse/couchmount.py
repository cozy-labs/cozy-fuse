#!/usr/bin/env python

# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 Jason Davies
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

import os
import platform
import errno
import fuse
import stat
import subprocess
import logging
import datetime
import calendar

import dbutils
import local_config

from couchdb import ResourceNotFound

fuse.fuse_python_api = (0, 2)

CONFIG_FOLDER = os.path.join(os.path.expanduser('~'), '.cozyfuse')
HDLR = logging.FileHandler(os.path.join(CONFIG_FOLDER, 'cozyfuse.log'))
HDLR.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))

logger = logging.getLogger(__name__)
logger.addHandler(HDLR)
logger.setLevel(logging.INFO)
#local_config.configure_logger(logger)


def get_date(ctime):
    ctime = ctime[0:24]
    try:
        date = datetime.datetime.strptime(ctime, "%a %b %d %H:%M:%S %Y")
    except ValueError:
        date = datetime.datetime.strptime(ctime, "%a %b %d %Y %H:%M:%S")
    return calendar.timegm(date.utctimetuple())



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
        logger.info('Mounting folder...')

        # Configure fuse
        fuse.Fuse.__init__(self, *args, **kwargs)
        self.fuse_args.mountpoint = mountpoint
        self.fuse_args.add('allow_other')
        self.currentFile = None

        # Configure database
        self.database = database
        (self.db, self.server) = dbutils.get_db_and_server(database)

        ## Configure Cozy
        device = dbutils.get_device(database)
        self.urlCozy = device['url']
        self.passwordCozy = device['password']
        self.loginCozy = device['login']

        # Configure replication urls.
        (self.db_username, self.db_password) = \
            local_config.get_db_credentials(database)
        string_data = (
            self.db_username,
            self.db_password,
            self.database
        )
        self.rep_source = 'http://%s:%s@localhost:5984/%s' % string_data
        string_data = (
            self.loginCozy,
            self.passwordCozy,
            self.urlCozy.split('/')[2]
        )
        self.rep_target = "https://%s:%s@%s/cozy" % string_data

        # init cache
        self.dirs = {}
        self.descriptors = {}
        self.writeBuffers = {}

    def add_file_to_dirs(self, path, name):
        '''
        Add file reference to directory cache.
        '''
        full_path = os.path.join(path, name)
        logger.info("path add: %s" % full_path)
        path = _normalize_path(path)
        filenames = self.dirs.setdefault(path, set())
        filenames.add(name)
        self.getattr(full_path)

    def remove_file_from_dirs(self, path, name):
        '''
        Remove file reference from directory cache.
        '''
        logger.info("path remove: " + path)
        if len(path) > 0:
            file_path = os.path.join(path, name)
        else:
            file_path = name
        path = _normalize_path(path)
        file_path = _normalize_path(file_path)

        filenames = self.get_dirs().setdefault(path, set())
        if name in filenames:
            filenames.remove(name)
        self.descriptors.pop(file_path, None)

    def get_dirs(self):
        """
        Get directories
        """
        try:
            if len(self.dirs.keys()) > 0:
                return self.dirs
            else:
                self.dirs = {}

                folders = dbutils.get_folders(self.db)
                for folder in folders:
                    folder_path = os.path.join(folder.value["path"],
                                               folder.value["name"])
                    if len(folder_path) != 0:
                        folder_path = folder_path[0:]

                    parents = [u'']
                    for name in folder_path.split('/'):
                        if name != '':
                            path = u'/'.join(parents[1:])

                            path = _normalize_path(path)
                            filenames = self.dirs.setdefault(path, set())
                            filenames.add(name)
                            parents.append(name)

                    folder_path = _normalize_path(folder_path)
                    self.dirs.setdefault(u'' + folder_path, set())

                files = dbutils.get_files(self.db)
                for file_doc in files:
                    file_path = os.path.join(
                        file_doc.value["path"], file_doc.value["name"])
                    parents = [u'']
                    for name in file_path.split('/'):
                        if name != '':
                            path = u'/'.join(parents[1:])

                            path = _normalize_path(path)
                            filenames = self.dirs.setdefault(path, set())
                            filenames.add(name)
                            parents.append(name)

            logger.info(self.dirs)
            return self.dirs

        except Exception, e:
            logger.exception(e)
            return {}

    def readdir(self, path, offset):
        """
        Generator: list files for given path and yield each file result when
        it arrives.
        """
        path = _normalize_path(path)
        for directory in '.', '..':  # this two folders are conventional in Unix system.
            yield fuse.Direntry(directory)
        for name in self.get_dirs().get(path, set()):
            yield fuse.Direntry(name.encode('utf-8'))

    def getattr(self, path):
        """
        Return file descriptor for given_path. Useful for 'ls -la' command like.
        """
        try:
            logger.debug('getattr %s' % path)

            # Result is cached.
            if path in self.descriptors:
                return self.descriptors[path]

            else:
                st = CouchStat()

                # Path is root
                if path is "/":
                    st.st_mode = stat.S_IFDIR | 0775
                    st.st_nlink = 2
                    self.descriptors[path] = st
                    return st

                else:
                    # Or path is a folder
                    folder = dbutils.get_folder(self.db, path)

                    if folder is not None:
                        st.st_mode = stat.S_IFDIR | 0775
                        st.st_nlink = 2
                        if 'lastModification' in folder:
                            st.st_atime = get_date(folder['lastModification'])
                            st.st_ctime = st.st_atime
                            st.st_mtime = st.st_atime

                        self.descriptors[path] = st
                        return st

                    else:
                        # Or path is a file
                        file_doc = dbutils.get_file(self.db, path)

                        if file_doc is not None:
                            st.st_mode = stat.S_IFREG | 0664
                            st.st_nlink = 1
                            # TODO: if size is not set, get the binary
                            # and save the information.
                            st.st_size = file_doc.get('size', 4096)
                            if 'lastModification' in file_doc:
                                st.st_atime = \
                                    get_date(file_doc['lastModification'])
                                st.st_ctime = st.st_atime
                                st.st_mtime = st.st_atime
                            self.descriptors[path] = st
                            return st

                        else:
                            print 'File does not exist: %s' % path
                            return -errno.ENOENT
                            return st

        except Exception, e:
            logger.exception(e)
            return -errno.ENOENT

    def open(self, path, flags):
        """
        Open file
            path {string}: file path
            flags {string}: opening mode
        """
        path = _normalize_path(path)

        try:
            logger.info('open %s' % path)
            parts = path.rsplit(u'/', 1)
            if len(parts) == 1:
                dirname, filename = u'', parts[0]
            else:
                dirname, filename = parts

            if filename in self.get_dirs()[dirname]:
                logger.info('%s found' % filename)
                return 0
            else:
                logger.error('File not found %s' % path)
                return -errno.ENOENT

        except Exception, e:
            logger.exception(e)
            return -errno.ENOENT

    def read(self, path, size, offset):
        """
        Return content of file located at given path.
            path {string}: file path
            size {integer}: size of file part to read
            offset {integer}: beginning of file part to read
        """
        # TODO: do not load the file for each chunk.
        # Save it in a cache file maybe?.
        try:
            path = _normalize_path(path)
            logger.info('read %s' % path)
            file_doc = dbutils.get_file(self.db, path)
            binary_id = file_doc["binary"]["file"]["id"]
            binary_attachment = self.db.get_attachment(binary_id, "file")
            logger.info(binary_id)

            if binary_attachment is None:
                logger.info('No attachment for this binary')
                return ''

            else:
                content = binary_attachment.read()
                content_length = len(content)
                logger.info('Return file content')

                if offset < content_length:
                    if offset + size > content_length:
                        size = content_length - offset
                    buf = content[offset:offset+size]

                else:
                    buf = ''
                    logger.info('Empty file content')

                return buf

        except Exception, e:
            logger.exception(e)
            return -errno.ENOENT

    def write(self, path, buf, offset):
        """
        Write data in file located at given path.
            path {string}: file path
            buf {buffer}: data to write
        """
        path = _normalize_path(path)
        logger.info('write %s' % path)
        if path not in self.writeBuffers:
            self.writeBuffers[path] = ''
        self.writeBuffers[path] = self.writeBuffers[path] + buf
        return len(buf)

    def release(self, path, fuse_file_info):
        """
        Save file to database and launch replication to remote Cozy.
            path {string}: file path
            fuse_file_info {struct}: information about open file

            Release is called when there are no more references
            to an open file: all file descriptors are closed and
            all memory mappings are unmapped.
        """
        try:
            path = _normalize_path(path)
            if len(path) > 0 and path[0] != '/':
                path = '/' + path
            logger.info('release file %s' % path)
            file_doc = dbutils.get_file(self.db, path)
            binary_id = file_doc["binary"]["file"]["id"]

            if path in self.writeBuffers:
                data = self.writeBuffers[path]
                self.db.put_attachment(self.db[binary_id],
                                       data,
                                       filename="file")
                file_doc['size'] = len(data)
                self.writeBuffers.pop(path, None)

                binary = self.db[binary_id]
                file_doc['binary']['file']['rev'] = binary['_rev']
                file_doc['lastModification'] = datetime.datetime.now().ctime()
                self.db.save(file_doc)

            logger.info("release is done")
            return 0

        except Exception, e:
            logger.exception(e)
            return -errno.ENOENT

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
        try:
            path = _normalize_path(path)
            logger.info('mknod %s' % path)
            (file_path, name) = _path_split(path)

            file_path = _normalize_path(file_path)
            new_binary = {"docType": "Binary"}
            binary_id = self.db.create(new_binary)
            self.db.put_attachment(self.db[binary_id], '', filename="file")

            rev = self.db[binary_id]["_rev"]
            newFile = {
                "name": name,
                "path": _normalize_path(file_path),
                "binary": {
                    "file": {
                        "id": binary_id,
                        "rev": rev
                    }
                },
                "docType": "File",
                'creationDate': datetime.datetime.now().ctime(),
                'lastModification': datetime.datetime.now().ctime(),
            }
            self.db.create(newFile)

            logger.info("file created")
            # TODO debug add_file_to_dirs
            self.add_file_to_dirs(file_path, name)
            logger.info('mknod is done for %s' % path)
            return 0
        except Exception, e:
            logger.exception(e)
            return -errno.ENOENT


    def unlink(self, path):
        """
        Remove file from database.
        """

        try:
            path = _normalize_path(path)
            logger.info('unlink %s' % path)
            parts = path.rsplit(u'/', 1)
            if len(parts) == 1:
                    dirname, filename = u'', parts[0]
            else:
                dirname, filename = parts

            file_doc = dbutils.get_file(self.db, path)
            if file_doc is not None:
                binary_id = file_doc["binary"]["file"]["id"]
                logger.info(self.db[file_doc["_id"]])

                try:
                    self.db.delete(self.db[binary_id])
                except ResourceNotFound:
                    pass
                self.db.delete(self.db[file_doc["_id"]])

                self.remove_file_from_dirs(dirname, filename)
                logger.info('file %s removed' % path)
                return 0
            else:
                logger.warn('Cannot delete file, no entry found')
                return -errno.ENOENT

        except Exception, e:
            logger.exception(e)
            return -errno.ENOENT

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
        try:
            (folder_path, name) = _path_split(path)

            logger.info('create new dir %s' % path)
            self.db.create({
                "name": name,
                "path": _normalize_path(folder_path),
                "docType": "Folder",
                'creationDate': datetime.datetime.now().ctime(),
                'lastModification': datetime.datetime.now().ctime(),
            })

            self.get_dirs().setdefault(path[1:], set())
            self.getattr(path)
            return 0

        except Exception, e:
            logger.exception(e)
            return -errno.ENOENT

    def rmdir(self, path):
        """
        Delete folder from database.
            path {string}: diretory path
        """
        try:
            path = _normalize_path(path)
            logger.info('rmdir %s' % path)
            folder = dbutils.get_folder(self.db, path)
            self.db.delete(self.db[folder['_id']])

            self.dirs.pop(path, None)
            self.descriptors.pop(path, None)
            return 0

        except Exception, e:
            logger.exception(e)
            return -errno.ENOENT

    def rename(self, pathfrom, pathto):
        """
        Rename file and subfiles (if it's a folder) in database.
        """
        logger.info("path rename %s: " % pathfrom)
        pathfrom = _normalize_path(pathfrom)
        pathto = _normalize_path(pathto)

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

            # TODO update get_dirs
            # TODO update last modification date
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
        self.rep = self.server.replicate(
            self.rep_source,
            self.rep_target,
            doc_ids=ids
        )


def _normalize_path(path):
    '''
    Remove trailing slash and/or empty path part.
    ex: /home//user/ becomes /home/user
    '''
    path = u'/'.join([part for part in path.split(u'/') if part != u''])
    if len(path) == 0:
        return ''
    elif path[0] == '/':
        return path[1:]
    else:
        return path


def _path_split(path):
    '''
    '''
    _normalize_path(path)
    (folder_path, name) = os.path.split(path)
    if folder_path[-1:] == '/':
        folder_path = folder_path[:-(len(name)+1)]
    return (folder_path, name)


def unmount(path):
    if platform.system() == "Darwin":
        command = ["umount", path]
    else:
        command = ["fusermount", "-u", path]

    subprocess.call(command)
    logger.info('Folder %s unmounted' % path)


def mount(name, path):
    logger.info('Attempt to mount %s' % path)
    fs = CouchFSDocument(name, path, 'http://localhost:5984/%s' % name)
    fs.multithreaded = 0
    fs.main()
