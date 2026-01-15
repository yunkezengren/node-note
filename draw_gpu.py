from dataclasses import dataclass
import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader
from bpy.types import Image, NodeTree, SpaceNodeEditor
from gpu.types import GPUShader, GPUTexture
from mathutils import Vector as Vec2
import math
import numpy as np
import os
from .typings import NotedNode, float2, int3, RGBA, AlignMode, TextWidthMode, BadgeScaleMode
from .preferences import pref
from .utils import (
    ui_scale,
    nd_abs_loc,
    get_region_zoom,
    text_split_lines,
    view_to_region_scaled,
    check_color_visibility,
    get_node_screen_rect,
)

# region 常量

PaddingX = 2
MinAutoWidth = 101
CornerRadius = 2.0
CornerScaleY = 1.1
DefaultBg = (0.2, 0.3, 0.5, 0.9)

handler = None
_shader_cache: dict[str, GPUShader] = {}
_manual_texture_cache: dict[str, GPUTexture] = {}
_font_id: int = 0
_font_path: str = ""

def get_font_id() -> int:
    """获取全局字体 ID"""
    global _font_id, _font_path
    font_path = pref().font_path
    if font_path != _font_path:
        _font_path = font_path
        if font_path and os.path.exists(font_path):
            _font_id = blf.load(font_path) or 0
        else:
            _font_id = 0
    return _font_id

# region 数据类

@dataclass
class DrawParams:
    """绘制参数"""
    scale: float
    occluders: list
    badge_radius: float
    arrow_size: float
    badge_font_size: float

@dataclass
class NodeInfo:
    """屏幕空间节点位置信息"""
    node: NotedNode
    top_y: float
    bottom_y: float
    left_x: float
    right_x: float
    loc: Vec2

@dataclass
class BadgeInfo:
    """序号徽章坐标"""
    pos: float2
    note_badge_color: RGBA

@dataclass
class TextDimensions:
    """文本尺寸和换行结果"""
    width: float
    height: float
    lines: list[str]
    font_size: int
    should_draw: bool

@dataclass
class ImageDimensions:
    """图像尺寸和纹理"""
    width: float
    height: float
    texture: GPUTexture | None
    should_draw: bool

@dataclass
class ElementPosition:
    """文本和图像的屏幕坐标"""
    txt_x: float
    txt_y: float
    img_x: float
    img_y: float

# region 基础工具函数

def get_shader(name: str) -> GPUShader | None:
    if name not in _shader_cache:
        try:
            _shader_cache[name] = gpu.shader.from_builtin(name)
        except Exception as e:
            if name == '2D_IMAGE':
                try:
                    _shader_cache[name] = gpu.shader.from_builtin('IMAGE')
                except:
                    pass
            return None
    return _shader_cache.get(name)

def get_image_shader() -> GPUShader:
    shader_name = "NODENOTE_IMAGE_SHADER"
    if shader_name in _shader_cache:
        return _shader_cache[shader_name]

    # 参考: references_overlays\references_overlays.py
    vert_out = gpu.types.GPUStageInterfaceInfo("node_note_interface") # type: ignore
    vert_out.smooth('VEC2', "uv")

    shader_info = gpu.types.GPUShaderCreateInfo()
    shader_info.sampler(0, 'FLOAT_2D', "image")
    shader_info.vertex_in(0, 'VEC2', "pos")
    shader_info.vertex_in(1, 'VEC2', "texCoord")
    shader_info.vertex_out(vert_out)

    shader_info.push_constant('MAT4', "ModelViewProjectionMatrix")
    shader_info.fragment_out(0, 'VEC4', "fragColor")

    shader_info.vertex_source(
        "void main()"
        "{"
        "   uv = texCoord;"
        "   gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);"
        "}"
    )

    shader_info.fragment_source(
        "void main()"
        "{"
        "  vec4 color = texture(image, uv);"
        "  fragColor = vec4(color.rgb, color.a);"
        "}"
    )

    shader = gpu.shader.create_from_info(shader_info)
    _shader_cache[shader_name] = shader
    return shader

