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
import OtrHandler
import logging
import urllib
import base64
import time
import datetime

try:
    import CommonFunctions
except ImportError, e:
    # local copy version from http://hg.tobiasussing.dk/hgweb.cgi/commonxbmc/ for apple tv integration
    import LocalCommonFunctions as CommonFunctions
    print "LocalCommonFunctions loaded"

try:
    from cgi import parse_qs
except ImportError:
    print "parse_qs not in cgi"
    from urlparse import parse_qs
    

__TITLE__ = 'onlinetvrecorder.com'
__THUMBURL__ = 'http://thumbs.onlinetvrecorder.com/'


class StorageServerDummy:

    dbg = False

    def cacheFunction(*args):
        return ""

    def delete(*args):
        return ""

    def set(*args):
        return ""

    def get(*args):
        return False

    def setMulti(*args):
        return ""

    def getMulti(*args):
        return False

    def lock(*args):
        return False

    def unlock(*arg):
        return False


try:
    import StorageServer
    cache = StorageServer.StorageServer(__TITLE__, 7)
except Exception, e:
    try:
    	# local copy version from http://hg.tobiasussing.dk/hgweb.cgi/cachexbmc/ for apple tv integration
        import LocalStorageServer as StorageServer
        cache = StorageServer.StorageServer(__TITLE__, 7)
        print "LocalStorageServer loaded"
    except Exception, e: 
        cache = StorageServerDummy()
        print "StorageServerDummy loaded (%s)" % e

#cache.dbg = True

