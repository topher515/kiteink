from datetime import datetime
import os
from pathlib import Path
from typing import Tuple
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


def paint_blk_and_red_imgs(graph_summary_data: dict, model_data: dict) -> Tuple[Image.Image, Image.Image]:
    '''
    Returns black
    '''
    base_blk = Image.new("1", DIMENSIONS, WHITE_BIT)
    base_red = Image.new("1", DIMENSIONS, WHITE_BIT)

    # make a blank image for the text, initialized to transparent text color
    # txt_img = Image.new("L", base.size, BLACK_8)
    # get a font
    fnt_40 = ImageFont.truetype(get_font_path(), 40)
    fnt_30 = ImageFont.truetype(get_font_path(), 30)
    fnt_20 = ImageFont.truetype(get_font_path(), 20)
    # get a drawing context
    draw_blk = ImageDraw.Draw(base_blk)
    draw_red = ImageDraw.Draw(base_red)
    # draw text, half opacity

    def write_text(coords: Tuple[int, int], fnt: ImageFont.FreeTypeFont, text: str, red=False):
        d = draw_red if red else draw_blk
        d.text(coords, text, font=fnt, fill=BLACK_BIT)

    now_hst = pytz.timezone("HST").fromutc(
        datetime.utcnow())

    write_text((10, 10), fnt_40, "Now")
    write_text((10, 60), fnt_20, now_hst.strftime("%H:%M %Z"))
    write_text((10, 160), fnt_40, "Today")
    write_text((10, 200), fnt_20, now_hst.strftime("%b %d"))
    write_text((10, 340), fnt_40, "7 Day", red=True)

    return (base_blk, base_red)


def paint_display_image(graph_summary_data: dict, model_data: dict) -> Image.Image:
    blk_img, red_img = paint_blk_and_red_imgs(
        graph_summary_data,
        model_data
    )
    return composite_red_blk(blk_img, red_img)