def get_gpu_texture(image: Image) -> GPUTexture | None:
    if not image: return None
    if image.size[0] == 0 or image.size[1] == 0: return None
    try:
        if hasattr(image, "gpu_texture") and image.gpu_texture: return image.gpu_texture
    except:
        pass
    try:
        texture = gpu.texture.from_image(image)
        if texture: return texture
    except:
        pass
    return create_texture_from_pixels(image)

def create_texture_from_pixels(image: Image) -> GPUTexture | None:
    global _manual_texture_cache
    cache_key = image.name
    if cache_key in _manual_texture_cache:
        return _manual_texture_cache[cache_key]
    try:
        width, height = image.size
        pixel_data = np.zeros(width * height * 4, dtype=np.float32)
        image.pixels.foreach_get(pixel_data)
        # texture = GPUTexture((width, height), format='SRGB8_A8', data=pixel_data)  # type: ignore
        texture = GPUTexture((width, height), format='RGBA32F', data=pixel_data)  # type: ignore
        _manual_texture_cache[cache_key] = texture
        return texture
    except:
        return None

def _wrap_text_pure(font_id: int, text: str, max_width: float):
    lines: list[str] = []
    for para in text_split_lines(text):
        curr_line, curr_w = "", 0
        if not para:
            lines.append("")
            continue
        for char in para:
            char_width = blf.dimensions(font_id, char)[0]
            if curr_w + char_width > max_width and curr_line:
                lines.append(curr_line)
                curr_line = char
                curr_w = char_width
            else:
                curr_line += char
                curr_w += char_width
        if curr_line: lines.append(curr_line)
    return lines

def _get_draw_params() -> DrawParams:
    """获取绘制参数"""
    context = bpy.context
    prefs = pref()
    # 缩放计算
    zoom = get_region_zoom(context)
    prefs_ui_scale = context.preferences.view.ui_scale
    scale = zoom * prefs_ui_scale
    # scale = ui_scale()
    # 遮挡检测
    occluders = []
    if prefs.use_occlusion and context.selected_nodes:
        occluders = [get_node_screen_rect(n) for n in context.selected_nodes]
    # 序号样式参数
    badge_rel_scale = prefs.badge_rel_scale
    badge_abs_scale = prefs.badge_abs_scale
    badge_scale_mode: BadgeScaleMode = prefs.badge_scale_mode
    if badge_scale_mode == 'RELATIVE':
        badge_radius = 7 * badge_rel_scale * scale
        arrow_size = 8.0 * badge_rel_scale * scale
        badge_font_size = 8 * badge_rel_scale * scale
    elif badge_scale_mode == 'ABSOLUTE':
        max_diameter = view_to_region_scaled(140, 0)[0] - view_to_region_scaled(0, 0)[0]
        badge_radius = min(7 * 2, max_diameter / 2) * badge_abs_scale
        arrow_size = min(16, max_diameter * 0.6) * badge_abs_scale
        badge_font_size = min(16, max_diameter / 2) * badge_abs_scale
    return DrawParams(
        scale,
        occluders,
        badge_radius,
        arrow_size,
        badge_font_size,
    )

def _wrap_text(font_id: int, text: str, txt_width_mode: TextWidthMode, note_width: float, pad: float) -> list[str]:
    """文本换行处理"""
    if txt_width_mode == 'FIT':
        return text_split_lines(text)
    else:
        return _wrap_text_pure(font_id, text, max(1, note_width - pad*2))

