#! /usr/bin/python


import os
import shutil
import ConfigParser
import urllib
import data
import rule
import DFA

from ast import literal_eval
from pulsar.core.harry import Harry
from pulsar.utils.preprocessing import derrick


class ModelGenerator():

    def __init__(self, models_dir, path_conf,
                 pcaps="", binaries="",
                 nmf_components=0, process=False):

        self.models_dir = models_dir
        self.path_conf = path_conf
        self.pcaps = pcaps
        self.binaries = binaries
        self.process = process
        self.nmf_components = nmf_components

        # open conf file
        config = ConfigParser.RawConfigParser()
        model_conf = os.path.join(path_conf, "model.conf")
        config.readfp(open(model_conf))

        # load model config
        self.prisma_dir = config.get('prisma', 'path')
        self.storage_dir = config.get('data', 'storage')
        self.binaries_dir = os.path.abspath(os.path.join(self.storage_dir,
                                                         'binaries'))
        self.analyses_dir = os.path.abspath(os.path.join(self.storage_dir,
                                                         'analyses'))
        self.analyses_ival = literal_eval(config.get('data',
                                                     'analyses_interval'))
        if self.analyses_ival:
            self.analyses_ival = range(self.analyses_ival[0],
                                       self.analyses_ival[-1]+1)
        self.whitespace = config.get('model', 'whitespace')
        self.order = literal_eval(config.get('model', 'order'))
        self.ngram = literal_eval(config.get('model', 'ngram'))
        self.dograph = literal_eval(config.get('model', 'dograph'))
        self.minimize = literal_eval(config.get('model', 'minimize'))
        self.subrules = literal_eval(config.get('model', 'subrules'))
        self.colorFieldStates = literal_eval(config.get('model',
                                             'colorFieldStates'))

    def generate_model(self):

        if self.pcaps:
            self._generate_model_pcaps()
        elif isinstance(self.binaries, list):
            self._generate_model_binaries()

    def _generate_model_pcaps(self):

        # generate model from each pcaps
        for pcap_origin in self.pcaps:
            pcap = os.path.basename(pcap_origin)
            pcap_noext = pcap.split('.')[0]
            pcap_named_dir = os.path.join(self.models_dir, pcap_noext)
            if not os.path.exists(pcap_named_dir):
                print ">>> Creating dir {}".format(pcap_named_dir)
                os.makedirs(pcap_named_dir)
            pcap_path_model = os.path.join(pcap_named_dir, pcap)
            shutil.copyfile(pcap_origin, pcap_path_model)
            self._extract_derrick(pcap_noext)
            self._generate_prisma_input(pcap_noext)
            self._generate_clusters(pcap_noext)
            self._build_model_files(pcap_noext)

    def _generate_model_binaries(self):

        # if a list of binary names is passed, only the associated pcaps
        # are merged and copied to their corresponding capture dir
        if len(self.binaries) == 0:
            self.binaries = os.listdir(self.binaries_dir)
        #initialize dic with all binaries analyzed
        pcaps = {b: [] for b in self.binaries}
        # find all pcaps associated to the same binary
        if not self.analyses_ival:
            for path, dirs, files in os.walk(os.path.abspath(self.analyses_dir)):
                for file in files:
                    if file.endswith("pcap"):
                        binary_link = os.path.join(path, 'binary')
                        binary_name = os.path.realpath(binary_link).split('/')[-1]
                        if binary_name in self.binaries:
                            pcap_path = os.path.join(path, file)
                            pcaps[binary_name] += [pcap_path]
        # find all pcaps associated to the same binary within
        # a range of executions
        else:
            print "finding pcaps in {}".format(self.analyses_ival)
            for d in self.analyses_ival:
                path = os.path.join(self.analyses_dir, str(d))
                files = os.listdir(os.path.abspath(path))
                for f in files:
                    if f.endswith("pcap"):
                        binary_link = os.path.join(path, 'binary')
                        binary_name = os.path.realpath(binary_link).split('/')[-1]
                        if binary_name in self.binaries:
                            pcap_path = os.path.join(path, f)
                            pcaps[binary_name] += [pcap_path]

        # generate model from each binary pcaps
        for bin_name, pcap_list in pcaps.items():
            self._merge_pcaps(bin_name, pcap_list)
            self._extract_derrick(bin_name)
            self._generate_prisma_input(bin_name)
            self._generate_clusters(bin_name)
            self._build_model_files(bin_name)

    def _merge_pcaps(self, bin_name, pcaps):
        """ Merge all pcap files captured from several executions
        of a sample in the sandbox.
        """
        bin_named_dir = os.path.join(self.models_dir, bin_name)
        if not os.path.exists(bin_named_dir):
            os.makedirs(bin_named_dir)
            bin_path_storage = os.path.join(self.binaries_dir, bin_name)
            bin_path_model = os.path.join(bin_named_dir, bin_name)
            shutil.copyfile(bin_path_storage, bin_path_model)
        merged_pcap_file = os.path.join(bin_named_dir,
                                        "{}.pcap".format(bin_name))
        print ">>> Merging PCAPS from {}".format(bin_name)
        cmd = "mergecap {} -w {}".format(' '.join(pcaps), merged_pcap_file)
        os.system(cmd)

    def _extract_derrick(self, bin_name):
        """ Extract derrick files from pcaps in a list of
        dirs or from all dirs in the captures directory
        """
        pcap_file = os.path.join(self.models_dir, bin_name,
                                 "{}.pcap".format(bin_name))
        drk_file = os.path.join(self.models_dir, bin_name,
                                "{}.drk".format(bin_name))
        print ">>> Extracting DERRICK files from {}".format(bin_name)
        cmd = "derrick -r {} -l {}".format(pcap_file, drk_file)
        os.system(cmd)

        if self.process:
            derrick.process(drk_file)

    def _generate_prisma_input(self, bin_name):
        """ Use harry.py to generate the input for the R PRISMA module
        """
        drk_file = os.path.join(self.models_dir, bin_name,
                                "{}.drk".format(bin_name))
        h = Harry(drk_file, self.path_conf)
        print ">>> Generating PRISMA input files from {}".format(bin_name)
        h.generate_prisma_input(drk_file)

    def _generate_clusters(self, bin_name):
        """ wrap call to cluster_generator.R script
        """
        clusters_file = os.path.join(self.models_dir, bin_name,
                                     "{}.cluster".format(bin_name))
        data_dir = os.path.join(self.models_dir, bin_name, bin_name)
        core_dir = os.path.dirname(os.path.abspath(__file__))
        cluster_generator_path = os.path.join(core_dir,
                                              "cluster_generator.R")
        print ">>> Clustering data..."
        cmd = "R --no-save --args {} {} {} {} < {}".format(self.prisma_dir,
                                                           data_dir,
                                                           clusters_file,
                                                           self.nmf_components,
                                                           cluster_generator_path)
        os.system(cmd)

    def _build_model_files(self, bin_name):
        """ wrap call to model.py to generate the markov model, rules and
        templates from the cluster calculated by PRISMA.
        """
        data_dir = os.path.join(self.models_dir, bin_name, bin_name)
        m = ModelFilesGenerator(data_dir, self.order, self.ngram,
                                urllib.unquote(self.whitespace), self.subrules)

        m.saveModel()
        if self.dograph:
            import pygraphviz
            if self.minimize:
                graph = m.minimizeModel()
            else:
                graph = m.mc
            if self.colorFieldStates:
                m.setColorStates()
                G = pygraphviz.AGraph(directed=True)
                cs = set(m.colorStates)
                print "Colouring {} states:".format(len(cs))
                for node, neighs in graph.items():
                    if node in cs:
                        print node
                        if node.endswith("UAC"):
                            G.add_node(node, style="filled", fillcolor="grey")
                        if node.endswith("UAS"):
                            G.add_node(node, style="filled", fillcolor="pink")
                    else:
                        G.add_node(node)
                for node, neighs in graph.items():
                    for neig in neighs:
                        G.add_edge(node, neig)
            else:
                G = pygraphviz.AGraph(graph, directed=True)
            G.draw("%s.eps" % data_dir, prog="dot")
            G.write("%s.dot" % data_dir)


