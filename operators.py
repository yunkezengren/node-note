import bpy
from bpy.types import Operator, Node, Nodes, NodeTree, Context, Image
from bpy.props import EnumProperty, BoolProperty
from .preferences import pref
from .utils import import_clipboard_image, text_split_lines
from bpy.app.translations import pgettext_iface as iface

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
    bl_label = "Swap Text and Image Position"
    bl_description = "Swap text and image note order for selected nodes"

    def execute(self, context):
        nodes = self.get_selected_nodes(context)
        for node in nodes:
            align_txt = node.note_txt_pos
            align_img = node.note_img_pos
            if align_txt != align_img:
                node.note_txt_pos = align_img
                node.note_img_pos = align_txt
            else:
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
    bl_label = "Delete Text (Multi-Select)"
    bl_description = "Delete text notes from selected nodes"

    def execute(self, context):
        for node in self.get_selected_nodes(context):
            if node.note_text:
                node.note_text = ""
        return {'FINISHED'}

class NODE_OT_note_delete_selected_badge(NoteBaseOperator):
    bl_idname = "node.note_delete_selected_badge"
    bl_label = "Delete Index (Multi-Select)"
    bl_description = "Delete index notes from selected nodes"

    def execute(self, context):
        for node in self.get_selected_nodes(context):
            if node.note_badge_index:
                node.note_badge_index = 0
        return {'FINISHED'}

class NoteDeleteOperator(NoteBaseOperator):
    confirm_delete: bpy.props.BoolProperty(name="Also remove images from Blender file", default=False)

    def draw(self, context):
        self.layout.prop(self, "confirm_delete", text="Also Remove Image")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

class NODE_OT_note_delete_selected_img(NoteDeleteOperator):
    bl_idname = "node.note_delete_selected_img"
    bl_label = "Remove Image (Multi-Select)"
    bl_description = "Remove images corresponding to selected nodes' image notes from Blender file"

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
    bl_label = "Delete All Three Note Types (Multi-Select)"
    bl_description = "Delete all three types of notes from selected nodes"

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
    bl_label = "Delete All Notes"
    bl_description = "Delete all notes in node tree, excluding those in node groups"

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
    bl_label = "Show Text (Multi-Select)"
    bl_description = "Show text notes of selected nodes"

    def execute(self, context):
        active_node = context.active_node
        new_value = not active_node.note_show_txt
        for node in self.get_selected_nodes(context):
            node.note_show_txt = new_value
        return {'FINISHED'}

class NODE_OT_note_show_selected_img(NoteBaseOperator):
    bl_idname = "node.note_show_selected_img"
    bl_label = "Show Image (Multi-Select)"
    bl_description = "Show image notes of selected nodes"

    def execute(self, context):
        active_node = context.active_node
        new_value = not active_node.note_show_img
        for node in self.get_selected_nodes(context):
            node.note_show_img = new_value
        return {'FINISHED'}

class NODE_OT_note_show_selected_badge(NoteBaseOperator):
    bl_idname = "node.note_show_selected_badge"
    bl_label = "Show Index (Multi-Select)"
    bl_description = "Show index notes of selected nodes"

    def execute(self, context):
        active_node = context.active_node
        new_value = not active_node.note_show_badge
        for node in self.get_selected_nodes(context):
            node.note_show_badge = new_value
        return {'FINISHED'}

class NODE_OT_note_apply_preset(NoteBaseOperator):
    bl_idname = "node.note_apply_preset"
    bl_label = "Apply Preset to Selected Nodes (Multi-Select)"
    bg_color: bpy.props.FloatVectorProperty(size=4)

    def execute(self, context):
        for node in self.get_selected_nodes(context):
            node.note_txt_bg_color = self.bg_color
            node.note_text_color = (1, 1, 1, 1)
        return {'FINISHED'}

class NODE_OT_note_copy_active_to_selected(NoteBaseOperator):
    bl_idname = "node.note_copy_to_selected"
    bl_label = "Sync Active Style to Selected (Multi-Select)"

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
        self.report({'INFO'}, iface("Style synced to {count} nodes").format(count=count))
        context.area.tag_redraw()
        return {'FINISHED'}

class NODE_OT_note_add_quick_tag(NoteBaseOperator):
    bl_idname = "node.note_add_quick_tag"
    bl_label = "Tag"
    tag_text: bpy.props.StringProperty()

    def execute(self, context):
        for node in self.get_selected_nodes(context):
            node.note_text = (self.tag_text + " " + node.note_text) if pref().tag_mode_prepend else (node.note_text + " " + self.tag_text)
        return {'FINISHED'}

class NODE_OT_note_reset_offset(NoteBaseOperator):
    bl_idname = "node.note_reset_offset"
    bl_label = "Reset Offset (Multi-Select)"
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
    bl_label = "Paste Image"
    bl_description = "Paste Image from Clipboard"

    def execute(self, context):
        active_node = context.active_node
        image = import_clipboard_image()
        if image:
            image.use_fake_user = False
            active_node.note_image = image
            active_node.note_show_img = True
            self.report({'INFO'}, iface("Successfully imported image: {image_name}").format(image_name=image.name))
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Clipboard is empty")
            return {'CANCELLED'}

