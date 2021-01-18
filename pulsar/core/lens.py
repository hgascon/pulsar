#!/usr/bin/python


import re
import random
import urllib.request, urllib.parse, urllib.error
import operator
from .util import scanTokens, scanNgrams
from Levenshtein import distance
from random import choice

LEXER_TOKENS = "TOKENS"
LEXER_NGRAMS = "NGRAMS"
OFS_TRANSITION = 3


def pickIndex(counts):
    total = sum(counts)
    dice = random.randint(1, total)
    countsSoFar = 0

    for (ind, count) in enumerate(counts):
        countsSoFar += count
        if countsSoFar >= dice:
            ret = ind
            break
    return ret


class MarkovModel:

    def __init__(self, model_file):
        self.load_markov_model(model_file)
        self.init()
        # setup auxilliary structures:
        self.simplifiedModel = {}
        for (state, suc) in self.markov_model.items():
            self.simplifiedModel[state] = {}.fromkeys([s[0] for s in suc],
                                                      True)
        self.allStates = self.simplifiedModel.copy()
        for trans in list(self.simplifiedModel.values()):
            self.allStates.update(trans)
        self.allStates = list(self.allStates.keys())

        self.fuzzer = ""

    def init(self):
        """ Set markov model to the initial state
        Avoids loading the model when a new session starts.
        """
        self.state = "|".join(["START"] * self.order)

    def set_fuzzer(self, fuzzer):
        self.fuzzer = fuzzer

    def getSimplifiedModel(self, stateFilter=None):
        """ return a map of maps giving the possible transitions from a
        given state. This is for instance useful for plotting:
        import pygraphviz; G = pygraphviz.AGraph(m.getSimplifiedModel(),
                                                 directed=True);
        G.draw("data/robotMinimized.pdf", prog="dot")
        """
        if stateFilter is None:
            ret = self.simplifiedModel
        else:
            ret = {}
            for k in list(self.simplifiedModel.keys()):
                if k in stateFilter:
                    ret[k] = dict([kv for kv in list(self.simplifiedModel[k].items())
                                   if kv[0] in stateFilter])
        return ret

    def getAllStates(self):
        return self.allStates

    def getMarkovMatrix(self):
        allStates = self.getAllStates()
        nStates = len(allStates)
        ret = [[0] * nStates for _ in range(nStates)]
        for (ind, state) in enumerate(allStates):
            counts = self.markov_model.get(state, [])
            for (s, c) in counts:
                ret[ind][allStates.index(s)] = c
        return ret

    def exportMarkovMartrix(self, fileName):
        f = file(fileName, "w")
        f.write("%s\n" % "\t".join(self.allStates))
        for (s, l) in zip(self.allStates, self.getMarkovMatrix()):
            f.write("%s\t%s\n" % (s, "\t".join([str(v) for v in l])))
        f.close()

    def update_state(self, state):
        """ Update markov model with new state and set previous states """
        self.state = state

    def getState(self):
        return self.state

    def getOrder(self):
        return self.order

    def load_markov_model(self, model_file):
        """ Return markov model from Prisma output file as a dictionary
        where keys are current states and values are next possible states
        """

        fd = open(model_file, "r")
        text_markov_model = fd.read()
        fd.close()
        re_markov_model = re.findall("(.*)->(.*),([0-9]*)\n",
                                     text_markov_model)

        markov_model = {}
        for edge in re_markov_model:
            if edge[0] in markov_model:
                (markov_model[edge[0]]).extend([(edge[1], int(edge[2]))])
            else:
                markov_model[edge[0]] = [(edge[1], int(edge[2]))]
        self.order = edge[0].count("|") + 1

        self.markov_model = markov_model

    def get_next_states(self, role):
        """ Return all possible next states at the current state.  """
        allStates = self.markov_model[self.state]
        if role is not None:
            ret = [s for s in allStates if s[0].endswith(role) or
                   s[0].endswith("END")]
        else:
            ret = allStates
        return ret

    def choose_most_probable_next_state(self, role):
        """ Choose the most probable state """
        next_states = self.get_next_states(role)
        print("Selecting next MOST probable state from: {}".format(next_states))
        sorted_states = [(s, c) for s, c in sorted(next_states,
                                              key=lambda k_v: (k_v[1], k_v[0]))]
        return sorted_states[-1]

    def choose_least_probable_next_state(self, role):
        """ Choose the least probable state """
        next_states = self.get_next_states(role)
        print("Selecting next LEAST probable state from: {}".format(next_states))
        sorted_states = [(s, c) for s, c in sorted(next_states,
                                              key=lambda k_v1: (k_v1[1], k_v1[0]))]
        state = sorted_states[0]
        print("State selected: {}".format(state))
        return state

    def choose_random_next_state(self, role):
        """ Choose the next state randomly. """
        next_states = self.get_next_states(role)
        print("Selecting next state in mode RANDOM from: {}".format(next_states))
        state = choice(next_states)
        print("State selected: {}".format(state))
        return state

    def choose_next_state_OFS(self, role, lens, transition=OFS_TRANSITION):
        """ Choose the next state that optimizes the fuzzing
        testing path in a fixed number of transitions.
        """
        states = {s: 0 for s in self.get_next_states(role)}
        for s in states:
            states[s] += self.get_subtree_weight_OFS(lens, s, transition)

        # Choose the state with the highest OFS weight. If two or more
        # states have the same value, choose randomly between them.
        # Even if all of them have a zero weight, a random choice is made.
        print(">>> Selecting next state in OFS mode...")
        state = choice([k for k, v in list(states.items()) if v is max(states.values())])
        #print states
        print("State selected: {}".format(state))
        return state

    def get_subtree_weight_OFS(self, lens, state, transition=OFS_TRANSITION):
        """ Compute the weight of the subtree that has
        the given state as root. The weight of a subtree is
        the sum of the weights of all the states that can be
        reached from the root in a given number of transitions.
        """
        w = self.get_state_weight_OFS(state[0], lens)
        if transition > 1:
            try:
                states = self.markov_model[state[0]]
            except KeyError:
                states = []
            for s in states:
                w += self.get_subtree_weight_OFS(lens, s, transition-1)
        if transition == 1:
                return w
        return w

    def get_state_weight_OFS(self, state, lens):
        """ Compute the weight of a state. The weight of a state
        is the sum of the remaining fuzzing masks to test
        in all templates associated to this state.
        """
        w = 0
        try:
            ids = lens.tl.state_id[state]
        except KeyError:
            return 0
        for i in ids:
            try:
                w += lens.fuzzer.tracker[i]
            except KeyError:
                pass
        return w


