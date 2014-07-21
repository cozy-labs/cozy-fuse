import sys
import os
import pytest

sys.path.append('..')

import cozy-fuse.local_config as local_config

local_config.CONFIG_FOLDER = \
    os.path.join(os.path.expanduser('~'), '.cozyfuse-test')

local_config.CONFIG_PATH = \
    os.path.join(local_config.CONFIG_FOLDER, 'config.yaml')


def touch(filename, times=None):
    with file(filename, 'a'):
        os.utime(filename, times)


@pytest.fixture(scope="module")
def config_file(request):
    if not os.path.isdir(local_config.CONFIG_FOLDER):
        os.mkdir(local_config.CONFIG_FOLDER)

    if os.path.isfile(local_config.CONFIG_PATH):
        os.remove(local_config.CONFIG_PATH)
    touch(local_config.CONFIG_PATH)


def test_get_full_config(config_file):
    config = local_config.get_full_config()
    assert {} == config


def test_add_config(config_file):
    name = 'test-device'
    url = 'https://localhost:2223'
    path = '/home/myself/cozyfiles'
    db_login = 'login'
    db_password = 'password'
    local_config.add_config(name, url, path, db_login, db_password)

    res = {
        'test-device': {
            'url': url,
            'path': path,
            'dblogin': db_login,
            'dbpassword': db_password,
        }
    }
    assert res == local_config.get_full_config()


def test_get_config(config_file):
    res = ('https://localhost:2223', '/home/myself/cozyfiles')
    assert res == local_config.get_config('test-device')


def test_get_db_credentials(config_file):
    res = ('login', 'password')
    assert res == local_config.get_db_credentials('test-device')


def test_set_get_device_config(config_file):
    local_config.set_device_config('test-device', 'remoteid', 'remotepassword')
    res = ('remoteid', 'remotepassword')
    assert res == local_config.get_device_config('test-device')


def test_no_config(config_file):
    pytest.raises(local_config.NoConfigFound,
                  local_config.get_config,
                  'test-no-device')


def test_clear_config(config_file):
    local_config.clear()
    assert False == os.path.isfile(local_config.CONFIG_PATH)
