__author__ = 'fep'

import xbmcaddon

def _(s):
    """
    Versucht einen nicht-lokalisierten String zu uebersetzen.

    @param s: unlokalisierter String
    @type  s: string
    """
    translations = {
        'missing login credentials': 30300,
        'login failed': 30301,
        'loading recording list': 30302,
        'recordings': 30303,
        'archive': 30304,
        'delete': 30305,
        'play': 30306,
        'refresh listing': 30307,
        'userinfo': 30308,
        'status: %s (until %s)': 30309,
        'decodings left: %s, gwp left: %s': 30310,
        'loading recording list failed': 30311,
        'new version available': 30312,
        'search': 30313,
        'scheduling': 30314,
        'searchpast': 30315,
        'searchfuture': 30316,
        'schedule job?': 30317,
        'scheduleJob: OK': 30318,
        'scheduleJob: DOUBLE': 30319,
        'pasthighlights': 30320,
        'downloadqueue': 30321,
        'queueposition %s of %s': 30322,
        'refresh in %s sec': 30323,
        'delete job?': 30324,
        'job deleted': 30325,
        'refresh element': 30326,
        'stream select': 30327,
        'URLError(timeout(\'timed out\',),)': 30328,
        'Monday': 30329,
        'Tuesday': 30330,
        'Wednesday': 30331,
        'Thursday': 30332,
        'Friday': 30333,
        'Saturday': 30334,
        'Sunday': 30335,
        'January': 30336,
        'February': 30337,
        'March': 30338,
        'April': 30339,
        'May': 30340,
        'June': 30341,
        'July': 30342,
        'August': 30343,
        'September': 30344,
        'October': 30345,
        'November': 30346,
        'December': 30347,
        '%s weeks': 30348,
        '%s week': 30349,
        'tvguide': 30350,
        'show all channels': 30351,
        'hide channel (%s)': 30352,
        'unhide channel (%s)': 30353,
        'hide language (%s)': 30354,
        'unhide language (%s)': 30355,
        'day before': 30356,
        'day after': 30357,
        'download': 30358,
        'download select': 30359,
        'download canceled': 30360,
        'local copy': 30361,
        'delete local copys': 30362,
        'file already exists, overwrite?': 30363,
        'download completed, play file now?': 30364,
        'do you want do delete existing local copys?': 30365,
        'skipped file (Operation not permitted)': 30366,
        'skipped file (No such file or directory)': 30367,
        }
    if s in translations:
        return xbmcaddon.Addon().getLocalizedString(translations[s]) or s
    print("untranslated: %s" % s)
    return s