#!/usr/bin/python

""" This module parses a tcpflow output file and
    to generate a new file with derrick format.
    The tcpflow version used includes timestamps and 
    date printing. It can be found in:
    https://github.com/mukhin/tcpflow
"""

import os
import sys
import datetime
import urllib.request, urllib.parse, urllib.error
import gzip


def unix_time(dt):
    epoch = datetime.datetime.utcfromtimestamp(0)
    delta = dt - epoch
    return delta.total_seconds()


def unix_time_millis(dt):
    return unix_time(dt) * 1000.0


def rreplace(s, old, new, occurrence):
    li = s.rsplit(old, occurrence)
    return new.join(li)

files = sys.argv[1:]
drk_dic = {}
for f in files:
    src = rreplace(os.path.basename(f).split('-')[0], '.', ':', 1)
    dst = rreplace(os.path.basename(f).split('-')[1], '.', ':', 1)
    fd = open(f, 'r')
    lines = fd.read().split('\n')
    fd.close()
    last_seen_time = 0000000000000.000
    for line in lines:
        try:
            ts = line[:15].split(':')
            msg = urllib.parse.quote(line[16:])
            msg = msg.replace("%20", " ")
            d = datetime.datetime(2014, 6, 1,
                                  int(ts[0]),
                                  int(ts[1]),
                                  int(ts[2].split('.')[0]),
                                  int(ts[2].split('.')[1]))
            d = unix_time_millis(d)
            last_seen_time = d
            drk_dic[d] = ' '.join(['T', src, dst, msg])
        except Exception as e:
            print(e)
            if last_seen_time in drk_dic:
                prev_line = drk_dic[last_seen_time]
                drk_dic[last_seen_time] = urllib.parse.quote('\r\n').join([prev_line,
                                                                     msg])
            else:
                drk_dic[last_seen_time] = ' '.join(['T', src, dst, msg])

fd = gzip.open("file.drk", "w")
keys = list(drk_dic.keys())
keys.sort()
for k in keys:
    if k == 0:
        timestamp = "0000000000000.000"
    else:
        timestamp = "%13.3f" % k
    line = "{} {}\n".format(timestamp, drk_dic[k])
    fd.write(line)
fd.close()
