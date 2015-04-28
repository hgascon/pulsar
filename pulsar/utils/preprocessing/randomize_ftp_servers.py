#!/usr/bin/python

import sys
from random import randrange

""" This script modifies each '227 Entering Passive Mode (...)' FTP message
with a random IP. In this way, it seems like each connection has been
established between the same client and a different server and PRISMA will
model the values in (...) as a field but not the parenthesis.
"""

file_name = sys.argv[1]
drk_list = open(file_name, 'r').read().split(' ')
for i in range(len(drk_list)):
    if drk_list[i].startswith("(10,0,0,2"):
        newip = '(' + ','.join([str(randrange(254)) for j in range(4)])
        elements = drk_list[i].split(',2,')
        elements[0] = newip
        drk_list[i] = ','.join(elements)

drk = ' '.join(drk_list)
drk = drk.replace("\n", "\r\n")
f = open(file_name, 'w')
f.write(drk)
