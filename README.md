# [Cozy](http://cozy.io) Fuse Linux

This programs allows you to mount files from your Cozy Files application in
your file system. This way you can browse and manage them with your favorite
file browser.


## Requirements

To run properly Cozy Fuse requires that you setup:

* a CouchDB instance running locally on your system.
* FUSE

On Debian like system you can simply add them via

    apt-get install couchdb fuse

## Installation

In a console run:

   pip install git+git@github.com:mycozycloud/cozy-fuse-linux.git


Configure your replication:

    # Configure once your cozy
    cozy-fuse configure -u https://mycozy.cozycloud.cc -n online-cozy -p /home/me/mycozyfolder
    cozy-fuse sync -n online -cozy # run it at each startup
    cozy-fuse mount -n online -cozy # run it at each startup

On Ubuntu you must add read rights on `/etc/fuse.conf`

    chmod a+r /etc/fuse.conf


## Troubleshootings

*File copy fails.*: It can be due to a bad initialization of your remote Cozy
Proxy. Restart your proxy, log in and retry.

## What is Cozy?

![Cozy
Logo](https://raw.github.com/mycozycloud/cozy-setup/gh-pages/assets/images/happycloud.png)

[Cozy](http://cozy.io) is a platform that brings all your web services in the
same private space.  With it, your web apps and your devices can share data
easily, providing you
with a new experience. You can install Cozy on your own hardware where no one
profiles you.

## Community

You can reach the Cozy Community by:

* Chatting with us on IRC #cozycloud on irc.freenode.net
* Posting on our
  [Forum](https://groups.google.com/forum/?fromgroups#!forum/cozy-cloud)
* Posting issues on the [Github repos](https://github.com/mycozycloud/)
* Mentioning us on [Twitter](http://twitter.com/mycozycloud)

