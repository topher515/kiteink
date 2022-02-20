
from PIL import Image
from waveshare_epd import epd7in5b_V2


def epd_display_images(img_blk: Image.Image, img_red: Image.Image):
    try:
        epd = epd7in5b_V2.EPD()
        epd.init()
        # epd.Clear()  # Doesn't seem necessary but is in examples!
        epd.display(epd.getbuffer(img_blk), epd.getbuffer(img_red))
        epd.sleep()

    except Exception:
        epd7in5b_V2.epdconfig.module_exit()  # type: ignore
        raise
