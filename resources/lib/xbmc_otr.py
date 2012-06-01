# vim: tabstop=4 shiftwidth=4 smarttab expandtab softtabstop=4 autoindent

"""
    Document   : xbmc_otr.py
    Package    : OTR Integration to XBMC
    Author     : Frank Epperlein
    Copyright  : 2012, Frank Epperlein, DE
    License    : Gnu General Public License 2
    Description: Worker class library
"""
#make xbmc and system modules available
import os
import subprocess
import xbmc
import xbmcplugin
import xbmcaddon
import xbmcgui
import OtrHandler
import logging
import urllib
try:
    from cgi import parse_qs
except ImportError:
    from urlparse import parse_qs
    
logger = logging.getLogger()

__TITLE__ = 'onlinetvrecorder.com'
__THUMBURL__ = 'http://thumbs.onlinetvrecorder.com/'


def getKey(obj, *elements):
    for element in elements:
        if element in obj:
            obj = obj[element]
        else:
            return False
    return obj

def getSizeStr(size):
    """
    Wandelt einen Groessenangabe in Bytes in einen String mit passender
    Menschenlesbaren Groessenangabe um.

    @param size: Groesse in Bytes
    @type  size: number
    """
    if   int(size) > 1099511627776: return "%.3f TB" % float(int(size) / 1099511627776.0)
    elif int(size) > 1073741824: return "%.3f GB" % float(int(size) / 1073741824.0)
    elif int(size) > 1048576: return "%.3f MB" % float(int(size) / 1048576.0)
    elif int(size) > 1024: return "%.3f KB" % float(int(size) / 1024.0)
    else: return "%d Bytes" % int(size)


def _(x, s):
    translations = {
        'missing login credentials': 30300,
        'login failed (%s)': 30301,
        'loading recording list': 30302,
        'recordings': 30303,
        'archive': 30304,
        'delete': 30305,
        }
    if s in translations:
        return x.getLocalizedString(translations[s]) or s
    return s


#define classes
class housekeeper:
    """
    Run any startup required for the addon
    """
    _xbmcaddon = None
    _url = None
    _otr = None


    def __init__(self, url):
        """
        constructor
        @param int pluginId - Current instance of plugin identifer
        """
        self._url = url
        self._xbmcaddon = xbmcaddon.Addon(id=url.netloc)

    def getOTR(self):
        if self._otr:
            return self._otr
        else:
            raise Exception('otr is None')

    def start(self):
        """
        Run the startup
        """

        username = self._xbmcaddon.getSetting('otrUsername')
        password = self._xbmcaddon.getSetting('otrPassword')
        if not len(username) or not len(password):
            xbmcgui.Dialog().ok(
               __TITLE__,
               _(self._xbmcaddon, 'missing login credentials') )
            raise Exception("missing login credentials")


        self._otr = OtrHandler.OtrHandler()
        try:
            #self._otr.getUserInfoDict(username)
            print(self._otr.getUserInfoDict(username))
            forced_errrrrrrrror
        except Exception, f:
            try:
                self._otr.login(username, password)
                pass
            except Exception, e:
                xbmcgui.Dialog().ok(
                    __TITLE__,
                    _(self._xbmcaddon, 'login failed (%s)')  % str(e) )
                raise Exception(e)
            else:
                print("otr login successful")
                print(self._otr.getUserInfoDict(username))

    
    def end(self):
        """
        Run the end processes
        """
        pass

