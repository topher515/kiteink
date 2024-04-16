import os
import statistics
from base64 import b64decode
from datetime import datetime, timedelta, tzinfo
from io import BytesIO
from itertools import chain, groupby
from numbers import Number
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import (Callable, Iterable, Optional, Sequence, Tuple, TypedDict,
                    Union, cast)
import logging

import dateutil.parser
import pytz
import qrcode
from PIL import Image, ImageDraw, ImageFont

# More fonts https://www.dafont.com/bitmap.php
# https://lucid.app/lucidchart/6a918925-6ff7-4aff-91ce-f57223f1599a/edit?beaconFlowId=B86FF4B9E5FF811D&invitationId=inv_afc6c6ae-b5ad-4c89-bf62-57c523d488b7&page=0_0#


DIMENSIONS = (800, 480)

WHITE_BIT = 1
BLACK_BIT = 0

TZ = pytz.timezone("Pacific/Honolulu")

CONSIDERED_OLD = timedelta(hours=1)

THRESHOLD_SPEED_KNOTS = float(os.environ.get(
    "HIGHLIGHT_THRESHOLD_SPEED_KNOTS", 15))
THRESHOLD_SPEEDS = {
    'kts': THRESHOLD_SPEED_KNOTS,
    'mph': 1.15078 * THRESHOLD_SPEED_KNOTS,
    'kph': 1.852 * THRESHOLD_SPEED_KNOTS,
}

CHART_SPEED_UNIT_MAX = int(os.environ.get("CHART_SPEED_UNIT_MAX", 25))
UNIT_SPEED_PIXEL_HEIGHT = float(os.environ.get("UNIT_SPEED_PIXEL_HEIGHT", 4))


def get_spot_website_url(spot_id: int):
    return f'https://wx.ikitesurf.com/spot/{spot_id}'


def get_font_path():
    # "vcr_osd_mono_1.ttf")
    return os.path.join(Path(__file__).resolve().parent, "fonts/pixellari.ttf")


def composite_red_blk_imgs(blk_img: Image.Image, red_img: Image.Image) -> Image.Image:
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


def get_div_hr_key(dt: datetime, mod: int) -> str:
    return dt.strftime("%Y-%m-%dT") + str(int(dt.hour / 3))


def get_3hr_key(dt: datetime) -> str:
    return get_div_hr_key(dt, 3)


def get_int_from_hour_key(hourkey: str) -> int:
    return int(hourkey.split("T")[1])


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


def group_by_3hr_model_items(data: Sequence[dict], to_tz: tzinfo):

    def _get_hour_key(datum: dict) -> str:
        dt = dateutil.parser.isoparse(datum['model_time_utc'])
        dt_local: datetime = dt.astimezone(to_tz)
        return get_3hr_key(dt_local)

    def get_value(datum) -> float:
        return datum["wind_speed"]

    return group_by(data, _get_hour_key, get_value)


def group_by_hour_model_items(data: Sequence[dict], to_tz: tzinfo):

    def _get_hour_key(datum: dict) -> str:
        dt = dateutil.parser.isoparse(datum['model_time_utc'])
        dt_local: datetime = dt.astimezone(to_tz)
        return get_hour_key(dt_local)

    def get_value(datum) -> float:
        return datum["wind_speed"]

    return group_by(data, _get_hour_key, get_value)


def mean_data(data: Sequence[Tuple[str, Sequence[float]]]) -> SummaryData:
    return [(hour, (statistics.mean(value_list) if value_list else 0)) for hour, value_list in data]


def calc_prev_5_hours_wind_mean(now_dt: datetime, graph_summary_data: dict, tz: tzinfo) -> HourlyData:

    if not now_dt.tzinfo:
        raise RuntimeError("Refuding to process naive datetime")

    hourlies = group_by_hour_historical_tuples(
        graph_summary_data["wind_avg_data"],
        pytz.timezone(graph_summary_data["local_timezone"]),
        tz
    )

    hourly_avg = dict(mean_data(hourlies))

    prev_6_hours = []

    for i in reversed(range(1, 6)):
        hourkey = get_hour_key(now_dt - timedelta(hours=i))
        prev_6_hours.append(
            (get_int_from_hour_key(hourkey), hourly_avg.get(hourkey, 0))
        )
    return prev_6_hours


