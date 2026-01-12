import math
import os
import subprocess
import tempfile
import time
from .preferences import pref
import bpy
from bpy.types import Context, Scene, Node

# ==================== 类型别名 ====================
float2 = tuple[float, float]
int2 = tuple[int, int]
int3 = tuple[int, int, int]
RGBA = tuple[float, float, float, float]
Rect = tuple[float, float, float, float]

# ==================== 工具函数 ====================

def ui_scale():
    return bpy.context.preferences.system.ui_scale

def nd_abs_loc(node: Node):
    if hasattr(node, "location_absolute"):
        return node.location_absolute
    return node.location + nd_abs_loc(node.parent) if node.parent else node.location

def get_region_zoom(context: Context) -> float:
    """获取节点编辑器的缩放比例"""
    view2d = context.region.view2d
    x0, y0 = view2d.view_to_region(0, 0, clip=False)
    x1, y1 = view2d.view_to_region(1000, 1000, clip=False)
    return 1.0 if x1 == x0 else math.sqrt((x1 - x0)**2 + (y1 - y0)**2) / 1000

def view_to_region_scaled(x: float, y: float) -> int2:
    """将节点编辑器坐标转换为屏幕坐标（考虑UI缩放）"""
    return bpy.context.region.view2d.view_to_region(x * ui_scale(), y * ui_scale(), clip=False)

# todo 需要改进
def check_color_visibility(color: RGBA) -> bool:
    """检查背景颜色是否可见（用于过滤显示）"""
    prefs = pref()
    r, g, b, a = color
    if a < 0.05: 
        return False  # 完全透明
    if r > 0.5 and g < 0.2 and b < 0.2:  # 红色系
        return prefs.filter_red
    if g > 0.4 and r < 0.3 and b < 0.3:  # 绿色系
        return prefs.filter_green
    if b > 0.4 and r < 0.3 and g < 0.3:  # 蓝色系
        return prefs.filter_blue
    if r > 0.5 and g > 0.2 and b < 0.2:  # 橙色系
        return prefs.filter_orange
    if r > 0.3 and g < 0.2 and b > 0.4:  # 紫色系
        return prefs.filter_purple

    return prefs.filter_other

def get_node_screen_rect(node: Node) -> Rect:
    """获取节点在屏幕空间中的矩形区域"""
    loc_x, loc_y = nd_abs_loc(node)
    width, height = node.width, node.dimensions.y
    min_x, min_y = view_to_region_scaled(loc_x, loc_y)
    max_x, max_y = view_to_region_scaled(loc_x + width, loc_y - height)
    return min_x, min_y, max_x, max_y

def is_rect_overlap(r1: Rect, r2: Rect) -> bool:
    """检查两个矩形是否重叠"""
    return not (r1[2] < r2[0] or r1[0] > r2[2] or r1[3] < r2[1] or r1[1] > r2[3])

def paste_image_from_clipboard():
    """从剪贴板粘贴图像的工具函数"""
    tmp = tempfile.gettempdir()
    path = os.path.join(tmp, f"blender_paste_{int(time.time()*1000)}.png")
    import sys
    if sys.platform == "win32":
        cmd = [
            "powershell", "-WindowStyle", "Hidden", "-command",
            f"Add-Type -AssemblyName System.Windows.Forms;$i=[System.Windows.Forms.Clipboard]::GetImage();if($i){{$i.Save('{path}',[System.Drawing.Imaging.ImageFormat]::Png);exit 0}}exit 1"
        ]
        subprocess.run(cmd)
    elif sys.platform == "darwin":
        subprocess.run(["pngpaste", path])
    elif sys.platform.startswith("linux"):
        with open(path, "wb") as f:
            subprocess.run(["xclip", "-selection", "clipboard", "-t", "image/png", "-o"], stdout=f)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
