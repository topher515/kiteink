#! /usr/bin/env python3
import re
from datetime import datetime

from lib.weatherflow_api import (
    WeatherflowApi,
    SPOT_ID_BY_NAME, MODEL_ID_BY_NAME
)


def main():
    spot_name = 'Lanikai Beach'
    # graph_data = fetch_graph(SPOT_ID_BY_NAME[spot_name])
    # model_data = fetch_model(
    #     SPOT_ID_BY_NAME[spot_name], MODEL_ID_BY_NAME['Quicklook'])
    # img_buff = fetch_gauge_img(
    #     graph_data["last_ob_avg"], graph_data["last_ob_dir"], graph_data["last_ob_dir_txt"]
    # )
    # spot_slug = re.sub('\s', '_', spot_name)
    # filename = f"{spot_slug}-gauge-{datetime.utcnow().isoformat()}.png"
    # with open(filename, 'wb') as fp:
    #     fp.write(img_buff.read())


if __name__ == '__main__':
    main()
