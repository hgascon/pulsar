#!/usr/bin/python

import os
import sys
import socket
import time
import json
import urllib.request, urllib.parse, urllib.error
import errno
import configparser
import numpy as np

from ast import literal_eval
from random import choice, randrange
from socket import error as SocketError

from pulsar.core.lens import Lens
from pulsar.common import pz
from pulsar.common.networking import Client, Server


SENSITVE_CHARACTERS = "#$%&(){};:\'\"|,.<>/?`\\"
FUZZ_STATUS_OK = "OK"
FUZZ_STATUS_CRASH = "CRASH"
FUZZ_STATUS_TERMINATED = "TERMINATED"


class Fuzzer:
    """ Definition and management of the fuzzing primitives
    """

    def __init__(self, model_dir, path_conf):

        self.model_dir = model_dir
        self.path_conf = path_conf

        # open conf file
        config = configparser.RawConfigParser()
        fuzzer_conf = os.path.join(path_conf, "fuzzer.conf")
        config.readfp(open(fuzzer_conf))

        # load network config
        self.host = config.get('network', 'host')
        self.port = literal_eval(config.get('network', 'port'))
        self.timeout = literal_eval(config.get('network', 'timeout'))
        self.bsize = literal_eval(config.get('network', 'bsize'))

        # load fuzzer config
        self.fuzzer_mode = config.get('fuzzer', 'fuzzermode')
        self.interactive = literal_eval(config.get('fuzzer', 'interactive'))
        self.fuzz_length = config.get('fuzzer', 'fuzzlength')
        self.timer_termination = literal_eval(config.get('fuzzer',
                                                         'terminationtimer'))

        #load config and initialize LENS object
        model_file = os.path.join(model_dir, os.path.basename(model_dir))
        role = config.get('fuzzer', 'role')
        if role == "client":
            role = "UAC"
        else:
            role = "UAS"
        sim_search = literal_eval(config.get('fuzzer', 'simsearch'))
        transition_mode = literal_eval(config.get('fuzzer', 'transitionmode'))
        lexer_style = config.get('fuzzer', 'lexerstyle')
        templates_no_fields = literal_eval(config.get('fuzzer',
                                                      'nofieldstemplates'))
        self.lens = Lens(model_file,
                         role,
                         sim_search,
                         transition_mode,
                         lexer_style,
                         templates_no_fields)

        #TODO add the passing of the fuzzer to the parameter of lens
        self.lens.set_fuzzer(self)

        #initialize Logger
        log_file_name = "{}.fuzzlog".format(self.lens.modelPath)
        self.logger = Logger(log_file_name)
        self.iteration = 0
        self.status = FUZZ_STATUS_OK
        self.trace = [], []

        self.tracker_path = "{}.tracker.pz".format(self.lens.modelPath)
        if not os.path.isfile(self.tracker_path):
            # every fuzzable template is initialized to 2^num_fields-1
            # to index all possible fuzzing masks of fields
            self.tracker = {}
            for t in self.lens.tl.template_list:
                if t.state.endswith(self.lens.role) and len(t.fields) != 0:
                    self.tracker[t.ID] = 2**len(t.fields)-1
            pz.save(self.tracker, self.tracker_path)
        else:
            self._load_tracker()

        # load cuckoo config
        self.cuckoo_session = literal_eval(config.get('cuckoo', 'active'))
        self.cuckoo_path = config.get('cuckoo', 'path')
        sys.path.insert(0, os.path.abspath(self.cuckoo_path))
        if self.cuckoo_session == 1:
            from lib.cuckoo.core.database import Database
            self.db = Database()
            self.bin_name = model_file

    def run(self):

        if self.lens.role == "UAC":
            while True:
                self.new_iteration()
                connection = Client(self.host, self.port,
                                    self.timeout, self.bsize)
                # generate first client message and send to the server
                snd_message = self.lens.transitionSelf()
                print("\n>>> SENDING msg:\n{}".format(snd_message[1]))
                try:
                    connection.send(str(snd_message[1]))
                except socket.error as e:
                    print("socket: {} in send operation".format(e))

                while self.status == FUZZ_STATUS_OK:
                    #time.sleep(0.3)
                    try:
                        rcv_message = connection.recv()
                        if len(rcv_message) == 0:
                            e = SocketError("Received empty message")
                            e.errno = 0
                            raise e
                        deco = '#'*80
                        quoted_rcv_msg = urllib.parse.quote(rcv_message)
                        print(">>> RECEIVED message:\n{}\n{}\n{}".format(deco,
                                                                         quoted_rcv_msg,
                                                                         deco))
                    except Exception as e:
                        print("socket: {}\n".format(e))
                        self._termination_check()
                        if self.status is FUZZ_STATUS_TERMINATED:
                            connection.close()
                            self._crash_check()
                            self.log_trace()
                            break
                        else:
                            if e.errno == errno.ECONNRESET:
                                connection.close()
                                connection.accept()
                                continue
                            if e.errno == errno.ETIMEDOUT:
                                pass

                    print(">>> Consuming RECEIVED msg of length {}".format(len(rcv_message)))
                    status = self.lens.consumeOtherSide(rcv_message)
                    print(">>> STATUS: {}".format(status))
                    if status == "END":
                        self.new_iteration(reset=1)
                        status = self.lens.consumeOtherSide(rcv_message)
                        print(">>> STATUS: {}".format(status))
                    if status == "NO TRANSITION":
                        print("Consuming empty message...")
                        status = self.lens.consumeOtherSide("")
                    self.log_trace()
                    status, msg, transition = self.lens.transitionSelf()
                    print(">>> STATUS: {}, TRANSITION: {}".format(status,
                                                                  transition))
                    if msg is not None:
                        try:
                            connection.send(str(msg))
                            print(">>> SENDING msg of length {}".format(len(msg)))
                            if len(msg) < 5000:
                                deco = '#'*80
                                print("{}\n{}\n{}".format(deco, msg, deco))
                        except socket.error as e:
                            print("socket: {} in send operation".format(e))
                            connection.close()
                            break

                 
        elif self.lens.role == "UAS":

            connection = Server(self.host, self.port,
                                self.timeout, self.bsize)
            while True:
                if self.cuckoo_session:
                    self._run_sample()
                connection.accept()
                connection.settimeout(self.timeout)
                self.new_iteration()
                rcv_message = ""
                while self.status == FUZZ_STATUS_OK:
                    try:
                        print(">>> RECEIVING message... ")
                        rcv_message = connection.recv()
                        if len(rcv_message) == 0:
                            e = SocketError("Received empty message")
                            e.errno = 0
                            raise e
                        deco = '#'*80
                        quoted_rcv_msg = urllib.parse.quote(rcv_message)
                        print(">>> RECEIVED message:\n{}\n{}\n{}".format(deco,
                                                                         quoted_rcv_msg,
                                                                         deco))
                    except Exception as e:
                        print("socket: {}".format(e))
                        self._termination_check()
                        if self.status is FUZZ_STATUS_TERMINATED:
                            connection.close()
                            self._crash_check()
                            self.log_trace()
                            break
                        else:
                            if e.errno == errno.ECONNRESET:
                                connection.close()
                                connection.accept()
                                continue
                            if e.errno == errno.ETIMEDOUT:
                                pass

                    #if rcv_message != "":
                    print(">>> Consuming RECEIVED msg of length {}".format(len(rcv_message)))
                    status = self.lens.consumeOtherSide(rcv_message)
                    print(">>> STATUS: {}".format(status))
                    if status == "END":
                        self.new_iteration(reset=1)
                        status = self.lens.consumeOtherSide(rcv_message)
                        print(">>> STATUS: {}".format(status))
                    if status == "NO TRANSITION":
                        print("Consuming empty message...")
                        status = self.lens.consumeOtherSide("")
                    self.log_trace()
                    status, msg, transition = self.lens.transitionSelf()
                    print(">>> STATUS: {}, TRANSITION: {}".format(status,
                                                                  transition))
                    if msg is not None:
                        try:
                            connection.send(str(msg))
                            print(">>> SENDING msg of length {}".format(len(msg)))
                            if len(msg) < 5000:
                                deco = '#'*80
                                print("{}\n{}\n{}".format(deco, msg, deco))
                        except socket.error as e:
                            print("socket: {} in send operation".format(e))
                            connection.close()
                            break

    ######## Sandbox Related Functions ########

    def _run_sample(self):
        self.task_id = self.db.add_path(self.bin_name)
        print("Running binary in sandbox with ID {}:\n{}".format(self.task_id,
                                                                 self.bin_name))

    ######## Tracking Functions ########

    def _termination_check(self):

        print(">>> CHECKING FOR TERMINATED EXECUTION")
        terminated = ""
        # verify termination with cuckoo output
        if self.cuckoo_session:
            # wait until result from execution is stored in db
            for i in range(self.timer_termination):
                time.sleep(1)
                print(".")
            try:
                task = self.db.view_task(self.task_id)
            except AttributeError:
                print("Err: The cuckoo interface is active but no " \
                      "cuckoo task has been found! You may consider " \
                      "setting cuckoo_session to 0 in fuzzer.conf")
                sys.exit()
            if task.completed_on:
                terminated = True
                print("Sample execution is terminated!")
            else:
                return
        # verify termination manually
        else:
            while terminated == "":
                inp = input('Connection terminated? [y/n]: ')
                if inp == 'y':
                    terminated = True
                elif inp == 'n':
                    terminated = False
        if terminated:
            self.status = FUZZ_STATUS_TERMINATED

    def _crash_check(self):
        """ Set fuzzing status according to result of
        last fuzzing input. This function should be read the exit
        code of the sample from the sandbox report.
        """
        print(">>> CHECKING FOR CRASH")
        crash = ""
        if self.cuckoo_session:
            task = self.db.view_task(self.task_id)
            if task.status == "reported":
                #fuzzer_path = os.path.dirname(os.path.realpath(__file__))
                #cuckoo_path = "/".join(fuzzer_path.split('/')[:-1] + ["cuckoo"])
                report_path = "storage/analyses/{}/reports/report.json".format(task.id)
                report_path = os.path.join(self.cuckoo_path, report_path)
                report = json.loads(open(report_path, 'r').read())
                for process in report['behavior']['processes']:
                    for call in process['calls']:
                        if call['api'] == 'LdrLoadDll':
                            for arg in call['arguments']:
                                if arg['name'] == 'FileName' and 'faultrep.dll' in arg['value']:
                                    crash = True
        else:
            while crash == "":
                inp = input('Binary crashed? [y/n]: ')
                if inp == 'y':
                    crash = True
                elif inp == 'n':
                    crash = False
        if crash:
            self.status = FUZZ_STATUS_CRASH
        print("Fuzzer status: {}".format(self.status))

    def _load_tracker(self):
        self.tracker = pz.load(self.tracker_path)

    def _save_tracker(self):
        pz.save(self.tracker, self.tracker_path)

    def new_iteration(self, reset=0):
        """ Increment current iteration of the fuzzer and
        initialize the status for the new run.
        """
        if not reset:
            self.iteration += 1
            self.status = FUZZ_STATUS_OK
        print(">>> RESETING MODEL...")
        self.lens.reset_model()

    def get_fuzz_fields(self, template_id):

        self._load_tracker()
        fields_len = len(self.lens.tl.template_dic[template_id].fields)
        fuzz_mask_int = self.tracker[template_id]
        fuzz_mask_bin = np.binary_repr(int(np.invert(np.array([fuzz_mask_int]))),
                                       fields_len)
        fuzz_mask_bin = [int(i) for i in fuzz_mask_bin]
        return np.nonzero(fuzz_mask_bin)[0]

    def update_tracker(self, template_id):

        self._load_tracker()
        fuzz_mask = self.tracker[template_id]
        if fuzz_mask > 0:
            self.tracker[template_id] -= 1
        elif fuzz_mask == 0:
            # if all fuzzing masks have been test, the masks
            # are reinitialized and the loop is restarted.
            t = self.lens.tl.template_dic[template_id]
            self.tracker[template_id] = 2**len(t.fields)-1
        self._save_tracker()

    def log_trace(self):
        """ Build a trace of the current configuration of the
        fuzzer and send it to the logger.
        """
        fields_to_fuzz, fields_data = self.trace
        template_id = self.lens.templates.getLastEntries(1)[0].ID
        state = self.lens.mm.state
