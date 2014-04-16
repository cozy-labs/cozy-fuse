import pytest
import sys
import os

sys.path.append('..')

import cozyfuse.local_config as local_config
local_config.CONFIG_PATH = \
    os.path.join(os.path.expanduser('~'), '.cozyfuse-test')

import cozyfuse.dbutils as dbutils

TESTDB = 'cozy-fuse-test'


@pytest.fixture(scope="module")
def config_db(request):
    filename = local_config.CONFIG_PATH
    with file(filename, 'a'):
        os.utime(filename, None)

    name = TESTDB
    url = 'https://localhost:2223'
    path = '/home/myself/cozyfiles'
    db_login = 'login'
    db_password = 'password'
    local_config.add_config(name, url, path, db_login, db_password)


def test_get_db(config_db):
    db = dbutils.get_db(TESTDB)
    assert db is not None


def get_db_and_server():
    pass

def init_db():
    pass


def remove_db():
    pass


def _create_device_view():
    pass


def get_device():
    pass


def get_random_key():
    pass


def create_db_user():
    local_config.clear()
