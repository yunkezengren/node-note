from bpy.types import Node, Image
from .utils import RGBA, int2

class NotedNode(Node):
    note_show_txt: bool
    note_show_img: bool
    note_show_badge: bool
    note_swap_order: bool
    note_text: str
    note_image: Image | None
    note_badge_index: int
    note_text_color: RGBA
    note_txt_bg_color: RGBA
    note_badge_color: RGBA
    note_font_size: int
    note_txt_bg_width: int
    note_img_width: int
    note_txt_width_mode: str
    note_img_width_mode: str
    note_txt_pos: str
    note_img_pos: str
    note_txt_center: bool
    note_img_center: bool
    note_txt_offset: int2
    note_img_offset: int2
