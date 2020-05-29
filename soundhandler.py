import os

import pyglet


class SoundHandler:
    def __init__(self):
        self.sounds = {}
        self.music = {}
        self.current_track = ''
        path = os.path.join('data', 'sfx')

        for file in os.listdir(path):
            if file.endswith('wav'):
                self.sounds[file.split('.')[0]] = pyglet.media.load(os.path.join(path, file), streaming=False)

        path = os.path.join('data', 'music')

        for file in os.listdir(path):
            if file.endswith('mp3'):
                self.music[file.split('.')[0]] = pyglet.media.load(os.path.join(path, file))

        self.set_music_volume(1.0)
        #self.set_music('chaos')

    def set_volume(self, vol):
        return
        for sound in self.sounds.values():
            sound.set_volume(0.5 * vol / 100)

    def set_music_volume(self, vol):
        return
        pygame.mixer.music.set_volume(0.5 * vol / 100)

    def set_music(self, track):
        if self.current_track != track:
            self.music[track].play()
            self.current_track = track
