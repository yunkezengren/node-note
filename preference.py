import bpy
from bpy.types import AddonPreferences

def tag_redraw(self, context):
    try:
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'NODE_EDITOR': area.tag_redraw()
    except:
        pass

class NodeMemoAddonPreferences(AddonPreferences):
    bl_idname = __package__

    # 1. 全局设置
    show_annotations: bpy.props.BoolProperty(name="显示所有", default=True, update=tag_redraw)
    show_global_sequence: bpy.props.BoolProperty(name="显示序号", default=True, update=tag_redraw, description="全局显示或隐藏所有序号")
    show_sequence_lines: bpy.props.BoolProperty(name="显示逻辑连线", default=False, update=tag_redraw)
    is_interactive_mode: bpy.props.BoolProperty(name="交互模式", default=False, update=tag_redraw, description="点击节点即可编号，右键或ESC退出")
    sort_by_sequence: bpy.props.BoolProperty(name="按序号排序", default=False, update=tag_redraw, description="勾选后，有序号的节点将优先显示在列表顶部")
    use_occlusion: bpy.props.BoolProperty(name="自动遮挡", default=False, update=tag_redraw)
    tag_mode_prepend: bpy.props.BoolProperty(name="前缀模式", default=True)
    navigator_search: bpy.props.StringProperty(name="搜索", default="")
    filter_red: bpy.props.BoolProperty(name="过滤红", default=True, update=tag_redraw)
    filter_green: bpy.props.BoolProperty(name="过滤绿", default=True, update=tag_redraw)
    filter_blue: bpy.props.BoolProperty(name="过滤蓝", default=True, update=tag_redraw)
    filter_orange: bpy.props.BoolProperty(name="过滤橙", default=True, update=tag_redraw)
    filter_purple: bpy.props.BoolProperty(name="过滤紫", default=True, update=tag_redraw)
    filter_other: bpy.props.BoolProperty(name="过滤杂", default=True, update=tag_redraw)

    # 2. 序号设置区
    seq_radius: bpy.props.FloatProperty(name="序号圆半径", default=7.0, min=1.0, max=50.0, update=tag_redraw)
    seq_bg_color: bpy.props.FloatVectorProperty(name="圆背景色",
                                                subtype='COLOR',
                                                size=4,
                                                default=(0.8, 0.1, 0.1, 1.0),
                                                min=0,
                                                max=1,
                                                update=tag_redraw)
    seq_font_size: bpy.props.IntProperty(name="数字字号", default=8, min=4, max=100, update=tag_redraw)
    seq_font_color: bpy.props.FloatVectorProperty(name="数字颜色",
                                                  subtype='COLOR',
                                                  size=4,
                                                  default=(1.0, 1.0, 1.0, 1.0),
                                                  min=0,
                                                  max=1,
                                                  update=tag_redraw)

    # 3. 文本设置区
    text_default_size: bpy.props.IntProperty(name="默认字号", default=8, min=4, max=100)
    text_default_color: bpy.props.FloatVectorProperty(name="默认字色", subtype='COLOR', size=4, default=(1.0, 1.0, 1.0, 1.0), min=0, max=1)
    bg_default_color: bpy.props.FloatVectorProperty(name="默认背景色", subtype='COLOR', size=4, default=(0.2, 0.3, 0.5, 0.9), min=0, max=1)

    text_default_fit: bpy.props.BoolProperty(name="默认适应文本", default=False)
    text_default_align: bpy.props.EnumProperty(name="默认对齐",
                                               items=[('TOP', "顶部", ""), ('BOTTOM', "底部", ""), ('LEFT', "左侧", ""), ('RIGHT', "右侧", "")],
                                               default='TOP')

    # 预设颜色
    col_preset_1: bpy.props.FloatVectorProperty(name="预设红", subtype='COLOR', size=4, default=(0.6, 0.1, 0.1, 0.9), min=0, max=1)
    col_preset_2: bpy.props.FloatVectorProperty(name="预设绿", subtype='COLOR', size=4, default=(0.2, 0.5, 0.2, 0.9), min=0, max=1)
    col_preset_3: bpy.props.FloatVectorProperty(name="预设蓝", subtype='COLOR', size=4, default=(0.2, 0.3, 0.5, 0.9), min=0, max=1)
    col_preset_4: bpy.props.FloatVectorProperty(name="预设橙", subtype='COLOR', size=4, default=(0.8, 0.35, 0.05, 0.9), min=0, max=1)
    col_preset_5: bpy.props.FloatVectorProperty(name="预设紫", subtype='COLOR', size=4, default=(0.4, 0.1, 0.5, 0.9), min=0, max=1)
    col_preset_6: bpy.props.FloatVectorProperty(name="预设无", subtype='COLOR', size=4, default=(0.0, 0.0, 0.0, 0.0), min=0, max=1)

    # 预设标签 (maxlen=8)
    label_preset_1: bpy.props.StringProperty(name="标签1", default="红", maxlen=8)
    label_preset_2: bpy.props.StringProperty(name="标签2", default="绿", maxlen=8)
    label_preset_3: bpy.props.StringProperty(name="标签3", default="蓝", maxlen=8)
    label_preset_4: bpy.props.StringProperty(name="标签4", default="橙", maxlen=8)
    label_preset_5: bpy.props.StringProperty(name="标签5", default="紫", maxlen=8)
    label_preset_6: bpy.props.StringProperty(name="标签6", default="无", maxlen=8)

    # 4. 图像设置区
    img_default_align: bpy.props.EnumProperty(name="默认对齐",
                                              items=[('TOP', "顶部", ""), ('BOTTOM', "底部", ""), ('LEFT', "左侧", ""), ('RIGHT', "右侧", "")],
                                              default='TOP')
    img_max_res: bpy.props.EnumProperty(name="纹理分辨率限制",
                                        description="限制显示的纹理最大尺寸以提升性能",
                                        items=[
                                            ('0', "原图 (最清晰)", ""),
                                            ('2048', "2048 px", ""),
                                            ('1024', "1024 px (推荐)", ""),
                                            ('512', "512 px (极速)", ""),
                                        ],
                                        default='1024',
                                        update=tag_redraw)

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        row = box.row()
        row.label(text="全局设置", icon='WORLD_DATA')
        col = box.column()

        col.label(text="快捷键设置 (默认: Shift + 右键):", icon='KEYINGSET')
        wm = context.window_manager
        kc = wm.keyconfigs.user
        km = kc.keymaps.get('Node Editor')
        if km:
            kmi = None
            for k in km.keymap_items:
                if k.idname == 'node.na_quick_edit':
                    kmi = k
                    break
            if kmi:
                col.prop(kmi, "type", text="", full_event=True)
            else:
                col.label(text="快捷键未注册", icon='ERROR')

        col.separator()
        col.prop(self, "use_occlusion", text="默认开启自动遮挡")

        col.separator()
        col.prop(self, "show_annotations", text="默认显示所有")
        col.prop(self, "show_global_sequence", text="默认显示序号")
        col.prop(self, "show_sequence_lines", text="默认显示逻辑连线")

        # 2. 序号设置
        box = layout.box()
        row = box.row()
        row.label(text="序号样式设置", icon='LINENUMBERS_ON')
        row.operator("node.na_reset_prefs", text="", icon='LOOP_BACK').target_section = 'SEQ'

        col = box.column(align=True)
        split = col.split(factor=0.6)
        split.prop(self, "seq_radius")
        split.prop(self, "seq_bg_color", text="")

        split = col.split(factor=0.6)
        split.prop(self, "seq_font_size")
        split.prop(self, "seq_font_color", text="")

        # 3. 文本设置
        box = layout.box()
        row = box.row()
        row.label(text="文本与背景默认值", icon='TEXT')
        row.operator("node.na_reset_prefs", text="", icon='LOOP_BACK').target_section = 'TEXT'

        col = box.column(align=True)
        row = col.row(align=True)
        row.prop(self, "text_default_size")
        row.prop(self, "text_default_color", text="")
        row.prop(self, "bg_default_color", text="")

        row = col.row(align=True)
        row.prop(self, "text_default_fit", text="默认适应文本")
        row.prop(self, "text_default_align", text="")

        col.separator()
        col.label(text="背景颜色预设 (颜色与文字):")

        grid_col = col.grid_flow(row_major=True, columns=6, align=True)
        for i in range(1, 7):
            grid_col.prop(self, f"col_preset_{i}", text="")

        grid_lbl = col.grid_flow(row_major=True, columns=6, align=True)
        for i in range(1, 7):
            grid_lbl.prop(self, f"label_preset_{i}", text="")

        # 4. 图像设置
        box = layout.box()
        row = box.row()
        row.label(text="图像默认值 & 性能", icon='IMAGE_DATA')
        row.operator("node.na_reset_prefs", text="", icon='LOOP_BACK').target_section = 'IMG'

        col = box.column(align=True)
        col.prop(self, "img_default_align", text="默认对齐")
        col.prop(self, "img_max_res")
        col.label(text="* 分辨率限制将在下次加载图片或重启时生效", icon='INFO')

def pref() -> NodeMemoAddonPreferences:
    assert __package__ is not None
    return bpy.context.preferences.addons[__package__].preferences
