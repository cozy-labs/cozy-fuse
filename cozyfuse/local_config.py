import os
import daemon
import lockfile
import logging

from yaml import load, dump
from yaml import Loader


CONFIG_FOLDER = os.path.join(os.path.expanduser('~'), '.cozyfuse')
# Create config folder if it doesn't exist.
if not os.path.isdir(CONFIG_FOLDER):
    os.mkdir(CONFIG_FOLDER)

CONFIG_PATH = os.path.join(CONFIG_FOLDER, 'config.yaml')

HDLR = logging.FileHandler(os.path.join(CONFIG_FOLDER, 'cozyfuse.log'))
HDLR.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))

logger = logging.getLogger(__name__)


class NoConfigFound(Exception):
    pass


class NoConfigFile(Exception):
    pass


class DaemonAlreadyRunning(Exception):
    pass


def add_config(name, url, path, db_login, db_password):
    '''
    Add to the config file (~/.cozyfuse/config.yaml) device named *name* with
    *url* and *path* as parameters.
    '''

    if name is None or url is None or path is None:
        print 'Name, URL or path is missing'

    else:
        # Create config file if it doesn't exist
        if not os.path.isfile(CONFIG_PATH):
            with file(CONFIG_PATH, 'a'):
                os.utime(CONFIG_PATH, None)

        config = get_full_config()
        config[name] = {
            'url': url,
            'path': path,
            'dblogin': db_login,
            'dbpassword': db_password,
        }

        output_file = file(CONFIG_PATH, 'w')
        dump(config, output_file, default_flow_style=False)
        logger.info('[Config] Configuration for %s saved' % name)


def remove_config(name):
    '''
    Add to the config file (~/.cozyfuse/config.yaml) device named *name* with
    *url* and *path* as parameters.
    '''
    config = get_full_config()
    config.pop(name, None)
    output_file = file(CONFIG_PATH, 'w')
    dump(config, output_file, default_flow_style=False)

    folder = os.path.join(CONFIG_FOLDER, name)
    if os.path.isdir(folder):
        os.rmdir(folder)
    logger.info('[Config] Configuration for %s removed' % name)


def get_config(name):
    '''
    Get configuration of device *name* from configuration file.
    '''
    config = get_full_config()

    if name not in config:
        raise NoConfigFound('[Config] No device is registered for %s' % name)

    else:
        url = config[name]['url']
        path = config[name]['path']
        return (url, path)


def get_device_config(name):
    '''
    Return device id and password on remote Cozy for given device name.
    '''
    config = get_full_config()

    if name not in config:
        raise NoConfigFound('[Config] No device is registered for %s' % name)

    else:
        try:
            device_id = config[name]['deviceid']
        except KeyError:
            device_id = None
        try:
            device_password = config[name]['devicepassword']
        except KeyError:
            device_password = None

        return (device_id, device_password)


def set_device_config(name, device_id, device_password):
    '''
    Save data coming from the remote server to the configuration file.
    '''
    config = get_full_config()

    if name not in config:
        raise NoConfigFound('[Config] No device is registered for %s' % name)

    else:
        config[name]['deviceid'] = device_id
        config[name]['devicepassword'] = device_password

        output_file = file(CONFIG_PATH, 'w')
        dump(config, output_file, default_flow_style=False)
        logger.info('[Config] Remote data added to config file')


def get_startup_config(name):
    '''
    Return automatic startup configuration
    '''
    config = get_full_config()

    if name not in config:
        raise NoConfigFound('[Config] No device is registered for %s' % name)

    return 'startup' in config[name] and config[name]['startup']


def set_startup_config(name, automatic_startup):
    '''
    Set automatic startup configuration
    '''
    config = get_full_config()

    if name not in config:
        raise NoConfigFound('[Config] No device is registered for %s' % name)

    config[name]['startup'] = automatic_startup

    output_file = file(CONFIG_PATH, 'w')
    dump(config, output_file, default_flow_style=False)
    logger.info('[Config] Remote data added to config file')


def get_startup_devices():
    '''
    Return a list of devices to synchronize and mount at startup
    '''
    config = get_full_config()

    if len(config) > 0:
        return [name for name, conf in config.items()
                if 'startup' in conf and conf['startup']]
    else:
        return []


def get_db_credentials(name):
    '''
    Extract DB credentials from config file.
    '''
    config = get_full_config()

    if name not in config:
        raise NoConfigFound('[Config] No device is registered for %s' % name)
    else:
        db_login = config[name]['dblogin']
        db_password = config[name]['dbpassword']

    return (db_login, db_password)


def get_full_config():
    '''
    Get config (~/.cozyfuse/config.yaml) file as a dict.
    '''
    try:
        stream = file(CONFIG_PATH, 'r')
    except IOError:
        msg = '[Config] Config file %s does not exist.' % CONFIG_PATH
        raise NoConfigFile(msg)

    config = load(stream, Loader=Loader)
    stream.close()

    if config is None:
        return {}
    else:
        return config


def clear():
    '''
    Delete configuration file.
    '''
    os.remove(CONFIG_PATH)


def get_daemon_context(device_name, daemon_name, files_preserve=[]):
    '''
    Return a proper daemon context:
    * create a working directory for the daemon ~/.cozyfuse/device_name.
    * save and lock this pid in this folder.
    '''
    folder = os.path.join(CONFIG_FOLDER, device_name)
    pidfile = '%s.pid' % daemon_name

    if not os.path.isdir(folder):
        os.mkdir(folder)

    if os.path.isfile(pidfile):
        raise DaemonAlreadyRunning(
            'Daemon %s for % is already running' % (daemon_name, device_name))

    return daemon.DaemonContext(
        working_directory=folder,
        pidfile=lockfile.FileLock(os.path.join(folder, pidfile))
        # files_preserve=files_preserve,
    )


def configure_logger(log):
    log.addHandler(HDLR)
    log.setLevel(logging.INFO)
    log.propagate = False
