import bpy
from bpy.types import AddonPreferences, Context
from bpy.props import BoolProperty, StringProperty, FloatProperty, FloatVectorProperty, IntProperty, EnumProperty
from .typings import AlignMode, TextWidthMode, ImageWidthMode, BadgeScaleMode

align_items: list[tuple[AlignMode, str, str]] = [
    ('TOP', "顶部", ""),
    ('BOTTOM', "底部", ""),
    ('LEFT', "左侧", ""),
    ('RIGHT', "右侧", ""),
]
txt_width_items: list[tuple[TextWidthMode, str, str]] = [
    ('AUTO', "跟随节点", "宽度自动跟随节点宽度"),
    ('FIT', "适应内容", "宽度自动适应文本内容"),
    ('MANUAL', "手动设置", "手动设置宽度"),
]
img_width_items: list[tuple[ImageWidthMode, str, str]] = [
    ('AUTO', "跟随节点", "宽度自动跟随节点宽度"),
    ('ORIGINAL', "原始宽度", "显示图像原始宽度"),
    ('MANUAL', "手动设置", "手动设置宽度"),
]
badge_width_items: list[tuple[BadgeScaleMode, str, str]] = [
    ('RELATIVE', "相对缩放", "跟随节点编辑器缩放"),
    ('ABSOLUTE', "屏幕空间", "固定屏幕像素大小"),
]

