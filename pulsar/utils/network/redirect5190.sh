#!/bin/bash

if [ $1 == '1' ]
then
    iptables -t nat -A OUTPUT -p tcp -d 178.237.19.22 --dport 5190 -j DNAT --to-destination 10.0.0.2:5190
    iptables -A POSTROUTING -t nat -j MASQUERADE
    sysctl -w net.ipv4.ip_forward=1
fi

if [ $1 == '0' ]
then
    iptables -t nat -D OUTPUT -p tcp -d 178.237.19.22 --dport 5190 -j DNAT --to-destination 10.0.0.2:5190
    iptables -D POSTROUTING -t nat -j MASQUERADE
    sysctl -w net.ipv4.ip_forward=0
fi
