#!/usr/bin/env bash

# Deploy current project to RPi

tar czf dist/kiteink.tgz Pipfile Pipfile.lock weather-reporter-package scripts && \
    ssh pi@$RPI_IP "rm -rf /tmp/app/ && mkdir -p /tmp/app" && \
    scp dist/kiteink.tgz pi@$RPI_IP:/tmp/app/kiteink.tgz && \
    ssh pi@$RPI_IP "cd /tmp/app && tar xfz kiteink.tgz && rm kiteink.tgz && PIPENV_VENV_IN_PROJECT=1 pipenv install"

