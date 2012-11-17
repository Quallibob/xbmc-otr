__author__ = 'fep'

import xbmc
import xbmcaddon
import xbmcgui
import os
import sys
import time
import urllib


import simplebmc
from translations import _

try:
    import json
except ImportError:
    import simplejson as json


__addon__ = xbmcaddon.Addon()
__title__ = 'onlinetvrecorder.com'
__sx__ = simplebmc.Simplebmc()

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


def getKey(obj, *elements):
    for element in elements:
        if element in obj:
            obj = obj[element]
        else:
            return False
    return obj


class LocalArchive:

    path = "."
    recordings = []

    def __getLocalDownloadPath(self, url):
        if isinstance(url, list):
            result = []
            for element in url:
                result.append(self._getLocalDownloadPath(element))
            return result
        else:
            return os.path.join(self.path, url.split('/').pop())


    def __getStreamSelection(self, otr, epgid):
        """
        aggregiert die informationen der verfuegbaren streams

        @param stream_list: stream xml struktur die von otr kommt
        @type  stream_list: dict
        @param epgid: epgid der  aufnahme
        @type  epgid: string
        """


        def get_aggregated_stream(stream, stream_element):
            """
            aggregiert die informationen eines einzelnen streams

            @param stream_element: stream xml struktur die von otr kommt
            @type  stream_element: dict
            """
            if not stream_element: return False
            if  __addon__.getSetting('otrPreferPrio') == 'true':
                stype = ( (getKey(stream_element, 'PRIO') and 'PRIO') or
                          (getKey(stream_element, 'FREE') and 'FREE') or False )
            else:
                stype = ( (getKey(stream_element, 'FREE') and 'FREE') or
                          (getKey(stream_element, 'PRIO') and 'PRIO') or False )
            if not stype: return False

            size = getKey(stream_element, 'SIZE')
            size_string = getSizeStr(long(size)*1024)
            url  = getKey(stream_element, stype)
            gwp  = getKey(stream_element, 'GWPCOSTS', stype)

            name = stream
            if not __addon__.getSetting('otrShowUnspported') == 'true':
                name = name.replace('unkodiert', '')
            name = name.replace('_', ' ').strip()
            name += ", %s" % size_string
            name += ", %s GWP" % gwp

            return {
                stream: {
                    'file': url,
                    'file_type': url.split('.').pop(),
                    'name': name,
                    'cost': gwp,
                    'size': size,
                    'size_string': size_string,
                    'type': stype
                    }
                }

        def get_stream_order():
            """
            streamvorsortierung nach den einsellungen
            """
            stream_order = []
            if __addon__.getSetting('otrAcceptAVI') == 'true':
                stream_order.append('AVI_unkodiert')
            stream_order.append('MP4_Stream')
            stream_order.append('MP4_unkodiert')
            if __addon__.getSetting('otrPreferCut') == 'true':
                stream_order.insert(0, 'MP4_geschnitten')
            if __addon__.getSetting('otrPreferHQ') == 'true':
                if __addon__.getSetting('otrAcceptAVI') == 'true':
                    stream_order.insert(0, 'HQAVI_unkodiert')
                stream_order.insert(0, 'HQMP4')
                stream_order.insert(0, 'HQMP4_Stream')
                if __addon__.getSetting('otrPreferCut') == 'true':
                    if __addon__.getSetting('otrAcceptAVI') == 'true':
                        stream_order.insert(0, 'HQ_geschnitten')
                    stream_order.insert(0, 'HQMP4_geschnitten')
            if __addon__.getSetting('otrPreferHD') == 'true':
                if __addon__.getSetting('otrAcceptAVI') == 'true':
                    stream_order.insert(0, 'HDAVI_unkodiert')
                stream_order.insert(0, 'HDMP4')
                stream_order.insert(0, 'HDMP4_Stream')
                if __addon__.getSetting('otrPreferCut') == 'true':
                    if __addon__.getSetting('otrAcceptAVI') == 'true':
                        stream_order.insert(0, 'HD_geschnitten')
                    stream_order.insert(0, 'HDMP4_geschnitten')
            return stream_order

        def get_stream_selection(stream_list):
            selection = dict()
            for stream in stream_list.keys():
                stream_info = get_aggregated_stream( stream, stream_list[stream] )
                if not stream_info:
                    continue
                if not __addon__.getSetting('otrShowUnsupported') == 'true':
                    if not stream_info[stream]['file_type'] in ['avi', 'mp4', 'mp3']:
                        # skip unsupported
                        continue
                selection.update( stream_info )
            return selection

        def get_ordered_selection(stream_selection, stream_order):
            result = dict(); count = 0
            for stream in stream_order:
                if getKey(stream_selection, stream):
                    result.update( {'%d_%s' % (count, stream) : stream_selection[stream] } )
                    count += 1
            return result

        stream_list = otr.getFileInfoDict(epgid)
        stream_order = get_stream_order()
        stream_selection = get_stream_selection(stream_list)
        stream_selection = get_ordered_selection(stream_selection, stream_order)

        return stream_selection


    def __getOnlineElementDetails(self, otr, element):

        item = {
            'epgid': element['EPGID'],
            'label': element['TITLE'],
            'filename': element['FILENAME'],
            'iconImage': self.__getOnlineImageName(element['FILENAME'], '1'),
            'thumbnailImage': self.__getOnlineImageName(element['FILENAME'], 'A')
            }

        if 'BEGIN' in element:
                                    item['label']       += " (%s)" % element['BEGIN']

        if 'DURATION' in element:   item['duration']    =  element['DURATION'].split()[0]
        if 'TITLE' in element:      item['title']       =  element['TITLE']
        if 'STATION' in element:    item['studio']      =  element['STATION']
        if 'BEGIN' in element:      item['date']        =  element['BEGIN']
        if 'TITLE2' in element:     item['plot']        =  element['TITLE2']

        item['streams'] = self.__getStreamSelection(otr, item['epgid'])

        return item


    def __getLocalEpgidPath(self, epgid, mkdir=True):
        path = os.path.join(self.path, epgid)
        if not os.path.exists(path) and mkdir:
            os.mkdir(path)
            print "created dir %s" % path
        return path


    def getImageUrl(self, epgid, filename):
        """
        liefert dynamisch die thumbnail url zurueck
        """
        url_local = os.path.join(self.__getLocalEpgidPath(epgid), filename)
        url_online = 'http://thumbs.onlinetvrecorder.com/' + filename
        if os.path.isfile(url_local):
            return url_local
        else:
            try:
                DownloaderClass(url_online, url_local)
                xbmc.log('wrote pic %s' % url_local)
            except Exception, e:
                xbmc.log('%s: %s' % (url_local, str(e)))
                return url_online
            else:
                return url_local

    def __getOnlineImageName(self, filename, selection):
        """
        liefert thumbnail dateinamen zurueck
        """
        url = filename.split('TVOON_DE')[0] + 'TVOON_DE' + '____'
        return '%s%s.jpg' % (url, selection)


    def __getOnlineList(self, otr):
        prdialog = xbmcgui.DialogProgress()
        prdialog.create(_('loading recording list'))
        prdialog.update(0)
        listing = []

        try:
            # eigentliche Liste abfragen
            recordings = otr.getRecordListDict(orderby="time_desc")

        except Exception, e:
            print "loading recording list failed (%s)" % str(e)
            prdialog.close()
            xbmcgui.Dialog().ok(
                __title__,
                _('loading recording list failed'),
                _(str(e)) )
            return []

        else:
            recordings = getKey(recordings, 'FILE') or []
            if not isinstance(recordings, list):
                # liste hat nur einen eintrag
                recordings = [recordings]

            for element in recordings:
                if prdialog.iscanceled():
                    return listing
                prdialog.update( int((recordings.index(element)+1)*100/len(recordings)) , element['FILENAME'])

                try:
                    item = self.__getOnlineElementDetails(otr, element)
                except Exception, e:
                    print "getFileInfo failed (%s)" % str(e)
                    __sx__.Notification(element['FILENAME'], str(e))
                else:
                    if item: listing.append(item)

        finally:
            prdialog.close()

        return listing

    class LastFile:

        __archive = None

        def __init__(self, archive):
            self.__archive = archive

        def getFilename(self):
            return os.path.join(self.__archive.path, 'last')

        def touch(self):
            try:
                last_file = os.path.join(self.__archive.path, 'last')
                open(last_file, 'w+').close()
            except Exception, e:
                __sx__.Notification(last_file, str(e))
                return False
            else:
                xbmc.log('touched %s' % last_file)
                return True

        def last(self):
            try:
                last_file = os.path.join(self.__archive.path, 'last')
                return int(time.time() - os.stat(last_file).st_mtime)
            except Exception, e:
                xbmc.log("%s: %s" % (last_file, str(e)))
                return -1

    def __dumpRecordingInfo(self):
        if self.LastFile(self).touch():
            for epgid in self.recordings:
                path = self.__getLocalEpgidPath(epgid)
                try:
                    json.dump(self.recordings[epgid], open(os.path.join(path, 'json.v1'), 'w+'))
                except Exception, e:
                    __sx__.Notification(path, str(e))
                else:
                    xbmc.log('wrote %s' % path)


    def load(self):
        for filename in os.listdir(self.path):
            json_file = os.path.join(self.path, filename, 'json.v1')
            try:
                if os.path.isfile(json_file):
                    self.recordings[filename] = json.load(open(json_file))
            except Exception, e:
                xbmc.log("%s: %s" % (json_file, str(e)))


    def refresh(self, otr):

        for element in self.__getOnlineList(otr):
            self.recordings[element['epgid']] = element

        self.__dumpRecordingInfo()


    def __init__(self):

        self.recordings = dict()

        # set path
        if __addon__.getSetting('otrDownloadFolder') in ['special://temp', '']:
            self.path = os.path.join(xbmc.translatePath('special://temp'), __addon__.getAddonInfo('id'))
        else:
            self.path = __addon__.getSetting('otrDownloadFolder')

        try:
            if not os.path.exists(self.path):
                os.mkdir(self.path)
                print "created dir %s" % self.path
        except OSError,e :
            __sx__.Notification(self.path, 'could not create dir (%s)' % str(e.strerror))
            sys.exit(0)
        except Exception, e:
            xbmc.log("%s: %s" % (self.path, str(e)))
            sys.exit(0)
