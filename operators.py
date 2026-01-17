import bpy
from bpy.types import Operator, Node, Nodes, NodeTree, Context, Image
from bpy.props import EnumProperty, BoolProperty
from .preferences import pref
from .utils import import_clipboard_image, text_split_lines


class NoteBaseOperator(Operator):
    bl_options = {'REGISTER', 'UNDO'}
    @classmethod
    def poll(cls, context):
        return context.active_node is not None

    def get_selected_nodes(self, context: Context, skip_active: bool = False) -> list[Node]:
        nodes = context.selected_nodes
        active = context.active_node
        if active and not active.select and not skip_active:
            nodes.append(active)
        return nodes

class NODE_OT_note_note_swap_order(NoteBaseOperator):
    bl_idname = "node.note_swap_order"
    bl_label = "交换图文位置"
    bl_description = "交换选中节点文本笔记和图像笔记顺序"

    def execute(self, context):
        nodes = self.get_selected_nodes(context)
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

def delete_notes(nodes: Nodes | list[Node]):
    for node in nodes:
        if node.note_text:
            node.note_text = ""
        if node.note_image:
            node.note_image = None
        if node.note_badge_index:
            node.note_badge_index = 0

class NODE_OT_note_delete_selected_txt(NoteBaseOperator):
    bl_idname = "node.note_delete_selected_txt"
    bl_label = "删除文本(多选)"
    bl_description = "删除选中节点的文字笔记"

    def execute(self, context):
        for node in self.get_selected_nodes(context):
            if node.note_text:
                node.note_text = ""
        return {'FINISHED'}

class NODE_OT_note_delete_selected_badge(NoteBaseOperator):
    bl_idname = "node.note_delete_selected_badge"
    bl_label = "删除序号(多选)"
    bl_description = "删除选中节点的序号笔记"

    def execute(self, context):
        for node in self.get_selected_nodes(context):
            if node.note_badge_index:
                node.note_badge_index = 0
        return {'FINISHED'}

class NoteDeleteOperator(NoteBaseOperator):
    confirm_delete: bpy.props.BoolProperty(name="同时从Blender文件里移除图片", default=False)

    def draw(self, context):
        self.layout.prop(self, "confirm_delete", text="同时移除图片")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

class NODE_OT_note_delete_selected_img(NoteDeleteOperator):
    bl_idname = "node.note_delete_selected_img"
    bl_label = "移除图片(多选)"
    bl_description = "从Blender文件里移除选中节点图片笔记对应的图片"

    def execute(self, context):
        for node in self.get_selected_nodes(context):
            if node.note_image:
                image = node.note_image
                node.note_image = None
                if self.confirm_delete:
                    bpy.data.images.remove(image)
        return {'FINISHED'}

class NODE_OT_note_delete_selected_notes(NoteDeleteOperator):
    bl_idname = "node.note_delete_selected_notes"
    bl_label = "删除选中三种笔记(多选)"
    bl_description = "删除选中节点的三种笔记"

    def execute(self, context):
        images_to_delete = []
        for node in self.get_selected_nodes(context):
            if node.note_image:
                image = node.note_image
                node.note_image = None
                if self.confirm_delete:
                    images_to_delete.append(image)
            if node.note_text:
                node.note_text = ""
            if node.note_badge_index:
                node.note_badge_index = 0
        if self.confirm_delete:
            for image in images_to_delete:
                bpy.data.images.remove(image)
        return {'FINISHED'}

class NODE_OT_note_delete_all_notes(NoteDeleteOperator):
    bl_idname = "node.note_delete_all_notes"
    bl_label = "删除所有笔记"
    bl_description = "删除节点树中所有笔记, 不包括节点组内的"

    def execute(self, context):
        tree: NodeTree = context.space_data.edit_tree
        if tree:
            images_to_delete = []
            for node in tree.nodes:
                if node.note_image:
                    image = node.note_image
                    node.note_image = None
                    images_to_delete.append(image)
                if node.note_text:
                    node.note_text = ""
                if node.note_badge_index:
                    node.note_badge_index = 0
            if self.confirm_delete:
                for image in images_to_delete:
                    bpy.data.images.remove(image)
        return {'FINISHED'}

