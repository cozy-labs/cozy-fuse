import argparse
import getpass
import sys
import requests
import json

import couchmount
import replication
import local_config
import remote

from argparse import RawTextHelpFormatter
from couchdb.http import ResourceNotFound

from download_binary import Replication
from dbutils import init_db, remove_db
from couchdb import Server


def register_device_remotely(name):
    (url, path) = local_config.get_config(name)
    password = getpass.getpass('Type your password:\n')
    (device_id, device_password) = remote.register_device(name, url,
                                                          path, password)
    local_config.save_remote_data_to_config(name, device_id, device_password)
    print 'Device registered'


def remove_device_remotely(name):
    (url, path) = local_config.get_config(name)
    (device_id, password) = local_config.get_device_config(name)
    password = getpass.getpass('Type your password:\n')
    remote.remove_device(url, device_id, password)
    print 'Device removed'


def run_replications(name):
    (url, path) = local_config.get_config(name)
    (device_id, password) = local_config.get_device_config(name)

    replication.replicate_to_local_one_shot_without_deleted(
       name, url, name, password, device_id)
    print '[Replication] One shot replication is done'

    replication.init_device(name, url, password, device_id)
    print '[Replication] Device initialized'

    replication.replicate_from_local_one_shot(
        name, url, name, password, device_id)
    print '[Replication] Add missing data to remote database.'

    Replication(name)
    print '[Replication] Binaries synchronized.'


def kill_running_replications():
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


def reset():
    # Remove devices remotely
    config = local_config.get_full_config()
    try:
        for name in config.keys():
            device = config[name]
            path = device['path']
            couchmount.unmount(path)
            remove_device_remotely(name)
            print '[reset] Device %s unregistered' % name

        # Remove database
        remove_db(name)
        print 'Local database deleted'

    except ResourceNotFound:
        print 'No device found locally'

    # Remove local config file
    local_config.clear()
    print 'Configuraton file deleted'



def mount_folder(name):
    try:
        (url, path) = local_config.get_config(name)
        couchmount.mount(name, path)
    except KeyboardInterrupt:
        unmount_folder()


def unmount_folder(name, path=None):
    if path is None:
        (url, path) = local_config.get_config(name)
    couchmount.unmount(path)


def display_config():
    config = local_config.get_full_config()
    for device in config.keys():
        print 'Configuration for device %s:' % device
        for key in config[device].keys():
            print '    %s = %s' % (key, config[device][key])
        print ' '


def unregister_device(name):
    (url, path) = local_config.get_config(name)
    (device_id, device_password) = local_config.get_device_config(name)
    local_config.remove(name)
    remove_db()
    password = getpass.getpass('Type your password:\n')
    remote.remove_device(url, device_id, password)


def configure_new_device(name, url, path):
    local_config.add_config(name, url, path)
    init_db(name)
    register_device_remotely(name)
    mount_folder(name)


def start_auto_sync(name):
    (url, path) = local_config.get_config(name)
    (device_id, device_password) = local_config.get_device_config(name)

    replication.replicate_to_local(
        name, url, name, device_password, device_id)
    replication.replicate_from_local(
        name, url, name, device_password, device_id)


def main(argv=sys.argv):
    parser = argparse.ArgumentParser(
        description='Manage your local configuration for Cozy syncing and ' \
                    'FUSE mounting',
        formatter_class=RawTextHelpFormatter)
    parser.add_argument('action', help='Action to perform.')
    parser.add_argument('-p', '--path')
    parser.add_argument('-u', '--url')
    parser.add_argument('-n', '--name')

    args = parser.parse_args()

    if args.action is None:
        parser.print_help()
        print('\nYou must specify an action argument\n')
        sys.exit(2)

    elif args.action == 'reset':
        reset()

    elif args.action == 'new_device':
        configure_new_device(args.name, args.url, args.path)

    elif args.action == 'init_db':
        init_db(args.name)

    elif args.action == 'add_device':
        local_config.add_config(args.name, args.url, args.path)

    elif args.action == 'register_device':
        register_device_remotely(args.name)

    elif args.action == 'run_replications':
        run_replications(args.name)

    elif args.action == 'start_auto_sync':
        start_auto_sync(args.name)

    elif args.action == 'mount_folder':
        mount_folder(args.name)

    elif args.action == 'unmount_folder':
        unmount_folder(args.name, args.path)

    elif args.action == 'display_config':
        display_config()

    elif args.action == 'unregister_device':
        unregister_device(args.name)

    elif args.action == 'unregister_device_remotely':
        remove_device_remotely()

    elif args.action == 'kill_running_replications':
        kill_running_replications()


if __name__ == "__main__":
    main()
