import os
import statistics
import textwrap
from base64 import b64decode
from collections import defaultdict
from datetime import datetime, timedelta, tzinfo
from email.headerregistry import Group
from io import BytesIO
from itertools import chain, groupby
from pathlib import Path
from time import timezone
from typing import Callable, Dict, Sequence, Tuple, Union

import dateutil.parser
import pytz
from PIL import Image, ImageColor, ImageDraw, ImageFont

# More fonts https://www.dafont.com/bitmap.php
# https://lucid.app/lucidchart/6a918925-6ff7-4aff-91ce-f57223f1599a/edit?beaconFlowId=B86FF4B9E5FF811D&invitationId=inv_afc6c6ae-b5ad-4c89-bf62-57c523d488b7&page=0_0#

# RGBA_WHITE = (255, 255, 255, 255)

DIMENSIONS = (800, 480)

WHITE_BIT = 1
BLACK_BIT = 0

TZ = pytz.timezone("HST")

CONSIDERED_OLD = timedelta(hours=1)


def get_font_path():
    return os.path.join(Path(__file__).resolve().parent, "vcr_osd_mono_1.ttf")


def composite_red_blk(blk_img: Image.Image, red_img: Image.Image) -> Image.Image:
    img_color = Image.new("RGB", DIMENSIONS, (255, 255, 255))
    out = Image.composite(img_color, blk_img, blk_img)
    out = Image.composite(out, Image.new(
        'RGB', DIMENSIONS, (255, 0, 0)), red_img)
    return out


def calc_180_graph_avg_wind_speed(now_dt: datetime, graph_summary_data: dict):
    '''
    `now_dt` the time to treat as now
    '''
    if not now_dt.tzinfo:
        raise RuntimeError(
            "Will not calculate graph avg wind speed for naive datetime")


def get_hour_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H")


GroupedData = Sequence[Tuple[str, Sequence[float]]]

SummaryData = Sequence[Tuple[str, float]]

HourlyData = Sequence[Tuple[int, float]]


def group_by(data: Sequence, get_key: Callable, get_value: Callable) -> GroupedData:
    groupby_iter = groupby(data, get_key)
    return [(key, [x for x in (get_value(item) for item in group) if x]) for key, group in groupby_iter]


def group_by_hour_historical_tuples(data: Sequence[Tuple[float, float]], data_tz: tzinfo, to_tz: tzinfo) -> GroupedData:

    def _get_hour_key(datum) -> str:
        dt = datetime.fromtimestamp(datum[0]/1000).replace(tzinfo=data_tz)
        dt_local: datetime = dt.astimezone(to_tz)
        return get_hour_key(dt_local)

    def get_value(datum) -> float:
        return datum[1]

    return group_by(data, _get_hour_key, get_value)


def group_by_hour_model_items(data: Sequence[dict], to_tz: tzinfo):

    def _get_hour_key(datum: dict) -> str:
        dt = dateutil.parser.isoparse(datum['model_time_utc'])
        dt_local: datetime = dt.astimezone(to_tz)
        print(dt_local.isoformat())
        return get_hour_key(dt_local)

    def get_value(datum) -> float:
        return datum["wind_speed"]

    return group_by(data, _get_hour_key, get_value)


def mean_data(data: Sequence[Tuple[str, Sequence[float]]]) -> SummaryData:
    return [(hour, (statistics.mean(value_list) if value_list else 0)) for hour, value_list in data]


def calc_prev_6_hours_wind_mean(now_dt: datetime, graph_summary_data: dict, tz: tzinfo) -> HourlyData:

    if not now_dt.tzinfo:
        raise RuntimeError("Refuding to process naive datetime")

    hourlies = group_by_hour_historical_tuples(
        graph_summary_data["wind_avg_data"],
        pytz.timezone(graph_summary_data["local_timezone"]),
        tz
    )

    hourly_avg = dict(mean_data(hourlies))

    prev_6_hours = []

    for i in reversed(range(6)):
        hourkey = get_hour_key(now_dt - timedelta(hours=i))
        prev_6_hours.append(
            (int(hourkey.split("T")[1]), hourly_avg.get(hourkey, 0))
        )
    return prev_6_hours


def calc_next_8_hours_wind_mean(now_dt: datetime, model_data: dict, tz: tzinfo) -> HourlyData:

    if not now_dt.tzinfo:
        raise RuntimeError("Refusing to process naive datetime")

    hourlies = group_by_hour_model_items(model_data["model_data"], tz)
    hourly_avg = dict(mean_data(hourlies))

    next_8_hours = []

    for i in range(1, 8):
        hourkey = get_hour_key(now_dt + timedelta(hours=i))
        next_8_hours.append(
            (int(hourkey.split("T")[1]), hourly_avg.get(hourkey, 0))
        )

    return next_8_hours


