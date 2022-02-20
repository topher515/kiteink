#! /usr/bin/env python3

import json
import logging
import time
from dataclasses import dataclass
from io import BytesIO
from typing import Optional, cast

import requests

SAMPLE_BASE_URL = 'https://api.weatherflow.com/wxengine/rest/stat/getSpotStats?callback=jQuery17209069701420982021_1644300565073&units_wind=mph&units_temp=f&units_distance=mi&threshold_list=0%2C10%2C15%2C20%2C25&years_back=50&full_day=false&spot_id=187573&wf_token=e5615b765be6c96e23cc17cba3373778&_=1644300565399'

DEFAULT_SPOT_ID = '187573'

BASE_HEADERS = {
    'upgrade-insecure-requests': '1',
    'Pragma': 'no-cache',
    'Cache-Control': 'no-cache',
    'sec-ch-ua': '" Not;A Brand";v="99", "Google Chrome";v="97", "Chromium";v="97"',
    'sec-ch-ua-mobile': '?0',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36',
    'sec-ch-ua-platform': '"macOS"',
}

HTML_HEADERS = {
    **BASE_HEADERS,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'accept-encoding': 'gzip, deflate, br',
    'Referer': 'https://wx.ikitesurf.com/',
    'Accept-Language': 'en-US,en;q=0.9',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'cross-site',
    'sec-fetch-user': '?1',
}

LOGIN_HEADERS = {
    **BASE_HEADERS,
    # 'origin: https://secure.ikitesurf.com'
    'authority': 'secure.ikitesurf.com',
    'content-type': 'application/x-www-form-urlencoded',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-user': '?1',
    'sec-fetch-dest': 'document',
    'referer': f'https://secure.ikitesurf.com/?app=wx&rd=spot/{DEFAULT_SPOT_ID}'
}


SPOT_ID_BY_NAME = {
    'Lanikai Beach': '187573'
}

MODEL_ID_BY_NAME = {
    'Quicklook': '-1'
}


def ms_epoch() -> int:
    return int(time.time() * 1000)


def parse_json_from_jquery_callback(jquery_callback: str, content: str) -> dict:
    start = len(jquery_callback)+1
    return json.loads(content[start:-1])


def make_logged_in_ikitesurf_session(username: str, password: str) -> requests.Session:
    sesh = requests.Session()

    resp = sesh.get(
        "https://secure.ikitesurf.com/",
        headers=HTML_HEADERS
    )

    resp = sesh.post(
        'https://secure.ikitesurf.com',
        params={
            'app': 'wx',
            'rd': f'spot/{DEFAULT_SPOT_ID}'
        },
        data={
            'isun': username,
            'ispw': password,
            'iwok.x': 'Sign In',
            'app': 'wx',
            'rd': f'spot/{DEFAULT_SPOT_ID}'
        },
        headers=LOGIN_HEADERS,
        allow_redirects=False
    )
    resp.raise_for_status()
    return sesh


def make_anonymous_ikitesurf_session() -> requests.Session:
    sesh = requests.Session()

    resp = sesh.get(
        "https://wx.ikitesurf.com/",
        headers=HTML_HEADERS
    )
    resp.raise_for_status()
    return sesh


def get_wf_token(sesh: requests.Session) -> str:
    return sesh.cookies['wfToken']


class WeatherflowApiFailure(Exception):
    pass


def raise_for_wfapi_status(resp: requests.Response):
    if resp.json()["status"]["status_code"] != 0:
        raise WeatherflowApiFailure(resp.json()["status"]["status_message"])


