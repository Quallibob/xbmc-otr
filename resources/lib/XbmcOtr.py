# vim: tabstop=4 shiftwidth=4 smarttab expandtab softtabstop=4 autoindent

"""
    Document   : XbmcOtr.py
    Package    : OTR Integration to XBMC
    Author     : Frank Epperlein
    Copyright  : 2012, Frank Epperlein, DE
    License    : Gnu General Public License 2
    Description: Worker class library
"""

import sys
import xbmc
import xbmcplugin
import xbmcaddon
import xbmcgui
import urllib
import time
import datetime
import types
import LocalCommonFunctions as CommonFunctions
import Archive
import OtrHandler
import Simplebmc
import traceback

from Translations import _
from Call import call
import Vfs as vfs


try:
    #noinspection PyUnresolvedReferences
    import CommonFunctions
except ImportError:
    # local copy version from http://hg.tobiasussing.dk/hgweb.cgi/commonxbmc/ for apple tv integration
    print "LocalCommonFunctions loaded"

try:
    from urlparse import parse_qs
except ImportError:
    #noinspection PyDeprecation
    from cgi import parse_qs


__title__ = 'onlinetvrecorder.com'
__addon__ = xbmcaddon.Addon()
__sx__ = Simplebmc.Simplebmc()
__common__ = CommonFunctions



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


#define classes
class housekeeper:
    """
    Run any startup required for the addon
    """
    _otr = None
    _logged_in = False

    def __init__(self):
        """
        constructor
        """
        self._start()


    def getOTR(self):
        """
        Liefert die geladene OTR instanz zurueck.
        """
        if self._otr:
            return self._otr
        else:
            raise Exception('otr is None')

    def _start(self):
        """
        Run the startup
        """

        # otr object
        try:
            # hanlder instanz laden
            self._otr = OtrHandler.OtrHandler()
        except Exception, e:
            print "login failed (1): %s" % e
            xbmc.log(traceback.format_exc(), level=xbmc.LOGERROR)
            xbmcgui.Dialog().ok(
                __title__,
                _('login failed'),  
                _(str(e)) )
            sys.exit(0)
        else:
            #noinspection PyBroadException
            try:
                timeout = int(float(__addon__.getSetting('otrTimeout')))
            except Exception:
                pass
            else:
                self._otr.setTimeout(timeout)

    def loginIfRequired(self):
        if not self._logged_in:
            self.login()

    def login(self):
        # login infos auslesen
        username = __addon__.getSetting('otrUsername')
        password = __addon__.getSetting('otrPassword')
        if not len(username) or not len(password):
            xbmcgui.Dialog().ok(
                __title__,
                _('missing login credentials') )
            raise Exception("missing login credentials")

        # eigentlicher login
        try:
            self._otr.login(username, password)
        except Exception, e:
            print "login failed (2): %s" % e
            xbmc.log(traceback.format_exc(), level=xbmc.LOGERROR)
            xbmcgui.Dialog().ok(
                __title__,
                _('login failed'),
                _(str(e)) )
            sys.exit(0)
        else:
            print("otr login successful")
            self._logged_in = True



    def end(self):
        """
        Run the end processes
        """
        pass



