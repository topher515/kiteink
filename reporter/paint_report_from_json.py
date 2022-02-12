
#!/usr/bin/env python3
import collections.abc
import json
import sys
import re
from datetime import datetime
import argparse

from lib.painter import paint_display_image

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
    parser.add_argument('infile', nargs='?',
                        type=argparse.FileType('r'), default=sys.stdin)
    parser.add_argument('outfile', nargs='?',
                        type=argparse.FileType('wb'))

    args = parser.parse_args()
    spots_data = json.load(args.infile)

    if not isinstance(spots_data, collections.abc.Sequence):
        spots_data = [spots_data]

    img = paint_display_image([
        normalize_spot_data(d) for d in spots_data
    ])

    def make_default_filename():
        # spot_name = data["graph_summary"]["name"]
        # spot_slug = re.sub(r'\s', '_', spot_name)
        return f"latest-report-v{VER}.png"

    fp = args.outfile if args.outfile else open(make_default_filename(), 'wb')

    try:
        img.save(fp, 'png')
    finally:
        fp.close()


if __name__ == '__main__':
    main()
