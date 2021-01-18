import urllib.request, urllib.parse, urllib.error
import random
from .sippy.SipRequest import SipRequest
from .sippy.SipResponse import SipResponse
from operator import itemgetter

class SessionInfo:

    def __init__(self, sessionId, msgNumber, role, msgType):
        self.sessionId = sessionId
        self.msgNumber = msgNumber
        self.role = role
        self.msgType = msgType

    def __str__(self):
        return "\t".join([self.sessionId, str(self.msgNumber), self.role, self.msgType])

class SessionHandler:

    def __init__(self, messages):
        self.session = [None] * len(messages)
        self.sessionIds = set()
        self.gatherSessionInformation(messages)

    def addSessionInformation(self, sinfo, index):
        self.session[index] = sinfo
        self.sessionIds.add(sinfo.sessionId)

    def getNumberOfSessions(self):
        return len(self.sessionIds)

    def splitBySession(self, ratio):
        N = self.getNumberOfSessions()
        test = set(random.sample(self.sessionIds, int(N * (1 - ratio))))
        isTest = [(s.sessionId in test) for s in self.session]
        return isTest

    def gatherSessionInformation(self, messages):
        pass

    def writeSessionInformation(self, path, what=None):
        f = open(path, "w")
        f.write("%s\n" % "\t".join(["dialogId", "msgNumber", "origin", "type"]))
        if what is None:
            for s in self.session:
                f.write("%s\n" % str(s))
        else:
            for (writeIt, s) in zip(what, self.session):
                if writeIt:
                    f.write("%s\n" % str(s))
        f.close()

class UniversalSessionHandler(SessionHandler):

    def __init__(self, messages, step):
        self.step = step
        SessionHandler.__init__(self, messages)

    def gatherSessionInformation(self, messages):
        dialogId_dic = {}
        dialogId_len_dic = {}
        dialogId_timestamp_dic = {}   #keys: dialogID, values: last appearing timestamp
        dialogId = 0
        for (index, msg) in enumerate(messages):
            src_dst = msg.src + "_" + msg.dst
            dst_src = msg.dst + "_" + msg.src
            msgType = msg.msg.split(None, 1)
            if len(msgType) > 0:
                msgType = msgType[0]
            else:
                msgType = "NONE"

            if src_dst in dialogId_dic and \
                   msg.ntime - dialogId_timestamp_dic[dialogId_dic[src_dst]] < self.step:
                dId = dialogId_dic[src_dst]
                dialogId_len_dic[dId] += 1
                self.addSessionInformation(SessionInfo(str(dId), dialogId_len_dic[dId],
                                                  "UAC", msgType), index)
                dialogId_timestamp_dic[dId] = msg.ntime
                continue

            if dst_src in dialogId_dic:
                dId = dialogId_dic[dst_src]     
                dialogId_len_dic[dId] += 1
                self.addSessionInformation(SessionInfo(str(dId), dialogId_len_dic[dId],
                                                       "UAS", msgType), index)
                dialogId_timestamp_dic[dId] = msg.ntime
                continue

            else:            
                dialogId_dic[src_dst] = dialogId
                dialogId_len_dic[dialogId] = 0
                self.addSessionInformation(SessionInfo(str(dialogId), dialogId_len_dic[dialogId],
                                                       "UAC", msgType), index)
                dialogId_timestamp_dic[dialogId] = msg.ntime
                dialogId += 1

class SipSessionHandler(SessionHandler):

    def gatherSessionInformation(self, messages):
        dialogs = {}
        allDialogs = []
        # gather dialogs based on the from-tag and callId
        for (i, dm) in enumerate(messages):
            m = SipMsg(dm)
            (cid, fromTag) = m.getCallIdAndFromTag()
            d = "%s | %s" % (cid, fromTag)
            dialogs.setdefault(d, SipDialog(cid)).addMessage(m, i)
        # now merge the two sides of a communication, if they exist:
        for k in list(dialogs.keys()):
            if k in dialogs:
                d = dialogs[k]
                toTag = d.getToTag()
                if toTag is not None:
                    # there might be an other side...
                    otherSide = "%s | %s" % (d.getCallId(), toTag)
                    if otherSide in dialogs:
                        d.mergeDialogs(dialogs[otherSide])
                        del dialogs[otherSide]
                d.orderMessages()
                d.determineType()
                allDialogs.append(d)
                del dialogs[k]
        # reorder the stuff
        messageTuples = [d.getMessageTuples() for d in allDialogs]
        allTuples = [oneTuple for sublist in messageTuples for oneTuple in sublist]
        allTuples.sort(key=itemgetter(4))
        for (index, tup) in enumerate(allTuples):
            (sessionId, msgNumber, role, msgType, _) = tup
            self.addSessionInformation(SessionInfo(sessionId, msgNumber, role, msgType), index)

def splitNet(netAddr):
    res = netAddr.split(":")
    if len(res) > 1:
        res[1] = int(res[1])
    return (res[0], res[1])

