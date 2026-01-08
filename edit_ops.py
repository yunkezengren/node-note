import bpy
from bpy.types import Operator
import os
import subprocess
import tempfile
import time
from .preference import pref


# [核心逻辑] 初始化注入
def inject_defaults_if_needed(node, prefs):
    """如果节点未初始化，注入偏好设置的默认值"""
    if not node.na_is_initialized and prefs:
        # 1. 注入文本相关默认值
        node.na_font_size = prefs.text_default_size
        node.na_text_color = prefs.text_default_color
        node.na_bg_color = prefs.bg_default_color

        # 2. 注入逻辑开关
        node.na_text_fit_content = prefs.text_default_fit
        node.na_align_pos = prefs.text_default_align

        # 3. 注入序号颜色默认值
        node.na_sequence_color = prefs.seq_bg_color

        # 标记已初始化，以后不再覆盖
        node.na_is_initialized = True

def paste_image_from_clipboard():
    try:
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
        if os.path.exists(path) and os.path.getsize(path) > 0: return path
    except:
        pass
    return None

class NODE_OT_reset_img_width(Operator):
    bl_idname = "node.na_reset_img_width"
    bl_label = "复位宽"
    bl_options = {'UNDO'}

    def execute(self, context):
        context.active_node.na_img_width_auto = True
        context.area.tag_redraw()
        return {'FINISHED'}

class NODE_OT_toggle_text_width_link(Operator):
    bl_idname = "node.na_toggle_text_width_link"
    bl_label = "跟随节点宽度"
    bl_options = {'UNDO'}

    def execute(self, context):
        node = context.active_node
        node.na_auto_width = not node.na_auto_width
        context.area.tag_redraw()
        return {'FINISHED'}

class NODE_OT_reset_offset(Operator):
    bl_idname = "node.na_reset_offset"
    bl_label = "复位"
    bl_options = {'UNDO'}

    def execute(self, context):
        node = context.active_node
        if hasattr(node, "na_offset"): node.na_offset = (0, 0)
        if hasattr(node, "na_align_pos"): node.na_align_pos = 'TOP'
        context.area.tag_redraw()
        return {'FINISHED'}

class NODE_OT_reset_img_offset(Operator):
    bl_idname = "node.na_reset_img_offset"
    bl_label = "复位图片偏移"
    bl_options = {'UNDO'}

    def execute(self, context):
        node = context.active_node
        if hasattr(node, "na_img_offset"): node.na_img_offset = (0, 0)
        if hasattr(node, "na_img_align_pos"): node.na_img_align_pos = 'TOP'
        context.area.tag_redraw()
        return {'FINISHED'}

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
            context.active_node.na_show_image = True

            # [注入] 图片默认对齐
            prefs = pref()
            if prefs:
                context.active_node.na_img_align_pos = prefs.img_default_align

            context.area.tag_redraw()
        except Exception as e:
            self.report({'ERROR'}, str(e))
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class NODE_OT_paste_image(Operator):
    bl_idname = "node.na_paste_image"
    bl_label = "粘贴"
    bl_options = {'UNDO'}

    def execute(self, context):
        path = paste_image_from_clipboard()
        if path:
            img = bpy.data.images.load(path)
            img.colorspace_settings.name, img.alpha_mode, img.use_fake_user = 'Non-Color', 'STRAIGHT', True
            img.pack()
            context.active_node.na_image = img
            context.active_node.na_show_image = True

            # [注入] 图片默认对齐
            prefs = pref()
            if prefs:
                context.active_node.na_img_align_pos = prefs.img_default_align

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
            n.na_bg_color = self.bg_color
            n.na_text_color = self.text_color
        return {'FINISHED'}

class NODE_OT_copy_active_to_selected(Operator):
    bl_idname = "node.na_copy_to_selected"
    bl_label = "同步给选中"
    bl_options = {'UNDO'}

    def execute(self, context):
        act = context.active_node
        if not act: return {'CANCELLED'}
        strict_sync_props = ["na_font_size", "na_text_color", "na_bg_color", "na_sequence_color", "na_text_fit_content", "na_auto_width"]
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

