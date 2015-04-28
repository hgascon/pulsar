#!/bin/bash

# Setup the network in linux to allow virtual machines
# access the internet from a host-only connection
# between the VM and Cuckoo sandbox.
# Call with the interface connected to the internet
# as parameter

[ $# -eq 0 ] && { echo "Usage: $0 <interface> <0/1>"; exit 1; }

# verify that vboxnet0 is up
VBoxManage list vms
ifconfig vboxnet0 192.168.56.1

if [ $2 == '1' ]
then
    iptables -A FORWARD -o $1 -i vboxnet0 -s 192.168.56.0/24 -m conntrack --ctstate NEW -j ACCEPT
    iptables -A FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
    iptables -A POSTROUTING -t nat -j MASQUERADE
    sysctl -w net.ipv4.ip_forward=1
fi

if [ $2 == '0' ]
then
    iptables -D FORWARD -o $1 -i vboxnet0 -s 192.168.56.0/24 -m conntrack --ctstate NEW -j ACCEPT
    iptables -D FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
    iptables -D POSTROUTING -t nat -j MASQUERADE
    sysctl -w net.ipv4.ip_forward=0
fi
