import bpy
from bpy.types import Node
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
    Node.note_show_txt       = BoolProperty(name="显示文本", default=True, update=tag_redraw)
    Node.note_show_img       = BoolProperty(name="显示图像", default=True, update=tag_redraw)
    Node.note_show_badge     = BoolProperty(name="显示序号", default=True, update=tag_redraw)
    Node.note_swap_order     = BoolProperty(name="交换位置", default=False, description="交换图片与文字的顺序", update=tag_redraw)
    Node.note_text           = StringProperty(name="文本", default="", options={'TEXTEDIT_UPDATE'}, update=tag_redraw)
    Node.note_image          = PointerProperty(name="图像", type=bpy.types.Image, update=tag_redraw)  # type: ignore
    Node.note_badge_index    = IntProperty(name="序号", default=0, min=0, description="徽章序号 (0为不显示)", update=tag_redraw)
    
    Node.note_text_color     = FloatVectorProperty(name="字体色", subtype='COLOR', size=4, default=prefs.default_text_color, min=0.0, max=1.0, update=tag_redraw)
    Node.note_txt_bg_color   = FloatVectorProperty(name="背景色", subtype='COLOR', size=4, default=prefs.default_txt_bg_color, min=0.0, max=1.0, update=tag_redraw)
    Node.note_badge_color    = FloatVectorProperty(name="背景色", subtype='COLOR', size=4, default=prefs.default_badge_color, min=0.0, max=1.0, update=tag_redraw)
    Node.note_font_size      = IntProperty(name="字号", default=prefs.default_font_size, min=4, max=500)
    Node.note_txt_bg_width   = IntProperty(name="背景宽度", default=prefs.default_txt_bg_width, min=1)
    Node.note_img_width      = IntProperty(name="图像宽度", default=prefs.default_img_width, min=10)
    Node.note_txt_width_mode = EnumProperty(name="宽度模式", items=get_txt_width_items, default=enum_to_int(prefs.default_txt_width_mode))
    Node.note_img_width_mode = EnumProperty(name="宽度模式", items=get_img_width_items, default=enum_to_int(prefs.default_img_width_mode))
    Node.note_txt_pos        = EnumProperty(name="对齐模式", items=align_items, default=prefs.default_txt_pos, description="文本位置")
    Node.note_img_pos        = EnumProperty(name="对齐模式", items=align_items, default=prefs.default_img_pos, description="图像位置")
    Node.note_txt_center     = BoolProperty(name="居中", default=False, description="顶/底对齐时居中")
    Node.note_img_center     = BoolProperty(name="居中", default=True, description="顶/底对齐时居中")

    Node.note_txt_offset     = IntVectorProperty(name="偏移", size=2, default=(0, 0), subtype='XYZ', description="文本偏移", update=tag_redraw)
    Node.note_img_offset     = IntVectorProperty(name="偏移", size=2, default=(0, 0), subtype='XYZ', description="图像偏移", update=tag_redraw)

def delete_props():
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
