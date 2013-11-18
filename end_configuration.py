#!/usr/bin/python
from gi.repository import Gtk
import sys

class End:
    def __init__(self):  
        self.builder = Gtk.Builder()
        self.builder.add_from_file('end_ui.glade')

        window = self.builder.get_object("window")
        button = self.builder.get_object("ok")
        button.connect("clicked", self.on_button_clicked)
        window.show_all()

        Gtk.main()

    def on_button_clicked(self, widget):        
        Gtk.main_quit()
        sys.exit(0)

if __name__ == "__main__":
    End()	