def tag_redraw(self, context: Context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'NODE_EDITOR':
                area.tag_redraw()

sort_mode_items: list[tuple[str, str, str]] = [
    ('COLOR_BADGE', "颜色+序号", "按颜色升序，然后按序号升序"),
    ('BADGE_COLOR', "序号+颜色", "按序号升序，然后按颜色升序"),
]

class NodeNoteAddonPreferences(AddonPreferences):
    bl_idname = __package__  # type: ignore

    # 1. 全局设置
    cursor_warp_x          : IntProperty(default=0, min=1, max=500, description="快捷键唤出面板时鼠标偏移")
    show_all_notes         : BoolProperty(name="显示所有", default=True)
    show_selected_only     : BoolProperty(name="仅显示选中", default=False, description="仅显示选中节点的笔记")
    dependent_overlay      : BoolProperty(name="跟随叠加层", default=True, description="当节点编辑器叠加层关闭时，是否隐藏笔记")
    show_badge_lines       : BoolProperty(name="显示逻辑连线", default=True, description="显示节点之间的序号连线")
    is_interactive_mode    : BoolProperty(name="交互模式", default=False, description="点击节点即可编号，右键或ESC退出")
    list_sort_mode         : EnumProperty(name="排序模式", items=sort_mode_items, default='BADGE_COLOR', description="选择列表排序方式")
    # todo 改进遮挡
    use_occlusion          : BoolProperty(name="自动遮挡", default=False)
    tag_mode_prepend       : BoolProperty(name="前缀模式", default=True, description="特殊字符添加到已有文本前")
    navigator_search       : StringProperty(name="搜索", default="", options={'TEXTEDIT_UPDATE'})
    line_separator         : StringProperty(name="换行符", default=";|\\", options={'TEXTEDIT_UPDATE'}, description="文本中用于换行的分隔符，支持多个（用 | 分隔），如 : ;|\\ ")

    # 2. 文本设置区
    default_font_size      : IntProperty(name="默认字号", default=8, min=4, max=100)
    font_path              : StringProperty(default='', subtype='FILE_PATH', options={'TEXTEDIT_UPDATE'}, description="字体文件路径,留空使用默认字体")
    default_text_color     : FloatVectorProperty(name="默认字色", subtype='COLOR', size=4, default=(1.0, 1.0, 1.0, 1.0), min=0, max=1)
    default_txt_bg_color   : FloatVectorProperty(name="默认背景色", subtype='COLOR', size=4, default=(0.2, 0.3, 0.5, 0.9), min=0, max=1)

    default_txt_width_mode : EnumProperty(name="宽度模式", items=txt_width_items, default=0)
    default_txt_bg_width   : IntProperty(name="默认文本背景宽度", default=200, min=50, max=2000)
    default_txt_pos       : EnumProperty(name="默认对齐", items=align_items, default='TOP')

    # 3. 图像设置区
    default_img_width_mode : EnumProperty(name="宽度模式", items=img_width_items, default=0)
    default_img_width      : IntProperty(name="默认图像宽度", default=300, min=10, max=4000)
    default_img_pos      : EnumProperty(name="默认对齐", items=align_items, default='TOP')

    # 4. 序号设置区
    default_badge_color    : FloatVectorProperty(name="圆背景色", subtype='COLOR', size=4, default=(0.8, 0.1, 0.1, 1.0), min=0, max=1)
    badge_scale_mode       : EnumProperty(name="缩放模式", items=badge_width_items, default='ABSOLUTE')
    badge_rel_scale        : FloatProperty(name="序号缩放", default=1.0, min=0.1, max=20.0)
    badge_abs_scale        : FloatProperty(name="屏幕空间缩放", default=1.0, min=0.1, max=10.0)
    badge_font_color       : FloatVectorProperty(name="数字颜色", subtype='COLOR', size=4, default=(1.0, 1.0, 1.0, 1.0), min=0, max=1, description="所有序号的数字颜色")
    badge_line_color       : FloatVectorProperty(name="连线颜色", subtype='COLOR', size=4, default=(1.0, 0.8, 0.2, 0.8), min=0, max=1)
    badge_line_thickness   : IntProperty(name="连线宽度", default=4, min=1, max=40)

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

    show_global      : BoolProperty(name="显示全局设置", default=True)
    show_text        : BoolProperty(name="显示文字笔记", default=True)
    show_image       : BoolProperty(name="显示图片笔记", default=True)
    show_badge       : BoolProperty(name="显示序号笔记", default=True)
    show_list        : BoolProperty(name="显示笔记列表", default=True)

    show_red             : BoolProperty(name="显示红", default=True, description="显示红")
    show_green           : BoolProperty(name="显示绿", default=True, description="显示绿")
    show_blue            : BoolProperty(name="显示蓝", default=True, description="显示蓝")
    show_orange          : BoolProperty(name="显示橙", default=True, description="显示橙")
    show_purple          : BoolProperty(name="显示紫", default=True, description="显示紫")
    show_other           : BoolProperty(name="显示杂", default=True, description="显示杂")
    hide_img_by_bg       : BoolProperty(name="同时过滤图片", default=True, description="过滤文本时是否同时过滤对应节点的图片")

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

        layout.label(text="部分属性更改后重启Blender后生效:", icon='INFO')

        # region 文本笔记
        txt_box = layout.box()
        txt_box.label(text="文本笔记默认设置", icon='FILE_TEXT')

        split_txt = txt_box.split(factor=0.5)
        split_txt.prop(self, "default_font_size", text="字号")
        split_txt.prop(self, "font_path", text="字体")

        split_color = txt_box.split(factor=0.5)
        split_color.row().prop(self, "default_text_color", text="文本色")
        split_color.row().prop(self, "default_txt_bg_color", text="背景色")

        row = txt_box.row()
        row.prop(self, "default_txt_width_mode", text="宽度")
        if self.default_txt_width_mode == 'MANUAL':
            row.prop(self, "default_txt_bg_width", text="")
        row.prop(self, "default_txt_pos", text="对齐")

        txt_box.label(text="背景颜色预设:")
        box_preset = txt_box.box()
        split_preset = box_preset.split(factor=0.05)
        split_preset.label(text="")
        split_preset = split_preset.column()
        grid_color = split_preset.grid_flow(row_major=True, columns=6, align=True)
        for i in range(1, 7):
            grid_color.prop(self, f"col_preset_{i}", text="")

        grid_label = split_preset.grid_flow(row_major=True, columns=6, align=True)
        for i in range(1, 7):
            grid_label.prop(self, f"label_preset_{i}", text="")
        # endregion

        # region 图像笔记
        box = layout.box()
        box.label(text="图像笔记默认设置", icon='IMAGE_DATA')

        col = box.column()
        row = col.row()

        row.prop(self, "default_img_width_mode", text="宽度")
        if self.default_img_width_mode == 'MANUAL':
            row.prop(self, "default_img_width", text="")
        row.prop(self, "default_img_pos", text="对齐")
        # endregion

        # region 序号笔记
        badge_box = layout.box()
        badge_box.label(text="序号笔记默认设置", icon='EVENT_NDOF_BUTTON_1')

        split = badge_box.split(factor=0.5)
        split.row().prop(self, "default_badge_color", text="背景色")
        split.row().prop(self, "badge_font_color", text="文本色")

        row_set = badge_box.row(align=True)
        row_set.prop(self, "badge_scale_mode", text="缩放")
        if self.badge_scale_mode == 'ABSOLUTE':
            row_set.prop(self, "badge_abs_scale", text="屏幕缩放")
        else:
            row_set.prop(self, "badge_rel_scale", text="相对缩放")

        row_set = badge_box.split(factor=0.3)
        row_set.prop(self, "show_badge_lines", text="显示连线", icon='EMPTY_ARROWS')
        row_set.row().prop(self, "badge_line_color", text="颜色")
        row_set.prop(self, "badge_line_thickness", text="线宽")
        # endregion

def pref() -> NodeNoteAddonPreferences:
    assert __package__ is not None
    return bpy.context.preferences.addons[__package__].preferences
