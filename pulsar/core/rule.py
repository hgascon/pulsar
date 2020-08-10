import urllib.request, urllib.parse, urllib.error

# controls, when a partial match is considered for a rule,
# i.e. a partial match must have at least length PARTIAL_MATCH_LEN to be
# considered for a partial match rule
PARTIAL_MATCH_LEN = 3

EXACT_THRESHOLD = .9
SEQ_THRESHOLD = .9
COPY_COMPLETE_THRESHOLD = .9
COPY_PARTIAL_THRESHOLD = .9

class RuleSet:

    def __init__(self, fingerprint, templateIds):
        self.fingerprint = fingerprint
        self.templateIds = templateIds

    def gatherRules(self, fieldsForMessages, isNgramProcessing):
        total = len(fieldsForMessages)
        target = fieldsForMessages[-1]
        targetId = self.templateIds[-1]
        self.rules = []
        fieldsToFill = list(range(target.getNumberOfFields()))
        if isNgramProcessing:
            theRules = [ExactRule, SeqRule]
        else:
            theRules = [ExactRule, SeqRule, CopyCompleteRule, CopyPartialRule]
        for currentRule in theRules:
            # we start with the nearest message in time and then go backwards:
            for index in range(-2, -total-1, -1):
                source = fieldsForMessages[index]
                sourceId = self.templateIds[index]
                for fromField in range(source.getNumberOfFields()):
                    for toField in fieldsToFill[:]:
                        r = currentRule(index, targetId, fromField, toField)
                        if r.isValid(source.getValuesForField(fromField),
                                     target.getValuesForField(toField)):
                            # we found a matching rule
                            self.rules.append(r)
                            fieldsToFill.remove(toField)
        # find rules inside the message itself
        index = -1
        source = fieldsForMessages[index]
        selfRules = []
        for currentRule in theRules:
            for fromField in fieldsToFill[:]:
                if fromField not in fieldsToFill:
                    # it's already deleted from fieldToFill...
                    # so we have nothing to do!
                    continue
                for toField in fieldsToFill[:]:
                    if fromField == toField:
                        continue
                    r = currentRule(index, targetId, fromField, toField)
                    if r.isValid(source.getValuesForField(fromField),
                                 target.getValuesForField(toField)):
                        # we found a matching rule
                        selfRules.append(r)
                        fieldsToFill.remove(toField)
        # ensure, that everything is filled in the correct order...
        alreadyFilled = fieldsToFill[:]
        orderedSelfRules = []
        while len(selfRules) > 0:
            for r in selfRules[:]:
                if r.sourceField in alreadyFilled:
                    orderedSelfRules.append(r)
                    selfRules.remove(r)
                    alreadyFilled.append(r.targetField)
        # fill the remaining fields with the data
        for toField in fieldsToFill:
            r = DataRule(0, targetId, -1, toField)
            r.isValid(None, target.getValuesForField(toField))
            self.rules.append(r)
        self.rules.extend(orderedSelfRules)

    def __str__(self):
        return "\n".join([str(r) for r in self.rules])

class Rule:

    def __init__(self, sourceId, targetId, sourceField, targetField):
        self.sourceId = sourceId
        self.targetId = targetId,
        self.sourceField = sourceField
        self.targetField = targetField

    def getSpecificSaveString(self):
        raise Exception


class ExactRule(Rule):

    def __str__(self):
        return "Exact %s -> %s" % (self.sourceField, self.targetField)

    def isValid(self, sourceVals, targetVals):
        similar = sum([s == t for (s, t) in zip(sourceVals, targetVals)])
        return similar >= (EXACT_THRESHOLD * len(sourceVals))

    def getSpecificSaveString(self):
        return ""

class SeqRule(Rule):

    def __str__(self):
        return "Seq %s -> %s" % (self.sourceField, self.targetField)

    def isValid(self, sourceVals, targetVals):
        similar = [False] * len(sourceVals)
        for index in range(len(sourceVals)):
            if sourceVals[index].isdigit() and targetVals[index].isdigit():
                similar[index] = ((int(targetVals[index]) - int(sourceVals[index])) == 1)
        similar = sum(similar)
        return similar >= (SEQ_THRESHOLD * len(sourceVals))

    def getSpecificSaveString(self):
        return "diff:1"

