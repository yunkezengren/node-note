import bpy
from bpy.types import Node
from bpy.props import StringProperty, IntProperty, FloatVectorProperty, BoolProperty, PointerProperty, FloatProperty, EnumProperty, IntVectorProperty
from .preferences import tag_redraw, align_items

# --- 属性更新回调 ---

def update_interactive_mode(self, context):
    # [修复] 不再通过回调启动操作符，只负责刷新界面
    context.area.tag_redraw()

def update_manual_text_width(self, context):
    self.note_txt_width_mode = 'MANUAL'
    tag_redraw(self, context)

def update_manual_img_width(self, context):
    self.note_img_width_mode = 'MANUAL'
    tag_redraw(self, context)

def update_note_image(self, context):
    node = self
    new_img = node.note_image
    prev_img_name = node.get("_note_last_img_name", "")
    if new_img:
        if not new_img.use_fake_user: new_img.use_fake_user = True
        if new_img.name != prev_img_name:
            if prev_img_name:
                old_img = bpy.data.images.get(prev_img_name)
                if old_img and old_img.use_fake_user and old_img.users == 1:
                    old_img.use_fake_user = False
            node["_note_last_img_name"] = new_img.name
    elif prev_img_name:
        old_img = bpy.data.images.get(prev_img_name)
        if old_img and old_img.use_fake_user and old_img.users == 1:
            old_img.use_fake_user = False
        node["_note_last_img_name"] = ""
    tag_redraw(self, context)

# --- 核心逻辑注入 ---

def inject_defaults_if_needed(node: Node):
    """如果节点未初始化，注入偏好设置的默认值"""
    from .preferences import pref
    prefs = pref()
    if not node.note_initialized and prefs:
        # 1. 注入文本相关默认值
        node.note_font_size = prefs.default_font_size
        node.note_text_color = prefs.default_text_color
        node.note_txt_bg_color = prefs.default_txt_bg_color

        # 2. 注入逻辑开关
        node.note_txt_width_mode = prefs.default_txt_width_mode
        node.note_txt_pos = prefs.default_text_pos

        # 3. 注入序号颜色默认值
        node.note_badge_color = prefs.default_badge_color

        # 标记已初始化，以后不再覆盖
        node.note_initialized = True

# --- 属性初始化 ---

def init_props():
    Node.note_text = StringProperty(name="内容", default="", update=tag_redraw, options={'TEXTEDIT_UPDATE'})
    Node.note_font_size = IntProperty(name="字号", default=10, min=4, max=500, update=tag_redraw)
    Node.note_txt_bg_color = FloatVectorProperty(name="背景",
                                                subtype='COLOR',
                                                size=4,
                                                default=(0.2, 0.3, 0.5, 0.9),
                                                min=0.0,
                                                max=1.0,
                                                update=tag_redraw)
    Node.note_text_color = FloatVectorProperty(name="文字",
                                              subtype='COLOR',
                                              size=4,
                                              default=(1.0, 1.0, 1.0, 1.0),
                                              min=0.0,
                                              max=1.0,
                                              update=tag_redraw)
    width_item_auto = [('AUTO', "跟随节点", "宽度自动跟随节点宽度")]
    txt_width_items_1 = [('FIT', "适应内容", "宽度自动适应文本内容"), ('MANUAL', "手动设置", "手动设置宽度")]
    img_width_items1 = [('ORIGINAL', "原始宽度", "显示图像原始宽度"), ('MANUAL', "手动设置", "手动设置宽度")]
    def get_txt_width_items(self, context):
        if self.bl_idname == "NodeReroute":
            return txt_width_items_1
        return width_item_auto + txt_width_items_1
    def get_img_width_items(self, context):
        if self.bl_idname == "NodeReroute":
            return img_width_items1
        return width_item_auto + img_width_items1
    Node.note_txt_width_mode = EnumProperty(name="宽度模式", items=get_txt_width_items, default=0, update=tag_redraw)
    Node.note_img_width_mode = EnumProperty(name="图宽模式", items=get_img_width_items, default=0, update=tag_redraw)
    Node.note_txt_bg_width = IntProperty(name="背景宽度", default=200, min=1, max=2000, update=tag_redraw)
    Node.note_img_width = IntProperty(name="图像宽度", default=140, min=10, max=2000, update=tag_redraw)
    Node.note_swap_content_order = BoolProperty(name="互换位置", default=False, update=tag_redraw)
    Node.note_z_order_switch = BoolProperty(name="层级切换", description="交换图片与文字的前后层级", default=False, update=tag_redraw)
    Node.note_badge_index = IntProperty(name="序号", default=0, min=0, update=tag_redraw, description="逻辑序号 (0为不显示)")
    Node.note_badge_color = FloatVectorProperty(name="序号颜色",
                                                  subtype='COLOR',
                                                  size=4,
                                                  default=(0.8, 0.1, 0.1, 1.0),
                                                  min=0.0,
                                                  max=1.0,
                                                  update=tag_redraw)
    Node.note_image = PointerProperty(name="图像", type=bpy.types.Image, update=update_note_image) # type: ignore
    Node.note_show_txt = BoolProperty(name="显示文本", default=True, update=tag_redraw)
    Node.note_show_img = BoolProperty(name="显示图片", default=True, update=tag_redraw)
    Node.note_show_badge = BoolProperty(name="显示序号", default=True, update=tag_redraw)
    Node.note_txt_pos = EnumProperty(name="对齐", items=align_items, default='TOP', update=tag_redraw, description="文本位置")
    Node.note_txt_offset = IntVectorProperty(name="文本偏移", size=2, default=(0, 0), update=tag_redraw, subtype='XYZ', description="文本偏移")
    Node.note_img_pos = EnumProperty(name="图对齐", items=align_items, default='TOP', update=tag_redraw, description="图像位置")
    Node.note_img_offset = IntVectorProperty(name="图像偏移", size=2, default=(0, 0), update=tag_redraw, subtype='XYZ', description="图像偏移")
    Node.note_initialized = BoolProperty(default=False)

def clear_props():
    props = [
        "note_text", "note_font_size", "note_txt_bg_color", "note_text_color", "note_txt_width_mode", "note_txt_bg_width", "note_swap_content_order",
        "note_image", "note_img_width", "note_show_img", "note_show_badge", "note_img_width_mode", "note_txt_pos", "note_txt_offset", "note_z_order_switch",
        "note_badge_index", "note_badge_color", "note_img_pos", "note_img_offset", "note_show_txt", "note_initialized"
    ]
    for prop in props:
        if hasattr(Node, prop):
            delattr(Node, prop)