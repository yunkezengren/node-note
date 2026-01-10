import bpy
from bpy.types import Operator, UILayout, Context, Node, NodeTree
from .preference import pref, text_split_lines


class NODE_OT_clear_search(Operator):
    """清除搜索内容"""
    bl_idname = "node.na_clear_search"
    bl_label = "清除搜索"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        pref().navigator_search = ""
        return {'FINISHED'}

class NODE_OT_jump_to_note(Operator):
    """跳转到指定注记节点"""
    bl_idname = "node.na_jump_to_note"
    bl_label = "跳转到注记"
    bl_description = "聚焦视图到该节点"
    
    node_name: bpy.props.StringProperty()

    def execute(self, context):
        tree = context.space_data.edit_tree
        if not tree: return {'CANCELLED'}
        
        target_node = tree.nodes.get(self.node_name)
        if target_node:
            for n in tree.nodes:
                n.select = False
            target_node.select = True
            tree.nodes.active = target_node
            bpy.ops.node.view_selected()
            return {'FINISHED'}
        
        self.report({'WARNING'}, f"节点 {self.node_name} 未找到")
        return {'CANCELLED'}

def draw_search_list(layout: UILayout, context: Context):
    tree: NodeTree = context.space_data.edit_tree
    
    row = layout.row(align=True)
    
    row.prop(pref(), "navigator_search", text="", icon='VIEWZOOM')
    search_key = pref().navigator_search.strip().lower()
    if search_key:
        row.operator("node.na_clear_search", text="", icon='X')

    annotated_nodes: list[Node] = []
    all_notes_count = 0
    
    for node in tree.nodes:
        has_text = hasattr(node, "na_text") and node.na_text.strip()
        has_seq = hasattr(node, "na_seq_index") and node.na_seq_index > 0
        
        if has_text or has_seq:
            all_notes_count += 1
            if search_key and has_text and (search_key not in node.na_text.lower()):
                continue
            annotated_nodes.append(node)
    
    # 排序逻辑
    if pref().sort_by_sequence:
        annotated_nodes.sort(key=lambda n: (
            0 if getattr(n, "na_seq_index", 0) > 0 else 1,
            getattr(n, "na_seq_index", 0),
            getattr(n, "location", (0,0))[0]
        ))
    else:
        annotated_nodes.sort(key=lambda n: (getattr(n, "location", (0,0))[0], -getattr(n, "location", (0,0))[1]))

    if not annotated_nodes and all_notes_count > 0:
        box = layout.box()
        col = box.column(align=True)
        col.label(text="未找到匹配项", icon='FILE_SCRIPT')
        col.operator("node.na_clear_search", text="清除过滤", icon='X')
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
        if hasattr(node, "na_txt_bg_color"):
            split.prop(node, "na_txt_bg_color", text="")
        else:
            split.label(text="", icon='QUESTION')
        
        display_text = ""
        seq_idx = getattr(node, "na_seq_index", 0)
        txt_content = getattr(node, "na_text", "").strip()
        
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
        
        op = split.operator("node.na_jump_to_note", text=display_text, icon='RIGHTARROW_THIN', emboss=True)
        op.node_name = node.name


def register():
    bpy.utils.register_class(NODE_OT_clear_search)
    bpy.utils.register_class(NODE_OT_jump_to_note)

def unregister():
    bpy.utils.unregister_class(NODE_OT_clear_search)
    bpy.utils.unregister_class(NODE_OT_jump_to_note)