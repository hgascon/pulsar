#!/usr/bin/env python

# Network Server/Client interface for LENS module
# Copyight (c) 2012 Hugo Gascon <hgascon@mail.de>


import sys
#import re
#import random
import socket
from optparse import OptionParser
#import urllib
#import select
import lens
import time

#TODO modify this to work with a similar loop as in the fuzzer and run() method etc

if __name__ == "__main__":
    usage = "usage: %prog [options] <LENS model file> <UAC/UAS (LENS client/server role)>"
    parser = OptionParser(usage)
    parser.add_option("-o", "--host", dest="host",
                      default="127.0.0.1",
                      help="robot server IP address (default %default)")
    parser.add_option("-p", "--port", type="int", dest="port",
                      default=80,
                      help="HTTP port (default %default)")
    parser.add_option("-t", "--timeout", type="float", dest="tout",
                      default=2.0,
                      help="socket timeout (default %default)")
    parser.add_option("-s", "--size", type="int", dest="bsize",
                      default=8192,
                      help="socket buffer bytes size (default %default)")
    (options, args) = parser.parse_args()
    if len(args) < 2:
        parser.print_help()
        sys.exit(1)

    model_file = args[0]
    role = args[1]
    l = lens.Lens(model_file, role)

    if role == "UAC":

        #network client configuration
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection.connect((options.host, options.port))
        connection.settimeout(options.tout)
        print "[*] Connected to server..."

        #client starts communications
        snd_message = l.transitionSelf()
        print "first client msg: "+str(snd_message[1])
        connection.send(str(snd_message[1]))

        while 1:
            time.sleep(0.3)
            try:
                rcv_message = connection.recv(options.bsize)
                print "rcv msg: "+str(rcv_message)
            except socket.timeout:
                rcv_message = ""
            if rcv_message != "":
                l.consumeOtherSide(rcv_message)
            snd_message = l.transitionSelf()
            print "snd mesg: " + str(snd_message[1])
            connection.send(str(snd_message[1]))
    else:

        #network server configuration
        backlog = 1
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((options.host, options.port))
        s.listen(backlog)
        connection, address = s.accept()
        connection.settimeout(options.tout)
        print "[*] Connected to client..."

        while 1:
            time.sleep(0.3)
            try:
                rcv_message = connection.recv(options.bsize)
            except socket.timeout:
                print "\n>>> TIMEOUT IN RECEIVE\n"
                rcv_message = ""
                if snd_message[1] is None:
                    print ">>> NO TRANSITION POSSIBLE."
                    print ">>> WAITING FOR NEW CONNECTION...\n"
                    connection.close()
                    connection, address = s.accept()
                    connection.settimeout(options.tout)
                    continue
            if rcv_message != "":
                print "\n>>> CONSUMING RECEIVED MESSAGE:\n{}".format(rcv_message)
                l.consumeOtherSide(rcv_message)
            snd_message = l.transitionSelf()
#            print "snd_message:\n{}".format(snd_message)
            if snd_message[1] is not None:
                print "\n>>> SENDING MESSAGE:\n{}".format(snd_message[1])
                connection.send(str(snd_message[1]))

    connection.close()



#TODO  implement class
class Simulator():

    def __init__(self, model_path):
        self._load_simulation_conf()
        return

    def _load_simulation_conf(self):
        return

    def start(self):
        return
