# Network Server/Client interface for LENS module
# Copyright (c) 2016 Hugo Gascon <hgascon@mail.de>

import configparser
import os
import socket
from . import lens
import time
from ast import literal_eval


class Simulator:

    def __init__(self, model_path, conf_path):

        self.model_path = model_path
        self.conf_path = conf_path

        # open and load conf file
        config = configparser.RawConfigParser()
        model_conf = os.path.join(self.conf_path, "simulator.conf")
        config.readfp(open(model_conf))

        # load model config
        self.role = config.get("model", "role")
        self.sim_search = literal_eval(config.get('model', 'simsearch'))
        self.transition_mode = literal_eval(config.get('model',
                                                       'transitionmode'))
        self.lexer_style = config.get('model', 'lexerstyle')
        self.templates_no_fields = literal_eval(config.get('model',
                                                           'nofieldstemplates'))

        if self.role == "client" or self.role == "server":
            self.host = config.get(self.role, "host")
            self.port = config.get(self.role, "port")
            self.tout = config.get(self.role, "timeout")
            self.bsize = config.get(self.role, "bsize")
        else:
            print("Err: set the Simulator role to 'client' \
                   or 'server' in {}".format(self.model_path))

    def run(self):

        # initialize LENS object
        l = lens.Lens(self.model_path,
                      self.role,
                      self.sim_search,
                      self.transition_mode,
                      self.lexer_style,
                      self.templates_no_fields)

        if self.role == "client":

            # network client configuration
            connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            connection.connect((self.host, self.port))
            connection.settimeout(self.tout)
            print("[*] Connected to server...")

            # client starts communications
            snd_message = l.transitionSelf()
            print("first client msg: "+str(snd_message[1]))
            connection.send(str(snd_message[1]))

            while 1:
                time.sleep(0.3)
                try:
                    rcv_message = connection.recv(self.bsize)
                    print("rcv msg: "+str(rcv_message))
                except socket.timeout:
                    rcv_message = ""
                if rcv_message != "":
                    l.consumeOtherSide(rcv_message)
                snd_message = l.transitionSelf()
                print("snd mesg: " + str(snd_message[1]))
                connection.send(str(snd_message[1]))

        elif self.role == "server":

            # network server configuration
            backlog = 1
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind((self.host, self.port))
            s.listen(backlog)
            connection, address = s.accept()
            connection.settimeout(self.tout)
            print("[*] Connected to client...")

            while 1:
                time.sleep(0.3)
                try:
                    rcv_message = connection.recv(self.bsize)
                except socket.timeout:
                    print("\n>>> TIMEOUT IN RECEIVE\n")
                    rcv_message = ""
                    if snd_message[1] is None:
                        print(">>> NO TRANSITION POSSIBLE.")
                        print(">>> WAITING FOR NEW CONNECTION...\n")
                        connection.close()
                        connection, address = s.accept()
                        connection.settimeout(self.tout)
                        continue
                if rcv_message != "":
                    print("\n>>> CONSUMING RECEIVED \
                            MESSAGE:\n{}".format(rcv_message))
                    l.consumeOtherSide(rcv_message)
                snd_message = l.transitionSelf()
                #            print "snd_message:\n{}".format(snd_message)
                if snd_message[1] is not None:
                    print("\n>>> SENDING MESSAGE:\n{}".format(snd_message[1]))
                    connection.send(str(snd_message[1]))

        try:
            connection.close()
        except:
            print("Err: No active connection to close.")
            pass
