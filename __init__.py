import bpy
# 导入新模块
from . import draw_gpu
from . import operators
from . import ui
from . import node_properties
from .preferences import NodeNoteAddonPreferences

addon_keymaps = []

classes = [
    ui.NODE_PT_node_note_gpu_panel,
    NodeNoteAddonPreferences,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    operators.register()
    draw_gpu.register_draw_handler()
    node_properties.init_props()
    
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='Node Editor', space_type='NODE_EDITOR')
        kmi = km.keymap_items.new("node.note_quick_edit", 'D', 'CLICK', ctrl=True)
        addon_keymaps.append((km, kmi))
    
    bpy.types.NODE_MT_context_menu.prepend(ui.draw_menu_func)

def unregister():
    bpy.types.NODE_MT_context_menu.remove(ui.draw_menu_func)

    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        for km, kmi in addon_keymaps:
            km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    draw_gpu.unregister_draw_handler()
    operators.unregister()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    node_properties.delete_props()

