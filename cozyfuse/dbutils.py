import replication

from couchdb import Server


def get_db(database):
    '''
    Get or create given database from/in CouchDB.
    '''
    try:
        server = Server('http://localhost:5984/')
        db = server[database]
    except Exception:
        print('Cannot connect to the database')
        return None
    return db


def init_db(database):
    '''
    Create all required views to make Cozy FUSE working properly.
    '''
    replication.init_database(database)
    print 'Local database initialized'


def remove_db(database):
    '''
    Destroy given database.
    '''
    server = Server('http://localhost:5984/')
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
