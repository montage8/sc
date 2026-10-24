# -*- coding: utf-8 -*-
# Screaming Strike "Rewind" (fast-forward) controller
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# License: GPL V2.0 (See copying.txt for details)

"""This module contains the controller which drives the "Rewind" nasty item.

Obtaining a rewind item fast-forwards the entire game instead of only the
music: the background music, every sound effect (enemies, items, punches and
so on) and the in-game time itself are accelerated together, so everything
both happens faster and sounds higher-pitched at the same rate.

The pitch climbs for about itemConstants.REWIND_RAMP_TIME milliseconds, at
exactly the same rate as the music pitch descends when a game ends (see
ssAppMain.resetMusicPitch), and it glides back down at the same rate when the
acceleration ends.

The controller is a singleton because the acceleration is global. Several
rewind effects can be active at the same time (they are duplicated like the
other nasty effects), and they all share one acceleration: the game only
returns to its normal speed once the last one has expired.
"""
import bgtsound
import itemConstants
import window


class RewindController():
    """Keeps track of the global fast-forward state and glides the pitch.

    :meth:`frameUpdate` must be called once per frame (ssAppMain.frameUpdate
    does that) for the pitch to glide.
    """

    def __init__(self):
        # Current pitch in percent. 100 means the normal speed / pitch.
        self.pitch = itemConstants.REWIND_PITCH_NORMAL
        # Pitch which the ongoing glide started from.
        self.startPitch = itemConstants.REWIND_PITCH_NORMAL
        # Pitch which the ongoing glide is heading to.
        self.target = itemConstants.REWIND_PITCH_NORMAL
        # Number of currently active rewind effects.
        self.requests = 0
        # Whether the in-game time is accelerated along with the pitch. It is
        # turned off as soon as the gameplay ends, so that only the audible
        # pitch glides back down while the game over sequence is played.
        self.timeScaleEnabled = True
        self.paused = False
        # The glide is measured in real time: it drives the in-game time scale,
        # so it must not be affected by it.
        self.rampTimer = window.Timer(scaled=False)

    def requestAcceleration(self):
        """Called when a rewind effect starts. The fast-forward begins when
        this is the first active rewind effect; additional ones simply keep it
        going until they have all expired."""
        self.requests += 1
        if self.requests == 1:
            self.startRamp(itemConstants.REWIND_PITCH_TARGET)
    # end requestAcceleration

    def releaseAcceleration(self):
        """Called when a rewind effect ends. The pitch glides back down to
        the normal speed once the last active rewind effect is gone."""
        self.requests -= 1
        if self.requests < 0:
            self.requests = 0
        if self.requests == 0:
            self.startRamp(itemConstants.REWIND_PITCH_NORMAL)
    # end releaseAcceleration

    def endGameplay(self):
        """Called when the gameplay ends (game over or abort). The in-game time
        stops being accelerated right away, and the pitch glides back down at
        the same rate as it climbed, just like the music pitch does when a game
        ends."""
        self.requests = 0
        self.timeScaleEnabled = False
        # Re-apply right away so that the in-game time returns to its normal
        # speed immediately; only the audible pitch keeps gliding.
        self.setPitch(self.pitch)
        self.startRamp(itemConstants.REWIND_PITCH_NORMAL)
    # end endGameplay

    def reset(self):
        """Instantly returns everything to the normal pitch and speed. Called
        before a new game starts (and before the menus are shown), so that no
        fast-forward state can leak out of the previous game."""
        self.requests = 0
        self.timeScaleEnabled = True
        self.setPaused(False)
        self.target = itemConstants.REWIND_PITCH_NORMAL
        self.startPitch = itemConstants.REWIND_PITCH_NORMAL
        self.setPitch(itemConstants.REWIND_PITCH_NORMAL)
    # end reset

    def startRamp(self, target):
        """Begins gliding the pitch from its current value toward the given
        target.

        :param target: Pitch to glide to, in percent.
        :type target: int
        """
        self.target = target
        self.startPitch = self.pitch
        self.rampTimer.restart()
    # end startRamp

    def frameUpdate(self):
        """Glides the pitch one step closer to the target. Called once per
        frame; does nothing while the game is paused or once the target has
        been reached."""
        if self.paused or self.pitch == self.target:
            return
        distance = self.target - self.startPitch
        if distance == 0:
            self.setPitch(self.target)
            return
        # Pitch units per millisecond, matching the rate at which the music
        # pitch is reverted when a game ends.
        rate = itemConstants.REWIND_PITCH_STEP / float(itemConstants.REWIND_PITCH_STEP_INTERVAL)
        moved = int(self.rampTimer.elapsed * rate)
        if moved >= abs(distance):
            self.setPitch(self.target)
            return
        direction = 1 if distance > 0 else -1
        self.setPitch(self.startPitch + direction * moved)
    # end frameUpdate

    def setPitch(self, pitch):
        """Sets the current pitch and hands it to the sound engine and to the
        in-game time scale.

        :param pitch: New pitch in percent.
        :type pitch: int
        """
        self.pitch = pitch
        scale = pitch / float(itemConstants.REWIND_PITCH_NORMAL)
        bgtsound.setGlobalPitchScale(scale)
        window.Timer.setTimeScale(scale if self.timeScaleEnabled else 1.0)
    # end setPitch

    def setPaused(self, p):
        """Pauses / resumes the pitch glide, together with the rest of the
        game (tab key).

        :param p: Paused?
        :type p: bool
        """
        if p == self.paused:
            return
        self.paused = p
        self.rampTimer.setPaused(p)
    # end setPaused

    def getPitch(self):
        """Returns the current pitch in percent (100 means normal).

        :rtype: int
        """
        return self.pitch
    # end getPitch

    def isAccelerated(self):
        """Returns whether the game is currently fast-forwarded, either because
        a rewind effect is active or because the pitch is still gliding.

        :rtype: bool
        """
        return self.requests > 0 or self.pitch != itemConstants.REWIND_PITCH_NORMAL
    # end isAccelerated

# end class RewindController


controller = None


def getController():
    """Returns the one and only rewind controller, creating it on the first
    call.

    :rtype: RewindController
    """
    global controller
    if controller is None:
        controller = RewindController()
    return controller
# end getController
