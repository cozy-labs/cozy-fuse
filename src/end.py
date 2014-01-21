from kivy.app import App
from kivy.uix.anchorlayout import AnchorLayout
from kivy.properties import *
import time
import sys

class End(AnchorLayout):
    '''
    Manage end window
    '''

    def end(self):
        '''
        End configuration
        '''
        sys.exit(0)


class EndApp(App):
    def build(self):
        end = End()


if __name__ == '__main__':
    EndApp().run()