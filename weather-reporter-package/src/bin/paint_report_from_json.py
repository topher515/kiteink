#!/usr/bin/env python3
import argparse
import collections.abc
import json
import logging
import os
import sys

from weather_reporter.log import setup_rotating_file_log
from weather_reporter.painter import (composite_red_blk_imgs,
                                      paint_blk_and_red_imgs)

logging.basicConfig(stream=sys.stderr, level=logging.INFO)


LOG_FILE_PATH = os.environ.get("KITE_LOG_FILE_PATH")


try:
    from weather_reporter.epaper_display import epd_display_images
except (ImportError, OSError) as err:
    logging.warning(f"Failed to import epaper display module: {err}")
    epd_display_images = None


VER = 1


def normalize_graph_summary_data(graph_summary_data: dict):
    return {
        **graph_summary_data,
        "last_ob_avg": graph_summary_data.get("last_ob_avg", 0)
    }


def normalize_spot_data(spot_data: dict) -> dict:
    return {
        **spot_data,
        "graph_summary": {
            **spot_data["graph_summary"],
            "last_ob_avg": spot_data["graph_summary"]["last_ob_avg"] or 0
        }
    }


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument('--infile', nargs='?',
                        type=argparse.FileType('r'), default=sys.stdin)

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--outfile', nargs='?',
                       type=argparse.FileType('wb'))
    ep_action = group.add_argument(
        '--epaper', action='store_true', default=False)
    group.add_argument(
        '--show', action='store_true', default=False)
    args = parser.parse_args()

    if LOG_FILE_PATH:
        setup_rotating_file_log(LOG_FILE_PATH)

    spots_data = json.load(args.infile)

    if not isinstance(spots_data, collections.abc.Sequence):
        spots_data = [spots_data]

    normalized_spots_data = [
        normalize_spot_data(d) for d in spots_data
    ]

    blk_img, red_img = paint_blk_and_red_imgs(normalized_spots_data)

    if args.epaper:
        if not epd_display_images:
            raise argparse.ArgumentError(
                ep_action, "Failed to import epaper module--cannot output to epaper")

        logging.info("Painting to epaper display")
        epd_display_images(blk_img, red_img)

    if args.show:
        logging.info("Painting and displaying temporary file")
        img = composite_red_blk_imgs(blk_img, red_img)
        img.show()

    if args.outfile:
        logging.info("Painting and saving file")
        img = composite_red_blk_imgs(blk_img, red_img)

        fp = args.outfile if args.outfile else open(
            f"latest-report-v{VER}.png", 'wb')
        try:
            img.save(fp, 'png')
        finally:
            fp.close()


if __name__ == '__main__':
    main()
