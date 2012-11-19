#!/usr/bin/python
# vim: tabstop=4 shiftwidth=4 smarttab expandtab softtabstop=4 autoindent

"""
    Document   : OtrHandler.py
    Package    : OTR Integration to XBMC
    Author     : Frank Epperlein
    Copyright  : 2012, Frank Epperlein, DE
    License    : Gnu General Public License 2
    Description: OTR access library
"""

import urllib
import urllib2
import hashlib
import os
import base64
import socket
import pprint
from resources.lib import XmlDict, pah2Nahbae4cahzihach1aep

try:
    from xml.etree import ElementTree
except ImportError:
    import ElementTree

try: import simplejson as json
except ImportError: import json

URL_OTR="http://www.onlinetvrecorder.com"
URL_SUBCODE="http://j.mp/otrsubcode"
VERSION="0.6"
VERSION_CHECK="http://shellshark.pythonanywhere.com/otr/xbmc-otr/currentstable?version=%s"

class OtrHandler:
    """
    OTR Representation
    """

    __session   = False
    __apiauth   = ""
    __subcode   = False
    __otr_did   = False
    __otr_auth  = False
    __url_cookiepath = False
    __url_cookie     = None
    __url_request    = None
    __url_urlopen    = None
    __lastUsername   = ""
    __lastPassword   = ""

    class foundDownloadErrorException(Exception):
        number = 0
        def __init__(self, number, value):
            self.value = value
            self.number = number
        def __str__(self):
            return repr(self.value)

    class inDownloadqueueException(Exception):
        position = 0
        def __init__(self, value, position):
            self.value = value
            self.position = position
        def __str__(self):
            return repr(self.value)


    def setCookie(self, path=False):
        """
        set cookie handler
        """
        if path:
            self.__url_cookiepath = path
        try:
            import cookielib
        except ImportError:
            try:
                import ClientCookie
            except ImportError:
                urlopen = urllib2.urlopen
                Request = urllib2.Request
            else:
                urlopen = ClientCookie.urlopen
                Request = ClientCookie.Request
                self.__url_cookie = ClientCookie.MozillaCookieJar()
                if path and os.path.isfile(path):
                    try:
                        self.__url_cookie.load(path)
                    except Exception, e:
                        pass
                opener = ClientCookie.build_opener(ClientCookie.HTTPCookieProcessor(self.__url_cookie))
                ClientCookie.install_opener(opener)
                self.__url_request = Request
                self.__url_urlopen = urlopen
        else:
            urlopen = urllib2.urlopen
            Request = urllib2.Request
            self.__url_cookie = cookielib.MozillaCookieJar()
            if path and os.path.isfile(path):
                try:
                    self.__url_cookie.load(path)
                except Exception, e:
                    pass
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.__url_cookie))
            urllib2.install_opener(opener)
            self.__url_request = Request
            self.__url_urlopen = urlopen

    def __getXMLDict(self, xml, encoding="latin9"):
        """
        parse xml into dict

        @param xml: xml data
        @type  xml: string
        """
        tree = ElementTree.XML(xml.decode(encoding).encode('utf-8'))
        return XmlDict.XmlDict(tree)

    def __getUrl(self, url):
        """
        query url

        @param url: url to request
        @type  url: string
        """
        if len(self.__lastPassword):
            print url.replace(self.__lastPassword, 'X'*10)
        else:
            print url
        req = self.__url_request(url)
        req.add_header('User-Agent', 'XBMC OtrHandler')
        try:
            resp = self.__url_urlopen(req)
        except urllib2.URLError, e:
            raise Exception(pprint.pformat(e))
        return resp

    def newVersionAvailable(self):
        """
        check for new version
        """
        try:
            master = self.__getUrl(VERSION_CHECK % VERSION).read()
            if str(master) == "ok":
                return False
        except Exception, e:
            pass
        return True


    def setOtrSubcode(self, subcode):
        self.__subcode = subcode

    def getOtrSubcode(self):
        self.__subcode = self.__getUrl(URL_SUBCODE).read()
        return self.__subcode

    def __setAPIAuthKey(self):
        """
        set internal api access code

        @param did: programm code
        @type  did: int
        @param code: access code
        @type  code: string
        """
        if not self.__subcode: self.getOtrSubcode()
        checksum = hashlib.md5(self.__otr_auth % self.__subcode).hexdigest()
        self.__apiauth = "&checksum=%s&did=%s" % (checksum, self.__otr_did)


    def login(self, email, password):
        """
        login to otr

        @param email: email address or username
        @type  email: string
        @param password: user password
        @type  password: string
        """
        self.__setAPIAuthKey()
        self.__lastUsername = email
        self.__lastPassword = password
        requrl = "%s/downloader/api/login.php?" % URL_OTR
        requrl += self.__apiauth
        requrl += "&email=%s&pass=%s" % ( urllib.quote(email), urllib.quote(password) )
        resp = self.__session = self.__getUrl(requrl)
        resp = resp.read()
        if len(resp) and ' ' in resp:
            raise Exception(resp)
        else:
            if self.__url_cookiepath:
                try:
                    self.__url_cookie.save(self.__url_cookiepath)
                except Exception, e:
                    pass

    def scheduleJob(self, epgid):
        """
        schedule recording

        @param epgid: epgid
        @type  epgid: string
        """
        requrl = "%s/index.php?aktion=createJob&api=true&byid=true" % URL_OTR
        requrl += "&email=%s&pass=%s&epgid=%s" % ( 
            urllib.quote(self.__lastUsername), 
            urllib.quote(self.__lastPassword), 
            base64.urlsafe_b64encode(epgid) )
        resp = self.__session = self.__getUrl(requrl)
        resp = resp.read()
        return resp


    def deleteJob(self, epgid):
        """
        delete recording

        @param epgid: epgid
        @type  epgid: string
        """
        requrl = "%s/index.php?aktion=deleteJob" % URL_OTR
        requrl += "&email=%s&epgid=%s" % ( base64.urlsafe_b64encode(self.__lastUsername), base64.urlsafe_b64encode(epgid) )
        resp = self.__getUrl(requrl)
        resp = resp.read()
        return resp


    def getChannelListingDict(self, *args, **kwargs):
        lst = self.getChannelListing(*args, **kwargs)
        try:
            dct = self.__getXMLDict(lst)
            return dct
        except Exception, e:
            raise Exception(e)

    def getChannelListing(self, stations, start, end):
        requrl = "%s/index.php?&aktion=epg_export&format=xml&btn_ok=OK&" % URL_OTR
        requrl += urllib.urlencode({
            'stations': ','.join(stations),
            'from': start.strftime("%d.%m.%Y"),
            'to': end.strftime("%d.%m.%Y"),
            })
        resp = self.__getUrl(requrl)
        resp = resp.read()
        return resp



    def getChannelsDict(self):
        """
        wrapper for getChannelsDict
        """
        lst = self.getChannels()
        res = {}
        try:
            dct = self.__getXMLDict(lst)
            for element in dct['channel']['STATIONS']['ITEM']:
                res[element['TITLE']] = { 
                    'COUNTRY': element['COUNTRY'],
                    'LANGUAGE': element['LANGUAGE']
                    }
        except Exception, e:
            raise Exception(e)
        return res


    def getChannels(self):
        """
        get available channels
        """
        requrl = "%s/downloader/api/stations.php" % URL_OTR
        resp = self.__session = self.__getUrl(requrl)
        resp = resp.read()
        return resp

    def getRecordListDict(self, *args, **kwargs):
        """
        wrapper for getRecordList
        """
        lst = self.getRecordList(*args, **kwargs)
        try:
            return self.__getXMLDict(lst)
        except Exception, e:
            print str('tree="""%s"""\n' % lst)
            raise Exception(e)

    def getRecordList(self, 
            showonly="recordings",
            orderby="time",
            scheduled=True, 
            recording=True, 
            ready=True, 
            downloaded=True, 
            decoded=True, 
            paid=True, 
            bad=False, 
            pending=False, 
            expected=False, 
            unknownstation=False, 
            removed=False):
        """
        get recording list

        @param showonly: list type
        @type  showonly: string
        @param orderby: ordering method
        @type  orderby: string
        @param scheduled: show scheduled
        @type  scheduled: boolean
        @param recording: show recording
        @type  recording: boolean
        @param ready: show ready
        @type  ready: boolean
        @param downloaded: show downloaded
        @type  downloaded: boolean
        @param decoded: show decoded
        @type  decoded: boolean
        @param paid: show paid
        @type  paid: boolean
        @param bad: show bad
        @type  bad: boolean
        @param pending: show pending
        @type  pending: boolean
        @param expected: show expected
        @type  expected: boolean
        @param unknownstation: show unknownstation
        @type  unknownstation: boolean
        @param removed: show removed
        @type  removed: boolean
        """
        if not self.__subcode: self.getOtrSubcode()
        requrl = "%s/downloader/api/request_list2.php?" % URL_OTR
        requrl += self.__apiauth
        requrl += "&showonly=%s" % showonly
        requrl += "&orderby=%s" % orderby
        if not scheduled:   requrl += "&show_scheduled=false"
        if not recording:   requrl += "&show_recording=false"
        if not ready:       requrl += "&show_ready=false"
        if not downloaded:  requrl += "&show_downloaded=false"
        if not decoded:     requrl += "&show_decoded=false"
        if not paid:        requrl += "&show_paid=false"
        if not bad:         requrl += "&show_bad=false"
        if not pending:     requrl += "&show_pending=false"
        if not expected:    requrl += "&show_expected=false"
        if not removed:     requrl += "&show_removed=false"
        if not unknownstation: requrl += "&unknownstation=false"
        resp = self.__session = self.__getUrl(requrl)
        return resp.read()

    def getFileInfoDict(self, *args, **kwargs):
        """
        wrapper for getFileInfo
        """
        lst = self.getFileInfo(*args, **kwargs)
        try:
            return self.__getXMLDict( lst )
        except Exception, e:
            raise Exception(lst)

    def getFileInfo(self, epgid, fid=False, filename=False):
        """
        get file details

        @param fid: file id
        @type  fid: string
        @param epgid: epgid
        @type  epgid: string
        @param filename: filename
        @type  filename: string
        """
        if not self.__subcode: self.getOtrSubcode()
        requrl = "%s/downloader/api/request_file2.php?" % URL_OTR
        requrl += self.__apiauth
        requrl += "&epgid=%s" % base64.urlsafe_b64encode(epgid)
        if fid:
            requrl += "&id=%s" % base64.urlsafe_b64encode(fid)
        if filename:
            requrl += "&file=%s" % base64.urlsafe_b64encode(filename)
        resp = self.__session = self.__getUrl(requrl)
        return resp.read()


    def getFileDownload(self, fileuri):
        """
        get filedownloadlink or wait status

        @param fileuri: the downloaduri
        @type  fileuri: string
        """

        def getDownloadinfo(fileuri):
            apiuri  = fileuri.replace('/download/', '/api/', 1)
            try:
                resp = self.__session = self.__getUrl(apiuri)
            except socket.timeout:
                raise self.inDownloadqueueException('in downloadqueue', 0)
            ret = resp.read()
            downloadinfo = json.loads(ret)
            return downloadinfo

        downloadinfo = getDownloadinfo(fileuri)
        if ('reservation_filename' in downloadinfo and
            'reservation_cancellink' in downloadinfo):
            print "canceling existing reservation"
            self.__getUrl(downloadinfo['reservation_cancellink'])
            downloadinfo = getDownloadinfo(fileuri)

        if 'filedownloadlink' in downloadinfo:
            return downloadinfo['filedownloadlink']

        if 'queueposition' in downloadinfo:
            raise self.inDownloadqueueException('in downloadqueue', int(downloadinfo['queueposition']))

        if 'error' in downloadinfo:
            number = downloadinfo['error']
            message = ""
            if 'message' in downloadinfo:
                 message = downloadinfo['message']
            raise self.foundDownloadErrorException(number, message)

        print("download processing failed")
        print(downloadinfo)
        return False


    def getPastHighlightsDict(self, *args, **kwargs):
        """
        wrapper for getRss to get past highlights
        """
        url = "%s/rss/highlights_past.php" % URL_OTR
        lst = self.getRss(url, *args, **kwargs)
        try:
            return self.__getXMLDict( lst )
        except Exception, e:
            raise Exception(lst)

    def getRss(self, url):
        """
        get search list

        @param url: what to search for
        @type  url: string
        """
        resp = self.__session = self.__getUrl(url)
        return resp.read()

    def getSearchListDict(self, *args, **kwargs):
        """
        wrapper for getSearchList
        """
        lst = self.getSearchList(*args, **kwargs)
        try:
            return self.__getXMLDict( lst )
        except Exception, e:
            raise Exception(lst)


    def getSearchList(self, searchstring, future=False):
        """
        get search list

        @param searchstring: what to search for
        @type  searchstring: string
        @param future: get future recordings too
        @type  future: bool
        """
        requrl = "%s/index.php?&aktion=search&api=true" % URL_OTR
        requrl += "&future=%s" % ((future and "true") or "false")
        requrl += "&searchterm=%s" % urllib.quote(searchstring)
        resp = self.__session = self.__getUrl(requrl)
        return resp.read()

    def getUserInfoDict(self, *args, **kwargs):
        """
        wrapper for getUserInfo
        """
        lst = self.getUserInfo(*args, **kwargs)
        try:
            return self.__getXMLDict( lst )
        except Exception, e:
            raise Exception(lst)

    def getUserInfo(self):
        """
        get user info
        """
        if not self.__subcode: self.getOtrSubcode()
        requrl = "%s/downloader/api/userinfo.php?" % URL_OTR
        requrl += self.__apiauth
        requrl += "&email=%s" % base64.urlsafe_b64encode(self.__lastUsername)
        resp = self.__session = self.__getUrl(requrl)
        return resp.read()


    def setTimeout(self, timeout=90):
        return socket.setdefaulttimeout(timeout)

    def __init__(self, did=False, authcode=False, sockettimeout=90):
        """
        constructor

        @param did: did
        @type  did: int
        @param authcode: authcode
        @type  authcode: string
        @param sockettimeout: timeout for requests
        @type  sockettimeout: int
        """
        if sockettimeout:
            self.setTimeout(sockettimeout)
        self.setCookie()
        if did and authcode:
            self.__otr_did  = did
            self.__otr_auth = authcode
        else:
            self.__otr_auth = pah2Nahbae4cahzihach1aep.code()
            self.__otr_did  = 131



if __name__ == '__main__':

    from pprint import pprint

    otr = OtrHandler()
    otr.login('', '')
    recordlist = otr.getRecordListDict()
    if 'FILE' in recordlist:
        for f in recordlist['FILE']:
            pprint(f)
            fi = otr.getFileInfoDict(f['EPGID'], f['ID'], f['FILENAME'])
            pprint(fi)

