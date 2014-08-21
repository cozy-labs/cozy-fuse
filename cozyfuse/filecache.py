import os
import requests
import couchmount
import dbutils


class BinaryCache:
    '''
    Utility class to manage file cachin properly.
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

        if not os.path.isdir(self.cache_path):
            os.makedirs(self.cache_path)

    def get_binary(self, binary_id, file_doc):
        '''
        Download binary from remote Cozy and save it in the cache folder.

        Path ex: cache_folder/binary_id/file

        'file' is a constant.
        '''
        cache_file_folder = os.path.join(self.cache_path, binary_id)

        # Create cache folder for given binary
        if not os.path.isdir(cache_file_folder):
            os.mkdir(cache_file_folder)

        # Path for target file.
        filename = os.path.join(cache_file_folder, 'file')

        # Download file if file doesn't already exists.
        if not os.path.isfile(filename):
            url = '%s/%s/%s' % (self.remote_url, binary_id, 'file')
            req = requests.get(url, stream=True)
            with open(filename, 'wb') as fd:
                for chunk in req.iter_content(1024):
                    fd.write(chunk)

        file_doc['size'] = os.path.getsize(filename)
        db = dbutils.get_db(self.name)
        db.save(file_doc)

        return open(filename, 'rb')

    def cache_file_by_path(self, path):
        '''
        For a given path in the the mounted folder, cache corresponding file.
        File is marked as stored on the device.
        '''
        abs_path = os.path.abspath(path)
        path = abs_path[len(self.device_mount_path):]
        path = couchmount._normalize_path(path)

        db = dbutils.get_db(self.name)
        file_doc = dbutils.get_file(db, path)
        binary_id = file_doc["binary"]["file"]["id"]

        self.get_binary(binary_id, file_doc)
        self.mark_file_as_stored(db, file_doc, self.name)

    def mark_file_as_stored(self, db, file_doc, device_name):
        '''
        Mark file as stored in the database. It's done by adding the device
        name to the storage list field.
        '''
        if file_doc.get('storage', None) is None:
            file_doc['storage'] = [device_name]
        elif not (device_name in file_doc['storage']):
            file_doc['storage'].append(device_name)

        db.save(file_doc)
