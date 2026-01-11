import bpy
import blf
import gpu
from dataclasses import dataclass
from gpu_extras.batch import batch_for_shader
from bpy.types import Image, Context, Scene, Node, NodeTree
import array
import math
from .preferences import pref, text_split_lines
from .utils import (
    float2,
    int3,
    RGBA,
    nd_abs_loc,
    get_region_zoom,
    view_to_region_scaled,
    check_color_visibility,
    get_node_screen_rect,
)

# ==================== 常量 ====================
PADDING_X = 2
PADDING_Y = 2
MARGIN_BOTTOM = 2
MIN_AUTO_WIDTH = 101
CORNER_RADIUS = 2.0
CORNER_SCALE_Y = 1.1
DEFAULT_BG = (0.2, 0.3, 0.5, 0.9)

handler = None
_shader_cache: dict[str, gpu.types.GPUShader] = {}
_manual_texture_cache: dict[str, gpu.types.GPUTexture] = {}


@dataclass
class DrawContext:
    """绘制上下文，避免大量参数传递"""
    context: Context
    prefs: object
    zoom: float
    scaled_zoom: float
    sys_ui_scale: float
    occlusion_enabled: bool
    occluders: list[tuple[float, float, float, float]]
    tree: NodeTree
    show_sequence_lines: bool
    seq_scale: float
    seq_scale_mode: str
    seq_abs_scale: float
    badge_radius: float
    arrow_size: float
    base_font_size: float
    seq_line_color: RGBA
    seq_line_thickness: float
    seq_bg_color: RGBA
    seq_font_color: list[float]


@dataclass
class NodeDrawContext:
    """单节点绘制上下文"""
    node: Node
    draw_ctx: DrawContext
    text: str
    image: Image | None
    show_image: bool
    sequence_idx: int
    show_text_bg: bool
    show_sequence: bool
    text_color: RGBA
    bg_color: RGBA
    font_size: int
    scaled_padding: float
    text_alignment: str
    text_offset: float2
    image_alignment: str
    image_offset: float2
    swap_content: bool
    node_region_x: float
    node_region_y: float
    node_region_y_bottom: float
    node_region_x_right: float
    node_width_px: float
    node_height_px: float
    text_target_width: float
    text_layer_height: float
    text_lines: list[str]
    image_draw_width: float
    image_draw_height: float
    image_texture: gpu.types.GPUTexture | None
    text_position: float2
    image_position: float2
    seq_position: tuple[float, float, float]
    is_visible: bool
    is_occluded: bool

def get_shader(name: str):
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

def get_gpu_texture(image: Image) -> gpu.types.GPUTexture | None:
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

def create_texture_from_pixels(image: Image) -> gpu.types.GPUTexture | None:
    global _manual_texture_cache
    cache_key = image.name
    if cache_key in _manual_texture_cache:
        return _manual_texture_cache[cache_key]
    try:
        width, height = image.size
        # TODO 优化性能
        pixel_data = array.array('f', [0.0] * width * height * 4)
        image.pixels.foreach_get(pixel_data)
        texture = gpu.types.GPUTexture((width, height), format='RGBA32F', data=pixel_data) # type: ignore
        _manual_texture_cache[cache_key] = texture
        return texture
    except:
        return None

