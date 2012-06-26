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

import urllib2
import hashlib
import os
import XmlDict
import base64
import socket
from xml.etree import ElementTree


URL_OTR="http://www.onlinetvrecorder.com"
URL_SUBCODE="http://j.mp/otrsubcode"
VERSION="0.2"
VERSION_CHECK="http://j.mp/otrhandler-version-check"

class OtrHandler:
    """
    OTR Representation
    """
    
    __session = False
    __apiauth = ""
    __url_cookie   = None
    __url_request  = None
    __url_urlopen  = None

    def __loadCookies(self):
        """
        get cookie handler
        """
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
        """
        parse xml into dict

        @param xml: xml data
        @type  xml: string
        """
        tree = ElementTree.XML(xml)
        return XmlDict.XmlDict(tree)

    def __getUrl(self, url):
        """
        query url

        @param url: url to request
        @type  url: string
        """
        req = self.__url_request(url)
        req.add_header('User-Agent', 'XBMC OtrHandler')
        resp = self.__url_urlopen(req)
        return resp

    def newVersionAvailable(self):
        """
        check for new version
        """
        try:
            master = self.__getUrl(VERSION_CHECK).read()
            if float(master) > float(VERSION):
                return True
        except Exception, e:
            pass
        return False



    def setAPIAuthKey(self, did=131, code="%s"):
        """
        set internal api access code

        @param did: programm code
        @type  did: int
        @param code: access code
        @type  code: string
        """
        subcode = self.__getUrl(URL_SUBCODE).read()
        checksum = hashlib.md5(code % subcode).hexdigest()
        self.__apiauth = "&checksum=%s&did=%s" % (checksum, did)


    def login(self, email, password):
        """
        login to otr

        @param email: email address or username
        @type  email: string
        @param password: user password
        @type  password: string
        """
        requrl = "%s/downloader/api/login.php?" % URL_OTR
        requrl += self.__apiauth
        requrl += "&email=%s&pass=%s" % (email, password)
        resp = self.__session = self.__getUrl(requrl)
        resp = resp.read()
        if len(resp) and ' ' in resp:
            raise Exception(resp)

    def deleteJob(self, email, epgid):
        """
        delete recording

        @param email: email address or username
        @type  email: string
        @param epgid: epgid
        @type  epgid: string
        """
        requrl = "%s/index.php?aktion=deleteJob" % URL_OTR
        requrl += "&email=%s&epgid=%s" % ( base64.urlsafe_b64encode(email), base64.urlsafe_b64encode(epgid) )
        resp = self.__session = self.__getUrl(requrl)
        resp = resp.read()
        return resp

    def getRecordListDict(self, *args, **kwargs):
        """
        wrapper for getRecordList
        """
        lst = self.getRecordList(*args, **kwargs)
        try:
            return self.__getXMLDict( lst )
        except Exception, e:
            raise Exception(lst)
        
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

    def getFileInfo(self, fid, epgid, filename):
        """
        get file details

        @param fid: file id
        @type  fid: string
        @param epgid: epgid
        @type  epgid: string
        @param filename: filename
        @type  filename: string
        """
        requrl = "%s/downloader/api/request_file2.php?" % URL_OTR
        requrl += self.__apiauth
        requrl += "&id=%s" % base64.urlsafe_b64encode(fid)
        requrl += "&epgid=%s" % base64.urlsafe_b64encode(epgid)
        requrl += "&file=%s" % base64.urlsafe_b64encode(filename)
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

    def getUserInfo(self, email):
        """
        get user info

        @param email: email address or username
        @type  email: string
        """
        requrl = "%s/downloader/api/userinfo.php?" % URL_OTR
        requrl += self.__apiauth
        requrl += "&email=%s" % base64.urlsafe_b64encode(email)
        resp = self.__session = self.__getUrl(requrl)
        return resp.read()


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
            pprint(f)
            fi = otr.getFileInfoDict(f['ID'], f['EPGID'], f['FILENAME'])
            pprint(fi)

