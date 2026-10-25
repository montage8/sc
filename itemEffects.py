# -*- coding: utf-8 -*-
# Screaming Strike item effects
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# License: GPL V2.0 (See copying.txt for details)
import math
import bgtsound
import random

import globalVars
import itemConstants
import rewind
import window


class ItemEffectBase(object):
    def initialize(self, player, onSound, offSound, name, effectType=itemConstants.TYPE_GOOD):
        self.paused = False
        self.player = player
        self.active = False
        self.timer = window.Timer()
        self.onSound = onSound
        self.offSound = offSound
        self.lasts = itemConstants.BASE_EFFECT_TIME
        self.name = name
        self.effectType = effectType
        self.scoreMultiplier = 1
        self.on = None
        self.off = None
        self.ex = None

    def activate(self, mode):
        self.on = bgtsound.sound()
        self.on.load(self.onSound)
        self.on.play()
        self.active = True
        self.timer.restart()
        self.player.field.log(_("A new \"%(item)s\" effect is starting!") % {"item": _(self.name)})

    def deactivate(self, mode):
        self.off = bgtsound.sound()
        self.off.load(self.offSound)
        self.off.play()
        self.active = False
        self.player.field.log(_("One of your \"%(item)s\" effects is ending!") % {"item": _(self.name)})

    def extend(self, ms):
        self.ex = bgtsound.sound()
        self.ex.load(self.onSound)
        self.ex.pitch = 130
        self.ex.play()
        self.lasts += ms
        self.player.field.log(_("Your \"%(item)s\" effect has been extended for %(extended)d milliseconds! (now %(newtime)d)") %
                              {"item": _(self.name), "extended": ms, "newtime": self.lasts - self.timer.elapsed})

    def summarize(self):
        """Returns the summary of this effect.

        :rtype: str
        """
        return _("%(name)s: %(sec).2f seconds left") % {"name": _(self.name), "sec": self.calculateTimeRemaining()}

    def calculateTimeRemaining(self):
        """
                Calculates the time after which this item expires in seconds.

                :rtype: float
        """
        return (self.lasts - self.timer.elapsed) / 1000

    def getTimeRemainingMs(self):
        """Returns the time after which this effect expires in milliseconds.

        :rtype: int
        """
        remaining = self.lasts - self.timer.elapsed
        return remaining if remaining > 0 else 0

    def setTimeRemainingMs(self, ms):
        """Forces the time after which this effect expires.

        :param ms: New remaining time in milliseconds.
        :type ms: int
        """
        if ms < 0:
            ms = 0
        self.lasts = self.timer.elapsed + ms

    def applyDurationCheat(self, multiplier):
        """Multiplies the remaining time of this effect (v cheat key).

        :param multiplier: Multiplier to apply.
        :type multiplier: int
        """
        self.setTimeRemainingMs(int(self.getTimeRemainingMs() * multiplier))
        self.player.field.log(_("The remaining time of your \"%(item)s\" effect has been multiplied by %(multiplier)d! (now %(sec).2f seconds)") %
                              {"item": _(self.name), "multiplier": multiplier, "sec": self.calculateTimeRemaining()})
    # end applyDurationCheat

    def frameUpdate(self, mode):
        if self.active is not True:
            return False
        if self.timer.elapsed >= self.lasts:
            self.deactivate(mode)
            return False
        return True

    def setPaused(self, p):
        """Pauses / unpauses this effect."""
        if p == self.paused:
            return
        self.paused = p
        self.timer.setPaused(p)
        if self.on:
            self.on.setPaused(p)
        if self.off:
            self.off.setPaused(p)
        if self.ex:
            self.ex.setPaused(p)
    # end setPaused


class ShrinkEffect(ItemEffectBase):
    def initialize(self, player):
        super().initialize(player, globalVars.appMain.sounds["shrink.ogg"], globalVars.appMain.sounds["shrinkFade.ogg"], "Shrink", itemConstants.TYPE_NASTY)

    def activate(self, mode):
        super().activate(mode)
        self.player.setPunchRange(math.floor(self.player.punchRange * mode.getShrinkMultiplier()))

    def deactivate(self, mode):
        super().deactivate(mode)
        self.player.setPunchRange(math.ceil(self.player.punchRange / mode.getShrinkMultiplier()))


class BlurredEffect(ItemEffectBase):
    def initialize(self, player):
        super().initialize(player, globalVars.appMain.sounds["blurred.ogg"], globalVars.appMain.sounds["blurredFade.ogg"], "Blurred", itemConstants.TYPE_NASTY)

    def frameUpdate(self, mode):
        if super().frameUpdate(mode) is False:
            return False
        if self.player.plantMode is True:
            return True  # a vegetable never moves, even when blurred
        # end plant
        if random.randint(1, 10) == 1:
            while(True):
                d = random.randint(0, self.player.field.getX() - 1)
                if d != self.player.x:
                    break
            # end while
            self.player.moveTo(d)
        # whether to trigger blurring?
        return True
    # end frameUpdate