#        if self.status == FUZZ_STATUS_CRASH:
#            fields_to_fuzz, fields_data = self.previous_trace
        trace = [int(time.time()), self.iteration,
                 self.status, state, template_id, fields_to_fuzz, fields_data]
        self.logger.write_trace(trace)
        print(trace)
        self.previous_trace = self.trace
        self.trace = [], []

    ######## Fuzzing Related Functions ########

    def fuzz(self, rule, data, fuzz_fields):

        # if data is not fuzzed, return it properly
        # not fuzzed either cause
        #   - not fuzzed in this iteration
        #   - for some reason fuzzer_mode could not be matched
        fuzzed_data = data
        if rule.dst_field in fuzz_fields:
            if self.fuzzer_mode == "rand_overflow":
                fuzzed_data = self._get_random_data()
            if self.fuzzer_mode == "const_overflow":
                fuzzed_data = self._get_constant_data()
            if self.fuzzer_mode == "int_overflow":
                fuzzed_data = self._get_overflowed_integer(data)
            if self.fuzzer_mode == "non_utf8":
                fuzzed_data = self._get_non_utf8_data()
        return fuzzed_data

    ######## Fuzzing Primitives ########

    def _get_random_data(self):
        """ Generate a stream of random data with a 5% of security
        sensitive characters (problematic in parsing).
        """
        length = self.fuzz_length
        chars_length = length * 5 / 100
        chars = [choice(SENSITVE_CHARACTERS) for i in range(chars_length)]
        chars_idx = [randrange(0, length-1) for i in range(chars_length)]
        rand = list(os.urandom(length))
        for idx, char in zip(chars_idx, chars):
            rand[idx] = char
        return ''.join(rand)

    def _get_constant_data(self):
        length = int(self.fuzz_length)
        return 'A' * length

    def _get_non_utf8_data(self):
        return "\xe7\x9f\x9b\xe7\x9b\\u0178\xe4\\u0153\xbf\
                \xe4\\u017e\\u20ac\xe5\\u20ac\xa7IT\xe5\xb7\
                \\u0161\xe5\\u20ac\\u017d\xe4\xb9\x8b\xe9\x97\
                \\u017d\xe4\xba\x89"

    def _get_overflowed_integer(self, data):
        if self.is_integer(data):
            #return 2**(len(bin(data))-2)
            return -1
        else:
            return data

    def is_integer(n):
        try:
            int(n)
            return True
        except ValueError:
            return False

class Logger:

    def __init__(self, log_file_name):
        self.log_file_name = log_file_name
        names = ["time", "iteration",
                 "status", "model state",
                 "template id", "fuzzed fields", "non-fuzzed data"]
        self.write_trace(names)

    def write_trace(self, trace):
        self.log_file = open(self.log_file_name, 'a')
        self.log_file.write(', '.join([str(s) for s in trace]))
        self.log_file.write('\n')
        self.log_file.close()