def _get_node_info(node: NotedNode) -> NodeInfo:
    """计算节点位置信息"""
    loc = nd_abs_loc(node)
    h_logical = node.dimensions.y / ui_scale()
    logical_top_y = max(loc.y - (h_logical/2 + 9), loc.y + (h_logical/2 - 9)) if node.hide else loc.y
    logical_bottom_y = min(loc.y - (h_logical/2 + 9), loc.y + (h_logical/2 - 9)) if node.hide else (loc.y - h_logical)

    left_x, top_y = view_to_region_scaled(loc.x, logical_top_y)
    _, bottom_y = view_to_region_scaled(loc.x, logical_bottom_y)
    right_x, _ = view_to_region_scaled(loc.x + node.width + 1.0, loc.y)

    return NodeInfo(
        node,
        top_y,
        bottom_y,
        left_x,
        right_x,
        loc,
    )

def _calc_note_pos(node_info: NodeInfo, alignment: AlignMode, offset_vec: float2, self_width: float, self_height: float,
                   scale: float) -> float2:
    """计算元素位置"""
    base_x = node_info.left_x
    base_y = node_info.top_y
    bottom_y = node_info.bottom_y
    right_x = node_info.right_x

    offset_x = offset_vec[0] * scale
    offset_y = offset_vec[1] * scale
    margin = 2

    if alignment == 'TOP':
        pos_x = base_x
        pos_y = base_y + margin*scale
    elif alignment == 'BOTTOM':
        pos_x = base_x
        pos_y = bottom_y - margin*scale - self_height
    elif alignment == 'LEFT':
        pos_x = base_x - margin*scale - self_width
        pos_y = base_y - self_height
    elif alignment == 'RIGHT':
        pos_x = right_x + margin*scale
        pos_y = base_y - self_height

    return pos_x + offset_x, pos_y + offset_y

# region 尺寸和位置计算函数

def _calc_text_dimensions(node_info: NodeInfo, scale: float, is_visible: bool) -> TextDimensions:
    """计算文本注释的尺寸和换行"""
    node = node_info.node
    text = node.note_text
    show_txt = node.note_show_txt

    if not (text and show_txt and is_visible):
        return TextDimensions(width=0, height=0, lines=[], font_size=0, should_draw=False)

    pad = PaddingX * scale
    node_width_px = node_info.right_x - node_info.left_x
    loc = node_info.loc

    fs = max(1, int(node.note_font_size * scale))
    txt_width_mode = node.note_txt_width_mode

    # 计算宽度
    if txt_width_mode == 'FIT' and text:
        font_id = get_font_id()
        blf.size(font_id, fs)
        max_line_w = max(blf.dimensions(font_id, line)[0] for line in text_split_lines(text))
        note_width = max_line_w + (pad * 2)
    elif txt_width_mode == 'AUTO':
        min_w = view_to_region_scaled(loc[0] + MinAutoWidth, loc[1])[0] - node_info.left_x
        note_width = max(node_width_px, min_w)
    else:
        note_width = view_to_region_scaled(loc[0] + node.note_txt_bg_width, loc[1])[0] - node_info.left_x

    # 文本换行
    font_id = get_font_id()
    blf.size(font_id, fs)
    lines = text_split_lines(text) if txt_width_mode == 'FIT' else _wrap_text(font_id, text, txt_width_mode, note_width, pad)
    text_note_height = (len(lines) * fs * 1.3) + pad * 2 if lines else 0

    return TextDimensions(width=note_width, height=text_note_height, lines=lines, font_size=fs, should_draw=True)

def _calc_image_dimensions(node_info: NodeInfo, scale: float) -> ImageDimensions:
    """计算图像注释的尺寸和纹理"""
    node = node_info.node
    img = node.note_image
    show_img = node.note_show_img

    if not (img and show_img):
        return ImageDimensions(width=0, height=0, texture=None, should_draw=False)

    node_width_px = node_info.right_x - node_info.left_x
    loc = node_info.loc
    ref_width = max(node_width_px, (view_to_region_scaled(loc[0] + MinAutoWidth, loc[1])[0] - node_info.left_x))

    # 计算宽度
    img_width_mode = node.note_img_width_mode
    if img_width_mode == 'ORIGINAL':
        base_width = img.size[0] * scale
    elif img_width_mode == 'AUTO':
        base_width = ref_width
    else:
        base_width = view_to_region_scaled(loc[0] + node.note_img_width, loc[1])[0] - node_info.left_x

    img_draw_h = base_width * (img.size[1] / img.size[0]) if img.size[0] > 0 else 0
    texture = get_gpu_texture(img) if img.size[0] > 0 else None

    return ImageDimensions(width=base_width, height=img_draw_h, texture=texture, should_draw=True)