@dataclass
class WeatherflowApi:
    username: Optional[str] = None
    password: Optional[str] = None
    wf_token: Optional[str] = None
    expect_upgraded: bool = False  # If True, then this login should have upgraded data

    units_wind: str = 'kts'
    units_temp: str = 'f'
    units_distance: str = 'mi'

    def __post_init__(self):
        if not self.wf_token:
            self.refresh_wf_token()

    def refresh_wf_token(self):
        if self.username and self.password:
            logging.info(
                f"Logging in to Weatherflow API with username {self.username}")
            self.wf_token = get_wf_token(
                make_logged_in_ikitesurf_session(self.username, self.password))

        else:
            logging.info(
                f"No login credentials found for Weatherflow API--using anonymous session")
            self.sesh = requests.Session()
            self.wf_token = get_wf_token(
                make_anonymous_ikitesurf_session())

    def fetch_graph_summary(self, spot_id: str) -> dict:
        # cbtext = 'jQuery17209069701420982021_1644300565073'
        resp = requests.get(
            'https://api.weatherflow.com/wxengine/rest/graph/getGraph',
            params={
                # 'callback': [cbtext],
                'units_wind': [self.units_wind],
                'units_temp': [self.units_temp],
                'units_distance': [self.units_distance],
                'fields': ['wind'],
                'format': ['json'],
                'null_ob_min_from_now': ['60'],
                'show_virtual_obs': ['true'],
                'time_start_offset_hours': ['-36'],
                'time_end_offset_hours': ['0'],
                'type': ['dataonly'],
                'model_ids': ['-101'],
                'spot_id': [spot_id],
                'wf_token': [self.wf_token or ""],
                '_': [str(ms_epoch())]  # Cachebreak ?
            },
        )
        resp.raise_for_status()
        raise_for_wfapi_status(resp)
        if self.expect_upgraded and resp.json()["upgrade_available"]:
            raise WeatherflowApiFailure("Received non-upgraded response")
        return resp.json()

    def fetch_model(self, spot_id: str, model_id: str) -> dict:
        resp = requests.get(
            'https://api.weatherflow.com/wxengine/rest/model/getModelDataBySpot',
            params={
                'units_wind': [self.units_wind],
                'units_temp': [self.units_temp],
                'units_distance': [self.units_distance],
                'model_id': [model_id],
                'spot_id': [spot_id],
                'wf_token': [self.wf_token or ""],
                '_': [ms_epoch()]  # Cachebreak ?
            },
        )

        resp.raise_for_status()
        raise_for_wfapi_status(resp)
        if self.expect_upgraded and resp.json()["is_upgrade_available"]:
            raise WeatherflowApiFailure("Received non-upgraded response")
        return resp.json()

    def fetch_gauge_img(self, wind_speed: int, wind_dir: int, wind_dir_txt: str) -> BytesIO:
        resp = requests.get(
            'https://api.weatherflow.com/wxengine/rest/graph/getGauge',
            params={
                'wf_token': [self.wf_token or ""],
                'units_wind': [self.units_wind],
                'units_temp': [self.units_temp],
                'units_distance': [self.units_distance],
                'color_arrow': ['0xffffff'],
                'color_gauge_bg': ['0xececec'],
                'format': ['raw'],
                'height': ['180'],
                'image_format': ['png'],
                'width': ['180'],
                'wind_dir': [wind_dir],  # e.g., '68'
                'wind_dir_txt': [wind_dir_txt],  # e.g., 'ENE',
                'message_code': ['1'],
                'wind_speed': [wind_speed],
                '_': [ms_epoch()]
            },
        )
        resp.raise_for_status()
        buf = BytesIO(resp.content)
        buf.seek(0)
        # Note: this api call is missing validation that it was a successful response!
        return buf


class WeatherflowApiWithWfTokenCache(WeatherflowApi):
    cache_file_path: str = '/tmp/wftokencache.txt'

    def __init__(self, *args, **kwargs):

        if kwargs.get("cache_file_path"):
            self.cache_file_path = kwargs.pop("cache_file_path")

        try:
            with open(self.cache_file_path, 'r') as fp:
                kwargs["wf_token"] = fp.read().strip()
                logging.info(
                    f"Using filesystem cached wftoken: {kwargs['wf_token']}")
        except FileNotFoundError:
            logging.warning(
                f"No filesystem cached wftoken found")

        super().__init__(*args, **kwargs)

    def refresh_wf_token(self):
        super().refresh_wf_token()
        with open(self.cache_file_path, 'w') as fp:
            fp.write(cast(str, self.wf_token))

    def fetch_graph_summary(self, *args, **kwargs):
        try:
            return super().fetch_graph_summary(*args, **kwargs)
        except WeatherflowApiFailure:
            self.refresh_wf_token()
            return super().fetch_graph_summary(*args, **kwargs)

    def fetch_model(self, *args, **kwargs):
        try:
            return super().fetch_model(*args, **kwargs)
        except WeatherflowApiFailure:
            self.refresh_wf_token()
            return super().fetch_model(*args, **kwargs)
