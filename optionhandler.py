from configparser import ConfigParser


class OptionHandler:
    def __init__(self):
        self.config = ConfigParser()

        self.fps = 120
        self.resolution = (1280, 720)
        self.vsync = False
        self.fullscreen = False
        self.sfx_volume = 100
        self.music_volume = 0
        self.shadows = True
        self.dust = True

        self.debug_draw = False

        try:
            self.load()
        except:
            self.save()

    def save(self):
        self.config.read('config.ini')

        if not self.config.has_section('video'):
            self.config.add_section('video')

        self.config.set('video', 'fps', str(self.fps))
        self.config.set('video', 'horizontal resolution', str(self.resolution[0]))
        self.config.set('video', 'vertical resolution', str(self.resolution[1]))
        self.config.set('video', 'fullscreen', str(self.fullscreen))

        if not self.config.has_section('audio'):
            self.config.add_section('audio')

        self.config.set('audio', 'sfx volume', str(self.sfx_volume))
        self.config.set('audio', 'music volume', str(self.music_volume))

        if not self.config.has_section('performance'):
            self.config.add_section('performance')

        self.config.set('performance', 'shadows', str(self.shadows))
        self.config.set('performance', 'dust', str(self.dust))

        with open('config.ini', 'w') as f:
            self.config.write(f)

    def load(self):
        self.config.read('config.ini')

        self.fps = self.config.getint('video', 'fps')
        self.resolution = tuple([self.config.getint('video', 'horizontal resolution'),
                                 self.config.getint('video', 'vertical resolution')])
        self.fullscreen = self.config.getboolean('video', 'fullscreen')

        self.sfx_volume = self.config.getint('audio', 'sfx volume')
        self.music_volume = self.config.getint('audio', 'music volume')

        self.shadows = self.config.getboolean('performance', 'shadows')
        self.dust = self.config.getboolean('performance', 'dust')
