import os
import random

import pyglet


class SoundHandler:
    def __init__(self, option_handler):
        self.sounds = {}
        self.music = {}

        path = os.path.join('data', 'sfx')
        for file in os.listdir(path):
            if file.endswith('wav'):
                self.sounds[file.split('.')[0]] = pyglet.media.load(os.path.join(path, file), streaming=False)

        path = os.path.join('data', 'music')
        for file in os.listdir(path):
            if file.endswith('mp3'):
                self.music[file.split('.')[0]] = pyglet.media.load(os.path.join(path, file))

        self.volume = 1.0
        self.set_volume(option_handler.sfx_volume)
        self.music_player = pyglet.media.player.Player()
        self.set_music_volume(option_handler.music_volume)

        self.track_list = list(self.music.keys())
        random.shuffle(self.track_list)
        self.play_track_list()
        self.music_player.on_player_eos = self.play_track_list

    def set_volume(self, vol):
        self.volume = vol / 100

    def set_music_volume(self, vol):
        self.music_player.volume = vol / 100

    def play_track_list(self):
        for track in self.track_list:
            self.music_player.queue(self.music[track])

        self.music_player.play()
