__author__ = 'fep'

import sys
import re
import urllib

try:
    from urlparse import parse_qs
except ImportError:
    #noinspection PyDeprecation
    from cgi import parse_qs


class Call:

    url, query, scheme, location, path, fragment = ["", "", "", "", "", ""]
    params = {}

    def __init__(self, url, query, fragment):
        self.url        = url
        self.query      = query

        if len(fragment):
            self.fragment   = int(fragment)
        else:
            self.fragment   = 0

        self.params = parse_qs(self.query.lstrip('?'))
        for element in self.params:
            if len(self.params[element]) == 1:
                self.params[element] = self.params[element].pop()


        m = re.match(r'([^/]*)://([^/]*)/(.*)', self.url)
        self.scheme, self.location, self.path = [m.group(1), m.group(2), m.group(3)]
        self.path = "/%s" % self.path.strip('/')

    def format(self, path=False, params=False, update=False):
        if not isinstance(params, dict):
            params = dict()
        else:
            if update:
                combine = self.params.copy()
                combine.update(params)
                params = combine
        if not isinstance(path, str):
            path = self.path
        if not path.startswith('/'):
            path = "/".join([self.path, path])

        result = "%s://%s%s" % (
            self.scheme,
            self.location,
            path )

        if len(params):
            to_append = list()
            for params_key in params:
                to_append.append(urllib.urlencode( {params_key: params[params_key]} ))
            result += "?%s" % "&".join(to_append)

        #print(result)
        return result


    def __str__(self):
        return str( {
            'scheme':   self.scheme,
            'location': self.location,
            'path':     self.path,
            'query':    self.params })



call = Call(sys.argv[0], sys.argv[2], sys.argv[1])
print(str(call))