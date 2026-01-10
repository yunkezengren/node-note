import bpy
from bpy.types import Operator, UILayout, Context, Node
import os
import subprocess
import tempfile
import time
from .preference import pref
from .search_ops import draw_search_list

# [核心逻辑] 初始化注入
def inject_defaults_if_needed(node: Node):
    """如果节点未初始化，注入偏好设置的默认值"""
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

def paste_image_from_clipboard():
    tmp = tempfile.gettempdir()
    path = os.path.join(tmp, f"blender_paste_{int(time.time()*1000)}.png")
    import sys
    if sys.platform == "win32":
        cmd = [
            "powershell", "-WindowStyle", "Hidden", "-command",
            f"Add-Type -AssemblyName System.Windows.Forms;$i=[System.Windows.Forms.Clipboard]::GetImage();if($i){{$i.Save('{path}',[System.Drawing.Imaging.ImageFormat]::Png);exit 0}}exit 1"
        ]
        subprocess.run(cmd)
    elif sys.platform == "darwin":
        subprocess.run(["pngpaste", path])
    elif sys.platform.startswith("linux"):
        with open(path, "wb") as f:
            subprocess.run(["xclip", "-selection", "clipboard", "-t", "image/png", "-o"], stdout=f)
    if os.path.exists(path) and os.path.getsize(path) > 0: 
        return path

class NODE_OT_reset_offset(Operator):
    bl_idname = "node.na_reset_offset"
    bl_label = "复位"
    bl_options = {'UNDO'}

    def execute(self, context):
        node = context.active_node
        if hasattr(node, "na_txt_offset"): node.na_txt_offset = (0, 0)
        if hasattr(node, "na_txt_pos"): node.na_txt_pos = 'TOP'
        context.area.tag_redraw()
        return {'FINISHED'}

class NODE_OT_reset_img_offset(Operator):
    bl_idname = "node.na_reset_img_offset"
    bl_label = "复位图片偏移"
    bl_options = {'UNDO'}

    def execute(self, context):
        node = context.active_node
        if hasattr(node, "na_img_offset"): node.na_img_offset = (0, 0)
        if hasattr(node, "na_img_pos"): node.na_img_pos = 'TOP'
        context.area.tag_redraw()
        return {'FINISHED'}

# 有点多余, 不确定 context.active_node.na_img_pos = prefs.img_default_align
class NODE_OT_open_image(Operator):
    bl_idname = "node.na_open_image"
    bl_label = "打开"
    bl_options = {'REGISTER', 'UNDO'}
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_folder: bpy.props.BoolProperty(default=True, options={'HIDDEN'})
    filter_image: bpy.props.BoolProperty(default=True, options={'HIDDEN'})

    def execute(self, context):
        try:
            img = bpy.data.images.load(self.filepath)
            img.colorspace_settings.name, img.alpha_mode, img.use_fake_user = 'Non-Color', 'STRAIGHT', True
            context.active_node.na_image = img
            context.active_node.na_show_img = True

            # [注入] 图片默认对齐
            prefs = pref()
            if prefs:
                context.active_node.na_img_pos = prefs.img_default_align

            context.area.tag_redraw()
        except Exception as e:
            self.report({'ERROR'}, str(e))
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

# todo 非常卡啊
class NODE_OT_paste_image(Operator):
    bl_idname = "node.na_paste_image"
    bl_label = "从剪贴板粘贴图像"
    bl_description = "从剪贴板粘贴图像"
    bl_options = {'UNDO'}

    def execute(self, context):
        path = paste_image_from_clipboard()
        if path:
            img = bpy.data.images.load(path)
            img.colorspace_settings.name, img.alpha_mode, img.use_fake_user = 'Non-Color', 'STRAIGHT', True
            img.pack()
            context.active_node.na_image = img
            context.active_node.na_show_img = True

            # [注入] 图片默认对齐
            prefs = pref()
            if prefs:
                context.active_node.na_img_pos = prefs.img_default_align

            self.report({'INFO'}, f"成功导入图片: {img.name}")
            return {'FINISHED'}
        self.report({'WARNING'}, "无图片")
        return {'CANCELLED'}

class NODE_OT_apply_preset(Operator):
    bl_idname = "node.na_apply_preset"
    bl_label = "预设"
    bl_options = {'UNDO'}
    bg_color: bpy.props.FloatVectorProperty(size=4)
    text_color: bpy.props.FloatVectorProperty(size=4, default=(1, 1, 1, 1))

    def execute(self, context):
        for n in (context.selected_nodes or [context.active_node]):
            n.na_txt_bg_color = self.bg_color
            n.na_text_color = self.text_color
        return {'FINISHED'}

