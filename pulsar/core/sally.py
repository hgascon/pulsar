# -*- coding: latin-1 -*-
import urllib.request, urllib.parse, urllib.error
from zipfile import ZipFile


def sallyQuote(msg):
    def quoter(char):
        ichar = ord(char)
        if ichar > 31 and ichar < 127 and char not in ["%", ":", ",", ' ']:
            return char
        else:
            return "%{:02x}".format(ichar)
    q = [quoter(c) for c in msg]
    return "".join(q)


# mainly for quoting %00 bytes in the string
def presallyQuote(msg):
    def quoter(char):
        ichar = ord(char)
        if ichar != 0 and char != "§":
            return char
        else:
            return "§{:02x}".format(ichar)
    q = [quoter(c) for c in msg]
    return "".join(q)


def ngramSplit(msg, ngramSize):
    n = len(msg)
    return [msg[ind:(ind+ngramSize)] for ind in range(n - ngramSize + 1)]


def rawWrite(messages, path, ngramSize):
    if ngramSize == 0:
        return rawWriteText(messages, path)
    else:
        return rawWriteBin(messages, path, ngramSize)


def rawWriteBin(messages, path, ngramSize):
    rawFileName = "%s.zipraw" % path
    rawFile = ZipFile(rawFileName, "w")
    rawQuotedFile = file("%s.rawquoted" % path, "w")
    for (ind, m) in enumerate(messages):
        raw = urllib.parse.unquote(m.msg)
        # write the complete stuff into one file
        rawFile.writestr("%09d" % ind, raw)
        tokens = ngramSplit(raw, ngramSize)
        # ... before writing out the tokens as sally will quote them
        tokensQuoted = [sallyQuote(t) for t in tokens]
        rawQuotedFile.write("%s\n" % " ".join(tokensQuoted))
    rawFile.close()
    return rawFileName


# splits the message by whitespaces and writes them out in one line seperated by space
def rawWriteText(messages, path):
    rawFileName = "%s.raw" % path
    rawFile = open(rawFileName, "w")
    rawQuotedFile = open("%s.rawquoted" % path, "w")
    for m in messages:
        raw = urllib.parse.unquote(m.msg)
        # we split the message by standard whitespace characters
        # an quote %00 bytes...
        tokens = [presallyQuote(t) for t in raw.split()]
        # ... before writing out the tokens as sally will quote them
        tokensQuoted = [sallyQuote(t) for t in tokens]
        rawFile.write("%s\n" % " ".join(tokens))
        rawQuotedFile.write("%s\n" % " ".join(tokensQuoted))
    rawQuotedFile.close()
    rawFile.close()
    return rawFileName


def fsallyPreprocessing(sallyFile, fsallyFile):
    sallyIn = open(sallyFile)
    sallyOut = open(fsallyFile, "w")
    sallyIn.readline()
    allNgrams = {}
    count = 0
    for l in sallyIn:
        count += 1
        info = l.split(" ")
        if info[0] == "":
            curNgrams = []
        else:
            curNgrams = [ngramInfo.split(":")[1] for ngramInfo in info[0].split(",")]
            allNgrams.update(allNgrams.fromkeys(curNgrams))
        sallyOut.write("%s\n" % " ".join(curNgrams))
    sallyOut.write("%s\n" % " ".join(list(allNgrams.keys())))
    sallyOut.close()
    sallyIn.close()