def _calc_non_stacked_positions(node_info: NodeInfo, scale: float, text_dims: TextDimensions, image_dims: ImageDimensions) -> ElementPosition:
    """计算非堆叠情况下的元素位置"""
    txt_x = txt_y = img_x = img_y = 0.0

    node = node_info.node
    if text_dims.should_draw:
        txt_x, txt_y = _calc_note_pos(node_info, node.note_txt_pos, node.note_txt_offset,
                                      text_dims.width, text_dims.height, scale)
    if image_dims.should_draw:
        img_x, img_y = _calc_note_pos(node_info, node.note_img_pos, node.note_img_offset,
                                      image_dims.width, image_dims.height, scale)

    return ElementPosition(txt_x=txt_x, txt_y=txt_y, img_x=img_x, img_y=img_y)

def _calc_stacked_positions(node_info: NodeInfo, scale: float, text_dims: TextDimensions,
                                image_dims: ImageDimensions, alignment: AlignMode) -> ElementPosition:
    """计算堆叠情况下的元素位置"""
    node = node_info.node
    swap = node_info.node.note_swap_order

    # 确定内外层
    if not swap:
        inner_w, inner_h, inner_off = text_dims.width, text_dims.height, node.note_txt_offset
        outer_w, outer_h, outer_off = image_dims.width, image_dims.height, node.note_img_offset
    else:
        inner_w, inner_h, inner_off = image_dims.width, image_dims.height, node.note_img_offset
        outer_w, outer_h, outer_off = text_dims.width, text_dims.height, node.note_txt_offset

    inner_x, inner_y = _calc_note_pos(node_info, alignment, inner_off, inner_w, inner_h, scale)
    offset_x_scaled, offset_y_scaled = outer_off[0] * scale, outer_off[1] * scale

    # 计算外层位置
    if alignment == 'TOP':
        outer_x, outer_y = inner_x + offset_x_scaled, inner_y + inner_h + offset_y_scaled
    elif alignment == 'BOTTOM':
        outer_x, outer_y = inner_x + offset_x_scaled, inner_y - outer_h + offset_y_scaled
    elif alignment == 'LEFT':
        outer_x, outer_y = inner_x - outer_w + offset_x_scaled, node_info.top_y - outer_h + offset_y_scaled
    else:  # RIGHT
        outer_x, outer_y = inner_x + inner_w + offset_x_scaled, node_info.top_y - outer_h + offset_y_scaled

    txt_x, txt_y = (inner_x, inner_y) if not swap else (outer_x, outer_y)
    img_x, img_y = (outer_x, outer_y) if not swap else (inner_x, inner_y)

    return ElementPosition(txt_x=txt_x, txt_y=txt_y, img_x=img_x, img_y=img_y)

def _apply_centering_offset(element_pos: ElementPosition, node_info: NodeInfo, text_dims: TextDimensions, image_dims: ImageDimensions):
    """应用居中偏移(仅对TOP/BOTTOM对齐有效)"""
    node = node_info.node
    node_width = node_info.right_x - node_info.left_x
    if text_dims.should_draw and node.note_txt_center and node.note_txt_pos in {'TOP', 'BOTTOM'}:
        element_pos.txt_x += (node_width - text_dims.width) / 2
    if image_dims.should_draw and node.note_img_center and node.note_img_pos in {'TOP', 'BOTTOM'}:
        element_pos.img_x += (node_width - image_dims.width) / 2
# region 基础绘制函数

