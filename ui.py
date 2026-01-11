from bpy.types import Panel, UILayout, Context, Menu, Node, NodeTree
from .preferences import pref, text_split_lines

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
        draw_ui_layout(layout, context)

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
        row_pos.prop(prefs, "show_all_notes", text="显示", icon='HIDE_OFF', toggle=True)
        row_pos.operator("node.note_clear_all_scene_notes", text="全删", icon='TRASH')
        # 还很不完善
        # body.column().prop(prefs, "use_occlusion", text="被遮挡时自动隐藏")
        
        row_del = body.row(align=True)
        # 暂时禁用这个
        # row_del.operator("node.note_clear_select_all", text="删除选中笔记", icon='TRASH')

        if prefs.show_all_notes:
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
            body.row().operator("node.note_copy_to_selected", text="同步活动样式到选中", icon='DUPLICATE')

    node = context.active_node
    if not node:
        layout.label(text="需要活动节点", icon='INFO')
        return

    header, body = layout.panel("setting1", default_closed=False)
    header.label(text="", icon='FILE_TEXT')
    header.operator("node.note_show_select_txt", text="文字笔记", icon="HIDE_OFF" if node.note_show_txt else "HIDE_ON")
    if node.note_show_txt and node.note_text and node.note_show_img and node.note_image:
        header.operator("node.note_swap_order", text="⇅ 交换")
    header.operator("node.note_clear_select_txt", text="", icon='TRASH')
    if body:
        body.active = node.note_show_txt
        body_split = body.split(factor=0.01)
        body_split.label(text="")
        txt_box = body_split.box()
        col = txt_box.column(align=True)
        col.prop(node, "note_text", text="描述: ")

        row_pos = txt_box.column()
        row_tag = row_pos.row(align=True)
        row_tag.prop(pref(), "tag_mode_prepend", text="", icon='ALIGN_LEFT' if pref().tag_mode_prepend else 'ALIGN_RIGHT', toggle=True)
        for tag in ["★", "⚠", "?", "!"]:
            op = row_tag.operator("node.note_add_quick_tag", text=tag)
            op.tag_text = tag

        txt_box.separator(factor=0.05)
        split_txt = txt_box.split(factor=0.5)
        split_txt.prop(node, "note_font_size", text="字号")
        split_txt.prop(pref(), "line_separator", text="换行符")
        
        split_color = txt_box.split(factor=0.5)
        split_color.row().prop(node, "note_text_color", text="文本色")
        split_color.row().prop(node, "note_txt_bg_color", text="背景色")

        row_pos = txt_box.row()
        row_pos.label(text="背景:")
        def_labels = ["红", "绿", "蓝", "橙", "紫", "无"]
        for i in range(len(def_labels)):
            split_color = row_pos.split(factor=0.1, align=True)
            split_color.prop(pref(), f"col_preset_{i+1}", text="")
            op = split_color.operator("node.note_apply_preset", text=def_labels[i])
            op.bg_color = col_vals[i]

        width_row = txt_box.row(align=True)
        width_row.prop(node, "note_txt_width_mode", text="宽度")
        if node.note_txt_width_mode == 'MANUAL':
            width_row.prop(node, "note_txt_bg_width", text="宽度")

        row_pos = txt_box.row(align=True)
        row_pos.prop(node, "note_txt_pos", text="")
        row_pos.prop(node, "note_txt_offset", text="")
        row_pos.operator("node.note_reset_offset", text="", icon='LOOP_BACK')

    header, body = layout.panel("setting2", default_closed=True)
    header.label(text="", icon='IMAGE_DATA')
    header.operator("node.note_show_select_img", text="图片笔记", icon="HIDE_OFF" if node.note_show_img else "HIDE_ON")
    header.operator("node.note_clear_select_img", text="", icon='TRASH')
    if body:
        body.active = node.note_show_img
        body_split = body.split(factor=0.01)
        body_split.label(text="")
        img_box = body_split.box()
        split = img_box.split(factor=0.75)
        split.template_ID(node, "note_image", open="image.open")
        split.operator("node.note_paste_image", text="粘贴", icon='PASTEDOWN')

        width_row = img_box.row(align=True)
        width_row.prop(node, "note_img_width_mode", text="宽度")
        if node.note_img_width_mode == 'MANUAL':
            width_row.prop(node, "note_img_width", text="宽度")

        row_pos = img_box.row(align=True)
        row_pos.prop(node, "note_img_pos", text="")
        row_pos.prop(node, "note_img_offset", text="")
        row_pos.operator("node.note_reset_img_offset", text="", icon='LOOP_BACK')

    header, body = layout.panel("setting3", default_closed=True)
    header.label(text="", icon='EVENT_NDOF_BUTTON_1')
    header.operator("node.note_show_select_seq", text="序号笔记", icon="HIDE_OFF" if node.note_show_seq else "HIDE_ON")
    header.operator("node.note_clear_select_seq", text="", icon='TRASH')
    if body:
        body.active = node.note_show_seq
        body_split = body.split(factor=0.01)
        body_split.label(text="")
        seq_box = body_split.box()
        split = seq_box.split(factor=0.5)
        split.prop(node, "note_seq_index", text="序号")
        split = seq_box.split(factor=0.5)
        split.row().prop(prefs, "seq_font_color", text="文本色")
        split.row().prop(prefs, "seq_bg_color", text="背景色")

        row_set = seq_box.row()
        row_set.operator("node.note_interactive_seq", text="交互编号", icon='BRUSH_DATA', depress=prefs.is_interactive_mode)

        row_set = seq_box.row(align=True)
        row_set.prop(prefs, "seq_scale_mode", text="缩放模式")
        if prefs.seq_scale_mode == 'ABSOLUTE':
            row_set.prop(prefs, "seq_abs_scale", text="屏幕缩放")
        else:
            row_set.prop(prefs, "seq_scale", text="相对缩放")
        
        row_set = seq_box.split(factor=0.3)
        row_set.prop(prefs, "show_sequence_lines", text="显示连线", icon='EMPTY_ARROWS')
        row_set.row().prop(prefs, "seq_line_color", text="颜色")
        row_set.prop(prefs, "seq_line_thickness", text="线宽")

    header, body = layout.panel("setting4", default_closed=True)
    header.label(text="文本导航列表")
    header.prop(prefs, "sort_by_sequence", text="按序号排列")
    if body:
        draw_search_list(body, context)