class NODE_OT_note_show_selected_txt(NoteBaseOperator):
    bl_idname = "node.note_show_selected_txt"
    bl_label = "显示文本(多选)"
    bl_description = "显示选中节点的文字笔记"

    def execute(self, context):
        active_node = context.active_node
        new_value = not active_node.note_show_txt
        for node in self.get_selected_nodes(context):
            node.note_show_txt = new_value
        return {'FINISHED'}

class NODE_OT_note_show_selected_img(NoteBaseOperator):
    bl_idname = "node.note_show_selected_img"
    bl_label = "显示图片(多选)"
    bl_description = "显示选中节点的图片笔记"

    def execute(self, context):
        active_node = context.active_node
        new_value = not active_node.note_show_img
        for node in self.get_selected_nodes(context):
            node.note_show_img = new_value
        return {'FINISHED'}

class NODE_OT_note_show_selected_badge(NoteBaseOperator):
    bl_idname = "node.note_show_selected_badge"
    bl_label = "显示序号(多选)"
    bl_description = "显示选中节点的序号笔记"

    def execute(self, context):
        active_node = context.active_node
        new_value = not active_node.note_show_badge
        for node in self.get_selected_nodes(context):
            node.note_show_badge = new_value
        return {'FINISHED'}

class NODE_OT_note_apply_preset(NoteBaseOperator):
    bl_idname = "node.note_apply_preset"
    bl_label = "应用预设给选中节点(多选)"
    bg_color: bpy.props.FloatVectorProperty(size=4)

    def execute(self, context):
        for node in self.get_selected_nodes(context):
            node.note_txt_bg_color = self.bg_color
            node.note_text_color = (1, 1, 1, 1)
        return {'FINISHED'}

class NODE_OT_note_copy_active_to_selected(NoteBaseOperator):
    bl_idname = "node.note_copy_to_selected"
    bl_label = "同步活动样式给选中(多选)"

    def execute(self, context):
        # todo 改为从偏好设置导入
        strict_sync_props = [
            "note_font_size", "note_text_color", "note_txt_bg_color", "note_badge_color", "note_txt_width_mode", "note_txt_bg_width",
            "note_img_width_mode", "note_img_width"
        ]
        count = 0
        active = context.active_node
        for node in self.get_selected_nodes(context, skip_active=True):
            for prop in strict_sync_props:
                setattr(node, prop, getattr(active, prop))
            count += 1
        self.report({'INFO'}, f"已同步 6 项样式至 {count} 个节点")
        context.area.tag_redraw()
        return {'FINISHED'}

class NODE_OT_note_add_quick_tag(NoteBaseOperator):
    bl_idname = "node.note_add_quick_tag"
    bl_label = "标签"
    tag_text: bpy.props.StringProperty()

    def execute(self, context):
        for node in self.get_selected_nodes(context):
            node.note_text = (self.tag_text + " " + node.note_text) if pref().tag_mode_prepend else (node.note_text + " " + self.tag_text)
        return {'FINISHED'}

class NODE_OT_note_reset_offset(NoteBaseOperator):
    bl_idname = "node.note_reset_offset"
    bl_label = "复位偏移(多选)"
    is_txt: bpy.props.BoolProperty()

    def execute(self, context):
        for node in self.get_selected_nodes(context):
            if self.is_txt:
                node.note_txt_offset = (0, 0)
            else:
                node.note_img_offset = (0, 0)
        return {'FINISHED'}

class NODE_OT_note_paste_image(NoteBaseOperator):
    bl_idname = "node.note_paste_image"
    bl_label = "从剪贴板粘贴图像"
    bl_description = "从剪贴板粘贴图像"

    def execute(self, context):
        active_node = context.active_node
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

