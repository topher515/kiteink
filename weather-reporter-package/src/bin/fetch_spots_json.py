#!/usr/bin/env python3
import argparse
import concurrent.futures
import json
import logging
import os
import sys
from base64 import b64encode

from weather_reporter.log import setup_rotating_file_log
from weather_reporter.weatherflow_api import (MODEL_ID_BY_NAME,
                                              WeatherflowApiWithWfTokenCache)

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

LOG_FILE_PATH = os.environ.get("KITE_LOG_FILE_PATH")


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument('--outfile',
                        type=argparse.FileType('w'), default=sys.stdout)
    parser.add_argument('spotids', action='store', type=int, nargs='+')
    parser.add_argument('--threaded', action='store_true', default=False)

    args = parser.parse_args()

    if LOG_FILE_PATH:
        setup_rotating_file_log(LOG_FILE_PATH)

    model_id = MODEL_ID_BY_NAME['Quicklook']

    username = os.environ.get("WF_USERNAME", None)
    pw = os.environ.get("WF_PASSWORD", None)
    wfapi = WeatherflowApiWithWfTokenCache(
        username=username, password=pw, expect_upgraded=bool(username and pw))

    def fetch_spot_data(spot_id: str):
        logging.info(f"Fetching spot {spot_id}")
        graph_summary_data = wfapi.fetch_graph_summary(spot_id)
        model_data = wfapi.fetch_model(spot_id, model_id)

        gauge_img = wfapi.fetch_gauge_img(
            # Decide if this is reasonable
            int(graph_summary_data["last_ob_avg"] or 0),
            graph_summary_data["last_ob_dir"],
            graph_summary_data["last_ob_dir_txt"]
        )

        return (
            {
                "graph_summary": graph_summary_data,
                "models": {
                    model_id: model_data
                },
                "gauge_img": b64encode(gauge_img.read()).decode('utf8')
            }
        )

    if args.threaded:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as exe:
            spots_data = list(exe.map(fetch_spot_data, args.spotids))
    else:
        spots_data = []
        for spot_id in args.spotids:
            spots_data.append(fetch_spot_data(spot_id))

    json.dump(spots_data, args.outfile, indent=2, sort_keys=True)


if __name__ == '__main__':
    main()
