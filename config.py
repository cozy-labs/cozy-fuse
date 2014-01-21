from kivy.app import App
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.progressbar import ProgressBar
from kivy.uix.textinput import TextInput
from kivy.properties import *
from requests import post
from replication import replicate_to_local, recover_progression, init_database, replicate_from_local_one_shot_without_deleted
from replication import init_device, replicate_from_local, replicate_to_local_one_shot_without_deleted, replicate_to_local_start_seq, replicate_from_local_start_seq
from couchdb import Database, Server
from kivy.clock import Clock
from threading import Thread

try:
    import simplejson as json
except ImportError:
    import json # Python 2.6
import sys
import signal


class TabTextInput(TextInput):
    '''
    TabTextInput rewrite TextInput to switch TextInput when user press tab or enter
    '''

    def __init__(self, *args, **kwargs):
        self.next = kwargs.pop('next', None)
        super(TabTextInput, self).__init__(*args, **kwargs)

    def set_next(self, next):
        '''
        Initialise next textinput
            next {TextInput}: next textinput on windows
        '''
        self.next = next

    def get_next(self):
        '''
        Return the next TextInput
        '''
        return self.next

    def _keyboard_on_key_down(self, window, keycode, text, modifiers):
        '''
        Catch keyboard events to force a switch between TextInput if necessary
        '''
        key, key_str = keycode
        if key in (9, 13):
            if self.next is not None:
                self.next.focus = True
                self.next.select_all()
        else:
            super(TabTextInput, self)._keyboard_on_key_down(window, keycode, text, modifiers)


class Configuration(AnchorLayout):
    '''
    Manage configuration window
    '''
    progress = ObjectProperty()
    url = TabTextInput()
    pwd = TabTextInput()
    name = TabTextInput()
    url.set_next(pwd)
    pwd.set_next(name)
    error = ObjectProperty()

    max_prog = 0

    def install(self):
        '''
        Install cozy-files: 
            * Add device in user's cozy
            * Replicate metadata from cozy to local 
            * Update device
            * Create replication filter
            * Replicate metadata from local to cozy
        '''
        url = self.url.text
        pwd = self.pwd.text
        name = self.name.text
        self.progress.value = 0
        if name is "" or pwd is "" or url is "":            
            self._display_error('Tous les champs doivent etre remplis')
            return
        url = self._normalize_url(url)
        if not url:        
            self._display_error("L'url de votre cozy n'est pas correcte")
            return      
        try:  
            data = {'login': name}
            req = post(url + '/device/', data=data, auth=('owner', pwd)) 
            if req.status_code == 401:
                self._display_error("""L'url et le mot de passe de votre cozy 
                            ne correspondent pas""")
                return
            elif req.status_code == 400:
                self._display_error('Ce nom est deja utilise par un autre device')
                return
        except Exception, e:
            print e
            self._display_error("Verifiez l'url de votre cozy")
            return

        Clock.schedule_interval(self.progress_bar, 1/25)
        thread_configure = Thread(target=self.configure, args=(url, pwd, name, req))
        thread_configure.start()


    def configure(self, url, pwd, name, req):
        '''
        Configure cozy-files
            url  {string}: cozy url
            pwd  {string}: cozy password
            name {string}: device name
            req  {object}: response of request to add device in cozy
        '''
        self.max_prog = 0.1
        self._display_error("")
        init_database() 
        self.max_prog = 0.15
        data = json.loads(req.content)
        repli = replicate_to_local_one_shot_without_deleted(url, name, data['password'], data['id'])   
        self.max_prog = 0.30  
        replicate_to_local_start_seq(url, name, data['password'], data['id'], repli['source_last_seq'])   
        self.max_prog = 0.98
        err = init_device(url, data['password'], data['id'])
        if err:
            self._display_error(err)
            return             
        replicate_from_local(url, name, data['password'], data['id'])
        pass
      
    def progress_bar(self, dt):
        '''
        Update progress bar
        '''
        if self.max_prog < 0.31:
            self.progress.value = 100 * self.max_prog
        else:
            progress = recover_progression()
            if progress > 0.98:
                sys.exit(0)
                return False
            self.progress.value = 30 + 70*progress

    def _normalize_url(self, url):
        '''
        Normalize url
            url {string}: cozy url
        '''
        url_parts = url.split('/')
        for part in url_parts:
            if part.find('cozycloud.cc') is not -1:
                return 'https://%s' %part
        return False

    def _display_error(self, error):
        '''
        Display error
            error {string}: message to display
        '''
        self.error.text = error
        self.error.texture_update()
        self.error.anchors


class ConfigurationApp(App):
    def build(self):
        return Configuration()


if __name__ == '__main__':
    ConfigurationApp().run()