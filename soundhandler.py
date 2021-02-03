import os
import random

import pyglet


class MusicPlayer(pyglet.media.player.Player):
    def __init__(self):
        super().__init__()
        self.paused = True

    def play(self):
        if self.paused:
            super().play()
            self.paused = False

    def pause(self):
        if not self.paused:
            super().pause()
            self.paused = True


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
            if file.endswith('ogg'):
                self.music[file.split('.')[0]] = pyglet.media.load(os.path.join(path, file))

        self.volume = 1.0
        self.music_volume = 1.0

        self.set_volume(option_handler.sfx_volume)

        self.music_player = MusicPlayer()
        tracklist = ['break', 'chaos', 'line', 'scatter', 'steady']
        random.shuffle(tracklist)
        self.set_tracklist(self.music_player, tracklist)
        self.music_player.on_player_eos = lambda: self.set_tracklist(self.music_player, tracklist)

        self.menu_player = MusicPlayer()
        self.set_tracklist(self.menu_player, ['somber'])
        self.menu_player.on_player_eos = lambda: self.set_tracklist(self.menu_player, ['somber'])

        self.set_music_volume(option_handler.music_volume)

    def set_volume(self, vol):
        self.volume = (vol / 100)**2

    def set_music_volume(self, vol):
        self.music_volume = (vol / 100)**2
        self.music_player.volume = self.music_volume
        self.menu_player.volume = self.music_volume

    def set_tracklist(self, player, tracklist):
        for track in tracklist:
            player.queue(self.music[track])
        player.play()
