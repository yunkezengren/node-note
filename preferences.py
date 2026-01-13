import bpy
from bpy.types import AddonPreferences, Context
from bpy.props import BoolProperty, StringProperty, FloatProperty, FloatVectorProperty, IntProperty, EnumProperty

align_items = [('TOP', "顶部", ""), ('BOTTOM', "底部", ""), ('LEFT', "左侧", ""), ('RIGHT', "右侧", "")]
txt_width_items = [('AUTO', "跟随节点", "宽度自动跟随节点宽度"), ('FIT', "适应内容", "宽度自动适应文本内容"), ('MANUAL', "手动设置", "手动设置宽度")]
img_width_items = [('AUTO', "跟随节点", "宽度自动跟随节点宽度"), ('ORIGINAL', "原始宽度", "显示图像原始宽度"), ('MANUAL', "手动设置", "手动设置宽度")]
badge_width_items = [('RELATIVE', "相对缩放", "跟随节点编辑器缩放"), ('ABSOLUTE', "屏幕空间", "固定屏幕像素大小")]

def get_txt_width_items(self, context):
    if self.bl_idname == "NodeReroute":
        return txt_width_items[1:]
    return txt_width_items

def get_img_width_items(self, context):
    if self.bl_idname == "NodeReroute":
        return img_width_items[1:]
    return img_width_items

