#!/usr/bin/python
# vim: tabstop=4 shiftwidth=4 smarttab expandtab softtabstop=4 autoindent

import urllib2
import hashlib
import os
import XmlDict
import base64
import socket
from xml.etree import ElementTree


URL_OTR="http://www.onlinetvrecorder.com"
URL_SUBCODE="%s/downloader/api/getcode.php" % URL_OTR


class OtrHandler:
    
    __session = False
    __apiauth = ""
    __url_cookie   = None
    __url_request  = None
    __url_urlopen  = None

    def __loadCookies(self):
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
                self.__url_cookie = ClientCookie.LWPCookieJar()
                opener = ClientCookie.build_opener(ClientCookie.HTTPCookieProcessor(self.__url_cookie))
                ClientCookie.install_opener(opener)
                self.__url_request = Request
                self.__url_urlopen = urlopen
        else:
            urlopen = urllib2.urlopen
            Request = urllib2.Request
            self.__url_cookie = cookielib.LWPCookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.__url_cookie))
            urllib2.install_opener(opener)
            self.__url_request = Request
            self.__url_urlopen = urlopen

    def __getXMLDict(self, xml):
        tree = ElementTree.XML(xml)
        return XmlDict.XmlDict(tree)

    def __getUrl(self, url):
        req = self.__url_request(url)
        resp = self.__url_urlopen(req)
        return resp

    def setAPIAuthKey(self, did=131, code="%s"):
        subcode = self.__getUrl(URL_SUBCODE).read()
        checksum = hashlib.md5(code % subcode).hexdigest()
        self.__apiauth = "&checksum=%s&did=%s" % (checksum, did)


    def login(self, email, password):
        requrl = "%s/downloader/api/login.php?" % URL_OTR
        requrl += self.__apiauth
        requrl += "&email=%s&pass=%s" % (email, password)
        resp = self.__session = self.__getUrl(requrl)
        resp = resp.read()
        if len(resp):
            raise Exception(resp)

    def getRecordListDict(self, *args, **kwargs):
        return self.__getXMLDict( self.getRecordList(*args, **kwargs) )
        
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
        return self.__getXMLDict( self.getFileInfo(*args, **kwargs) )

    def getFileInfo(self, fid, epgid, filename):
        requrl = "%s/downloader/api/request_file2.php?" % URL_OTR
        requrl += self.__apiauth
        requrl += "&id=%s" % base64.urlsafe_b64encode(fid)
        requrl += "&epgid=%s" % base64.urlsafe_b64encode(epgid)
        requrl += "&file=%s" % base64.urlsafe_b64encode(filename)
        resp = self.__session = self.__getUrl(requrl)
        return resp.read()


    def __init__(self, did=False, authcode=False, sockettimeout=90):
        if sockettimeout:
            socket.setdefaulttimeout(sockettimeout)
        self.__loadCookies()
        if did and authcode:
            self.setAPIAuthKey(did, authcode)
        else:
            import pah2Nahbae4cahzihach1aep
            self.setAPIAuthKey(code=pah2Nahbae4cahzihach1aep.code())



if __name__ == '__main__':

    from pprint import pprint

    otr = OtrHandler()
    otr.login('', '')
    recordlist = otr.getRecordListDict()
    if 'FILE' in recordlist:
        for f in recordlist['FILE']:
            print "########################################"
            pprint(f)
            fi = otr.getFileInfoDict(f['ID'], f['EPGID'], f['FILENAME'])
            pprint(fi)

