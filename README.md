CouchDB-FUSE
============

A FUSE interface to CouchDB. 


Requirements
------------

 * [Python FUSE bindings](http://fuse.sourceforge.net/)
 * [CouchDB-Python](http://code.google.com/p/couchdb-python/) 0.5 or greater

Usage
-----

    $ mkdir mnt
    $ couchmount http://localhost:5984/jasondavies/_design%2Flinks mnt/
    $ ls mnt/
    $ touch mnt/foo
    $ ls mnt/
    foo
    $ 

Happy Couching!
