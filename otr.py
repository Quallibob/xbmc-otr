"""
    Document   : otr.py
    Package    : OTR Integration to XBMC
    Author     : Frank Epperlein
    Copyright  : 2012, Frank Epperlein, DE
    License    : Gnu General Public License 2
    Description: Main program script for package
"""

import xbmcplugin
import xbmcaddon

from call import call
import XbmcOtr as worker

def trace(
        e,
        lineformat= "{filename} " +
                    "+{line} " +
                    "({definer}): " +
                    "{code}",
        lastlineformat= "{filename} " +
                        "+{line} " +
                        "(" +
                        "{definer}, " +
                        "args={args}, " +
                        "kwargs={kwargs}, " +
                        "vargs={vargs}, " +
                        "locals={locals}" +
                        "): " +
                        "{code}"):
    import sys
    import inspect

    def getLine(filename, line):
        try:
            fh = open(filename, 'r')
            for _ in range(line-1):
                fh.next()
            return fh.next().strip()
        except Exception, e:
            pass

    type, value, traceback = sys.exc_info()
    ret = {
            'type': type,
            'value': value,
            'message': str(e),
            'class': e.__class__.__name__,
            'lines': []
          }

    while traceback:
        co = traceback.tb_frame.f_code
        (args, varargs, keywords, locals) = inspect.getargvalues(traceback.tb_frame)
        try:
            nwlocals = {}
            for _ in locals:
                if locals[_] != ret['value']:
                    nwlocals[_] = locals[_]
            locals = nwlocals
        except Exception:
            pass
        next = {
            'code'      : getLine(co.co_filename, traceback.tb_lineno),
            'definer'   : traceback.tb_frame.f_code.co_name,
            'filename'  : str(co.co_filename),
            'line'      : str(traceback.tb_lineno),
            'args'      : args,
            'vargs'     : varargs,
            'kwargs'    : keywords,
            'locals'    : locals
            }
        next['formated'] = lineformat.format(**next)
        ret['lines'].append(next)
        traceback = traceback.tb_next
    ret['lastcall'] = ret['lines'].pop()
    ret['lastcall']['lastlineformated'] = lastlineformat.format(**ret['lastcall'])
    ret['lines'].append(ret['lastcall'])
    return ret


class NoException(Exception): pass

try:
    housekeeper = worker.housekeeper()
    creator = worker.creator(login=housekeeper.loginIfRequired)
    creator.eval(housekeeper.getOTR())
    creator.send()
    housekeeper.end()

except NoException, e:
    xbmc.log("#### BEGIN OTR-XBMC EXCEPTION ####", xbmc.LOGERROR)
    to = trace(e)
    xbmc.log("%s(%s)" % (to['class'], to['message']), xbmc.LOGERROR)
    for line in to['lines']:
        xbmc.log("   %s" % line['formated'], xbmc.LOGERROR)
    xbmc.log("        args:    {args}".format(**to['lastcall']), xbmc.LOGERROR)
    xbmc.log("        kwargs:  {kwargs}".format(**to['lastcall']), xbmc.LOGERROR)
    xbmc.log("        vargs:   {vargs}".format(**to['lastcall']), xbmc.LOGERROR)
    xbmc.log("        locals:  {locals}".format(**to['lastcall']), xbmc.LOGERROR)
    xbmc.log("#### END OTR-XBMC EXCEPTION ####", xbmc.LOGERROR)
    