def draw_rounded_rect_batch(x: float, y: float, width: float, height: float, color: RGBA, radius: float = 3.0) -> None:
    shader = get_shader('UNIFORM_COLOR')
    if not shader: return
    r_base = min(radius, width / 2, height / 2)
    r_x = r_base
    r_y = r_base * CORNER_SCALE_Y
    r_y = min(r_y, height / 2)
    vertices: list[float2] = []
    indices: list[int3] = []
    idx_cursor = 0

    def add_quad(x1: float, y1: float, x2: float, y2: float):
        nonlocal idx_cursor
        vertices.extend([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])
        indices.extend([(idx_cursor, idx_cursor + 1, idx_cursor + 2), (idx_cursor, idx_cursor + 2, idx_cursor + 3)])
        idx_cursor += 4

    if r_base < 0.5:
        add_quad(x, y, x + width, y + height)
    else:
        add_quad(x, y + r_y, x + width, y + height - r_y)
        add_quad(x + r_x, y, x + width - r_x, y + r_y)
        add_quad(x + r_x, y + height - r_y, x + width - r_x, y + height)
        corners = [(x + width - r_x, y + height - r_y, 0.0, math.pi / 2), (x + r_x, y + height - r_y, math.pi / 2, math.pi),
                   (x + r_x, y + r_y, math.pi, 3 * math.pi / 2), (x + width - r_x, y + r_y, 3 * math.pi / 2, 2 * math.pi)]
        for cx, cy, sa, ea in corners:
            center_idx = idx_cursor
            vertices.append((cx, cy))
            idx_cursor += 1
            theta_step = (ea-sa) / 12
            for k in range(13):
                px = cx + math.cos(sa + k*theta_step) * r_x
                py = cy + math.sin(sa + k*theta_step) * r_y
                vertices.append((px, py))
                idx_cursor += 1
            for k in range(12):
                indices.append((center_idx, center_idx + 1 + k, center_idx + 2 + k))
    batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
    shader.bind()
    shader.uniform_float("color", color)
    gpu.state.blend_set('ALPHA')
    batch.draw(shader)

def draw_circle_batch(x: float, y: float, radius: float, color: RGBA) -> None:
    shader = get_shader('UNIFORM_COLOR')
    if not shader: return
    vertices: list[float2] = [(x, y)]
    indices: list[int3] = []
    theta_step = (2 * math.pi) / 32
    for i in range(33):
        px = x + math.cos(i * theta_step) * radius
        py = y + math.sin(i * theta_step) * radius
        vertices.append((px, py))
    for i in range(32):
        indices.append((0, i + 1, i + 2))
    batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
    shader.bind()
    shader.uniform_float("color", color)
    gpu.state.blend_set('ALPHA')
    batch.draw(shader)

def draw_lines_batch(points: list[float2], color: RGBA, thickness: float = 2.0) -> None:
    if len(points) < 2: return
    shader = get_shader('UNIFORM_COLOR')
    if not shader: return
    gpu.state.line_width_set(thickness)
    batch = batch_for_shader(shader, 'LINES', {"pos": points})
    shader.bind()
    shader.uniform_float("color", color)
    gpu.state.blend_set('ALPHA')
    batch.draw(shader)

def draw_texture_batch(texture: gpu.types.GPUTexture, x: float, y: float, width: float, height: float) -> None:
    if not texture: return
    shader = get_shader('2D_IMAGE')
    if not shader: return
    vertices = ((x, y), (x + width, y), (x + width, y + height), (x, y + height))
    uvs = ((0, 0), (1, 0), (1, 1), (0, 1))
    indices = ((0, 1, 2), (2, 3, 0))
    batch = batch_for_shader(shader, 'TRIS', {"pos": vertices, "texCoord": uvs}, indices=indices)
    shader.bind()
    shader.uniform_sampler("image", texture)
    gpu.state.blend_set('ALPHA')
    batch.draw(shader)
    gpu.state.blend_set('NONE')

def draw_missing_placeholder(x: float, y: float, width: float, height: float) -> None:
    shader = get_shader('UNIFORM_COLOR')
    if not shader: return
    vertices = ((x, y), (x + width, y), (x + width, y + height), (x, y + height))
    batch_box = batch_for_shader(shader, 'LINE_LOOP', {"pos": vertices})
    shader.bind()
    shader.uniform_float("color", (1.0, 0.0, 0.0, 1.0))
    gpu.state.blend_set('ALPHA')
    batch_box.draw(shader)
    vertices_x = ((x, y), (x + width, y + height), (x, y + height), (x + width, y))
    batch_x = batch_for_shader(shader, 'LINES', {"pos": vertices_x})
    batch_x.draw(shader)