class TemplateList:

    def __init__(self, templates_file, lexerStyle=LEXER_TOKENS):

        self.template_list = self.load_templates(templates_file)
        self.template_dic = {}
        self.state_id = {}
        self.lexerStyle = lexerStyle

        # Build Template dictionaries for later searching
        for template in self.template_list:
            self.template_dic[template.ID] = template
            if template.state in self.state_id:
                self.state_id[template.state].extend([template.ID])
            else:
                self.state_id[template.state] = [template.ID]

    def load_templates(self, templates_file):
        """ Return templates from Prisma output file as
        list of Template objects.
        """
        fd = open(templates_file, "r")
        text_templates = fd.read()
        fd.close()
        templates_str = text_templates.split("TEMPLATE")

        # Load templates structure
        r = re.compile("id:([0-9]*) state:(.*) count:([0-9]*) ntokens:([0-9]*) fields:(.*?)\n(.*)", re.DOTALL)
        template_list = []
        for i in range(1, len(templates_str)):
            template_data = r.findall(templates_str[i])
            ID, state, count, ntokens, fields, content = template_data[0]
            if content == "\n" and ntokens == "1":
                content = [""]
            else:
                # drop the last newline-generated phantom field
                content = content.split("\n")[0:-1]
            new_template = Template(ID, state, count, ntokens, fields, content)
            template_list.append(new_template)
        return template_list

    def getPossibleNextTemplates(self, next_possible_states):
        """ Get matching template and fields of message
        for next possible states.
        """
        ret = []
        # Set matching template and its fields as current template
        for state in next_possible_states:
            try:
                id_list = self.state_id[state[0]]
            except KeyError:
                continue
            for id in id_list:
                template = self.template_dic[id]
                ret.append(template)
        ret.sort(key=lambda t: t.count, reverse=True)
        return ["%s (%d)" % (t.display(), t.count) for t in ret]

    def find_template(self, next_possible_states, message):
        """ Get matching template and fields of message
        for next possible states.
        """

        # Set matching template and its fields as current template
        for state in next_possible_states:
            try:
                id_list = self.state_id[state[0]]
            except KeyError:
                continue
            for id in id_list:
                template = self.template_dic[id]
                matcher = TemplateMessageMatcher(template, message,
                                                 self.lexerStyle)
                fields = matcher.match()
                if fields is not None:
                    return (template, fields)
        return (None, None)

    def find_similar_template(self, next_possible_states, message):
        """ Get most similar template and its fields to a message
        for next possible transitions.
        """

        for state in next_possible_states:
            try:
                id_list = self.state_id[state[0]]
            except KeyError:
                continue
            templates = []
            for id in id_list:
                template = self.template_dic[id]
                matcher = SimilarTemplateMessageMatcher(template, message,
                                                        self.lexerStyle)
                fields, dist = matcher.match()
                templates += [(template, fields, distance)]
            sorted_templates = [(t, f, d) for t, f, d in sorted(templates,
                                              key=lambda t_f_d: (t_f_d[2], t_f_d[0], t_f_d[1]))]
            template, fields = sorted_templates[0][:2]
            return (template, fields)

    def find_next_template(self, state, rl, previousTemplates, interactive):
        """ Find a template according to current state of
        the model and available transitions. If a fuzzer is active
        select only templates with fields. If none of them has fields,
        pick a template as usually.
        """
        # Throw KeyError if state has not id list (END state is reached)
        try:
            id_list = self.state_id[state[0]]
        except KeyError:
            return None
        # Find templates with valid rule transitions and select
        # with a similar distribution to the templates ocurrence probability
        templates_with_rules = []
        for template_id in id_list:
            new_template = self.template_dic[template_id]
            if (not new_template.has_fields()
                    or rl.transition_exists(previousTemplates, new_template)):
                templates_with_rules.append(new_template)
        if len(templates_with_rules) > 0:
            # if a fuzzer is active, choose those templates that
            # has fields. If all are completed or the fuzzer is
            # inactive, pick from all of them as normal.
            fuzz_templates = [t for t in templates_with_rules if t.has_fields()]
            if fuzz_templates:
                templates = fuzz_templates
            else:
                templates = templates_with_rules
            
            templates_ids = [t.ID for t in templates]
            if interactive:
                choice = ""
                while choice not in templates_ids:
                    print("Manually selecting from templates: {}".format(templates_ids))
                    if len(templates_ids) == 1:
                        choice = templates_ids[0]
                    else:
                        choice = input('Selection: ')
                ind = templates_ids.index(choice)
            else:
                print("Probability-based selection from templates: {}".format(templates_ids))
                ind = pickIndex([t.count for t in templates])
            return templates[ind]
        else:
            return None

    def find_next_template_no_rules(self, state, templates_no_fields, interactive):
        try:
            id_list = self.state_id[state[0]]
        except KeyError:
            return None
        templates = []
        fuzz_templates = []
        # find templates with fields
        for template_id in id_list:
            templates += [self.template_dic[template_id]]
        for t in templates:
            if t.has_fields():
                fuzz_templates += [t]
        if not fuzz_templates or templates_no_fields:
            fuzz_templates = templates
        fuzz_templates_ids = [t.ID for t in fuzz_templates]
        if interactive:
            choice = ""
            while choice not in fuzz_templates_ids:
                print("Manually selecting from templates: {}".format(fuzz_templates_ids))
                if len(fuzz_templates_ids) == 1:
                    choice = fuzz_templates_ids[0]
                else:
                    choice = input('Selection: ')
            ind = fuzz_templates_ids.index(choice)
        else:
            print("Probability-based selection from templates: {}".format(fuzz_templates_ids))
            ind = pickIndex([t.count for t in fuzz_templates])
        return fuzz_templates[ind]


