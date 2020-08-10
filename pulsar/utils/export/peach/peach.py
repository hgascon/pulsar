#!/usr/bin/env python3
# To change this license header, choose License Headers in Project Properties.
# To change this template openFile, choose Tools | Templates
# and open the template in the editor.

__author__="dasmoep"
__date__ ="$Jun 23, 2014 5:01:41 PM$"

import os

#will once contain the history leading to some state
#{state:[preTemp:curTemp:nextTemp]}
history = {}

#will once contain names of states and there history to construct names ofdatamodel!
#[hist1 state1, hist2 state2,...]
dataModelNames = []

#will once contain all identified states
#[[state,[nextState1,nextState2,...]],...]
allStates = []

#also not proud of
#will contain a list of to be written END STATES, as they seem to be special...
endStates = []

#not the least proud of...
writtenStates = []
writtenModels = []

def createPIT(path=None):
    #handle where we are
    if path==None:
        path= os.getcwd()
    #handle construction of StateModel
    f= openFile(path,'muster','r')
    #g= openFile(path,'pit','w') 
    g= open(path+'/'+'prePit','w')
    for line in f:
        g.write(line)
        #if 'Create data model' in line:
            #insertDataModel(path,g)
        if '<StateModel name="TheState"' in line:
            insertStateModel(path,g)
        
    g.close()
    f.close()
    #for i,j in history.items():
     #   print(i,j)
    #handle construction of DataModel
    #print( dataModelNames)
    f= openFile(path,'prePit','r')
    g=open(path+'/'+'pit.xml','w')
    for line in f:
        g.write(line)
        if 'Create data model' in line:
            insertDataModel(path,g)
    g.close()
        
def insertStateModel(path,pitFile):
    f=openFile(path,'markov','r')
    #for each state find all transitions
    states= []
    flag=1
    for line in f:
        for i in range(len(states)):
            if line.split('->')[0] in states[i][0]:
                states[i][1].append(line.split('->')[1])
                flag=0
                break
        if flag==1:
            states.append([line.split('->')[0],[line.split('->')[1]]])
        flag=1
    f.close()
    
    #states=getMostProbable(path,states)
    allStates = states[:]
    while states != []:
        #print(states)
        writtenState = ''
        for i in states:
            #newState = True
            writtenState, possibleNewStates = gsecStates2Peach(i, path, pitFile)
            #writtenStates.append(gsecStates2Peach(i,path,pitFile))
            #print(possibleNewStates)
            for i in writtenStates:
                if i != []:
                    #print(i.split('\n')[0]) 
                    if possibleNewStates != []:
                        #print(possibleNewState[0] in i.split('\n')[0])
                        copy = possibleNewStates[:]
                        for s in copy:
                            if s in i.split('\n')[0]:
                                possibleNewStates.remove(s)
            if possibleNewStates != []:
                #print('Hurray!')
                for s in possibleNewStates:
                    for i in allStates:
                        if s.split()[1] == i[0]:
                            #print(i)
                            states.append(i)
            if writtenState != 'void':
                states.remove(writtenState)
    #for i in endStates:
        #print(i)
    writeEndStates(endStates,pitFile)
    return
      
def insertDataModel(path, pitFile):
    f=openFile(path,'template','r')
    s= ''
    flag=0
    for line in f:
        #due to nature of TEMPLATE-file-format read text up to SECOND TEMPLATE in text and THEN work out the FIRST
        if 'TEMPLATE' in line and flag==1:
            gsecData2Peach(s,path,pitFile)
            s= ''
        s+= line
        flag=1
    gsecData2Peach(s,path,pitFile)
    f.close()
    return

            

