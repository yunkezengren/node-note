import bpy
from bpy.types import Operator
from bpy.props import StringProperty
from .preferences import pref
from .utils import get_image_from_clipboard
from .ui import draw_ui_layout

class NODE_OT_note_reset_prefs(Operator):
    """重置当前页面的设置"""
    bl_idname = "node.note_reset_prefs"
    bl_label = "重置为默认"
    bl_options = {'INTERNAL'}

    target_section: StringProperty()

    def execute(self, context):
        prefs = pref()
        if self.target_section == 'SEQ':
            for p in ["badge_radius", "default_badge_color", "badge_font_size", "badge_font_color"]:
                prefs.property_unset(p)
        elif self.target_section == 'TEXT':
            for p in ["default_font_size", "default_text_color", "default_txt_bg_color", "text_default_fit", "default_text_pos"]:
                prefs.property_unset(p)
            for i in range(1, 7):
                prefs.property_unset(f"col_preset_{i}")
                prefs.property_unset(f"label_preset_{i}")
        elif self.target_section == 'IMG':
            for p in ["img_default_align"]:
                prefs.property_unset(p)
        return {'FINISHED'}

class NODE_OT_note_note_swap_order(Operator):
    bl_idname = "node.note_swap_order"
    bl_label = "交换图文位置"
    bl_description = "交换选中节点文本笔记和图像笔记顺序"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        node = context.active_node
        if not node: return {'CANCELLED'}
        nodes = context.selected_nodes if context.selected_nodes else [context.active_node]
        for node in nodes:
            if hasattr(node, "note_txt_pos") and hasattr(node, "note_img_pos"):
                align_txt = node.note_txt_pos
                align_img = node.note_img_pos
                if align_txt != align_img:
                    node.note_txt_pos = align_img
                    node.note_img_pos = align_txt
                else:
                    if hasattr(node, "note_swap_content_order"):
                        node.note_swap_content_order = not node.note_swap_content_order
                context.area.tag_redraw()
        return {'FINISHED'}

class NODE_OT_note_interactive_badge(Operator):
    bl_idname = "node.note_interactive_badge"
    bl_label = "交互式编号"
    bl_description = "画笔点选节点自动编号 (右键/ESC退出)"
    bl_options = {'REGISTER', 'UNDO'}

    def modal(self, context, event):
        # 检查标记，如果被外部关闭则退出
        if not pref().is_interactive_mode:
            context.window.cursor_modal_restore()
            context.area.header_text_set(None)
            return {'FINISHED'}

        if event.type in {'RIGHTMOUSE', 'ESC'}:
            pref().is_interactive_mode = False
            context.window.cursor_modal_restore()
            context.area.header_text_set(None)
            return {'FINISHED'}

        if context.region.type == 'WINDOW':
            context.window.cursor_modal_set('PAINT_BRUSH')

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if context.region.type == 'WINDOW':
                bpy.ops.node.select(location=(event.mouse_region_x, event.mouse_region_y), extend=False)
                node = context.active_node

                if node and node != self.last_node:
                    self.current_idx += 1
                    node.note_badge_index = self.current_idx

                    if node.note_badge_index > 0:
                        node.note_badge_color = pref().default_badge_color

                    self.last_node = node

                    msg = f"交互式编号模式 [右键/ESC退出] | 已标记: {node.name} -> #{self.current_idx}"
                    context.area.header_text_set(msg)
                    context.area.tag_redraw()
                return {'RUNNING_MODAL'}
            else:
                return {'PASS_THROUGH'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        # 如果已经是交互模式，再次点击则关闭（自开关逻辑）
        if pref().is_interactive_mode:
            pref().is_interactive_mode = False
            return {'FINISHED'}

        if context.area.type == 'NODE_EDITOR':
            # 开启模式
            pref().is_interactive_mode = True

            max_idx = 0
            tree = context.space_data.edit_tree
            if tree:
                for node in tree.nodes:
                    if hasattr(node, "note_badge_index"):
                        max_idx = max(max_idx, node.note_badge_index)

            self.current_idx = max_idx
            self.last_node = None

            context.window_manager.modal_handler_add(self)
            context.window.cursor_modal_set('PAINT_BRUSH')
            context.area.header_text_set(f"交互式编号模式 [右键/ESC退出] | 当前最大序号: #{max_idx}")
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "未找到节点编辑器")
            pref().is_interactive_mode = False
            return {'CANCELLED'}