def paint_blk_and_red_imgs(graph_summary_data: dict, model_data: dict, gauge_img_data: Union[str, bytes]) -> Tuple[Image.Image, Image.Image]:
    '''
    Returns black
    '''
    base_blk = Image.new("1", DIMENSIONS, WHITE_BIT)
    base_red = Image.new("1", DIMENSIONS, WHITE_BIT)

    # Get drawing contexts
    draw_blk = ImageDraw.Draw(base_blk)
    draw_red = ImageDraw.Draw(base_red)

    fnt_40 = ImageFont.truetype(get_font_path(), 40)
    fnt_30 = ImageFont.truetype(get_font_path(), 30)
    fnt_20 = ImageFont.truetype(get_font_path(), 20)
    fnt_12 = ImageFont.truetype(get_font_path(), 10)

    now_local = TZ.fromutc(
        datetime.utcnow())

    def write_text(coords: Tuple[int, int], fnt: ImageFont.FreeTypeFont, text: str, red=False):
        d = draw_red if red else draw_blk
        d.text(coords, text, font=fnt, fill=BLACK_BIT, )

    def write_hourlies(coords: Tuple[int, int], hourlies: Sequence[Tuple[int, float, bool]], width: int = 2, filled=True, red=False, pixels_per_unit=4):
        d = draw_red if red else draw_blk

        x_start, y_start = coords

        for j in range(25):
            if j % 4 == 0:
                write_text((x_start, y_start - (10 + j*pixels_per_unit)),
                           fnt_12, str(j), red=red)

        x = x_start + 10
        y = y_start
        for i, (hour, value, filled) in enumerate(hourlies):
            d.rectangle((x, y - 5, x + width, y - (5 + value*pixels_per_unit)),
                        outline=BLACK_BIT, fill=BLACK_BIT if filled else WHITE_BIT, width=1)

            if i % 2 == 0:
                # Print every other hour
                write_text((x, y), fnt_12, str(hour), red=red)
            x += width

    def paint_col1(x_start: int):

        write_text((x_start, 70), fnt_40, "Now")
        write_text((x_start, 110), fnt_20, now_local.strftime("%H:%M %Z"))
        write_text((x_start, 190), fnt_40, "Today")
        write_text((x_start, 230), fnt_20, now_local.strftime("%b %d"))
        write_text((x_start, 350), fnt_40, "7 Day", red=True)

    def paint_col2(x_start: int):

        # Write Spot title
        spot_name = graph_summary_data["name"][:8]
        # offset = 10
        # for line in textwrap.wrap(spot_name, width=10):
        #     write_text((x_start, offset), fnt_30, line)
        #     offset += fnt_30.getsize(line)[1]
        write_text((x_start, 10), fnt_30, spot_name)

        # Write Last updated
        last_fetch = datetime.fromtimestamp(
            graph_summary_data["current_time_epoch_utc"]/1000)  # .astimezone(pytz.UTC)
        last_fetch_local = TZ.fromutc(last_fetch)

        if now_local - last_fetch_local > CONSIDERED_OLD:
            # Is old data
            write_text((x_start, 40), fnt_12,
                       last_fetch_local.strftime("Old! %b %d, %H:%M %Z"), red=True)
        else:
            write_text((x_start, 40), fnt_12,
                       last_fetch_local.strftime("Last: %b %d, %H:%M %Z"))

        # Write Gauge
        gauge_img = Image.open(BytesIO(b64decode(gauge_img_data))).convert("1")
        base_blk.paste(gauge_img.crop((20, 20, 160, 160)
                                      ).resize((100, 100)), (x_start, 70))

        # Write today bar chart
        hourlies_past = calc_prev_6_hours_wind_mean(
            now_local, graph_summary_data, TZ)
        hourlies_future = calc_next_8_hours_wind_mean(
            now_local, model_data, TZ)
        hourlies = list(chain(
            ((hour, val, True) for hour, val in hourlies_past),
            ((hour, val, False) for hour, val in hourlies_future)
        ))
        write_hourlies((x_start, 300), hourlies, filled=True, width=10)

    paint_col1(10)
    paint_col2(200)

    return (base_blk, base_red)


def paint_display_image(graph_summary_data: dict, model_data: dict, gauge_img: bytes) -> Image.Image:
    blk_img, red_img = paint_blk_and_red_imgs(
        graph_summary_data,
        model_data,
        gauge_img
    )
    return composite_red_blk(blk_img, red_img)
