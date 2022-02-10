
#!/usr/bin/env python3
import json
import re
from datetime import datetime

from lib.weatherflow_api import (
    WeatherflowApi,
    SPOT_ID_BY_NAME, MODEL_ID_BY_NAME
)


def main():
    spot_name = 'Lanikai Beach'
    model_id = MODEL_ID_BY_NAME['Quicklook']
    wfapi = WeatherflowApi(wf_token=WeatherflowApi.fetch_wf_token())
    graph_summary_data = wfapi.fetch_graph_summary(SPOT_ID_BY_NAME[spot_name])
    model_data = wfapi.fetch_model(
        SPOT_ID_BY_NAME[spot_name], model_id)

    print(json.dumps(
        {
            "graph_summary": graph_summary_data,
            "models": {
                model_id: model_data
            }
        }, indent=2, sort_keys=True))

    # img_buff = fetch_gauge_img(
    #     graph_data["last_ob_avg"], graph_data["last_ob_dir"], graph_data["last_ob_dir_txt"]
    # )
    # spot_slug = re.sub('\s', '_', spot_name)
    # filename = f"{spot_slug}-gauge-{datetime.utcnow().isoformat()}.png"
    # with open(filename, 'wb') as fp:
    #     fp.write(img_buff.read())


if __name__ == '__main__':
    main()
