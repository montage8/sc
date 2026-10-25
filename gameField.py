# -*- coding: utf-8 -*-
# Screaming Strike game field
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# License: GPL V2.0 (See copying.txt for details)
import datetime
import random
import bgtsound
import bonusCounter
import collection
import enemy
import gameModes
import globalVars
import item
import itemConstants
import itemVoicePlayer
import player
import rewind
import window


class _DebugItem():
    """Lightweight stand-in for item.Item used to apply item effects via debug keys."""

    def __init__(self, type, identifier):
        self.type = type
        self.identifier = identifier


class GameField():
    def initialize(self, x, y, mode, voice, easter=False):
        self.gameTimer = window.Timer()
        self.paused = False
        self.easter = easter
        self.logs = []
        self.log(_("Game started at %(startedtime)s!") % {"startedtime": datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")})
        self.x = x
        self.y = y
        self.setModeHandler(mode)
        self.leftPanningLimit = -100
        self.rightPanningLimit = 100
        self.lowVolumeLimit = -30
        self.highVolumeLimit = 0
        self.level = 1
        if self.easter:
            self.level = 10
        self.enemies = []
        self.items = []
        for i in range(self.level):
            self.enemies.append(None)
        self.player = player.Player()
        self.player.initialize(self)
        self.collectionCounter = collection.CollectionCounter()
        self.collectionCounter.initialize(globalVars.appMain.collectionStorage)
        self.defeats = 0
        self.nextLevelup = self.modeHandler.calculateNextLevelup()
        self.levelupBonus = bonusCounter.BonusCounter()
        self.levelupBonus.initialize()
        self.destructing = False
        self.destructTimer = window.Timer()
        # Remaining times of good effects, remembered before the v cheat key
        # multiplied them, so Shift+V can restore the original values exactly.
        self.goodTimeCheatSnapshot = {}
        # The same for every effect (good and nasty), used by j / Shift+J.
        self.allTimeCheatSnapshot = {}
        # Debug repeating destruction (Shift+F): performs an instant destruction
        # every 0.25 seconds until toggled off, without the powerup prep sound.
        self.repeatDestructing = False
        self.repeatDestructTimer = window.Timer()
        # Debug scheduled destruction (f): performs a user-specified number of
        # instant destructions, one every 0.5 seconds, without the prep sound.
        self.scheduledDestructRemaining = 0
        self.scheduledDestructTimer = window.Timer()
        self.itemVoicePlayer = itemVoicePlayer.ItemVoicePlayer()
        self.itemVoicePlayer.initialize(voice)
        self.destructPowerup = bgtsound.sound()
        self.destructPowerup.load(globalVars.appMain.sounds["destructPowerup.ogg"])
        self.destruct = bgtsound.sound()
        self.destruct.load(globalVars.appMain.sounds["destruct.ogg"])

    def setModeHandler(self, mode):
        self.modeHandler = gameModes.getModeHandler(mode)
        self.modeHandler.initialize(self)
        self.log(
            _("Playing: %(mode)s, high score: %(highscore)d.") % {
                "mode": _(
                    self.modeHandler.getName() + " mode"),
                "highscore": globalVars.appMain.statsStorage.get(
                    "hs_" + self.modeHandler.getName())})

    def setLimits(self, lpLimit, rpLimit):
        self.leftPanningLimit = lpLimit
        self.rightPanningLimit = rpLimit

    def frameUpdate(self):
        if globalVars.appMain.keyPressed(window.K_s):
            globalVars.appMain.say("%.1f" % self.player.score)
        self.handleDebugKeys()
        self.collectionCounter.frameUpdate()
        self.modeHandler.frameUpdate()
        self.levelupBonus.frameUpdate()
        for elem in self.items[:]:
            if elem is not None and elem.state == itemConstants.STATE_SHOULDBEDELETED:
                self.items.remove(elem)
            if elem is not None:
                elem.frameUpdate()
        self.updateRepeatDestruction()
        self.updateScheduledDestruction()
        if self.destructing:
            if self.destructTimer.elapsed >= 1800:
                self.performDestruction()
            return True
        # end if destruct
        self.player.frameUpdate()
        if self.player.dead is True:
            self.log(_("Game over! Final score: %(score)d") % {"score": self.player.score})
            return False
        # end if
        for i in range(len(self.enemies)):
            if self.enemies[i] is not None and self.enemies[i].state == enemy.STATE_SHOULDBEDELETED:
                self.enemies[i] = None
            if self.enemies[i] is not None:
                self.enemies[i].frameUpdate()
                self.processPlantKill(self.enemies[i])
            if self.enemies[i] is None:
                self.spawnEnemy(i)
        # end for
        return True

    def processPlantKill(self, e):
        """While the player is a vegetable, every enemy which reaches the
        player's own position screams and dies on the spot (the vegetable dies
        neither from the slap nor from anything else). Called from frameUpdate
        for each enemy.

        :param e: Enemy to check.
        :type e: enemy.Enemy

        :rtype: bool
        """
        if self.player.plantMode is not True:
            return False
        if e is None or e.state != enemy.STATE_ALIVE:
            return False
        if e.y > itemConstants.PLANT_KILL_RANGE:
            return False
        self.log(_("An enemy reached the vegetable and died on the spot!"))
        e.hit()
        self.modeHandler.onEnemyDefeated()
        self.logDefeat()
        return True
    # end processPlantKill

    def handleDebugKeys(self):
        """Handles debug / cheat keys. These work identically in every game mode.

        Uppercase (Shift + letter) applies an effect instantly, while the
        lowercase letter makes the corresponding item fall from the sky.
        The lowercase "h" drops a random positive (good) item.

        The nasty items have keys too: "n" drops the rewind item, which fast
        forwards the whole game (music, every sound and the in-game time) while
        it is active. Shift+N applies that effect instantly.

        Additional cheat keys:
        v: multiplies the remaining time of every active good effect by 100.
        Shift+V: restores those times to the values from before pressing v.
        j: multiplies the remaining time of every active effect by 100, no
          matter if it is good or nasty.
        Shift+J: restores those times to the values from before pressing j.
        . (period): starts the score multiplier effect, which multiplies every
          point gain by 10000 while it is active. The score multiplier item
          never drops by itself, so this key is the only way to get it.
        / (slash): immediately removes every active nasty effect.
        ? (Shift+/): forcibly ends every active effect, good or nasty.
        u: while the player is screaming after losing the last life, refuses
          death and turns the player into a vegetable (plant state). The player
          slows down, can no longer punch or move, and every enemy which reaches
          the player's own position dies on the spot. The vegetable state has no
          duration: it ends only when an extra life item is eaten (the player is
          revived) or when shift+U is pressed (the player gives up and dies).
        Shift+U: while being a vegetable, gives up and dies (bodyfall, then game
          over).
        l: starts the instant unlock effect: any enemy punched while it is
          active unlocks its scream in the collection at once.
        x: throws away every item which is currently falling, no matter if it
          is good or nasty (the items shatter without being used).
        Shift+X: collects every item which is currently falling, no matter if it
          is good or nasty (all of their effects are applied instantly).
        """
        app = globalVars.appMain
        shift = app.keyPressing(window.K_LSHIFT) or app.keyPressing(window.K_RSHIFT)
        if app.keyPressed(window.K_d):
            if shift:
                self.applyGoodEffect(itemConstants.GOOD_DESTRUCTION)
            else:
                self.spawnDebugItem(itemConstants.TYPE_GOOD, itemConstants.GOOD_DESTRUCTION)
        if app.keyPressed(window.K_b):
            if shift:
                self.applyGoodEffect(itemConstants.GOOD_BOOST)
            else:
                self.spawnDebugItem(itemConstants.TYPE_GOOD, itemConstants.GOOD_BOOST)
        if app.keyPressed(window.K_p):
            if shift:
                self.applyGoodEffect(itemConstants.GOOD_PENETRATION)
            else:
                self.spawnDebugItem(itemConstants.TYPE_GOOD, itemConstants.GOOD_PENETRATION)
        if app.keyPressed(window.K_e):
            if shift:
                self.addExtraLives(300)
            else:
                self.spawnDebugItem(itemConstants.TYPE_GOOD, itemConstants.GOOD_EXTRALIFE)
        if app.keyPressed(window.K_h):
            self.spawnDebugItem(itemConstants.TYPE_GOOD, random.choice(itemConstants.GOOD_RANDOM_ITEMS))
        if app.keyPressed(window.K_g):
            if shift:
                self.applyGoodEffect(itemConstants.GOOD_RESETENEMIES)
            else:
                self.spawnDebugItem(itemConstants.TYPE_GOOD, itemConstants.GOOD_RESETENEMIES)
        if app.keyPressed(window.K_c):
            if shift:
                self.addStoredDestruction(3000)
            else:
                self.promptStoredDestruction()
        if app.keyPressed(window.K_m):
            if shift:
                self.applyGoodEffect(itemConstants.GOOD_MEGATONPUNCH)
            else:
                self.spawnDebugItem(itemConstants.TYPE_GOOD, itemConstants.GOOD_MEGATONPUNCH)
        if app.keyPressed(window.K_f):
            if shift:
                self.toggleRepeatDestruction()
            else:
                self.promptScheduledDestruction()
        if app.keyPressed(window.K_v):
            if shift:
                self.restoreGoodEffectTimes()
            else:
                self.extendGoodEffectTimes()
        if app.keyPressed(window.K_j):
            if shift:
                self.restoreAllEffectTimes()
            else:
                self.extendAllEffectTimes()
        if app.keyPressed(window.K_n):
            if shift:
                self.applyNastyEffect(itemConstants.NASTY_REWIND)
            else:
                self.spawnDebugItem(itemConstants.TYPE_NASTY, itemConstants.NASTY_REWIND)
        if app.keyPressed(window.K_PERIOD):
            self.applyGoodEffect(itemConstants.GOOD_SCOREMULTIPLIER)
        if app.keyPressed(window.K_SLASH):
            if shift:
                self.stopAllItemEffects()
            else:
                self.stopNastyItemEffects()
        if app.keyPressed(window.K_x):
            if shift:
                self.collectFallingItems()
            else:
                self.discardFallingItems()
        if app.keyPressed(window.K_u):
            if shift:
                self.player.giveUpAndDie()
            else:
                self.player.enterPlantMode()
        if app.keyPressed(window.K_l):
            self.applyGoodEffect(itemConstants.GOOD_INSTANTUNLOCK)

    def getFallingItems(self):
        """Returns the items which are currently falling and can still be
        obtained or destroyed.

        :rtype: list
        """
        return [e for e in self.items if e.state == itemConstants.STATE_ALIVE]
    # end getFallingItems

    def discardFallingItems(self):
        """Cheat key x: throws away every falling item. Good and nasty items are
        both shattered on the spot, so none of their effects is applied."""
        targets = self.getFallingItems()
        if len(targets) == 0:
            self.log(_("There are no falling items to throw away!"))
            return
        for elem in targets:
            elem.destroy()
        # end for
        self.log(_("Threw away %(count)d falling item(s)! (good and nasty)") % {"count": len(targets)})
    # end discardFallingItems

    def collectFallingItems(self):
        """Cheat key Shift+X: collects every falling item at once. Good and nasty
        items are both obtained, so every effect is applied immediately."""
        targets = self.getFallingItems()
        if len(targets) == 0:
            self.log(_("There are no falling items to collect!"))
            return
        for elem in targets:
            elem.obtain()
            self.player.processItemHit(elem)
        # end for
        self.log(_("Collected %(count)d falling item(s) at once! (good and nasty)") % {"count": len(targets)})
    # end collectFallingItems

    def extendEffectTimes(self, snapshot, effectType=None):
        """Multiplies the remaining time of the active item effects by 100.

        The remaining times from before the first multiplication are remembered
        in the given snapshot, so they can be restored exactly afterwards.

        :param snapshot: Dictionary in which the original remaining times are kept.
        :type snapshot: dict
        :param effectType: If given, only the effects of this type (TYPE_GOOD or
                           TYPE_NASTY) are extended. Otherwise every active
                           effect is extended.
        :type effectType: int

        :rtype: int
        """
        extended = 0
        for elem in self.player.itemEffects:
            if getattr(elem, "permanent", False):
                continue  # the vegetable slow down has no duration
            # end permanent
            if effectType is not None and elem.effectType != effectType:
                continue
            if elem not in snapshot:
                snapshot[elem] = elem.getTimeRemainingMs()
            elem.applyDurationCheat(itemConstants.EFFECT_TIME_CHEAT_MULTIPLIER)
            extended += 1
        # end for
        return extended
    # end extendEffectTimes

    def restoreEffectTimes(self, snapshot):
        """Restores the effect times which were remembered before the cheat key
        multiplied them, and empties the snapshot.

        :param snapshot: Dictionary in which the original remaining times are kept.
        :type snapshot: dict

        :rtype: int
        """
        restored = 0
        for elem in self.player.itemEffects[:]:
            if elem not in snapshot:
                continue
            elem.setTimeRemainingMs(snapshot.pop(elem))
            restored += 1
            self.log(_("The remaining time of your \"%(item)s\" effect has been restored! (now %(sec).2f seconds)") %
                     {"item": _(elem.name), "sec": elem.calculateTimeRemaining()})
        # end for
        snapshot.clear()
        return restored
    # end restoreEffectTimes

    def extendGoodEffectTimes(self):
        """Cheat key v: multiplies the remaining time of every active good item
        effect by 100. The remaining times before the first multiplication are
        remembered so Shift+V can restore them."""
        extended = self.extendEffectTimes(self.goodTimeCheatSnapshot, itemConstants.TYPE_GOOD)
        if extended == 0:
            self.log(_("There are no good effects to extend!"))
            return
        self.log(_("The time of %(count)d good effect(s) has been multiplied by %(multiplier)d! Press Shift+V to restore it.") %
                 {"count": extended, "multiplier": itemConstants.EFFECT_TIME_CHEAT_MULTIPLIER})
    # end extendGoodEffectTimes

    def restoreGoodEffectTimes(self):
        """Cheat key Shift+V: restores the good effect remaining times which were
        remembered before the v cheat key multiplied them."""
        restored = self.restoreEffectTimes(self.goodTimeCheatSnapshot)
        if restored == 0:
            self.log(_("There are no good effect times to restore!"))
            return
        self.log(_("Restored the original time of %(count)d good effect(s).") % {"count": restored})
    # end restoreGoodEffectTimes

    def extendAllEffectTimes(self):
        """Cheat key j: multiplies the remaining time of every active item effect
        by 100, no matter if it is good or nasty. The remaining times before the
        first multiplication are remembered so Shift+J can restore them."""
        extended = self.extendEffectTimes(self.allTimeCheatSnapshot)
        if extended == 0:
            self.log(_("There are no effects to extend!"))
            return
        self.log(_("The time of %(count)d item effect(s) has been multiplied by %(multiplier)d! Press Shift+J to restore it.") %
                 {"count": extended, "multiplier": itemConstants.EFFECT_TIME_CHEAT_MULTIPLIER})
    # end extendAllEffectTimes

    def restoreAllEffectTimes(self):
        """Cheat key Shift+J: restores every effect remaining time which was
        remembered before the j cheat key multiplied it."""
        restored = self.restoreEffectTimes(self.allTimeCheatSnapshot)
        if restored == 0:
            self.log(_("There are no effect times to restore!"))
            return
        self.log(_("Restored the original time of %(count)d item effect(s).") % {"count": restored})
    # end restoreAllEffectTimes

    def stopNastyItemEffects(self):
        """Cheat key /: immediately removes every active nasty item effect."""
        removed = self.player.removeItemEffects(itemConstants.TYPE_NASTY)
        self.forgetTimeCheatSnapshots()
        if len(removed) == 0:
            self.log(_("There are no nasty effects to remove!"))
            return
        self.log(_("Removed all nasty item effects (%(items)s)!") % {"items": ", ".join(_(name) for name in removed)})
    # end stopNastyItemEffects

    def stopAllItemEffects(self):
        """Cheat key ?: forcibly ends every active item effect, good or nasty."""
        removed = self.player.removeItemEffects()
        self.goodTimeCheatSnapshot = {}
        self.allTimeCheatSnapshot = {}
        if len(removed) == 0:
            self.log(_("There are no effects to end!"))
            return
        self.log(_("Forcibly ended all item effects (%(items)s)!") % {"items": ", ".join(_(name) for name in removed)})
    # end stopAllItemEffects

    def forgetTimeCheatSnapshots(self):
        """Drops the remembered effect times of effects which are gone."""
        remaining = self.player.itemEffects
        for snapshot in (self.goodTimeCheatSnapshot, self.allTimeCheatSnapshot):
            for elem in list(snapshot):
                if elem not in remaining:
                    del snapshot[elem]
        # end for
    # end forgetTimeCheatSnapshots

    def applyGoodEffect(self, identifier):
        """Applies a good item effect to the player as if the item was obtained."""
        it = _DebugItem(itemConstants.TYPE_GOOD, identifier)
        self.player.processItemHit(it)

    def applyNastyEffect(self, identifier):
        """Applies a nasty item effect to the player as if the item was obtained."""
        it = _DebugItem(itemConstants.TYPE_NASTY, identifier)
        self.player.processItemHit(it)

    def addExtraLives(self, amount):
        """Instantly grants the player a number of extra lives."""
        self.player.lives += amount
        self.log(_("Extra life! (now %(lives)d lives)") % {"lives": self.player.lives})
        s = bgtsound.sound()
        s.load(globalVars.appMain.sounds["extraLife.ogg"])
        s.play()
        if self.player.plantMode is True:
            self.player.reviveFromPlantMode()
        # end revive

    def resetEnemies(self):
        """Resets the enemy progression back to the exact state of a fresh game
        start, while preserving the player's accumulated score.

        The enemy roster grows by one on every level-up and never shrinks, so a
        long game accumulates so many enemies that performance degrades and the
        field becomes overwhelming. Obtaining the reset item should give the
        player relief by collapsing the field back to a single enemy and then
        letting the enemy count climb again the same way it does at the very
        beginning of a game.

        At game start (see ``__init__``) the level is ``1``, the enemy roster
        holds a single slot, the defeat count is ``0`` and ``nextLevelup`` is
        seeded from :meth:`calculateNextLevelup`. Because the number of defeats
        required for the next level-up grows with the level, leaving the level
        high made regrowth take a very long time and then jump unevenly. Mirror
        the initial state instead so enemies start increasing right away and ramp
        up gradually, exactly like a new game. The player's accumulated
        ``player.score`` is intentionally left untouched."""
        self.level = 1
        if self.easter:
            self.level = 10
        self.enemies = []
        for i in range(self.level):
            self.enemies.append(None)
        self.defeats = 0
        self.nextLevelup = self.modeHandler.calculateNextLevelup()
        self.log(_("The number of enemies has been reset to one!"))

    def setStoredDestruction(self, amount):
        """Sets the player's stored (auto) destruction count to a fixed value."""
        if amount < 0:
            amount = 0
        self.player.autoDestructionRemaining = amount
        self.log(_("Stored destruction count is now %(r)d!") % {"r": self.player.autoDestructionRemaining})

    def addStoredDestruction(self, amount):
        """Adds to the player's stored (auto) destruction count (Shift+C)."""
        self.setStoredDestruction(self.player.autoDestructionRemaining + amount)

    def promptStoredDestruction(self):
        """Asks the user for an exact stored destruction count (c debug key)."""
        ret = globalVars.appMain.input(_("Stored destruction"), _("How many stored destructions should you have?"))
        if ret is None:
            return
        try:
            count = int(ret)
        except ValueError:
            return
        self.setStoredDestruction(count)

    def spawnDebugItem(self, type, identifier):
        """Makes an item of the given type / identifier fall from the sky."""
        i = item.Item()
        i.initialize(self, random.randint(0, self.x - 1), random.randint(300, 800), type, identifier)
        self.items.append(i)

    def spawnEnemy(self, slot):
        e = enemy.Enemy()
        if self.easter:
            e.initialize(self, random.randint(0, self.x - 1), random.randint(300, 900), random.randint(90, 91))
        else:
            e.initialize(self, random.randint(0, self.x - 1), random.randint(300, 900), random.randint(0, globalVars.appMain.getNumScreams() - 1))
        self.enemies[slot] = e

    def logDefeat(self):
        self.defeats += 1
        self.nextLevelup -= 1
        if self.nextLevelup == 0:
            self.levelup()

    def log(self, s):
        self.logs.append(s)

    def getLog(self):
        """Retrieves the list in which the log is written.

        :rtype: list
        """
        return self.logs

    def exportLog(self):
        l = self.logs[:]
        l.append("")
        return "\n".join(l)

    def levelup(self):
        self.log(_("Leveled up to %(newlevel)d! (Accuracy %(accuracy).1f%%, with %(lives)d hp remaining)") %
                 {"newlevel": self.level + 1, "accuracy": self.player.hitPercentage, "lives": self.player.lives})
        self.processLevelupBonus()
        self.level += 1
        self.enemies.append(None)
        self.nextLevelup = self.modeHandler.calculateNextLevelup()
        globalVars.appMain.changeMusicPitch_relative(2)

    def processLevelupBonus(self):
        if not self.modeHandler.allowLevelupBonus:
            return
        self.player.addScore(self.player.hitPercentage * self.player.hitPercentage * self.level * self.player.lives * 0.5)
        self.levelupBonus.start(int(self.player.hitPercentage * 0.1))

    def getCenterPosition(self):
        if self.x % 2 == 0:
            return int((self.x / 2) + 1)
        else:
            return int(self.x / 2)

    def getPan(self, pos):
        return self.leftPanningLimit + (self.rightPanningLimit - self.leftPanningLimit) / (self.x - 1) * pos

    def getVolume(self, pos):
        result = self.highVolumeLimit - (self.highVolumeLimit - self.lowVolumeLimit) / self.y * pos
        if result < self.lowVolumeLimit:
            result = self.lowVolumeLimit
        if result > self.highVolumeLimit:
            result = self.highVolumeLimit
        return result

    def getPitch(self, y):
        return 70 + (y * 3)

    def getX(self):
        return self.x

    def getY(self):
        return self.y

    def abort(self):
        """aborts the gameplay."""
        self.log(_("Game aborted."))
        self.clear()

    def clear(self):
        self.enemies = []
        self.items = []
        # The gameplay is over. Stop accelerating the in-game time right away
        # and let the pitch of the rewind (fast-forward) effect glide back down
        # at the same rate as it climbed, just like the music pitch does when a
        # game ends.
        rewind.getController().endGameplay()

    def startDestruction(self):
        if self.destructing:
            return False
        self.destructPowerup.play()
        self.destructTimer.restart()
        self.destructing = True
        return True

    def performDestruction(self):
        self.destruct.play()
        self.log(_("Activating destruction!"))
        for elem in self.enemies:
            if elem is not None and elem.state == enemy.STATE_ALIVE:
                elem.hit()
            self.logDefeat()
        for elem in self.items:
            if elem.type == itemConstants.TYPE_NASTY:
                elem.destroy()
            else:
                elem.obtain()
                self.player.processItemHit(elem)
        self.destructing = False
        self.log(_("End destruction!"))

    def toggleRepeatDestruction(self):
        """Toggles the repeating instant destruction (Shift+F debug key). When
        enabled, an instant destruction is performed every 0.25 seconds without
        the powerup prep sound; pressing the key again stops it."""
        self.repeatDestructing = not self.repeatDestructing
        if self.repeatDestructing:
            self.repeatDestructTimer.restart()
            self.performDestruction()

    def updateRepeatDestruction(self):
        """Performs a repeating instant destruction every 0.25 seconds while the
        repeating mode is active. Called once per frame."""
        if not self.repeatDestructing:
            return
        if self.repeatDestructTimer.elapsed >= 250:
            self.repeatDestructTimer.restart()
            self.performDestruction()

    def promptScheduledDestruction(self):
        """Asks the user how many instant destructions to perform (f debug key),
        then schedules them one every 0.5 seconds without the prep sound."""
        ret = globalVars.appMain.input(_("Repeat destruction"), _("How many times should destruction repeat (every 0.5 seconds)?"))
        if ret is None:
            return
        try:
            count = int(ret)
        except ValueError:
            return
        if count <= 0:
            return
        self.scheduledDestructTimer.restart()
        self.performDestruction()
        self.scheduledDestructRemaining = count - 1

    def updateScheduledDestruction(self):
        """Performs the remaining scheduled instant destructions, one every 0.5
        seconds. Called once per frame."""
        if self.scheduledDestructRemaining <= 0:
            return
        if self.scheduledDestructTimer.elapsed >= 500:
            self.scheduledDestructTimer.restart()
            self.performDestruction()
            self.scheduledDestructRemaining -= 1
# end class GameField

    def setPaused(self, p):
        """Pauses / unpauses this field."""
        if p == self.paused:
            return
        self.paused = p
        self.destructPowerup.setPaused(p)
        self.destruct.setPaused(p)
        for elem in self.enemies:
            if elem:
                elem.setPaused(p)
        # end enemies
        for elem in self.items:
            elem.setPaused(p)
        # end items
        self.player.setPaused(p)
        self.destructTimer.setPaused(p)
        self.repeatDestructTimer.setPaused(p)
        self.scheduledDestructTimer.setPaused(p)
        self.gameTimer.setPaused(p)
        # The rewind (fast-forward) pitch glide must stop along with the game,
        # otherwise the pitch would keep climbing while nothing else moves.
        rewind.getController().setPaused(p)