def draw_arrow_head(start_point: float2, end_point: float2, color: RGBA, size: float = 10.0, retreat: float = 8.0) -> None:
    shader = get_shader('UNIFORM_COLOR')
    if not shader: return
    x1, y1 = start_point
    x2, y2 = end_point
    dx = x2 - x1
    dy = y2 - y1
    length = math.sqrt(dx*dx + dy*dy)
    if length < 0.001: return
    ux = dx / length
    uy = dy / length
    tip_x = x2 - ux*retreat
    tip_y = y2 - uy*retreat
    base_x = tip_x - ux*size
    base_y = tip_y - uy*size
    perp_x = -uy
    perp_y = ux
    half_w = size * 0.5
    v1 = (tip_x, tip_y)
    v2 = (base_x + perp_x*half_w, base_y + perp_y*half_w)
    v3 = (base_x - perp_x*half_w, base_y - perp_y*half_w)
    vertices = [v1, v2, v3]
    batch = batch_for_shader(shader, 'TRIS', {"pos": vertices})
    shader.bind()
    shader.uniform_float("color", color)
    gpu.state.blend_set('ALPHA')
    batch.draw(shader)

def wrap_text_pure(font_id: int, text: str, max_width: float):
    lines = []
    for para in text_split_lines(text):
        curr_line, curr_w = "", 0
        if not para:
            lines.append("")
            continue
        for char in para:
            cw = blf.dimensions(font_id, char)[0]
            if curr_w + cw > max_width and curr_line:
                lines.append(curr_line)
                curr_line = char
                curr_w = cw
            else:
                curr_line += char
                curr_w += cw
        if curr_line: lines.append(curr_line)
    return lines


def _calc_text_target_width(
    node: Node, context: Context, font_id: int, text: str, node_region_x: float,
    node_region_x_right: float, scaled_zoom: float
) -> float:
    """计算文本目标宽度"""
    txt_width_mode = getattr(node, "na_txt_width_mode", 'AUTO')
    pad = PADDING_X * scaled_zoom

    if txt_width_mode == 'FIT' and text:
        max_line_w = 0
        for line in text_split_lines(text):
            width = blf.dimensions(font_id, line)[0]
            if width > max_line_w:
                max_line_w = width
        return max_line_w + (pad * 2)

    if txt_width_mode == 'AUTO':
        min_w = view_to_region_scaled(context, node_region_x + MIN_AUTO_WIDTH, 0)[0] - node_region_x
        return max(node_region_x_right - node_region_x, min_w)

    manual_w = getattr(node, "na_txt_bg_width", 200)
    return view_to_region_scaled(context, node_region_x + manual_w, 0)[0] - node_region_x


def _calc_image_dimensions(
    node: Node, context: Context, image: Image, scaled_zoom: float, node_region_x: float,
    node_region_x_right: float
) -> tuple[float, float, gpu.types.GPUTexture | None]:
    """计算图像绘制尺寸和纹理"""
    img_width_mode = getattr(node, "na_img_width_mode", 'AUTO')
    ref_w = max(node_region_x_right - node_region_x, view_to_region_scaled(context, node_region_x + MIN_AUTO_WIDTH, 0)[0] - node_region_x)

    if img_width_mode == 'ORIGINAL':
        base_w = image.size[0] * scaled_zoom
    elif img_width_mode == 'AUTO':
        base_w = ref_w
    else:
        base_w = getattr(node, "na_img_width", 140) * scaled_zoom

    if image.size[0] <= 0:
        return 0, 0, None

    draw_w = base_w
    draw_h = base_w * (image.size[1] / image.size[0])
    texture = get_gpu_texture(image)

    return draw_w, draw_h, texture


def _get_base_position(
    alignment: str, offset_vec: float2, self_w: float, self_h: float,
    sx: float, sy: float, sy_b: float, sx_r: float, scaled_zoom: float
) -> float2:
    """根据对齐方式计算基础位置"""
    bx, by = sx, sy
    ox = offset_vec[0] * scaled_zoom
    oy = offset_vec[1] * scaled_zoom

    if alignment == 'TOP':
        bx = sx
        by = sy + MARGIN_BOTTOM * scaled_zoom
    elif alignment == 'BOTTOM':
        bx = sx
        by = sy_b - MARGIN_BOTTOM * scaled_zoom - self_h
    elif alignment == 'LEFT':
        bx = sx - MARGIN_BOTTOM * scaled_zoom - self_w
        by = sy - self_h
    elif alignment == 'RIGHT':
        bx = sx_r + MARGIN_BOTTOM * scaled_zoom
        by = sy - self_h

    return bx + ox, by + oy