class NODE_OT_copy_active_to_selected(Operator):
    bl_idname = "node.na_copy_to_selected"
    bl_label = "同步给选中"
    bl_options = {'UNDO'}

    def execute(self, context):
        act = context.active_node
        if not act: return {'CANCELLED'}
        strict_sync_props = ["na_font_size", "na_text_color", "na_txt_bg_color", "na_sequence_color", "na_txt_width_mode", "na_txt_bg_width", "na_img_width_mode", "na_img_width"]
        count = 0
        for n in context.selected_nodes:
            if n == act: continue
            for p in strict_sync_props:
                if hasattr(act, p) and hasattr(n, p):
                    setattr(n, p, getattr(act, p))
            count += 1
        self.report({'INFO'}, f"已同步 6 项样式至 {count} 个节点")
        context.area.tag_redraw()
        return {'FINISHED'}

class NODE_OT_add_quick_tag(Operator):
    bl_idname = "node.na_add_quick_tag"
    bl_label = "标签"
    bl_options = {'UNDO'}
    tag_text: bpy.props.StringProperty()

    def execute(self, context):
        for n in (context.selected_nodes or [context.active_node]):
            n.na_text = (self.tag_text + " " + n.na_text) if pref().tag_mode_prepend else (n.na_text + " " + self.tag_text)
        return {'FINISHED'}

class NODE_OT_copy_node_label(Operator):
    bl_idname = "node.na_copy_node_label"
    bl_label = "引用"
    bl_options = {'UNDO'}

    def execute(self, context):
        for n in (context.selected_nodes or [context.active_node]):
            lbl = n.label or n.name
            if not n.na_text.startswith(lbl): n.na_text = lbl + " " + n.na_text
        return {'FINISHED'}

def draw_ui_layout(layout: UILayout, context: Context):
    header: UILayout
    body: UILayout
    prefs = pref()
    col_vals = []
    def_labels = ["红", "绿", "蓝", "橙", "紫", "无"]
    for i in range(len(def_labels)):
        col_vals.append(getattr(prefs, f"col_preset_{i+1}"))
        custom_lbl = getattr(prefs, f"label_preset_{i+1}", "")
        if custom_lbl:
            def_labels[i] = custom_lbl

    header, body = layout.panel("setting", default_closed=True)
    header.label(text="全局设置", icon='TOOL_SETTINGS')
    if body:
        row_pos = body.row()
        row_pos.operator("preferences.addon_show", text="偏好", icon='PREFERENCES').module = __package__
        row_pos.prop(prefs, "show_annotations", text="显示", icon='HIDE_OFF', toggle=True)
        row_pos.operator("node.na_clear_all_scene_notes", text="全删", icon='TRASH')
        # 还很不完善
        # body.column().prop(prefs, "use_occlusion", text="被遮挡时自动隐藏")
        
        row_del = body.row(align=True)
        # 暂时禁用这个
        # row_del.operator("node.na_clear_select_all", text="删除选中笔记", icon='TRASH')

        if prefs.show_annotations:
            body.label(text="按背景色显示文本和图片:", icon='FILTER')
            split = body.split(factor=0.1, align=True)
            split.label(text="    ")
            split.prop(prefs, "filter_red", text=def_labels[0], toggle=True)
            split.prop(prefs, "filter_green", text=def_labels[1], toggle=True)
            split.prop(prefs, "filter_blue", text=def_labels[2], toggle=True)
            split.prop(prefs, "filter_orange", text=def_labels[3], toggle=True)
            split.prop(prefs, "filter_purple", text=def_labels[4], toggle=True)
            split.prop(prefs, "filter_other", text=def_labels[5], toggle=True)

        if len(context.selected_nodes) > 1:
            body.row().operator("node.na_copy_to_selected", text="同步活动样式到选中", icon='DUPLICATE')

    node = context.active_node
    if not node:
        layout.label(text="需要活动节点", icon='INFO')
        return

    header, body = layout.panel("setting1", default_closed=False)
    header.label(text="", icon='FILE_TEXT')
    header.operator("node.na_show_select_txt", text="文字笔记", icon="HIDE_OFF" if node.na_show_txt else "HIDE_ON")
    if node.na_show_txt and node.na_text and node.na_show_img and node.na_image:
        header.operator("node.na_swap_order", text="⇅ 交换")
    header.operator("node.na_clear_select_txt", text="", icon='TRASH')
    if body:
        body.active = node.na_show_txt
        body_split = body.split(factor=0.01)
        body_split.label(text="")
        txt_box = body_split.box()
        col = txt_box.column(align=True)
        col.prop(node, "na_text", text="描述: ")

        row_pos = txt_box.column()
        row_tag = row_pos.row(align=True)
        row_tag.prop(pref(), "tag_mode_prepend", text="", icon='ALIGN_LEFT' if pref().tag_mode_prepend else 'ALIGN_RIGHT', toggle=True)
        for tag in ["★", "⚠", "?", "!"]:
            op = row_tag.operator("node.na_add_quick_tag", text=tag)
            op.tag_text = tag

        txt_box.separator(factor=0.05)
        split_txt = txt_box.split(factor=0.5)
        split_txt.prop(node, "na_font_size", text="字号")
        split_txt.prop(pref(), "line_separator", text="换行符")
        
        split_color = txt_box.split(factor=0.5)
        split_color.row().prop(node, "na_text_color", text="文本色")
        split_color.row().prop(node, "na_txt_bg_color", text="背景色")

        row_pos = txt_box.row()
        row_pos.label(text="背景:")
        def_labels = ["红", "绿", "蓝", "橙", "紫", "无"]
        for i in range(len(def_labels)):
            split_color = row_pos.split(factor=0.1, align=True)
            split_color.prop(pref(), f"col_preset_{i+1}", text="")
            op = split_color.operator("node.na_apply_preset", text=def_labels[i])
            op.bg_color = col_vals[i]

        width_row = txt_box.row(align=True)
        width_row.prop(node, "na_txt_width_mode", text="宽度")
        if node.na_txt_width_mode == 'MANUAL':
            width_row.prop(node, "na_txt_bg_width", text="宽度")

        row_pos = txt_box.row(align=True)
        row_pos.prop(node, "na_txt_pos", text="")
        row_pos.prop(node, "na_txt_offset", text="")
        row_pos.operator("node.na_reset_offset", text="", icon='LOOP_BACK')

    header, body = layout.panel("setting2", default_closed=True)
    header.label(text="", icon='IMAGE_DATA')
    header.operator("node.na_show_select_img", text="图片笔记", icon="HIDE_OFF" if node.na_show_img else "HIDE_ON")
    header.operator("node.na_clear_select_img", text="", icon='TRASH')
    if body:
        body.active = node.na_show_img
        body_split = body.split(factor=0.01)
        body_split.label(text="")
        img_box = body_split.box()
        split = img_box.split(factor=0.75)
        split.template_ID(node, "na_image", open="image.open")
        split.operator("node.na_paste_image", text="粘贴", icon='PASTEDOWN')

        width_row = img_box.row(align=True)
        width_row.prop(node, "na_img_width_mode", text="宽度")
        if node.na_img_width_mode == 'MANUAL':
            width_row.prop(node, "na_img_width", text="宽度")

        row_pos = img_box.row(align=True)
        row_pos.prop(node, "na_img_pos", text="")
        row_pos.prop(node, "na_img_offset", text="")
        row_pos.operator("node.na_reset_img_offset", text="", icon='LOOP_BACK')

    header, body = layout.panel("setting3", default_closed=True)
    header.label(text="", icon='EVENT_NDOF_BUTTON_1')
    header.operator("node.na_show_select_seq", text="序号笔记", icon="HIDE_OFF" if node.na_show_seq else "HIDE_ON")
    header.operator("node.na_clear_select_seq", text="", icon='TRASH')
    if body:
        body.active = node.na_show_seq
        body_split = body.split(factor=0.01)
        body_split.label(text="")
        seq_box = body_split.box()
        split = seq_box.split(factor=0.5)
        split.prop(node, "na_seq_index", text="序号")
        split = seq_box.split(factor=0.5)
        split.row().prop(prefs, "seq_font_color", text="文本色")
        split.row().prop(prefs, "seq_bg_color", text="背景色")

        row_pos = seq_box.row()
        row_pos.operator("node.na_interactive_seq", text="交互编号", icon='BRUSH_DATA', depress=prefs.is_interactive_mode)

        row_set = seq_box.row()
        row_set.label(text="全局设置:", icon='INFO')
        row_set.prop(prefs, "seq_scale", text="缩放")
        
        row_set = seq_box.split(factor=0.5)
        row_set.prop(prefs, "show_sequence_lines", text="显示连线", icon='EMPTY_ARROWS')
        row_set.row().prop(prefs, "seq_line_color", text="连线颜色")

    header, body = layout.panel("setting4", default_closed=True)
    header.label(text="文本导航列表")
    header.prop(prefs, "sort_by_sequence", text="按序号排列")
    if body:
        draw_search_list(body, context)

