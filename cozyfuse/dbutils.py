import json
import string
import random
import requests
import logging

import replication
import local_config


from couchdb import Server


def get_db(database):
    '''
    Get or create given database from/in CouchDB.
    '''
    try:
        server = Server('http://localhost:5984/')
        server.resource.credentials = local_config.get_db_credentials(database)
        db = server[database]
    except Exception:
        logging.exception('[DB] Cannot connect to the database')

        return None
    return db


def get_db_and_server(database):
    '''
    Get or create given database from/in CouchDB.
    '''
    try:
        server = Server('http://localhost:5984/')
        server.resource.credentials = local_config.get_db_credentials(database)
        db = server[database]
        return (db, server)
    except Exception:
        print('[DB] Cannot connect to the database')
        return (None, None)


def init_db(database):
    '''
    Create all required views to make Cozy FUSE working properly.
    '''
    replication.init_database(database)
    password = get_random_key()
    create_db_user(database, database, password)
    print '[DB] Local database initialized'
    return (database, password)


def remove_db(database):
    '''
    Destroy given database.
    '''
    (db, server) = get_db_and_server(database)
    server.delete(database)


def _create_device_view(db):
    '''
    Create CouchDB device design document to allow requesting on devices.
    '''
    db = get_db()
    if '_design/device' not in db:
        db["_design/device"] = {
            "views": {
                "all": {
                    "map": "function (doc) {\n" +
                           "    if (doc.docType === \"Device\") {\n" +
                           "        emit(doc.login, doc) \n    }\n}"
                }
            }
        }


def get_device(name):
    '''
    Get device corresponding to given name. Device is returned as a dict.
    '''
    try:
        device = list(get_db().view("device/all", key=name))[0]
    except IndexError:
        device = None
    return device


def get_random_key():
    '''
    Generate a random key of 20 chars. The first character is not a number
    because CouchDB does not link string that starts with a digit.
    '''
    chars = string.ascii_lowercase + string.digits
    random_val = ''.join(random.choice(chars) for x in range(19))
    return random.choice(string.ascii_lowercase) + random_val


def create_db_user(database, login, password, protocol="http"):
    '''
    Create a user for given *database*. User credentials are *login* and
    *password*.
    '''
    headers = {'content-type': 'application/json'}
    data = {
        "_id": "org.couchdb.user:%s" % login,
        "name": login,
        "type": "user",
        "roles": [],
        "password": password
    }
    requests.post('%s://localhost:5984/_users' % (protocol),
                  data=json.dumps(data),
                  headers=headers,
                  verify=False)

    headers = {'content-type': 'application/json'}
    data = {
       "admins": {
           "names": [login],
           "roles": []
        },
       "members": {
           "names": [login],
           "roles": []
        },
    }
    requests.put('%s://localhost:5984/%s/_security' % (protocol, database),
                 data=json.dumps(data),
                 headers=headers,
                 verify=False)
