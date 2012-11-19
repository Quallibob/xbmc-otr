__author__ = 'fep'

import xbmc
import xbmcgui
import urllib
from resources.lib.Translations import _


class Simplebmc:

    def Notification(self, title, text, duration=False, img=False):
        if not duration:
            duration = 8
        if not img:
            img = "False"
        duration = int(duration)*1000
        print "%s: %s" % (title, str(text))
        return xbmc.executebuiltin('Notification("%s", "%s", %s, %s)' % (title, _(str(text)), duration, img))

    def Downloader(self, url, dest, progress=True):
        if progress:
            dp = xbmcgui.DialogProgress()
            dp.create("Download", url.split('/').pop())
            urllib.urlretrieve(url,dest,lambda nb, bs, fs, url=url: self._pbhook(nb,bs,fs,dp))
        else:
            urllib.urlretrieve(url,dest)

    def _pbhook(self, numblocks, blocksize, filesize, dp=None):
        try:
            percent = min((numblocks*blocksize*100)/filesize, 100)
            dp.update(percent)
        except Exception, e:
            xbmc.log(str(e))
            dp.close()
        if dp.iscanceled():
            dp.close()
            raise Exception('download canceled')