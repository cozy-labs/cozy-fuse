# -*- coding: UTF-8 -*-

import wx
import os
import sys

from CozyFrame import getProgramFolder

TRAY_TOOLTIP = 'Cozy'
TRAY_ICON = os.path.join(getProgramFolder(), "icon/icon.png")
SMALL_TRAY_ICON = os.path.join(getProgramFolder(), "icon/small_icon.png")

# Helper to add menu item
def create_menu_item(menu, label, func):
    item = wx.MenuItem(menu, -1, label)
    menu.Bind(wx.EVT_MENU, func, id=item.GetId())
    menu.AppendItem(item)
    return item

class CozyTray(wx.TaskBarIcon):
    def __init__(self):
        super(CozyTray, self).__init__()
        self.set_icon(TRAY_ICON)
        # Temporarily bind an event on tray icon click
        self.Bind(wx.EVT_TASKBAR_LEFT_DOWN, self.on_left_down)

    def CreatePopupMenu(self):
        # Initialize Menu
        menu = wx.Menu()
        create_menu_item(menu, 'Configure', self.on_configure)
        menu.AppendSeparator()
        create_menu_item(menu, 'Exit', self.on_exit)
        return menu

    def SetMainFrame(self, frame):
        self.frame = frame

    def set_icon(self, path):
        icon = wx.IconFromBitmap(wx.Bitmap(path))
        self.SetIcon(icon, TRAY_TOOLTIP)

    def on_left_down(self, event):
        pass
        #self.set_icon(SMALL_TRAY_ICON)
        #print 'Tray icon was changed.'

    def on_configure(self, event):
        # Show dialog window
        self.frame.Show()

    def on_exit(self, event):
        sys.exit(0)
