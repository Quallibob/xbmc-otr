__author__ = 'fep'

import xbmc
from translations import _


class Simplebmc:

    def Notification(self, title, text, duration=False, img=False):
        if not duration:
            duration = 8
        if not img:
            img = "False"
        duration = int(duration)*1000
        print "%s: %s" % (title, str(text))
        return xbmc.executebuiltin('Notification("%s", "%s")' % (title, _(str(text))))