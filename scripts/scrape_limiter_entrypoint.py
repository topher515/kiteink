#!/usr/bin/env python3

import logging
from logging.handlers import RotatingFileHandler
import os
from pprint import pformat
import subprocess
import sys
import time
from random import randint, random as randfloat

logging.basicConfig(stream=sys.stderr, level=logging.INFO)


def parse_probability(strn: str) -> float:
    splat = strn.split('/')
    if len(splat) == 2:
        numer, denom = splat
        return float(numer) / float(denom)
    elif len(splat) == 1:
        return float(splat[0])
    raise ValueError(f"Cannot parse probabilty str of '{strn}'")


# Designed for a crontab like: */5 6-22 * * * * * *
EXEC_PROBABILITY = parse_probability(
    os.environ.get("KITE_EXEC_PROBABILITY", "1/4"))
EXEC_DELAY_MIN_SECS = int(os.environ.get("KITE_EXEC_DELAY_MIN_SECS", 0))
EXEC_DELAY_MAX_SECS = int(os.environ.get("KITE_EXEC_DELAY_MAX_SECS", 120))
SPOT_IDS = [int(x.strip())
            for x in os.environ.get("KITE_SPOT_IDS", "").split(",") if x]
LOG_FILE_PATH = os.environ.get("KITE_LOG_FILE_PATH")


def setup_rotating_file_log(log_filepath: str):
    try:
        os.mkdir(os.path.dirname(log_filepath))
    except FileExistsError:
        pass
    log_handler = RotatingFileHandler(log_filepath)
    formatter = logging.Formatter(
        '%(asctime)s kiteink [%(process)d]: %(message)s',
        '%b %d %H:%M:%S')
    # formatter.converter = time.gmtime  # if you want UTC time
    log_handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(log_handler)
    logger.setLevel(logging.INFO)


def main():
    '''
    Every time this funcion is called there is only some probabilty of the fetch getting run
    and some amount of time delay. 

    (It seems like using the API for personal use is ok based on weatherflow Terms Of Use[1],
    as long as you don't make money from this data or display it publicly, but it seems wise
    to not behave too much like a bot, so we delay and randomize our API fetches.)

    [1] https://help.weatherflow.com/hc/en-us/articles/206504298-Terms-of-Use
    '''

    if LOG_FILE_PATH:
        setup_rotating_file_log(LOG_FILE_PATH)

    if not SPOT_IDS:
        logging.error("No SPOT_IDS specified")
        sys.exit(1)

    if EXEC_PROBABILITY < randfloat():

        sleep_secs = randint(EXEC_DELAY_MIN_SECS, EXEC_DELAY_MAX_SECS)
        logging.info(f"Will fetch + paint--delaying for {sleep_secs} secs")
        time.sleep(sleep_secs)
        logging.info("Beginning fetch + paint")
        spot_ids = ' '.join([str(x) for x in SPOT_IDS])
        subprocess.call(
            f'pipenv run fetch_spots_json.py --threaded {spot_ids} | pipenv run paint_report_from_json.py --epaper', shell=True
        )
    else:
        logging.info(
            f"Randomly skipping fetch + paint--{1-EXEC_PROBABILITY} probabilty to skip")


if __name__ == '__main__':
    main()
