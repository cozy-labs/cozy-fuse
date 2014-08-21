import os
import shutil
import requests
import datetime

import dbutils
import cache


ATTR_VALIDITY_PERIOD = datetime.timedelta(seconds=5 * 60)

class BinaryCache:
    '''
    Utility class to manage file caching properly.
    '''

    def __init__(self,
                 name, device_config_path, remote_url, device_mount_path):
        '''
        Register information required to handle caching.
        '''
        self.name = name
        self.device_config_path = device_config_path
        self.remote_url = remote_url
        self.cache_path = os.path.join(device_config_path, 'cache')
        self.device_mount_path = device_mount_path
        self.db = dbutils.get_db(self.name)
        self.metadata_cache = cache.Cache(ATTR_VALIDITY_PERIOD)

        if not os.path.isdir(self.cache_path):
            os.makedirs(self.cache_path)

    def get_file_metadata(self, path):
        res = self.metadata_cache.get(path)
        if res is None:
            file_doc = dbutils.get_file(self.db, path)
            binary_id = file_doc["binary"]["file"]["id"]
            cache_file_folder = os.path.join(self.cache_path, binary_id)
            cache_file_name = os.path.join(cache_file_folder, 'file')

            res = (file_doc, binary_id, cache_file_name)
            self.metadata_cache.add(path, res)
        return res

    def is_cached(self, path):
        '''
        Return True is the file is already present in the cache folder.
        '''
        (file_doc, binary_id, filename) = self.get_file_metadata(path)

        return os.path.exists(filename)

    def get(self, path):
        '''
        Returns the required file from the cache (local file system).
        '''
        (file_doc, binary_id, filename) = self.get_file_metadata(path)

        return open(filename, 'rb')

    def add(self, path):
        '''
        Download binary from local CouchDB and save it in the cache folder.
        File is marked as stored in the file metadata.
        '''
        (file_doc, binary_id, filename) = self.get_file_metadata(path)
        cache_file_folder = os.path.join(self.cache_path, binary_id)

        # Create cache folder for given binary
        if not os.path.isdir(cache_file_folder):
            os.mkdir(cache_file_folder)

        # Download file.
        url = '%s/%s/%s' % (self.remote_url, binary_id, 'file')
        req = requests.get(url, stream=True)
        with open(filename, 'wb') as fd:
            for chunk in req.iter_content(1024):
                fd.write(chunk)

        # Update metadata.
        file_doc['size'] = os.path.getsize(filename)
        self.mark_file_as_stored(file_doc)

    def remove(self, path):
        '''
        Remove file from cache.
        '''
        (file_doc, binary_id, filename) = self.get_file_metadata(path)

        cache_file_folder = os.path.join(self.cache_path, binary_id)
        shutil.rmtree(cache_file_folder)
        self.mark_file_as_not_stored(file_doc)

    def mark_file_as_stored(self, file_doc):
        '''
        Mark file as stored in the database. It's done by adding the device
        name to the storage list field.
        '''
        if file_doc.get('storage', None) is None:
            file_doc['storage'] = [self.name]
        elif not (self.name in file_doc['storage']):
            file_doc['storage'].append(self.name)

        self.db.save(file_doc)

    def mark_file_as_not_stored(self, file_doc):
        '''
        Remove the device name from the storage list linked to the given
        file_doc.
        '''
        if file_doc.get('storage', None) is None:
            return
        elif self.name in file_doc['storage']:
            file_doc['storage'].remove(self.name)

        self.db.save(file_doc)
