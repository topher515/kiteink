
#!/usr/bin/env python3
import collections.abc
import json
import sys
import re
from datetime import datetime
import argparse

from lib.painter import paint_display_image

VER = 1


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

    img = paint_display_image(spots_data)

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