def draw_ui_layout(layout, context, draw_footer=True, draw_sequence=True):
    node = context.active_node
    if not node: return
    col = layout.column(align=True)

    col.label(text="输入笔记 (分号换行):", icon='TEXT')
    col.prop(node, "na_text", text="")

    row = col.row(align=True)
    row.scale_y = 0.8
    row.prop(pref(),
             "tag_mode_prepend",
             text="",
             icon='ALIGN_LEFT' if pref().tag_mode_prepend else 'ALIGN_RIGHT',
             toggle=True)
    for t in ["★", "⚠", "?", "!"]:
        op = row.operator("node.na_add_quick_tag", text=t)
        op.tag_text = t

    layout.separator(factor=0.5)

    seq_box = layout.column(align=True).box()
    row = seq_box.row(align=True)
    row.prop(node, "na_sequence_index", text="")
    row.prop(node, "na_sequence_color", text="")

    # [修复] 改为 operator 按钮，并根据 boolean 属性显示是否按下状态
    row.operator("node.na_interactive_seq", text="", icon='BRUSH_DATA', depress=pref().is_interactive_mode)

    row.prop(pref(), "show_sequence_lines", text="", icon='GRAPH')
    row.prop(pref(), "show_global_sequence", text="", icon='HIDE_OFF' if pref().show_global_sequence else 'HIDE_ON')
    row.operator("node.na_clear_global_sequence", text="", icon='TRASH')

    layout.separator(factor=0.5)

    box = layout.box()
    row = box.row(align=True)
    row.label(text="预设:")

    prefs = pref()

    def_colors = [(0.6, 0.1, 0.1, 0.9), (0.2, 0.5, 0.2, 0.9), (0.2, 0.3, 0.5, 0.9), (0.8, 0.35, 0.05, 0.9), (0.4, 0.1, 0.5, 0.9),
                  (0.0, 0.0, 0.0, 0.0)]
    def_labels = ["红", "绿", "蓝", "橙", "紫", "无"]

    for i in range(6):
        col_val = def_colors[i]
        label_text = def_labels[i]

        if prefs:
            col_val = getattr(prefs, f"col_preset_{i+1}")
            custom_lbl = getattr(prefs, f"label_preset_{i+1}", "")
            if custom_lbl:
                label_text = custom_lbl

        op = row.operator("node.na_apply_preset", text=label_text)
        op.bg_color = col_val

    row = box.row(align=True)
    split = row.split(factor=0.8, align=True)
    split.prop(node, "na_font_size", text="字号")
    try:
        split.operator("node.na_swap_order", text="⇅")
    except:
        split.label(text="Err")

    row = box.row(align=True)
    row.prop(node, "na_text_fit_content", text="适应文本")
    row.prop(node, "na_show_text", text="", icon='HIDE_OFF' if node.na_show_text else 'HIDE_ON')
    row.operator("node.na_toggle_text_width_link", text="", icon='LINKED' if node.na_auto_width else 'UNLINKED')

    sub = row.row(align=True)
    sub.active = bool(node.na_text)
    sub.prop(node, "na_bg_width", text="宽")

    if hasattr(node, "na_align_pos") and hasattr(node, "na_offset"):
        row = box.row(align=True)
        row.prop(node, "na_align_pos", text="")
        sub = row.row(align=True)
        sub.prop(node, "na_offset", text="")
        sub.operator("node.na_reset_offset", text="", icon='LOOP_BACK')

    row = box.row(align=True)
    row.prop(node, "na_text_color", text="")
    row.prop(node, "na_bg_color", text="")

    layout.separator(factor=0.5)

    img_box = layout.column(align=True).box()
    row = img_box.row(align=True)
    row.template_ID(node, "na_image", open="")
    row.operator("node.na_open_image", text="", icon='FILE_FOLDER')
    row = img_box.row(align=True)
    row.scale_y = 1.2
    split = row.split(factor=0.35, align=True)
    split.operator("node.na_paste_image", text="粘贴", icon='PASTEDOWN')
    rr = split.row(align=True)
    rr.prop(node, "na_show_image", text="", icon='HIDE_OFF' if node.na_show_image else 'HIDE_ON')
    rr.operator("node.na_reset_img_width", text="", icon='LINKED' if node.na_img_width_auto else 'UNLINKED')

    sub = rr.row(align=True)
    sub.active = (node.na_image is not None)
    sub.prop(node, "na_img_width", text="宽")

    if hasattr(node, "na_img_align_pos") and hasattr(node, "na_img_offset"):
        row = img_box.row(align=True)
        row.prop(node, "na_img_align_pos", text="")
        sub = row.row(align=True)
        sub.prop(node, "na_img_offset", text="")
        sub.operator("node.na_reset_img_offset", text="", icon='LOOP_BACK')

    if draw_footer:
        sel = len(context.selected_nodes)
        layout.separator(factor=0.2)
        row = layout.row(align=True)
        if sel > 1:
            row.operator("node.na_copy_to_selected", text="同步给选中", icon='DUPLICATE')
            row.operator("node.na_clear_text", text="批量清除", icon='TRASH')
        else:
            row.operator("node.na_clear_text", text="清除单项", icon='TRASH')

# [更新] 呼出菜单时触发注入
class NODE_OT_na_quick_edit(Operator):
    bl_idname = "node.na_quick_edit"
    # [修改点] 右键菜单名称改为“节点随记”
    bl_label = "节点随记"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_node is not None

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        prefs = pref()
        if context.active_node and prefs:
            inject_defaults_if_needed(context.active_node, prefs)

        context.window.cursor_warp(event.mouse_x + 100, event.mouse_y)
        return context.window_manager.invoke_popup(self, width=220)

    def draw(self, context):
        draw_ui_layout(self.layout, context, draw_sequence=False)

def draw_menu_func(self, context):
    layout = self.layout
    layout.separator()
    layout.operator_context = 'INVOKE_DEFAULT'
    layout.operator(NODE_OT_na_quick_edit.bl_idname, icon='TEXT')

classes = [
    NODE_OT_reset_img_width, NODE_OT_toggle_text_width_link, NODE_OT_reset_offset, NODE_OT_reset_img_offset, NODE_OT_open_image,
    NODE_OT_paste_image, NODE_OT_apply_preset, NODE_OT_copy_active_to_selected, NODE_OT_add_quick_tag, NODE_OT_copy_node_label,
    NODE_OT_na_quick_edit
]

def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.NODE_MT_context_menu.prepend(draw_menu_func)

def unregister():
    if hasattr(bpy.types, "NODE_MT_context_menu"): bpy.types.NODE_MT_context_menu.remove(draw_menu_func)
    for c in classes:
        bpy.utils.unregister_class(c)
