import logging
from logging.handlers import RotatingFileHandler
from typing import Optional


def setup_rotating_file_log(log_filepath: str):

    log_handler = RotatingFileHandler(log_filepath)
    formatter = logging.Formatter(
        '%(asctime)s kiteink [%(process)d]: %(message)s',
        '%b %d %H:%M:%S')
    # formatter.converter = time.gmtime  # if you want UTC time
    log_handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(log_handler)
    logger.setLevel(logging.INFO)