class NODE_OT_note_clear_select_all(Operator):
    bl_idname = "node.note_clear_select_all"
    bl_label = "删除全部"
    bl_description = "删除选中节点的所有笔记"
    bl_options = {'UNDO'}

    def execute(self, context):
        nodes = context.selected_nodes if context.selected_nodes else [context.active_node]
        for node in nodes:
            if node.note_text or node.note_image or node.note_badge_index:
                node.note_text = ""
                node.note_image = None
                node.note_badge_index = 0
                node.note_initialized = False
        return {'FINISHED'}

class NODE_OT_note_clear_select_txt(Operator):
    bl_idname = "node.note_clear_select_txt"
    bl_label = "删除文本"
    bl_description = "删除选中节点的文字笔记"
    bl_options = {'UNDO'}

    def execute(self, context):
        nodes = context.selected_nodes if context.selected_nodes else [context.active_node]
        for node in nodes:
            if not node.note_text: continue
            node.note_text = ""
            if not node.note_image and not node.note_badge_index:
                node.note_initialized = False
        return {'FINISHED'}

class NODE_OT_note_clear_select_img(Operator):
    bl_idname = "node.note_clear_select_img"
    bl_label = "删除图片"
    bl_description = "删除选中节点的图片笔记"
    bl_options = {'UNDO'}

    def execute(self, context):
        nodes = context.selected_nodes if context.selected_nodes else [context.active_node]
        for node in nodes:
            if not node.note_image: continue
            node.note_image = None
            if not node.note_text and not node.note_badge_index:
                node.note_initialized = False
        return {'FINISHED'}

class NODE_OT_note_clear_select_badge(Operator):
    bl_idname = "node.note_clear_select_badge"
    bl_label = "删除序号"
    bl_description = "删除选中节点的序号笔记"
    bl_options = {'UNDO'}

    def execute(self, context):
        nodes = context.selected_nodes if context.selected_nodes else [context.active_node]
        for node in nodes:
            if not node.note_badge_index: continue
            node.note_badge_index = 0
            if not node.note_text and not node.note_image:
                node.note_initialized = False
        return {'FINISHED'}