class NODE_OT_note_pack_unpack_images(NoteBaseOperator):
    bl_idname = "node.note_pack_unpack_images"
    bl_label = "Pack/Unpack Images"
    bl_options = {'REGISTER', 'UNDO'}

    is_pack: BoolProperty(name="Pack Mode", default=False)
    pack_scope: EnumProperty(
        name="Operation Scope",
        items=[
            ('ALL', "All Node Trees", "Traverse nodes in all node trees"),
            ('CURRENT', "Current Node Tree", "Only nodes in the current node tree"),
            ('SELECTED', "Selected Nodes", "Only selected nodes"),
        ],
        default='SELECTED',
    )
    unpack_method: EnumProperty(
        name="Unpack Method",
        items=[
            ('USE_LOCAL', "Use Current Directory", "Create files in blend file directory (no overwrite)", 'FILE_FOLDER', 0),
            ('WRITE_LOCAL', "Write to Current Directory", "Write files to blend file directory (overwrite)", 'EXPORT', 1),
            ('USE_ORIGINAL', "Use Original Location", "Create files in original image directory (no overwrite)", 'FILE', 2),
            ('WRITE_ORIGINAL', "Write to Original Location", "Write files to original image directory (overwrite)", 'EXPORT', 3),
        ],
        default='USE_LOCAL',
    )

    @classmethod
    def description(cls, context, properties):
        if properties.is_pack:
            return iface("External images will be packed into Blend file")
        else:
            return iface("Images will be unpacked to original or current directory")

    def draw(self, context):
        layout = self.layout
        row1 = layout.split(factor=0.3)
        row1.label(text="Operation Scope")
        row1.column().prop(self, "pack_scope", expand=True)
        if not self.is_pack:
            row2 = layout.split(factor=0.3)
            row2.label(text="Unpack Method")
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
            self.report({'WARNING'}, "Please save Blend file first")
            return {'CANCELLED'}

        return self._process_images(nodes, process=lambda img: (img.save(), img.unpack(method=self.unpack_method)))

    def _pack_images(self, nodes):
        return self._process_images(nodes, process=lambda img: img.pack())

    def _process_images(self, nodes, process):
        pack_status = self.is_pack
        count = found = valid = 0
        action = "Pack" if pack_status else "Unpack"
        status_name = "External images" if pack_status else "Already packed"

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
                print(f"Cannot {action} image {image.name}: {e}")

        if count > 0:
            self.report({'INFO'}, iface("{action}ed {count} images").format(action=iface(action), count=count))
        else:
            self.report({'WARNING'}, iface("No images found to {action} (found: {found}, {status_name}: {valid})").format(action=iface(action), found=found, status_name=iface(status_name), valid=valid))

        return {'FINISHED'}

class NODE_OT_note_jump_to_note(Operator):
    bl_idname = "node.note_jump_to_note"
    bl_label = "Jump to Node with Note"
    bl_description = "Jump to the node containing the note"
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
    bl_label = "Open Image Editor"
    bl_description = "View image in floating image editor"

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
            self.report({'WARNING'}, iface("Failed to open image editor: {error}").format(error=e))
        finally:
            # Restore settings
            render.resolution_x = old_res_x
            render.resolution_y = old_res_y
            render.resolution_percentage = old_res_percent
            view.render_display_type = old_display_type

        return {'FINISHED'}

class NODE_OT_note_note_quick_edit(Operator):
    bl_idname = "node.note_quick_edit"
    bl_label = "Node Notes"
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
    bl_label = "Interactive Numbering"
    bl_description = "Click nodes to auto-number (right-click/ESC to exit)"
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

                    msg = iface("Interactive Mode [Right-click/ESC to exit] | Market: {node_name} -> #{index}").format(node_name=node.name, index=self.current_idx)
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
                max_idx = max((node.note_badge_index for node in tree.nodes), default=0)

            self.current_idx = max_idx
            self.last_node = None

            context.window_manager.modal_handler_add(self)
            context.window.cursor_modal_set('PAINT_BRUSH')
            context.area.header_text_set(iface("Interactive Mode [Right-click/ESC to exit] | Current max index: #{max_idx}").format(max_idx=max_idx))
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "Node editor not found")
            pref().is_interactive_mode = False
            return {'CANCELLED'}

class NODE_OT_note_paste_text_from_clipboard(NoteBaseOperator):
    bl_idname = "node.note_paste_text_from_clipboard"
    bl_label = "Paste Text from Clipboard"
    bl_description = "Paste text from clipboard, replace line breaks according to settings"

    def execute(self, context):
        node = context.active_node
        text = context.window_manager.clipboard
        if not text:
            self.report({'WARNING'}, "Clipboard is empty")
            return {'CANCELLED'}

        separator = pref().line_separatore
        if separator:
            first_sep = separator.split('|')[0]
            text = text.replace('\n', first_sep)

        node.note_text = text
        return {'FINISHED'}

class NODE_OT_note_copy_text_to_clipboard(NoteBaseOperator):
    bl_idname = "node.note_copy_text_to_clipboard"
    bl_label = "Copy Text to Clipboard"
    bl_description = "Copy text to clipboard, restore line breaks to \\n"

    def execute(self, context):
        node = context.active_node
        lines = text_split_lines(node.note_text)
        text = "\n".join(lines)
        context.window_manager.clipboard = text
        self.report({'INFO'}, "Copied to clipboard")
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
