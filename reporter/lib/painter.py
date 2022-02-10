from base64 import b64decode
from datetime import datetime
from io import BytesIO
import os
from pathlib import Path
import textwrap
from typing import Tuple, Union
from PIL import Image, ImageColor, ImageFont, ImageDraw
import pytz

# More fonts https://www.dafont.com/bitmap.php
# https://lucid.app/lucidchart/6a918925-6ff7-4aff-91ce-f57223f1599a/edit?beaconFlowId=B86FF4B9E5FF811D&invitationId=inv_afc6c6ae-b5ad-4c89-bf62-57c523d488b7&page=0_0#

# RGBA_WHITE = (255, 255, 255, 255)

DIMENSIONS = (800, 480)

WHITE_BIT = 1
BLACK_BIT = 0


def get_font_path():
    return os.path.join(Path(__file__).resolve().parent, "vcr_osd_mono_1.ttf")


def composite_red_blk(blk_img: Image.Image, red_img: Image.Image) -> Image.Image:
    img_color = Image.new("RGB", DIMENSIONS, (255, 255, 255))
    out = Image.composite(img_color, blk_img, blk_img)
    out = Image.composite(out, Image.new(
        'RGB', DIMENSIONS, (255, 0, 0)), red_img)
    return out


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

    def write_text(coords: Tuple[int, int], fnt: ImageFont.FreeTypeFont, text: str, red=False):
        d = draw_red if red else draw_blk
        d.text(coords, text, font=fnt, fill=BLACK_BIT, )

    def paint_col1(x_start: int):

        now_hst = pytz.timezone("HST").fromutc(
            datetime.utcnow())

        write_text((x_start, 70), fnt_40, "Now")
        write_text((x_start, 110), fnt_20, now_hst.strftime("%H:%M %Z"))
        write_text((x_start, 190), fnt_40, "Today")
        write_text((x_start, 230), fnt_20, now_hst.strftime("%b %d"))
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
        last_fetch_local = pytz.timezone("HST").fromutc(last_fetch)
        write_text((x_start, 40), fnt_12,
                   last_fetch_local.strftime("Update: %b %d, %H:%M %Z"))

        # Write Gauge
        gauge_img = Image.open(BytesIO(b64decode(gauge_img_data))).convert("1")
        base_blk.paste(gauge_img.crop((20, 20, 160, 160)
                                      ).resize((100, 100)), (x_start, 70))

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
