#!/bin/bash

for i in `cat /proc/net/ip_tables_names`; do echo ""; echo "TABLE: $i <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<"; echo "";  iptables -nL -v --line-numbers -t $i ; done