def _calc_annotations_position(
    align: str, off: float2, img_align: str, img_off: float2,
    target_w: float, target_h: float, img_w: float, img_h: float,
    swap: bool, sx: float, sy: float, sy_b: float, sx_r: float, scaled_zoom: float
) -> tuple[float2, float2]:
    """计算文本和图像的绘制位置"""
    txt_x, txt_y = 0, 0
    img_x, img_y = 0, 0
    is_stacked = (align == img_align)

    if not is_stacked:
        txt_x, txt_y = _get_base_position(align, off, target_w, target_h, sx, sy, sy_b, sx_r, scaled_zoom)
        img_x, img_y = _get_base_position(img_align, img_off, img_w, img_h, sx, sy, sy_b, sx_r, scaled_zoom)
    else:
        inner_w, inner_h, inner_off = (target_w, target_h, off) if not swap else (img_w, img_h, img_off)
        outer_w, outer_h, outer_off = (img_w, img_h, img_off) if not swap else (target_w, target_h, off)
        inner_x, inner_y = _get_base_position(align, inner_off, inner_w, inner_h, sx, sy, sy_b, sx_r, scaled_zoom)
        outer_x, outer_y = inner_x, inner_y

        gap = 0
        ox_scaled = outer_off[0] * scaled_zoom
        oy_scaled = outer_off[1] * scaled_zoom

        if align == 'TOP':
            outer_y = inner_y + inner_h + gap + oy_scaled
            outer_x = inner_x + ox_scaled
        elif align == 'BOTTOM':
            outer_y = inner_y - outer_h - gap + oy_scaled
            outer_x = inner_x + ox_scaled
        elif align == 'LEFT':
            outer_x = inner_x - outer_w - gap + ox_scaled
            outer_y = inner_y + oy_scaled
        elif align == 'RIGHT':
            outer_x = inner_x + inner_w + gap + ox_scaled
            outer_y = inner_y + oy_scaled

        if not swap:
            txt_x, txt_y = inner_x, inner_y
            img_x, img_y = outer_x, outer_y
        else:
            img_x, img_y = inner_x, inner_y
            txt_x, txt_y = outer_x, outer_y

    return (txt_x, txt_y), (img_x, img_y)


def _check_occlusion(
    txt_x: float, txt_y: float, target_w: float, target_h: float,
    img_x: float, img_y: float, img_w: float, img_h: float,
    occluders: list[tuple[float, float, float, float]]
) -> bool:
    """检查是否被遮挡"""
    if not occluders:
        return False

    min_x = min(txt_x, img_x)
    max_x = max(txt_x + target_w, img_x + img_w)
    min_y = min(txt_y, img_y)
    max_y = max(txt_y + target_h, img_y + img_h)
    bbox = (min_x, min_y, max_x, max_y)

    return any(not (bbox[2] < o[0] or bbox[0] > o[2] or bbox[3] < o[1] or bbox[1] > o[3]) for o in occluders)


def _init_context() -> DrawContext | None:
    """初始化绘制上下文"""
    context = bpy.context
    if not context.space_data or context.space_data.type != 'NODE_EDITOR':
        return None

    prefs = pref()
    if not prefs.show_annotations:
        return None

    tree = context.space_data.edit_tree
    if not tree:
        return None

    sys_ui_scale = context.preferences.system.ui_scale
    zoom = get_region_zoom(context)
    prefs_ui_scale = context.preferences.view.ui_scale
    scaled_zoom = zoom * prefs_ui_scale

    is_occlusion_enabled = prefs.use_occlusion
    occluders = []
    if is_occlusion_enabled and context.selected_nodes:
        occluders = [get_node_screen_rect(context, n) for n in context.selected_nodes]

    seq_scale = prefs.seq_scale
    seq_scale_mode = prefs.seq_scale_mode
    seq_abs_scale = prefs.seq_abs_scale

    if seq_scale_mode == 'RELATIVE':
        badge_radius = 7 * seq_scale * scaled_zoom
        arrow_size = 8.0 * seq_scale * scaled_zoom
        base_font_size = 8 * seq_scale * scaled_zoom
    else:
        max_diameter = view_to_region_scaled(context, 140, 0)[0] - view_to_region_scaled(context, 0, 0)[0]
        badge_radius = min(7 * 2, max_diameter / 2) * seq_abs_scale
        arrow_size = min(16, max_diameter * 0.6) * seq_abs_scale
        base_font_size = min(16, max_diameter / 2) * seq_abs_scale

    return DrawContext(
        context=context,
        prefs=prefs,
        zoom=zoom,
        scaled_zoom=scaled_zoom,
        sys_ui_scale=sys_ui_scale,
        occlusion_enabled=is_occlusion_enabled,
        occluders=occluders,
        tree=tree,
        show_sequence_lines=prefs.show_sequence_lines,
        seq_scale=seq_scale,
        seq_scale_mode=seq_scale_mode,
        seq_abs_scale=seq_abs_scale,
        badge_radius=badge_radius,
        arrow_size=arrow_size,
        base_font_size=base_font_size,
        seq_line_color=tuple(prefs.seq_line_color),
        seq_line_thickness=prefs.seq_line_thickness,
        seq_bg_color=tuple(prefs.seq_bg_color),
        seq_font_color=list(prefs.seq_font_color)
    )


