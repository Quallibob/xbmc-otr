__author__ = 'fep'

import xbmc
import xbmcaddon
import xbmcgui
import shutil
import sys
import time
import re

from Translations import _
import Simplebmc
import Vfs as vfs

try:
    import json
except ImportError:
    #noinspection PyUnresolvedReferences
    import simplejson as json


__addon__ = xbmcaddon.Addon()
__title__ = 'onlinetvrecorder.com'
__sx__ = Simplebmc.Simplebmc()



def getKey(obj, *elements):
    for element in elements:
        if element in obj:
            obj = obj[element]
        else:
            return False
    return obj

class NoException(Exception): pass

class Archive:

    path = "."
    recordings = []

    class LastFile:

        __archive = None

        def __init__(self, archive):
            assert isinstance(archive, Archive)
            self.__archive = archive

        def getFilename(self):
            return vfs.path.join(self.__archive.path, 'last')

        def touch(self):
            last_file = vfs.path.join(self.__archive.path, 'last')
            try:
                last_file_object = vfs.File(last_file, 'w')
                last_file_object.write(str(int(time.time())))
                last_file_object.close()
            except Exception, e:
                __sx__.Notification(last_file, str(e))
                return False
            else:
                xbmc.log('touched %s' % last_file)
                return True

        def last(self):
            last_file = vfs.path.join(self.__archive.path, 'last')
            try:
                last_file_object = vfs.File(last_file, 'r')
                last_content = last_file_object.read()
                last_file_object.close()
                return int(time.time() - int( __sx__.noNull(last_content)) )
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
            size_string = __sx__.humanSize(long(size)*1024)
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

        def getXbmcDate(otr_date):
            try:
                otr_date = time.strptime(element['BEGIN'], '%d.%m.%Y %H:%M:%S');
            except Exception, e:
                print("%s: %s" % (element['BEGIN'], e))
                return otr_date
            else:
                otr_date = "%02d/%02d/%04d" % (otr_date.tm_mday, otr_date.tm_mon, otr_date.tm_year)
                return otr_date


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
        if 'BEGIN' in element:      item['date']        =  getXbmcDate(element['BEGIN'])
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


    def __cleanupAllLocalCopies(self):
        for epgid in self.__findAllRecordingInfo():
            if len(list(self.__findEpgidLocalCopies(self.__getLocalEpgidPath(epgid)))) < 1:
                self.deleteLocalEpgidPath(epgid=epgid)
            else:
                json_file = self.__getEpgidJsonFile(epgid)
                recording_info = json.loads( __sx__.noNull(vfs.File(json_file).read()) )
                recording_info['streams'] = {}
                try:
                    vfs.File(json_file, 'w').write(json.dumps(recording_info))
                except Exception, e:
                    __sx__.Notification(json_file, str(e))
                else:
                    xbmc.log('wrote %s' % json_file)


    def __dumpAllRecordingInfo(self):
        if self.LastFile(self).touch():
            for epgid in self.recordings:
                path = self.__getLocalEpgidPath(epgid)
                try:
                    vfs.File(self.__getEpgidJsonFile(epgid), 'w').write(json.dumps(self.recordings[epgid]))
                except Exception, e:
                    __sx__.Notification(path, str(e))
                else:
                    xbmc.log('wrote %s' % path)


    def __getLocalEpgidPath(self, epgid, mkdir=True):
        path = vfs.path.join(self.path, epgid)
        if not vfs.exists(path) and mkdir:
            vfs.mkdir(path)
            print "created dir %s" % path
        return path


    def __findEpgidLocalCopies(self, local_path):
        for file_name in vfs.listdir(local_path)[1]:
            if file_name.endswith('.json.v1'):
                json_file = vfs.path.join(local_path, file_name)
                reference_file = json_file.rstrip('.json.v1')

                if not vfs.exists(reference_file):
                    continue

                try:
                    file_info = json.loads( __sx__.noNull(vfs.File(json_file).read()) )
                except Exception, e:
                    xbmc.log("%s: %s" % (json_file, str(e)))
                else:
                    if 'type' in file_info and file_info['type'] == 'local_copy':
                        file_info['file'] = reference_file
                        file_info['file_type'] = reference_file.split('.').pop()
                        file_info['json_file'] = json_file
                        yield {file_info['file_name']:file_info}


    def __getEpgidJsonFile(self, epgid):
        path = self.__getLocalEpgidPath(epgid, mkdir=False)
        json_file = vfs.path.join(path, 'json.v1')
        return json_file

    def __findAllRecordingInfo(self):
        for dir_name in vfs.listdir(self.path)[0]:
            json_file = self.__getEpgidJsonFile(dir_name)
            try:
                if vfs.exists(json_file):
                    if not isinstance(json.loads( __sx__.noNull(vfs.File(json_file).read()) ), dict):
                        continue
                else:
                    continue
            except Exception, e:
                xbmc.log("%s: %s" % (json_file, str(e)))
            else:
                epgid = dir_name
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

        if not vfs.exists(json_file):
            xbmc.log('could not delete %s, no info file found' % path)
            return False

        else:
            try:
                if file:
                    if vfs.exists(path):
                        vfs.delete(path)
                    if vfs.exists(json_file):
                        vfs.delete(json_file)
                elif epgid and vfs.exists(path):
                    for file_name in vfs.listdir(path)[1]:
                        file_path = vfs.path.join(path, file_name)
                        vfs.delete(file_path)
                    vfs.rmdir(path)
            except Exception, e:
                xbmc.log("failed to delete %s (%s)" % (path, str(e)))
            else:
                return True

        return False


    def downloadEpgidItem(self, epgid, name, url):
        local_dir = self.__getLocalEpgidPath(epgid)
        local_filename = str(url.split('/').pop())
        local_path = vfs.path.join(local_dir, local_filename)

        file_info = {
            'name':  name,
            'file_name': local_filename,
            'type': 'local_copy',
            'date': int(time.time())
        }

        try:
            xbmc.log("download: %s" % __sx__.Downloader(url, local_path))
        except IOError,e :
            __sx__.Notification(local_filename, 'could not write file (%s)' % str(e.strerror))
        except NoException, e:
            __sx__.Notification(local_filename, e)
        else:
            xbmc.log('wrote %s' % local_path)
            json_filename = local_path +  '.json.v1'
            try:
                vfs.File(json_filename, 'w').write(json.dumps(file_info))
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
        url_local = vfs.path.join(self.__getLocalEpgidPath(epgid), filename)
        if vfs.exists(url_local):
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
                __sx__.Downloader(url_online, url_local, progress=False, background=True)
                xbmc.log('wrote pic %s' % url_local)
                return url_local
            except Exception, e:
                xbmc.log('%s: %s' % (url_local, str(e)))
                return url_online


    def load(self):
        for epgid in self.__findAllRecordingInfo():
            recording_info = json.loads( __sx__.noNull(vfs.File(self.__getEpgidJsonFile(epgid)).read()) )
            local_path = vfs.path.join(self.path, epgid)
            recording_info['copies'] = dict()
            for copy in self.__findEpgidLocalCopies(local_path):
                recording_info['copies'].update(copy)
            self.recordings[epgid] = recording_info


    def refresh(self, otr):

        self.__cleanupAllLocalCopies()

        for element in self.__getOnlineList(otr):
            self.recordings[element['epgid']] = element

        self.__dumpAllRecordingInfo()


    def __init__(self):

        self.recordings = dict()

        # set path
        if __addon__.getSetting('otrDownloadFolder') in ['special://temp', '']:
            self.path = vfs.path.join(xbmc.translatePath('special://temp'), __addon__.getAddonInfo('id'))
        else:
            self.path = __addon__.getSetting('otrDownloadFolder')

        try:
            if not vfs.exists(self.path):
                vfs.mkdir(self.path)
                print "created dir %s" % self.path
        except OSError,e :
            __sx__.Notification(self.path, 'could not create dir (%s)' % str(e.strerror))
            sys.exit(0)
        except Exception, e:
            xbmc.log("%s: %s" % (self.path, str(e)))
            sys.exit(0)
