#!/usr/bin/python

import time
import os.path
import os
import ConfigParser

from ast import literal_eval

from pulsar.core import sally
from pulsar.core.derrick import DerrickReader, DerrickWriter
from pulsar.core.filter import PacketMerger, ProtocolFilter, ValidSip
from pulsar.core.session import UniversalSessionHandler, SipSessionHandler


PARSER_UNIVERSAL = "universal"
PARSER_SIP = "sip"


class Harry():

    def __init__(self, drk_file, path_conf):

        self.drk_file = drk_file
        self.path_conf = path_conf

        # open conf file
        config = ConfigParser.RawConfigParser()
        harry_conf = os.path.join(path_conf, "harry.conf")
        config.readfp(open(harry_conf))

        self.parser = config.get('harry', 'parser')
        self.sally_bin = config.get('harry', 'sally')
        self.step = literal_eval(config.get('harry', 'step'))
        self.ngram = literal_eval(config.get('harry', 'ngram'))
        self.ratio = literal_eval(config.get('harry', 'ratio'))
        self.timeout = literal_eval(config.get('harry', 'timeout'))
        self.validateSip = literal_eval(config.get('harry', 'validateSip'))

    def generate_prisma_input(self, drk_file):

        (base, _) = os.path.splitext(self.drk_file)
        dr = DerrickReader(drk_file)

        if self.parser == PARSER_UNIVERSAL:
            pm = PacketMerger(self.step)
            # filter step:
            filteredMessages = pm.filterMessages(dr.messages)
            # get session information
            sessionHandler = UniversalSessionHandler(filteredMessages,
                                                     self.timeout)
        elif self.parser == PARSER_SIP:
            udpKeeper = ProtocolFilter(["U"])
            if self.validateSip:
                # just keep SIP messages
                udpKeeper.addFilter(ValidSip())
            # filter step:
            filteredMessages = udpKeeper.filterMessages(dr.messages)
            sessionHandler = SipSessionHandler(filteredMessages)
        else:
            raise Exception("Unknown parser type: %s" % self.parser)

        def doSingleWrite(fMessages, theBase):
            dw = DerrickWriter("%s.fdrk" % theBase)
            dw.writePackets(fMessages)
            # write sally information
            sallyInputFile = sally.rawWrite(fMessages, theBase, self.ngram)
            sallyOutputFile = "%s.sally" % theBase
            fsallyOutputFile = "%s.fsally" % theBase
            # process with sally
            sallyCfg = os.path.join(self.path_conf, 'sally.conf')
            os.system("%s -c %s %s %s" % (self.sally_bin, sallyCfg,
                                          sallyInputFile, sallyOutputFile))
            # generate fsally output
            sally.fsallyPreprocessing(sallyOutputFile, fsallyOutputFile)

        if self.ratio < 1.0 and self.ratio > 0.0:
            # do a split in train and test data
            t = time.time()
            isTest = sessionHandler.splitBySession(self.ratio)
            isTrain = [not(test) for test in isTest]
            sessionHandler.writeSessionInformation("%sTrain.harry" % base, isTrain)
            sessionHandler.writeSessionInformation("%sTest.harry" % base, isTest)
            doSingleWrite([f for (w, f) in zip(isTrain, filteredMessages) if w], base + "Train")
            doSingleWrite([f for (w, f) in zip(isTest, filteredMessages) if w], base + "Test")
        else:
            sessionHandler.writeSessionInformation("%s.harry" % base)
            doSingleWrite(filteredMessages, base)
