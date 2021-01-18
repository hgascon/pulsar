#!/usr/bin/env python

"""
Derrick file to universal Derrick file (uharry)

"""
import this
import sys, re, random, socket
import parser
import select
import time
import urllib.request, urllib.parse, urllib.error
from this import s
from gzip import GzipFile
from optparse import OptionParser



if __name__ == "__main__":
    
    usage = "usage: %prog [options] drk-file step "
    parser = OptionParser(usage)
    parser.add_option("-o", "--out", dest="out",
                     default="-",
                     help="input file (default %default)")
    (options, args) = parser.parse_args()    
    if len(args) < 2:
        parser.print_usage()
        sys.exit(1)
        
    
    fd = GzipFile(args[0], 'r')
   
    #aux buffer for new modified file
    output=""   
    #aux dict with keys src_dst combination and its corresponding line of the file as value.
    src_dst_dic={}
    #aux boolean dict with keys src_dst combination. 0=no response from DST yet, 1=response from DST for the last src_dst message.
    response={}
    #adjustable step time for messages in the same session
    step = float(args[1])
    
    while 1:
        line = fd.readline()
        #if script gets to the end of file and line is empty, break the loop
        if line == "": break
        line = line.split(' ')
        src_dst = line[2]+"_"+line[3]
        dst_src = line[3]+"_"+line[2]
        line[4] = (' '.join(str(n) for n in line[4:])).replace("\n","")
        line = line[0:5]
        
        #check if there's an entry for this combination of SRC and DST
        if src_dst in src_dst_dic:
            
            if response[src_dst] == 0 and float(line[0]) - float(src_dst_dic[src_dst][0]) < step:
                src_dst_dic[src_dst][4] += line[4]
            else:
                output += ' '.join(src_dst_dic[src_dst])+"\n"
                src_dst_dic[src_dst] = line
                response[src_dst] = 0
       
        #if the combination SRC DST isnt read yet, it is added and response is set to 0
        else:
            src_dst_dic[src_dst] = line
            response[src_dst] = 0
        
        #check if there's an entry for the combination of DST to SRC in order to set RESPONSE to 1 for this combination
        if dst_src in src_dst_dic:
            response[dst_src] = 1        
             
    fd.close()
    
    filename = args[0][0:-3]+"udrk"
    fd = GzipFile(filename, 'wb')
    fd.write(output)
    fd.close()
    print("Generated file: "+filename)

