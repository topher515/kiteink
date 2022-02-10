from PIL import Image, ImageColor

RGB_WHITE = (255, 255, 255)


def paint_display_image(graph_summary_data: dict, model_data: dict) -> Image.Image:
    img = Image.new("RGB", (1280, 800), RGB_WHITE)

    return img
