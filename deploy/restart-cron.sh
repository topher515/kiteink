#!/usr/bin/env bash

cat configs/etc_cron.d_kiteink | ssh pi@$RPI_IP "crontab -"