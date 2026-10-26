# -*- coding: utf-8 -*-
# Screaming Strike player handler class
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# License: GPL V2.0 (See copying.txt for details)
import bgtsound
import random
import bonusCounter
import enemy
import globalVars
import itemConstants
import itemEffects
import window

DEFAULT_PUNCH_RANGE = 4
DEFAULT_PUNCH_SPEED = 200


class Player():
    """This class represents a player."""

    def initialize(self, field):
        """Initializes this player.

        :param field: The field instance on which this player should be bound.
        :type field: gameField.GameField
        """
        self.paused = False
        self.field = field
        self.lives = 3
        self.x = field.getCenterPosition()
        self.punchTimer = window.Timer()
        self.punching = False
        self.punchSpeed = DEFAULT_PUNCH_SPEED
        self.punchRange = DEFAULT_PUNCH_RANGE
        self.score = 0
        self.score_validator = []
        self.punches = 0
        self.hits = 0
        self.hitPercentage = 0
        self.consecutiveHitBonus = bonusCounter.BonusCounter()
        self.consecutiveHitBonus.initialize()
        self.consecutiveMissUnbonus = bonusCounter.BonusCounter()
        self.consecutiveMissUnbonus.initialize()
        self.consecutiveHits = 0
        self.consecutiveMisses = 0
        self.itemEffects = []
        self.penetrate = False
        self.autoDestructionRemaining = 0
        self.lastHighscore = globalVars.appMain.statsStorage.get("hs_" + self.field.modeHandler.getName())
        self.gotHighscore = False
        # Instant unlock effect (cheat key l): every punched enemy is unlocked
        # in the collection right away.
        self.instantUnlock = False
        # Death sequence: scream first, then fall down. Pressing U while the
        # scream is audible turns the player into a vegetable instead of dying.
        self.dying = False
        self.dyingPhase = None
        self.dead = False
        self.deathTimer = window.Timer()
        self.deathScream = None
        self.deathFall = None
        # Vegetable state (see enterPlantMode).
        self.plantMode = False
        self.plantSlowDown = None
        # True once the bodyfall of the death sequence has been played, so the
        # game over sequence does not play it a second time.
        self.deathSoundPlayed = False

    def frameUpdate(self):
        """Call this method once per frame to keep everything updated."""
        self.consecutiveHitBonus.frameUpdate()
        self.consecutiveMissUnbonus.frameUpdate()
        self.updateDeathSequence()
        if self.dead is True:
            return
        if self.plantMode is True:
            # A vegetable cannot punch, cannot move and cannot be moved by the
            # blurred effect. Only the item effects keep running (and the slow
            # down effect of the vegetable state is kept alive).
            self.updatePlantMode()
        else:
            if self.punching is False and globalVars.appMain.keyPressed(window.K_SPACE):
                self.punchLaunch()
            if self.punching is True and self.punchTimer.elapsed >= self.punchSpeed:
                self.punchHit()
            if self.x != 0 and globalVars.appMain.keyPressed(window.K_LEFT):
                self.moveTo(self.x - 1)
            if self.x != self.field.getX() - 1 and globalVars.appMain.keyPressed(window.K_RIGHT):
                self.moveTo(self.x + 1)
        for elem in self.itemEffects[:]:
            if not elem.frameUpdate(self.field.modeHandler):
                self.itemEffects.remove(elem)

    def updateDeathSequence(self):
        """Advances the death sequence. Called from frameUpdate.

        The player screams first and falls down afterwards. As long as the
        scream is audible (and for a minimum amount of time), U can still be
        pressed to refuse death, so the fall never starts before the player had
        a real chance to react.
        """
        if self.dying is not True:
            return
        if self.dyingPhase == itemConstants.DEATH_PHASE_SCREAM:
            if self.deathTimer.elapsed < itemConstants.DEATH_SCREAM_MAX_TIME:
                if self.deathScream is not None and self.deathScream.playing is True:
                    return  # still screaming: keep the window for U open
                # end still screaming
                if self.deathTimer.elapsed < itemConstants.DEATH_SCREAM_TIME:
                    return  # the scream was short, but U must stay possible
                # end minimum time
            # end scream phase
            self.startFall()
            return
        # end scream phase
        if self.dyingPhase == itemConstants.DEATH_PHASE_FALL and self.deathTimer.elapsed >= itemConstants.DEATH_FALL_TIME:
            self.finishDeath()
        # end fall phase
    # end updateDeathSequence

    def startDeath(self):
        """Starts the death sequence by screaming. Called when the last life is
        lost. For a short while after this, U refuses death (see
        enterPlantMode)."""
        if self.dying is True or self.plantMode is True or self.dead is True:
            return
        self.dying = True
        self.dyingPhase = itemConstants.DEATH_PHASE_SCREAM
        self.deathTimer.restart()
        self.deathScream = bgtsound.sound()
        self.deathScream.load(globalVars.appMain.sounds["scream%d.ogg" % random.randint(
            0, max(0, globalVars.appMain.getNumScreams() - 1))])
        self.deathScream.pitch = random.randint(70, 95)
        self.deathScream.play()
        self.field.log(_("You scream as your last life is taken away!"))
        self.field.log(_("Press U before you hit the ground to refuse death and become a vegetable!"))
    # end startDeath

    def startFall(self):
        """Moves the death sequence on to falling down. From this moment on U
        can no longer save the player."""
        self.dying = True
        self.dyingPhase = itemConstants.DEATH_PHASE_FALL
        self.deathTimer.restart()
        self.deathFall = bgtsound.sound()
        self.deathFall.load(globalVars.appMain.sounds["dead.ogg"])
        self.deathFall.pitch = random.randint(80, 100)
        self.deathFall.play()
        self.deathSoundPlayed = True
        self.field.log(_("You fall to the ground!"))
    # end startFall

    def finishDeath(self):
        """Ends the death sequence. The game field sees the dead flag and ends
        the game."""
        self.dying = False
        self.dyingPhase = None
        self.dead = True
        s = bgtsound.sound()
        s.load(globalVars.appMain.sounds["gameover.ogg"])
        s.volume = -10
        s.play()
        self.field.log(_("Game over!"))
    # end finishDeath

    def canEnterPlantMode(self):
        """Returns whether U can turn this player into a vegetable right now,
        that is, while the player is screaming after losing the last life.

        :rtype: bool
        """
        if self.plantMode is True or self.dead is True:
            return False
        if self.lives > 0:
            return False
        return self.dying is True and self.dyingPhase == itemConstants.DEATH_PHASE_SCREAM
    # end canEnterPlantMode

    def enterPlantMode(self):
        """Cheat key U: refuses death and becomes a vegetable. The player can no
        longer punch or move, and every enemy which comes close dies on its own.
        An extra life item is needed to come back.

        :rtype: bool
        """
        if self.plantMode is True:
            self.field.log(_("You are already a vegetable!"))
            return False
        if self.lives > 0:
            self.field.log(_("You can only become a vegetable at the very moment you would die!"))
            return False
        if self.dying is not True:
            self.field.log(_("You can only become a vegetable at the very moment you would die!"))
            return False
        if self.dyingPhase != itemConstants.DEATH_PHASE_SCREAM:
            self.field.log(_("It's too late! You have already hit the ground."))
            return False
        # Stop the scream which was about to end in death.
        self.dying = False
        self.dyingPhase = None
        if self.deathScream is not None:
            self.deathScream.stop()
        self.lives = 0
        self.plantMode = True
        self.plantSlowDown = None
        self.field.log(_("You refused death and became a vegetable! You cannot punch or move, but every enemy which comes close dies on its own."))
        self.field.log(_("Eat an extra life item (for example with shift+X) to come back. Press shift+U to give up and die."))
        self.applyPlantSlowDown()
        return True
    # end enterPlantMode

    def applyPlantSlowDown(self):
        """Makes sure the vegetable state is slowed down. Called when the
        vegetable state starts and whenever its slow down effect is gone.

        The effect used here has no duration: the vegetable state lasts until
        the player eats an extra life item or gives up with shift+U."""
        if self.plantSlowDown is not None and self.plantSlowDown in self.itemEffects:
            return
        e = itemEffects.PlantSlowDownEffect()
        e.initialize(self)
        e.activate(self.field.modeHandler)
        self.itemEffects.append(e)
        self.plantSlowDown = e
    # end applyPlantSlowDown

    def updatePlantMode(self):
        """Keeps the vegetable state running. Called from frameUpdate."""
        self.applyPlantSlowDown()
    # end updatePlantMode

    def exitPlantMode(self):
        """Leaves the vegetable state (either because an extra life was eaten or
        because the player gave up). Returns whether the state was left."""
        if self.plantMode is not True:
            return False
        self.plantMode = False
        if self.plantSlowDown is not None and self.plantSlowDown in self.itemEffects:
            self.plantSlowDown.deactivate(self.field.modeHandler)
            self.itemEffects.remove(self.plantSlowDown)
        self.plantSlowDown = None
        return True
    # end exitPlantMode

    def reviveFromPlantMode(self):
        """Called when this player gains a life while being a vegetable. Returns
        to normal gameplay."""
        if self.exitPlantMode() is not True:
            return False
        self.field.log(_("The extra life brought you back! You can punch and move again."))
        return True
    # end reviveFromPlantMode

    def giveUpAndDie(self):
        """Cheat key Shift+U: gives up the vegetable state and dies. The bodyfall
        sound is played and the game ends right after it.

        :rtype: bool
        """
        if self.plantMode is not True:
            self.field.log(_("You are not a vegetable!"))
            return False
        self.exitPlantMode()
        self.lives = 0
        self.startFall()
        return True
    # end giveUpAndDie

    def setInstantUnlock(self, p):
        """Enables / disables the instant unlock effect.

        :param p: Whether a single punch unlocks a collection.
        :type p: bool
        """
        if p is True:
            self.field.log(_("Your punches now unlock screams in one hit!"))
        else:
            self.field.log(_("Your punches no longer unlock screams in one hit."))
        self.instantUnlock = p
    # end setInstantUnlock

    def punchLaunch(self):
        """Launches a punch. If this player is already punching, this method does nothing. """
        if self.punching or self.plantMode is True or self.dead is True:
            return
        self.punches += 1
        self.punching = True
        s = bgtsound.sound()
        s.load(globalVars.appMain.sounds["fists.ogg"])
        s.pan = self.field.getPan(self.x)
        s.pitch = int(DEFAULT_PUNCH_SPEED / self.punchSpeed * 100) + random.randint(-10, 10)
        s.play()
        self.punchTimer.restart()

    def punchHit(self):
        """Process punch hits. Called from frameUpdate as it is needed."""
        self.punching = False
        hit = 0
        for pos in range(int(self.punchRange) + 1):
            for elem in self.field.enemies:
                if elem is not None and elem.state == enemy.STATE_ALIVE and self.x == elem.x and elem.y == pos:
                    elem.hit()
                    self.field.modeHandler.onEnemyDefeated()
                    hit += 1
                    self.hits += 1
                    self.consecutiveHits += 1
                    self.processConsecutiveMisses()
                    self.calcHitPercentage()  # penetration would higher the percentage, but I don't care
                    self.field.logDefeat()
                    if not self.penetrate:
                        break
                # end if
            # end for enemies
            if not self.penetrate and hit > 0:
                break
            for elem in self.field.items:
                if elem.state == itemConstants.STATE_ALIVE and self.x == elem.x and elem.y == pos:
                    if globalVars.appMain.keyPressing(window.K_UP):
                        elem.punch()
                    else:
                        elem.obtain()
                        self.field.modeHandler.onItemObtained()
                        self.processItemHit(elem)
                    # end item hit
                    hit = True
                    self.hits += 1
                    self.consecutiveHits += 1
                    self.processConsecutiveMisses()
                    self.calcHitPercentage()
                    if not self.penetrate:
                        break
                # end if
            # end for items
        # end for range
        if not hit:
            self.punchMiss()
    # end punchHit

    def punchMiss(self):
        """Processes punch miss. Called from punchHit."""
        self.consecutiveMisses += 1
        if self.hits > 0:
            self.calcHitPercentage()
        self.processConsecutiveHits()

    def processConsecutiveHits(self):
        """Processes consecutive hits bonus. Called from punchHit."""
        if not self.field.modeHandler.allowConsecutiveHitsBonus:
            return
        if self.consecutiveHits > 5:
            self.field.log(_("%(hits)d consecutive hits bonus!") % {"hits": self.consecutiveHits})
            self.addScore(self.consecutiveHits * self.consecutiveHits * self.field.level * self.field.level)
            self.consecutiveHitBonus.start(self.consecutiveHits)
        # end if
        self.consecutiveHits = 0

    def processConsecutiveMisses(self):
        """Processes consecutive misses penalty. Called from punchHit."""
        if not self.field.modeHandler.allowConsecutiveMissesBonus:
            return
        if self.consecutiveMisses > 5:
            self.field.log(_("%(misses)d consecutive misses penalty!") % {"misses": self.consecutiveMisses})
            self.addScore(self.consecutiveMisses * self.consecutiveMisses * self.field.level * self.field.level * -1)
            self.consecutiveMissUnbonus.start(self.consecutiveMisses * -1)
        # end if
        self.consecutiveMisses = 0

    def processItemHit(self, it):
        """
        Processes hitting an item. Called from punchHit. This method just checks the item is good or nasty, then calls the specific methods.

        :param it: Item instance which got hit.
        :type it: item.Item
        """
        if it.type == itemConstants.TYPE_NASTY:
            self.processNastyItemHit(it)
        else:
            self.processGoodItemHit(it)

    def processNastyItemHit(self, it):
        """
        Processes a nasty item hit. Called from processItemHit.

        :param it: Item instance which got hit.
        :type it: item.Item
        """
        if it.identifier == itemConstants.NASTY_SHRINK:
            # When player's punching range cannot be decreased further, find an existing shrink effect and extend the effect expiration.
            self.processShrinkItemEffect()
            return
        if it.identifier == itemConstants.NASTY_BLURRED:
            e = itemEffects.BlurredEffect()
            e.initialize(self)
            e.activate(self.field.modeHandler)
            self.itemEffects.append(e)
            return
        if it.identifier == itemConstants.NASTY_SLOWDOWN:
            e = itemEffects.SlowDownEffect()
            e.initialize(self)
            e.activate(self.field.modeHandler)
            self.itemEffects.append(e)
            return
        if it.identifier == itemConstants.NASTY_REWIND:
            e = itemEffects.RewindEffect()
            e.initialize(self)
            e.activate(self.field.modeHandler)
            self.itemEffects.append(e)
            return

    def processShrinkItemEffect(self):
        """
                Processes an edge case where player's punching range is 1 and cannot be decreased further.
                In this case, find an existing shrink effect, which will be expired next.
                Extend the found shrink effect's expiration.
                Otherwise, normally process the shrink effect.
        """
        if self.punchRange == 1:
            shrinks = [e for e in self.itemEffects if e.name == itemConstants.NAMES[itemConstants.TYPE_NASTY]
                       [itemConstants.NASTY_SHRINK]]  # length should never be 0
            shrinks.sort(key=lambda e: e.calculateTimeRemaining())
            shrinks[0].extend(itemConstants.BASE_EFFECT_TIME)
            return
        # normal
        e = itemEffects.ShrinkEffect()
        e.initialize(self)
        e.activate(self.field.modeHandler)
        self.itemEffects.append(e)

    def processGoodItemHit(self, it):
        """
        Processes a good item hit. Called from processItemHit.

        :param it: Item instance which got hit.
        :type it: item.Item
        """
        if it.identifier == itemConstants.GOOD_MEGATONPUNCH:
            existing = self.findEffect("Megaton punch")
            if existing is None:
                e = itemEffects.MegatonPunchEffect()
                e.initialize(self)
                e.activate(self.field.modeHandler)
                self.itemEffects.append(e)
            else:
                existing.extend(itemConstants.BASE_EFFECT_TIME)
            return
        if it.identifier == itemConstants.GOOD_BOOST:
            e = itemEffects.BoostEffect()
            e.initialize(self)
            e.activate(self.field.modeHandler)
            self.itemEffects.append(e)
            return
        if it.identifier == itemConstants.GOOD_PENETRATION:
            existing = self.findEffect("Penetration")
            if existing is None:
                e = itemEffects.PenetrationEffect()
                e.initialize(self)
                e.activate(self.field.modeHandler)
                self.itemEffects.append(e)
            else:
                existing.extend(itemConstants.BASE_EFFECT_TIME)
            return
        if it.identifier == itemConstants.GOOD_SCOREMULTIPLIER:
            existing = self.findEffect(
                itemConstants.NAMES[itemConstants.TYPE_GOOD][itemConstants.GOOD_SCOREMULTIPLIER])
            if existing is None:
                e = itemEffects.ScoreMultiplierEffect()
                e.initialize(self)
                e.activate(self.field.modeHandler)
                self.itemEffects.append(e)
            else:
                existing.extend(itemConstants.BASE_EFFECT_TIME)
            return
        if it.identifier == itemConstants.GOOD_DESTRUCTION:
            ok = self.field.startDestruction()
            if not ok:  # Already destructing
                self.autoDestructionRemaining += 1
                self.field.log(_("This effect will be used when it's necessary! (Remaining %(r)d)") % {"r": self.autoDestructionRemaining})
                return
        if it.identifier == itemConstants.GOOD_EXTRALIFE:
            self.lives += 1
            self.field.log(_("Extra life! (now %(lives)d lives)") % {"lives": self.lives})
            s = bgtsound.sound()
            s.load(globalVars.appMain.sounds["extraLife.ogg"])
            s.pitch = 60 + (self.lives * 10)
            s.play()
            if self.plantMode is True:
                self.reviveFromPlantMode()
            # end revive
            return
        if it.identifier == itemConstants.GOOD_INSTANTUNLOCK:
            existing = self.findEffect(
                itemConstants.NAMES[itemConstants.TYPE_GOOD][itemConstants.GOOD_INSTANTUNLOCK])
            if existing is None:
                e = itemEffects.InstantUnlockEffect()
                e.initialize(self)
                e.activate(self.field.modeHandler)
                self.itemEffects.append(e)
            else:
                existing.extend(itemConstants.BASE_EFFECT_TIME)
            # end if existing
            return
        if it.identifier == itemConstants.GOOD_RESETENEMIES:
            self.field.resetEnemies()
            return

    def getScoreMultiplier(self):
        """Returns the multiplier which is currently applied to every point
        this player gains. Returns 1 when no score multiplier effect is active.

        :rtype: int
        """
        multiplier = 1
        for elem in self.itemEffects:
            if elem.scoreMultiplier > multiplier:
                multiplier = elem.scoreMultiplier
        return multiplier

    def removeItemEffects(self, effectType=None):
        """Immediately ends (deactivates) active item effects. Used by the
        cheat keys. Returns the names of the effects which have been ended.

        :param effectType: If given, only the effects of this type (TYPE_GOOD or
                           TYPE_NASTY) are ended. Otherwise every active effect
                           is ended.
        :type effectType: int
        :rtype: list
        """
        removed = []
        for elem in self.itemEffects[:]:
            if getattr(elem, "permanent", False):
                continue  # the vegetable slow down ends only with the state
            # end permanent
            if effectType is not None and elem.effectType != effectType:
                continue
            elem.deactivate(self.field.modeHandler)  # announces its end
            self.itemEffects.remove(elem)
            removed.append(elem.name)
        # end for
        return removed

    def findEffect(self, name):
        """
        Checks whether this player has the specified effect currently active.

        :param name: Name of the effect to search(Blurred, Megaton Punch, etc).
        :type name: str

        :rtype: bool
        """
        for elem in self.itemEffects:
            if elem.name == name:
                return elem
        return None

    def setPunchRange(self, r):
        """
        Changes this player's effective punch length.

        :param r: New range.
        :type r: int
        """
        previous = self.punchRange
        self.field.log(_("The effective range of your Punch is now %(range)d (from %(from)d)") % {"range": r, "from": previous})
        self.punchRange = r

    def setPunchSpeed(self, s):
        """
        Changes this player's punching speed.

        :param s: New speed in milliseconds.
        :type s: int
        """
        previous = self.punchSpeed
        self.field.log(_("The speed of your punch is now %(speed)d milliseconds (from %(from)d)") % {"speed": s, "from": previous})
        self.punchSpeed = s

    def setPenetration(self, p):
        """
        Sets whether this player's punches penetrate.

        :param p: Penetrate?
        :type p: bool
        """
        if p is True:
            self.field.log(_("Your punches now penetrate enemies and items!"))
        else:
            self.field.log(_("Your punches no longer penetrate enemies and items!"))
        self.penetrate = p

    def calcHitPercentage(self):
        """Calculates the hitting percentage of this player and updates the hitPercentage property."""
        self.hitPercentage = self.hits / self.punches * 100

    def moveTo(self, p):
        """
        Moves this player to the specified position.

        :param p: New position.
        :type p: int
        """
        self.x = p
        s = bgtsound.sound()
        s.load(globalVars.appMain.sounds["change.ogg"])
        s.pan = self.field.getPan(self.x)
        s.play()

    def hit(self):
        """Called when this player gets hit by one of the enemies. Returns true when the attack succeeds, or False if player attacks back with auto destruction."""
        if self.autoDestructionRemaining > 0:
            self.autoDestructionRemaining -= 1
            self.field.log(_("You're about to be attacked, but you have a counter!"))
            self.field.startDestruction()

            return False
        # end auto destruction
        if self.dying is True or self.dead is True:
            # Already screaming / falling: further attacks change nothing.
            return False
        # end dying
        if self.plantMode is True:
            # A vegetable is not slapped any more; the attacker dies instead.
            return False
        # end plant
        self.lives -= 1
        self.field.log(_("You've been slapped! (%(lives)d HP remaining)") % {"lives": self.lives})
        s = bgtsound.sound()
        if self.lives > 0:
            s.load(globalVars.appMain.sounds["attacked.ogg"])
            s.play()
            return True
        # end survived
        if self.lives <= 0:
            # The last life is gone: scream first, fall down later. Pressing U
            # while screaming refuses death (see enterPlantMode).
            self.lives = 0
            self.startDeath()
            return False
        # end dying

    def addScore(self, score):
        """
        Add a specified amount of score to this player. Also checks for high score.

        :param score: Score to add.
        :type score: int
        """
        multiplier = self.getScoreMultiplier()
        if score > 0 and multiplier > 1:
            multiplied = score * multiplier
            self.field.log(_("Score multiplier x%(multiplier)d! %(fromscore).1f points became %(toscore).1f points.") %
                           {"multiplier": multiplier, "fromscore": score, "toscore": multiplied})
            score = multiplied
        self.score += score
        self.score_validator.append(score)
        if self.gotHighscore is False and self.score >= self.lastHighscore:
            self.processHighscore()
        which = _("added")
        if score <= 0:
            which = _("subtracted")
        self.field.log(_("Point: %(added).1f %(changestr)s (%(total).1f)") % {"added": score, "changestr": which, "total": self.score})
    # end addScore

    def processHighscore(self):
        """Plays the highscore sound and logs that this player has achieved high score."""
        bgtsound.playOneShot(globalVars.appMain.sounds["highscore.ogg"])
        self.gotHighscore = True
    # end processHighscore

    def getNewHighscore(self):
        """Returns the new high score if this player got one, otherwise None."""
        return None if self.gotHighscore is False else int(self.score)
    # end getNewHighscore

    def getPreviousHighscore(self):
        """Retrieves the previous high score. If this player has achieved a new high score, the previous one is returned. Otherwise, the currently standing highscore is returned.

        :rtype: int
        """
        return self.lastHighscore
    # end getPreviousHighscore

    def setPaused(self, p):
        """Pauses this player."""
        if p == self.paused:
            return
        self.paused = p
        for elem in self.itemEffects:
            elem.setPaused(p)
        # end item effects
        self.punchTimer.setPaused(p)
        self.deathTimer.setPaused(p)
    # end pause


# end class Player
