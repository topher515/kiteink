#!/usr/bin/env bash

# Setup RPi
# - Copy SSH pub key to authorized_keys on RPi
# - Install basic packages

scp ~/.ssh/id_rsa.pub pi@$RPI_IP:/tmp/id_rsa.pub && \
    ssh pi@$RPI_IP "mkdir -p /home/pi/.ssh/ && chmod 700 /home/pi/.ssh && cat /tmp/id_rsa.pub >> /home/pi/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && rm /tmp/id_rsa.pub" && \
    ssh pi@$RPI_IP "sudo apt-get -y install python3 pipenv"