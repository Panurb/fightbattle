import os

import pygame


def load_sound(path):
    try:
        sound = pygame.mixer.Sound(path)
    except pygame.error as message:
        raise SystemExit(message)

    return sound


class SoundHandler:
    def __init__(self):
        self.volume = 1
        self.sounds = {}
        self.current_track = ''
        path = os.path.join('data', 'sfx')

        for file in os.listdir(path):
            if file.endswith('wav'):
                self.sounds[file.split('.')[0]] = load_sound(os.path.join(path, file))

        self.set_music_volume(1.0)

    def set_volume(self, vol):
        self.volume = vol
        for sound in self.sounds.values():
            sound.set_volume(0.5 * vol)

    def set_music_volume(self, vol):
        pygame.mixer.music.set_volume(vol)

    def set_music(self, track):
        if self.current_track != track:
            if track == '':
                pygame.mixer.music.fadeout(1000)
            else:
                path = os.path.join('data', 'music', f'{track}.mp3')
                pygame.mixer.music.load(path)
                pygame.mixer.music.play(-1)
            self.current_track = track
