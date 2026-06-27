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
        if self.destructing:
            if self.destructTimer.elapsed >= 1800:
                self.performDestruction()
            return True
        # end if destruct
        self.player.frameUpdate()
        if self.player.lives <= 0:
            self.log(_("Game over! Final score: %(score)d") % {"score": self.player.score})
            return False
        # end if
        for i in range(self.level):
            if self.enemies[i] is not None and self.enemies[i].state == enemy.STATE_SHOULDBEDELETED:
                self.enemies[i] = None
            if self.enemies[i] is not None:
                self.enemies[i].frameUpdate()
            if self.enemies[i] is None:
                self.spawnEnemy(i)
        # end for
        return True

    def handleDebugKeys(self):
        """Handles debug / cheat keys. These work identically in every game mode.

        Uppercase (Shift + letter) applies an effect instantly, while the
        lowercase letter makes the corresponding item fall from the sky.
        The lowercase "h" drops a random positive (good) item.
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
            self.spawnDebugItem(itemConstants.TYPE_GOOD, random.randint(0, itemConstants.GOOD_MAX))
        if app.keyPressed(window.K_m):
            if shift:
                self.applyGoodEffect(itemConstants.GOOD_MEGATONPUNCH)
            else:
                self.spawnDebugItem(itemConstants.TYPE_GOOD, itemConstants.GOOD_MEGATONPUNCH)

    def applyGoodEffect(self, identifier):
        """Applies a good item effect to the player as if the item was obtained."""
        it = _DebugItem(itemConstants.TYPE_GOOD, identifier)
        self.player.processItemHit(it)

    def addExtraLives(self, amount):
        """Instantly grants the player a number of extra lives."""
        self.player.lives += amount
        self.log(_("Extra life! (now %(lives)d lives)") % {"lives": self.player.lives})
        s = bgtsound.sound()
        s.load(globalVars.appMain.sounds["extraLife.ogg"])
        s.play()

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
        base = self.highVolumeLimit - (self.highVolumeLimit - self.lowVolumeLimit) / self.y * pos
        result = base
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
        self.gameTimer.setPaused(p)