class SlowDownEffect(ItemEffectBase):
    def initialize(self, player):
        super().initialize(player, globalVars.appMain.sounds["slowDown.ogg"], globalVars.appMain.sounds["slowDownFade.ogg"], "Slow down", itemConstants.TYPE_NASTY)

    def activate(self, mode):
        super().activate(mode)
        self.player.setPunchSpeed(self.player.punchSpeed * mode.getSlowDownMultiplier())

    def deactivate(self, mode):
        super().deactivate(mode)
        self.player.setPunchSpeed(self.player.punchSpeed / mode.getSlowDownMultiplier())


class PlantSlowDownEffect(SlowDownEffect):
    """The slow down of the vegetable (plant) state.

    Unlike every other effect this one has no duration: the vegetable state
    lasts until the player eats an extra life item or gives up with shift+U, and
    the effect is removed only then. It is therefore ignored by the duration
    cheats (v, j) and by the cheats which stop effects (/, ?).
    """

    permanent = True

    def frameUpdate(self, mode):
        return self.active is True

    def summarize(self):
        return _("Slow down: for as long as you are a vegetable")

    def extend(self, ms):
        pass  # the vegetable state is not a timed effect

    def applyDurationCheat(self, multiplier):
        pass  # the vegetable state is not a timed effect


class MegatonPunchEffect(ItemEffectBase):
    def initialize(self, player):
        super().initialize(player, globalVars.appMain.sounds["megatonPunch.ogg"], globalVars.appMain.sounds["megatonPunchFade.ogg"], "Megaton punch")

    def activate(self, mode):
        super().activate(mode)
        self.player.setPunchRange(self.player.punchRange * 5)

    def deactivate(self, mode):
        super().deactivate(mode)
        self.player.setPunchRange(self.player.punchRange / 5)


class BoostEffect(ItemEffectBase):
    def initialize(self, player):
        super().initialize(player, globalVars.appMain.sounds["boost.ogg"], globalVars.appMain.sounds["boostFade.ogg"], "Boost")

    def activate(self, mode):
        super().activate(mode)
        self.player.setPunchSpeed(self.player.punchSpeed / 2)

    def deactivate(self, mode):
        super().deactivate(mode)
        self.player.setPunchSpeed(self.player.punchSpeed * 2)


class PenetrationEffect(ItemEffectBase):
    def initialize(self, player):
        super().initialize(player, globalVars.appMain.sounds["penetration.ogg"], globalVars.appMain.sounds["penetrationFade.ogg"], "Penetration")

    def activate(self, mode):
        super().activate(mode)
        self.player.setPenetration(True)

    def deactivate(self, mode):
        super().deactivate(mode)
        self.player.setPenetration(False)


class ScoreMultiplierEffect(ItemEffectBase):
    """Score multiplier effect.

    While this effect is active, every point the player gains is multiplied by
    itemConstants.SCORE_CHEAT_MULTIPLIER. It starts and ends exactly like the
    boost effect (same sounds, same life time).
    """

    def initialize(self, player):
        super().initialize(player, globalVars.appMain.sounds["boost.ogg"], globalVars.appMain.sounds["boostFade.ogg"],
                           itemConstants.NAMES[itemConstants.TYPE_GOOD][itemConstants.GOOD_SCOREMULTIPLIER])
        self.scoreMultiplier = itemConstants.SCORE_CHEAT_MULTIPLIER

    def activate(self, mode):
        super().activate(mode)
        self.player.field.log(_("Every point you gain is now multiplied by %(multiplier)d!") %
                              {"multiplier": self.scoreMultiplier})


class RewindEffect(ItemEffectBase):
    """Rewind (fast-forward) effect.

    This is a nasty effect. While it is active, not only the music but the
    whole game is fast forwarded: the in-game time itself flows faster, and
    every sound (the enemies, the falling items, the sound effects and so on)
    is pitched up along with it, so everything happens and sounds accelerated
    at once.

    The pitch climbs for about 3 seconds at exactly the same rate as the music
    pitch descends when a game ends, holds there while the effect lasts, and
    glides back down at the same rate when it ends. The acceleration itself is
    driven by rewind.RewindController, since it is shared by every active
    rewind effect and by the entire game.
    """

    def initialize(self, player):
        super().initialize(player, globalVars.appMain.sounds["boost.ogg"], globalVars.appMain.sounds["boostFade.ogg"],
                           itemConstants.NAMES[itemConstants.TYPE_NASTY][itemConstants.NASTY_REWIND], itemConstants.TYPE_NASTY)

    def activate(self, mode):
        super().activate(mode)
        rewind.getController().requestAcceleration()
        self.player.field.log(_("The game is being fast forwarded! The music, every sound and the time itself are speeding up!"))

    def deactivate(self, mode):
        super().deactivate(mode)
        rewind.getController().releaseAcceleration()


class InstantUnlockEffect(ItemEffectBase):
    """Instant unlock effect (cheat key l).

    While this effect is active, every enemy the player punches is unlocked in
    the collection immediately, so a single punch is enough instead of ten.
    """

    def initialize(self, player):
        super().initialize(player, globalVars.appMain.sounds["penetration.ogg"],
                           globalVars.appMain.sounds["penetrationFade.ogg"],
                           itemConstants.NAMES[itemConstants.TYPE_GOOD][itemConstants.GOOD_INSTANTUNLOCK])

    def activate(self, mode):
        super().activate(mode)
        self.player.setInstantUnlock(True)

    def deactivate(self, mode):
        super().deactivate(mode)
        self.player.setInstantUnlock(False)
