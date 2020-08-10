import urllib.request, urllib.parse, urllib.error
from .session import SipMsg


class Filter(object):

    def __init__(self):
        self.nextFilter = None

    def addFilter(self, filter):
        if self.nextFilter is None:
            self.nextFilter = filter
        else:
            self.nextFilter.addFilter(filter)

    def filterMessages(self, messages):
        return messages


class StatelessFilter(Filter):

    def __init__(self):
        Filter.__init__(self)

    def addFilter(self, filter):
        assert(isinstance(filter, StatelessFilter))
        Filter.addFilter(self, filter)

    def predicate(self, msg):
        return True

    def messageOk(self, msg):
        if self.predicate(msg):
            if self.nextFilter is None:
                return True
            else:
                return self.nextFilter.messageOk(msg)
        return False

    def filterMessages(self, messages):
        return [m for m in messages if self.messageOk(m)]


class ValidSip(StatelessFilter):
    def __init__(self):
        StatelessFilter.__init__(self)

    def predicate(self, msg):
        ret = True
        try:
            s = SipMsg(msg)
        except:
            ret = False
        return ret


class ContentFilter(StatelessFilter):

    def __init__(self):
        StatelessFilter.__init__(self)

    def predicate(self, msg):
        msgContent = urllib.parse.unquote(msg.msg)
        return msgContent.strip() != ""


class ProtocolFilter(StatelessFilter):

    def __init__(self, keep=["U"]):
        StatelessFilter.__init__(self)
        self.keep = keep

    def predicate(self, msg):
        return msg.proto in self.keep


class StatefulFilter(Filter):

    def __init__(self):
        Filter.__init__(self)

    def addFilter(self, filter):
        assert(isinstance(filter, StatefulFilter))
        Filter.addFilter(self, filter)

    def singlePassCheck(self, messages):
        return messages

    def filterMessages(self, messages):
        messages = self.singlePassCheck(messages)
        if self.nextFilter is not None:
            messages = self.nextFilter.filterMessages(messages)
        return messages


class PacketMerger(StatefulFilter):

    def __init__(self, step):
        StatefulFilter.__init__(self)
        self.step = step

    def singlePassCheck(self, messages):
#        if self.step <= 0:
        if self.step < 0:
            return messages
        src_dst_dic = {}
        # aux boolean dict with keys src_dst combination.
        # 0=no response from DST yet, 1=response from DST
        # for the last src_dst message.
        response = {}
        mergedMessages = []

        #### TEST unify port info ####
#        for msg in messages:
#            ip_src, port_src = msg.src.split(':')
#            if port_src != '80':
#                msg.src = ip_src + str(':1337')
#            ip_dst, port_dst = msg.dst.split(':')
#            if port_dst != '80':
#                msg.dst = ip_dst + str(':1337')
        ########

        for msg in messages:

            src_dst = msg.src + "_" + msg.dst
            dst_src = msg.dst + "_" + msg.src
            # check if there's an entry for this combination of SRC and DST
#            if src_dst_dic.has_key(src_dst):
            if src_dst in src_dst_dic:
                prevMessage = src_dst_dic[src_dst]
                if (response[src_dst] == 0 and
                        msg.ntime - prevMessage.ntime < self.step):
                    prevMessage.concat(msg)
                else:
                    mergedMessages.append(prevMessage)
                    src_dst_dic[src_dst] = msg
                    response[src_dst] = 0
            # if the combination SRC DST isn't read yet,
            # it is added and response is set to 0
            else:
                src_dst_dic[src_dst] = msg
                response[src_dst] = 0

            # check if there's an entry for the combination of DST to SRC
            # in order to set RESPONSE to 1 for this combination
#            if src_dst_dic.has_key(dst_src):
            if dst_src in src_dst_dic:
                response[dst_src] = 1
        for (k, msg) in src_dst_dic.items():
            if response[k] == 0:
                mergedMessages.append(msg)
        mergedMessages.sort(key=lambda m: m.ntime)
        return mergedMessages