def _create_node_context(draw_ctx: DrawContext, node: Node) -> NodeDrawContext | None:
    """为单个节点创建绘制上下文"""
    text = getattr(node, "na_text", "").strip()
    img = getattr(node, "na_image", None)
    show_img = getattr(node, "na_show_img", True)
    seq_idx = getattr(node, "na_seq_index", 0)
    show_text_bg = getattr(node, "na_show_txt", True)
    show_seq = getattr(node, "na_show_seq", True)

    if not text and not (img and show_img) and not (seq_idx > 0 and show_seq):
        return None

    col = getattr(node, "na_txt_bg_color", DEFAULT_BG)
    is_visible_by_color = check_color_visibility(draw_ctx.context.scene, col)

    if not is_visible_by_color and seq_idx == 0:
        return None

    fs = max(1, int(getattr(node, "na_font_size", 8) * draw_ctx.scaled_zoom))
    pad = PADDING_X * draw_ctx.scaled_zoom

    align = getattr(node, "na_txt_pos", 'TOP')
    off = getattr(node, "na_txt_offset", (0, 0))
    img_align = getattr(node, "na_img_pos", 'TOP') if hasattr(node, "na_img_pos") else 'TOP'
    img_off = getattr(node, "na_img_offset", (0, 0)) if hasattr(node, "na_img_offset") else (0, 0)
    swap = getattr(node, "na_swap_content_order", False)

    loc = nd_abs_loc(node)
    h_logical = node.dimensions.y / draw_ctx.sys_ui_scale
    logical_top_y = max(loc.y - (h_logical / 2 + 9), loc.y + (h_logical / 2 - 9)) if node.hide else loc.y
    logical_bottom_y = min(loc.y - (h_logical / 2 + 9), loc.y + (h_logical / 2 - 9)) if node.hide else (loc.y - h_logical)

    sx, sy = view_to_region_scaled(draw_ctx.context, loc.x, logical_top_y)
    _, sy_b = view_to_region_scaled(draw_ctx.context, loc.x, logical_bottom_y)
    sx_r, _ = view_to_region_scaled(draw_ctx.context, loc.x + node.width + 1.0, loc.y)

    node_w_px = sx_r - sx
    node_h_px = sy - sy_b

    font_id = 0
    blf.size(font_id, fs)

    target_width_px = _calc_text_target_width(
        node, draw_ctx.context, font_id, text, sx, sx_r, draw_ctx.scaled_zoom
    )

    lines = []
    if text and show_text_bg:
        txt_width_mode = getattr(node, "na_txt_width_mode", 'AUTO')
        if txt_width_mode == 'FIT':
            lines = text_split_lines(text)
        else:
            lines = wrap_text_pure(font_id, text, max(1, target_width_px - pad * 2))

    text_layer_height = (len(lines) * fs * 1.3) + pad * 2 if lines else 0

    img_draw_w, img_draw_h, texture = 0, 0, None
    if img and show_img:
        img_draw_w, img_draw_h, texture = _calc_image_dimensions(
            node, draw_ctx.context, img, draw_ctx.scaled_zoom, sx, sx_r
        )

    txt_pos, img_pos = _calc_annotations_position(
        align, off, img_align, img_off, target_width_px, text_layer_height,
        img_draw_w, img_draw_h, swap, sx, sy, sy_b, sx_r, draw_ctx.scaled_zoom
    )

    seq_x, seq_y = sx, sy

    is_occluded = False
    if draw_ctx.occlusion_enabled and draw_ctx.occluders and not node.select and node != draw_ctx.context.active_node:
        is_occluded = _check_occlusion(
            txt_pos[0], txt_pos[1], target_width_px, text_layer_height,
            img_pos[0], img_pos[1], img_draw_w, img_draw_h, draw_ctx.occluders
        )

    is_visible = not is_occluded and is_visible_by_color

    return NodeDrawContext(
        node=node,
        draw_ctx=draw_ctx,
        text=text,
        image=img,
        show_image=show_img,
        sequence_idx=seq_idx,
        show_text_bg=show_text_bg,
        show_sequence=show_seq,
        text_color=getattr(node, "na_text_color", (1, 1, 1, 1)),
        bg_color=col,
        font_size=fs,
        scaled_padding=pad,
        text_alignment=align,
        text_offset=off,
        image_alignment=img_align,
        image_offset=img_off,
        swap_content=swap,
        node_region_x=sx,
        node_region_y=sy,
        node_region_y_bottom=sy_b,
        node_region_x_right=sx_r,
        node_width_px=node_w_px,
        node_height_px=node_h_px,
        text_target_width=target_width_px,
        text_layer_height=text_layer_height,
        text_lines=lines,
        image_draw_width=img_draw_w,
        image_draw_height=img_draw_h,
        image_texture=texture,
        text_position=txt_pos,
        image_position=img_pos,
        seq_position=(seq_x, seq_y, draw_ctx.badge_radius),
        is_visible=is_visible,
        is_occluded=is_occluded
    )


