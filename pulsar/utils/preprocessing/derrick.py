#!/usr/bin/python

import sys
import os
import gzip
from progressbar import ProgressBar
from progressbar import Percentage
from progressbar import Bar
from progressbar import ETA

DEFAULT_EXPANSION_COEF = 100


def process(drk_file):
    """ Wrapper to the desired processing function
    """
    unify_ports(drk_file)


def expand(drk_file):
    """ Replicate traffic consecutively and generate new timestamps. This
    allows feeding the learning algorithm a larger amount of data without
    altering their properties.  """

    print(">>> Expanding data...")
    expansion_times = DEFAULT_EXPANSION_COEF
    drk_expanded = "{}.exp".format(drk_file)

    #original file expansion
    cmd = "for i in $(seq 1 {}); do zcat {} >> {}; done".format(expansion_times,
                                                                drk_file,
                                                                drk_expanded)
    os.system(cmd)
    cmd = "gzip {}; mv {}.gz {}".format(drk_expanded,
                                        drk_expanded,
                                        drk_file)
    os.system(cmd)
    fd = gzip.open(drk_file, 'r')
    lines = fd.read().split('\n')[:-1]
    fd.close()

    #each line to a list
    for i in range(len(lines)):
        lines[i] = lines[i].split(' ')

    #random init time
    init_time = float(1406136867.474)

    #rewrite times & randomize deny message
    widgets = ['Reformatting... : ', Percentage(), ' ', Bar(marker='#',
               left='[', right=']'), ' ', ETA(), ' ']
    pbar = ProgressBar(widgets=widgets, maxval=len(lines))
    pbar.start()
    progress = 0
    for i in range(len(lines)):
        try:
            if lines[i][0] == lines[i+1][0]:
                lines[i][0] = init_time + i + 1
            else:
                lines[i][0] = init_time + i
        except:
            lines[i][0] = init_time + i
        progress += 1
        pbar.update(progress)
    pbar.finish()

    #merging and writing
    widgets = ['Merging lines... : ', Percentage(), ' ', Bar(marker='#',
               left='[', right=']'), ' ', ETA(), ' ']
    pbar = ProgressBar(widgets=widgets, maxval=len(lines))
    pbar.start()
    progress = 0
    for i in range(len(lines)):
        lines[i] = ' '.join([str(j) for j in lines[i]])
        progress += 1
        pbar.update(progress)
    pbar.finish()

    extended = '\n'.join(lines)
    fd = gzip.open(drk_file, "w")
    fd.write(extended)
    fd.close()


def unify_ports(drk_file):
    """ Unify IP addresses and ports in the derrick file
        according to their network end point
    """

    #uncompress drk file in tmp file
    drk_tmp = "{}.tmp".format(drk_file)
    cmd = "do zcat {} >> {}; done".format(drk_file, drk_tmp)
    os.system(cmd)
    cmd = "gzip {}; mv {}.gz {}".format(drk_tmp, drk_tmp, drk_file)

    #open file
    os.system(cmd)
    fd = gzip.open(drk_file, 'r')
    lines = fd.read().split('\n')[:-1]
    fd.close()

    #each line to a list
    for i in range(len(lines)):
        lines[i] = lines[i].split(' ')

    widgets = ['Reformatting... : ', Percentage(), ' ', Bar(marker='#',
               left='[', right=']'), ' ', ETA(), ' ']
    pbar = ProgressBar(widgets=widgets, maxval=len(lines))
    pbar.start()
    progress = 0
    for i in range(len(lines)):
        if lines[i][3].endswith("36666"):
            lines[i][3] = "10.0.1.2:36666"
            lines[i][2] = "10.0.1.1:59999"
        else:
            lines[i][2] = "10.0.1.2:36666"
            lines[i][3] = "10.0.1.1:59999"
        #other alternative
        #ip_field = 0
        #if lines[i][2].startswith('10.0.0.5'):
            #ip_field = 2
        #else:
            #ip_field = 3

        #ip = lines[i][ip_field].split(':')
        #ip[1] = '1337'
        #lines[i][ip_field] = ':'.join(ip)
        progress += 1
        pbar.update(progress)
    pbar.finish()

    #merging and writing
    widgets = ['Merging lines... : ', Percentage(), ' ', Bar(marker='#',
               left='[', right=']'), ' ', ETA(), ' ']
    pbar = ProgressBar(widgets=widgets, maxval=len(lines))
    pbar.start()
    progress = 0
    for i in range(len(lines)):
        lines[i] = ' '.join([str(j) for j in lines[i]])
        progress += 1
        pbar.update(progress)
    pbar.finish()

    extended = '\n'.join(lines)
    fd = gzip.open(drk_file, "w")
    fd.write(extended)
    fd.close()


if __name__ == "__main__":
    process(sys.argv[1])
