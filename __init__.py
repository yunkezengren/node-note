import bpy
from bpy.types import Operator

# 导入新模块
from . import draw_gpu
from . import operators
from . import ui
from .node_properties import init_props, clear_props
from .preferences import NodeMemoAddonPreferences

addon_keymaps = []

classes = [
    ui.NODE_PT_annotator_gpu_panel,
    NodeMemoAddonPreferences,
]

def register():
    # 初始化节点属性
    init_props()
    
    # 注册UI面板和偏好设置
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # 注册操作符
    operators.register()
    
    # 注册绘制处理器
    draw_gpu.register_draw_handler()
    
    # 注册快捷键
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='Node Editor', space_type='NODE_EDITOR')
        kmi = km.keymap_items.new("node.note_quick_edit", 'RIGHTMOUSE', 'PRESS', shift=True)
        addon_keymaps.append((km, kmi))
    
    # 注册右键菜单
    bpy.types.NODE_MT_context_menu.prepend(ui.draw_menu_func)

def unregister():
    # 移除右键菜单
    bpy.types.NODE_MT_context_menu.remove(ui.draw_menu_func)
    
    # 移除快捷键
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        for km, kmi in addon_keymaps:
            km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    
    # 注销绘制处理器
    draw_gpu.unregister_draw_handler()
    
    # 注销操作符
    operators.unregister()
    
    # 注销UI面板和偏好设置
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    # 清理节点属性
    clear_props()

if __name__ == "__main__": register()