class TemplateMessageMatcher:

    def __init__(self, template, msg, lexerType=LEXER_TOKENS,
                 whitespace=" \t\n\r"):
        self.template = template
        self.msg = msg
        self.lexerType = lexerType
        self.ws = whitespace

    def match(self):
        if self.lexerType == LEXER_TOKENS:
            tokens = scanTokens(self.msg, self.ws)
        else:
            tokens = scanNgrams(self.msg)
        if len(tokens) != len(self.template.content):
            # no match due to different token count
            return None
        fields = []
        match = True
        for (tok, msg) in zip(self.template.content, tokens):
            curVal = msg[1]
            # check for field
            if tok == "":
                fields.append(curVal)
            else:
                if urllib.parse.quote(curVal) != tok:
                    match = False
                    break
        if match:
            ret = fields
        else:
            ret = None
        return ret


class SimilarTemplateMessageMatcher:
    """ Return the fields in a template and the distance between this
    template an a given input message.
    """
    def __init__(self, template, msg, lexerType=LEXER_TOKENS,
                 whitespace=" \t\n\r"):
        self.template = template
        self.msg = msg
        self.lexerType = lexerType
        self.ws = whitespace

    def match(self):
        # tokenize the message
        if self.lexerType == LEXER_TOKENS:
            tokens = scanTokens(self.msg, self.ws)
        else:
            tokens = scanNgrams(self.msg)
        fields = []
        for (tok, msg) in zip(self.template.content, tokens):
            curVal = msg[1]
            # check for field
            if tok == "":
                fields.append(curVal)
        # find distance between msg and template
        template_str = ''.join([t for t in self.template.content])
        d = distance(self.msg, template_str)
        return fields, d


