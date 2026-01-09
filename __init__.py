import bpy
from bpy.types import Operator, Panel, UILayout, Node
from bpy.props import StringProperty, IntProperty, FloatVectorProperty, BoolProperty, PointerProperty, FloatProperty, EnumProperty, IntVectorProperty
from . import draw_core
from . import edit_ops
from . import search_ops
from .preference import pref, tag_redraw, NodeMemoAddonPreferences

addon_keymaps = []

# --- 属性更新回调 ---

def update_interactive_mode(self, context):
    # [修复] 不再通过回调启动操作符，只负责刷新界面
    context.area.tag_redraw()

def update_manual_text_width(self, context):
    if self.na_auto_txt_width: self.na_auto_txt_width = False
    if self.na_text_fit_content: self.na_text_fit_content = False
    tag_redraw(self, context)

def update_manual_img_width(self, context):
    if self.na_auto_img_width: self.na_auto_img_width = False
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

class NODE_OT_reset_prefs(Operator):
    """重置当前页面的设置"""
    bl_idname = "node.na_reset_prefs"
    bl_label = "重置为默认"
    bl_options = {'INTERNAL'}

    target_section: StringProperty()

    def execute(self, context):
        prefs = pref()
        if self.target_section == 'SEQ':
            for p in ["seq_radius", "seq_bg_color", "seq_font_size", "seq_font_color"]:
                prefs.property_unset(p)
        elif self.target_section == 'TEXT':
            for p in ["text_default_size", "text_default_color", "bg_default_color", "text_default_fit", "text_default_align"]:
                prefs.property_unset(p)
            for i in range(1, 7):
                prefs.property_unset(f"col_preset_{i}")
                prefs.property_unset(f"label_preset_{i}")
        elif self.target_section == 'IMG':
            for p in ["img_max_res", "img_default_align"]:
                prefs.property_unset(p)
        return {'FINISHED'}

# --- 属性初始化 ---

def init_props():
    Node.na_text = StringProperty(name="内容", default="", update=tag_redraw, options={'TEXTEDIT_UPDATE'})
    Node.na_font_size = IntProperty(name="字号", default=8, min=4, max=500, update=tag_redraw)
    Node.na_txt_bg_color = FloatVectorProperty(name="背景",
                                               subtype='COLOR',
                                               size=4,
                                               default=(0.2, 0.3, 0.5, 0.9),
                                               min=0.0,
                                               max=1.0,
                                               update=tag_redraw)
    Node.na_text_color = FloatVectorProperty(name="文字",
                                             subtype='COLOR',
                                             size=4,
                                             default=(1.0, 1.0, 1.0, 1.0),
                                             min=0.0,
                                             max=1.0,
                                             update=tag_redraw)
    Node.na_text_fit_content = BoolProperty(name="适应文本", default=False, update=tag_redraw, description="背景宽度自动适应文本内容")
    Node.na_show_txt = BoolProperty(name="显示文本", default=True, update=tag_redraw)
    Node.na_auto_txt_width = BoolProperty(name="跟随节点", default=True, update=tag_redraw, description="宽度自动跟随节点宽度")
    Node.na_txt_bg_width = IntProperty(name="背景宽", default=200, min=1, max=2000, update=update_manual_text_width)
    Node.na_swap_content_order = BoolProperty(name="互换位置", default=False, update=tag_redraw)
    Node.na_z_order_switch = BoolProperty(name="层级切换", description="交换图片与文字的前后层级", default=False, update=tag_redraw)
    Node.na_seq_index = IntProperty(name="序号", default=0, min=0, update=tag_redraw, description="逻辑序号 (0为不显示)")
    Node.na_sequence_color = FloatVectorProperty(name="序号颜色",
                                                 subtype='COLOR',
                                                 size=4,
                                                 default=(0.8, 0.1, 0.1, 1.0),
                                                 min=0.0,
                                                 max=1.0,
                                                 update=tag_redraw)
    Node.na_image = PointerProperty(name="图像", type=bpy.types.Image, update=update_na_image)
    Node.na_auto_img_width = BoolProperty(name="自动图宽", default=True, update=tag_redraw)
    Node.na_img_width = IntProperty(name="图宽", default=140, min=10, max=2000, update=update_manual_img_width)
    Node.na_show_img = BoolProperty(name="显示图片", default=True, update=tag_redraw)
    Node.na_show_seq = BoolProperty(name="显示序号", default=True, update=tag_redraw)
    align_items = [('TOP', "顶部", ""), ('BOTTOM', "底部", ""), ('LEFT', "左侧", ""), ('RIGHT', "右侧", "")]
    Node.na_txt_pos = EnumProperty(name="对齐", items=align_items, default='TOP', update=tag_redraw, description="文本位置")
    Node.na_txt_offset = IntVectorProperty(name="文本偏移", size=2, default=(0, 0), update=tag_redraw, subtype='XYZ', description="文本偏移")
    Node.na_img_pos = EnumProperty(name="图对齐", items=align_items, default='TOP', update=tag_redraw, description="图像位置")
    Node.na_img_offset = IntVectorProperty(name="图像偏移", size=2, default=(0, 0), update=tag_redraw, subtype='XYZ', description="图像偏移")
    Node.na_is_initialized = BoolProperty(default=False)

