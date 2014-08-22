#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import sys
import wx
import gettext
import socket
from cozyfuse.local_config import get_full_config, NoConfigFile
from CozyFrame import CozyFrame
from CozyTray import CozyTray

def start():
    gettext.install("app") # replace with the appropriate catalog name

    app = wx.PySimpleApp(0)
    wx.InitAllImageHandlers()

    # Initialize dialog window and tray menu
    cozy_frame = CozyFrame(None, wx.ID_ANY, "")
    cozy_tray = CozyTray()

    # Get them know each other
    cozy_frame.SetMainTray(cozy_tray)
    cozy_tray.SetMainFrame(cozy_frame)

    # Set the dialog window as top window
    app.SetTopWindow(cozy_frame)

    # Set default values
    cozy_frame.text_device_name.SetValue(socket.gethostname().replace('.', '_').replace('-', '_').lower())
    cozy_frame.text_sync_folder.SetValue('%s/cozy' % (os.path.expanduser("~")))

    try:
        # Fetch configuration and select the first device
        config = get_full_config().itervalues().next()

        # Fill the dialog window with configuration values
        cozy_frame.text_cozy_password.SetValue('aaaaa')
        if 'dblogin' in config:
            cozy_frame.text_device_name.SetValue(config['dblogin'])
        if 'url' in config:
            cozy_frame.text_cozy_url.SetValue(config['url'])
        if 'path' in config:
            cozy_frame.text_sync_folder.SetValue(config['path'])

        # Indicate that Cozy is already configured to the dialog window
        if 'deviceid' in config:
            cozy_frame.SetConfigured(True)

    except NoConfigFile:
        # If no config file exists, show the dialog window
        cozy_frame.Show()

    app.MainLoop()

if __name__ == "__main__":
    start()