def gsecStates2Peach(s,path,pitFile):
    #print(history)
    #print(s) 
    #print(s[1][0].split(',')[0],history,s[1][0].split(',')[0] in history) 
    if s[0] != 'START|START':
        if s[0] not in history:
            return 'void',[]
    #first find potential DataModels(templates) to be output by this state:
    f=openFile(path,'template','r')
    models=[]
    allModels=[]
    for line in f:
        if 'TEMPLATE' in line:
            t=line.split()
            allModels.append(t[1]+' '+t[2].split(':')[1])
            if t[2].split(':')[1]==s[0]:
                models.append(t[1]+' '+t[2].split(':')[1])
    f.close()
    if len(models) > 1:
        models = getMostProbable(path,models)
    nextStates = []
    nextModels=[]
    for nextState in s[1]:
        #print(models,s,i)
        nextState=nextState.split(',')[0]
        if not 'END' in nextState:
            f=openFile(path,'template','r')
            for line in f:
                if 'TEMPLATE' in line:
                    t=line.split()
                    #allModels.append(t[1]+' '+t[2].split(':')[1])
                    if t[2].split(':')[1]==nextState:
                        nextModels.append(t[1]+' '+t[2].split(':')[1])
            f.close()
        #print('NEXTMODELS:',nextModels,s)
        #mostProbableNextModel=getMostProbable(path,nextModels)
        #print(mostProbableNextModel)
        #retChange += '\t\t\t<Action type=\"changeState\" ref=\"'+nextState+'\" when=\"???\"></Action>\n'
        nextStates.append(nextState)
        #ret += '\t\t\t' +i+'\n'
    
    retFinal= '\t\t</State>\n'
    #compose state's real name
    if s[0] == 'START|START':
        if models != []:
            hist = "-1:-1:"+models[0]
            #retName= '\t\t<State name="-1:-1:'+m[0]+s[0]+'">\n'
            
        else:
            hist = "-1:-1:-1"
            #retName= '\t\t<State name="-1:-1:-1 '+s[0]+'">\n'
        preHist='-1:-1:-1'
    else:
        #if len(history[s[0]])>1:
            #print('>>>',s,models[0],history)
        #HAVE TO FIND RIGHT HISTORY HERE, IF MORE THAN ONE AVAILABLE
        hist = history[s[0]][-1].split(':')
        preHist=hist[0]+':'+hist[1]+':'+hist[2]
        #print('>>>',preHist)
        #print(models[0])
        hist = hist[1]+':'+hist[2]+':'+models[0].split()[0].split(':')[1]
        #print('...',hist,preHist)
        retName = '\t\t<State name="'+hist+' '+s[0]+'">\n'
    for i in nextStates:
        #print('>>>',i,s,hist)
        if i in list(history.keys()) and history[i]!=hist:
            #print('>>>>>>',history[i]+[1])
            #print('CRITICAL WARNING!')
            #print(i,hist,history[i])
            history.update({i:history[i]+[hist]})
            #print(i,hist,history[i])
        else:
            history.update({i:[hist]})
    if hist+' '+s[0] not in dataModelNames:
        dataModelNames.append(hist+' '+s[0])
    #print('PPPPPPPPPPPPPP',dataModelNames)
    retName = '\t\t<State name="'+hist+' '+s[0]+'">\n'

    #print(s[0],hist,preHist)
#deal with slurp AND output/input actions
    if 'START|START' in s[0] or 'UAC' in s[0].split('|')[0]:
        #get slurp action
        retSlurp= '\t\t\t<!-- find slurp Action -->\n'
        slurpAction = slurp(path,hist,preHist)
        if slurpAction != '':
            retSlurp += slurpAction
        else: retSlurp += '\t\t\t<!-- No slurp Action found -->\n'
        retData= '\t\t\t<!-- DataModel to be send -->\n'
        #for i in models:
        if not ('START|START' in s[0] and hist.split(':')[2]=='-1'):
            retData += '\t\t\t<Action type="output"><DataModel ref="'+hist+'"/></Action>\n'
    #client receives from server 
    else:
        #ToDo insert slurping here as well!
        retSlurp= '\t\t\t<!-- find slurp Action -->\n'
        slurpAction = slurp(path,hist,preHist)
        if slurpAction != '':
            retSlurp += slurpAction
        else: retSlurp += '\t\t\t<!-- No slurp Action found -->\n'
        #for i in models:
        retData = '<!-- DataModel to be received -->\n'
        retData += '\t\t\t<Action type="input"><DataModel ref="'+hist+'"/></Action>\n'
    retData += '\t\t\t<!-- possible next States -->\n'

    #deal with changeState actions
    retChange=''
    #print(s,len(nextStates))
    numNextStates=0
    for i in nextStates:
        #if 'END' not in i:
        numNextStates+=1
    possibleNewStates = []
    for nextState in nextStates:
        #mostProbableNextModel=getMostProbable(path,nextModels)
        #print( nextState,history[nextState],nextModels)
        possibleNextModels = []
        for i in nextModels:
            if i.split()[1]==nextState:
                possibleNextModels.append(i)
        #if 'END' in nextState:
            #print(s,nextState,possibleNextModels,hist) 
        mostProbNextModel=getMostProbable(path,possibleNextModels)
        #print('MOST PROB!',mostProbNextModel)
        #print(history,hist)
        hist = history[nextState][-1].split(':')
        #print('HIST',hist)
        if 'END' in nextState:
            #print(hist)
            writeHist = hist[1]+':'+hist[2]+':'+'00'
            when = ' when="'
            if numNextStates != 1:
                when += 'random.randint(0,'+str(numNextStates-1)+') == 0"'
                numNextStates -= 1
            else:
                when = ''
            retChange += '\t\t\t<Action type=\"changeState\" ref=\"'+writeHist+' '+nextState+'\"'+when+'></Action>\n'
            if not writeHist +' '+ nextState in endStates:
                endStates.append(writeHist +' '+ nextState)
        elif mostProbNextModel != []:
            when = ' when="'
            if numNextStates != 1:
                when += 'random.randint(0,'+str(numNextStates-1)+') == 0"'
                numNextStates -= 1 
            else:
                when = ''
            writeHist = hist[1]+':'+hist[2]+':'+mostProbNextModel[0].split()[0].split(':')[1]
            #print('>>>>>>>>>>')
            #print(writeHist)
            #print(s,hist,preHist,nextState)
            #print(history)
            #print()
            #print('>>>>> error here!')
            #print(writeHist,nextState)
            retChange += '\t\t\t<Action type=\"changeState\" ref=\"'+writeHist+' '+nextState+'\"'+when+'></Action>\n'
            possibleNewStates = [writeHist +' '+ nextState]
        #else: hist = 'bla?!'
        #retChange += '\t\t\t<Action type=\"changeState\" ref=\"'+hist+' '+nextState+'\" when=\"???\"></Action>\n'
    #print(possibleNewStates)
    state = retName+retSlurp+retData+retChange+retFinal
    #print(state in writtenStates)
    if state in writtenStates:
        return s,possibleNewStates
    pitFile.write(state)
    writtenStates.append(state)
    return s,possibleNewStates