def pprint(s):
    import pprint
    xbmc.log(pprint.pformat(s))

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
        'login failed': 30301,
        'loading recording list': 30302,
        'recordings': 30303,
        'archive': 30304,
        'delete': 30305,
        'play': 30306,
        'refresh listing': 30307,
        'userinfo': 30308,
        'status: %s (until %s)': 30309,
        'decodings left: %s, gwp left: %s': 30310,
        'loading recording list failed': 30311,
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
        'queueposition %s of %s': 30322,
        'refresh in %s sec': 30323,
        'delete job?': 30324,
        'job deleted': 30325,
        'refresh element': 30326,
        'stream select': 30327,
        'URLError(timeout(\'timed out\',),)': 30328,
        'Monday': 30329,
        'Tuesday': 30330,
        'Wednesday': 30331,
        'Thursday': 30332,
        'Friday': 30333,
        'Saturday': 30334,
        'Sunday': 30335,
        'January': 30336,
        'February': 30337,
        'March': 30338,
        'April': 30339,
        'May': 30340,
        'June': 30341,
        'July': 30342,
        'August': 30343,
        'September': 30344,
        'October': 30345,
        'November': 30346,
        'December': 30347,
        '%s weeks': 30348,
        'tvguide': 30349,
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


    def __autoclearCache(self):
        settings = [
            'otrUsername',
            'otrPreferPrio',
            'otrShowUnspported',
            'otrAcceptAVI',
            'otrPreferCut',
            'otrPreferHQ', 
            'otrPreferHD' ]
        identstring = "0.1" #cacheversion
        for setting in settings:
            if self._xbmcaddon.getSetting(setting):
                identstring += "#%s:%s" % (setting, self._xbmcaddon.getSetting(setting))
        if not cache.get('settings') == base64.urlsafe_b64encode(identstring):
            print "forced cache refresh"
            cache.delete('%')
            cache.set('settings', base64.urlsafe_b64encode(identstring))
        if cache.get('otrsubcode') and cache.get('otrsubcode_refreshtime'):
            if ( int(cache.get('otrsubcode_refreshtime')) < int(time.time() - 60) or
                 int(cache.get('otrsubcode_refreshtime')) > int(time.time()) ):
                print "otrsubcode refresh"
                cache.delete('otrsubcode')
                cache.delete('otrsubcode_refreshtime')



    def getOTR(self):
        """
        Liefert die geladene OTR instanz zurueck.
        """
        if self._otr:
            return self._otr
        else:
            raise Exception('otr is None')

    def start(self, login=True):
        """
        Run the startup
        """

        # clean cache
        self.__autoclearCache()


        # login infos auslesen
        username = self._xbmcaddon.getSetting('otrUsername')
        password = self._xbmcaddon.getSetting('otrPassword')
        if not len(username) or not len(password):
            xbmcgui.Dialog().ok(
               __TITLE__,
               _(self._xbmcaddon, 'missing login credentials') )
            raise Exception("missing login credentials")

        # otr object
        try:
            # hanlder instanz laden
            self._otr = OtrHandler.OtrHandler()
            # subcode caching
            if cache.get('otrsubcode'):
                self._otr.setOtrSubcode(cache.get('otrsubcode'))
            else:
                cache.set('otrsubcode', self._otr.getOtrSubcode())
                cache.set('otrsubcode_refreshtime', str(int(time.time())))
        except Exception, e:
            print "login failed (1): %s" % e
            xbmcgui.Dialog().ok(
                __TITLE__,
                _(self._xbmcaddon, 'login failed'),  
                _(self._xbmcaddon, str(e)) )
            sys.exit(0)
        else:
            if login:
                try:
                    # eigentlicher login
                    coockie = os.path.join(
                                xbmc.translatePath('special://temp'), 
                                '%s%s' % (__TITLE__, '.cookie') )
                    self._otr.setCookie(coockie)
                    self._otr.login(username, password)
                except Exception, e:
                    print "login failed (2): %s" % e
                    xbmcgui.Dialog().ok(
                        __TITLE__,
                        _(self._xbmcaddon, 'login failed'), 
                        _(self._xbmcaddon, str(e)) )
                    sys.exit(0)
                else:
                    print("otr login successful")

        try:
            timeout = int(float(self._xbmcaddon.getSetting('otrTimeout')))
        except Exception, e:
            pass
        else:
            self._otr.setTimeout(timeout)


    
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

        def getListItemFromElement(element):
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


            cachekey = 'epgid_%s' % element['EPGID']
            try:
                elementuri, basicitem, infos, contextmenueitems = eval(cache.get(cachekey))
            except Exception, e:
                cache.delete(cachekey)
                elementinfo = otr.getFileInfoDict(element['EPGID'])
                streaminfo = getStreamSelection(elementinfo, element['EPGID'])
                stream_preselect, stream_selection = streaminfo

                if not stream_preselect: return False
                elementuri = "%s" % stream_preselect['uri']
                label = element['TITLE']
                if 'BEGIN' in element:
                    # zeitangabe vorhanden
                    label += " (%s)" % element['BEGIN']

                # item basic infos
                basicitem = {
                    'label': label,
                    'label2': element['FILENAME'],
                    'iconImage': '%s1.jpg' % getImageUrl(element['FILENAME']),
                    'thumbnailImage': '%sA.jpg' % getImageUrl(element['FILENAME'])
                    }

                # item detail infos
                infos= {}
                infos['size'] = long(stream_preselect['size'])
                infos['plot'] = "%s GWP (%s, %s, %s)\n" % (
                    stream_preselect['cost'], 
                    stream_preselect['type'], 
                    stream_preselect['stream'].replace('_', ' '),
                    stream_preselect['rsize'] )
                if 'DURATION' in element: infos['duration'] = element['DURATION'].split()[0]
                if 'DOWNLOADCOUNT' in element: infos['playcount'] = int(element['DOWNLOADCOUNT'])
                if 'TITLE' in element: infos['title'] = element['TITLE']
                if 'STATION' in element: infos['studio'] = element['STATION']
                if 'BEGIN' in element: infos['date'] = element['BEGIN']
                if 'TITLE2' in element: infos['plot'] += "\n%s" % element['TITLE2']

                streamlist = {}
                for stream in stream_selection:
                    streamlist[stream['name']] = stream['file']
                streamlist = base64.urlsafe_b64encode(repr(streamlist))

                # contextmenue
                contextmenueitems = []
                contextmenueitems.append (tuple(( 
                        _(self._xbmcaddon, 'play'), 
                        "PlayWith()" )))
                contextmenueitems.append (tuple((
                        _(self._xbmcaddon, 'stream select'), 
                        "XBMC.RunPlugin(%s://%s/%s?list=%s&file=%s)" % (
                            self._url.scheme,
                            self._url.netloc,
                            'streamselect',
                            streamlist,
                            base64.urlsafe_b64encode(label)) )))
                contextmenueitems.append (tuple((
                        _(self._xbmcaddon, 'refresh listing'),
                        "XBMC.RunPlugin(%s://%s/%s)" % (
                            self._url.scheme,
                            self._url.netloc,
                            'cleancache') )))
                contextmenueitems.append (tuple((
                        _(self._xbmcaddon, 'refresh element'),
                        "XBMC.RunPlugin(%s://%s/%s?search=%%25%s)" % (
                            self._url.scheme,
                            self._url.netloc,
                            'cleancache',
                            element['EPGID']) )))
                contextmenueitems.append (tuple((
                        _(self._xbmcaddon, 'delete'), 
                        "XBMC.RunPlugin(%s://%s/%s?epgid=%s)" % (
                            self._url.scheme,
                            self._url.netloc,
                            'deletejob',
                            element['EPGID']) )))
                contextmenueitems.append (tuple((
                        _(self._xbmcaddon, 'userinfo'), 
                        "XBMC.RunPlugin(%s://%s/%s)" % (
                            self._url.scheme,
                            self._url.netloc,
                            'userinfo' ) )))

                # cache object
                cache.set(cachekey, repr([elementuri, basicitem, infos, contextmenueitems]))

            # listelement erzeugen
            li = xbmcgui.ListItem(**basicitem)
            li.setInfo('video', infos)
            li.addContextMenuItems(contextmenueitems, replaceItems=True )
            return elementuri, li, False

    
        def getStreamSelection(elementinfo, epgid):
            """
            aggregiert die informationen der verfuegbaren streams
            
            @param streamelement: stream xml struktur die von otr kommt
            @type  streamelement: dict
            @param epgid: epgid der  aufnahme
            @type  epgid: string
            """


            def aggrstreaminfo(streamelement, epgid):
                """
                aggregiert die informationen eines einzelnen streams
                
                @param streamelement: stream xml struktur die von otr kommt
                @type  streamelement: dict
                @param epgid: epgid der  aufnahme
                @type  epgid: string
                """
                if not streamelement: return False
                if  self._xbmcaddon.getSetting('otrPreferPrio') == 'true':
                    stype = ( (getKey(streamelement, 'PRIO') and 'PRIO') or
                              (getKey(streamelement, 'FREE') and 'FREE') or False )
                else:
                    stype = ( (getKey(streamelement, 'FREE') and 'FREE') or
                              (getKey(streamelement, 'PRIO') and 'PRIO') or False )
                if not stype: return False

                size = getKey(streamelement, 'SIZE')
                rsize = getSizeStr(long(size)*1024)
                fileuri  = getKey(streamelement, stype)
                uri = "%s://%s/%s?fileuri=%s&epgid=%s" % (
                        self._url.scheme,
                        self._url.netloc,
                        "play",
                        base64.urlsafe_b64encode(fileuri),
                        epgid)
                gwp  = getKey(streamelement, 'GWPCOSTS', stype)
                name = stream
                if not self._xbmcaddon.getSetting('otrShowUnspported') == 'true':
                    name = name.replace('unkodiert', '')
                name = name.replace('_', ' ').strip()
                name += ", %s" % rsize
                name += ", %s GWP" % gwp

                return {
                    'uri': uri,
                    'file': fileuri,
                    'name': name,
                    'cost': gwp, 
                    'size': size, 
                    'rsize': rsize,
                    'type': stype, 
                    'stream': stream } 



            # streamvorauswahl nach den einsellungen
            preselectable = ['MP4_Stream', 'MP4_unkodiert']
            if self._xbmcaddon.getSetting('otrAcceptAVI') == 'true':
                preselectable.append('AVI_unkodiert')
            if self._xbmcaddon.getSetting('otrPreferCut') == 'true':
                preselectable.insert(0, 'MP4_geschnitten')
            if self._xbmcaddon.getSetting('otrPreferHQ') == 'true':
                if self._xbmcaddon.getSetting('otrAcceptAVI') == 'true':
                    preselectable.insert(0, 'HQAVI_unkodiert')
                preselectable.insert(0, 'HQMP4') 
                preselectable.insert(0, 'HQMP4_Stream')
                if self._xbmcaddon.getSetting('otrPreferCut') == 'true':
                    if self._xbmcaddon.getSetting('otrAcceptAVI') == 'true':
                        preselectable.insert(0, 'HQ_geschnitten')
                    preselectable.insert(0, 'HQMP4_geschnitten')
            if self._xbmcaddon.getSetting('otrPreferHD') == 'true':
                if self._xbmcaddon.getSetting('otrAcceptAVI') == 'true':
                    preselectable.insert(0, 'HDAVI_unkodiert')
                preselectable.insert(0, 'HDMP4') 
                preselectable.insert(0, 'HDMP4_Stream')
                if self._xbmcaddon.getSetting('otrPreferCut') == 'true':
                    if self._xbmcaddon.getSetting('otrAcceptAVI') == 'true':
                        preselectable.insert(0, 'HD_geschnitten')
                    preselectable.insert(0, 'HDMP4_geschnitten')

            
            selection = []
            for stream in elementinfo.keys():
                streaminfo = aggrstreaminfo(
                                getKey(elementinfo, stream),
                                epgid )
                if not streaminfo: continue
                if not self._xbmcaddon.getSetting('otrShowUnsupported') == 'true':
                    # hide unsupported
                    supportedendings = ['avi', 'mp4', 'mp3']
                    if 'otrkey' in streaminfo['file']: continue
                    if not streaminfo['file'].split('.').pop() in supportedendings: continue
                selection.append( streaminfo )

            for stream in preselectable: 
                if getKey(elementinfo, stream): 
                    break
            preselectstream = aggrstreaminfo(
                                getKey(elementinfo, stream),
                                epgid )

            return preselectstream, selection


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
                    _(self._xbmcaddon, 'loading recording list failed'),
                    _(self._xbmcaddon, str(e)) )
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
                    # fileinfo abfragen
                    litem = getListItemFromElement(element)
                except Exception, e:
                    print "getFileInfo failed (%s)" % str(e)
                    xbmc.executebuiltin('Notification("%s", "%s")' % (element['FILENAME'], str(e)))
                else:
                    if litem: listing.append(litem)

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
        if self._xbmcaddon.getSetting('otrAskSchedule') == 'true': ask = True
        if self._xbmcaddon.getSetting('otrAskSchedule') == 'false': ask = False
        if not ask or xbmcgui.Dialog().yesno(__TITLE__, _(self._xbmcaddon, 'schedule job?')):
            prdialog = xbmcgui.DialogProgress()
            prdialog.create(_(self._xbmcaddon, 'scheduling'))
            prdialog.update(0)
            res = otr.scheduleJob(parse_qs(self._url.query)['epgid'].pop())
            prdialog.update(100)
            prdialog.close()
            if len(res) > 0:
                xbmc.executebuiltin('Notification("%s", "%s")' % (
                    __TITLE__, 
                    _(self._xbmcaddon, "scheduleJob: %s" % res) ) )
            return True

    def _cleanCache(self, otr, search="%"):
        """
        cache aufraeumen

        @param otr: OtrHandler
        @type  otr: OtrHandler Instanz
        @param search: key selector
        @type  search: string
        """
        if 'search' in parse_qs(self._url.query):
            search = parse_qs(self._url.query)['search'].pop()
        cache.delete(search)
        xbmc.executebuiltin("Container.Refresh")
        return True

    def _deleteJob(self, otr, ask=True):
        """
        aufnahme loeschen

        @param otr: OtrHandler
        @type  otr: OtrHandler Instanz
        """
        if self._xbmcaddon.getSetting('otrAskDelete') == 'true': ask = True
        if self._xbmcaddon.getSetting('otrAskDelete') == 'false': ask = False
        if not ask or xbmcgui.Dialog().yesno(__TITLE__, _(self._xbmcaddon, 'delete job?')):
            prdialog = xbmcgui.DialogProgress()
            prdialog.create(_(self._xbmcaddon, 'delete'))
            prdialog.update(0)
            otr.deleteJob( parse_qs(self._url.query)['epgid'].pop() )
            prdialog.update(100)
            prdialog.close()
            xbmc.executebuiltin("Container.Refresh")
            xbmc.executebuiltin('Notification("%s", "%s")' % (
                __TITLE__, 
                _(self._xbmcaddon, "job deleted") ) )
            return True

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


    def _createProgrammList(self, otr):


        arglist = parse_qs(self._url.query)
        uri = "%s://%s/%s?%s" % (
            self._url.scheme,
            self._url.netloc,
            self._url.path,
            self._url.query)
        print arglist

        listing = []

        thisweek = datetime.datetime.now()
        thisweek = thisweek - datetime.timedelta(days=thisweek.weekday())

        if not 'week' in arglist and not 'day' in arglist:
            # wochenliste
            thisweek = datetime.datetime.now()
            thisweek = thisweek - datetime.timedelta(days=thisweek.weekday())
            for weekdelta in range(-4, 0):
                weekstart = thisweek+datetime.timedelta(weeks=weekdelta)
                weekstring = " -" + _(self._xbmcaddon, "%s weeks") % (weekdelta*-1) 
                month_start_name = _(self._xbmcaddon, weekstart.date().strftime("%B")) 
                month_end_name = _(self._xbmcaddon, (weekstart.date()+datetime.timedelta(days=6)).strftime("%B"))
                weekstring += " (%s - %s)" % (
                        weekstart.date().strftime("%d. " + month_start_name + " %Y"), 
                        (weekstart.date()+datetime.timedelta(days=6)).strftime("%d. " + month_end_name + " %Y")
                        ) 
                listing.append(  [
                    uri + '&week=%s' % weekdelta, 
                    xbmcgui.ListItem(label=weekstring),
                    True] )

        if not 'day' in arglist:
            # tagesliste
            weekstart = thisweek+datetime.timedelta(weeks=int(
                'week' in arglist and arglist['week'].pop() or 0))
            for day in range(7):
                singleday = weekstart + datetime.timedelta(days=day)
                weekday_name = _(self._xbmcaddon, singleday.date().strftime("%A"))
                month_name = _(self._xbmcaddon, singleday.date().strftime("%B"))
                listitem = xbmcgui.ListItem(label=singleday.date().strftime(weekday_name + " (%d. " + month_name + " %Y)"))
                if singleday.date() == datetime.date.today():
                    listitem.select(True)
                listing.append( [
                    uri + '&' + urllib.urlencode({'day': int(time.mktime(singleday.timetuple()))}), 
                    listitem,
                    True] )

        if not 'week' in arglist and not 'day' in arglist:
            # wochenliste
            for weekdelta in range(1, 5):
                weekstart = thisweek+datetime.timedelta(weeks=weekdelta)
                weekstring = " +" + _(self._xbmcaddon, "%s weeks") % (weekdelta)
                month_start_name = _(self._xbmcaddon, weekstart.date().strftime("%B")) 
                month_end_name = _(self._xbmcaddon, (weekstart.date()+datetime.timedelta(days=6)).strftime("%B"))
                weekstring += " (%s - %s)" % (
                        weekstart.date().strftime("%d. " + month_start_name + " %Y"), 
                        (weekstart.date()+datetime.timedelta(days=6)).strftime("%d. " + month_end_name + " %Y")
                        ) 
                listing.append(  [
                    uri + '&' + urllib.urlencode({'week': weekdelta}), 
                    xbmcgui.ListItem(label=weekstring),
                    True] )

        if not 'day' in arglist: 
            return listing

        if not 'channel' in arglist:
            # kanalliste
            channels = otr.getChannelsDict()
            keys = channels.keys()
            keys.sort()
            for key in keys:
                listing.append( [
                    uri + '&' + urllib.urlencode({'channel': key}),
                    xbmcgui.ListItem(label=key),
                    True] )
            return listing

        selected_day = datetime.datetime.fromtimestamp(int(arglist['day'].pop())).date()
        selected_channel = arglist['channel'].pop()

        print "%s@%s" % (selected_channel, selected_day)

        return None




    def _selectStream(self, otr):
        """
        aufnahme loeschen

        @param otr: OtrHandler
        @type  otr: OtrHandler Instanz
        """
        streamlist = eval(base64.urlsafe_b64decode(parse_qs(self._url.query)['list'].pop()))
        filename = base64.urlsafe_b64decode(parse_qs(self._url.query)['file'].pop())
        choice = xbmcgui.Dialog().select(filename, streamlist.keys())
        if choice >= 0:
            uri = streamlist[streamlist.keys()[choice]]
            self._play(otr, uri) #executebuiltin("RunScript(%s)" % uri, True)
        return True

    def _play(self, otr, requesturi=False):
        queuemax = 0;
        xbmc.executebuiltin("Dialog.Close(all,true)", True)
        prdialog = xbmcgui.DialogProgress()
        prdialog.create(_(self._xbmcaddon, 'downloadqueue'))
        prdialog.update(0)

        if not requesturi:
            if not 'fileuri' in parse_qs(self._url.query):
                raise Exception('play without fileuri not possible')
                return False
            else:
                requesturi = base64.urlsafe_b64decode(parse_qs(self._url.query)['fileuri'].pop())

        if 'epgid' in parse_qs(self._url.query):
            egid = parse_qs(self._url.query)['epgid'].pop()
            cache.delete('epgid_%s' % egid)

        while True:
            try:
                fileuri = otr.getFileDownload(requesturi)
                prdialog.close()
                print "got url %s" % fileuri
                xbmc.executebuiltin("XBMC.PlayMedia(\"%s\")" % fileuri, True)
                return True
            except otr.inDownloadqueueException, e:
                if e.position > queuemax:
                    queuemax = e.position
                percent = (100 - int(e.position * 100 / queuemax))
                for step in reversed(range(1, 20)):
                    prdialog.update(
                        percent, 
                        _(self._xbmcaddon, 'queueposition %s of %s') % (e.position, queuemax),
                        _(self._xbmcaddon, 'refresh in %s sec') % int(step/2) )
                    if not prdialog.iscanceled():
                        time.sleep(0.5)
                    else:
                        return False
            except otr.foundDownloadErrorException, e:
                xbmcgui.Dialog().ok(
                    "%s (%s)" % (__TITLE__, e.number),
                    _(self._xbmcaddon, e.value) )
                return False
                
            
        
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
                '': ['recordings', 'scheduling'],
                'scheduling' : ['searchpast', 'searchfuture', 'pasthighlights', 'tvguide'],
                'scheduling/searchpast': self._createPastSearchList,
                'scheduling/searchfuture': self._createFutureSearchList,
                'scheduling/pasthighlights': self._createPastHightlightsList,
                'scheduling/tvguide': self._createProgrammList,
                'recordings': self._createRecordingList,
                'deletejob': self._deleteJob,
                'schedulejob': self._scheduleJob,
                'userinfo': self._showUserinfo,
                'streamselect': self._selectStream,
                'play': self._play,
                'cleancache': self._cleanCache,
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
        if isinstance(listing, list):
            handler = int(self._url.fragment)
            xbmcplugin.setContent(handler, 'tvshows')
            for item in listing:
                xbmcplugin.addDirectoryItem(handler, item[0], item[1], item[2])
            xbmcplugin.endOfDirectory(handler)
