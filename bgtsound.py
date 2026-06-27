# -*- coding: utf-8 -*-
# BGT-ish Sound_lib wrapper
# Original author: Carter Temm
# Edited by Yukio Nozawa <personal@nyanchangames.com>
# License: GPL V2.0 (See copying.txt for details)

import math
import sound_lib
import sound_lib.output
import sound_lib.sample
from sound_lib import stream
from sound_lib.external.pybass import BASS_SetConfig, BASS_CONFIG_GVOL_SAMPLE
from sound_lib.main import BassError
from dialog import dialog
o = sound_lib.output.Output()


def setGlobalSfxVolume(value):
    """Sets the global volume of every sample-based sound effect.

    ``value`` uses the same decibel-like unit as ``sound.volume`` (0 means full
    volume, negative values are quieter). This affects all sound effects at once
    because they are loaded as BASS samples, while background music and the intro
    are played as streams and are therefore unaffected."""
    # Standard decibel-to-amplitude conversion (0 dB -> 1.0, -20 dB -> 0.1).
    linear = 10 ** (float(value) / 20)
    # BASS global sample volume ranges from 0 (silent) to 10000 (full).
    BASS_SetConfig(BASS_CONFIG_GVOL_SAMPLE, int(round(linear * 10000)))


class sound():
    def __init__(self):
        self.handle = None
        self.freq = 44100
        self.paused = False

    def stream(self, filename=""):
        if self.handle:
            self.close()
# end close previous
        self.handle = stream.FileStream(file=filename)
        self.freq = self.handle.get_frequency()

    def load(self, sample=None):
        if self.handle:
            self.close()
# end close previous
        try:
            self.handle = sound_lib.sample.SampleBasedChannel(sample)
        except BassError:
            # No free channel was available (e.g. a huge number of enemies are
            # playing the same sound at once). Degrade gracefully by skipping
            # this sound instead of crashing the game.
            self.handle = None
            return
        self.freq = self.handle.get_frequency()

    def play(self):
        if not self.handle:
            return
        self.handle.looping = False
        self.handle.play()

    def setPaused(self, p):
        if self.paused == p:
            return
        if not self.playing and p:
            return
        self.paused = p
        if p:
            self.handle.pause()
        else:
            self.handle.play()
        # end pause or unpause
    # end setPaused

    def play_wait(self):
        if not self.handle:
            return
        self.handle.looping = False
        self.handle.play_blocking()

    def play_looped(self):
        if not self.handle:
            return
        self.handle.looping = True
        self.handle.play()

    def stop(self):
        if self.handle and self.handle.is_playing:
            self.handle.stop()
            self.handle.set_position(0)

    def fadeout(self, fadetime):
        """The faded sound might be kept playing internally. Make sure that you call stop() before fading in or playing again. Fading will be performed by BASS's internal thread, so playing this instance after calling fadeout() may sound strangely."""
        if self.handle and self.handle.is_playing:
            self.handle.slide_attribute("volume", 0, fadetime)

    @property
    def volume(self):
        if not self.handle:
            return False
        return round(math.log10(self.handle.volume) * 20)

    @volume.setter
    def volume(self, value):
        if not self.handle:
            return False
        self.handle.set_volume(10**(float(value) / 20))

    @property
    def pitch(self):
        if not self.handle:
            return False
        return (self.handle.get_frequency() / self.freq) * 100

    @pitch.setter
    def pitch(self, value):
        if not self.handle:
            return False
        if value < 1:
            value = 1
        # No upper ceiling is enforced here; callers are responsible for
        # capping the pitch before assigning (e.g. ssAppMain.MUSIC_PITCH_MAX).
        try:
            self.handle.set_frequency((float(value) / 100) * self.freq)
        except BassError:
            # The requested frequency is beyond what the audio engine supports.
            # Keep the previous (highest achievable) frequency rather than
            # crashing, so the pitch can keep climbing as far as possible.
            pass

    @property
    def pan(self):
        if not self.handle:
            return False
        return self.handle.get_pan() * 100

    @pan.setter
    def pan(self, value):
        if not self.handle:
            return False
        self.handle.set_pan(float(value) / 100)

    @property
    def playing(self):
        if self.handle is None:
            return False
        try:
            s = self.handle.is_playing
        except BassError:
            return False
        # end try
        return s

    @property
    def stopped(self):
        """True only when the channel has genuinely finished/stopped playing.

        Unlike ``not playing`` this returns False while the channel is merely
        stalled (its buffer momentarily ran dry, which happens at very high
        pitch and is automatically resumed by BASS) or paused. Callers that
        decide whether a track has ended should use this so a temporary stall
        is not mistaken for the end of the track."""
        if self.handle is None:
            return True
        try:
            return self.handle.is_stopped
        except BassError:
            return True

    def close(self):
        if self.handle:
            self.handle.free()

# helper functions


def playOneShot(sample, vol=0, pitch=100):
    s = sound()
    s.load(sample)
    s.volume = vol
    s.pitch = pitch
    s.play()