class NODE_OT_note_pack_unpack_images(NoteBaseOperator):
    bl_idname = "node.note_pack_unpack_images"
    bl_label = "打包/解包图片"
    bl_options = {'REGISTER', 'UNDO'}

    is_pack: BoolProperty(name="打包模式", default=False)
    pack_scope: EnumProperty(
        name="操作范围",
        items=[
            ('ALL', "所有节点树", "遍历所有节点树中的节点"),
            ('CURRENT', "当前节点树", "仅当前节点树的节点"),
            ('SELECTED', "选中节点", "仅选中的节点"),
        ],
        default='SELECTED',
    )
    unpack_method: EnumProperty(
        name="解包方式",
        items=[
            ('USE_LOCAL', "使用当前目录", "在blend文件所在目录创建文件(不覆盖)", 'FILE_FOLDER', 0),
            ('WRITE_LOCAL', "写入当前目录", "在blend文件所在目录写入文件(覆盖)", 'EXPORT', 1),
            ('USE_ORIGINAL', "使用原始位置", "在图片原始目录创建文件(不覆盖)", 'FILE', 2),
            ('WRITE_ORIGINAL', "写入原始位置", "在图片原始目录写入文件(覆盖)", 'EXPORT', 3),
        ],
        default='USE_LOCAL',
    )

    @classmethod
    def description(cls, context, properties):
        if properties.is_pack:
            return "外部图片将打包到Blend文件"
        else:
            return "将图片将解包到原始目录或当前目录"

    def draw(self, context):
        layout = self.layout
        row1 = layout.split(factor=0.2)
        row1.label(text="范围:")
        row1.column().prop(self, "pack_scope", expand=True)
        if not self.is_pack:
            row2 = layout.split(factor=0.2)
            row2.label(text="位置:")
            row2.column().prop(self, "unpack_method", expand=True)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def execute(self, context):
        nodes = []
        if self.pack_scope == 'ALL':
            for tree in bpy.data.node_groups:
                nodes.extend(tree.nodes)
        elif self.pack_scope == 'CURRENT':
            tree = context.space_data.edit_tree
            if tree:
                nodes = list(tree.nodes)
        elif self.pack_scope == 'SELECTED':
            nodes = self.get_selected_nodes(context)

        if self.is_pack:
            return self._pack_images(nodes)
        else:
            return self._unpack_images(nodes)

    def _unpack_images(self, nodes):
        if not bpy.data.filepath:
            self.report({'WARNING'}, "请先保存Blend文件")
            return {'CANCELLED'}

        return self._process_images(nodes, process=lambda img: (img.save(), img.unpack(method=self.unpack_method)))

    def _pack_images(self, nodes):
        return self._process_images(nodes, process=lambda img: img.pack())

    def _process_images(self, nodes, process):
        pack_status = self.is_pack
        count = found = valid = 0
        action = "打包" if pack_status else "解包"
        status_name = "外部图片" if pack_status else "已打包"

        for node in nodes:
            if not node.note_image:
                continue

            found += 1
            image: Image = node.note_image
            if image.packed_file is not None if pack_status else image.packed_file is None:
                continue
            valid += 1
            try:
                process(image)
                count += 1
            except Exception as e:
                print(f"无法{action}图片 {image.name}: {e}")

        if count > 0:
            self.report({'INFO'}, f"已{action} {count} 张图片")
        else:
            self.report({'WARNING'}, f"未找到需要{action}的图片 (找到: {found}, {status_name}: {valid})")

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

