#! /usr/bin/env python3

from dataclasses import dataclass
import sys
import time
from io import BytesIO
from typing import Optional, Union
import requests
import re


# https://wx.ikitesurf.com/spot/187573

SAMPLE_BASE_URL = 'https://api.weatherflow.com/wxengine/rest/stat/getSpotStats?callback=jQuery17209069701420982021_1644300565073&units_wind=mph&units_temp=f&units_distance=mi&threshold_list=0%2C10%2C15%2C20%2C25&years_back=50&full_day=false&spot_id=187573&wf_token=e5615b765be6c96e23cc17cba3373778&_=1644300565399'

DEFAULT_SPOT_ID = '187573'

BASE_HEADERS = {
    'Pragma': 'no-cache',
    'Cache-Control': 'no-cache',
    'sec-ch-ua': '" Not;A Brand";v="99", "Google Chrome";v="97", "Chromium";v="97"',
    'sec-ch-ua-mobile': '?0',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36',
    'sec-ch-ua-platform': '"macOS"',
}

NORMAL_HEADERS = {
    **BASE_HEADERS,
    'Connection': 'keep-alive',
    'Accept': '*/*',
    'Sec-Fetch-Site': 'cross-site',
    'Sec-Fetch-Mode': 'no-cors',
    'Sec-Fetch-Dest': 'script',
    'Referer': 'https://wx.ikitesurf.com/',
    'Accept-Language': 'en-US,en;q=0.9',
}

LOGIN_HEADERS = {
    **BASE_HEADERS,
    # 'origin: https://secure.ikitesurf.com'
    'upgrade-insecure-requests: 1'
    'authority': 'secure.ikitesurf.com',
    'content-type': 'application/x-www-form-urlencoded',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-user': '?1',
    'sec-fetch-dest': 'document',
    'referer': f'https://secure.ikitesurf.com/?app=wx&rd=spot/{DEFAULT_SPOT_ID}'
    # 'cookie: ab=%7b%22lm%22%3a%22b%22%7d; wfToken=e5615b765be6c96e23cc17cba3373778; TemperatureUnits=f; SearchRadius=30; DistanceUnits=mi; SortOrder=rank; FavSortOrder=windspeed; AlertsSortOrder=userdefined; PrimaryMapType=High Contrast; fsv=list; uid=09296ad8-2441-4c79-b062-5843d689db7c; Profile=%5B%7B%22name%22%3A%22Favorites%22%2C%22profile_id%22%3A0%2C%22my_profile%22%3A%22true%22%2C%22created_by%22%3A%22local%22%2C%22favorite_spots%22%3A%5B%5D%2C%22containers%22%3A%5B%7B%22container_id%22%3A1%2C%22container_type_id%22%3A%22Favorite%20Spots%22%2C%22container_name%22%3A%22Favorite%20Spots%22%2C%22flowview_options%22%3Anull%2C%22options%22%3A%22%22%7D%5D%7D%5D; PreviousSearch=kailua; SpeedUnits=kts; _ga=GA1.2.1944158511.1644626857; _gid=GA1.2.625208938.1644626857; _gat=1' \

}


SPOT_ID_BY_NAME = {
    'Lanikai Beach': '187573'
}

MODEL_ID_BY_NAME = {
    'Quicklook': '-1'
}


def ms_epoch() -> int:
    return int(time.time() * 1000)


SCRAPING_WF_TOKEN_RE = re.compile("var token = '(?P<wf_token>.+)'")


