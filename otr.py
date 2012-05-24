"""
    Document   : otr.py
    Package    : OTR Integration to XBMC
    Author     : Frank Epperlein
    Copyright  : 2012, Frank Epperlein, DE
    License    : Gnu General Public License 2
    Description: Main program script for package
"""

import os
import sys

#set our library path
sys.path.insert(0, xbmc.translatePath( os.path.join( os.getcwd(), 'resources', 'lib' ) ) )

# local version as bugfix for http://bugs.python.org/issue9374
import urlparse

import xbmcplugin
import xbmc_otr as worker

_url = urlparse.urlparse("%s%s#%s" % (sys.argv[0], sys.argv[2], sys.argv[1]))

housekeeper = worker.housekeeper(_url)
creator = worker.creator(_url)
sender = worker.sender(_url)

housekeeper.start()
sender.send(creator.get(housekeeper.getOTR()))
xbmcplugin.endOfDirectory(int(_url.fragment))
housekeeper.end()
