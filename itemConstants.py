# -*- coding: utf-8 -*-
# Screaming Strike item constant values
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# License: GPL V2.0 (See copying.txt for details)
STATE_ALIVE = 0
STATE_BROKEN = 1
STATE_SHOULDBEDELETED = 2

BASE_EFFECT_TIME = 15000
TYPE_NASTY = 0
TYPE_GOOD = 1

NASTY_SHRINK = 0
NASTY_BLURRED = 1
NASTY_SLOWDOWN = 2
NASTY_REWIND = 3
NASTY_MAX = 3

GOOD_MEGATONPUNCH = 0
GOOD_BOOST = 1
GOOD_PENETRATION = 2
GOOD_DESTRUCTION = 3
GOOD_EXTRALIFE = 4
GOOD_RESETENEMIES = 5
GOOD_SCOREMULTIPLIER = 6
GOOD_INSTANTUNLOCK = 7
GOOD_MAX = 7

# Good items which are allowed to drop randomly (arcade mode's automatic item
# spawning and the "h" debug key). The reset enemies item is deliberately
# excluded from this list: it may only be summoned with the g key. The score
# multiplier item is excluded as well: multiplying every point gain is far too
# strong to be left to the automatic item spawning, so it may only be started
# with the "." cheat key. The instant unlock item is key only as well, since
# unlocking a scream with a single punch is much too strong for random drops.
GOOD_RANDOM_ITEMS = [GOOD_MEGATONPUNCH, GOOD_BOOST, GOOD_PENETRATION,
                     GOOD_DESTRUCTION, GOOD_EXTRALIFE]

# "Vegetable" (plant) state. When the player's last life is taken away, the
# player screams and only afterwards falls down, exactly like before. Pressing U
# while the scream is audible refuses death and turns the player into a
# vegetable instead: the player cannot punch or move any more, and every enemy
# which reaches the player's position dies on the spot. The vegetable state has
# no duration: it goes on until the player eats an extra life item (revived) or
# presses shift+U (gives up and dies).
DEATH_PHASE_SCREAM = 0
DEATH_PHASE_FALL = 1
# Milliseconds the scream lasts at least, so that U can be pressed even when the
# scream itself is short.
DEATH_SCREAM_TIME = 2500
# Upper limit of the scream phase in case the scream sound never reports that it
# has finished playing.
DEATH_SCREAM_MAX_TIME = 6000
DEATH_FALL_TIME = 900  # milliseconds between hitting the ground and game over
# Enemies at this distance or closer die on their own. 0 means the enemy has to
# reach the vegetable's own position.
PLANT_KILL_RANGE = 0

# Cheat multipliers. Pressing v multiplies the remaining time of all active good
# effects by this value, and the score multiplier effect multiplies every point
# gain by the score value.
EFFECT_TIME_CHEAT_MULTIPLIER = 100
SCORE_CHEAT_MULTIPLIER = 10000

# Rewind (fast-forward) nasty item. Obtaining it accelerates the whole game:
# the music, every sound effect and the in-game time itself are sped up
# together. The pitch climbs for about REWIND_RAMP_TIME milliseconds, at
# exactly the same rate as the music pitch descends when a game ends (see
# ssAppMain.resetMusicPitch: REWIND_PITCH_STEP percent per
# REWIND_PITCH_STEP_INTERVAL milliseconds), and it descends at the same rate
# again when the effect ends.
REWIND_PITCH_NORMAL = 100
REWIND_PITCH_STEP = 2
REWIND_PITCH_STEP_INTERVAL = 100
REWIND_RAMP_TIME = 3000
REWIND_PITCH_TARGET = REWIND_PITCH_NORMAL + int(REWIND_RAMP_TIME / REWIND_PITCH_STEP_INTERVAL) * REWIND_PITCH_STEP

NAMES = {}
NAMES[TYPE_NASTY] = {NASTY_SHRINK: "Shrink",
                     NASTY_BLURRED: "Blurred", NASTY_SLOWDOWN: "Slow down",
                     NASTY_REWIND: "Rewind"}
NAMES[TYPE_GOOD] = {GOOD_MEGATONPUNCH: "Megaton punch", GOOD_BOOST: "Boost",
                    GOOD_PENETRATION: "Penetration", GOOD_DESTRUCTION: "Destruction", GOOD_EXTRALIFE: "Extra life",
                    GOOD_RESETENEMIES: "Reset enemies",
                    GOOD_SCOREMULTIPLIER: "Score multiplier",
                    GOOD_INSTANTUNLOCK: "Instant unlock"}
