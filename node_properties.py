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
    Node.note_show_txt       = BoolProperty(name="Show Text", default=True, update=tag_redraw)
    Node.note_show_img       = BoolProperty(name="Show Image", default=True, update=tag_redraw)
    Node.note_show_badge     = BoolProperty(name="Show Index", default=True, update=tag_redraw)
    Node.note_swap_order     = BoolProperty(name="Swap Position", default=False, description="Swap image and text order", update=tag_redraw)
    Node.note_text           = StringProperty(name="Text", default="", options={'TEXTEDIT_UPDATE'}, update=tag_redraw)
    Node.note_image          = PointerProperty(name="Image", type=bpy.types.Image, update=tag_redraw) # type: ignore
    Node.note_badge_index    = IntProperty(name="Index", default=0, min=0, description="Badge Index (0 to hide)", update=tag_redraw)
    
    Node.note_text_color     = FloatVectorProperty(name="Font Color", subtype='COLOR', size=4, default=prefs.default_text_color, min=0.0, max=1.0, update=tag_redraw)
    Node.note_txt_bg_color   = FloatVectorProperty(name="Background Color", subtype='COLOR', size=4, default=prefs.default_txt_bg_color, min=0.0, max=1.0, update=tag_redraw)
    Node.note_badge_color    = FloatVectorProperty(name="Background Color", subtype='COLOR', size=4, default=prefs.default_badge_color, min=0.0, max=1.0, update=tag_redraw)
    Node.note_font_size      = IntProperty(name="Font Size", default=prefs.default_font_size, min=4, max=500)
    Node.note_txt_bg_width   = IntProperty(name="Background Width", default=prefs.default_txt_bg_width, min=1)
    Node.note_img_width      = IntProperty(name="Image Width", default=prefs.default_img_width, min=10)
    Node.note_txt_width_mode = EnumProperty(name="Width Mode", items=get_txt_width_items, default=enum_to_int(prefs.default_txt_width_mode))
    Node.note_img_width_mode = EnumProperty(name="Width Mode", items=get_img_width_items, default=enum_to_int(prefs.default_img_width_mode))
    Node.note_txt_pos        = EnumProperty(name="Alignment Mode", items=align_items, default=prefs.default_txt_pos, description="Text Position")
    Node.note_img_pos        = EnumProperty(name="Alignment Mode", items=align_items, default=prefs.default_img_pos, description="Image Position")
    Node.note_txt_center     = BoolProperty(name="Center", default=False, description="Center when top/bottom aligned")
    Node.note_img_center     = BoolProperty(name="Center", default=True, description="Center when top/bottom aligned")

    Node.note_txt_offset     = IntVectorProperty(name="Offset", size=2, default=(0, 0), subtype='XYZ', description="Text and Image offset", update=tag_redraw)
    Node.note_img_offset     = IntVectorProperty(name="Offset", size=2, default=(0, 0), subtype='XYZ', description="Image offset", update=tag_redraw)

# 不要忘记往 NotedNode 和 NODE_OT_note_copy_active_style 新增
base_props = [
    "note_text",
    "note_image",
    "note_badge_index",
    "note_show_txt",
    "note_show_img",
    "note_show_badge",
]
style_props = [
    "note_font_size",
    "note_text_color",
    "note_txt_bg_color",
    "note_txt_bg_width",
    "note_img_width",
    "note_swap_order",
    "note_badge_color",
    "note_txt_width_mode",
    "note_img_width_mode",
    "note_txt_pos",
    "note_img_pos",
    "note_txt_center",
    "note_img_center",
    "note_txt_offset",
    "note_img_offset",
]

def delete_props():
    for prop in base_props + style_props:
        if hasattr(Node, prop):
            delattr(Node, prop)