def calc_next_12_hours_wind_mean(now_dt: datetime, model_data: dict, tz: tzinfo) -> HourlyData:

    if not now_dt.tzinfo:
        raise RuntimeError("Refusing to process naive datetime")

    hourlies = group_by_hour_model_items(model_data["model_data"], tz)
    hourly_avg = dict(mean_data(hourlies))

    next_8_hours = []

    for i in range(1, 12):
        hourkey = get_hour_key(now_dt + timedelta(hours=i))
        next_8_hours.append(
            (get_int_from_hour_key(hourkey), hourly_avg.get(hourkey, 0))
        )

    return next_8_hours


def calc_next_60_3hr_wind_mean(now_dt: datetime, model_data: dict, tz: tzinfo):

    if not now_dt.tzinfo:
        raise RuntimeError("Refusing to process naive datetime")

    hourlies = group_by_3hr_model_items(model_data["model_data"], tz)
    hourly_avg = dict(mean_data(hourlies))

    next_60_time_blocks = []

    def calc_day_of_week(_3hrkey: str):
        dt = datetime.strptime(_3hrkey, "%Y-%m-%dT%H").replace(tzinfo=tz)
        return dt.strftime("%a")

    for i in range(1, 178, 3):
        _3hrkey = get_3hr_key(now_dt + timedelta(hours=i))
        next_60_time_blocks.append(
            (calc_day_of_week(_3hrkey), hourly_avg.get(_3hrkey, 0))
        )

    return next_60_time_blocks


class BarChartDatum(TypedDict):
    value: int
    label: Union[str, Number]
    filled: Optional[bool]
    red: Optional[bool]