def draw_rounded_rect_batch(x: float, y: float, width: float, height: float, color: RGBA, radius: float = 3.0) -> None:
    shader = get_shader('UNIFORM_COLOR')
    if not shader: return
    base_radius = min(radius, width / 2, height / 2)
    radius_x = base_radius
    radius_y = base_radius * CornerScaleY
    radius_y = min(radius_y, height / 2)
    vertices: list[float2] = []
    indices: list[int3] = []
    vertex_index = 0

    def add_quad(x1: float, y1: float, x2: float, y2: float):
        nonlocal vertex_index
        vertices.extend([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])
        indices.extend([(vertex_index, vertex_index + 1, vertex_index + 2), (vertex_index, vertex_index + 2, vertex_index + 3)])
        vertex_index += 4

    if base_radius < 0.5:
        add_quad(x, y, x + width, y + height)
    else:
        add_quad(x, y + radius_y, x + width, y + height - radius_y)
        add_quad(x + radius_x, y, x + width - radius_x, y + radius_y)
        add_quad(x + radius_x, y + height - radius_y, x + width - radius_x, y + height)
        corners = [(x + width - radius_x, y + height - radius_y, 0.0, math.pi / 2),
                   (x + radius_x, y + height - radius_y, math.pi / 2, math.pi),
                   (x + radius_x, y + radius_y, math.pi, 3 * math.pi / 2),
                   (x + width - radius_x, y + radius_y, 3 * math.pi / 2, 2 * math.pi)]
        for corner_x, corner_y, start_angle, end_angle in corners:
            center_idx = vertex_index
            vertices.append((corner_x, corner_y))
            vertex_index += 1
            theta_step = (end_angle-start_angle) / 12
            for k in range(13):
                point_x = corner_x + math.cos(start_angle + k*theta_step) * radius_x
                point_y = corner_y + math.sin(start_angle + k*theta_step) * radius_y
                vertices.append((point_x, point_y))
                vertex_index += 1
            for k in range(12):
                indices.append((center_idx, center_idx + 1 + k, center_idx + 2 + k))
    batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
    shader.bind()
    shader.uniform_float("color", color)
    gpu.state.blend_set('ALPHA')
    batch.draw(shader)

def draw_circle_batch(pos: float2, radius: float, color: RGBA) -> None:
    """ Screen Space """
    shader = get_shader('UNIFORM_COLOR')
    if not shader: return
    vertices: list[float2] = [pos]
    indices: list[int3] = []
    step = (2 * math.pi) / 32
    for i in range(33):
        # 点 33 与点 1 重合（都是 0° 和 360°），确保圆闭合
        point_x = pos[0] + math.cos(i * step) * radius
        point_y = pos[1] + math.sin(i * step) * radius
        vertices.append((point_x, point_y))
    for i in range(32):
        indices.append((0, i + 1, i + 2))   # vertices 索引
    batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
    shader.bind()
    shader.uniform_float("color", color)
    gpu.state.blend_set('ALPHA')
    batch.draw(shader)

def draw_lines_batch(points: list[float2], thickness: int) -> None:
    if len(points) < 2: return
    shader = get_shader('UNIFORM_COLOR')
    if not shader: return
    gpu.state.line_width_set(thickness)
    batch = batch_for_shader(shader, 'LINES', {"pos": points})
    shader.bind()
    shader.uniform_float("color", pref().badge_line_color)
    gpu.state.blend_set('ALPHA')
    batch.draw(shader)

