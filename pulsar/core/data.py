import operator
import csv
import os
import sys

from .util import scanNgrams, scanTokens, readDerrick

csv.field_size_limit(sys.maxsize)
START_STATE = "START"
END_STATE = "END"


class DataHandler:

    def __init__(self, datapath, ngram, whitespace):
        self.datapath = datapath
        self.ngram = ngram
        self.whitespace = whitespace
        self._readDerrick()
        self._readHarry()
        self._readClusterAssignments()

    def getCluster(self, index):
        return self.clusterAssignments[index]

    def getNCluster(self):
        return self.Ncluster

    def getN(self):
        return self.N

    def _readClusterAssignments(self):
        path = "%s.cluster" % self.datapath
        if not os.path.exists(path):
            print("Error during clustering (not enough data?)")
            print("Cluster file not generated:", path)
            print("Exiting learning module...")
            sys.exit(1)

        def clusterProcessor(clusterRow):
            return clusterRow[0]
        self.clusterAssignments = self._processData(path, clusterProcessor,
                                                    self.N, skipFirstLine=False)
        assert(len(self.clusterAssignments) == self.N)
        self.Ncluster = len(set(self.clusterAssignments))

    def _readHarry(self):
        path = "%s.harry" % self.datapath

        def harryProcessor(harryRow):
            return [harryRow[0], int(harryRow[1]), harryRow[2]]
        self.harry = self._processData(path, harryProcessor,
                                       self.N, skipFirstLine=True)
        self.comms = {}

        for i, h in enumerate(self.harry):
            self.comms.setdefault(h[0], []).append((i, h[1], h[2]))
        for oneComm in list(self.comms.values()):
            oneComm.sort(key=operator.itemgetter(1))

    def getCommunicationIds(self):
        return list(self.comms.keys())

    def getMsgIndexForComm(self, commId):
        return [c[0] for c in self.comms[commId]]

    def getMsgDirForComm(self, commId):
        return [c[2] for c in self.comms[commId]]

    def getMsgClustForComm(self, commId):
        return [self.getCluster(c[0]) for c in self.comms[commId]]

    def getStateIdsForComm(self, commId, padding):
        if padding <= 0:
            # we want at least one start/end marker
            padding = 1
        ret = [START_STATE] * padding
        ret.extend(["%s.%s" % tup
                    for tup in zip(self.getMsgClustForComm(commId),
                                   self.getMsgDirForComm(commId))])
        ret.append(END_STATE)
        return ret

    def getTokensForMsg(self, msgIndex):
        if self.ngram == 0:
            return scanTokens(self.messages[msgIndex], self.whitespace)
        else:
            return scanNgrams(self.messages[msgIndex])

    def _processData(self, fname, process, init, skipFirstLine=False):
        f = open(fname, "r")
        data = csv.reader(f, delimiter="\t", quotechar=None, escapechar=None)
        if init is None:
            res = []
        else:
            res = [None] * init
        indexShift = 0
        for i, r in enumerate(data):
            if skipFirstLine:
                skipFirstLine = False
                indexShift = 1
                continue
            if init is None:
                res.append(process(r))
            else:
                res[i-indexShift] = process(r)
        f.close()
        return res

    def _readDerrick(self, ):
        path = "%s.fdrk" % self.datapath
        self.messages = readDerrick(path)
        self.N = len(self.messages)