def draw_search_list(layout: UILayout, context: Context):
    row = layout.row(align=True)
    row.prop(pref(), "navigator_search", text="", icon='VIEWZOOM')
    search_key = pref().navigator_search.strip().lower()
    if search_key:
        row.operator("node.note_clear_search", text="", icon='X')

    annotated_nodes: list[Node] = []
    all_notes_count = 0
    
    tree: NodeTree = context.space_data.edit_tree
    for node in tree.nodes:
        has_text = hasattr(node, "note_text") and node.note_text.strip()
        has_seq = hasattr(node, "note_seq_index") and node.note_seq_index > 0
        
        if has_text or has_seq:
            all_notes_count += 1
            if search_key and has_text and (search_key not in node.note_text.lower()):
                continue
            annotated_nodes.append(node)
    
    # 排序逻辑
    if pref().sort_by_sequence:
        annotated_nodes.sort(key=lambda n: (
            0 if getattr(n, "note_seq_index", 0) > 0 else 1,
            getattr(n, "note_seq_index", 0),
            getattr(n, "location", (0,0))[0]
        ))
    else:
        annotated_nodes.sort(key=lambda n: (getattr(n, "location", (0,0))[0], -getattr(n, "location", (0,0))[1]))

    if not annotated_nodes and all_notes_count > 0:
        box = layout.box()
        col = box.column(align=True)
        col.label(text="未找到匹配项", icon='FILE_SCRIPT')
        col.operator("node.note_clear_search", text="清除过滤", icon='X')
        return

    if all_notes_count == 0:
        layout.label(text="暂无注记", icon='INFO')
        return
    
    sort_icon = 'SORT_ASC' if pref().sort_by_sequence else 'GRID'
    if search_key: sort_icon = 'FILTER'
    
    layout.label(text=f"列表 ({len(annotated_nodes)}):", icon=sort_icon)
    
    col = layout.column(align=True)
    for node in annotated_nodes:
        row = col.row(align=True)
        
        split = row.split(factor=0.2, align=True)
        if hasattr(node, "note_txt_bg_color"):
            split.prop(node, "note_txt_bg_color", text="")
        else:
            split.label(text="", icon='QUESTION')
        
        display_text = ""
        seq_idx = getattr(node, "note_seq_index", 0)
        txt_content = getattr(node, "note_text", "").strip()
        
        if seq_idx > 0:
            display_text += f"[{seq_idx}] "
        
        if txt_content:
            # todo 提示里完整显示
            txt_pure = text_split_lines(txt_content)[0]
            display_text += txt_pure
        else:
            display_text += node.name 
        
        if len(display_text) > 60:
            display_text = display_text[:60] + "..."
        
        op = split.operator("node.note_jump_to_note", text=display_text, icon='RIGHTARROW_THIN', emboss=True)
        op.node_name = node.name

def draw_menu_func(self: Menu, context: Context):
    layout = self.layout
    layout.separator()
    layout.operator_context = 'INVOKE_DEFAULT'
    layout.operator("node.note_quick_edit", icon='TEXT')