def draw_arrow_head(start_point: float2, end_point: float2, size: float, retreat: float) -> None:
    shader = get_shader('UNIFORM_COLOR')
    if not shader: return
    x1, y1 = start_point
    x2, y2 = end_point
    dx = x2 - x1
    dy = y2 - y1
    length = math.sqrt(dx*dx + dy*dy)
    if length < 0.001: return
    dir_x = dx / length
    dir_y = dy / length
    tip_x = x2 - dir_x*retreat
    tip_y = y2 - dir_y*retreat
    base_x = tip_x - dir_x*size
    base_y = tip_y - dir_y*size
    normal_x = -dir_y
    normal_y = dir_x
    half_width = size * 0.5
    v1 = (tip_x, tip_y)
    v2 = (base_x + normal_x*half_width, base_y + normal_y*half_width)
    v3 = (base_x - normal_x*half_width, base_y - normal_y*half_width)
    vertices = [v1, v2, v3]
    batch = batch_for_shader(shader, 'TRIS', {"pos": vertices})
    shader.bind()
    shader.uniform_float("color", pref().badge_line_color)
    gpu.state.blend_set('ALPHA')
    batch.draw(shader)

def draw_texture_batch(texture: GPUTexture | None, x: float, y: float, width: float, height: float) -> None:
    if not texture: return

    shader = get_image_shader()
    vertices = ((x, y), (x + width, y), (x + width, y + height), (x, y + height))
    uvs = ((0, 0), (1, 0), (1, 1), (0, 1))
    indices = ((0, 1, 2), (2, 3, 0))
    batch = batch_for_shader(shader, 'TRIS', {"pos": vertices, "texCoord": uvs}, indices=indices)
    shader.bind()
    shader.uniform_sampler("image", texture)
    gpu.state.blend_set('ALPHA')
    batch.draw(shader)
    gpu.state.blend_set('NONE')

def draw_image_error_placeholder(x: float, y: float, width: float, height: float) -> None:
    draw_rounded_rect_batch(x, y, max(width, 70), max(height, 70), (1, 0, 0, 1))

# region 核心绘制函数

def _draw_text_note(node_info: NodeInfo, scale:float, bg_color: RGBA, txt_x: float, txt_y: float, text_dims: TextDimensions) -> None:
    """绘制文本+背景"""
    pad = PaddingX * scale
    font_id = get_font_id()

    # 绘制背景
    draw_rounded_rect_batch(txt_x, txt_y, text_dims.width, text_dims.height, bg_color, CornerRadius * scale)

    # 绘制文本
    blf.color(font_id, *node_info.node.note_text_color)
    blf.disable(font_id, blf.SHADOW)
    blf.size(font_id, text_dims.font_size)
    line_y = txt_y + pad
    line_height = text_dims.font_size * 1.3
    for i, line in enumerate(reversed(text_dims.lines)):
        blf.position(font_id, int(txt_x + pad), int(line_y + i*line_height + text_dims.font_size*0.25), 0)
        blf.draw(font_id, line)

def _draw_image_note(texture: GPUTexture | None, img_x: float, img_y: float, img_draw_w: float, img_draw_h: float) -> None:
    if texture:
        draw_texture_batch(texture, img_x, img_y, img_draw_w, img_draw_h)
    else:
        draw_image_error_placeholder(img_x, img_y, img_draw_w, img_draw_h)

def _collect_badge_coords(node_info: NodeInfo, badge_infos: dict[int, list[BadgeInfo]]) -> None:
    """收集序号坐标"""
    badge_pos = (node_info.left_x, node_info.top_y)
    badge_idx = node_info.node.note_badge_index
    if badge_idx not in badge_infos:
        badge_infos[badge_idx] = []
    badge_infos[badge_idx].append(BadgeInfo(badge_pos, node_info.node.note_badge_color))

