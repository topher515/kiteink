
#!/usr/bin/env python3
import argparse
import concurrent.futures
import json
import re
import sys
from base64 import b64encode
from datetime import datetime

from lib.weatherflow_api import MODEL_ID_BY_NAME, WeatherflowApi


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument('--outfile',
                        type=argparse.FileType('w'), default=sys.stdout)
    parser.add_argument('spotids', action='store', type=int, nargs='+')
    parser.add_argument('--threaded', action='store_true', default=False)

    args = parser.parse_args()

    spot_name = 'Lanikai Beach'
    model_id = MODEL_ID_BY_NAME['Quicklook']

    wfapi = WeatherflowApi(wf_token=WeatherflowApi.fetch_wf_token())

    def fetch_spot_data(spot_id: str):
        print(f"Fetching spot {spot_id}", file=sys.stderr)
        graph_summary_data = wfapi.fetch_graph_summary(spot_id)
        model_data = wfapi.fetch_model(spot_id, model_id)

        gauge_img = wfapi.fetch_gauge_img(
            int(graph_summary_data["last_ob_avg"]
                ), graph_summary_data["last_ob_dir"], graph_summary_data["last_ob_dir_txt"]
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
