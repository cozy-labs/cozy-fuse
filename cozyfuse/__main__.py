#!/usr/bin/env python
import argparse
import sys

import actions

from argparse import RawTextHelpFormatter


DOC = '''
manage your local configuration for Cozy syncing and FUSE mounting. Available
actions are:

   configure: configure a new Cozy locally and register current device remotely.
   sync: synchronize current device with its remote Cozy.
   reset: clear all data from local computer and remove current device remotely.

   mount: mount folder for current device.
   unmount: unmount folder for current device.

   display_config: display configuration for remote cozy.
   kill_running_replications: ask to database to stop synchronization.
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

    elif args.action == 'configure':
        actions.configure_new_device(args.name, args.url, args.path)

    elif args.action == 'remove_configuration':
        actions.remove_device(args.name)

    elif args.action == 'sync':
        actions.sync(args.name)

    elif args.action == 'mount':
        actions.mount_folder(args.name)

    elif args.action == 'unmount':
        actions.unmount_folder(args.name, args.path)

    elif args.action == 'reset':
        actions.reset()

    elif args.action == 'display_config':
        actions.display_config()

    elif args.action == 'kill_running_replications':
        actions.kill_running_replications()

    else:
        parser.print_help()
        print('\nYou must specify an action argument\n')

if __name__ == "__main__":
    main()
