
#!/usr/bin/env python3
import argparse
import json
import re
from datetime import datetime
from base64 import b64encode
import sys

from lib.weatherflow_api import (
    WeatherflowApi,
    MODEL_ID_BY_NAME
)


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument('--outfile',
                        type=argparse.FileType('w'), default=sys.stdout)
    parser.add_argument('spotids', action='store', type=int, nargs='+')

    args = parser.parse_args()

    spot_name = 'Lanikai Beach'
    model_id = MODEL_ID_BY_NAME['Quicklook']

    wfapi = WeatherflowApi(wf_token=WeatherflowApi.fetch_wf_token())

    spots_data = []
    for spot_id in args.spotids:
        graph_summary_data = wfapi.fetch_graph_summary(spot_id)
        model_data = wfapi.fetch_model(spot_id, model_id)

        gauge_img = wfapi.fetch_gauge_img(
            int(graph_summary_data["last_ob_avg"]
                ), graph_summary_data["last_ob_dir"], graph_summary_data["last_ob_dir_txt"]
        )

        spots_data.append(
            {
                "graph_summary": graph_summary_data,
                "models": {
                    model_id: model_data
                },
                "gauge_img": b64encode(gauge_img.read()).decode('utf8')
            }
        )

    json.dump(spots_data, args.outfile, indent=2, sort_keys=True)


if __name__ == '__main__':
    main()