def paint_blk_and_red_imgs(spots_data: Sequence[dict]) -> Tuple[Image.Image, Image.Image]:
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
    fnt_sm = ImageFont.truetype(get_font_path(), 13)

    now_local = datetime.utcnow().replace(tzinfo=pytz.UTC).astimezone(TZ)

    def write_text(coords: Tuple[int, int], fnt: ImageFont.FreeTypeFont, text: str, red=False):
        d = draw_red if red else draw_blk
        d.text(coords, text, font=fnt, fill=BLACK_BIT, )

    # def write_bar_chart(*args, **kwargs):
    #     print("write_bar_chart", args, kwargs)
    #     return _write_bar_chart(*args, **kwargs)

    def write_bar_chart(coords: Tuple[int, int], bars: Iterable[BarChartDatum], width: int = 2, red=False, pixels_per_unit=UNIT_SPEED_PIXEL_HEIGHT, x_axis_skip=2):
        d = draw_red if red else draw_blk

        x_start, y_start = coords

        for j in range(CHART_SPEED_UNIT_MAX):
            if j % 4 == 0:
                write_text((x_start, y_start - (10 + j*pixels_per_unit)),
                           fnt_sm, str(j), red=red)

        x = x_start + 10
        y = y_start
        for i, bar_datum in enumerate(bars):
            filled = bar_datum["filled"]
            label = bar_datum["label"]
            value = bar_datum["value"]
            bar_red = bar_datum.get("red", red)
            bar_d = draw_red if bar_red else draw_blk
            rect = (x, y - 5, x + width, y - (5 + value*pixels_per_unit))
            bar_d.rectangle(rect, outline=BLACK_BIT, fill=BLACK_BIT if filled else WHITE_BIT, width=1)

            if i % x_axis_skip == 0:
                # Print every other hour
                write_text((x, y), fnt_sm, str(label), red=red)
            x += width

    def write_qrcode(coords: Tuple[int, int], data: str, red=False):
        base_img = base_red if red else base_blk

        with NamedTemporaryFile("wb", delete=False) as fp_w:
            qr = qrcode.QRCode(
                box_size=2,
                border=1,
            )
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image()
            img.save(fp_w)

        with open(fp_w.name, 'rb') as fp_r:
            qrcode_img = Image.open(fp_r)
            base_img.paste(qrcode_img, coords)

        os.remove(fp_w.name)

    def paint_header_col(x_start: int, graph_summary_data: dict):

        units_wind = graph_summary_data["units_wind"]
        threshold_value = THRESHOLD_SPEEDS[units_wind]

        write_text((x_start, 70), fnt_40, "Now")
        write_text((x_start, 110), fnt_20,
                   now_local.strftime("%H:%M %Z"))
        write_text((x_start, 190), fnt_40, "Today")
        write_text((x_start, 230), fnt_20, now_local.strftime("%b %d"))
        write_text((x_start, 350), fnt_40, "7 Day")

        write_text((x_start, 450), fnt_sm,
                   f"Threshold: {threshold_value} {units_wind}")

    def paint_spot_col(x_start: int, graph_summary_data: dict, gauge_img_data: Union[str, bytes], model_data: dict):

        units_wind = model_data["units_wind"]
        threshold_value = THRESHOLD_SPEEDS[units_wind]

        # Write Spot title
        spot_name = graph_summary_data["name"][:8]
        write_text((x_start, 10), fnt_30, spot_name)

        # Write Last updated
        last_fetch = dateutil.parser.isoparse(
            graph_summary_data["current_time_local"])
        last_fetch = last_fetch.replace(
            tzinfo=pytz.timezone(graph_summary_data["local_timezone"]))
        last_fetch_local = last_fetch.astimezone(TZ)

        if now_local - last_fetch_local > CONSIDERED_OLD:
            # Is old data
            write_text((x_start, 40), fnt_sm,
                       last_fetch_local.strftime("old: %b %d, %H:%M %Z"), red=True)
        else:
            write_text((x_start, 40), fnt_sm,
                       last_fetch_local.strftime("last: %b %d, %H:%M %Z"))

        # Write Gauge
        cur_speed = graph_summary_data["last_ob_avg"]
        red = cur_speed >= threshold_value
        base_img = base_red if red else base_blk
        gauge_img = Image.open(BytesIO(b64decode(gauge_img_data))).convert("1")
        base_img.paste(gauge_img.crop((20, 20, 160, 160)
                                      ).resize((100, 100)), (x_start, 70))

        # Write qrcode
        write_qrcode((x_start+120, 70),
                     get_spot_website_url(model_data["spot_id"]))

        # Write today bar chart
        hourlies_past = calc_prev_5_hours_wind_mean(
            now_local, graph_summary_data, TZ)
        hourlies_now = [(
            get_int_from_hour_key(get_hour_key(now_local)),
            float(graph_summary_data["last_ob_avg"])
        )]
        hourlies_future = calc_next_12_hours_wind_mean(
            now_local, model_data, TZ)
        hourlies = [cast(BarChartDatum, x) for x in chain(
            ({'label': hour, 'value': val, 'filled': True, "red": val >= threshold_value}
             for hour, val in hourlies_past),
            ({'label': hour, 'value': val, 'filled': True, "red": val >= threshold_value}
             for hour, val in hourlies_now),
            ({'label': hour, 'value': val, 'filled': False, "red": val >= threshold_value}
             for hour, val in hourlies_future)
        )]
        write_bar_chart((x_start, 300), hourlies, width=10)

        # Write this week bar chart
        _3hrsly_distant_future = calc_next_60_3hr_wind_mean(
            now_local, model_data, TZ)
        _3hrlies = []
        last_seen_label = None
        for label, val in _3hrsly_distant_future:
            if not last_seen_label:
                _3hrlies.append({"label": "", "value": val,
                                "filled": False, "red": val >= threshold_value})
                last_seen_label = label
            elif last_seen_label != label:
                # Every new day gets a filled bar
                _3hrlies.append({"label": label, "value": val,
                                "filled": True,  "red": val >= threshold_value})
                last_seen_label = label
            else:
                _3hrlies.append(
                    {"label": "", "value": val, "filled": False,  "red": val >= threshold_value})

        write_bar_chart((x_start, 450), _3hrlies, width=3, x_axis_skip=1)

    paint_header_col(10, spots_data[0]["graph_summary"])

    spot_x = 150
    for spot_data in spots_data:
        graph_summary_data: dict = spot_data["graph_summary"]
        if len(spot_data["models"]) > 1:
            logging.warning(f"Painter observed multiple models: {[x for x in spot_data['models'].keys()]} selecting one arbitrarily")
        model_data = list(spot_data["models"].values())[0]
        gauge_img_data: Union[str, bytes] = spot_data["gauge_img"]
        paint_spot_col(spot_x, graph_summary_data, gauge_img_data, model_data)
        spot_x += 220

    return (base_blk, base_red)


def paint_composite_img(spots_data:  Sequence[dict]) -> Image.Image:
    blk_img, red_img = paint_blk_and_red_imgs(spots_data)
    return composite_red_blk_imgs(blk_img, red_img)
