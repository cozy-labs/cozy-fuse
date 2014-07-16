# [Cozy](http://cozy.io) Fuse Linux

This programs allows you to mount files from your Cozy Files application in
your file system. This way you can browse and manage them with your favorite
file browser.


## Requirements

To run properly Cozy Fuse requires that you setup:

* a CouchDB instance running locally on your system.
* FUSE

On Debian like system you can simply add them via

    apt-get install couchdb fuse python-dev python-fuse libfuse-dev libgl1-mesa-dev python-setuptools python-pip git

On OSX:
* `brew install couchdb` (Homebrew) or `sudo port install couchdb && sudo port update couchdb && sudo port load couchdb` (MacPorts)
* Download and install [OSXFuse](http://osxfuse.github.io/)

## Installation

In a console run:

    pip install git+https://@github.com/mycozycloud/cozy-fuse-linux.git

On OSX, if this error occured: `error: command 'cc' failed with exit status 1`, try again with the following command:

    ARCHFLAGS=-Wno-error=unused-command-line-argument-hard-error-in-future pip install git+https://github.com/mycozycloud/cozy-fuse-linux.git

On OSX, you must start couchdb in a terminal or daemonize it by yourself:

    couchdb
    
Create an empty sync directory:

    mkdir /home/me/cozy_sync

Configure your connection with the remote Cozy:

    cozy-fuse configure -u <url_of_your_cozy> -n <name_of_your_device> -p <sync>
    
For example:

    cozy-fuse configure -u https://mycozy.cozycloud.cc -n laptop -p /home/me/cozy_sync

Then starts synchronization and mount your target folder (both commands must
be run at each startup):

    cozy-fuse sync -n laptop
    cozy-fuse mount -n laptop

On Ubuntu you must add read rights on `/etc/fuse.conf`

    chmod a+r /etc/fuse.conf

On OSX, you must start CouchDB manually in a terminal, simply type `couchdb`


## Troubleshootings

*File copy fails.*: It can be due to a bad initialization of your remote Cozy
Proxy. Restart your proxy, log in and retry.

*Where to find logs?*: Local logs are stored in ~/.cozyfuse/cozyfuse.log .

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