def clear_props():
    props = [
        "na_text", "na_font_size", "na_txt_bg_color", "na_text_color", "na_auto_txt_width", "na_txt_bg_width", "na_swap_content_order",
        "na_image", "na_img_width", "na_show_img", "na_auto_img_width", "na_txt_pos", "na_txt_offset", "na_z_order_switch",
        "na_seq_index", "na_sequence_color", "na_img_pos", "na_img_offset", "na_text_fit_content", "na_show_txt", "na_is_initialized"
    ]
    for p in props:
        if hasattr(Node, p): delattr(Node, p)
    for p in dir(bpy.types.Scene):
        if p.startswith("na_"): delattr(bpy.types.Scene, p)

class NODE_PT_annotator_gpu_panel(Panel):
    bl_label = "节点随记"
    bl_idname = "NODE_PT_annotator_gpu_panel"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Node"

    @classmethod
    def poll(cls, context):
        return context.space_data.type == 'NODE_EDITOR'

    def draw(self, context):
        layout = self.layout
        edit_ops.draw_ui_layout(layout, context)

class NODE_OT_na_swap_order(Operator):
    bl_idname = "node.na_swap_order"
    bl_label = "交换图文位置"
    bl_description = "文本笔记和图像笔记交换顺序"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        node = context.active_node
        if not node: return {'CANCELLED'}
        if hasattr(node, "na_txt_pos") and hasattr(node, "na_img_pos"):
            align_txt = node.na_txt_pos
            align_img = node.na_img_pos
            if align_txt != align_img:
                node.na_txt_pos = align_img
                node.na_img_pos = align_txt
            else:
                if hasattr(node, "na_swap_content_order"):
                    node.na_swap_content_order = not node.na_swap_content_order
            context.area.tag_redraw()
        return {'FINISHED'}

class NODE_OT_interactive_seq(Operator):
    bl_idname = "node.na_interactive_seq"
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
                try:
                    bpy.ops.node.select(location=(event.mouse_region_x, event.mouse_region_y), extend=False)
                    node = context.active_node

                    if node and node != self.last_node:
                        self.current_idx += 1
                        node.na_seq_index = self.current_idx

                        if node.na_seq_index > 0:
                            node.na_sequence_color = pref().seq_bg_color

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
        if pref().is_interactive_mode:
            pref().is_interactive_mode = False
            return {'FINISHED'}

        if context.area.type == 'NODE_EDITOR':
            # 开启模式
            pref().is_interactive_mode = True

            max_idx = 0
            tree = context.space_data.edit_tree
            if tree:
                for n in tree.nodes:
                    if hasattr(n, "na_seq_index"):
                        max_idx = max(max_idx, n.na_seq_index)

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

# todo 增加 self.report({'INFO'}, f"已删除 {count} 个节点的序号")

class NODE_OT_clear_select_all(Operator):
    bl_idname = "node.na_clear_select_all"
    bl_label = "删除全部"
    bl_description = "删除选中节点的所有笔记"
    bl_options = {'UNDO'}

    def execute(self, context):
        nodes = context.selected_nodes if context.selected_nodes else [context.active_node]
        for node in nodes:
            if node.na_text or node.na_image or node.na_seq_index:
                node.na_text = ""
                node.na_image = None
                node.na_seq_index = 0
                node.na_is_initialized = False
        return {'FINISHED'}

