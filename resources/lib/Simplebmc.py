__author__ = 'fep'

import xbmc
import xbmcgui
import urllib2
import threading
from resources.lib.Translations import _


class Simplebmc:

    def Notification(self, title, text, duration=False, img=False):
        if not duration:
            duration = 8
        if not img:
            img = "False"
        duration = int(duration)*1000
        print "%s: %s" % (title, str(text))
        return xbmc.executebuiltin('Notification("%s", "%s", %s, %s)' % (title, _(str(text)), duration, img))


    def humanSize(self, num):
        for x in ['bytes','KB','MB','GB','TB','PB','EB', 'ZB']:
            if num < 1024.0 and num > -1024.0:
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
        destination_file_handler = None
        destination_file_path = None
        destination_file_name = None

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
                    self.destination_file_handler.close()
                    break

                if self.progress:
                    if self.progress.iscanceled():
                        self.destination_file_handler.close()
                        os.remove(self.destination_file_path)
                        self.progress.close()

                if report_hook:
                    self.destination_file_handler.write(chunk)
                    report_hook(bytes_so_far, total_size)

            return bytes_so_far

        def __init__(self, url, dest, progress=True, background=False):

            self.destination_file_handler = open(dest, 'wb')
            self.destination_file_path = dest
            self.destination_file_name = url.split('/').pop()

            if progress:
                self.progress = xbmcgui.DialogProgress()
                self.progress.create("Download", self.destination_file_name)

            request = urllib2.Request(url)
            request.add_header('User-Agent', 'XBMC/OtrHandler')

            def download(request):
                response = urllib2.urlopen()
                self.size = self.chunk_read(response)

            if background:
                bg = Simplebmc().Background()
                bg(download, request)
            else:
                download(request)