def writeEndStates(states,pitFile):
    for s in states:
        retName = '\t\t<State name="'+s+'">\n'
        retFinal= '\t\t</State>\n'
        ret = retName + retFinal
        pitFile.write(ret)

def gsecData2Peach(s,path,pitFile):
    s=s.split('\n')
    t=s[0].split()
    fieldsToFill = t[-1].split(':')[1].split(',')
    for observedModel in dataModelNames:
        ret=''
        if observedModel.split()[0].split(':')[2]==t[1].split(':')[1]:
            ret= '\t<DataModel name=\"'+observedModel.split()[0]+'\">\n'
            i = 0
            for field in s[1:-1]:
                if field == '':
                    dataRule=isDataRuleAvailable(observedModel.split()[0],i,fieldsToFill.index(str(i)),path)
                    if dataRule != []:
                        ret+= '\t\t<Choice name="'+str(i)+'" minOccurs="1" maxOccurs="1">\n'
                        j=0
                        for data in dataRule:
                            ret+= '\t\t\t<String name="'+str(j)+'" value="'+str(data)+'"/>\n'
                            j+=1
                        ret+= '\t\t</Choice>\n'
                    else:
                        ret+= '\t\t<String name="'+str(i)+'" value="non-DataRule EXISTS"/>\n'
                else:
                    ret+='\t\t<String name="'+str(i)+'" value=\"'+field+'\"/>\n'
                i+=1
            ret+= '\t</DataModel>\n'
        pitFile.write(ret)
    return #ret

def getMostProbable(path,models):
    #print('IN GETMOST')
    #print(models)
    if models == []:
        return []
    if len(models) == 1:
        return models
    mostModel = None
    f = openFile(path,'template','r')
    for m in models:
        for line in f:
            if 'TEMPLATE id:'+m.split()[0].split(':')[1] in line:
                count=line.split()[3].split(':')[1]
                break
        if mostModel==None:
            mostModel=(m,count)
        else:
            if count > mostModel[1]:
                mostModel=(m,count)
    f.close()
    #print(mostModel)
    return [mostModel[0]]

def slurp(path,hist,preHist):
    #print(models,dataModelNames)
    ret = ''
    f=openFile(path,'rules','r')
    #find out whether template can be filled or not; IGNORE preState!?NOOOOOO
    #OF COURSE NOT; CONVOLUTE STATEMODEL WITH PREVIOUS SENT MESSAGE ID!
    for line in f:
        #search RULES for non-DATA rules
        if 'RULE' in line and 'DataRule' not in line and hist.replace(':',';') in line:
            #print(hist,preHist,line)
            t=line.split()
            #print(t[1].split(':')[1],preHist.replace(':',';'))
                #print(True)
            fromDataModel= preHist
            fromAttributeName= t[3].split(':')[1]
            toDataModel= hist
            toAttributeName= t[4].split(':')[1]
            ret+= '\t\t\t<Action type ="slurp" valueXpath="//'+str(fromDataModel)+'//'+fromAttributeName+'//Value" setXpath="//'+toDataModel+'//'+toAttributeName+'//Value"/> \n'
    f.close()
    return ret
    f.close()
    return ret

def isDataRuleAvailable(id,field,relField,path):
    #return [1,2,3]
    ret=[]
    f=openFile(path,'rules','r')
    flag=0
    for line in f:
        if 'RULE' in line and 'DataRule' in line:
            t = line.split()
            #print(t[1].split(';')[2],id,field,t[4].split(':')[1])
            #print (t)
            #print(id,t[1].split(';')[2],type(field),type(t[4].split(':')[1]),field==t[4].split(':')[1])
            #t[1][2] TEMPLATE to be filled (ID)
            if t[1].split(':')[1] == id.replace(':',';') and t[4].split(':')[1] == str(relField):
                #print('found DataRule')
                flag=1
                continue
        if flag == 1:
            #print('found fitting DataModel')
            for t in line.split(','):
                #maybe not accurate!
                if 'data:' in t:
                    t=t.split(':')[1]
                ret.append(t.split('\n')[0])
            flag = 0
    f.close()
    #print (ret)
    return ret

def openFile(path,name,mode):
    for f in os.listdir(path):
        if name in f:
            f=open(path+'/'+f,mode)
            return f

if __name__ == "__main__":
    #print ("Hello World!")
    createPIT()
