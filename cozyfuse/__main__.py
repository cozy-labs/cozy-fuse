#!/usr/bin/env python
import argparse
import sys

import local_config
import actions

from argparse import RawTextHelpFormatter


DOC = '''
manage your local configuration for Cozy syncing and FUSE mounting. Available
actions are:

   new_device: register a new device locally and remotely.
   remove_device: remove given device locally and remotely.

   mount_folder: mount folder for given device.
   unmount_folder: unmount folder for given device.

   run_replication: run first replication for given device.
   start_sync: synchronize given device with its remote configuration.
   kill_running_replications: terminate running replications.

   reset: clear all data from local computer and remove all device remotely.
   display_config: display configuration for all devices.

'''

def main(argv=sys.argv):
    parser = argparse.ArgumentParser(
        description=DOC, formatter_class=RawTextHelpFormatter)
    parser.add_argument('action',
                        help='Action to perform.')
    parser.add_argument('-p', '--path',
                        help='Path where Cozy files will be mounted')
    parser.add_argument('-u', '--url',
                        help='URL of remote Cozy to sync')
    parser.add_argument('-n', '--name',
                        help='Name of the device on which action occurs')

    args = parser.parse_args()

    if args.action is None:
        parser.print_help()
        print('\nYou must specify an action argument\n')
        sys.exit(2)

    elif args.action == 'reset':
        actions.reset()

    elif args.action == 'new_device':
        actions.configure_new_device(args.name, args.url, args.path)

    elif args.action == 'add_device':
        local_config.add_config(args.name, args.url, args.path)

    elif args.action == 'register_device':
        actions.register_device_remotely(args.name)

    elif args.action == 'run_replication':
        actions.run_replication(args.name)

    elif args.action == 'start_sync':
        actions.start_auto_sync(args.name)

    elif args.action == 'mount_folder':
        actions.mount_folder(args.name)

    elif args.action == 'unmount_folder':
        actions.unmount_folder(args.name, args.path)

    elif args.action == 'display_config':
        actions.display_config()

    elif args.action == 'unregister_device':
        actions.unregister_device(args.name)

    elif args.action == 'remove_device':
        print 'not implemented yet'

    elif args.action == 'kill_running_replications':
        actions.kill_running_replications()


if __name__ == "__main__":
    main()