class Template:

    def __init__(self, ID="-1", state="", count="0", ntokens="0",
                 fields="", content=[]):
        """ Values in each one of the templates in
        the prisma templates file.
        """

        self.ID = ID
        self.state = state
        self.count = int(count)
        self.ntokens = int(ntokens)
        if fields == "":
            self.fields = []
        else:
            self.fields = [int(f) for f in fields.split(",")]
        self.content = content

    def display(self):
        return str(self).strip()

    def __str__(self):
        tokens = [urllib.parse.unquote(t) if t != "" else "|_|" for t in self.content]
        return "".join(tokens)

    def fillFields(self, fields):
        """ Fill each field in the template with the values in fields.
        If the the fuzzer is active, the content for the new fields
        is fuzzed. If no content for the new fields is given, a random
        value is used to feed the fuzzing primitives.
        """

        fuzz = None
        if self.ID in self.fuzzer.tracker:
            print(self.fuzzer.tracker)
            if self.fuzzer.interactive:
                while fuzz is None:
                    inp = input('Fuzz template {}? [y/n]: '.format(self.ID))
                    if inp == 'y':
                        fuzz = True
                    elif inp == 'n':
                        fuzz = False
            else:
                fuzz = True
            if fuzz:
                self.new_fields = fields
                ret = self.fuzzer.fuzz_template(self)

        if not fuzz:
            ret = self.content[:]
            for (k, v) in fields.items():
                try:
                    ret[self.fields[k]] = v
                except IndexError:
                    print("Warning: trying to assign value to non-existing field")
                    pass
        return ret

    def fillFields(self, fields):
        """ Fill each field in the template with the values in fields.
        """

        ret = self.content[:]
        for (k, v) in fields.items():
            try:
                ret[self.fields[k]] = v
            except IndexError:
                print("Warning: trying to assign value to non-existing field")
                pass

        return ret

    def has_fields(self):
        return len(self.fields) is not 0