class NODE_OT_note_open_image_editor(NoteBaseOperator):
    bl_idname = "node.note_open_image_editor"
    bl_label = "打开图像编辑器"
    bl_description = "在浮动的图像编辑器中查看图片"

    def execute(self, context):
        node = context.active_node

        # Use render resolution to control window size
        render = context.scene.render
        view = context.preferences.view

        # Save original settings
        old_res_x = render.resolution_x
        old_res_y = render.resolution_y
        old_res_percent = render.resolution_percentage
        old_display_type = view.render_display_type

        try:
            # Set target resolution to fit image within half window size
            # Calculate scale based on area (target: 1/4 of window area)
            image_width, image_height = node.note_image.size
            window_width = context.window.width
            window_height = context.window.height

            target_area = (window_width*window_height) / 4
            image_area = image_width * image_height
            scale = (target_area / image_area)**0.5
            scale = min(scale, (window_width*0.8) / image_width, (window_height*0.8) / image_height)

            res_x = int(image_width * scale)
            res_y = int(image_height * scale)
            render.resolution_x = res_x
            render.resolution_y = res_y
            render.resolution_percentage = 100
            view.render_display_type = 'WINDOW'

            # Open window
            bpy.ops.render.view_show('INVOKE_DEFAULT')

            # Configure new window
            new_window = context.window_manager.windows[-1]
            area = next((_area for _area in new_window.screen.areas if _area.type == 'IMAGE_EDITOR'), None)
            if area:
                space = area.spaces.active
                space.image = node.note_image
                space.show_region_toolbar = True

                for region in area.regions:
                    if region.type == 'WINDOW':
                        with context.temp_override(window=new_window, area=area, region=region):
                            bpy.ops.image.view_all(fit_view=True)
                            bpy.ops.image.view_zoom_out(location=(0.5, 0.5))
                        break
        except Exception as e:
            self.report({'WARNING'}, f"打开图像编辑器失败: {e}")
        finally:
            # Restore settings
            render.resolution_x = old_res_x
            render.resolution_y = old_res_y
            render.resolution_percentage = old_res_percent
            view.render_display_type = old_display_type

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
        from .ui import draw_panel_for_shortcut
        draw_panel_for_shortcut(self.layout, context)

class NODE_OT_note_interactive_badge(Operator):
    bl_idname = "node.note_interactive_badge"
    bl_label = "交互式编号"
    bl_description = "画笔点选节点自动编号 (右键/ESC退出)"
    bl_options = {'REGISTER', 'UNDO'}

    def modal(self, context, event):
        # 检查标记,如果被外部关闭则退出
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
        # 如果已经是交互模式,再次点击则关闭(自开关逻辑)
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


class NODE_OT_note_paste_text_from_clipboard(NoteBaseOperator):
    bl_idname = "node.note_paste_text_from_clipboard"
    bl_label = "从剪贴板粘贴文本"
    bl_description = "从剪贴板粘贴文本,并根据设置替换换行符"

    def execute(self, context):
        node = context.active_node
        text = context.window_manager.clipboard
        if not text:
            self.report({'WARNING'}, "剪贴板为空")
            return {'CANCELLED'}

        separator = pref().line_separator
        if separator:
            first_sep = separator.split('|')[0]
            text = text.replace('\n', first_sep)

        node.note_text = text
        return {'FINISHED'}

class NODE_OT_note_copy_text_to_clipboard(NoteBaseOperator):
    bl_idname = "node.note_copy_text_to_clipboard"
    bl_label = "复制文本到剪贴板"
    bl_description = "复制文本到剪贴板,并将换行符还原为\\n"

    def execute(self, context):
        node = context.active_node
        lines = text_split_lines(node.note_text)
        text = "\n".join(lines)
        context.window_manager.clipboard = text
        self.report({'INFO'}, "已复制到剪贴板")
        return {'FINISHED'}

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
    NODE_OT_note_reset_offset,
    NODE_OT_note_paste_image,
    NODE_OT_note_apply_preset,
    NODE_OT_note_copy_active_to_selected,
    NODE_OT_note_add_quick_tag,
    NODE_OT_note_pack_unpack_images,
    NODE_OT_note_note_quick_edit,
    NODE_OT_note_jump_to_note,
    NODE_OT_note_open_image_editor,
    NODE_OT_note_paste_text_from_clipboard,
    NODE_OT_note_copy_text_to_clipboard,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
