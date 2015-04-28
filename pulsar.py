#!/usr/bin/python

import sys
import os
import argparse

from pulsar.core.model import ModelGenerator
from pulsar.core.simulator import Simulator
from pulsar.core.fuzzer import Fuzzer


def print_logo():
    print("""
                 _
     _ __  _   _| |___  __ _ _ __
    | '_ \| | | | / __|/ _` | '__|
    | |_) | |_| | \__ \ (_| | |
    | .__/ \__,_|_|___/\__,_|_|  v0.1-dev
    |_|
        """)


def exit():
    print_logo()
    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Protocol Learning and\
                                     Stateful Fuzzing')

    parser.add_argument("-c", "--conf", default="pulsar/conf",
                        help="Change default directory for configuration files.\
                        If no directory is given, the files from 'pulsar/conf'\
                        will be read.")

    learner = parser.add_argument_group('MODEL LEARNING')
    learner.add_argument("-l", "--learner", action="store_true",
                         help="Learn a model from a set of network traces.")
    learner.add_argument("-p", "--pcap", default="",
                         help="tcpdump output file (pcap) or list of files\
                         separated by commas to use as input data for a\
                         new model.")
    learner.add_argument("-b", "--binaries", default=[],
                         help="Name of binaries to process from the cuckoo\
                         storage dir separated with commas.")
    learner.add_argument("-a", "--all-binaries", action="store_true",
                         help="Generate models for all binaries from the cuckoo\
                         storage dir (cuckoo/storage/binaries).")
    learner.add_argument("-x", "--process", action="store_true",
                         help="Process derrick files through the functions\
                         defined in utils/preprocessing/derrick.py.")
    learner.add_argument("-o", "--out", default="models",
                         help="Change output directory for generated models.\
                         If no directory is given, the model will be written\
                         to the 'models' directory.")
    learner.add_argument("-d", "--dimension", default=0,
                         help="Number of components to be used for NMF clustering.")

    sim_fuzz = parser.add_argument_group('SIMULATION & FUZZING')
    sim_fuzz.add_argument("-s", "--simulate", action="store_true",
                          help="Simulate communication based on a given model.")
    sim_fuzz.add_argument("-z", "--fuzzer", action="store_true",
                          help="Start a fuzzing session based on a given model.")
    sim_fuzz.add_argument("-m", "--model", default="",
                          help="Path of the dir containing the model files to be\
                          loaded for simulation or fuzzing.")

    args = parser.parse_args()
    path_conf = os.path.realpath(args.conf)
    models_dir = os.path.realpath(args.out)

    if args.learner:
        mg = ""
        if args.pcap:
            pcaps = args.pcap.split(',')
            pcaps = [os.path.realpath(p) for p in pcaps]
            mg = ModelGenerator(models_dir, path_conf,
                                pcaps=pcaps,
                                nmf_components=args.dimension,
                                process=args.process)
        elif args.binaries:
            binaries = args.binaries.split(',')
            mg = ModelGenerator(models_dir, path_conf,
                                binaries=binaries,
                                nmf_components=args.dimension,
                                process=args.process)
        elif args.all_binaries:
            mg = ModelGenerator(models_dir, path_conf,
                                binaries=[],
                                nmf_components=args.dimension,
                                process=args.process)
        if mg:
            print_logo()
            mg.generate_model()
        else:
            print ("\nPlease, provide the path to a pcap or a list of pcaps"
                   " (-p),\nor a list of names from binaries which have been"
                   " analyzed by cuckoo (-b | -a).\n")
    elif args.simulate:
        if args.model:
            #TODO implement the Simulator class as a subset of the fuzzer
            s = Simulator(os.path.realpath(args.model), path_conf)
            print_logo()
            s.run()
        else:
            print ("\nPlease, provide the path containing the communication"
                   " model with option -m.\n")
    elif args.fuzzer:
        if args.model:
            f = Fuzzer(os.path.realpath(args.model), path_conf)
            f.run()
        else:
            print ("\nPlease, provide the path containing the communication"
                   " model with option -m.\n")
    else:
        exit()
