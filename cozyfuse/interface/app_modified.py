#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import wx
import gettext
from CozyFrame import CozyFrame, TaskBarIcon

if __name__ == "__main__":
    gettext.install("app") # replace with the appropriate catalog name

    app = wx.PySimpleApp(0)
    wx.InitAllImageHandlers()
    cozy_frame = CozyFrame(None, wx.ID_ANY, "")
    app.SetTopWindow(cozy_frame)
    cozy_frame.Show()
    TaskBarIcon()
    app.MainLoop()
