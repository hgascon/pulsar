from gzip import GzipFile


class DerrickPacket:

    def __init__(self, line):
        (self.ntime, self.proto, self.src, self.dst, self.msg) = line.split(b" ", 4)
        self.ntime = float(self.ntime)

    def __str__(self):
        return " ".join([str(self.ntime), str(self.proto), str(self.src), str(self.dst), str(self.msg)])

    def concat(self, newPacket):
        assert(self.src == newPacket.src and
               self.dst == newPacket.dst)
#               self.proto == newPacket.proto and
#               self.ntime <= newPacket.ntime
        self.ntime = newPacket.ntime
        self.msg += newPacket.msg


class DerrickReader:

    def __init__(self, derrickFile):
        self.derrickFile = derrickFile
        g = GzipFile(derrickFile, "rb")
        self.messages = [DerrickPacket(l.rstrip(b"\r\n")) for l in g]
        g.close()


class DerrickWriter:

    def __init__(self, derrickFile):
        self.derrickFile = derrickFile

    def writePackets(self, messages):
        g = GzipFile(self.derrickFile, "wb")
        for m in messages:
            g.write(("%s\n" % str(m)).encode())
        g.close()