class NODE_OT_clear_select_txt(Operator):
    bl_idname = "node.na_clear_select_txt"
    bl_label = "删除文本"
    bl_description = "删除选中节点的文字笔记"
    bl_options = {'UNDO'}

    def execute(self, context):
        nodes = context.selected_nodes if context.selected_nodes else [context.active_node]
        for node in nodes:
            if not node.na_text: continue
            node.na_text = ""
            if not node.na_image and not node.na_seq_index:
                node.na_is_initialized = False
        return {'FINISHED'}

class NODE_OT_clear_select_img(Operator):
    bl_idname = "node.na_clear_select_img"
    bl_label = "删除图片"
    bl_description = "删除选中节点的图片笔记"
    bl_options = {'UNDO'}

    def execute(self, context):
        nodes = context.selected_nodes if context.selected_nodes else [context.active_node]
        for node in nodes:
            if not node.na_image: continue
            node.na_image = None
            if not node.na_text and not node.na_seq_index:
                node.na_is_initialized = False
        return {'FINISHED'}

class NODE_OT_clear_select_seq(Operator):
    bl_idname = "node.na_clear_select_seq"
    bl_label = "删除序号"
    bl_description = "删除选中节点的序号笔记"
    bl_options = {'UNDO'}

    def execute(self, context):
        nodes = context.selected_nodes if context.selected_nodes else [context.active_node]
        for node in nodes:
            if not node.na_seq_index: continue
            node.na_seq_index = 0
            if not node.na_text and not node.na_image:
                node.na_is_initialized = False
        return {'FINISHED'}

class NODE_OT_show_select_txt(Operator):
    bl_idname = "node.na_show_select_txt"
    bl_label = "显示文本"
    bl_description = "显示选中节点的文字笔记"
    bl_options = {'UNDO'}

    def execute(self, context):
        nodes = context.selected_nodes if context.selected_nodes else [context.active_node]
        for node in nodes:
            node.na_show_txt = True
        return {'FINISHED'}

class NODE_OT_show_select_img(Operator):
    bl_idname = "node.na_show_select_img"
    bl_label = "显示图片"
    bl_description = "显示选中节点的图片笔记"
    bl_options = {'UNDO'}

    def execute(self, context):
        nodes = context.selected_nodes if context.selected_nodes else [context.active_node]
        for node in nodes:
            node.na_show_img = True
        return {'FINISHED'}

class NODE_OT_show_select_seq(Operator):
    bl_idname = "node.na_show_select_seq"
    bl_label = "显示序号"
    bl_description = "显示选中节点的序号笔记"
    bl_options = {'UNDO'}

    def execute(self, context):
        nodes = context.selected_nodes if context.selected_nodes else [context.active_node]
        for node in nodes:
            node.na_show_seq = True
        return {'FINISHED'}

class NODE_OT_clear_all_scene_notes(Operator):
    bl_idname = "node.na_clear_all_scene_notes"
    bl_label = "删除所有笔记"
    bl_description = "删除节点树中所有笔记"
    bl_options = {'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    # todo: 是否递归节点组内
    def execute(self, context):
        edit_tree = context.space_data.edit_tree
        if not edit_tree: return {'CANCELLED'}
        for node in edit_tree.nodes:
            if not node.na_text and not node.na_image and not node.na_seq_index: continue
            node.na_text = ""
            node.na_image = None
            node.na_seq_index = 0
            node.na_is_initialized = False
        return {'FINISHED'}

class NODE_OT_fix_prop(Operator):
    bl_idname = "node.na_fix_prop"
    bl_label = "修复属性"

    def execute(self, context):
        init_props()
        return {'FINISHED'}

classes = [
    NODE_PT_annotator_gpu_panel,
    NODE_OT_clear_select_all,
    NODE_OT_clear_select_txt,
    NODE_OT_clear_select_img,
    NODE_OT_clear_select_seq,
    NODE_OT_fix_prop,
    NODE_OT_clear_all_scene_notes,
    NODE_OT_na_swap_order,
    NODE_OT_interactive_seq,
    NODE_OT_reset_prefs,
    NodeMemoAddonPreferences,
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
