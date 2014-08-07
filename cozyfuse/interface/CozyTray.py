# -*- coding: UTF-8 -*-

import wx

TRAY_TOOLTIP = 'Cozy'
TRAY_ICON = 'icon/icon.png'
SMALL_TRAY_ICON = 'icon/small_icon.png'


def create_menu_item(menu, label, func):
    item = wx.MenuItem(menu, -1, label)
    menu.Bind(wx.EVT_MENU, func, id=item.GetId())
    menu.AppendItem(item)
    return item


class CozyTray(wx.TaskBarIcon):
    def __init__(self):
        super(CozyTray, self).__init__()
        self.set_icon(TRAY_ICON)
        self.Bind(wx.EVT_TASKBAR_LEFT_DOWN, self.on_left_down)

    def CreatePopupMenu(self):
        menu = wx.Menu()
        create_menu_item(menu, 'Say Hello', self.on_hello)
        menu.AppendSeparator()
        create_menu_item(menu, 'Exit', self.on_exit)
        return menu

    def set_icon(self, path):
        icon = wx.IconFromBitmap(wx.Bitmap(path))
        self.SetIcon(icon, TRAY_TOOLTIP)

    def on_left_down(self, event):
        print 'Tray icon was left-clicked.'

    def on_hello(self, event):
        self.set_icon(SMALL_TRAY_ICON)
        print 'Hello, world!'

    def on_exit(self, event):
        wx.CallAfter(self.Destroy)
