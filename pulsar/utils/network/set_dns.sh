#!/bin/bash
ifconfig eth0:2 8.8.8.8/24
dnsmasq -a 8.8.8.8 -h --address=/#/10.0.0.3
