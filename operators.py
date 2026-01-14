import bpy
from bpy.types import Operator, Node, Nodes, NodeTree
from .preferences import pref
from .utils import get_image_from_clipboard, import_clipboard_image
from .ui import draw_panel_for_shortcut

class NODE_OT_note_note_swap_order(Operator):
    bl_idname = "node.note_swap_order"
    bl_label = "交换图文位置"
    bl_description = "交换选中节点文本笔记和图像笔记顺序"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        node = context.active_node
        if not node: return {'CANCELLED'}
        nodes = context.selected_nodes + [context.active_node]
        for node in nodes:
            if hasattr(node, "note_txt_pos") and hasattr(node, "note_img_pos"):
                align_txt = node.note_txt_pos
                align_img = node.note_img_pos
                if align_txt != align_img:
                    node.note_txt_pos = align_img
                    node.note_img_pos = align_txt
                else:
                    if hasattr(node, "note_swap_order"):
                        node.note_swap_order = not node.note_swap_order
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

def delete_notes(nodes: Nodes | list[Node]):
    for node in nodes:
        if node.note_text:
            node.note_text = ""
        if node.note_image:
            node.note_image = None
        if node.note_badge_index:
            node.note_badge_index = 0

class NODE_OT_note_delete_selected_txt(Operator):
    bl_idname = "node.note_delete_selected_txt"
    bl_label = "删除文本"
    bl_description = "删除选中节点的文字笔记"
    bl_options = {'UNDO'}

    def execute(self, context):
        for node in context.selected_nodes + [context.active_node]:
            if node.note_text:
                node.note_text = ""
        return {'FINISHED'}

class NODE_OT_note_delete_selected_img(Operator):
    bl_idname = "node.note_delete_selected_img"
    bl_label = "删除图片"
    bl_description = "删除选中节点的图片笔记"
    bl_options = {'UNDO'}

    def execute(self, context):
        nodes = context.selected_nodes + [context.active_node]
        for node in nodes:
            if node.note_image:
                node.note_image = None
        return {'FINISHED'}

class NODE_OT_note_delete_selected_badge(Operator):
    bl_idname = "node.note_delete_selected_badge"
    bl_label = "删除序号"
    bl_description = "删除选中节点的序号笔记"
    bl_options = {'UNDO'}

    def execute(self, context):
        nodes = context.selected_nodes + [context.active_node]
        for node in nodes:
            if node.note_badge_index:
                node.note_badge_index = 0
        return {'FINISHED'}

class NODE_OT_note_delete_selected_notes(Operator):
    bl_idname = "node.note_delete_selected_notes"
    bl_label = "删除全部"
    bl_description = "删除选中节点的所有笔记"
    bl_options = {'UNDO'}

    def execute(self, context):
        # todo 改进类似调用
        if not context.active_node: return {'CANCELLED'}
        nodes = context.selected_nodes + [context.active_node]
        delete_notes(nodes)
        return {'FINISHED'}

class NODE_OT_note_delete_all_notes(Operator):
    bl_idname = "node.note_delete_all_notes"
    bl_label = "删除所有笔记"
    bl_description = "删除节点树中所有笔记, 不包括节点组内的"
    bl_options = {'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        tree: NodeTree = context.space_data.edit_tree
        if tree:
            delete_notes(tree.nodes)
        return {'FINISHED'}

class NODE_OT_note_show_selected_txt(Operator):
    bl_idname = "node.note_show_selected_txt"
    bl_label = "显示文本"
    bl_description = "显示选中节点的文字笔记"
    bl_options = {'UNDO'}

    def execute(self, context):
        active_node = context.active_node
        nodes = context.selected_nodes
        new_value = not active_node.note_show_txt
        active_node.note_show_txt = new_value
        for node in nodes:
            node.note_show_txt = new_value
        return {'FINISHED'}

class NODE_OT_note_show_selected_img(Operator):
    bl_idname = "node.note_show_selected_img"
    bl_label = "显示图片"
    bl_description = "显示选中节点的图片笔记"
    bl_options = {'UNDO'}

    def execute(self, context):
        active_node = context.active_node
        nodes = context.selected_nodes
        new_value = not active_node.note_show_img
        active_node.note_show_img = new_value
        for node in nodes:
            node.note_show_img = new_value
        return {'FINISHED'}

class NODE_OT_note_show_selected_badge(Operator):
    bl_idname = "node.note_show_selected_badge"
    bl_label = "显示序号"
    bl_description = "显示选中节点的序号笔记"
    bl_options = {'UNDO'}

    def execute(self, context):
        active_node = context.active_node
        nodes = context.selected_nodes
        new_value = not active_node.note_show_badge
        active_node.note_show_badge = new_value
        for node in nodes:
            node.note_show_badge = new_value
        return {'FINISHED'}

class NODE_OT_note_reset_txt_offset(Operator):
    bl_idname = "node.note_reset_txt_offset"
    bl_label = "复位文本偏移"
    bl_options = {'UNDO'}

    def execute(self, context):
        node = context.active_node
        if hasattr(node, "note_txt_offset"): node.note_txt_offset = (0, 0)
        context.area.tag_redraw()
        return {'FINISHED'}

class NODE_OT_note_reset_img_offset(Operator):
    bl_idname = "node.note_reset_img_offset"
    bl_label = "复位图片偏移"
    bl_options = {'UNDO'}

    def execute(self, context):
        node = context.active_node
        if hasattr(node, "note_img_offset"): node.note_img_offset = (0, 0)
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
        image = import_clipboard_image()
        if image:
            image.use_fake_user = False
            active_node.note_image = image
            active_node.note_show_img = True
            self.report({'INFO'}, f"成功导入图片: {image.name}")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "剪贴板无图像或粘贴失败")
            return {'CANCELLED'}