class NODE_OT_note_delete_all_notes(Operator):
    bl_idname = "node.note_delete_all_notes"
    bl_label = "删除所有笔记"
    bl_description = "删除节点树中所有笔记"
    bl_options = {'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    # todo: 是否递归删除节点组内
    def execute(self, context):
        edit_tree = context.space_data.edit_tree
        if not edit_tree: return {'CANCELLED'}
        for node in edit_tree.nodes:
            if not node.note_text and not node.note_image and not node.note_badge_index: continue
            node.note_text = ""
            node.note_image = None
            node.note_badge_index = 0
            node.note_initialized = False
        return {'FINISHED'}

class NODE_OT_note_show_select_txt(Operator):
    bl_idname = "node.note_show_select_txt"
    bl_label = "显示文本"
    bl_description = "显示选中节点的文字笔记"
    bl_options = {'UNDO'}

    def execute(self, context):
        active_node = context.active_node
        nodes = context.selected_nodes
        if not active_node: return {'CANCELLED'}
        new_value = not active_node.note_show_txt
        active_node.note_show_txt = new_value
        for node in nodes:
            node.note_show_txt = new_value
        return {'FINISHED'}

class NODE_OT_note_show_select_img(Operator):
    bl_idname = "node.note_show_select_img"
    bl_label = "显示图片"
    bl_description = "显示选中节点的图片笔记"
    bl_options = {'UNDO'}

    def execute(self, context):
        active_node = context.active_node
        nodes = context.selected_nodes
        if not active_node: return {'CANCELLED'}
        new_value = not active_node.note_show_img
        active_node.note_show_img = new_value
        for node in nodes:
            node.note_show_img = new_value
        return {'FINISHED'}

class NODE_OT_note_show_select_badge(Operator):
    bl_idname = "node.note_show_select_badge"
    bl_label = "显示序号"
    bl_description = "显示选中节点的序号笔记"
    bl_options = {'UNDO'}

    def execute(self, context):
        active_node = context.active_node
        nodes = context.selected_nodes
        if not active_node: return {'CANCELLED'}
        new_value = not active_node.note_show_badge
        active_node.note_show_badge = new_value
        for node in nodes:
            node.note_show_badge = new_value
        return {'FINISHED'}

class NODE_OT_note_reset_offset(Operator):
    bl_idname = "node.note_reset_offset"
    bl_label = "复位"
    bl_options = {'UNDO'}

    def execute(self, context):
        node = context.active_node
        if hasattr(node, "note_txt_offset"): node.note_txt_offset = (0, 0)
        if hasattr(node, "note_txt_pos"): node.note_txt_pos = 'TOP'
        context.area.tag_redraw()
        return {'FINISHED'}

class NODE_OT_note_reset_img_offset(Operator):
    bl_idname = "node.note_reset_img_offset"
    bl_label = "复位图片偏移"
    bl_options = {'UNDO'}

    def execute(self, context):
        node = context.active_node
        if hasattr(node, "note_img_offset"): node.note_img_offset = (0, 0)
        if hasattr(node, "note_img_pos"): node.note_img_pos = 'TOP'
        context.area.tag_redraw()
        return {'FINISHED'}

class NODE_OT_note_paste_image(Operator):
    bl_idname = "node.note_paste_image"
    bl_label = "从剪贴板粘贴图像"
    bl_description = "从剪贴板粘贴图像"
    bl_options = {'UNDO'}

    def execute(self, context):
        active_node = context.active_node
        if not active_node:
            return {'CANCELLED'}
        image, error = get_image_from_clipboard()
        if image:
            image.colorspace_settings.name = 'sRGB'
            image.use_fake_user = True
            active_node.note_image = image
            active_node.note_show_img = True
            self.report({'INFO'}, f"成功导入图片: {image.name}")
            return {'FINISHED'}
        elif error:
            self.report({'WARNING'}, error)
            return {'CANCELLED'}
        else:
            self.report({'WARNING'}, "剪贴板无图像")
            return {'CANCELLED'}

class NODE_OT_note_apply_preset(Operator):
    bl_idname = "node.note_apply_preset"
    bl_label = "应用预设"
    bl_options = {'UNDO'}
    bg_color: bpy.props.FloatVectorProperty(size=4)

    def execute(self, context):
        for node in (context.selected_nodes or [context.active_node]):
            node.note_txt_bg_color = self.bg_color
            node.note_text_color = (1, 1, 1, 1)
        return {'FINISHED'}

class NODE_OT_note_copy_active_to_selected(Operator):
    bl_idname = "node.note_copy_to_selected"
    bl_label = "同步给选中"
    bl_options = {'UNDO'}

    def execute(self, context):
        act = context.active_node
        if not act: return {'CANCELLED'}
        strict_sync_props = ["note_font_size", "note_text_color", "note_txt_bg_color", "note_badge_color", "note_txt_width_mode", "note_txt_bg_width", "note_img_width_mode", "note_img_width"]
        count = 0
        for node in context.selected_nodes:
            if node == act: continue
            for p in strict_sync_props:
                if hasattr(act, p) and hasattr(node, p):
                    setattr(node, p, getattr(act, p))
            count += 1
        self.report({'INFO'}, f"已同步 6 项样式至 {count} 个节点")
        context.area.tag_redraw()
        return {'FINISHED'}

class NODE_OT_note_add_quick_tag(Operator):
    bl_idname = "node.note_add_quick_tag"
    bl_label = "标签"
    bl_options = {'UNDO'}
    tag_text: bpy.props.StringProperty()

    def execute(self, context):
        for node in (context.selected_nodes or [context.active_node]):
            node.note_text = (self.tag_text + " " + node.note_text) if pref().tag_mode_prepend else (node.note_text + " " + self.tag_text)
        return {'FINISHED'}

class NODE_OT_note_copy_node_label(Operator):
    bl_idname = "node.note_copy_node_label"
    bl_label = "引用"
    bl_options = {'UNDO'}

    def execute(self, context):
        for node in (context.selected_nodes or [context.active_node]):
            lbl = node.label or node.name
            if not node.note_text.startswith(lbl): node.note_text = lbl + " " + node.note_text
        return {'FINISHED'}

class NODE_OT_note_clear_search(Operator):
    """清除搜索内容"""
    bl_idname = "node.note_clear_search"
    bl_label = "清除搜索"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        pref().navigator_search = ""
        return {'FINISHED'}

class NODE_OT_note_jump_to_note(Operator):
    """跳转到指定注记节点"""
    bl_idname = "node.note_jump_to_note"
    bl_label = "跳转到注记"
    bl_description = "聚焦视图到该节点"

    node_name: bpy.props.StringProperty()

    def execute(self, context):
        tree = context.space_data.edit_tree
        if not tree: return {'CANCELLED'}

        target_node = tree.nodes.get(self.node_name)
        if target_node:
            for node in tree.nodes:
                node.select = False
            target_node.select = True
            tree.nodes.active = target_node
            bpy.ops.node.view_selected()
            return {'FINISHED'}

        self.report({'WARNING'}, f"节点 {self.node_name} 未找到")
        return {'CANCELLED'}

class NODE_OT_note_note_quick_edit(Operator):
    bl_idname = "node.note_quick_edit"
    bl_label = "节点随记"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_node is not None

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window.cursor_warp(event.mouse_x + pref().cursor_warp_x, event.mouse_y)
        return context.window_manager.invoke_popup(self, width=220)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        prefs = pref()
        row.prop(prefs, "show_global", text="", icon="TOOL_SETTINGS")
        row.prop(prefs, "show_text", text="", icon="FILE_TEXT")
        row.prop(prefs, "show_image", text="", icon="IMAGE_DATA")
        row.prop(prefs, "show_badge", text="", icon="EVENT_NDOF_BUTTON_1")
        row.prop(prefs, "show_list", text="", icon="ALIGN_JUSTIFY")
        draw_ui_layout(layout,
                       context,
                       show_global=prefs.show_global,
                       show_text=prefs.show_text,
                       show_image=prefs.show_image,
                       show_badge=prefs.show_badge,
                       show_list=prefs.show_list)


classes = [
    NODE_OT_note_clear_select_all,
    NODE_OT_note_clear_select_txt,
    NODE_OT_note_clear_select_img,
    NODE_OT_note_clear_select_badge,
    NODE_OT_note_show_select_txt,
    NODE_OT_note_show_select_img,
    NODE_OT_note_show_select_badge,
    NODE_OT_note_delete_all_notes,
    NODE_OT_note_note_swap_order,
    NODE_OT_note_interactive_badge,
    NODE_OT_note_reset_prefs,
    NODE_OT_note_reset_offset,
    NODE_OT_note_reset_img_offset,
    NODE_OT_note_paste_image,
    NODE_OT_note_apply_preset,
    NODE_OT_note_copy_active_to_selected,
    NODE_OT_note_add_quick_tag,
    NODE_OT_note_copy_node_label,
    NODE_OT_note_note_quick_edit,
    NODE_OT_note_clear_search,
    NODE_OT_note_jump_to_note,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