@dataclass
class WeatherflowApi:
    username: Optional[str] = None
    password: Optional[str] = None

    units_wind: str = 'kts'
    units_temp: str = 'f'
    units_distance: str = 'mi'

    def __post_init__(self):
        if self.username and self.password:
            print(
                f"Logging in to Weatherflow API with username {self.username}",  file=sys.stderr)
            self.login(self.username, self.password)
        else:
            print(f"No login credentials found for Weatherflow API", file=sys.stderr)
            self.sesh = requests.Session()

        self.refresh_wf_token()

    def login(self, username, password):
        sesh = requests.Session()
        resp = sesh.post(
            'https://secure.ikitesurf.com/?app=wx&rd=',
            params={
                'app': 'wx',
                'rd': 'spot/187573'
            },
            data={
                'isun': username,
                'ispw': password,
                'iwok.x': 'Sign In',
                'app': 'wx',
                'rd': f'spot/{DEFAULT_SPOT_ID}'
            }
        )
        resp.raise_for_status()
        self.sesh = sesh

    def fetch_wf_token(self, spot_id: Optional[str] = DEFAULT_SPOT_ID) -> str:

        resp = self.sesh.get(f'https://wx.ikitesurf.com/spot/{spot_id}')
        resp.raise_for_status()

        for line in resp.iter_lines(decode_unicode=True):
            if match := re.search(SCRAPING_WF_TOKEN_RE, line):
                return match.group("wf_token")

        raise RuntimeError("Could not find wf_token in page")

    def refresh_wf_token(self, spot_id: Optional[str] = DEFAULT_SPOT_ID):
        self.wf_token = self.fetch_wf_token()

    def fetch_graph_summary(self, spot_id: str) -> dict:
        resp = self.sesh.get(
            'https://api.weatherflow.com/wxengine/rest/graph/getGraph',
            params={
                # 'callback': ['jQuery17209069701420982021_1644300565073'],
                'units_wind': [self.units_wind],
                'units_temp': [self.units_temp],
                'units_distance': [self.units_distance],
                # 'threshold_list': ['0,10,15,20,25'],
                # 'years_back': ['50'],
                # 'full_day': ['false'],
                'null_ob_min_from_now': ['60'],
                'show_virtual_obs': ['true'],
                'time_start_offset_hours': ['-36'],
                'time_end_offset_hours': ['0'],
                'type': ['dataonly'],
                'model_ids': ['-101'],
                'fields': ['winds'],
                'format': ['json'],
                'spot_id': [spot_id],
                'wf_token': [self.wf_token],
                '_': [ms_epoch()]  # Cachebreak ?
            },
            headers=NORMAL_HEADERS
        )
        resp.raise_for_status()
        return resp.json()

    def fetch_model(self, spot_id: str, model_id: str) -> dict:
        resp = self.sesh.get(
            'https://api.weatherflow.com/wxengine/rest/model/getModelDataBySpot',
            params={
                # 'callback': ['jQuery17209069701420982021_1644300565073'],
                'units_wind': [self.units_wind],
                'units_temp': [self.units_temp],
                'units_distance': [self.units_distance],
                'model_id': ['-1'],
                'spot_id': [spot_id],
                'wf_token': [self.wf_token],
                '_': [ms_epoch()]  # Cachebreak ?
            },
            headers=NORMAL_HEADERS
        )

        resp.raise_for_status()
        return resp.json()

    # def fetch_and_process_lanikai_beach():
    #     graph_data = fetch_graph(SPOT_ID_BY_NAME['Lanikai Beach'])

    def fetch_gauge_img(self, wind_speed: int, wind_dir: int, wind_dir_txt: str) -> BytesIO:
        resp = self.sesh.get(
            'https://api.weatherflow.com/wxengine/rest/graph/getGauge',
            params={
                'wf_token': [self.wf_token],
                'units_wind': [self.units_wind],
                'units_temp': [self.units_temp],
                'units_distance': [self.units_distance],
                'color_arrow': ['0xffffff'],
                'color_gauge_bg': ['0xececec'],
                'format': ['raw'],
                'height': ['180'],
                'image_format': ['png'],
                'width': ['180'],
                'wind_dir': [wind_dir],  # '68'
                'wind_dir_txt': [wind_dir_txt],  # 'ENE',
                'message_code': ['1'],
                'wind_speed': [wind_speed],
                '_': [ms_epoch()]
            },
            headers=NORMAL_HEADERS
        )
        resp.raise_for_status()
        buf = BytesIO(resp.content)
        buf.seek(0)
        return buf
