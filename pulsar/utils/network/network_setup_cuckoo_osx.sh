#!/bin/bash

# Setup the network in OSX to allow virtual machines
# access the internet from a host-only connection
# between the VM and Cuckoo sandbox.
# Call with the interface connected to the internet
# as parameter

[ $# -eq 0 ] && { echo "Usage: $0 interface 0/1"; exit 1; }

if [ $2 == '1' ]
then
    sysctl -w net.inet.ip.forwarding=1
    natd -interface $1
    ipfw add divert natd ip from any to any via $1
fi

if [ $2 == '0' ]
then
    echo "TODO: find a way to deactivate this"
fi