SOURCE_IS_PREFIX = 1
SOURCE_IS_SUFFIX = 2
"""
Copy the complete source field to the target field
and add the rest as suffix, if the ptype is COPY_AS_PREFIX,
and add the rest as prefix, if the COPY_AS_SUFFIX.
"""
class CopyCompleteRule(Rule):

    def __str__():
        pass

    def isValid(self, sourceVals, targetVals):
        nvalues = len(sourceVals)
        similar = [0] * nvalues
        for index in range(nvalues):
            curVal = 0
            if len(sourceVals[index]) >= PARTIAL_MATCH_LEN:
                if targetVals[index].startswith(sourceVals[index]):
                    curVal = SOURCE_IS_PREFIX
                elif targetVals[index].endswith(sourceVals[index]):
                    curVal = SOURCE_IS_SUFFIX
            similar[index] = curVal
        threshold = COPY_COMPLETE_THRESHOLD * nvalues
        ret = False
        if sum([s == SOURCE_IS_PREFIX for s in similar]) >= threshold:
            self.ptype = "COPY_AS_PREFIX"
            self.rest = [t[len(s):] for (s, t, i) in
                         zip(sourceVals, targetVals, range(nvalues))
                         if similar[i] == SOURCE_IS_PREFIX]
            ret = True
        elif sum([s == SOURCE_IS_SUFFIX for s in similar]) >= threshold:
            self.ptype = "COPY_AS_SUFFIX"
            self.rest = [t[0:(len(t)-len(s))] for (s, t, i) in
                         zip(sourceVals, targetVals, range(nvalues))
                         if similar[i] == SOURCE_IS_SUFFIX]
            ret = True
        return ret

    def getSpecificSaveString(self):
        return "ptype:%s rest:%s" % (self.ptype, ",".join(map(urllib.parse.quote, self.rest)))


TARGET_IS_PREFIX = 1
TARGET_IS_SUFFIX = 2
"""
Copy just a part of the source field to the target field, namely
parse the source until the sep is found (i.e. we have source = prefix sep suffix ), and 
then copy the prefix, if ptype is COPY_THE_PREFIX,
or copy the suffix, if ptype is COPY_THE_SUFFIX.
"""
class CopyPartialRule(Rule):

    def __str__():
        pass

    @staticmethod
    def findLongestCommonStart(rest):
        toCheck = 0
        pivot = rest[0]
        smallestSize = min([len(r) for r in rest])
        while True:
            if toCheck == smallestSize or \
                   any([r[toCheck] != pivot[toCheck] for r in rest]):
                return pivot[0:toCheck]
            toCheck += 1

    @staticmethod
    def findLongestCommonEnd(rest):
        toCheck = -1
        pivot = rest[0]
        smallestSize = -min([len(r) for r in rest]) - 1 
        while True:
            if toCheck == smallestSize or \
                   any([r[toCheck] != pivot[toCheck] for r in rest]):
                if toCheck == -1:
                    return ""
                else:
                    return pivot[(toCheck+1):]
            toCheck -= 1

    def isValid(self, sourceVals, targetVals):
        nvalues = len(sourceVals)
        similar = [0] * nvalues
        for index in range(nvalues):
            curVal = 0
            if len(targetVals[index]) >= PARTIAL_MATCH_LEN:
                if sourceVals[index].startswith(targetVals[index]):
                    curVal = TARGET_IS_PREFIX
                elif sourceVals[index].endswith(targetVals[index]):
                    curVal = TARGET_IS_SUFFIX
            similar[index] = curVal
        threshold = COPY_PARTIAL_THRESHOLD * nvalues
        ret = False
        if sum([s == TARGET_IS_PREFIX for s in similar]) >= threshold:
            self.ptype = "COPY_THE_PREFIX"
            rest = [s[len(t):] for (s, t, i) in
                    zip(sourceVals, targetVals, range(nvalues))
                    if similar[i] == TARGET_IS_PREFIX]
            self.sep = self.findLongestCommonStart(rest)
            ret = (self.sep != "")
        elif sum([s == TARGET_IS_SUFFIX for s in similar]) >= threshold:
            self.ptype = "COPY_THE_SUFFIX"
            rest = [s[0:(len(s)-len(t))] for (s, t, i) in
                    zip(sourceVals, targetVals, range(nvalues))
                    if similar[i] == TARGET_IS_SUFFIX]
            self.sep = self.findLongestCommonEnd(rest)
            ret = (self.sep != "")
        return ret

    def getSpecificSaveString(self):
        return "ptype:%s sep:%s" % (self.ptype, urllib.parse.quote(self.sep))

class DataRule(Rule):

    def __str__(self):
        return "Data: %s" % ",".join(self.model)

    def isValid(self, sourceVals, targetVals):
        self.model = targetVals
        return True

    def getSpecificSaveString(self):
        return "data:%s" % (",".join(map(urllib.parse.quote, self.model)))