class creator:
    """
    Responsible for creating the list of items that will get displayed
    """
    _xbmcaddon = None
    _url = None

    def __init__(self, url):
        """
        constructor
        @param int pluginId - Current instance of plugin identifer
        """
        self._url = url
        self._xbmcaddon = xbmcaddon.Addon(id=url.netloc)

    def _createList(self, otr, scope):
        """
        Create the dynamic list of all content
        @param list dirContent - list of __PLAYLIST__ files in gpodder directory
        @param string dir - gpodder directory location
        @access private
        @return list
        """

        def getListItemFromElement(element, fileinfo):

            def getImageUrl(filename):
                url = __THUMBURL__
                url += filename.split('TVOON_DE')[0]
                url += 'TVOON_DE'
                url += '____'
                return url

            label = element['TITLE']
            if 'BEGIN' in element:
                label += " (%s)" % element['BEGIN']
            li = xbmcgui.ListItem(
                label=label,
                label2=element['FILENAME'],
                iconImage='%s1.jpg' % getImageUrl(element['FILENAME']),
                thumbnailImage='%sA.jpg' % getImageUrl(element['FILENAME']) )
            infos= {}
            infos['size'] = long(fileinfo['size'])
            infos['plot'] = "%s GWP (%s, %s, %s)\n" % (
                fileinfo['cost'], 
                fileinfo['type'].replace('_', ' '), 
                fileinfo['stream'],
                getSizeStr(infos['size']*1024) )
            if 'DURATION' in element: infos['duration'] = element['DURATION'].split()[0]
            if 'DOWNLOADCOUNT' in element: infos['playcount'] = int(element['DOWNLOADCOUNT'])
            if 'TITLE' in element: infos['title'] = element['TITLE']
            if 'STATION' in element: infos['studio'] = element['STATION']
            if 'BEGIN' in element: infos['date'] = element['BEGIN']
            if 'TITLE2' in element: infos['plot'] += "\n%s" % element['TITLE2']
            li.setInfo('video', infos)
            li.addContextMenuItems(
                [ ( _(self._xbmcaddon, 'delete'), 
                    "XBMC.RunPlugin(%s://%s/%s?epgid=%s)" % (
                        self._url.scheme,
                        self._url.netloc,
                        'deletejob',
                        element['EPGID']), ),
                ] )
            return li


        def getFileInfo(element):
            streams = ['MP4_Stream', 'MP4']
            if self._xbmcaddon.getSetting('otrPreferCut') == 'true':
                streams.insert(0, 'MP4_geschnitten')
            if self._xbmcaddon.getSetting('otrPreferHQ') == 'true':
                streams.insert(0, 'HQMP4') 
                streams.insert(0, 'HQMP4_Stream')
                if self._xbmcaddon.getSetting('otrPreferCut') == 'true':
                    streams.insert(0, 'HQMP4_geschnitten')
            if self._xbmcaddon.getSetting('otrPreferHD') == 'true':
                streams.insert(0, 'HDMP4') 
                streams.insert(0, 'HDMP4_Stream')
                if self._xbmcaddon.getSetting('otrPreferCut') == 'true':
                    streams.insert(0, 'HDMP4_geschnitten')
            elementinfo = otr.getFileInfoDict(element['ID'], element['EPGID'], element['FILENAME'])
            for stream in streams: 
                if getKey(elementinfo, stream): break
            stype = ( (getKey(elementinfo, stream, 'FREE') and 'FREE') or
                      (getKey(elementinfo, stream, 'PRIO') and 'PRIO') or False ) 
            if not stype: 
                return False
            else:
                size = getKey(elementinfo, stream, 'SIZE')
                uri  = getKey(elementinfo, stream, stype)
                gwp  = getKey(elementinfo, stream, 'GWPCOSTS', stype)
            return {'uri':uri, 'type': stype, 'cost': gwp, 'size':size, 'stream':stream}

        prdialog = xbmcgui.DialogProgress()
        prdialog.create(_(self._xbmcaddon, 'loading recording list'))
        prdialog.update(0)

        try:
            recordings = otr.getRecordListDict(scope, orderby="time_desc")
        except Exception, e:
            prdialog.close()
            xbmcgui.Dialog().ok(__TITLE__, str(e))
            return []
        else:
            listing = []
            recordings = getKey(recordings, 'FILE') or []
            if not isinstance(recordings, list): recordings = [recordings]
            for element in recordings:
                percent = int((recordings.index(element)+1)*100/len(recordings))
                prdialog.update(percent, element['FILENAME'])
                try:
                    fileinfo = getFileInfo(element)
                except Exception, e:
                    xbmcgui.Dialog().ok(element['FILENAME'], str(e))
                else:
                    listing.append([ fileinfo['uri'], getListItemFromElement(element, fileinfo), False ])

            prdialog.close()
            return listing

    def createDir(self, subs):
        listing = []
        for element in subs:
            listing.append( [
                "%s://%s/%s/%s" % (
                    self._url.scheme,
                    self._url.netloc,
                    self._url.path,
                    element),
                xbmcgui.ListItem( label=_(self._xbmcaddon, element) ),
                True] )
        return listing

    def _createRecordingList(self, otr): return self._createList(otr, 'recordings')

    def _createArchiveList(self, otr): return self._createList(otr, 'archive')
        

    def _deleteJob(self, otr):
        print(otr.deleteJob( self._xbmcaddon.getSetting('otrUsername'), parse_qs(self._url.query)['epgid'].pop() ))
        xbmc.executebuiltin("Container.Refresh")
        return []

    def get(self, otr):
        """
        Refresh and retrieve the current list for display
        @access public
        @returns list
        @usage      c=example2.creator()
                    list = c.get()
        """

        path =  {
                '': ['recordings', 'archive'],
                'recordings': self._createRecordingList,
                'archive': self._createArchiveList,
                'deletejob': self._deleteJob,
                }

        #get the list
        sub = getKey(path, *self._url.path.strip('/').split('/'))
        if isinstance(sub, list):
            return self.createDir(sub)
        else:
            return sub(otr)

class sender:
    """
    Responsible for sending output to XBMC
    """
    # current instance of plugin identifer
    _url = None
 
    def __init__(self, url):
        """
        constructor
        @parm int pluginId - current instance of plugin identifer
        """
        self._url=url


    def send(self,listing):
        """
        Send output to XBMC
        @param list listing - the list of items to display
        @return void
        """
        for item in listing:
            xbmcplugin.addDirectoryItem(int(self._url.fragment), item[0], item[1], item[2])