class RuleList:

    def __init__(self, rules_file):
        self.load_rules(rules_file)

    def replaceData(self, transition, dst_field, newData):
        for r in self.rules[transition]:
            r.replaceData(transition, dst_field, newData)

    def load_rules(self, rules_file):
        """ Return the rules from the prisma output file
        as list of Rule objects.
        """

        fd = open(rules_file, "r")
        text_rules = fd.read()
        fd.close()
        rules_str = text_rules.split("RULE")

        # Load rules structure
        r = re.compile("transition:([^ ]*) srcId:(.*) srcField:(.*) dstField:(.*) type:(.*?)\n(.*)", re.DOTALL)
        self.rules = {}
        for i in range(1, len(rules_str)):
            rule_data = r.findall(rules_str[i])
            transition, src_id, src_field, dst_field, typ, data = rule_data[0]
            new_rule = Rule(transition, src_id, src_field,
                            dst_field, typ, data)
            self.rules.setdefault(transition, []).append(new_rule)

    def create_message(self, previousTemplates, previousFields, next_template):
        """ Craft a message according to previous templates
        and new selected template.
        """
        transition = self.generateTransitionLabel(previousTemplates,
                                                  next_template)
        # we fill the ids according to neg. index
        # in the transitions, for instance:
        # 23;12;15
        # -3 -2 -1
        # so "-1" is the current message, -2 the previous message and so on.
        fields = dict(list(zip([str(ind) for ind in range(-len(previousFields)-1,
                                                     -1)], previousFields)))
        # Find rules matching current transition
        if transition not in self.rules:
            if not next_template.has_fields():
                current_rules = []
            else:
                return (None, None, None)
        else:
            current_rules = self.rules[transition]
        # Find new fields content according to rules
        dst_fields = {}
        # this is a bit sick... model.py generates the rules in the right
        # sequence, such that all fields in the current message are already
        # filled, if their values are referenced by rules; i.e. we can just
        # add a reference to dst_fields as the "-1" (=current) fields
        fields["-1"] = dst_fields
        for rule in current_rules:
            src_id = rule.src_id
            dst = rule.dst_field
            src = rule.src_field
            if "rule.ExactRule" in rule.typ:
                dst_fields[dst] = fields[src_id][src]
                continue
            if "rule.DataRule" in rule.typ:
                dst_fields[dst] = random.choice(rule.data[5:].split(","))
                continue
            if "rule.CopyCompleteRule" in rule.typ:
                # Copy the exact content of a field 
                if rule.data[6:20] == "COPY_AS_PREFIX":
                    dst_fields[dst] = fields[src_id][src]+random.choice(rule.data[26:].split(","))
                else:
                    dst_fields[dst] = random.choice(rule.data[26:].split(","))+fields[src_id][src]
                continue
            if "rule.CopyPartialRule" in rule.typ:
                # Copy the front or back part of a field splitted
                # by a separator s
                split_data = fields[src_id][src].split(rule.data[26:], 1)
                if rule.data[6:20] == "COPY_THE_PREFIX":
                    if len(split_data) == 2:
                        dst_fields[dst] = split_data[0]
                    else:
                        # we could not split the data with the seperator...
                        # ... so we cannot enter anything at this point
                        dst_fields[dst] = ""
                else:
                    if len(split_data) == 2:
                        dst_fields[dst] = split_data[1]
                    else:
                        # we could not split the data with the seperator...
                        # ... so we cannot enter anything at this point
                        dst_fields[dst] = ""
                continue
            if "rule.SeqRule" in rule.typ:
                try:
                    dst_fields[dst] = int(fields[src_id][src])+int(rule.data[5:])
                except:
                    dst_fields[dst] = 0
                continue

        # Fill new template fields with new content
        message = next_template.fillFields(dst_fields)
        fields = list(dst_fields.items())
        fields.sort(key=operator.itemgetter(0))
        msg = urllib.parse.unquote(''.join(str(n) for n in message))
        return (msg, [f[1] for f in fields], transition)

    def create_fuzzed_message(self, previousTemplates, previousFields,
                              next_template, fuzzer):
        """ Craft a fuzzed message according to previous templates
        and new selected template or a forced transition if a similarity
        based transition has been triggered.
        """
        try:
            transition = self.generateTransitionLabel(previousTemplates,
                                                      next_template)
        except:
            transition = None

        fields = dict(list(zip([str(ind) for ind in range(-len(previousFields)-1,
                                                     -1)], previousFields)))

        template_rules = [r for t, r in list(self.rules.items()) if t.endswith(next_template.ID)]
        rules = [item for sublist in template_rules for item in sublist]
        dst_fields = {}
        fields["-1"] = dst_fields
        fuzz_fields = fuzzer.get_fuzz_fields(next_template.ID)
        non_fuzzed_values = []

        for rule in rules:
            src_id = rule.src_id
            dst = rule.dst_field
            src = rule.src_field
            if "rule.ExactRule" in rule.typ:
                try:
                    data = fields[src_id][src]
                except:
                    data = ""
                dst_fields[dst] = fuzzer.fuzz(rule, data, fuzz_fields)
                continue
            if "rule.DataRule" in rule.typ:
                try:
                    data = random.choice(rule.data[5:].split(","))
                except:
                    data = ""
                dst_fields[dst] = fuzzer.fuzz(rule, data, fuzz_fields)
                continue
            if "rule.CopyCompleteRule" in rule.typ:
                try:
                    if rule.data[6:20] == "COPY_AS_PREFIX":
                        data = fields[src_id][src]+random.choice(rule.data[26:].split(","))
                    else:
                        data = random.choice(rule.data[26:].split(","))+fields[src_id][src]
                except:
                    data = ""
                dst_fields[dst] = fuzzer.fuzz(rule, data, fuzz_fields)
                continue
            if "rule.CopyPartialRule" in rule.typ:
                try:
                    split_data = fields[src_id][src].split(rule.data[26:], 1)
                    if rule.data[6:20] == "COPY_THE_PREFIX":
                        if len(split_data) == 2:
                            data = split_data[0]
                        else:
                            # we could not split the data with the seperator...
                            # ... so we cannot enter anything at this point
                            data = ""
                    else:
                        if len(split_data) == 2:
                            data = split_data[1]
                        else:
                            # we could not split the data with the seperator...
                            # ... so we cannot enter anything at this point
                            data = ""
                except:
                    data = ""
                dst_fields[dst] = fuzzer.fuzz(rule, data, fuzz_fields)
                continue
            if "rule.SeqRule" in rule.typ:
                try:
                    data = int(fields[src_id][src])+int(rule.data[5:])
                except:
                    data = 0
                dst_fields[dst] = fuzzer.fuzz(rule, data, fuzz_fields)
                continue

            #save original not fuzzed values for the log trace
            if len(dst_fields) > dst and dst_fields[dst] == data:
                non_fuzzed_values += [data]

        # Fill new template fields with new content
        message = next_template.fillFields(dst_fields)
        fields = list(dst_fields.items())
        fields.sort(key=operator.itemgetter(0))

        #update tracker
        fuzzer.update_tracker(next_template.ID)
        fuzzer.trace = list(fuzz_fields), non_fuzzed_values
        print("fields_to_fuzz: ", fuzz_fields)
        print(">>> FUZZING msg...")

        return (urllib.parse.unquote(''.join(str(n) for n in message)),
                [f[1] for f in fields], transition)

    def generateTransitionLabel(self, previousTemplates, nextTemplate):
        if len(previousTemplates) == 0:
            transition = nextTemplate.ID
        else:
            transition = "%s;%s" % (";".join([p.ID for p in previousTemplates]), nextTemplate.ID)
        return transition

    def transition_exists(self, previousTemplates, nextTemplate):
        """ Check if there is a valid transition for
        the sequence of templates.
        """
        transition = self.generateTransitionLabel(previousTemplates,
                                                  nextTemplate)
        return transition in self.rules


