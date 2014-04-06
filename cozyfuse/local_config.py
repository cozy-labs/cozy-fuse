import os

from yaml import load, dump
from yaml import Loader


CONFIG_PATH = os.path.join(os.path.expanduser('~'), '.cozyfuse')


def add_config(name, url, path, db_login, db_password):
    '''
    Add to the config file (~/.cozyfuse) device named *name* with *url* and
    *path* as parameters.
    '''

    if name is None or url is None or path is None:
        print 'Name, URL or path is missing'

    else:
        try:
            config_file = file(CONFIG_PATH, 'r')
        except IOError:
            config_file = None
            print 'No config file (~/.cozyfuse), create a new one.'

        if config_file is not None:
            config = load(config_file, Loader=Loader)
            config_file.close()
        else:
            config = {}

        config[name] = {
            'url': url,
            'path': path,
            'dblogin': db_login,
            'dbpassword': db_password,
        }

        output_file = file(CONFIG_PATH, 'w')
        print dump(config, default_flow_style=False)
        dump(config, output_file, default_flow_style=False)

        print 'Configuration saved'


def get_config(name):
    '''
    Get configuration of device *name* from configuration file.
    '''
    try:
        stream = file(CONFIG_PATH, 'r')
    except IOError:
        print 'Config file (~/.cozyfuse) does not exist.'
        return None

    data = load(stream, Loader=Loader)

    for key in data.keys():
        if key == name:
            url = data[key]['url']
            path = data[key]['path']

    return (url, path)


def get_device_config(name):
    try:
        stream = file(CONFIG_PATH, 'r')
    except IOError:
        print 'Config file (~/.cozyfuse) does not exist.'
        return None

    data = load(stream, Loader=Loader)

    for key in data.keys():
        if key == name:
            try:
                device_id = data[key]['deviceid']
            except KeyError:
                device_id = None
            try:
                device_password = data[key]['devicepassword']
            except KeyError:
                device_password = None

    return (device_id, device_password)


def get_db_credentials(name):
    try:
        stream = file(CONFIG_PATH, 'r')
    except IOError:
        print 'Config file (~/.cozyfuse) does not exist.'
        return None

    data = load(stream, Loader=Loader)

    for key in data.keys():
        if key == name:
            db_login = data[key]['dblogin']
            db_password = data[key]['dbpassword']

    return (db_login, db_password)


def get_full_config():
    '''
    Get config (~/.cozyfuse) file as a dict.
    '''
    try:
        stream = file(CONFIG_PATH, 'r')
    except IOError:
        print 'Config file (~/.cozyfuse) does not exist.'
        return None

    return load(stream, Loader=Loader)


def save_remote_data_to_config(name, device_id, device_password):
    '''
    Save data coming from the remote server to the configuration file.
    '''
    try:
        config_file = file(CONFIG_PATH, 'r')
    except IOError:
        config_file = None
        print 'No config file (~/.cozyfuse), create a new one.'

    if config_file is not None:
        config = load(config_file, Loader=Loader)
        config_file.close()
    else:
        print 'No device is registered for this name'

    config[name]['deviceid'] = device_id
    config[name]['devicepassword'] = device_password

    output_file = file(CONFIG_PATH, 'w')
    dump(config, output_file, default_flow_style=False)
    print 'Remote data added to config file'


def clear():
    '''
    Delete configuration file
    '''
    config_path = os.path.join(os.path.expanduser('~'), '.cozyfuse')
    os.remove(config_path)
