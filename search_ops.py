import bpy

class NODE_OT_clear_search(bpy.types.Operator):
    """清除搜索内容"""
    bl_idname = "node.na_clear_search"
    bl_label = "清除搜索"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        if hasattr(context.scene, "na_navigator_search"):
            context.scene.na_navigator_search = ""
        return {'FINISHED'}

class NODE_OT_jump_to_note(bpy.types.Operator):
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

class NODE_PT_note_navigator(bpy.types.Panel):
    """注记导航面板"""
    # [核心修改 1] 将系统自带标题置空，以便我们手动接管布局
    bl_label = "" 
    bl_idname = "NODE_PT_na_navigator"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    # [修改点] 侧边栏标签统一为“节点随记”
    bl_category = "节点随记"
    bl_options = {'DEFAULT_CLOSED'} 

    @classmethod
    def poll(cls, context):
        return context.space_data.type == 'NODE_EDITOR' and context.space_data.edit_tree

    # [核心修改 2] 手动绘制完整的 Header 布局
    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        # 左侧：手动绘制标题
        row.label(text="文本导航列表")
        # 右侧：绘制复选框
        row.prop(context.scene, "na_sort_by_sequence", text="按序号排列")

    def draw(self, context):
        layout = self.layout
        
        try:
            tree = context.space_data.edit_tree
            
            row = layout.row(align=True)
            
            if hasattr(context.scene, "na_navigator_search"):
                row.prop(context.scene, "na_navigator_search", text="", icon='VIEWZOOM')
                search_key = context.scene.na_navigator_search.strip().lower()
                if search_key:
                    row.operator("node.na_clear_search", text="", icon='X')
            else:
                row.label(text="请重启 Blender 以加载搜索功能", icon='ERROR')
                search_key = ""

            annotated_nodes = []
            all_notes_count = 0
            
            for node in tree.nodes:
                has_text = hasattr(node, "na_text") and node.na_text.strip()
                has_seq = hasattr(node, "na_sequence_index") and node.na_sequence_index > 0
                
                if has_text or has_seq:
                    all_notes_count += 1
                    if search_key and has_text and (search_key not in node.na_text.lower()):
                        continue
                    annotated_nodes.append(node)
            
            # 排序逻辑
            if getattr(context.scene, "na_sort_by_sequence", False):
                annotated_nodes.sort(key=lambda n: (
                    0 if getattr(n, "na_sequence_index", 0) > 0 else 1,
                    getattr(n, "na_sequence_index", 0),
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
            
            sort_icon = 'SORT_ASC' if getattr(context.scene, "na_sort_by_sequence", False) else 'GRID'
            if search_key: sort_icon = 'FILTER'
            
            layout.label(text=f"列表 ({len(annotated_nodes)}):", icon=sort_icon)
            
            col = layout.column(align=True)
            for node in annotated_nodes:
                row = col.row(align=True)
                
                split = row.split(factor=0.2, align=True)
                if hasattr(node, "na_bg_color"):
                    split.prop(node, "na_bg_color", text="")
                else:
                    split.label(text="", icon='QUESTION')
                
                display_text = ""
                seq_idx = getattr(node, "na_sequence_index", 0)
                txt_content = getattr(node, "na_text", "").strip()
                
                if seq_idx > 0:
                    display_text += f"[{seq_idx}] "
                
                if txt_content:
                    txt_pure = txt_content.split('\n')[0].split(';')[0]
                    display_text += txt_pure
                else:
                    display_text += node.name 
                
                if len(display_text) > 60:
                    display_text = display_text[:60] + "..."
                
                op = split.operator("node.na_jump_to_note", text=display_text, icon='RIGHTARROW_THIN', emboss=True)
                op.node_name = node.name

        except Exception as e:
            layout.alert = True
            layout.label(text=f"UI Error: {str(e)}", icon='ERROR')
            import traceback
            traceback.print_exc()

def register():
    bpy.utils.register_class(NODE_OT_clear_search)
    bpy.utils.register_class(NODE_OT_jump_to_note)
    bpy.utils.register_class(NODE_PT_note_navigator)

def unregister():
    bpy.utils.unregister_class(NODE_PT_note_navigator)
    bpy.utils.unregister_class(NODE_OT_jump_to_note)
    bpy.utils.unregister_class(NODE_OT_clear_search)