STATE_SEP = "|"
TEMPLATE_SEP = ";"


class ModelFilesGenerator:

    def __init__(self, datapath, order=2, ngram=0,
                 whitespace=" \t\n\r", subrules=False):
        self.datapath = datapath
        self.ngram = ngram
        self.dh = data.DataHandler(datapath, ngram, whitespace)
        self.order = order
        self._calculateMarkovChain()
        self._gatherTemplates()
        self.rules = {}
        if subrules:
            # generate all subrules
            subrulesOrder = range(self.order, -1, -1)
        else:
            # just the rules for this particular order
            subrulesOrder = [self.order]
        for theOrder in subrulesOrder:
            templateCombinations = self._gatherTemplatesPerCommunication(theOrder)
            self._constructRules(templateCombinations)

    def minimizeModel(self):
        dfa = DFA.prismaModel2DFA(self.mc)
        # get the states, which we should collapse
        collapse = dfa.minimize()
        return(DFA.DFA2prismaModel(dfa))

    def saveModel(self):
        # write out the markov model:
        f = file(self.datapath + ".markovModel", "w")
        for state, nextStates in self.mc.iteritems():
            for nextState, count in nextStates.iteritems():
                f.write("%s->%s,%d\n" % (state, nextState, count))
        f.close()
        # write out the templates:
        f = file(self.datapath + ".templates", "w")
        for template in self.structureTemplates:
            f.write("TEMPLATE id:%d state:%s count:%d ntokens:%d fields:%s\n" %
                    (template.templateId, template.state,
                     template.numberOfMessages, len(template.tokens),
                     ",".join(map(str, template.getFieldIndices()))))
            for tok in template.tokens:
                f.write("%s\n" % urllib.quote(tok))
        f.close()
        f = file(self.datapath + ".rules", "w")
        for ruleSet in self.rules.itervalues():
            for r in ruleSet.rules:
                f.write("RULE transition:%s srcId:%d srcField:%d dstField:%d type:%s\n" %
                        (ruleSet.fingerprint, r.sourceId, r.sourceField,
                         r.targetField, str(r.__class__)))
                f.write("%s\n" % r.getSpecificSaveString())
        f.close()

    def setColorStates(self):
        """ Create a boolean dic indicating if each state must
        be colored. A state is colored if any of its templates
        has fields that can be fuzzed.
        """
        self.colorStates = []
        for st in self.structureTemplates:
            if st.getFieldIndices():
                self.colorStates += [st.state]

    def setStateLabel(self, msgIndex, stateLabel):
        self.stateLabel4msg[msgIndex] = stateLabel
        self.msgs4state.setdefault(stateLabel, []).append(msgIndex)

    def getStartLabel(self):
        return STATE_SEP.join([data.START_STATE] * self.order)

    def _calculateMarkovChain(self):
        # we employ a sparse representation here:
        # dict of dicts...
        self.mc = {}
        startLabel = self.getStartLabel()
        self.stateLabel4msg = [""] * self.dh.getN()
        self.msgs4state = {}
        self.mc[startLabel] = {}
        for commId in self.dh.getCommunicationIds():
            # all states embraced by (order-1) START_STATE and END_STATE
            states = self.dh.getStateIdsForComm(commId, self.order-1)
            indices = self.dh.getMsgIndexForComm(commId)
            for ind in range(0, len(states)-self.order):
                s1 = STATE_SEP.join(states[ind:(ind+self.order)])
                s2 = STATE_SEP.join(states[(ind+1):(ind+self.order+1)])
                # increase the transition count
                trans = self.mc.setdefault(s1, {})
                trans[s2] = trans.get(s2, 0) + 1
                # store the state labels
                if self.order == 1:
                    if ind >= 1:
                        self.setStateLabel(indices[ind-1], s1)
                else:
                    # higher order markov chain
                    if ind < len(indices):
                        self.setStateLabel(indices[ind], s1)
                    if ind == 0:
                        trans = self.mc[startLabel]
                        trans[s1] = trans.get(s1, 0) + 1

    def _gatherTemplates(self):
        self.templateid4msg = [-1] * self.dh.getN()
        self.msg4templateIds = {}
        self.structureTemplates = []
        templateId = 0
        for (state, msgs) in self.msgs4state.iteritems():
            # get all tokenized messages associated with this state
            tokens = [self.dh.getTokensForMsg(m) for m in msgs]
            # cluster them according to the number of tokens
            len2tokens = {}
            for (tok, msg) in zip(tokens, msgs):
                len2tokens.setdefault(len(tok), []).append((tok, msg))
            for (theLen, sameLengthMsgs) in len2tokens.iteritems():
                # construct an empty template capable of holding theLen tokens
                curTemplate = StructureTemplate(state, templateId, theLen)
                # merge the messages
                for (tok, msg) in sameLengthMsgs:
                    curTemplate.addTokenizedMessage(tok)
                    self.templateid4msg[msg] = templateId
                curTemplate.inferStructure()
                self.structureTemplates.append(curTemplate)
                self.msg4templateIds[templateId] = [m[1] for m in sameLengthMsgs]
                templateId += 1

    def _gatherTemplatesPerCommunication(self, theOrder):
        templateCombinations = {}
        for comm in self.dh.getCommunicationIds():
            msgs = self.dh.getMsgIndexForComm(comm)
            tids = [self.templateid4msg[msg] for msg in msgs]

            msgs = ([-1] * theOrder) + msgs
            tids = ([-1] * theOrder) + tids

            for ind in xrange(len(msgs) - theOrder):
                curTids = [str(t) for t in tids[ind:(ind+theOrder+1)]]
                curMsgs = msgs[ind:(ind+theOrder+1)]
                templateCombinations.setdefault(TEMPLATE_SEP.join(curTids),
                                                []).append(tuple(curMsgs))
        return templateCombinations

    def _constructRules(self, templateCombinations):

        def getTokens(mid):
            if mid == -1:
                return []
            else:
                return self.dh.getTokensForMsg(mid)

        def getFields(tid):
            if tid == -1:
                return []
            else:
                return self.structureTemplates[tid].getFieldIndices()

        for (templateIds, msgs) in templateCombinations.iteritems():
            tids = [int(tid) for tid in templateIds.split(TEMPLATE_SEP)]
            fieldsForMessages = [None] * len(tids)
            for (ind, tid) in enumerate(tids):
                tokenizedMessages = [getTokens(mids[ind]) for mids in msgs]
                fieldsForMessages[ind] = FieldArray(tokenizedMessages,
                                                    getFields(tid))
            ruleSet = rule.RuleSet(templateIds, tids)
            ruleSet.gatherRules(fieldsForMessages, self.ngram > 0)
            self.rules[templateIds] = ruleSet