def _draw_text_annotation(node_ctx: NodeDrawContext) -> None:
    """绘制文本标注"""
    if not node_ctx.text or not node_ctx.show_text_bg:
        return

    draw_rounded_rect_batch(
        node_ctx.text_position[0], node_ctx.text_position[1],
        node_ctx.text_target_width, node_ctx.text_layer_height,
        node_ctx.bg_color, CORNER_RADIUS * node_ctx.draw_ctx.scaled_zoom
    )

    font_id = 0
    blf.color(font_id, *node_ctx.text_color)
    blf.disable(font_id, blf.SHADOW)
    blf.size(font_id, node_ctx.font_size)

    pad = node_ctx.scaled_padding
    py = node_ctx.text_position[1] + pad
    lh = node_ctx.font_size * 1.3

    for i, line in enumerate(reversed(node_ctx.text_lines)):
        bx = int(node_ctx.text_position[0] + pad)
        by = int(py + i * lh + node_ctx.font_size * 0.25)
        blf.position(font_id, bx, by, 0)
        blf.draw(font_id, line)


def _draw_image_annotation(node_ctx: NodeDrawContext) -> None:
    """绘制图像标注"""
    if not node_ctx.image or not node_ctx.show_image:
        return

    img_x = node_ctx.image_position[0]
    img_y = node_ctx.image_position[1]
    img_w = node_ctx.image_draw_width
    img_h = node_ctx.image_draw_height

    if (node_ctx.text_alignment == node_ctx.image_alignment and
        node_ctx.text_alignment in {'TOP', 'BOTTOM'}):
        center_correction = (node_ctx.node_width_px - img_w) / 2
        img_x += center_correction

    if node_ctx.image_texture:
        draw_texture_batch(node_ctx.image_texture, img_x, img_y, img_w, img_h)
    else:
        draw_missing_placeholder(img_x, img_y, img_w, img_h)


def _process_node_annotations(node_ctx: NodeDrawContext) -> None:
    """处理单个节点的所有标注绘制"""
    if not node_ctx.is_visible:
        return

    if node_ctx.show_text_bg and node_ctx.text:
        _draw_text_annotation(node_ctx)

    if node_ctx.show_image and node_ctx.image:
        _draw_image_annotation(node_ctx)


