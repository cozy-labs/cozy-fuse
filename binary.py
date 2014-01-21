from kivy.app import App
from kivy.uix.anchorlayout import AnchorLayout
from kivy.properties import *
from replication import recover_progression_binary
from kivy.clock import Clock
import sys

class Binary(AnchorLayout):
    '''
    Manage binaries download window
    '''
    progress = ObjectProperty()

    def init(self):
        '''
        Initialize class
        '''       
        Clock.schedule_interval(self.progress_bar, 1/25)
        pass

    def progress_bar(self, dt):
        '''
        Update progress bar
        '''
        progress = recover_progression_binary()
        print progress
        print self.progress.value
        if progress == 1.0:
            self.progress.value = 100
            sys.exit(0)
            return False
        self.progress.value = 5 + 95*progress


class BinaryApp(App):
    def build(self):
        bin = Binary()
        bin.init()


if __name__ == '__main__':
    BinaryApp().run()