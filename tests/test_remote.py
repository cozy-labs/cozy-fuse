import pytest
import sys
import os
import httpretty


sys.path.append('..')

import cozyfuse.local_config as local_config
local_config.CONFIG_FOLDER = \
    os.path.join(os.path.expanduser('~'), '.cozyfuse-test')

local_config.CONFIG_PATH = \
    os.path.join(local_config.CONFIG_FOLDER, 'config.yaml')


import cozyfuse.remote as remote

TESTDB = 'cozy-fuse-test'


@pytest.fixture(scope="module")
def config_db(request):
    # Create config folder and YAML file if not exist
    if not os.path.isdir(local_config.CONFIG_FOLDER):
        os.mkdir(local_config.CONFIG_FOLDER)
    with open(local_config.CONFIG_PATH, 'a'):
        os.utime(local_config.CONFIG_PATH, None)

    name = TESTDB
    url = 'https://localhost:2223'
    path = '/home/myself/cozyfiles'
    db_login = 'login'
    db_password = 'password'
    local_config.add_config(name, url, path, db_login, db_password)


def test_register_device(config_db):
    httpretty.enable()
    url = "http://localhost:2223"
    httpretty.register_uri(httpretty.POST, url + '/device/' ,
                           body='{"id":"123","password":"456"}')
    (device_id, device_password) = remote.register_device(TESTDB, url, '/path', 'test')
    assert device_id == '123'
    assert device_password == '456'


def test_remove_device():
    url = "http://localhost:2223"
    httpretty.register_uri(httpretty.DELETE, url + '/device/123/', status=204)
    response = remote.remove_device(url, '123', '456')
    assert response.status_code == 204

    httpretty.disable()
    httpretty.reset()