class Rule:
    """Each one of the rules in the prisma rules file"""
    def __init__(self, transition, src_id, src_field, dst_field, typ, data):
        self.transition = transition
        self.src_id = src_id
        self.src_field = int(src_field)
        self.dst_field = int(dst_field)
        self.typ = typ
        # remove the newline at the end of the data line
        self.data = data.rstrip()

    def replaceData(self, transition, dst_field, newData):
        if (self.transition == transition
           and self.dst_field == dst_field
           and self.src_id == "0"
           and self.src_field == -1
           and self.typ == "rule.DataRule"):
            self.data = "data:%s" % newData


class RingBuffer:
    def __init__(self, size_max):
        self.max = size_max
        self.data = []

    def getLastEntries(self, n):
        if n == 0:
            return []
        else:
            return self.data[-n:]

    def append(self, x):
        """append an element at the end of the buffer"""
        self.data.append(x)
        if len(self.data) == self.max:
            self.cur = 0
            self.__class__ = RingBuffer.__Full

    def get(self):
        """ return a list of elements from the oldest to the newest"""
        return self.data

    class __Full:

        def __init__(self, n):
            raise "you should use RingBuffer"

        def append(self, x):
            self.data[self.cur] = x
            self.cur = (self.cur + 1) % self.max

        def get(self):
            return self.data[self.cur:]+self.data[:self.cur]

        def getLastEntries(self, n):
            if n == 0:
                return []
            else:
                if self.cur >= n:
                    return self.data[(self.cur-n):self.cur]
                else:
                    return self.get()[-n:]

STATUS_OK = "OK"
STATUS_NO_TRANSITION = "NO TRANSITION"
STATUS_END = "END"

