
## PULSAR
#### Protocol Learning, Simulation and Stateful Fuzzer

### Functions

    - Generate model from a PCAP -m  -f file.pcap
    - Simulate communication -s -m model_file
    - Start a fuzzing session -z -m model_file

### to remember

    - different options to give a pcap as input:
        - 1 pcap
        - several pcaps same binary (cuckoo)
        - several pcaps different binaries (cuckoo)

### examples from 'processData.sh' for harry
# robot data is generated by ../robot/simulator.py
./harry.py -n 0 -s 10 -S 300000 -a sally -p sip -r .9 ../prisma/data/alca.drk
./harry.py -n 0 -s 10 -S 300000 -a sally -p sip -v -r .9 ../prisma/data/fsa.drk
./harry.py -n 2 -s 0 -S 300000 -a sally -p universal -r .9 ../prisma/data/dns.drk
./harry.py -n 0 -s 10 -S 300000 -a sally -p universal -r .9 ../prisma/data/20031009-lbnl.drk
# cat ftp_ls.drk ftp2_ls.drk | gzip - > ftpLS.drk
./harry.py -n 0 -s 10 -S 300000 -a sally -p universal -r 1 ../prisma/data/ftpLS.drk