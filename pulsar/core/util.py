from gzip import GzipFile
import urllib.request, urllib.parse, urllib.error

WS = 0
TOK = 1

def scanNgrams(msg):
    if len(msg) == 0:
        scan = [(TOK, msg)]
    else:
        scan = [(TOK, m) for m in msg]
    return(scan)

def scanTokens(msg, whitespace):
    curVal = ""
    curType = None
    scan = []
    for m in msg:
        if m in whitespace:
            # we have whitespace
            if curType is None:
                curType = WS
                curVal = m
            elif curType is TOK:
                scan.append( (TOK, curVal) )
                curType = WS
                curVal = m
            else:
                curVal += m
        else:
            # we have a token
            if curType is None:
                curType = TOK
                curVal = m
            elif curType is WS:
                scan.append( (WS, curVal) )
                curType = TOK
                curVal = m
            else:
                curVal += m

    if curType is not None:
        if curType is TOK:
            scan.append( (TOK, curVal) )
        else:
            scan.append( (WS, curVal) )
    return scan


def readDerrick(path):
        g = GzipFile(path, "rb")
        messages = [] 
        for l in g:
            messages.append(urllib.parse.unquote(l.rstrip("\r\n").split(" ", 4)[-1]))
        g.close()
        return messages
