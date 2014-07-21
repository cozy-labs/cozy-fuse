#!/usr/bin/env python
import argparse
import argcomplete
import sys

import actions
import local_config

from argparse import RawTextHelpFormatter
from yaml import load


# Implement ArgumentParser class to display help on error
class DefaultHelpParser(argparse.ArgumentParser):

    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)


def DeviceCompleter(prefix, **kwargs):
    '''
    Autocomplete device name
    '''
    try:
        config = local_config.get_full_config()
    except:
        return ()
    else:
        return (name for name, conf in config.items())


def main(argv=sys.argv):

    parser = DefaultHelpParser(
        description='Manage your local configuration for Cozy syncing'
                    ' and FUSE mounting',
        formatter_class=RawTextHelpFormatter)

    subparsers = parser.add_subparsers()

    # "configure" action
    parser_configure = subparsers.add_parser(
        'configure',
        help='Configure a new Cozy locally and register current'
             ' device remotely.'
    )
    parser_configure.set_defaults(func=actions.configure_new_device)

    parser_configure.add_argument(
        'url',
        help='URL of remote Cozy to sync'
    )
    parser_configure.add_argument(
        'device',
        help='Device name to choose to refer to the synchronized device'
    )
    parser_configure.add_argument(
        'path',
        help='Local path to choose where Cozy files will be mounted'
             ' (must be an existing directory)'
    )

    # "sync" action
    parser_sync = subparsers.add_parser(
        'sync',
        help='Synchronize current device with its remote Cozy.'
    )
    parser_sync.set_defaults(func=actions.sync)

    parser_sync.add_argument(
        'devices',
        nargs='*',
        help='Name of devices to sync'
    ).completer = DeviceCompleter

    # "unsync" action
    parser_kill = subparsers.add_parser(
        'unsync',
        help='Ask database to stop synchronization.'
    )
    parser_kill.set_defaults(func=actions.kill_running_replications)

    # "mount" action
    parser_mount = subparsers.add_parser(
        'mount',
        help='mount folder for current device.'
    )
    parser_mount.set_defaults(func=actions.mount_folder)

    parser_mount.add_argument(
        'devices',
        nargs='*',
        help='Name of synchronized devices to mount'
    ).completer = DeviceCompleter

    # "unmount" action
    parser_unmount = subparsers.add_parser(
        'unmount',
        help='unmount folder for current device.'
    )
    parser_unmount.set_defaults(func=actions.unmount_folder)

    parser_unmount.add_argument(
        'devices',
        nargs='*',
        help='Name of the synchronized device to unmount'
    ).completer = DeviceCompleter
    parser_unmount.add_argument(
        '-p', '--path',
        help='Path to unmount'
    )

    # "set_default" action
    parser_mount = subparsers.add_parser(
        'set_default',
        help='synchronize and mount device at startup'
    )
    parser_mount.set_defaults(func=actions.set_default)

    parser_mount.add_argument(
        'device',
        help='Name of the device to synchronize and mount at startup'
    ).completer = DeviceCompleter

    # "unset_default" action
    parser_mount = subparsers.add_parser(
        'unset_default',
        help='avoid device synchronization and mounting at startup'
    )
    parser_mount.set_defaults(func=actions.unset_default)

    parser_mount.add_argument(
        'devices',
        nargs='*',
        help='Name of synchronized devices to remove from startup'
    ).completer = DeviceCompleter

    # "display_config" action
    parser_display_conf = subparsers.add_parser(
        'display_config',
        help='Display configuration for remote cozy.'
    )
    parser_display_conf.set_defaults(func=actions.display_config)

    # "remove_config" action
    parser_rmconf = subparsers.add_parser(
        'remove_config',
        help='Remove device from local and remote configuration'
    )
    parser_rmconf.set_defaults(func=actions.remove_device)

    parser_rmconf.add_argument(
        'device',
        help='Name of the synchronized device'
    ).completer = DeviceCompleter

    # "reset" action
    parser_reset = subparsers.add_parser(
        'reset',
        help='Clear all data from local computer and remove '
             'current device remotely.'
    )
    parser_reset.set_defaults(func=actions.reset)

    # Initialize autocompletion
    argcomplete.autocomplete(parser)

    # Parse CLI arguments and execute related function
    args = parser.parse_args()
    args_dict = vars(args).copy()
    del args_dict['func']
    args.func(**args_dict)

if __name__ == "__main__":
    main()
