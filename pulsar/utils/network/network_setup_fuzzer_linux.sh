#!/bin/bash

# Setup the network in linux to sinkhole virtual machines
# to the local ip of the fuzzer from a host-only connection
# between the VM and Cuckoo sandbox.
# Call with the interface connected to the internet and 
# where the fuzzer should be listeing as parameter

[ $# -eq 0 ] && { echo "Usage: $0 interface 0/1"; exit 1; }

# set the fuzzer interface
ifconfig $1 10.0.0.3/24

# verify that vboxnet0 is up
VBoxManage list vms
ifconfig vboxnet0 192.168.56.1

if [ $2 == '1' ]
then
    iptables -A FORWARD -o $1 -i vboxnet0 -s 192.168.56.0/24 -m conntrack --ctstate NEW -j ACCEPT
    iptables -A FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
    #iptables -t nat -A PREROUTING -s 192.168.56.101 ! -d 192.168.56.1 -p udp -j DNAT --to-destination 10.0.0.1:80
    iptables -t nat -A PREROUTING -s 192.168.56.101 ! -d 192.168.56.1 -p tcp -j DNAT --to-destination 10.0.0.3:80
    iptables -t nat -A PREROUTING -s 192.168.56.102 ! -d 192.168.56.1 -p tcp -j DNAT --to-destination 10.0.0.3:80
    iptables -t nat -A PREROUTING -s 192.168.56.103 ! -d 192.168.56.1 -p tcp -j DNAT --to-destination 10.0.0.3:80
    iptables -A POSTROUTING -t nat -j MASQUERADE
    sysctl -w net.ipv4.ip_forward=1
fi

if [ $2 == '0' ]
then
    iptables -D FORWARD -o $1 -i vboxnet0 -s 192.168.56.0/24 -m conntrack --ctstate NEW -j ACCEPT
    iptables -D FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
    #iptables -t nat -D PREROUTING -s 192.168.56.101 ! -d 192.168.56.1 -p udp -j DNAT --to-destination 10.0.0.1:80
    iptables -t nat -D PREROUTING -s 192.168.56.101 ! -d 192.168.56.1 -p tcp -j DNAT --to-destination 10.0.0.3:80
    iptables -t nat -D PREROUTING -s 192.168.56.102 ! -d 192.168.56.1 -p tcp -j DNAT --to-destination 10.0.0.3:80
    iptables -t nat -D PREROUTING -s 192.168.56.103 ! -d 192.168.56.1 -p tcp -j DNAT --to-destination 10.0.0.3:80
    iptables -D POSTROUTING -t nat -j MASQUERADE
    sysctl -w net.ipv4.ip_forward=0
fi