MODE_MOST_PROBABLE_TRANSITION = 0
MODE_LEAST_PROBABLE_TRANSITION = 1
MODE_RANDOM_TRANSITION = 2
MODE_FUZZING_TRANSITION = 3


class Lens:

    def __init__(self, modelPath, role, sim_search, mode,
                 lexerStyle, templates_no_fields):
        markov_model, rule_list, template_list = ("%s.markovModel" % modelPath,
                                                  "%s.rules" % modelPath,
                                                  "%s.templates" % modelPath)
        self.modelPath = modelPath
        # MarkovModel object is created
        self.mm = MarkovModel(markov_model)
        # RuleList and Rule objects are created
        self.rl = RuleList(rule_list)
        # TemplateList and Template objects are created
        self.tl = TemplateList(template_list, lexerStyle)
        # Transition mode
        self.mode = int(mode)
        # Reference to fuzzer object
        self.fuzzer = ""
        # Role: client or server (UAC/UAS)
        self.role = role
        if role == "UAC":
            self.otherside = "UAS"
        else:
            self.otherside = "UAC"
        self.templates = RingBuffer(20)
        self.fields = RingBuffer(20)
        self.reset_model()
        # force a transition after receiving a message even if no template
        # is exactly matched by matching the closest template
        self.similarity_search = sim_search
        self.sim_matched_template = False
        # in a fuzzing state, allow selecting templates with no
        # fields to help the model go on
        self.templates_no_fields = templates_no_fields

    def set_fuzzer(self, fuzzer):
        """ Save reference to a fuzzer object and add
        this reference to the markovModel and templates objects.
        """
        self.fuzzer = fuzzer
