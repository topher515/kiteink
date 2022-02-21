#!/usr/bin/env bash

# Deploy current project to RPi

scp -r weather-reporter-package scripts pi@$RPI_IP:/home/pi/app/ && \
    cat configs/etc_cron.d_kiteink | ssh pi@$RPI_IP "crontab -"

