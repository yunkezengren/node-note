import bpy
from bpy.types import Node
from bpy.props import StringProperty, IntProperty, FloatVectorProperty, BoolProperty, PointerProperty, FloatProperty, EnumProperty, IntVectorProperty
from .preferences import tag_redraw

# --- 属性更新回调 ---

def update_interactive_mode(self, context):
    # [修复] 不再通过回调启动操作符，只负责刷新界面
    context.area.tag_redraw()

def update_manual_text_width(self, context):
    self.na_txt_width_mode = 'MANUAL'
    tag_redraw(self, context)

def update_manual_img_width(self, context):
    self.na_img_width_mode = 'MANUAL'
    tag_redraw(self, context)

def update_na_image(self, context):
    node = self
    new_img = node.na_image
    prev_img_name = node.get("_na_last_img_name", "")
    if new_img:
        if not new_img.use_fake_user: new_img.use_fake_user = True
        if new_img.name != prev_img_name:
            if prev_img_name:
                old_img = bpy.data.images.get(prev_img_name)
                if old_img and old_img.use_fake_user and old_img.users == 1:
                    old_img.use_fake_user = False
            node["_na_last_img_name"] = new_img.name
    elif prev_img_name:
        old_img = bpy.data.images.get(prev_img_name)
        if old_img and old_img.use_fake_user and old_img.users == 1:
            old_img.use_fake_user = False
        node["_na_last_img_name"] = ""
    tag_redraw(self, context)

# --- 核心逻辑注入 ---

def inject_defaults_if_needed(node: Node):
    """如果节点未初始化，注入偏好设置的默认值"""
    from .preferences import pref
    prefs = pref()
    if not node.na_is_initialized and prefs:
        # 1. 注入文本相关默认值
        node.na_font_size = prefs.text_default_size
        node.na_text_color = prefs.text_default_color
        node.na_txt_bg_color = prefs.bg_default_color

        # 2. 注入逻辑开关
        node.na_text_fit_content = prefs.text_default_fit
        node.na_txt_pos = prefs.text_default_align

        # 3. 注入序号颜色默认值
        node.na_sequence_color = prefs.seq_bg_color

        # 标记已初始化，以后不再覆盖
        node.na_is_initialized = True

# --- 属性初始化 ---

def init_props():
    Node.na_text = StringProperty(name="内容", default="", update=tag_redraw, options={'TEXTEDIT_UPDATE'})
    Node.na_font_size = IntProperty(name="字号", default=10, min=4, max=500, update=tag_redraw)
    Node.na_txt_bg_color = FloatVectorProperty(name="背景",
                                                subtype='COLOR',
                                                size=4,
                                                default=(0.2, 0.3, 0.5, 0.9),
                                                min=0.0,
                                                max=1.0,
                                                update=tag_redraw)
    Node.na_text_color = FloatVectorProperty(name="文字",
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
    Node.na_txt_width_mode = EnumProperty(name="宽度模式", items=get_txt_width_items, default=0, update=tag_redraw)
    Node.na_img_width_mode = EnumProperty(name="图宽模式", items=get_img_width_items, default=0, update=tag_redraw)
    Node.na_txt_bg_width = IntProperty(name="背景宽度", default=200, min=1, max=2000, update=update_manual_text_width)
    Node.na_img_width = IntProperty(name="图像宽度", default=140, min=10, max=2000, update=update_manual_img_width)
    Node.na_swap_content_order = BoolProperty(name="互换位置", default=False, update=tag_redraw)
    Node.na_z_order_switch = BoolProperty(name="层级切换", description="交换图片与文字的前后层级", default=False, update=tag_redraw)
    Node.na_seq_index = IntProperty(name="序号", default=0, min=0, update=tag_redraw, description="逻辑序号 (0为不显示)")
    Node.na_sequence_color = FloatVectorProperty(name="序号颜色",
                                                  subtype='COLOR',
                                                  size=4,
                                                  default=(0.8, 0.1, 0.1, 1.0),
                                                  min=0.0,
                                                  max=1.0,
                                                  update=tag_redraw)
    Node.na_image = PointerProperty(name="图像", type=bpy.types.Image, update=update_na_image) # type: ignore
    Node.na_show_txt = BoolProperty(name="显示文本", default=True, update=tag_redraw)
    Node.na_show_img = BoolProperty(name="显示图片", default=True, update=tag_redraw)
    Node.na_show_seq = BoolProperty(name="显示序号", default=True, update=tag_redraw)
    align_items = [('TOP', "顶部", ""), ('BOTTOM', "底部", ""), ('LEFT', "左侧", ""), ('RIGHT', "右侧", "")]
    Node.na_txt_pos = EnumProperty(name="对齐", items=align_items, default='TOP', update=tag_redraw, description="文本位置")
    Node.na_txt_offset = IntVectorProperty(name="文本偏移", size=2, default=(0, 0), update=tag_redraw, subtype='XYZ', description="文本偏移")
    Node.na_img_pos = EnumProperty(name="图对齐", items=align_items, default='TOP', update=tag_redraw, description="图像位置")
    Node.na_img_offset = IntVectorProperty(name="图像偏移", size=2, default=(0, 0), update=tag_redraw, subtype='XYZ', description="图像偏移")
    Node.na_is_initialized = BoolProperty(default=False)

def clear_props():
    props = [
        "na_text", "na_font_size", "na_txt_bg_color", "na_text_color", "na_txt_width_mode", "na_txt_bg_width", "na_swap_content_order",
        "na_image", "na_img_width", "na_show_img", "na_show_seq", "na_img_width_mode", "na_txt_pos", "na_txt_offset", "na_z_order_switch",
        "na_seq_index", "na_sequence_color", "na_img_pos", "na_img_offset", "na_show_txt", "na_is_initialized"
    ]
    for p in props:
        if hasattr(Node, p): delattr(Node, p)
    for p in dir(bpy.types.Scene):
        if p.startswith("na_"): delattr(bpy.types.Scene, p)