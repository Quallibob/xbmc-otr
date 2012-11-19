__author__ = 'fep'

import xbmc
import xbmcaddon
import xbmcgui
import os
import shutil
import sys
import time
import re

from Translations import _
import Simplebmc

try:
    import json
except ImportError:
    import simplejson as json


__addon__ = xbmcaddon.Addon()
__title__ = 'onlinetvrecorder.com'
__sx__ = Simplebmc.Simplebmc()


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

    class LastFile:

        __archive = None

        def __init__(self, archive):
            self.__archive = archive

        def getFilename(self):
            return os.path.join(self.__archive.path, 'last')

        def touch(self):
            last_file = os.path.join(self.__archive.path, 'last')
            try:
                open(last_file, 'w+').close()
            except Exception, e:
                __sx__.Notification(last_file, str(e))
                return False
            else:
                xbmc.log('touched %s' % last_file)
                return True

        def last(self):
            last_file = os.path.join(self.__archive.path, 'last')
            try:
                return int(time.time() - os.stat(last_file).st_mtime)
            except Exception, e:
                xbmc.log("%s: %s" % (last_file, str(e)))
                return -1


    def __getStreamSelection(self, otr, epgid):
        """
        aggregiert die informationen der verfuegbaren streams

        @param otr: OtrHandler
        @type  otr: OtrHandler Instanz
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

        # from pprint import pprint; pprint(element)

        item = {
            'epgid': element['EPGID'],
            'label': element['TITLE'],
            'filename': element['FILENAME'],
            'icon_image': self.__getOnlineImageName(element['FILENAME'], '1'),
            'thumbnail_image': self.__getOnlineImageName(element['FILENAME'], 'A')
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


    def __getOnlineImageName(self, filename, selection):
        """
        liefert thumbnail dateinamen zurueck
        """
        filename = filename.split('TVOON_DE')[0] + 'TVOON_DE' + '____'
        filename = re.sub('^\d*_', '', filename)
        return '%s%s.jpg' % (filename, selection)


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


    def __cleanupOnlineinfoFromAllLocalCopies(self):
        for epgid in self.__findAllRecordingInfo():
            json_file = self.__getEpgidJsonFile(epgid)
            recording_info = json.load(open(json_file))
            recording_info['streams'] = {}
            try:
                json.dump(recording_info, open(json_file, 'w+'))
            except Exception, e:
                __sx__.Notification(json_file, str(e))
            else:
                xbmc.log('wrote %s' % json_file)


    def __dumpAllRecordingInfo(self):
        if self.LastFile(self).touch():
            for epgid in self.recordings:
                path = self.__getLocalEpgidPath(epgid)
                try:
                    json.dump(self.recordings[epgid], open(self.__getEpgidJsonFile(epgid), 'w+'))
                except Exception, e:
                    __sx__.Notification(path, str(e))
                else:
                    xbmc.log('wrote %s' % path)


    def __getLocalEpgidPath(self, epgid, mkdir=True):
        path = os.path.join(self.path, epgid)
        if not os.path.exists(path) and mkdir:
            os.mkdir(path)
            print "created dir %s" % path
        return path


    def __findEpgidLocalCopies(self, local_path):
        for filename in os.listdir(local_path):
            json_file = os.path.join(local_path, filename)
            if filename.endswith('.json.v1'):
                reference_file = json_file.rstrip('.json.v1')
                try:
                    file_info = json.load(open(json_file))
                except Exception, e:
                    xbmc.log("%s: %s" % (json_file, str(e)))
                else:
                    if 'type' in file_info and file_info['type'] == 'local_copy':
                        file_info['file'] = reference_file
                        file_info['file_type'] = reference_file.split('.').pop()
                        file_info['json_file'] = json_file
                        yield {file_info['date']:file_info}


    def __getEpgidJsonFile(self, epgid):
        path = self.__getLocalEpgidPath(epgid, mkdir=False)
        json_file = os.path.join(path, 'json.v1')
        return json_file

    def __findAllRecordingInfo(self):
        for filename in os.listdir(self.path):
            json_file = self.__getEpgidJsonFile(filename)
            try:
                if os.path.isfile(json_file):
                    if not isinstance(json.load(open(json_file)), dict):
                        continue
                else:
                    continue
            except Exception, e:
                xbmc.log("%s: %s" % (json_file, str(e)))
            else:
                epgid = filename
                yield epgid


    def deleteLocalEpgidPath(self, epgid=False, file=False):

        if epgid:
            path = self.__getLocalEpgidPath(epgid, mkdir=False)
            json_file = self.__getEpgidJsonFile(epgid)
        elif file:
            path = file
            json_file = path + '.json.v1'
        else:
            return False

        if not os.path.isfile(json_file):
            xbmc.log('could not delete %s, no info file found' % path)
        else:
            try:
                if os.path.isfile(path):
                    os.remove(path)
                    if os.path.isfile(json_file):
                        os.remove(json_file)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
            except Exception, e:
                xbmc.log("failed to delete %s (%s)" % (path, str(e)))
            else:
                return True

        return False


    def downloadEpgidItem(self, epgid, name, url):
        local_dir = self.__getLocalEpgidPath(epgid)
        local_filename = str(url.split('/').pop())
        local_path = os.path.join(local_dir, local_filename)

        file_info = {
            'name':  name,
            'type': 'local_copy',
            'date': int(time.time())
        }

        try:
            xbmc.log("download: %s" % __sx__.Downloader(url, local_path))
        except IOError,e :
            __sx__.Notification(local_filename, 'could not write file (%s)' % str(e.strerror))
        except Exception, e:
            __sx__.Notification(local_filename, e)
        else:
            xbmc.log('wrote %s' % local_path)
            json_filename = local_path +  '.json.v1'
            try:
                json.dump(file_info, open(json_filename, 'w+'))
            except Exception, e:
                __sx__.Notification(json_filename, str(e))
            else:
                xbmc.log('wrote %s' % json_filename)
                return local_path
        return False


    def getImageUrl(self, epgid, filename):
        """
        liefert dynamisch die thumbnail url zurueck
        """
        url_local = os.path.join(self.__getLocalEpgidPath(epgid), filename)
        if os.path.isfile(url_local):
            return url_local
        else:

            date_match = re.match('.*_(\d\d\.\d\d\.\d\d)_.*', filename)
            if date_match:
                date_part = "%s/" % date_match.group(1)
            else:
                date_part = ""

            url_online = 'http://thumbs.onlinetvrecorder.com/' + date_part + filename
            print url_online
            try:
                __sx__.Downloader(url_online, url_local, progress=False)
                xbmc.log('wrote pic %s' % url_local)
                return url_local
            except Exception, e:
                xbmc.log('%s: %s' % (url_local, str(e)))
                return url_online


    def load(self):
        for epgid in self.__findAllRecordingInfo():
                recording_info = json.load(open(self.__getEpgidJsonFile(epgid)))
                local_path = os.path.join(self.path, epgid)
                recording_info['copies'] = dict()
                for copy in self.__findEpgidLocalCopies(local_path):
                    recording_info['copies'].update(copy)
                self.recordings[epgid] = recording_info


    def refresh(self, otr):

        self.__cleanupOnlineinfoFromAllLocalCopies()

        for element in self.__getOnlineList(otr):
            self.recordings[element['epgid']] = element

        self.__dumpAllRecordingInfo()


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