def _draw_sequence_connections(
    seq_coords: dict[int, list[tuple[float, float, float]]],
    line_color: RGBA,
    arrow_size: float,
    line_thickness: float
) -> None:
    """绘制序号之间的连线箭头"""
    if len(seq_coords) < 2:
        return

    line_points: list[float2] = []
    sorted_indices = sorted(seq_coords.keys())
    max_idx = max(sorted_indices)

    for idx_a in sorted_indices:
        target_idx = None
        for next_idx in range(idx_a + 1, max_idx + 1):
            if next_idx in seq_coords:
                target_idx = next_idx
                break

        if target_idx is None:
            continue

        for p1 in seq_coords[idx_a]:
            for p2 in seq_coords[target_idx]:
                line_points.append(p1[:2])
                line_points.append(p2[:2])
                retreat = p1[2]
                draw_arrow_head(p1[:2], p2[:2], line_color, size=arrow_size, retreat=retreat)

    if line_points:
        draw_lines_batch(line_points, line_color, thickness=line_thickness)


def _draw_sequence_badge_backgrounds(
    seq_coords: dict[int, list[tuple[float, float, float]]],
    bg_color: RGBA
) -> None:
    """绘制序号徽章背景"""
    for coords in seq_coords.values():
        for badge_x, badge_y, badge_radius in coords:
            draw_circle_batch(badge_x, badge_y, badge_radius, bg_color)


def _draw_sequence_numbers(
    seq_coords: dict[int, list[tuple[float, float, float]]],
    font_color: list[float],
    base_font_size: float
) -> None:
    """绘制序号数字"""
    font_id = 0
    blf.size(font_id, int(base_font_size))
    blf.color(font_id, *font_color)

    for coords in seq_coords.values():
        for badge_x, badge_y, _ in coords:
            num_str = str(list(seq_coords.keys())[list(seq_coords.values()).index(coords)])
            idx = None
            for k, v in seq_coords.items():
                if v is coords:
                    idx = k
                    break
            if idx is None:
                continue

            num_str = str(idx)
            dims = blf.dimensions(font_id, num_str)
            blf.position(font_id, int(badge_x - dims[0] / 2), int(badge_y - dims[1] / 2.5), 0)
            blf.draw(font_id, num_str)


def _draw_sequence_overlay(
    draw_ctx: DrawContext,
    seq_coords: dict[int, list[tuple[float, float, float]]]
) -> None:
    """绘制序号叠加层"""
    if not seq_coords:
        return

    gpu.state.depth_test_set('NONE')

    if draw_ctx.show_sequence_lines and len(seq_coords) > 1:
        _draw_sequence_connections(
            seq_coords, draw_ctx.seq_line_color,
            draw_ctx.arrow_size, draw_ctx.seq_line_thickness
        )

    _draw_sequence_badge_backgrounds(seq_coords, draw_ctx.seq_bg_color)
    _draw_sequence_numbers(seq_coords, draw_ctx.seq_font_color, draw_ctx.base_font_size)


def _collect_sequence_positions(
    nodes: list[Node],
    node_ctxs: list[NodeDrawContext]
) -> dict[int, list[tuple[float, float, float]]]:
    """收集所有节点的序号位置"""
    seq_coords: dict[int, list[tuple[float, float, float]]] = {}

    for node_ctx in node_ctxs:
        if node_ctx.sequence_idx > 0 and node_ctx.show_sequence:
            seq_coords[node_ctx.sequence_idx].append(node_ctx.seq_position)

    return seq_coords


def draw_callback_px() -> None:
    """主绘制回调，Blender 调用入口"""
    draw_ctx = _init_context()
    if draw_ctx is None:
        return

    node_contexts: list[NodeDrawContext] = []
    for node in draw_ctx.tree.nodes:
        node_ctx = _create_node_context(draw_ctx, node)
        if node_ctx is not None:
            node_contexts.append(node_ctx)

    for node_ctx in node_contexts:
        _process_node_annotations(node_ctx)

    seq_coords = _collect_sequence_positions(draw_ctx.tree.nodes, node_contexts)
    _draw_sequence_overlay(draw_ctx, seq_coords)

def register_draw_handler() -> None:
    global handler
    if not handler:
        handler = bpy.types.SpaceNodeEditor.draw_handler_add(draw_callback_px, (), 'WINDOW', 'POST_PIXEL') # type: ignore

def unregister_draw_handler() -> None:
    global handler
    if handler:
        bpy.types.SpaceNodeEditor.draw_handler_remove(handler, 'WINDOW')
        handler = None