class SipMsg:
    def __init__(self, derrickMsg):
        self.ntime = derrickMsg.ntime
        self.proto = derrickMsg.proto
        msg = urllib.parse.unquote(derrickMsg.msg)
        self.msg = None
        if len(msg) > 3:
            if msg[0:3] == "SIP":
                self.msg = SipResponse(msg)
                self.isRequest = False
            else:
                self.msg = SipRequest(msg)
                self.isRequest = True
        (self.srcIp, self.srcPort) = splitNet(derrickMsg.src)
        (self.dstIp, self.dstPort) = splitNet(derrickMsg.dst)
        self.__getMetaData()

    def __getMetaData(self):
        (self.callId, self.fromTag, self.cseq, self.cseqMethod) = self.msg.getTId(True)
        theTo = self.msg.getHFBodys("to")[0]
        self.toTag = None
        if theTo.getTag() is not None:
            self.toTag = str(theTo.getTag())
        
    def getCallIdAndFromTag(self):
        return (self.callId, self.fromTag)

    def isEstablished(self):
        return self.toTag is not None

    def isRegister(self):
        return self.isRequest and self.msg.method == "REGISTER"

    def isInvite(self):
        return self.isRequest and self.msg.method == "INVITE"

    def isOptions(self):
        return self.isRequest and self.msg.method == "OPTIONS"

    def getOrigin(self, relativeToUAC):
        ret = "UNKNOWN"
        if self.isRequest:
            if self.fromTag == relativeToUAC:
                ret = "UAC"
            elif self.toTag == relativeToUAC:
                ret = "UAS"
        else:
            if self.fromTag == relativeToUAC:
                ret = "UAS"
            elif self.toTag == relativeToUAC:
                ret = "UAC"
        return ret
    
    def getType(self):
        if self.isRequest:
            return "REQUEST"
        else:
            return "RESPONSE"
            
class SipDialog:

    def __init__(self, callId):
        self.callId = callId
        self.messages = []

    def mergeDialogs(self, dialog):
        self.messages.extend(dialog.messages)

    def getDiagId(self):
        return "%s | %s | %s" % (self.getFromTag(), self.getCallId(), self.getToTag())

    def getCallId(self):
        return self.callId

    def getFromTag(self):
        return self.messages[0][0].fromTag

    def getToTag(self):
        toTags = set([m.toTag for (m, i) in self.messages])
        toTags.discard(None)
        if len(toTags) == 0:
            return None
        elif len(toTags) == 1:
            return toTags.pop()
        elif len(toTags) == 2:
            toTags.discard(self.getFromTag())
            return toTags.pop()
        else:
            toTags.discard(self.getFromTag())
            if self.messages[0][0].msg.method == "INVITE":
                assert(len(toTags) == 2)
                # use the freshest to-tag for this INVITE with
                # multiple to tags, since some clients drop the assigned
                # to-tag if they have to authorize themselfes
                return [m[0].toTag for m in sorted(self.messages, key=lambda m: m[0].ntime, reverse=True) if m[0].toTag in toTags][0]
            if self.messages[0][0].msg.method not in ["REGISTER", "OPTIONS", "INVITE"]:
                sys.stderr.write("Warning: Unreasonable number of to-tags in non-REGISTER/OPTIONS/INVITE dialog:\n%s\n" % "\n".join([str(m.msg) for (m, i) in self.messages]))
            return None

    def orderMessages(self):
        self.messages.sort(key=lambda m: m[0].ntime)

    def determineType(self):
        assert(len(self.messages) > 0)
        fm  = self.messages[0][0]
        self.type = "UNKNOWN"
        self.uac = None
        self.msgAnnotation = [None] * len(self.messages)
        if fm.isRequest:
            self.type = fm.msg.method
            self.uac = fm.fromTag
            for (i, m) in enumerate(self.messages):
                self.msgAnnotation[i] = (m[0].getOrigin(self.uac), m[0].getType())
        else:
            assert(len(self.messages) == 1)
            self.uac = fm.fromTag
            self.msgAnnotation[0] = (self.uac, self.type)

    def getMessageTuples(self):
        N = len(self.messages)
        ret = [None] * N
        def tupelizer(index):
            return (self.getDiagId(), index,
                    self.msgAnnotation[index][0],
                    self.msgAnnotation[index][1],
                    self.messages[index][1])
        return([tupelizer(i) for i in range(N)])
    
    def addMessage(self, msg, lineNumber):
        self.messages.append( (msg, lineNumber) )

    def isRejected(self):
        return not self.isEstablishedConnection() and not self.isRegisterOnly()
        
    def isEstablishedConnection(self):
        return any([m.isEstablished() for (m, i) in self.messages]) and not self.isRegisterOnly()

    def isRegisterOnly(self):
        return any([m.isRegister() for (m, i) in self.messages]) and not \
               any([m.isInvite() for (m, i) in self.messages])

    def getCleartextMessages(self):
        return [str(m.msg)[0:200] for (m, i) in self.messages]
