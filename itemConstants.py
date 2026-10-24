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
NASTY_MAX = 2

GOOD_MEGATONPUNCH = 0
GOOD_BOOST = 1
GOOD_PENETRATION = 2
GOOD_DESTRUCTION = 3
GOOD_EXTRALIFE = 4
GOOD_RESETENEMIES = 5
GOOD_SCOREMULTIPLIER = 6
GOOD_MAX = 6

# Good items which are allowed to drop randomly (arcade mode's automatic item
# spawning and the "h" debug key). The reset enemies item is deliberately
# excluded from this list: it may only be summoned with the g key.
GOOD_RANDOM_ITEMS = [GOOD_MEGATONPUNCH, GOOD_BOOST, GOOD_PENETRATION,
                     GOOD_DESTRUCTION, GOOD_EXTRALIFE, GOOD_SCOREMULTIPLIER]

# Cheat multipliers. Pressing v multiplies the remaining time of all active good
# effects by this value, and the score multiplier effect multiplies every point
# gain by the score value.
EFFECT_TIME_CHEAT_MULTIPLIER = 100
SCORE_CHEAT_MULTIPLIER = 10000
NAMES = {}
NAMES[TYPE_NASTY] = {NASTY_SHRINK: "Shrink",
                     NASTY_BLURRED: "Blurred", NASTY_SLOWDOWN: "Slow down"}
NAMES[TYPE_GOOD] = {GOOD_MEGATONPUNCH: "Megaton punch", GOOD_BOOST: "Boost",
                    GOOD_PENETRATION: "Penetration", GOOD_DESTRUCTION: "Destruction", GOOD_EXTRALIFE: "Extra life",
                    GOOD_RESETENEMIES: "Reset enemies",
                    GOOD_SCOREMULTIPLIER: "Score multiplier"}