class creator:

    listing = []
    __login = None

    def __init__(self, login=None):
        """
        constructor
        """
        #noinspection PyUnusedLocal
        def dummyFunction(*args, **kwargs): pass

        self.listing = list()
        if login:   self.__login = login
        else:       self.__login = dummyFunction


    def _createDir(self, subs):
        """
        dir listing fuer uebersichten erzeugen

        @param subs: listenelemente
        @type  subs: list
        """
        listing = []
        for element in subs:
            li = xbmcgui.ListItem( label=_(element) )

            if element == 'recordings':
                li.addContextMenuItems(
                    [
                        ( _('refresh listing'),
                          "XBMC.RunPlugin(\"%s\")" % call.format('/refreshlisting') ),
                        ( _('userinfo'),
                          "XBMC.RunPlugin(%s)" % call.format('userinfo') ),
                        ], replaceItems=True )
            else:
                li.addContextMenuItems(
                    [
                      ( _('refresh listing'),
                        "Container.Refresh" ),
                      ( _('userinfo'),
                        "XBMC.RunPlugin(%s)" % call.format('userinfo') ),
                    ], replaceItems=True )
            listing.append( [
                call.format(element),
                li,
                True] )
        return listing


    def _createRecordingList(self, otr): 
        """
        wrapper um createList fuer recordings aufzurufen

        @param otr: OtrHandler
        @type  otr: OtrHandler Instanz
        """

        def get_recording_list_item(archive, recording):

            li = xbmcgui.ListItem(
                recording['label'],
                recording['filename'],
                archive.getImageUrl(recording['epgid'], recording['icon_image']),
                archive.getImageUrl(recording['epgid'], recording['thumbnail_image'])
                )

            contextmenueitems = [tuple((
                _('delete local copies'),
                "XBMC.RunPlugin(\"%s\")" % call.format('/deletelocalcopies', params={'epgid': recording['epgid']})
                )), tuple((
                _('delete'),
                "XBMC.RunPlugin(\"%s\")" % call.format('/deletejob', params={'epgid': recording['epgid']})
                )), tuple((
                _('refresh listing'),
                "XBMC.RunPlugin(\"%s\")" % call.format('/refreshlisting', params={'epgid': recording['epgid']})
                )), tuple((
                _('userinfo'),
                "XBMC.RunPlugin(\"%s\")" % call.format('/userinfo')
                ))]
            li.addContextMenuItems(contextmenueitems, replaceItems=True )

            infos = dict(
                filter(
                    lambda r: r[0] in ['duration', 'title', 'studio', 'date', 'plot'],
                    recording.items()
                    ) )
            li.setInfo('video', infos)
            return [
                call.format(params={ 'epgid': recording['epgid'] }),
                li,
                True
                ]

        def get_recordingstreams_list_item(archive, recording):
            if not 'streams' in recording: return
            list = recording['streams'].keys()
            list.sort()
            for stream in list:

                li = xbmcgui.ListItem(
                    "%s %s" % (_('stream:'), recording['streams'][stream]['name']),
                    recording['streams'][stream]['type'],
                    archive.getImageUrl(recording['epgid'], recording['icon_image']),
                    archive.getImageUrl(recording['epgid'], recording['thumbnail_image'])
                    )

                contextmenueitems = []
                contextmenueitems.append( tuple((
                    _('play'),
                    "PlayWith()" )))

                if 'copies' in recording:
                    if not str(recording['streams'][stream]['file'].split('/').pop()) in recording['copies']:
                        contextmenueitems.append( tuple((
                            _('download'),
                            "XBMC.RunPlugin(\"%s\")" % call.format('/download', params={
                                'url': recording['streams'][stream]['file'],
                                'epgid': recording['epgid'],
                                'name': recording['streams'][stream]['name']
                            }) )) )

                contextmenueitems.append( tuple((
                    _('userinfo'),
                    "XBMC.RunPlugin(\"%s\")" % call.format('/userinfo')
                    )) )
                li.addContextMenuItems(contextmenueitems, replaceItems=True )

                yield [
                    call.format('/play', params={
                        'url': recording['streams'][stream]['file'],
                        'epgid': recording['epgid']}),
                    li,
                    False,
                    ]

        def get_recordingcopies_list_item(archive, recording):
            if not 'copies' in recording: return
            for copy in recording['copies'].keys():

                li = xbmcgui.ListItem(
                    "%s %s" % (_('local copy:'), recording['copies'][copy]['name']),
                    '',
                    archive.getImageUrl(recording['epgid'], recording['icon_image']),
                    archive.getImageUrl(recording['epgid'], recording['thumbnail_image'])
                )

                contextmenueitems = [tuple((
                    _('play'),
                    "PlayWith()" )), tuple((
                    _('delete'),
                    "XBMC.RunPlugin(\"%s\")" % call.format('/deletelocalcopies',
                        params={'file': recording['copies'][copy]['file']})
                    )), tuple((
                    _('userinfo'),
                    "XBMC.RunPlugin(\"%s\")" % call.format('/userinfo')
                    ))]
                li.addContextMenuItems(contextmenueitems, replaceItems=True )

                yield [
                    recording['copies'][copy]['file'],
                    li,
                    False,
                    ]


        listing = list()
        archive = Archive.Archive()
        archive.load()
        print "last: %s" % archive.LastFile(archive).last()

        if archive.LastFile(archive).last() < 0 or archive.LastFile(archive).last() > 900:
            self.__login()
            archive.refresh(otr)
            archive.load()

        if not 'epgid' in call.params:
            for epgid in archive.recordings:
                listing.append(get_recording_list_item(archive, archive.recordings[epgid]))
        else:
            epgid = call.params['epgid']
            for stream in get_recordingstreams_list_item(archive, archive.recordings[epgid]):
                listing.append(stream)
            for stream in get_recordingcopies_list_item(archive, archive.recordings[epgid]):
                listing.append(stream)

        return listing


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
        searchstring = __common__.getUserInput(_('search'), False)
        if searchstring:
            for show in getKey(otr.getSearchListDict(searchstring, future=future), 'SHOW') or []:
                #noinspection PyBroadException
                try:
                    duration = (int(show['END']) - int(show['BEGIN'])) / 60
                except Exception:
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
                listing.append( [call.format('/schedulejob', {'epgid':show['EPGID']}), li,  False] )
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
                description = __common__.stripTags(description)
                description = description.replace('Informationen und Screnshots', '')
                description = description.replace('Zum Download', '')
                li.setInfo('video', {'plot' : description, 'title': title })
                li.addContextMenuItems([], replaceItems=True )
            listing.append( [call.format('/schedulejob', {'epgid':item['epg_id']}), li, False] )
        return listing


    def _scheduleJob(self, otr, ask=True):
        """
        aufnahme planen

        @param otr: OtrHandler
        @type  otr: OtrHandler Instanz
        """
        self.__login()
        if __addon__.getSetting('otrAskSchedule') == 'true': ask = True
        if __addon__.getSetting('otrAskSchedule') == 'false': ask = False
        if not ask or xbmcgui.Dialog().yesno(__title__, _('schedule job?')):
            prdialog = xbmcgui.DialogProgress()
            prdialog.create(_('scheduling'))
            prdialog.update(0)
            res = otr.scheduleJob(call.params['epgid'])
            prdialog.update(100)
            prdialog.close()
            if len(res) > 0:
                xbmc.executebuiltin('show_notification("%s", "%s")' % (
                    __title__,
                    _("scheduleJob: %s" % res) ) )
            return True


    def _deleteJob(self, otr, ask=True):
        """
        aufnahme loeschen

        @param otr: OtrHandler
        @type  otr: OtrHandler Instanz
        """
        self.__login()

        if not __addon__.getSetting('otrAskDelete') == 'false':
            if not ask or xbmcgui.Dialog().yesno(__title__, _('delete job?')):
                return False

        otr.deleteJob( call.params['epgid'] )

        if not self._deleteLocalCopies(otr):
            xbmc.executebuiltin("Container.Refresh")

        xbmc.executebuiltin('show_notification("%s", "%s")' % (
            __title__,
            _("job deleted") ) )

        return True


    #noinspection PyUnusedLocal
    def _deleteLocalCopies(self, otr):

        if not __addon__.getSetting('otrAskDeleteLocal') == 'false':
            if not xbmcgui.Dialog().yesno(
                __title__,
                _('do you want do delete existing local copies?')):
                    return False

        archive = Archive.Archive()
        if 'epgid' in call.params and call.params['epgid']:
            archive.deleteLocalEpgidPath(epgid=call.params['epgid'])
        elif 'file' in call.params and call.params['file']:
            archive.deleteLocalEpgidPath(file=call.params['file'])
        xbmc.executebuiltin("Container.Refresh")
        return True


    def _refreshListing(self, otr):
        self.__login()
        archive = Archive.Archive()
        archive.refresh(otr)
        xbmc.executebuiltin("Container.Refresh")


    def _showUserinfo(self, otr):
        """
        userinfo anzeigen

        @param otr: OtrHandler
        @type  otr: OtrHandler Instanz
        """
        self.__login()
        info = otr.getUserInfoDict()
        line1 = "%s" % (info['EMAIL'])
        line2 = _("status: %s (until %s)") % ( 
            info['STATUS'],
            info['UNTILNICE'])
        line3 = _("decodings left: %s, gwp left: %s") % ( 
            info['DECODINGS_LEFT'],
            info['GWP'])
        xbmcgui.Dialog().ok( __title__, line1, line2, line3)
        return []


    def _createProgrammList(self, otr):

        def getStationThumburl(station):
            url = "http://static.onlinetvrecorder.com/images/easy/stationlogos/%s.gif"
            return url % urllib.quote(station.lower())

        listing = []

        thisweek = datetime.datetime.now()
        thisweek = thisweek - datetime.timedelta(days=thisweek.weekday())

        if not 'week' in call.params and not 'day' in call.params:
            # wochenliste
            thisweek = datetime.datetime.now()
            thisweek = thisweek - datetime.timedelta(days=thisweek.weekday())
            for weekdelta in range(-4, 0):
                weekstart = thisweek+datetime.timedelta(weeks=weekdelta)
                weekstring = " -" + _(weekdelta<-1 and "%s weeks" or "%s week") % str(weekdelta*-1)
                month_start_name = _(weekstart.date().strftime("%B")) 
                month_end_name = _((weekstart.date()+datetime.timedelta(days=6)).strftime("%B"))
                weekstring += u" (%s - %s)" % (
                        weekstart.date().strftime("%d. ") + month_start_name + weekstart.date().strftime(" %Y"),
                        (weekstart.date()+datetime.timedelta(days=6)).strftime("%d. ") +
                            month_end_name +
                            (weekstart.date()+datetime.timedelta(days=6)).strftime(" %Y")
                        )
                listitem = xbmcgui.ListItem(label=weekstring)
                listitem.addContextMenuItems([], replaceItems=True )
                listing.append(  [
                    call.format(params={'week':weekdelta}, update=True),
                    listitem,
                    True] )

        if not 'day' in call.params:
            # tagesliste
            weekstart = thisweek+datetime.timedelta(weeks=int(
                'week' in call.params and call.params['week'] or 0))
            for day in range(7):
                singleday = weekstart + datetime.timedelta(days=day)
                weekday_name = _(singleday.date().strftime("%A"))
                month_name = _(singleday.date().strftime("%B"))
                listitem = xbmcgui.ListItem(label=singleday.date().strftime(weekday_name + " (%d. " + month_name + " %Y)"))
                contextmenueitems = [tuple((
                    _('show all channels'),
                    "Container.Update(%s,True)" % call.format(params={'showall': True}, update=True) ))]
                listitem.addContextMenuItems(contextmenueitems, replaceItems=True )
                if singleday.date() == datetime.date.today():
                    listitem.select(True)
                listing.append( [
                    call.format(params={'day': int(time.mktime(singleday.timetuple()))}, update=True),
                    listitem,
                    True] )

        if not 'week' in call.params and not 'day' in call.params:
            # wochenliste
            for weekdelta in range(1, 5):
                weekstart = thisweek+datetime.timedelta(weeks=weekdelta)
                weekstring = " +" + _(weekdelta>1 and "%s weeks" or "%s week") % str(weekdelta)
                month_start_name = _(weekstart.date().strftime("%B")) 
                month_end_name = _((weekstart.date()+datetime.timedelta(days=6)).strftime("%B"))
                weekstring += u" (%s - %s)" % (
                    weekstart.date().strftime("%d. ") + month_start_name + weekstart.date().strftime(" %Y"),
                    (weekstart.date()+datetime.timedelta(days=6)).strftime("%d. ") +
                    month_end_name +
                    (weekstart.date()+datetime.timedelta(days=6)).strftime(" %Y")
                    )
                listitem = xbmcgui.ListItem(label=weekstring)
                listitem.addContextMenuItems([], replaceItems=True )
                listing.append(  [
                    call.format(params={'week':weekdelta}, update=True),
                    listitem,
                    True] )

        if not 'day' in call.params:
            return listing

        if not 'channel' in call.params:
            # kanalliste
            hidden_chan = __addon__.getSetting('otrChannelsHidden').split(',')
            hidden_lang = __addon__.getSetting('otrLanguagesHidden').split(',')

            if getKey(call.params, 'hidechannel'):
                hidden_chan.append(getKey(call.params, 'hidechannel'))
                __addon__.setSetting('otrChannelsHidden', ','.join(hidden_chan).strip(','))
                xbmc.executebuiltin("Container.Refresh")
            elif getKey(call.params, 'unhidechannel'):
                name = getKey(call.params, 'unhidechannel')
                if name in hidden_chan: 
                    hidden_chan.remove(name)
                    __addon__.setSetting('otrChannelsHidden', ','.join(hidden_chan).strip(','))
                    xbmc.executebuiltin("Container.Refresh")

            elif getKey(call.params, 'hidelanguage'):
                hidden_lang.append(getKey(call.params, 'hidelanguage'))
                __addon__.setSetting('otrLanguagesHidden', ','.join(hidden_lang).strip(','))
                xbmc.executebuiltin("Container.Refresh")
            elif getKey(call.params, 'unhidelanguage'):
                name = getKey(call.params, 'unhidelanguage')
                if name in hidden_lang: 
                    hidden_lang.remove(name)
                    __addon__.setSetting('otrLanguagesHidden', ','.join(hidden_lang).strip(','))
                    xbmc.executebuiltin("Container.Refresh")

            channels = otr.getChannelsDict()
            keys = channels.keys()
            keys.sort()

            for key in keys:
                language = channels[key]['LANGUAGE']
                contextmenueitems = []

                if not ('showall' in call.params and call.params['showall'] == 'True'):
                    if language in hidden_lang: continue
                    if key in hidden_chan: continue
                    showall = False
                    hiddenitem = False
                else:
                    hiddenitem = False
                    if language in hidden_lang: 
                        hiddenitem = True
                    if key in hidden_chan: 
                        hiddenitem = True
                    showall = True

                if not hiddenitem: contextmenueitems.append ( tuple((
                    _('hide channel (%s)') % key,
                    "XBMC.RunPlugin(%s)" % call.format(params={'hidechannel': key}, update=True),
                    )) )
                if hiddenitem and key in hidden_chan: contextmenueitems.append ( tuple((
                    _('unhide channel (%s)') % key,
                    "XBMC.RunPlugin(%s)" % call.format(params={'unhidechannel': key}, update=True),
                    )) )
                if not hiddenitem: contextmenueitems.append ( tuple((
                    _('hide language (%s)') % language,
                    "XBMC.RunPlugin(%s)" % call.format(params={'hidelanguage': language}, update=True),
                    )) )
                if hiddenitem and language in hidden_lang: contextmenueitems.append ( tuple((
                    _('unhide language (%s)') % language,
                    "XBMC.RunPlugin(%s)" % call.format(params={'unhidelanguage': language}, update=True),
                    )) )
                if not showall: contextmenueitems.append ( tuple((
                        _('show all channels'),
                        "Container.Update(%s,True)" % call.format(params={'showall': True}, update=True) )) )

                li = xbmcgui.ListItem(label=key, iconImage=getStationThumburl(key))
                li.addContextMenuItems(contextmenueitems, replaceItems=True )

                if hiddenitem: li.select(True)

                listing.append( [
                    call.format(params={'channel': key}, update=True),
                    li,
                    True] )

            return listing

        if 'day' in call.params and 'channel' in call.params:
            selected_daystamp = int(call.params['day'])
            selected_day = datetime.datetime.fromtimestamp(selected_daystamp).date()
            selected_channel = call.params['channel']

            entries = otr.getChannelListingDict([selected_channel], selected_day, selected_day) or []
            entries = getKey(entries, 'ITEM') or []

            listing.append( [
                call.format(params={'day': str(selected_daystamp-86400)}, update=True),
                xbmcgui.ListItem(label=_('day before')),
                True] )
            

            for entry in entries:
                title = urllib.unquote_plus(entry['TITEL'])

                attribs = []
                if 'NICEDATE' in entry: attribs.append(entry['NICEDATE'])
                title += " (%s)" % ', '.join(attribs)

                info = {}
                if 'NICEDATE' in entry and entry['NICEDATE']: info['date'] = entry['NICEDATE']
                if 'TYP' in entry and entry['TYP']: info['genre'] = urllib.unquote_plus(entry['TYP'])
                if 'TEXT' in entry and entry['TEXT']: info['plot'] = urllib.unquote_plus(entry['TEXT'])
                if 'RATING' in entry and entry['RATING']: info['rating'] = int(entry['RATING'])
                if 'PROGRAMMINGS' in entry and entry['PROGRAMMINGS']: info['playcount'] = int(entry['PROGRAMMINGS'])
                if 'DAUER' in entry and entry['DAUER']: info['duration'] = entry['DAUER']
                if 'FSK' in entry and entry['FSK']: info['mpaa'] = urllib.unquote_plus(entry['FSK'])

                li = xbmcgui.ListItem(label=title)
                li.setInfo('video', info)
                if 'HIGHLIGHT' in entry and entry['HIGHLIGHT'] and int(entry['HIGHLIGHT'])>0:
                    li.select(True)

                listing.append( [call.format('/schedulejob', {'epgid':entry['ID']}), li, False] )

            listing.append( [
                call.format(params={'day': str(selected_daystamp+86400)}, update=True),
                xbmcgui.ListItem(label=_('day after')),
                True] )

            return listing

        return None


    def _downloadqueue(self, otr, requesturi):
        queuemax = 0
        prdialog = xbmcgui.DialogProgress()
        prdialog.create(_('downloadqueue'))
        prdialog.update(0)

        while True:
            try:
                fileuri = otr.getFileDownload(requesturi)
                prdialog.close()
                return fileuri
            except otr.inDownloadqueueException, e:
                if e.position > queuemax:
                    queuemax = e.position
                percent = (100 - int(e.position * 100 / queuemax))
                for step in reversed(range(1, 40)):
                    prdialog.update(
                        percent, 
                        _('queueposition %s of %s') % (e.position, queuemax),
                        _('refresh in %s sec') % int(step/2) )
                    if not prdialog.iscanceled():
                        time.sleep(0.5)
                    else:
                        return False
            except otr.foundDownloadErrorException, e:
                xbmcgui.Dialog().ok(
                    "%s (%s)" % (__title__, e.number),
                    _(e.value) )
                return False


    def _play(self, otr, url=False):
        if not url:
            url = call.params['url']

        if not vfs.exists(url) and url.startswith('http'):
            remote_url = self._downloadqueue(otr, url)

        if url:
            xbmc.log('got remote download url <%s> %s' % (type(remote_url), remote_url))
            return False
            xbmc.Player().play(remote_url)
            print "player returned"
        return True


    def _download(self, otr, remote_url=False):
        if not remote_url:
            remote_url = self._downloadqueue(otr, call.params['url'])
            xbmc.log('got remote download url <%s> %s' % (type(remote_url), remote_url))
        if isinstance(remote_url, str) or isinstance(remote_url, unicode):
            archive = Archive.Archive()
            local_path = archive.downloadEpgidItem(call.params['epgid'], call.params['name'], remote_url)
            if local_path and __addon__.getSetting('otrAskPlayAfterDownload') == 'true':
                xbmc.executebuiltin("Container.Refresh")
                if xbmcgui.Dialog().yesno(
                    __title__,
                    _('download completed, play file now?'),
                    str(remote_url.split('/').pop()) ):
                    self._play(otr, local_path)
        return True


    def eval(self, otr):
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
                '/': ['recordings', 'scheduling'],
                '/scheduling' : ['tvguide', 'searchpast', 'searchfuture'],
                '/scheduling/searchpast': self._createPastSearchList,
                '/scheduling/searchfuture': self._createFutureSearchList,
                '/scheduling/tvguide': self._createProgrammList,
                '/recordings': self._createRecordingList,
                '/deletejob': self._deleteJob,
                '/schedulejob': self._scheduleJob,
                '/userinfo': self._showUserinfo,
                '/deletelocalcopies': self._deleteLocalCopies,
                '/refreshlisting': self._refreshListing,
                '/play': self._play,
                '/download': self._download,
                }

        #get the list
        sub = getKey(path, call.path)
        if isinstance(sub, list):
            self.listing = self._createDir(sub)
        elif isinstance(sub, types.MethodType):
            self.listing = sub(otr)
        else:
            print('unknown menue type: %s' % sub)


    def send(self):
        """
        Send output to XBMC
        @return void
        """
        if isinstance(self.listing, list):
            handler = int(call.fragment)
            xbmcplugin.setContent(handler, 'tvshows')
            for item in self.listing:
                xbmcplugin.addDirectoryItem(handler, item[0], item[1], item[2])
            xbmcplugin.endOfDirectory(handler)


