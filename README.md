
## PULSAR 

[![Join the chat at https://gitter.im/hgascon/pulsar](https://badges.gitter.im/hgascon/pulsar.svg)](https://gitter.im/hgascon/pulsar?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)


#### Protocol Learning, Simulation and Stateful Fuzzer

Pulsar is a network fuzzer with automatic protocol learning and simulation capabilites. The tool allows to model a protocol through machine learning techniques, such as clustering and hidden Markov models. These models can be used to simulate communication between Pulsar and a real client or server thanks to semantically correct messages which, in combination with a series of fuzzing primitives, allow to test the implementation of an unknown protocol for errors in deeper states of its protocol state machine.

For detailed information about the method implemented by Pulsar, you can read the following publications:

**[Pulsar: Stateful Black-Box Fuzzing of Proprietary Network Protocols](http://www.hugogascon.com/publications/2015-securecomm.pdf)**  
Hugo Gascon, Christian Wressnegger, Fabian Yamaguchi, Daniel Arp and Konrad Rieck  
*Proc. of 11th EAI International Conference on Security and Privacy in Communication Networks (SECURECOMM) October 2015*

**[Learning Stateful Models for Network Honeypots](http://www.hugogascon.com/publications/2012a-aisec.pdf)**  
Tammo Krueger, Hugo Gascon, Nicole Krämer and Konrad Rieck  
*ACM Workshop on Security and Artificial Intelligence (AISEC) October 2012*

                     _
         _ __  _   _| |___  __ _ _ __
        | '_ \| | | | / __|/ _` | '__|
        | |_) | |_| | \__ \ (_| | |
        | .__/ \__,_|_|___/\__,_|_|  v0.1-dev
        |_|

    usage: pulsar.py [-h] [-c CONF] [-l] [-p PCAP] [-b BINARIES] [-a] [-x]
                     [-o OUT] [-d DIMENSION] [-s] [-z] [-m MODEL]

    Protocol Learning and Stateful Fuzzing

    optional arguments:
      -h, --help            show this help message and exit
      -c CONF, --conf CONF  Change default directory for configuration files. If
                            no directory is given, the files from 'pulsar/conf'
                            will be read.

    MODEL LEARNING:
      -l, --learner         Learn a model from a set of network traces.
      -p PCAP, --pcap PCAP  tcpdump output file (pcap) or list of files separated
                            by commas to use as input data for a new model.
      -b BINARIES, --binaries BINARIES
                            Name of binaries to process from the cuckoo storage
                            dir separated with commas.
      -a, --all-binaries    Generate models for all binaries from the cuckoo
                            storage dir (cuckoo/storage/binaries).
      -x, --process         Process derrick files through the functions defined in
                            utils/preprocessing/derrick.py.
      -o OUT, --out OUT     Change output directory for generated models. If no
                            directory is given, the model will be written to the
                            'models' directory.
      -d DIMENSION, --dimension DIMENSION
                            Number of components to be used for NMF clustering.

    SIMULATION & FUZZING:
      -s, --simulate        Simulate communication based on a given model.
      -z, --fuzzer          Start a fuzzing session based on a given model.
      -m MODEL, --model MODEL
                            Path of the dir containing the model files to be
                            loaded for simulation or fuzzing.


### Configuration

The directory *pulsar/conf* contains a series of configuration files that define the parameters required for certain operations in each one of the Pulsar methods for automatic learning, simulation and fuzzing.

### Examples

Generate the model of a communication channel from individual PCAP files or the recorded traces of one or more binaries run by cuckoo sandbox:
    
    $> pulsar.py -l -p file.pcap (1 pcap file)
    $> pulsar.py -b 016169EBEBF1CEC2AAD6C7F0D0EE9026 (1 or more binaries from cuckoo storage)
    $> pulsar.py -a (all binaries from cuckoo storage)

Simulate a communication channel based on a learnt model:

    $> pulsar.py -s -m model_file

Initiate a fuzzing session against a target given the model of its communication channel:

    $> pulsar.py -z -m model_file