class NODE_OT_note_paste_image_pil(Operator):
    bl_idname = "node.note_paste_image_pil"
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
    bl_label = "应用预设给选中节点"
    bl_options = {'UNDO'}
    bg_color: bpy.props.FloatVectorProperty(size=4)

    def execute(self, context):
        for node in (context.selected_nodes + [context.active_node]):
            node.note_txt_bg_color = self.bg_color
            node.note_text_color = (1, 1, 1, 1)
        return {'FINISHED'}

class NODE_OT_note_copy_active_to_selected(Operator):
    bl_idname = "node.note_copy_to_selected"
    bl_label = "同步活动样式给选中"
    bl_options = {'UNDO'}

    def execute(self, context):
        active = context.active_node
        if not active: return {'CANCELLED'}
        strict_sync_props = [
            "note_font_size", "note_text_color", "note_txt_bg_color", "note_badge_color", "note_txt_width_mode", "note_txt_bg_width",
            "note_img_width_mode", "note_img_width"
        ]
        count = 0
        for node in context.selected_nodes:
            if node == active: continue
            for prop in strict_sync_props:
                if hasattr(node, prop) and hasattr(active, prop):
                    setattr(node, prop, getattr(active, prop))
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
        for node in (context.selected_nodes + [context.active_node]):
            node.note_text = (self.tag_text + " " + node.note_text) if pref().tag_mode_prepend else (node.note_text + " " + self.tag_text)
        return {'FINISHED'}

class NODE_OT_note_jump_to_note(Operator):
    """跳转到指定注记节点"""
    bl_idname = "node.note_jump_to_note"
    bl_label = "跳转到注记"
    bl_description = "聚焦视图到该节点"
    node_name: bpy.props.StringProperty()

    def execute(self, context):
        nodes = context.space_data.edit_tree.nodes
        target_node = nodes[self.node_name]
        for node in nodes:
            node.select = False
        target_node.select = True
        nodes.active = target_node
        bpy.ops.node.view_selected()
        return {'FINISHED'}

class NODE_OT_note_note_quick_edit(Operator):
    bl_idname = "node.note_quick_edit"
    bl_label = "节点随记"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  # 空的也得有
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window.cursor_warp(event.mouse_x + pref().cursor_warp_x, event.mouse_y)
        return context.window_manager.invoke_popup(self, width=220)

    def draw(self, context):
        draw_panel_for_shortcut(self.layout, context)

classes = [
    NODE_OT_note_delete_selected_txt,
    NODE_OT_note_delete_selected_img,
    NODE_OT_note_delete_selected_badge,
    NODE_OT_note_delete_selected_notes,
    NODE_OT_note_delete_all_notes,
    NODE_OT_note_show_selected_txt,
    NODE_OT_note_show_selected_img,
    NODE_OT_note_show_selected_badge,
    NODE_OT_note_note_swap_order,
    NODE_OT_note_interactive_badge,
    NODE_OT_note_reset_txt_offset,
    NODE_OT_note_reset_img_offset,
    NODE_OT_note_paste_image,
    NODE_OT_note_paste_image_pil,
    NODE_OT_note_apply_preset,
    NODE_OT_note_copy_active_to_selected,
    NODE_OT_note_add_quick_tag,
    NODE_OT_note_note_quick_edit,
    NODE_OT_note_jump_to_note,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