def _draw_badge_notes(badge_infos: dict[int, list[BadgeInfo]], params: DrawParams) -> None:
    def _draw_badge_lines(badge_infos: dict[int, list[BadgeInfo]], params: DrawParams) -> None:
        """绘制序号连线"""
        if not pref().show_badge_lines or len(badge_infos) < 2: return
        line_points: list[float2] = []
        indices = sorted(badge_infos.keys())

        for i in range(len(indices) - 1):
            for badge1 in badge_infos[indices[i]]:
                for badge2 in badge_infos[indices[i+1]]:
                    line_points.append(badge1.pos)
                    line_points.append(badge2.pos)
                    draw_arrow_head(badge1.pos, badge2.pos, params.arrow_size, params.badge_radius)

        draw_lines_batch(line_points, pref().badge_line_thickness)

    def _draw_badge_badges(badge_infos: dict[int, list[BadgeInfo]], params: DrawParams) -> None:
        """绘制序号徽章(背景+文本)"""
        font_id = 0
        blf.size(font_id, params.badge_font_size)
        blf.color(font_id, *pref().badge_font_color)
        for i in badge_infos:
            for badge in badge_infos[i]:
                # 绘制背景圆
                draw_circle_batch(badge.pos, params.badge_radius, badge.note_badge_color)
                # 绘制数字文本
                num_str = str(i)
                dims = blf.dimensions(font_id, num_str)
                x = badge.pos[0] - dims[0] / 2
                y = badge.pos[1] - dims[1] / 2.5
                blf.position(font_id, x, y, 0)
                blf.draw(font_id, num_str)

    _draw_badge_lines(badge_infos, params)
    _draw_badge_badges(badge_infos, params)

def _process_and_draw_text_and_image_note(node: NotedNode, params: DrawParams, badge_infos: dict[int, list[BadgeInfo]]) -> None:
    """处理单个节点的注释绘制"""
    # 早期返回检查
    text, img, badge_idx = node.note_text, node.note_image, node.note_badge_index
    show_txt, show_img, show_badge = node.note_show_txt, node.note_show_img, node.note_show_badge

    if not (text and show_txt) and not (img and show_img) and not (badge_idx > 0 and show_badge):
        return

    bg_color = node.note_txt_bg_color
    is_visible = check_color_visibility(bg_color)
    if pref().hide_img_by_bg and not is_visible and badge_idx == 0:
        return

    # 计算尺寸和位置
    scale = params.scale
    node_info = _get_node_info(node)
    text_dims = _calc_text_dimensions(node_info, scale, is_visible)
    image_dims = _calc_image_dimensions(node_info, scale)

    is_stacked = (node.note_txt_pos == node.note_img_pos)
    element_pos = (_calc_stacked_positions(node_info, scale, text_dims, image_dims, node.note_txt_pos) if is_stacked
                else _calc_non_stacked_positions(node_info, scale, text_dims, image_dims))
    _apply_centering_offset(element_pos, node_info, text_dims, image_dims)

    # 绘制
    if image_dims.should_draw:
        _draw_image_note(image_dims.texture, element_pos.img_x, element_pos.img_y, image_dims.width, image_dims.height)
    if text_dims.should_draw:
        _draw_text_note(node_info, scale, bg_color,  element_pos.txt_x, element_pos.txt_y, text_dims)
    if badge_idx > 0 and show_badge:
        _collect_badge_coords(node_info, badge_infos)

# region 主入口和注册函数

def draw_callback_px() -> None:
    """主绘制回调函数"""
    space: SpaceNodeEditor = bpy.context.space_data
    if space.type != 'NODE_EDITOR' or not pref().show_all_notes: return
    if pref().dependent_overlay and not space.overlay.show_overlays: return
    tree: NodeTree = space.edit_tree
    if not tree: return

    active = tree.nodes.active
    params = _get_draw_params()
    # 收集序号坐标
    badge_infos: dict[int, list[BadgeInfo]] = {}
    for node in tree.nodes:
        if node == active: continue
        _process_and_draw_text_and_image_note(node, params, badge_infos)  # type: ignore
    if active:
        _process_and_draw_text_and_image_note(active, params, badge_infos)  # type: ignore
    _draw_badge_notes(badge_infos, params)

def register_draw_handler() -> None:
    global handler
    if not handler:
        handler = SpaceNodeEditor.draw_handler_add(draw_callback_px, (), 'WINDOW', 'POST_PIXEL')  # type: ignore

def unregister_draw_handler() -> None:
    global handler
    if handler:
        SpaceNodeEditor.draw_handler_remove(handler, 'WINDOW')
        handler = None
