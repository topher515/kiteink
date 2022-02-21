#!/usr/bin/env bash

# Deploy current project to RPi
ssh pi@$RPI_IP "rm -rf /home/pi/app/ && mkdir -p /home/pi/app" && \
    scp -r Pipfile Pipfile.lock weather-reporter-package scripts pi@$RPI_IP:/home/pi/app/ && \
    ssh pi@$RPI_IP "cd /home/pi/app && PIPENV_VENV_IN_PROJECT=1 pipenv install" && \
    cat configs/etc_cron.d_kiteink | ssh pi@$RPI_IP "crontab -"

