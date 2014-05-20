__author__ = 'fep'

import xbmc
import xbmcgui
import urllib2
import threading
import random
import string

from resources.lib.Translations import _
import Vfs as vfs


class Simplebmc:

    def Notification(self, title, text, duration=False, img=False):
        if not duration:
            duration = 8
        if not img:
            img = "False"
        duration = int(duration)*1000
        print "%s: %s" % (title, str(text))
        return xbmc.executebuiltin('show_notification("%s", "%s", %s, %s)' % (title, _(str(text)), duration, img))


    def humanSize(self, num):
        for x in ['bytes','KB','MB','GB','TB','PB','EB', 'ZB']:
            if 1024.0 > num > -1024.0:
                return "%3.1f%s" % (num, x)
            num /= 1024.0
        return "%3.1f%s" % (num, 'YB')


    class Background(threading.Thread):

        result = None
        exception = None
        debug = False

        function = None
        args = None
        kwargs = None

        def __call__(self, function_object, *args, **kwargs):

            if self.debug:
                print('threaded call %s %s %s' % (function_object, args, kwargs))

            self.function = function_object
            self.args = args
            self.kwargs = kwargs
            self.run()

        def run(self):
            try:
                self.result = self.function(*self.args, **self.kwargs)
            except Exception, e:
                self.exception = e



    class Downloader:

        size = 0
        progress = False
        temp_file_handler = None
        destination_file_path = None
        destination_file_name = None

        def randomFilename(self, size=10, chars=string.ascii_uppercase + string.digits):
            return ''.join(random.choice(chars) for x in range(size))

        def chunk_report(self, bytes_so_far, total_size):
            if total_size > 0:
                percent = float(bytes_so_far) / total_size
                percent = int(round(percent*100, 2))
                if self.progress:
                    self.progress.update(
                        percent,
                        self.destination_file_name,
                        '%s/%s' % (Simplebmc().humanSize(bytes_so_far), Simplebmc().humanSize(total_size))
                        )

        def chunk_read(self, response, chunk_size=1024*100, report_hook=None):

            if report_hook is None:
                report_hook = self.chunk_report

            total_size = response.info().getheader('Content-Length').strip()
            total_size = int(total_size)
            bytes_so_far = 0

            while True:
                chunk = response.read(chunk_size)
                bytes_so_far += len(chunk)

                if not chunk:
                    self.temp_file_handler.close()
                    break

                if self.progress:
                    if self.progress.iscanceled():
                        self.temp_file_handler.close()
                        vfs.delete(self.temp_file_path)
                        self.progress.close()

                if report_hook:
                    self.temp_file_handler.write( chunk )
                    report_hook(bytes_so_far, total_size)

            return bytes_so_far

        def __init__(self, url, dest, progress=True, background=False, local=False):
            if local:
                # workaround for some bugy frodo pre-versions
                self.destination_file_path = dest
                self.temp_file_path = vfs.path.join(xbmc.translatePath('special://temp'), self.randomFilename(size=10))
                self.temp_file_handler = open(self.temp_file_path, 'wb')
            else:
                self.destination_file_path = dest
                self.temp_file_path =  dest + '.' + self.randomFilename(3)
                self.temp_file_handler = vfs.File(self.temp_file_path, 'wb')

            self.destination_file_name = url.split('/').pop()

            if progress:
                self.progress = xbmcgui.DialogProgress()
                self.progress.create("Download", self.destination_file_name)

            request = urllib2.Request(url)
            request.add_header('User-Agent', 'XBMC/OtrHandler')

            def download(request):
                response = urllib2.urlopen(request)
                self.size = self.chunk_read(response)

                if progress:
                    self.progress = xbmcgui.DialogProgress()
                    self.progress.create("Move", self.destination_file_name)

                xbmc.log("move %s -> %s" % (self.temp_file_path, self.destination_file_path))
                vfs.rename(self.temp_file_path, self.destination_file_path)
                if vfs.exists(self.temp_file_path):
                    vfs.copy(self.temp_file_path, self.destination_file_path)
                    vfs.delete(self.temp_file_path)

                self.progress.close()

            if background is True:
                bg = Simplebmc().Background()
                bg(download, request)
            else:
                download(request)


    def noNull(self, s):
        #return re.sub('\0', '', s)
        #return s.rstrip('\x00')
        return s





