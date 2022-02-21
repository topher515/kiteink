#!/usr/bin/env python3

import logging
import os
import shutil
import subprocess
import sys
import time
from random import randint

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

# Designed for a crontab like: 0,5,10,15,20,25,30,35,40,45,50,55 * * * *
PROBABILITY_X = 3  # 1 in X
DELAY_MAX_SECS = 120
DELAY_MIN_SECS = 0
SPOT_IDS = [429, 187573, 430]
LOG_PATH = "/home/pi/logs/"


def main():
    '''
    Every time this funcion is called there is only some probabilty of the fetch getting run
    and some amount of time delay. 

    (It seems like using the API for personal use is ok based on weatherflow Terms Of Use[1],
    as long as you don't make money from this data or display it publicly, but it seems wise
    to not behave too much like a bot, so we delay and randomize our API fetches.)

    [1] https://help.weatherflow.com/hc/en-us/articles/206504298-Terms-of-Use
    '''
    if randint(0, PROBABILITY_X) == 0:

        sleep_secs = randint(DELAY_MIN_SECS, DELAY_MAX_SECS)
        logging.info(f"Will fetch + paint--delaying for {sleep_secs} secs")
        time.sleep(sleep_secs)
        logging.info("Beginning fetch + paint")
        spot_ids = ' '.join([str(x) for x in SPOT_IDS])
        try:
            os.mkdir(LOG_PATH)
        except FileExistsError:
            pass
        subprocess.call(
            f'pipenv run fetch_spots_json.py --log={LOG_PATH}/fetch.log --threaded {spot_ids} | pipenv run paint_report_from_json.py --log={LOG_PATH}/paint.log --epaper', shell=True
        )
    else:
        logging.info("Randomly skipping fetch + paint")


if __name__ == '__main__':
    main()
