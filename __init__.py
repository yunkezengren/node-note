bl_info = {
    "name": "NodeMemo (节点随记)",
    "author": "Wudong",
    "version": (1, 0, 0),
    "blender": (5, 0, 0),
    "location": "节点编辑器 > 右键菜单",
    "description": "为节点思路设置清晰的路标和精准的导航",
    "category": "Node",
}

import bpy
from . import draw_core
from . import edit_ops
from . import search_ops

addon_keymaps = []

def pref() -> "NodeMemoAddonPreferences":
    assert __package__ is not None
    return bpy.context.preferences.addons[__package__].preferences

def tag_redraw(self, context):
    try:
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'NODE_EDITOR': area.tag_redraw()
    except:
        pass

# --- 属性更新回调 ---

def update_interactive_mode(self, context):
    # [修复] 不再通过回调启动操作符，只负责刷新界面
    context.area.tag_redraw()

def update_manual_text_width(self, context):
    if self.na_auto_width: self.na_auto_width = False
    if self.na_text_fit_content: self.na_text_fit_content = False
    tag_redraw(self, context)

def update_manual_img_width(self, context):
    if self.na_img_width_auto: self.na_img_width_auto = False
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

# --- 偏好设置类 ---

class NODE_OT_reset_prefs(bpy.types.Operator):
    """重置当前页面的设置"""
    bl_idname = "node.na_reset_prefs"
    bl_label = "重置为默认"
    bl_options = {'INTERNAL'}

    target_section: bpy.props.StringProperty()

    def execute(self, context):
        prefs = pref()
        if self.target_section == 'SEQ':
            for p in ["pref_seq_radius", "pref_seq_bg_color", "pref_seq_font_size", "pref_seq_font_color"]:
                prefs.property_unset(p)
        elif self.target_section == 'TEXT':
            for p in [
                    "pref_text_default_size", "pref_text_default_color", "pref_bg_default_color", "pref_text_default_fit",
                    "pref_text_default_align"
            ]:
                prefs.property_unset(p)
            for i in range(1, 7):
                prefs.property_unset(f"pref_col_preset_{i}")
                prefs.property_unset(f"pref_label_preset_{i}")
        elif self.target_section == 'IMG':
            for p in ["pref_img_max_res", "pref_img_default_align"]:
                prefs.property_unset(p)
        return {'FINISHED'}

class NodeMemoAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    # 1. 全局设置

    # 2. 序号设置区
    pref_seq_radius: bpy.props.FloatProperty(name="序号圆半径", default=7.0, min=1.0, max=50.0, update=tag_redraw)
    pref_seq_bg_color: bpy.props.FloatVectorProperty(name="圆背景色",
                                                     subtype='COLOR',
                                                     size=4,
                                                     default=(0.8, 0.1, 0.1, 1.0),
                                                     min=0,
                                                     max=1,
                                                     update=tag_redraw)
    pref_seq_font_size: bpy.props.IntProperty(name="数字字号", default=8, min=4, max=100, update=tag_redraw)
    pref_seq_font_color: bpy.props.FloatVectorProperty(name="数字颜色",
                                                       subtype='COLOR',
                                                       size=4,
                                                       default=(1.0, 1.0, 1.0, 1.0),
                                                       min=0,
                                                       max=1,
                                                       update=tag_redraw)

    # 3. 文本设置区
    pref_text_default_size: bpy.props.IntProperty(name="默认字号", default=8, min=4, max=100)
    pref_text_default_color: bpy.props.FloatVectorProperty(name="默认字色", subtype='COLOR', size=4, default=(1.0, 1.0, 1.0, 1.0), min=0, max=1)
    pref_bg_default_color: bpy.props.FloatVectorProperty(name="默认背景色", subtype='COLOR', size=4, default=(0.2, 0.3, 0.5, 0.9), min=0, max=1)

    pref_text_default_fit: bpy.props.BoolProperty(name="默认适应文本", default=False)
    pref_text_default_align: bpy.props.EnumProperty(name="默认对齐",
                                                    items=[('TOP', "顶部", ""), ('BOTTOM', "底部", ""), ('LEFT', "左侧", ""),
                                                           ('RIGHT', "右侧", "")],
                                                    default='TOP')

    # 预设颜色
    pref_col_preset_1: bpy.props.FloatVectorProperty(name="预设红", subtype='COLOR', size=4, default=(0.6, 0.1, 0.1, 0.9), min=0, max=1)
    pref_col_preset_2: bpy.props.FloatVectorProperty(name="预设绿", subtype='COLOR', size=4, default=(0.2, 0.5, 0.2, 0.9), min=0, max=1)
    pref_col_preset_3: bpy.props.FloatVectorProperty(name="预设蓝", subtype='COLOR', size=4, default=(0.2, 0.3, 0.5, 0.9), min=0, max=1)
    pref_col_preset_4: bpy.props.FloatVectorProperty(name="预设橙", subtype='COLOR', size=4, default=(0.8, 0.35, 0.05, 0.9), min=0, max=1)
    pref_col_preset_5: bpy.props.FloatVectorProperty(name="预设紫", subtype='COLOR', size=4, default=(0.4, 0.1, 0.5, 0.9), min=0, max=1)
    pref_col_preset_6: bpy.props.FloatVectorProperty(name="预设无", subtype='COLOR', size=4, default=(0.0, 0.0, 0.0, 0.0), min=0, max=1)

    # 预设标签 (maxlen=8)
    pref_label_preset_1: bpy.props.StringProperty(name="标签1", default="红", maxlen=8)
    pref_label_preset_2: bpy.props.StringProperty(name="标签2", default="绿", maxlen=8)
    pref_label_preset_3: bpy.props.StringProperty(name="标签3", default="蓝", maxlen=8)
    pref_label_preset_4: bpy.props.StringProperty(name="标签4", default="橙", maxlen=8)
    pref_label_preset_5: bpy.props.StringProperty(name="标签5", default="紫", maxlen=8)
    pref_label_preset_6: bpy.props.StringProperty(name="标签6", default="无", maxlen=8)

    # 4. 图像设置区
    pref_img_default_align: bpy.props.EnumProperty(name="默认对齐",
                                                   items=[('TOP', "顶部", ""), ('BOTTOM', "底部", ""), ('LEFT', "左侧", ""), ('RIGHT', "右侧", "")],
                                                   default='TOP')
    pref_img_max_res: bpy.props.EnumProperty(name="纹理分辨率限制",
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

        # 1. 全局设置
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
        if context.scene:
            col.prop(context.scene, "na_use_occlusion", text="默认开启自动遮挡")

        # 2. 序号设置
        box = layout.box()
        row = box.row()
        row.label(text="序号样式设置", icon='LINENUMBERS_ON')
        row.operator("node.na_reset_prefs", text="", icon='LOOP_BACK').target_section = 'SEQ'

        col = box.column(align=True)
        split = col.split(factor=0.6)
        split.prop(self, "pref_seq_radius")
        split.prop(self, "pref_seq_bg_color", text="")

        split = col.split(factor=0.6)
        split.prop(self, "pref_seq_font_size")
        split.prop(self, "pref_seq_font_color", text="")

        # 3. 文本设置
        box = layout.box()
        row = box.row()
        row.label(text="文本与背景默认值", icon='TEXT')
        row.operator("node.na_reset_prefs", text="", icon='LOOP_BACK').target_section = 'TEXT'

        col = box.column(align=True)
        row = col.row(align=True)
        row.prop(self, "pref_text_default_size")
        row.prop(self, "pref_text_default_color", text="")
        row.prop(self, "pref_bg_default_color", text="")

        row = col.row(align=True)
        row.prop(self, "pref_text_default_fit", text="默认适应文本")
        row.prop(self, "pref_text_default_align", text="")

        col.separator()
        col.label(text="背景颜色预设 (颜色与文字):")

        grid_col = col.grid_flow(row_major=True, columns=6, align=True)
        for i in range(1, 7):
            grid_col.prop(self, f"pref_col_preset_{i}", text="")

        grid_lbl = col.grid_flow(row_major=True, columns=6, align=True)
        for i in range(1, 7):
            grid_lbl.prop(self, f"pref_label_preset_{i}", text="")

        # 4. 图像设置
        box = layout.box()
        row = box.row()
        row.label(text="图像默认值 & 性能", icon='IMAGE_DATA')
        row.operator("node.na_reset_prefs", text="", icon='LOOP_BACK').target_section = 'IMG'

        col = box.column(align=True)
        col.prop(self, "pref_img_default_align", text="默认对齐")
        col.prop(self, "pref_img_max_res")
        col.label(text="* 分辨率限制将在下次加载图片或重启时生效", icon='INFO')

# --- 属性初始化 ---

def init_props():
    bpy.types.Node.na_text = bpy.props.StringProperty(name="内容", default="", update=tag_redraw, options={'TEXTEDIT_UPDATE'})

    bpy.types.Node.na_font_size = bpy.props.IntProperty(name="字号", default=8, min=4, max=500, update=tag_redraw)
    bpy.types.Node.na_bg_color = bpy.props.FloatVectorProperty(name="背景",
                                                               subtype='COLOR',
                                                               size=4,
                                                               default=(0.2, 0.3, 0.5, 0.9),
                                                               min=0.0,
                                                               max=1.0,
                                                               update=tag_redraw)
    bpy.types.Node.na_text_color = bpy.props.FloatVectorProperty(name="文字",
                                                                 subtype='COLOR',
                                                                 size=4,
                                                                 default=(1.0, 1.0, 1.0, 1.0),
                                                                 min=0.0,
                                                                 max=1.0,
                                                                 update=tag_redraw)
    bpy.types.Node.na_text_fit_content = bpy.props.BoolProperty(name="适应文本", default=False, update=tag_redraw)
    bpy.types.Node.na_show_text = bpy.props.BoolProperty(name="显示文本", default=True, update=tag_redraw)
    bpy.types.Node.na_auto_width = bpy.props.BoolProperty(name="跟随节点", default=True, update=tag_redraw)
    bpy.types.Node.na_bg_width = bpy.props.IntProperty(name="背景宽", default=200, min=1, max=2000, update=update_manual_text_width)
    bpy.types.Node.na_swap_content_order = bpy.props.BoolProperty(name="互换位置", default=False, update=tag_redraw)
    bpy.types.Node.na_z_order_switch = bpy.props.BoolProperty(name="层级切换", description="交换图片与文字的前后层级", default=False, update=tag_redraw)
    bpy.types.Node.na_sequence_index = bpy.props.IntProperty(name="序号", default=0, min=0, update=tag_redraw, description="逻辑序号 (0为不显示)")
    bpy.types.Node.na_sequence_color = bpy.props.FloatVectorProperty(name="序号颜色",
                                                                     subtype='COLOR',
                                                                     size=4,
                                                                     default=(0.8, 0.1, 0.1, 1.0),
                                                                     min=0.0,
                                                                     max=1.0,
                                                                     update=tag_redraw)
    bpy.types.Node.na_image = bpy.props.PointerProperty(name="图像", type=bpy.types.Image, update=update_na_image)
    bpy.types.Node.na_img_width_auto = bpy.props.BoolProperty(name="自动图宽", default=True, update=tag_redraw)
    bpy.types.Node.na_img_width = bpy.props.FloatProperty(name="图宽", default=150.0, min=10.0, max=2000.0, update=update_manual_img_width)
    bpy.types.Node.na_show_image = bpy.props.BoolProperty(name="显图", default=True, update=tag_redraw)
    align_items = [('TOP', "顶部", ""), ('BOTTOM', "底部", ""), ('LEFT', "左侧", ""), ('RIGHT', "右侧", "")]
    bpy.types.Node.na_align_pos = bpy.props.EnumProperty(name="对齐", items=align_items, default='TOP', update=tag_redraw)
    bpy.types.Node.na_offset = bpy.props.FloatVectorProperty(name="偏移", size=2, default=(0.0, 0.0), update=tag_redraw, subtype='XYZ')
    bpy.types.Node.na_img_align_pos = bpy.props.EnumProperty(name="图对齐", items=align_items, default='TOP', update=tag_redraw)
    bpy.types.Node.na_img_offset = bpy.props.FloatVectorProperty(name="图偏移", size=2, default=(0.0, 0.0), update=tag_redraw, subtype='XYZ')
    bpy.types.Node.na_is_initialized = bpy.props.BoolProperty(default=False)

    bpy.types.Scene.na_show_annotations = bpy.props.BoolProperty(name="显示所有", default=True, update=tag_redraw)
    bpy.types.Scene.na_show_global_sequence = bpy.props.BoolProperty(name="显示序号",
                                                                     default=True,
                                                                     update=tag_redraw,
                                                                     description="全局显示或隐藏所有序号")
    bpy.types.Scene.na_show_sequence_lines = bpy.props.BoolProperty(name="显示逻辑连线", default=False, update=tag_redraw)

    # 注意：这个属性现在只作为一个状态标记，不通过 update 回调触发逻辑
    bpy.types.Scene.na_is_interactive_mode = bpy.props.BoolProperty(name="交互模式",
                                                                    default=False,
                                                                    update=update_interactive_mode,
                                                                    description="点击节点即可编号，右键或ESC退出")

    bpy.types.Scene.na_sort_by_sequence = bpy.props.BoolProperty(name="按序号排序",
                                                                 default=False,
                                                                 update=tag_redraw,
                                                                 description="勾选后，有序号的节点将优先显示在列表顶部")
    bpy.types.Scene.na_use_occlusion = bpy.props.BoolProperty(name="自动遮挡", default=False, update=tag_redraw)
    bpy.types.Scene.na_tag_mode_prepend = bpy.props.BoolProperty(name="前缀模式", default=True)
    bpy.types.Scene.na_navigator_search = bpy.props.StringProperty(name="搜索", default="")
    for color in ['red', 'green', 'blue', 'orange', 'purple', 'other']:
        setattr(bpy.types.Scene, f"na_filter_{color}", bpy.props.BoolProperty(default=True, update=tag_redraw))

def clear_props():
    props = [
        "na_text", "na_font_size", "na_bg_color", "na_text_color", "na_auto_width", "na_bg_width", "na_swap_content_order", "na_image",
        "na_img_width", "na_show_image", "na_img_width_auto", "na_align_pos", "na_offset", "na_z_order_switch", "na_sequence_index",
        "na_sequence_color", "na_img_align_pos", "na_img_offset", "na_text_fit_content", "na_show_text", "na_is_initialized"
    ]
    for p in props:
        if hasattr(bpy.types.Node, p): delattr(bpy.types.Node, p)
    for p in dir(bpy.types.Scene):
        if p.startswith("na_"): delattr(bpy.types.Scene, p)

class NODE_PT_annotator_gpu_panel(bpy.types.Panel):
    bl_label = "节点随记"
    bl_idname = "NODE_PT_annotator_gpu_panel"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    # [修改点] 侧边栏标签统一为“节点随记”
    bl_category = "节点随记"

    @classmethod
    def poll(cls, context):
        return context.space_data.type == 'NODE_EDITOR'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        box = layout.box()
        row = box.row()
        row.label(text="全局控制", icon='WORLD_DATA')
        row = box.row(align=True)
        row.prop(scene, "na_show_annotations", text="总开关", icon='HIDE_OFF', toggle=True)
        row.operator("node.na_clear_all_scene_notes", text="全清", icon='TRASH')
        if scene.na_show_annotations:
            box.label(text="通道过滤:", icon='FILTER')
            row = box.row(align=True)
            row.prop(scene, "na_filter_red", text="红", toggle=True)
            row.prop(scene, "na_filter_green", text="绿", toggle=True)
            row.prop(scene, "na_filter_blue", text="蓝", toggle=True)
            row.prop(scene, "na_filter_orange", text="橙", toggle=True)
            row.prop(scene, "na_filter_purple", text="紫", toggle=True)
            row.prop(scene, "na_filter_other", text="杂", toggle=True)

        row = layout.row(align=True)
        row.prop(scene, "na_use_occlusion", text="被遮挡时自动隐藏")

        layout.separator()

        try:
            edit_ops.draw_ui_layout(layout, context, draw_footer=False, draw_sequence=True)
        except Exception as e:
            layout.label(text=f"UI Error: {e}", icon="ERROR")

        node = context.active_node
        if node:
            sel_count = len(context.selected_nodes)
            layout.separator(factor=0.2)
            if sel_count > 1:
                row = layout.row(align=True)
                row.operator("node.na_copy_to_selected", text="同步给选中", icon='DUPLICATE')
                row.operator("node.na_clear_text", text="批量清除", icon='TRASH')
            else:
                row = layout.row(align=True)
                row.operator("node.na_clear_text", text="清除单项", icon='TRASH')
                row.operator("preferences.addon_show", text="偏好设置", icon='PREFERENCES').module = __package__

class NODE_OT_na_swap_order(bpy.types.Operator):
    bl_idname = "node.na_swap_order"
    bl_label = "交换图文位置"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        node = context.active_node
        if not node: return {'CANCELLED'}
        if hasattr(node, "na_align_pos") and hasattr(node, "na_img_align_pos"):
            align_txt = node.na_align_pos
            align_img = node.na_img_align_pos
            if align_txt != align_img:
                node.na_align_pos = align_img
                node.na_img_align_pos = align_txt
            else:
                if hasattr(node, "na_swap_content_order"):
                    node.na_swap_content_order = not node.na_swap_content_order
            context.area.tag_redraw()
        return {'FINISHED'}

class NODE_OT_interactive_seq(bpy.types.Operator):
    """画笔点选编号 (右键/ESC退出)"""
    bl_idname = "node.na_interactive_seq"
    bl_label = "交互式编号"
    bl_options = {'REGISTER', 'UNDO'}

    def modal(self, context, event):
        # 检查标记，如果被外部关闭则退出
        if not context.scene.na_is_interactive_mode:
            context.window.cursor_modal_restore()
            context.area.header_text_set(None)
            return {'FINISHED'}

        if event.type in {'RIGHTMOUSE', 'ESC'}:
            context.scene.na_is_interactive_mode = False
            context.window.cursor_modal_restore()
            context.area.header_text_set(None)
            return {'FINISHED'}

        if context.region.type == 'WINDOW':
            context.window.cursor_modal_set('PAINT_BRUSH')

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if context.region.type == 'WINDOW':
                try:
                    bpy.ops.node.select(location=(event.mouse_region_x, event.mouse_region_y), extend=False)
                    node = context.active_node

                    if node and node != self.last_node:
                        self.current_idx += 1
                        node.na_sequence_index = self.current_idx

                        if node.na_sequence_index > 0:
                            node.na_sequence_color = pref().pref_seq_bg_color

                        self.last_node = node

                        msg = f"交互式编号模式 [右键/ESC退出] | 已标记: {node.name} -> #{self.current_idx}"
                        context.area.header_text_set(msg)
                        context.area.tag_redraw()
                    return {'RUNNING_MODAL'}
                except Exception:
                    pass
            else:
                return {'PASS_THROUGH'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        # 如果已经是交互模式，再次点击则关闭（自开关逻辑）
        if context.scene.na_is_interactive_mode:
            context.scene.na_is_interactive_mode = False
            return {'FINISHED'}

        if context.area.type == 'NODE_EDITOR':
            # 开启模式
            context.scene.na_is_interactive_mode = True

            max_idx = 0
            tree = context.space_data.edit_tree
            if tree:
                for n in tree.nodes:
                    if hasattr(n, "na_sequence_index"):
                        max_idx = max(max_idx, n.na_sequence_index)

            self.current_idx = max_idx
            self.last_node = None

            context.window_manager.modal_handler_add(self)
            context.window.cursor_modal_set('PAINT_BRUSH')
            context.area.header_text_set(f"交互式编号模式 [右键/ESC退出] | 当前最大序号: #{max_idx}")
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "未找到节点编辑器")
            context.scene.na_is_interactive_mode = False
            return {'CANCELLED'}

class NODE_OT_clear_global_sequence(bpy.types.Operator):
    bl_idname = "node.na_clear_global_sequence"
    bl_label = "清除全局序号"
    bl_options = {'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        if context.space_data.edit_tree:
            count = 0
            for node in context.space_data.edit_tree.nodes:
                if hasattr(node, "na_sequence_index") and node.na_sequence_index > 0:
                    node.na_sequence_index = 0
                    count += 1
            self.report({'INFO'}, f"已清除 {count} 个节点的序号")
            context.area.tag_redraw()
        return {'FINISHED'}

class NODE_OT_clear_text(bpy.types.Operator):
    bl_idname = "node.na_clear_text"
    bl_label = "清除"
    bl_options = {'UNDO'}

    def execute(self, context):
        nodes = context.selected_nodes if context.selected_nodes else [context.active_node]
        for node in nodes:
            node.na_text = ""
            node.na_image = None
            node.na_sequence_index = 0
            node.na_is_initialized = False
        return {'FINISHED'}

class NODE_OT_clear_all_scene_notes(bpy.types.Operator):
    bl_idname = "node.na_clear_all_scene_notes"
    bl_label = "清除所有"
    bl_options = {'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        if context.space_data.edit_tree:
            for node in context.space_data.edit_tree.nodes:
                if hasattr(node, "na_text"):
                    node.na_text = ""
                    node.na_image = None
                    node.na_sequence_index = 0
                    node.na_is_initialized = False
        return {'FINISHED'}

class NODE_OT_fix_prop(bpy.types.Operator):
    bl_idname = "node.na_fix_prop"
    bl_label = "修复属性"

    def execute(self, context):
        init_props()
        return {'FINISHED'}

classes = [
    NODE_PT_annotator_gpu_panel, NODE_OT_clear_text, NODE_OT_fix_prop, NODE_OT_clear_all_scene_notes, NODE_OT_na_swap_order,
    NODE_OT_interactive_seq, NODE_OT_clear_global_sequence, NODE_OT_reset_prefs, NodeMemoAddonPreferences
]

def register():
    init_props()
    for cls in classes:
        bpy.utils.register_class(cls)
    if draw_core: draw_core.register_draw_handler()
    if edit_ops: edit_ops.register()
    if search_ops: search_ops.register()
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='Node Editor', space_type='NODE_EDITOR')
        kmi = km.keymap_items.new("node.na_quick_edit", 'RIGHTMOUSE', 'PRESS', shift=True)
        addon_keymaps.append((km, kmi))

def unregister():
    if search_ops: search_ops.unregister()
    if edit_ops: edit_ops.unregister()
    if draw_core: draw_core.unregister_draw_handler()
    for cls in classes:
        bpy.utils.unregister_class(cls)
    clear_props()
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        for km, kmi in addon_keymaps:
            km.keymap_items.remove(kmi)
    addon_keymaps.clear()

if __name__ == "__main__": register()
