from base64 import b64decode
from collections import defaultdict
from datetime import datetime, timedelta, tzinfo
import statistics
from io import BytesIO
from itertools import groupby
import os
from pathlib import Path
import textwrap
from time import timezone
from typing import Dict, Sequence, Tuple, Union
from PIL import Image, ImageColor, ImageFont, ImageDraw
import pytz

# More fonts https://www.dafont.com/bitmap.php
# https://lucid.app/lucidchart/6a918925-6ff7-4aff-91ce-f57223f1599a/edit?beaconFlowId=B86FF4B9E5FF811D&invitationId=inv_afc6c6ae-b5ad-4c89-bf62-57c523d488b7&page=0_0#

# RGBA_WHITE = (255, 255, 255, 255)

DIMENSIONS = (800, 480)

WHITE_BIT = 1
BLACK_BIT = 0

TZ = "HST"

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


# graph_summary_data["wind_avg_data"]

TimestampedDatum = Tuple[float, float]


def get_hour_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H")


def group_by_hour(data: Sequence[TimestampedDatum], tz: tzinfo = pytz.UTC) -> Sequence[Tuple[str, Sequence[float]]]:

    def get_hour_key_from_timestamp(timestamp: float) -> str:
        # timestamp, value = datum
        dt = datetime.fromtimestamp(timestamp/1000)
        dt_local: datetime = tz.fromutc(dt)
        return get_hour_key(dt_local)

    hourly = defaultdict(list)
    for timestamp, value in data:
        hourly[get_hour_key_from_timestamp(timestamp)].append(value)

    groupby_iter = groupby(
        data, lambda datum: get_hour_key_from_timestamp(datum[0]))
    return [(hourkey, [value for timestamp, value in group if value is not None]) for hourkey, group in groupby_iter]


def mean_data(data: Sequence[Tuple[str, Sequence[float]]]) -> Sequence[Tuple[str, float]]:
    return [(hour, (statistics.mean(value_list) if value_list else 0)) for hour, value_list in data]


def calc_prev_6_hours_wind_mean(now_dt: datetime, graph_summary_data: dict):

    if not now_dt.tzinfo:
        raise RuntimeError("Refuding to process naive datetime")

    hourlies = group_by_hour(graph_summary_data["wind_avg_data"])

    hourly_avg = dict(mean_data(hourlies))

    prev_6_hours = []

    for i in reversed(range(6)):
        hourkey = get_hour_key(now_dt - timedelta(hours=i))
        prev_6_hours.append(
            (int(hourkey.split("T")[1]), hourly_avg.get(hourkey, 0))
        )

    return prev_6_hours


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

    now_local = pytz.timezone(TZ).fromutc(
        datetime.utcnow())

    def write_text(coords: Tuple[int, int], fnt: ImageFont.FreeTypeFont, text: str, red=False):
        d = draw_red if red else draw_blk
        d.text(coords, text, font=fnt, fill=BLACK_BIT, )

    def write_hourlies(coords: Tuple[int, int], hourlies: Sequence[Tuple[int, float]], width: int = 2, filled=True, red=False, pixels_per_unit=4):
        d = draw_red if red else draw_blk

        x_start, y_start = coords

        for j in range(25):
            if j % 4 == 0:
                write_text((x_start, y_start - (10 + j*pixels_per_unit)),
                           fnt_12, str(j), red=red)

        x = x_start + 10
        y = y_start
        for i, (hour, value) in enumerate(hourlies):
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
        last_fetch_local = pytz.timezone(TZ).fromutc(last_fetch)

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
        hourlies = calc_prev_6_hours_wind_mean(now_local, graph_summary_data)
        print(hourlies)
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
