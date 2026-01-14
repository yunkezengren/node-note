import bpy
from bpy.types import Node, Context
from bpy.props import StringProperty, IntProperty, FloatVectorProperty, BoolProperty, PointerProperty, EnumProperty, IntVectorProperty
from .preferences import pref, tag_redraw, align_items, txt_width_items, img_width_items

def get_txt_width_items(self, context):
    if self.bl_idname == "NodeReroute":
        return txt_width_items[1:]
    return txt_width_items

def get_img_width_items(self, context):
    if self.bl_idname == "NodeReroute":
        return img_width_items[1:]
    return img_width_items

def enum_to_int(enum: str):
    if enum == txt_width_items[0][0]:
        return 0
    if enum == txt_width_items[1][0] or enum == img_width_items[1][0]:
        return 1
    if enum == txt_width_items[2][0]:
        return 2

def init_props():
    prefs = pref()
    Node.note_show_txt       = BoolProperty(default=True)
    Node.note_show_img       = BoolProperty(default=True)
    Node.note_show_badge     = BoolProperty(default=True)
    Node.note_swap_order     = BoolProperty(default=False, description="交换图片与文字的顺序")
    Node.note_text           = StringProperty(default="", options={'TEXTEDIT_UPDATE'})
    Node.note_image          = PointerProperty(type=bpy.types.Image)  # type: ignore
    Node.note_badge_index    = IntProperty(default=0, min=0, description="徽章序号 (0为不显示)")
    
    Node.note_text_color     = FloatVectorProperty(subtype='COLOR', size=4, default=prefs.default_text_color, min=0.0, max=1.0)
    Node.note_txt_bg_color   = FloatVectorProperty(subtype='COLOR', size=4, default=prefs.default_txt_bg_color, min=0.0, max=1.0)
    Node.note_badge_color    = FloatVectorProperty(subtype='COLOR', size=4, default=prefs.default_badge_color, min=0.0, max=1.0)
    Node.note_font_size      = IntProperty(default=prefs.default_font_size, min=4, max=500)
    Node.note_txt_bg_width   = IntProperty(default=prefs.default_txt_bg_width, min=1, max=2000)
    Node.note_img_width      = IntProperty(default=prefs.default_img_width, min=10, max=2000)
    Node.note_txt_width_mode = EnumProperty(items=get_txt_width_items, default=enum_to_int(prefs.default_txt_width_mode))
    Node.note_img_width_mode = EnumProperty(items=get_img_width_items, default=enum_to_int(prefs.default_img_width_mode))
    Node.note_txt_pos        = EnumProperty(items=align_items, default=prefs.default_txt_pos, description="文本位置")
    Node.note_img_pos        = EnumProperty(items=align_items, default=prefs.default_img_pos, description="图像位置")
    Node.note_txt_center     = BoolProperty(default=False, description="顶/底对齐时居中")
    Node.note_img_center     = BoolProperty(default=True, description="顶/底对齐时居中")

    Node.note_txt_offset     = IntVectorProperty(size=2, default=(0, 0), subtype='XYZ', description="文本偏移")
    Node.note_img_offset     = IntVectorProperty(size=2, default=(0, 0), subtype='XYZ', description="图像偏移")

def clear_props():
    props = [
        "note_text",
        "note_image",
        "note_font_size",
        "note_text_color",
        "note_txt_bg_color",
        "note_txt_bg_width",
        "note_img_width",
        "note_swap_order",
        "note_badge_index",
        "note_badge_color",
        "note_show_txt",
        "note_show_img",
        "note_show_badge",
        "note_txt_width_mode",
        "note_img_width_mode",
        "note_txt_pos",
        "note_img_pos",
        "note_txt_center",
        "note_img_center",
        "note_txt_offset",
        "note_img_offset",
    ]
    for prop in props:
        if hasattr(Node, prop):
            delattr(Node, prop)