class NODE_OT_na_quick_edit(Operator):
    bl_idname = "node.na_quick_edit"
    bl_label = "节点随记"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_node is not None

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        if context.active_node:
            inject_defaults_if_needed(context.active_node)

        context.window.cursor_warp(event.mouse_x + 100, event.mouse_y)
        return context.window_manager.invoke_popup(self, width=220)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.label(icon="TOOL_SETTINGS")
        row.label(icon="FILE_TEXT")
        row.label(icon="IMAGE_DATA")
        row.label(icon="EVENT_NDOF_BUTTON_1")
        draw_ui_layout(layout, context)

def draw_menu_func(self: bpy.types.Menu, context: Context):
    layout = self.layout
    layout.separator()
    layout.operator_context = 'INVOKE_DEFAULT'
    layout.operator(NODE_OT_na_quick_edit.bl_idname, icon='TEXT')

classes = [
    NODE_OT_reset_offset, NODE_OT_reset_img_offset,
    NODE_OT_paste_image, NODE_OT_apply_preset, NODE_OT_copy_active_to_selected, NODE_OT_add_quick_tag, NODE_OT_copy_node_label,
    NODE_OT_na_quick_edit
]

def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.NODE_MT_context_menu.prepend(draw_menu_func)

def unregister():
    bpy.types.NODE_MT_context_menu.remove(draw_menu_func)
    for c in classes:
        bpy.utils.unregister_class(c)
