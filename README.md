# [Cozy](http://cozy.io) Fuse client

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

On FreeBSD 10:
* `sudo pkg install couchdb`
* `sudo kldload fuse.ko`
* You will have to run all the cozy-fuse client's command as root in order to make it work properly (for now)

## Installation

In a console run:

    (sudo) pip install git+https://@github.com/cozy/cozy-fuse.git

On OSX, if this error occured: `error: command 'cc' failed with exit status 1`, try again with the following command:

    ARCHFLAGS=-Wno-error=unused-command-line-argument-hard-error-in-future pip install git+https://github.com/cozy/cozy-fuse.git

On OSX and FreeBSD, you must start couchdb in a terminal or daemonize it by yourself:

    couchdb

Configure your connection with the remote Cozy:

    cozy-fuse configure <url_of_your_cozy> <name_of_your_device> <sync_directory>

For example:

    cozy-fuse configure https://mycozy.cozycloud.cc laptop /home/me/cozy_sync

The configurator will ask you if you want to set the newly configured device as "default", and if you want to start the synchronization right away. You will be able to execute it afterward with these commands:

    cozy-fuse sync laptop
    (sudo) cozy-fuse mount laptop

## Permission issues

On Ubuntu you must add read rights on `/etc/fuse.conf`

    (sudo) chmod a+r /etc/fuse.conf

On FreeBSD, you may want to get inpiration from this tutorial in order to allow users to mount their own synchronized folder:

http://blog.ataboydesign.com/2014/04/23/freebsd-10-mounting-usb-drive-with-ext4-filesystem/


## Tab completion

In order to activate tab completion in CLI, you have to execute this command, or add it to your ~/.bashrc or ~/.zshrc file:

    sudo activate-global-python-argcomplete
    python-argcomplete-check-easy-install-script /usr/local/bin/cozy-fuse
    # OR
    eval "$(register-python-argcomplete cozy-fuse/__main__.py)"


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

