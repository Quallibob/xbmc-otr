import xbmc
import xbmcvfs
import os

ALLOW_FRODO=False


try:
    import json
except ImportError:
    #noinspection PyUnresolvedReferences
    import simplejson as json

class PythonFile:

    __fo = None

    def __init__(self, path, mode='r', unknown=False):

        if isinstance(mode, list):
            mode = list[0]

        self.__fo = open(path, mode)

    def close(self):
        return self.__fo.close()

    def read(self, size=False):
        if size:
            return self.__fo.read(size)
        else:
            return self.__fo.read()

    def seek(self, position):
        return self.__fo.seek(position)

    def size(self):
        return 0

    def write(self, buffer):
        return self.__fo.write(buffer)


def listdir(path):

    if 'listdir' in dir(xbmcvfs) and ALLOW_FRODO:
        return xbmcvfs.listdir(path)

    else:
        file_list = []
        dir_list = []
        json_response = xbmc.executeJSONRPC("""
            { "jsonrpc" : "2.0" ,
              "method"  : "Files.GetDirectory" ,
              "params"  : { "directory" : "%s" , "sort" : { "method" : "file" } } ,
              "id"      : 1 }
            """ % path.encode('utf-8').replace('\\', '\\\\'))
        json_object = json.loads(json_response)

        if 'result' in json_object:
            if json_object['result']['files']:
                for item in json_object['result']['files']:
                    if item['file'].endswith('/') or item['file'].endswith('\\'):
                        dir_list.append(os.path.basename(item['file'].rstrip('/').rstrip('\\')))
                    else:
                        file_list.append(os.path.basename(item['file']))
        return (dir_list, file_list)


def copy(source, destination):
    return xbmcvfs.copy(source, destination)


def delete(path):
    return xbmcvfs.delete(path)


def exists(path):
    return xbmcvfs.exists(path)


def mkdir(path):
    return xbmcvfs.mkdir(path)


def rename(source, target):
    return xbmcvfs.rename(source, target)


def rmdir(path):
    return xbmcvfs.rmdir(path)


File = None
if 'File' in dir(xbmcvfs) and ALLOW_FRODO:
    File = xbmcvfs.File
else:
    File = PythonFile
print File



class Path:

    def join(self, *args):
        return os.path.join(*args)

path = Path()