#!/usr/bin/env bash

# Deploy current project to RPi

# tar -czf dist/kiteink.tgz Pipfile Pipfile.lock weather-reporter-package scripts && \
ssh pi@$RPI_IP "rm -rf /tmp/app/ && mkdir -p /tmp/app" && \
    scp -r Pipfile Pipfile.lock weather-reporter-package scripts pi@$RPI_IP:/tmp/app/ && \
    ssh pi@$RPI_IP "cd /tmp/app && PIPENV_VENV_IN_PROJECT=1 pipenv install"