def tag_redraw(self, context: Context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'NODE_EDITOR':
                area.tag_redraw()

class NodeNoteAddonPreferences(AddonPreferences):
    bl_idname = __package__

    # 1. 全局设置
    cursor_warp_x          : IntProperty(default=0, min=1, max=500, description="快捷键唤出面板时鼠标偏移")
    show_all_notes         : BoolProperty(name="显示所有", default=True, update=tag_redraw)
    show_badge_lines       : BoolProperty(name="显示逻辑连线", default=True, update=tag_redraw, description="显示节点之间的序号连线")
    is_interactive_mode    : BoolProperty(name="交互模式", default=False, update=tag_redraw, description="点击节点即可编号，右键或ESC退出")
    sort_by_badge          : BoolProperty(name="按序号排序", default=True, update=tag_redraw, description="勾选后，有序号的节点将优先显示在列表顶部")
    # todo 实现这个
    use_occlusion          : BoolProperty(name="自动遮挡", default=False, update=tag_redraw)
    tag_mode_prepend       : BoolProperty(name="前缀模式", default=True, description="特殊字符添加到已有文本前")
    navigator_search       : StringProperty(name="搜索", default="")

    show_global      : BoolProperty(name="显示全局设置", default=True, update=tag_redraw)
    show_text        : BoolProperty(name="显示文字笔记", default=True, update=tag_redraw)
    show_image       : BoolProperty(name="显示图片笔记", default=True, update=tag_redraw)
    show_badge       : BoolProperty(name="显示序号笔记", default=True, update=tag_redraw)
    show_list        : BoolProperty(name="显示笔记列表", default=True, update=tag_redraw)

    show_red             : BoolProperty(name="显示红", default=True, description="显示红", update=tag_redraw)
    show_green           : BoolProperty(name="显示绿", default=True, description="显示绿", update=tag_redraw)
    show_blue            : BoolProperty(name="显示蓝", default=True, description="显示蓝", update=tag_redraw)
    show_orange          : BoolProperty(name="显示橙", default=True, description="显示橙", update=tag_redraw)
    show_purple          : BoolProperty(name="显示紫", default=True, description="显示紫", update=tag_redraw)
    show_other           : BoolProperty(name="显示杂", default=True, description="显示杂", update=tag_redraw)
    hide_img_by_bg       : BoolProperty(name="同时过滤图片", default=True, description="过滤文本时是否同时过滤对应节点的图片", update=tag_redraw)

    # 2. 文本设置区
    default_font_size      : IntProperty(name="默认字号", default=8, min=4, max=100)
    default_text_color     : FloatVectorProperty(name="默认字色", subtype='COLOR', size=4, default=(1.0, 1.0, 1.0, 1.0), min=0, max=1)
    default_txt_bg_color   : FloatVectorProperty(name="默认背景色", subtype='COLOR', size=4, default=(0.2, 0.3, 0.5, 0.9), min=0, max=1)
    line_separator         : StringProperty(name="换行符", default=";|\\", description="文本中用于换行的分隔符，支持多个（用 | 分隔），如 : ;|\\ ")

    default_txt_width_mode : EnumProperty(name="宽度模式", items=txt_width_items, default=0, update=tag_redraw)
    default_text_pos       : EnumProperty(name="默认对齐", items=align_items, default='TOP')

    # 3. 图像设置区
    img_default_align      : EnumProperty(name="默认对齐", items=align_items, default='TOP')

    # 4. 序号设置区
    badge_rel_scale        : FloatProperty(name="序号缩放", default=1.0, min=0.1, max=20.0, update=tag_redraw)
    badge_scale_mode       : EnumProperty(name="缩放模式", items=badge_width_items, default='ABSOLUTE', update=tag_redraw)
    badge_abs_scale        : FloatProperty(name="屏幕空间缩放", default=1.0, min=0.1, max=10.0, update=tag_redraw)
    default_badge_color    : FloatVectorProperty(name="圆背景色", subtype='COLOR', size=4, default=(0.8, 0.1, 0.1, 1.0), min=0, max=1, update=tag_redraw)
    badge_font_color       : FloatVectorProperty(name="数字颜色", subtype='COLOR', size=4, default=(1.0, 1.0, 1.0, 1.0), min=0, max=1, description="所有序号的数字颜色", update=tag_redraw)
    badge_line_color       : FloatVectorProperty(name="连线颜色", subtype='COLOR', size=4, default=(1.0, 0.8, 0.2, 0.8), min=0, max=1, update=tag_redraw)
    badge_line_thickness   : IntProperty(name="连线宽度", default=4, min=1, max=40, update=tag_redraw)

    # 预设颜色
    col_preset_1           : FloatVectorProperty(name="预设红", subtype='COLOR', size=4, default=(0.6, 0.1, 0.1, 0.9), min=0, max=1)
    col_preset_2           : FloatVectorProperty(name="预设绿", subtype='COLOR', size=4, default=(0.2, 0.5, 0.2, 0.9), min=0, max=1)
    col_preset_3           : FloatVectorProperty(name="预设蓝", subtype='COLOR', size=4, default=(0.2, 0.3, 0.5, 0.9), min=0, max=1)
    col_preset_4           : FloatVectorProperty(name="预设橙", subtype='COLOR', size=4, default=(0.8, 0.35, 0.05, 0.9), min=0, max=1)
    col_preset_5           : FloatVectorProperty(name="预设紫", subtype='COLOR', size=4, default=(0.4, 0.1, 0.5, 0.9), min=0, max=1)
    col_preset_6           : FloatVectorProperty(name="预设无", subtype='COLOR', size=4, default=(0.0, 0.0, 0.0, 0.0), min=0, max=1)

    # 预设标签
    label_preset_1         : StringProperty(name="标签1", default="红")
    label_preset_2         : StringProperty(name="标签2", default="绿")
    label_preset_3         : StringProperty(name="标签3", default="蓝")
    label_preset_4         : StringProperty(name="标签4", default="橙")
    label_preset_5         : StringProperty(name="标签5", default="紫")
    label_preset_6         : StringProperty(name="标签6", default="无")

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        row = box.row()
        row.label(text="全局设置", icon='WORLD_DATA')
        col = box.column()
        split = col.split(factor=0.5)
        split1 = split.row()
        split.prop(self, "cursor_warp_x", text="默认鼠标偏移")

        split1.label(text="面板快捷键:", icon='KEYINGSET')
        wm = context.window_manager
        kc = wm.keyconfigs.user
        km = kc.keymaps.get('Node Editor')
        if km:
            kmi = None
            for k in km.keymap_items:
                if k.idname == 'node.note_quick_edit':
                    kmi = k
                    break
            if kmi:
                split1.prop(kmi, "type", text="", full_event=True)
            else:
                split1.label(text="快捷键未注册", icon='ERROR')

        # ============================================================================================
        box = layout.box()
        row = box.row()
        row.label(text="文本笔记默认设置", icon='FILE_TEXT')
        row.operator("node.note_reset_prefs", text="", icon='LOOP_BACK').target_section = 'TEXT'

        col = box.column(align=True)
        row = col.row(align=True)
        row.prop(self, "default_font_size")
        row.prop(self, "default_text_color", text="")
        row.prop(self, "default_txt_bg_color", text="")

        row = col.row(align=True)
        row.prop(self, "text_default_fit", text="默认适应文本")
        row.prop(self, "default_text_pos", text="默认对齐模式")

        col.separator()
        col.label(text="文本背景颜色预设:")
        grid_color = col.grid_flow(row_major=True, columns=6, align=True)
        for i in range(1, 6):
            grid_color.prop(self, f"col_preset_{i}", text="")

        grid_label = col.grid_flow(row_major=True, columns=6, align=True)
        for i in range(1, 6):
            grid_label.prop(self, f"label_preset_{i}", text="")

        # ============================================================================================
        box = layout.box()
        row = box.row()
        row.label(text="图像笔记默认设置", icon='IMAGE_DATA')
        row.operator("node.note_reset_prefs", text="", icon='LOOP_BACK').target_section = 'IMG'
        col = box.column(align=True)
        col.prop(self, "img_default_align", text="默认对齐模式")

        # ============================================================================================
        box = layout.box()
        row = box.row()
        row.label(text="序号笔记默认设置", icon='EVENT_NDOF_BUTTON_1')
        row.operator("node.note_reset_prefs", text="", icon='LOOP_BACK').target_section = 'SEQ'

        col = box.column(align=True)
        split = col.split(factor=0.5)
        split.prop(self, "badge_scale_mode")
        if self.badge_scale_mode == 'ABSOLUTE':
            split.prop(self, "badge_abs_scale")
        else:
            split.prop(self, "badge_rel_scale")
        split = col.split(factor=0.5)
        split.row().prop(self, "badge_font_color", text="文本色")
        split.row().prop(self, "default_badge_color", text="背景色")

def pref() -> NodeNoteAddonPreferences:
    assert __package__ is not None
    return bpy.context.preferences.addons[__package__].preferences
