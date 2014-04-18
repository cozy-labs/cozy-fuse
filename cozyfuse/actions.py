import getpass
import requests
import json

import couchmount
import replication
import local_config
import remote

from couchdb.http import ResourceNotFound

import dbutils
from couchdb import Server


def register_device_remotely(name):
    '''
    Register device to target Cozy
    '''
    (url, path) = local_config.get_config(name)
    if url[-1:] == '/':
         url = url[:-(len(name)+1)]
    password = getpass.getpass('Type your password:\n')
    (device_id, device_password) = remote.register_device(name, url,
                                                          path, password)
    local_config.set_device_config(name, device_id, device_password)
    print '[Remote] Device %s registered' % name


def remove_device_remotely(name):
    '''
    Delete given device form target Cozy.
    '''
    (url, path) = local_config.get_config(name)
    (device_id, password) = local_config.get_device_config(name)
    password = getpass.getpass('Type your Cozy password:\n')
    remote.remove_device(url, device_id, password)
    print '[Remote] %s removed' % name


def init_replication(name):
    '''
    Run initial replications then start continutous replication.
    Write device information in database.
    '''
    (url, path) = local_config.get_config(name)
    (device_id, password) = local_config.get_device_config(name)
    (db_login, db_password) = local_config.get_db_credentials(name)

    replication.replicate(
       name, url, name, password, device_id, db_login, db_password,
       to_local=True, continuous=False, deleted=False)
    print '[Replication] One shot replication is done'

    dbutils.init_device(name, url, path, password, device_id)
    print '[Replication] Device initialized'

    replication.replicate(
        name, url, name, password, device_id, db_login, db_password,
        to_local=False, continuous=False)
    print '[Replication] Add missing data to remote database.'

    replication.replicate(name, url, name, password, device_id,
                          db_login, db_password, to_local=True)
    print '[Replication] Start remote to local replication'

    replication.replicate(name, url, name, password, device_id,
                          db_login, db_password)
    print '[Replication] Start local to remote replication'


def kill_running_replications():
    '''
    Kill running replications in CouchDB (based on active tasks info).
    Useful when a replication is in Zombie mode.
    '''
    server = Server('http://localhost:5984/')

    for task in server.tasks():
        data = {
            "replication_id": task["replication_id"],
            "cancel": True
        }
        headers = {'content-type': 'application/json'}
        response = requests.post('http://localhost:5984/_replicate',
                json.dumps(data), headers=headers)
        if response.status_code == 200:
            print 'Replication %s stopped.' % data['replication_id']
        else:
            print 'Replication %s was not stopped.' % data['replication_id']


def remove_device(name):
    '''
    Remove device from local and remote configuration by:

    * Unmounting device folder.
    * Removing device on corresponding remote cozy.
    * Removing device from configuration file.
    * Destroying corresponding DB.
    '''
    (url, path) = local_config.get_config(name)

    couchmount.unmount(path)
    print '[mount] %s unmounted' % path
    remove_device_remotely(name)
    print '[remote] Device %s unregistered' % name

    # Remove database
    dbutils.remove_db(name)
    dbutils.remove_db_user(name)
    print '[db] Local database deleted for %s' % name

    local_config.remove_config(name)


def reset():
    '''
    Reset local and remote configuration by:

    * Unmounting each device folder.
    * Removing each device on corresponding remote cozies.
    * Removing configuration file.
    * Destroy corresponding DBs.
    '''
    # Remove devices remotely
    try:
        config = local_config.get_full_config()
    except local_config.NoConfigFile:
        print 'No config file found, cannot reset anything'
        return True

    try:
        for name in config.keys():
            print '[reset] Clearing %s' % name
            remove_device(name)

    except ResourceNotFound:
        print '[reset] No device found locally'


    # Remove local config file
    local_config.clear()
    print '[reset] Configuraton file deleted'


def mount_folder(name):
    '''
    Mount folder linked to given device.
    '''
    try:
        (url, path) = local_config.get_config(name)
        couchmount.unmount(path)
        context = local_config.get_daemon_context(name, 'mount')
        with context:
            couchmount.mount(name, path)
        print '[mount] Folder %s mounted' % path
    except KeyboardInterrupt:
        unmount_folder(name)


def unmount_folder(name, path=None):
    '''
    Unmount folder linked to given device.
    '''
    if path is None:
        (url, path) = local_config.get_config(name)
    couchmount.unmount(path)
    print '[mount] Folder %s unmounted' % path


def display_config():
    '''
    Display config file in a human readable way.
    '''
    config = local_config.get_full_config()
    for device in config.keys():
        print 'Configuration for device %s:' % device
        for key in config[device].keys():
            print '    %s = %s' % (key, config[device][key])
        print ' '


def unregister_device(name):
    '''
    Remove device from local configuration, destroy corresponding database
    and unregister it from remote Cozy.
    '''
    print '[Device] %s removed' % name
    (url, path) = local_config.get_config(name)
    (device_id, device_password) = local_config.get_device_config(name)
    local_config.remove(name)
    dbutils.remove_db(name)
    password = getpass.getpass('Type your password:\n')
    remote.remove_device(url, device_id, password)


def configure_new_device(name, url, path):
    '''
    * Create configuration for given device.
    * Create database and init CouchDB views.
    * Register device on remote Cozy defined by *url*.
    * Init replications.
    '''
    (db_login, db_password) = dbutils.init_db(name)
    local_config.add_config(name, url, path, db_login, db_password)
    register_device_remotely(name)
    init_replication(name)
    print 'New device %s configured.' % name
    print 'Use cozy-fuse mount -n %s to see your files.' % name


def sync(name):
    '''
    Run continuous synchronization between CouchDB instances.
    '''
    (url, path) = local_config.get_config(name)
    (device_id, device_password) = local_config.get_device_config(name)
    (db_login, db_password) = local_config.get_db_credentials(name)

    replication.replicate(name, url, name, device_password, device_id,
                          db_login, db_password, to_local=True)
    print '[Replication] Start remote to local replication'

    replication.replicate(name, url, name, device_password, device_id,
                          db_login, db_password)
    print '[Replication] Start local to remote replication'

    print '[Replication] Run binary synchronization...'
    try:
        context = local_config.get_daemon_context(name, 'sync')
        with context:
            replication.BinaryReplication(name)
    except KeyboardInterrupt:
        print '[Replication] Synchronization interrupted.'
