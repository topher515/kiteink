# Kiteink

Fetch wind data from Weatherflow API and display it on an Waveshare ePaper display
using a Raspberry PI.

Note that the specific hardware used was:
- Raspberry Pi 4 
- Waveshare 7.5 inch red+black display with ePaper Driver HAT (for GPIO)

You will need to modify code for other hardware

(It seems like using the API for personal use is ok based on weatherflow Terms Of Use[1],
as long as you don't sell this data or display it publicly—but IANAL so maybe you could
run afoul of the Weatherflow lawyers.)

[1] https://help.weatherflow.com/hc/en-us/articles/206504298-Terms-of-Use

## Setup for development

- Copy and fill in your own values for `.envrc.example` -> `.envrc`
  - `export RPI_IP="192.168.1.208"` should be the IP address of your RaspberryPi
- Install **direnv**. e.g., `brew install direnv` (https://direnv.net/docs/installation.html)

## Deploy on Raspberry PI

- Copy and fill in your own values for `configs/etc_cron.d_kiteink.example` -> `configs/etc_cron.d_kiteink`
- Deploy to RaspberryPi: `bash deploy/deploy.sh`
- Start the cronjob `bash deploy/restart-cron.sh`