class FieldArray:

    def __init__(self, tokenizedMessages, fieldIndices):
        # list of lists
        # self.array[m] contains the field values for the m-th message
        self.array = [[tokm[ind][1] for ind in fieldIndices]
                      for tokm in tokenizedMessages]

    def getValuesForField(self, index):
        return [m[index] for m in self.array]

    def getNumberOfFields(self):
        if len(self.array[0]) == 0:
            return 0
        else:
            return len(self.array[0])


class StructureTemplate:

    def __init__(self, state, templateId, nTokens):
        self.state = state
        self.templateId = templateId
        self.tokens = [set() for _ in xrange(nTokens)]
        self.numberOfMessages = 0

    def addTokenizedMessage(self, toks):
        assert(len(toks) == len(self.tokens))
        self.numberOfMessages += 1
        for (ind, tok) in enumerate(toks):
            # TODO: care for type of token (WS, TOK)?
            self.tokens[ind].add(tok[1])

    def inferStructure(self):
        self.fields = [ind for (ind, f) in enumerate(self.tokens)
                       if len(f) > 1]
        # convert the token sets to list of strings
        for ind in xrange(len(self.tokens)):
            cur = self.tokens[ind]
            if len(cur) == 1:
                self.tokens[ind] = cur.pop()
            else:
                self.tokens[ind] = ""

    def getFieldIndices(self):
        return self.fields
