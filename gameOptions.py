# -*- coding: utf-8 -*-
# Screaming Strike game options handler
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# License: GPL V2.0 (See copying.txt for details)
import glob
import locale
import os
import pickle


class GameOptions:
    def __init__(self):
        self.BGMVOLUME_NEGATIVE_BOUNDARY = -30
        self.BGMVOLUME_POSITIVE_BOUNDARY = 0
        self.SFXVOLUME_NEGATIVE_BOUNDARY = -30
        self.SFXVOLUME_POSITIVE_BOUNDARY = 0
        self.LEFTPANNINGLIMIT_NEGATIVE_BOUNDARY = -100
        self.LEFTPANNINGLIMIT_POSITIVE_BOUNDARY = -20
        self.RIGHTPANNINGLIMIT_NEGATIVE_BOUNDARY = 20
        self.RIGHTPANNINGLIMIT_POSITIVE_BOUNDARY = 100

    def __del__(self):
        pass

    def initialize(self, importer):
        if isinstance(importer, GameOptions):
            self.copyFrom(importer)
        elif isinstance(importer, str):
            self.load(importer)
        else:
            self.setDefault()

    def setDefault(self):
        self.bgmVolume = -10
        self.sfxVolume = 0
        self.leftPanningLimit = -100
        self.rightPanningLimit = 100
        self.itemVoice = "chris"
        self.language = self.detectLanguage()

    def detectLanguage(self):
        """Detects the language of the system and returns a locale folder name
        which actually exists in the game.

        The system may report a bare language code (ko), an encoding qualified
        name (ko_KR.UTF-8) or a platform specific name (Korean_Korea on some
        Windows setups), so the exact name is tried first and then the language
        part is matched against the installed locales.

        :rtype: str
        """
        detected = None
        try:
            detected = locale.getdefaultlocale()[0]
        except (TypeError, ValueError):
            # Some platforms report a language name which the locale module
            # cannot parse (Windows reports e.g. Korean_Korea), so fall back to
            # the raw environment and normalise it below.
            for name in ("LC_ALL", "LC_CTYPE", "LANG", "LANGUAGE"):
                if os.environ.get(name):
                    detected = os.environ[name]
                    break
        # end try
        if detected is None:
            return "en_US"  # OSX may fail to auto language detect when frozen
        detected = detected.split(":")[0].split(".")[0].replace("-", "_").strip()
        if os.path.isdir("locale/%s" % detected):
            return detected
        code = detected[0:2].lower()
        for elem in sorted(glob.glob("locale/*")):
            if not os.path.isdir(elem):
                continue
            name = os.path.basename(elem)
            if name[0:2].lower() == code:
                return name
        # end for
        return "en_US"  # No such locale in the game
    # end detectLanguage

    def copyFrom(self, importer):
        self.bgmVolume = importer.bgmVolume
        self.sfxVolume = importer.sfxVolume
        self.leftPanningLimit = importer.leftPanningLimit
        self.rightPanningLimit = importer.rightPanningLimit
        self.itemVoice = importer.itemVoice
        self.language = importer.language

    def load(self, filename):
        if os.path.isfile(filename) is not True:
            self.setDefault()
            self.save(filename)
            return False
        with open(filename, mode='r') as f:
            values = f.read().split("#")
        # end with
        numValues = len(values)
        self.bgmVolume = int(values[0])
        if self.bgmVolume < self.BGMVOLUME_NEGATIVE_BOUNDARY:
            self.bgmVolume = self.BGMVOLUME_NEGATIVE_BOUNDARY
        if self.bgmVolume > self.BGMVOLUME_POSITIVE_BOUNDARY:
            self.bgmVolume = self.BGMVOLUME_POSITIVE_BOUNDARY
        self.leftPanningLimit = int(values[1])
        if self.leftPanningLimit < self.LEFTPANNINGLIMIT_NEGATIVE_BOUNDARY:
            self.leftPanningLimit = self.LEFTPANNINGLIMIT_NEGATIVE_BOUNDARY
        if self.leftPanningLimit > self.LEFTPANNINGLIMIT_POSITIVE_BOUNDARY:
            self.leftPanningLimit = self.LEFTPANNINGLIMIT_POSITIVE_BOUNDARY
        self.rightPanningLimit = int(values[2])
        if self.rightPanningLimit > self.RIGHTPANNINGLIMIT_POSITIVE_BOUNDARY:
            self.rightPanningLimit = self.RIGHTPANNINGLIMIT_POSITIVE_BOUNDARY
        if self.rightPanningLimit < self.RIGHTPANNINGLIMIT_NEGATIVE_BOUNDARY:
            self.rightPanningLimit = self.RIGHTPANNINGLIMIT_NEGATIVE_BOUNDARY
        self.itemVoice = values[3]
        self.language = values[4] if numValues > 4 else locale.getdefaultlocale()[0]
        self.sfxVolume = int(values[5]) if numValues > 5 else 0
        if self.sfxVolume < self.SFXVOLUME_NEGATIVE_BOUNDARY:
            self.sfxVolume = self.SFXVOLUME_NEGATIVE_BOUNDARY
        if self.sfxVolume > self.SFXVOLUME_POSITIVE_BOUNDARY:
            self.sfxVolume = self.SFXVOLUME_POSITIVE_BOUNDARY
        return True

    def save(self, filename):
        s = "%d#%d#%d#%s#%s#%d" % (self.bgmVolume, self.leftPanningLimit, self.rightPanningLimit, self.itemVoice, self.language, self.sfxVolume)
        with open(filename, mode="w") as f:
            f.write(s)
