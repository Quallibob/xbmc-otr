# vim: tabstop=4 shiftwidth=4 smarttab expandtab softtabstop=4 autoindent

"""
    Document   : xbmc_otr.py
    Package    : OTR Integration to XBMC
    Author     : Frank Epperlein
    Copyright  : 2012, Frank Epperlein, DE
    License    : Gnu General Public License 2
    Description: Worker class library
"""

import os
import sys
import subprocess
import xbmc
import xbmcplugin
import xbmcaddon
import xbmcgui
import CommonFunctions
import OtrHandler
import logging
import urllib
import base64

try:
    from cgi import parse_qs
except ImportError:
    print "parse_qs not in cgi"
    from urlparse import parse_qs
    


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
    """
    Versucht einen nicht-lokalisierten String zu uebersetzen.

    @param x: addon das befragt werden soll
    @type  x: xbmcaddon.Addon Instance
    @param s: unlokalisierter String
    @type  s: string
    """
    translations = {
        'missing login credentials': 30300,
        'login failed (%s)': 30301,
        'loading recording list': 30302,
        'recordings': 30303,
        'archive': 30304,
        'delete': 30305,
        'play': 30306,
        'refresh listing': 30307,
        'userinfo': 30308,
        'status: %s (until %s)': 30309,
        'decodings left: %s, gwp left: %s': 30310,
        'loading recording list failed (%s)': 30311,
        'new version available': 30312,
        'search': 30313,
        'scheduling': 30314,
        'searchpast': 30315,
        'searchfuture': 30316,
        'schedule job?': 30317,
        'scheduleJob: OK': 30318,
        'scheduleJob: DOUBLE': 30319,
        'pasthighlights': 30320,
        'downloadqueue': 30321,
        'queueposition %s': 30322,
        }
    if s in translations:
        return x.getLocalizedString(translations[s]) or s
    print("untranslated: %s" % s)
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
        """
        Liefert die geladene OTR instanz zurueck.
        """
        if self._otr:
            return self._otr
        else:
            raise Exception('otr is None')

    def start(self):
        """
        Run the startup
        """

        # login infos auslesen
        username = self._xbmcaddon.getSetting('otrUsername')
        password = self._xbmcaddon.getSetting('otrPassword')
        if not len(username) or not len(password):
            xbmcgui.Dialog().ok(
               __TITLE__,
               _(self._xbmcaddon, 'missing login credentials') )
            raise Exception("missing login credentials")


        # login
        try:
            # hanlder instanz laden
            self._otr = OtrHandler.OtrHandler()
        except Exception, e:
            print "login failed (1)"
            xbmcgui.Dialog().ok(
                __TITLE__,
                _(self._xbmcaddon, 'login failed (%s)')  % str(e) )
            sys.exit(0)
        else:
            try:
                # eigentlicher login
                self._otr.login(username, password)
            except Exception, e:
                print "login failed (2)"
                xbmcgui.Dialog().ok(
                    __TITLE__,
                    _(self._xbmcaddon, 'login failed (%s)')  % str(e) )
                sys.exit(0)
            else:
                print("otr login successful")

    
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
    _common = None

    def __init__(self, url):
        """
        constructor
        @param int pluginId - Current instance of plugin identifer
        """
        self._url = url
        self._xbmcaddon = xbmcaddon.Addon(id=url.netloc)
        self._common = CommonFunctions

    def _createList(self, otr, scope):
        """
        Create the dynamic list of all content
        @param list dirContent - list of __PLAYLIST__ files in gpodder directory
        @param string dir - gpodder directory location
        @access private
        @return list
        """

        def getListItemFromElement(element, fileinfo):
            """
            generiert xbmcgui.ListItem fuer ein element

            @param element: elementDict vom OtrHandler
            @type  element: dict
            @param fileinfo: fileinfoDict vom OtrHandler
            @type  fileinfo: dict
            """

            def getImageUrl(filename):
                """
                liefert generierte thumbnail url zurueck
                """
                url = __THUMBURL__
                url += filename.split('TVOON_DE')[0]
                url += 'TVOON_DE'
                url += '____'
                return url

            label = element['TITLE']
            if 'BEGIN' in element:
                # zeitangabe vorhanden
                label += " (%s)" % element['BEGIN']

            # listelement erzeugen
            li = xbmcgui.ListItem(
                label=label,
                label2=element['FILENAME'],
                iconImage='%s1.jpg' % getImageUrl(element['FILENAME']),
                thumbnailImage='%sA.jpg' % getImageUrl(element['FILENAME']) )

            # infos aggregieren
            infos= {}
            infos['size'] = long(fileinfo['size'])
            infos['plot'] = "%s GWP (%s, %s, %s)\n" % (
                fileinfo['cost'], 
                fileinfo['type'].replace('_', ' '), 
                fileinfo['stream'].replace('_', ' '),
                getSizeStr(infos['size']*1024) )
            if 'DURATION' in element: infos['duration'] = element['DURATION'].split()[0]
            if 'DOWNLOADCOUNT' in element: infos['playcount'] = int(element['DOWNLOADCOUNT'])
            if 'TITLE' in element: infos['title'] = element['TITLE']
            if 'STATION' in element: infos['studio'] = element['STATION']
            if 'BEGIN' in element: infos['date'] = element['BEGIN']
            if 'TITLE2' in element: infos['plot'] += "\n%s" % element['TITLE2']
            li.setInfo('video', infos)

            # contextmenue erzeuegen
            li.addContextMenuItems(
                [ 
                  ( _(self._xbmcaddon, 'play'), 
                    "PlayWith()" ),
                  ( _(self._xbmcaddon, 'delete'), 
                    "XBMC.RunPlugin(%s://%s/%s?epgid=%s)" % (
                        self._url.scheme,
                        self._url.netloc,
                        'deletejob',
                        element['EPGID']), ),
                  ( _(self._xbmcaddon, 'refresh listing'), 
                    "Container.Refresh" ),
                  ( _(self._xbmcaddon, 'userinfo'), 
                    "XBMC.RunPlugin(%s://%s/%s)" % (
                        self._url.scheme,
                        self._url.netloc,
                        'userinfo' ),)
                ], replaceItems=True )

            return li


        def getFileInfo(element):

            # streamauswahl
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

            # fileinfoDict abfragen
            elementinfo = otr.getFileInfoDict(element['ID'], element['EPGID'], element['FILENAME'])
            for stream in streams: 
                if getKey(elementinfo, stream): break
            if  self._xbmcaddon.getSetting('otrPreferPrio') == 'true':
                stype = ( (getKey(elementinfo, stream, 'PRIO') and 'PRIO') or
                          (getKey(elementinfo, stream, 'FREE') and 'FREE') or False )
            else:
                stype = ( (getKey(elementinfo, stream, 'FREE') and 'FREE') or
                          (getKey(elementinfo, stream, 'PRIO') and 'PRIO') or False )

            if not stype: 
                return False
            else:
                size = getKey(elementinfo, stream, 'SIZE')
                fileuri  = getKey(elementinfo, stream, stype)
                uri = "%s://%s/%s?fileuri=%s" % (
                    self._url.scheme,
                    self._url.netloc,
                    'play',
                    base64.urlsafe_b64encode(fileuri))
                gwp  = getKey(elementinfo, stream, 'GWPCOSTS', stype)

            # aggergieren und ausliefern
            return {'uri':uri, 'type': stype, 'cost': gwp, 'size':size, 'stream':stream}

        # progressdialog erzeuegen
        prdialog = xbmcgui.DialogProgress()
        prdialog.create(_(self._xbmcaddon, 'loading recording list'))
        prdialog.update(0)

        try:
            # eigentliche Liste abfragen
            recordings = otr.getRecordListDict(scope, orderby="time_desc")
        except Exception, e:
            print "loading recording list failed (%s)" % str(e)
            prdialog.close()
            xbmcgui.Dialog().ok(
                    __TITLE__, 
                    _(self._xbmcaddon, 'loading recording list failed (%s)' % str(e)) )
            return []
        else:
            listing = []
            recordings = getKey(recordings, 'FILE') or []
            if not isinstance(recordings, list): 
                # liste hat nur einen eintrag
                recordings = [recordings]

            for element in recordings:

                # progressdialog updaten
                percent = int((recordings.index(element)+1)*100/len(recordings))
                if prdialog.iscanceled(): return listing
                prdialog.update(percent, element['FILENAME'])

                try:
                    # fileinfoDict abfragen
                    fileinfo = getFileInfo(element)
                except Exception, e:
                    print "getFileInfo failed (%s)" % str(e)
                    xbmc.executebuiltin('Notification("%s", "%s")' % (element['FILENAME'], str(e)))
                else:
                    listing.append([ fileinfo['uri'], getListItemFromElement(element, fileinfo), False ])

            # progressdialog abschliessen
            prdialog.close()
            return listing


    def createDir(self, subs):
        """
        dir listing fuer uebersichten erzeugen

        @param subs: listenelemente
        @type  subs: list
        """
        listing = []
        for element in subs:
            li = xbmcgui.ListItem( label=_(self._xbmcaddon, element) )
            li.addContextMenuItems(
                [ 
                  ( _(self._xbmcaddon, 'refresh listing'), 
                    "Container.Refresh" ),
                  ( _(self._xbmcaddon, 'userinfo'), 
                    "XBMC.RunPlugin(%s://%s/%s)" % (
                        self._url.scheme,
                        self._url.netloc,
                        'userinfo' ),)
                ], replaceItems=True )
            listing.append( [
                "%s://%s/%s/%s" % (
                    self._url.scheme,
                    self._url.netloc,
                    self._url.path,
                    element),
                li,
                True] )
        return listing

    def _createRecordingList(self, otr): 
        """
        wrapper um createList fuer recordings aufzurufen

        @param otr: OtrHandler
        @type  otr: OtrHandler Instanz
        """
        return self._createList(otr, 'recordings')

    def _createArchiveList(self, otr): 
        """
        wrapper um createList fuer archive aufzurufen

        @param otr: OtrHandler
        @type  otr: OtrHandler Instanz
        """
        return self._createList(otr, 'archive')
    

    def _createFutureSearchList(self, otr): 
        """
        wrapper um createSearchList fuer die Zukunft aufzurufen

        @param otr: OtrHandler
        @type  otr: OtrHandler Instanz
        """
        return self._createSearchList(otr, future=True)

    def _createPastSearchList(self, otr): 
        """
        wrapper um createSearchList fuer die Vergangenheit aufzurufen

        @param otr: OtrHandler
        @type  otr: OtrHandler Instanz
        """
        return self._createSearchList(otr, future=False)


    def _createSearchList(self, otr, future=False):
        """
        search for recordings

        @param otr: OtrHandler
        @type  otr: OtrHandler Instanz
        """
        listing = []
        searchstring = self._common.getUserInput(_(self._xbmcaddon, 'search'), False)
        if searchstring:
            for show in getKey(otr.getSearchListDict(searchstring, future=future), 'SHOW') or []:
                try:
                    duration = (int(show['END']) - int(show['BEGIN'])) / 60
                except Exception, e:
                    duration = False
                elementname = ""
                elementname += "%s: " % show['STATION']
                elementname += "%s"   % show['TITLE']
                elementname += " ("
                elementname += "%s"   % (show['NICEBEGIN'])
                if duration:
                    elementname += ", %s min" % duration
                elementname += ")"
                li = xbmcgui.ListItem( label=elementname )
                li.addContextMenuItems([], replaceItems=True )
                listing.append( [
                    "%s://%s/%s?epgid=%s" % (
                        self._url.scheme,
                        self._url.netloc,
                        'schedulejob',
                        show['EPGID']),
                    li,
                    False] )
        return listing

    def _createPastHightlightsList(self, otr):
        """
        get past hightlights

        @param otr: OtrHandler
        @type  otr: OtrHandler Instanz
        """
        items = getKey(otr.getPastHighlightsDict(), 'channel', 'item') or []
        listing = []
        for item in items:
            thumbnail = getKey(item, '{http://search.yahoo.com/mrss/}thumbnail', 'url')
            title = item['title']
            li = xbmcgui.ListItem( 
                label=title, 
                iconImage=thumbnail or None,
                thumbnailImage=thumbnail or None )
            description = getKey(item, 'description')
            if description:
                description = self._common.stripTags(description)
                description = description.replace('Informationen und Screnshots', '')
                description = description.replace('Zum Download', '')
                li.setInfo('video', {'plot' : description, 'title': title })
                li.addContextMenuItems([], replaceItems=True )
            listing.append( [
                    "%s://%s/%s?epgid=%s" % (
                        self._url.scheme,
                        self._url.netloc,
                        'schedulejob',
                        item['epg_id']),
                    li,
                    False] )
        return listing

    def _scheduleJob(self, otr, ask=True):
        """
        aufnahme planen

        @param otr: OtrHandler
        @type  otr: OtrHandler Instanz
        """
        if not ask or xbmcgui.Dialog().yesno(__TITLE__, _(self._xbmcaddon, 'schedule job?')):
            res = otr.scheduleJob(parse_qs(self._url.query)['epgid'].pop())
            if len(res) > 0:
                xbmcgui.Dialog().ok(__TITLE__, _(self._xbmcaddon, "scheduleJob: %s" % res))
        return None

    def _deleteJob(self, otr):
        """
        aufnahme loeschen

        @param otr: OtrHandler
        @type  otr: OtrHandler Instanz
        """
        print(otr.deleteJob( parse_qs(self._url.query)['epgid'].pop() ))
        xbmc.executebuiltin("Container.Refresh")
        return []

    def _showUserinfo(self, otr):
        """
        userinfo anzeigen

        @param otr: OtrHandler
        @type  otr: OtrHandler Instanz
        """
        info = otr.getUserInfoDict()
        line1 = "%s" % (info['EMAIL'])
        line2 = _(self._xbmcaddon, "status: %s (until %s)") % ( 
            info['STATUS'],
            info['UNTILNICE'])
        line3 = _(self._xbmcaddon, "decodings left: %s, gwp left: %s") % ( 
            info['DECODINGS_LEFT'],
            info['GWP'])
        xbmcgui.Dialog().ok( __TITLE__, line1, line2, line3)
        return []

    def _playWithWait(self, otr):
        queuemax = 0;
        waiting = True
        prdialog = xbmcgui.DialogProgress()
        prdialog.create(_(self._xbmcaddon, 'downloadqueue'))
        prdialog.update(0)
        while waiting:
            print "waiting"
            try:
                fileuri = base64.urlsafe_b64decode(parse_qs(self._url.query)['fileuri'].pop())
                xbmc.executebuiltin("PlayMedia(%s)" % otr.getFileDownload(fileuri))
                prdialog.close()
                break
            except otr.inDownloadqueueException, e:
                print "otr.inDownloadqueueException"
                if e.position > queuemax:
                    queuemax = e.position
                percent = (100 - int(e.position * 100 / queuemax))
                print "%s percent" % percent
                prdialog.update(percent, _(self._xbmcaddon, 'queueposition %s') % e.position)
                print "sleep 10 sec!"
                for i in range(1, 20):
                    if not prdialog.iscanceled():
                        time.sleep(0.5)
                    else:
                        waiting = False
                        break
            
        
    def get(self, otr):
        """
        pfad aufloesen und auflistung zurueckliefern

        @access public
        @returns list
        @usage      c=example2.creator()
                    list = c.get()
        @param otr: OtrHandler
        @type  otr: OtrHandler Instanz
        """
        path =  {
                '': ['recordings', 'archive', 'scheduling'],
                'scheduling' : ['searchpast', 'searchfuture', 'pasthighlights'],
                'scheduling/searchpast': self._createPastSearchList,
                'scheduling/searchfuture': self._createFutureSearchList,
                'scheduling/pasthighlights': self._createPastHightlightsList,
                'recordings': self._createRecordingList,
                'archive': self._createArchiveList,
                'deletejob': self._deleteJob,
                'schedulejob': self._scheduleJob,
                'userinfo': self._showUserinfo,
                'play': self._playWithWait,
                }

        #get the list
        sub = getKey(path, self._url.path.strip('/'))
        if isinstance(sub, list):
            ret = self.createDir(sub)
            if self._url.path == '/':
                if otr.newVersionAvailable():
                    # main dir and new version available
                    # TODO! remove in repo release!
                    print "new version available!"
                    ret.append(
                        [
                        "%s://%s/%s" % (
                            self._url.scheme,
                            self._url.netloc,
                            self._url.path),
                        xbmcgui.ListItem( label=_(self._xbmcaddon, 'new version available') ),
                        False
                        ])
            return ret
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
        handler = int(self._url.fragment)
        xbmcplugin.setContent(handler, 'tvshows')
        if listing:
            for item in listing:
                xbmcplugin.addDirectoryItem(handler, item[0], item[1], item[2])