#        self.mode = MODE_FUZZING_TRANSITION
        self.mm.set_fuzzer(fuzzer)

    def getLastFields(self):
        ret = self.fields.getLastEntries(1)
        if len(ret) == 1:
            return ret[0]
        else:
            return []

    def replaceData(self, transition, dst_field, newData):
        self.rl.replaceData(transition, dst_field, newData)

    def reset_model(self):
        # sets the markov chain to the starting point
        self.mm.init()
        for o in range(self.mm.getOrder()):
            self.templates.append(Template())
            self.fields.append([])

    def consumeOtherSide(self, message):
        """
        consume method for a deployed LENS system
        """
        return self.consume(message, self.otherside)

    def transitionSelf(self):
        """
        This is the modus in which no prefiltering according
        to a fixed role is done, i.e. this is the function a
        deployed LENS system should call
        """
        return self.transition(self.role, True)

    def consume(self, message, role):
        """ Save message, find template and update model state """
        status = STATUS_NO_TRANSITION

        if not(self.mm.getState().endswith("END")):
            # Find matching template for the other side
            next_states = self.mm.get_next_states(role)
            if next_states:
                (template, fields) = self.tl.find_template(next_states, message)
            else:
                # TODO in some cases, next_states is null because only
                # a transition with a message from the other side is possible.
                # By using the role of the otherside and forcing a transition
                # by similarity search the exploration of the model is not blocked.
                if role == self.role:
                    other_role = self.otherside
                else:
                    other_role = self.role
                next_states = self.mm.get_next_states(other_role)
                template = None

            # if similarity search is active, the closest template to the
            # received message is selected.
            if self.similarity_search:
                if template is not None:
                    self.sim_matched_template = False
                    print(">>> EXACT MATCHED TEMPLATE: {}".format(template.ID))
                elif template is None:
                    try:
                        next_OFS_states = []
                        for state in self.mm.get_next_states(role):
                            if self.mm.get_subtree_weight_OFS(self,
                                                              state) > 0:
                                next_OFS_states += [state]
                            if not next_OFS_states:
                                next_OFS_states = self.mm.get_next_states(role)
                        (template, fields) = self.tl.find_similar_template(next_OFS_states,
                                                                           message)
                    except TypeError:
                        (template, fields) = (None, None)
                        status = STATUS_END
                    if template is not None:
                        self.sim_matched_template = True
                        print(">>> SIMILARITY MATCHED TEMPLATE: {}".format(template.ID))

            # wether an exact or a similar matching has been found,
            # the templates and fields are added to the ringBuffer
            # and the state in the model is updated
            if template is not None:
                self.templates.append(template)
                self.fields.append(fields)
                self.mm.update_state(template.state)
                print(">>> TRANSITION TO STATE: {}".format(self.mm.state))
                if template.state.endswith("END"):
                    status = STATUS_END
                else:
                    status = STATUS_OK
            else:
                # Only possible if similarity matching is deactivated or STATUS_END
                if status == STATUS_END:
                    print(">>> END STATE REACHED.")
                else:
                    print(">>> CAN'T MATCH MESSAGE TO TEMPLATE!")
        else:
            status = STATUS_END
        return status

    def transition(self, role, chooseNextStateIndependentFromRole=False):
        """ Trigger selected transition and return
        message or none if waiting.
        """
        status = STATUS_NO_TRANSITION
        if chooseNextStateIndependentFromRole:
            roleForNextState = None
        else:
            roleForNextState = role
        # Select transition mode according to mode initialization
        if self.mode == MODE_MOST_PROBABLE_TRANSITION:
            next_state = self.mm.choose_most_probable_next_state(roleForNextState)
        elif self.mode == MODE_LEAST_PROBABLE_TRANSITION:
            next_state = self.mm.choose_least_probable_next_state(roleForNextState)
        elif self.mode == MODE_RANDOM_TRANSITION:
            next_state = self.mm.choose_random_next_state(roleForNextState)
        elif self.mode == MODE_FUZZING_TRANSITION:
            next_state = self.mm.choose_next_state_OFS(roleForNextState, self)
        else:
            raise "Unknown mode %d" % self.mode

        # we first have to check, whether the chosen
        # state is according to our role...
        if not next_state[0].endswith("END"):
            if chooseNextStateIndependentFromRole and not(next_state[0].endswith(role)):
                next_state = None

        (state, template, msg, fields, transition) = self._transition_to_state(next_state)

        if state is not None and state.endswith("END"):
            # since we have reached the END state, no message is generated...
            status = STATUS_END

        if msg is not None:
            # set the state!
            self.templates.append(template)
            print(">>> SELECTED TEMPLATE: {}".format(template.ID))
            self.fields.append(fields)
            self.mm.update_state(state)
            print(">>> TRANSITION TO STATE: {}".format(self.mm.state))
            status = STATUS_OK

        return (status, msg, transition)

    def _transition_to_state(self, next_state):
        if next_state is not None:
            # iterate here over the possible orders...
            for theOrder in range(self.mm.getOrder(), -1, -1):
                previousTemplates = self.templates.getLastEntries(theOrder)
                previousFields = self.fields.getLastEntries(theOrder)
                if not self.sim_matched_template:
                    next_template = self.tl.find_next_template(next_state,
                                                               self.rl,
                                                               previousTemplates,
                                                               self.fuzzer.interactive)
                else:
                    # If a transition may have been triggered by similarity matching
                    # a special function is called to find a template and create a
                    # message without explicit rules.
                    print(">>> Searching template with no rules")
                    next_template = self.tl.find_next_template_no_rules(next_state,
                                                                        self.templates_no_fields,
                                                                        self.fuzzer.interactive)

                if next_template is not None:
                    break

            if next_template is not None:
                if self.sim_matched_template or self.do_fuzz(next_template):
                    (message, fields,
                     transition) = self.rl.create_fuzzed_message(previousTemplates,
                                                                 previousFields,
                                                                 next_template,
                                                                 self.fuzzer)
                else:
                    (message, fields,
                     transition) = self.rl.create_message(previousTemplates,
                                                          previousFields,
                                                          next_template)
            else:
                message = None
                fields = None
                transition = None
            ret = (next_state[0], next_template, message, fields, transition)
        else:
            ret = (None, None, None, None, None)
        return ret

    def waiting_response(self):
        return not bool(self.mm.get_next_states(self.role))

    def getPossibleNextTemplates(self):
        return self.tl.getPossibleNextTemplates(self.mm.get_next_states(self.otherside))

    def do_fuzz(self, template):
        fuzz = None
        if template.ID in self.fuzzer.tracker:
            if self.fuzzer.interactive:
                while fuzz is None:
                    inp = input('Fuzz template {}? [y/n]: '.format(template.ID))
                    if inp == 'y':
                        fuzz = True
                    elif inp == 'n':
                        fuzz = False
                return fuzz
            else:
                return True
        else:
            return False
