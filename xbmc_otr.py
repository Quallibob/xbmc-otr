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
import xbmc
import xbmcplugin
import xbmcaddon
import xbmcgui
import urllib
import base64
import time
import datetime
import types
import OtrHandler
import simplebmc

from translations import _
from LocalArchive import LocalArchive
from call import call

try:
    import CommonFunctions
except ImportError, e:
    # local copy version from http://hg.tobiasussing.dk/hgweb.cgi/commonxbmc/ for apple tv integration
    print "LocalCommonFunctions loaded"

try:
    from urlparse import parse_qs
except ImportError:
    #noinspection PyDeprecation
    from cgi import parse_qs

    

__title__ = 'onlinetvrecorder.com'
__addon__ = xbmcaddon.Addon()
__sx__ = simplebmc.Simplebmc()
__common__ = CommonFunctions

def DownloaderClass(url,dest):
    dp = xbmcgui.DialogProgress()
    dp.create("Download", url.split('/').pop())
    urllib.urlretrieve(url,dest,lambda nb, bs, fs, url=url: _pbhook(nb,bs,fs,url,dp))
 
def _pbhook(numblocks, blocksize, filesize, url=None, dp=None):
    try:
        percent = min((numblocks*blocksize*100)/filesize, 100)
        dp.update(percent)
    except:
        dp.close()
    if dp.iscanceled(): 
        dp.close()
        raise Exception('download canceled')



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

    def __init__(self):
        """
        constructor
        @param int pluginId - Current instance of plugin identifer
        """
        __addon__ = xbmcaddon.Addon()
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
            self._otr.getOtrSubcode()
        except Exception, e:
            print "login failed (1): %s" % e
            xbmcgui.Dialog().ok(
                __title__,
                _('login failed'),  
                _(str(e)) )
            sys.exit(0)
        else:
            try:
                timeout = int(float(__addon__.getSetting('otrTimeout')))
            except Exception, e:
                pass
            else:
                self._otr.setTimeout(timeout)

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
            coockie = os.path.join(
                        xbmc.translatePath('special://temp'),
                        '%s%s' % (__title__, '.cookie') )
            self._otr.setCookie(coockie)
            self._otr.login(username, password)
        except Exception, e:
            print "login failed (2): %s" % e
            xbmcgui.Dialog().ok(
                __title__,
                _('login failed'),
                _(str(e)) )
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
    _common = None
    listing = []

    def __init__(self):
        """
        constructor
        """

    def _createList(self, otr):
        """
        Create the dynamic list of all content
        @param list dirContent - list of __PLAYLIST__ files in gpodder directory
        @param string dir - gpodder directory location
        @access private
        @return list
        """
        archive = LocalArchive()
        archive.load()
        print "last: %s" % archive.LastFile(archive).last()
        if archive.LastFile(archive).last() < 0 or archive.LastFile(archive).last() > 500:
            archive.refresh(otr)
        return []


    def createDir(self, subs):
        """
        dir listing fuer uebersichten erzeugen

        @param subs: listenelemente
        @type  subs: list
        """
        listing = []
        for element in subs:
            li = xbmcgui.ListItem( label=_(element) )
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
        return self._createList(otr)

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
                xbmc.executebuiltin('Notification("%s", "%s")' % (
                    __title__,
                    _("scheduleJob: %s" % res) ) )
            return True


    def _deleteJob(self, otr, ask=True):
        """
        aufnahme loeschen

        @param otr: OtrHandler
        @type  otr: OtrHandler Instanz
        """
        if __addon__.getSetting('otrAskDelete') == 'true': ask = True
        if __addon__.getSetting('otrAskDelete') == 'false': ask = False
        if not ask or xbmcgui.Dialog().yesno(__title__, _('delete job?')):
            prdialog = xbmcgui.DialogProgress()
            prdialog.create(_('delete'))
            prdialog.update(0)
            otr.deleteJob( call.params['epgid'] )
            prdialog.update(100)
            prdialog.close()
            self._deleteLocalCopys(otr, ask=True)
            xbmc.executebuiltin("Container.Refresh")
            xbmc.executebuiltin('Notification("%s", "%s")' % (
                __title__,
                _("job deleted") ) )
            return True

    def _showUserinfo(self, otr):
        """
        userinfo anzeigen

        @param otr: OtrHandler
        @type  otr: OtrHandler Instanz
        """
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
                weekstring = " -" + _(weekdelta<-1 and "%s weeks" or "%s week") % (weekdelta*-1) 
                month_start_name = _(weekstart.date().strftime("%B")) 
                month_end_name = _((weekstart.date()+datetime.timedelta(days=6)).strftime("%B"))
                weekstring += " (%s - %s)" % (
                        weekstart.date().strftime("%d. " + month_start_name + " %Y"), 
                        (weekstart.date()+datetime.timedelta(days=6)).strftime("%d. " + month_end_name + " %Y")
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
                weekstring = " +" + _(weekdelta>1 and "%s weeks" or "%s week") % weekdelta
                month_start_name = _(weekstart.date().strftime("%B")) 
                month_end_name = _((weekstart.date()+datetime.timedelta(days=6)).strftime("%B"))
                weekstring += " (%s - %s)" % (
                        weekstart.date().strftime("%d. " + month_start_name + " %Y"), 
                        (weekstart.date()+datetime.timedelta(days=6)).strftime("%d. " + month_end_name + " %Y")
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




    def _deleteLocalCopys(self, otr, ask=False):
        if ask:
            if not xbmcgui.Dialog().yesno(
                __title__,
                _('do you want do delete existing local copys?')):
                    return False
            
        streamlist = eval(base64.urlsafe_b64decode(parse_qs(self._url.query)['streamlist'].pop()))
        for filepath in self._getLocalDownloadPath(streamlist.values()):
            try:
                if os.access(filepath, os.F_OK):
                    os.remove(filepath)
            except OSError, e:
                __sx__.Notification(filepath.split('/').pop(), 'skipped file (%s)' % e.strerror)
            except IOError, e:
                __sx__.Notification(filepath.split('/').pop(), 'could not delete file (%s)' % e.strerror)
            except Exception, e:
                __sx__.Notification(filepath.split('/').pop(), e)
                raise e


            


    def _selectStream(self, otr):
        """
        aufnahme loeschen

        @param otr: OtrHandler
        @type  otr: OtrHandler Instanz
        """
        mode = self._url.path.lstrip('/')

        streamlist = eval(base64.urlsafe_b64decode(parse_qs(self._url.query)['streamlist'].pop()))
        filename = base64.urlsafe_b64decode(parse_qs(self._url.query)['file'].pop())
        choice = xbmcgui.Dialog().select(filename, streamlist.keys())
        if choice >= 0:
            uri = streamlist[streamlist.keys()[choice]]
            if mode == 'streamselect':
                self._play(otr, uri) #executebuiltin("RunScript(%s)" % uri, True)
            if mode == 'downloadselect':
                self._download(otr, uri)
        return True



    def _downloadqueue(self, otr, requesturi):
        queuemax = 0
        xbmc.executebuiltin("Dialog.Close(all,true)", True)
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
                for step in reversed(range(1, 20)):
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
                
    def _play(self, otr, requesturi=False):

        if not requesturi:
            if not 'fileuri' in parse_qs(self._url.query):
                raise Exception('play without fileuri not possible')
            else:
                requesturi = base64.urlsafe_b64decode(parse_qs(self._url.query)['fileuri'].pop())

        localfile = self._getLocalDownloadPath(requesturi)
        if os.access(localfile, os.F_OK):
            print "playing file %s" % localfile
            xbmc.executebuiltin("XBMC.PlayMedia(\"%s\")" % localfile, True)
        else:
            remoteurl = self._downloadqueue(otr, requesturi)
            if remoteurl:
                print "playing url %s" % remoteurl
                xbmc.executebuiltin("XBMC.PlayMedia(\"%s\")" % remoteurl, True)

        return True






    def _download(self, otr, requesturi=False):

        if not requesturi:
            if not 'fileuri' in parse_qs(self._url.query):
                raise Exception('play without fileuri not possible')
            else:
                requesturi = base64.urlsafe_b64decode(parse_qs(self._url.query)['fileuri'].pop())

        url = self._downloadqueue(otr, requesturi)
        if isinstance(url, str):
            filename = url.split('/').pop()
            target = self._getLocalDownloadPath(url)

            if os.access(target, os.F_OK):
                if not xbmcgui.Dialog().yesno(
                    __title__,
                    _('file already exists, overwrite?'),
                    str(filename) ): return True

            try:
                print "downloading url %s to %s" % (url, target)
                DownloaderClass(url, target)
            except IOError,e :
                __sx__.Notification(filename, 'could not write file (%s)' % str(e.strerror))
            except Exception, e:
                __sx__.Notification(filename, e)
            else:
                if 'epgid' in parse_qs(self._url.query):
                    egid = parse_qs(self._url.query)['epgid'].pop()
                if __addon__.getSetting('otrAskPlayAfterDownload') == 'true':
                    if xbmcgui.Dialog().yesno(
                        __title__,
                        _('download completed, play file now?'),
                        str(filename) ):
                            self._play(otr, target)
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
                #'/scheduling/pasthighlights': self._createPastHightlightsList,
                '/scheduling/tvguide': self._createProgrammList,
                '/recordings': self._createRecordingList,
                '/deletejob': self._deleteJob,
                '/schedulejob': self._scheduleJob,
                '/userinfo': self._showUserinfo,
                '/streamselect': self._selectStream,
                '/downloadselect': self._selectStream,
                '/deletelocalcopys': self._deleteLocalCopys,
                '/play': self._play,
                '/download': self._download,
                }

        #get the list
        sub = getKey(path, call.path)
        if isinstance(sub, list):
            ret = self.createDir(sub)
            if call.path == '/':
                if otr.newVersionAvailable():
                    # main dir and new version available
                    # TODO! remove in repo release!
                    print "new version available!"
                    ret.append(
                        [
                        call.format(),
                        xbmcgui.ListItem( label=_('new version available') ),
                        False
                        ])
            self.listing = ret
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


