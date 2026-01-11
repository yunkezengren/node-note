import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader
from bpy.types import Image, Node, NodeTree, Context
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

def get_shader(name: str) -> gpu.types.GPUShader | None:
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
        texture = gpu.types.GPUTexture((width, height), format='RGBA32F', data=pixel_data)  # type: ignore
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
    lines: list[str] = []
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

def _get_draw_params() -> dict:
    """获取绘制参数"""
    context = bpy.context
    prefs = pref()
    # 缩放计算
    sys_ui_scale = context.preferences.system.ui_scale
    zoom = get_region_zoom(context)
    prefs_ui_scale = context.preferences.view.ui_scale
    scaled_zoom = zoom * prefs_ui_scale
    # 遮挡检测
    is_occlusion_enabled = prefs.use_occlusion
    occluders = []
    if is_occlusion_enabled and context.selected_nodes:
        occluders = [get_node_screen_rect(n) for n in context.selected_nodes]
    # 序号样式参数
    seq_scale = prefs.seq_scale
    seq_scale_mode = prefs.seq_scale_mode
    seq_abs_scale = prefs.seq_abs_scale
    if seq_scale_mode == 'RELATIVE':
        badge_radius = 7 * seq_scale * scaled_zoom
        arrow_size = 8.0 * seq_scale * scaled_zoom
        base_font_size = 8 * seq_scale * scaled_zoom
    else:
        max_diameter = view_to_region_scaled(140, 0)[0] - view_to_region_scaled(0, 0)[0]
        badge_radius = min(7 * 2, max_diameter / 2) * seq_abs_scale
        arrow_size = min(16, max_diameter * 0.6) * seq_abs_scale
        base_font_size = min(16, max_diameter / 2) * seq_abs_scale
    return {
        'sys_ui_scale': sys_ui_scale,
        'scaled_zoom': scaled_zoom,
        'is_occlusion_enabled': is_occlusion_enabled,
        'occluders': occluders,
        'badge_radius': badge_radius,
        'arrow_size': arrow_size,
        'base_font_size': base_font_size,
    }

def _wrap_text(font_id: int, text: str, txt_width_mode: str, target_width_px: float, pad: float) -> list:
    """文本换行处理"""
    if txt_width_mode == 'FIT':
        return text_split_lines(text)
    else:
        return wrap_text_pure(font_id, text, max(1, target_width_px - pad*2))

def _draw_text_note(node: Node, text, bg_color: RGBA, node_info: dict, txt_x: float, txt_y: float, target_width_px: float, text_layer_height: float) -> None:
    """绘制文本笔记(文本+背景)"""
    scaled_zoom = node_info['scaled_zoom']
    pad = PADDING_X * scaled_zoom
    # 计算文本尺寸
    fs = max(1, int(getattr(node, "na_font_size", 8) * scaled_zoom))
    # 文本换行
    font_id = 0
    blf.size(font_id, fs)
    txt_width_mode = getattr(node, "na_txt_width_mode", 'AUTO')
    lines = _wrap_text(font_id, text, txt_width_mode, target_width_px, pad)
    # 绘制背景
    draw_rounded_rect_batch(txt_x, txt_y, target_width_px, text_layer_height, bg_color, CORNER_RADIUS * scaled_zoom)
    # 绘制文本
    blf.color(font_id, *node.na_text_color)
    blf.disable(font_id, blf.SHADOW)
    blf.size(font_id, fs)
    py = txt_y + pad
    lh = fs * 1.3
    for i, l in enumerate(reversed(lines)):
        blf.position(font_id, int(txt_x + pad), int(py + i*lh + fs*0.25), 0)
        blf.draw(font_id, l)

def _draw_image_note(node: Node, img: Image, img_x: float, img_y: float, img_draw_w: float, img_draw_h: float, texture) -> None:
    """绘制图像笔记"""
    # 绘制
    if texture:
        draw_texture_batch(texture, img_x, img_y, img_draw_w, img_draw_h)
    else:
        draw_missing_placeholder(img_x, img_y, img_draw_w, img_draw_h)

def _calculate_node_position(node: Node, params: dict) -> dict:
    """计算节点位置信息"""
    scaled_zoom = params['scaled_zoom']
    sys_ui_scale = params['sys_ui_scale']
    loc = nd_abs_loc(node)
    h_logical = node.dimensions.y / sys_ui_scale
    logical_top_y = max(loc.y - (h_logical/2 + 9), loc.y + (h_logical/2 - 9)) if node.hide else loc.y
    logical_bottom_y = min(loc.y - (h_logical/2 + 9), loc.y + (h_logical/2 - 9)) if node.hide else (loc.y - h_logical)

    sx, sy = view_to_region_scaled(loc.x, logical_top_y)
    _, sy_b = view_to_region_scaled(loc.x, logical_bottom_y)
    sx_r, _ = view_to_region_scaled(loc.x + node.width + 1.0, loc.y)

    node_w_px = sx_r - sx
    node_h_px = sy - sy_b

    return {
        'sx': sx,
        'sy': sy,
        'sy_b': sy_b,
        'sx_r': sx_r,
        'node_w_px': node_w_px,
        'node_h_px': node_h_px,
        'loc': loc,
        'scaled_zoom': scaled_zoom,
    }

def _process_and_draw_text_and_image_note(node: Node, params: dict, sequence_coords: dict) -> None:
    """处理单个节点的注释绘制"""
    # 获取节点属性
    text = getattr(node, "na_text", "").strip()
    img = getattr(node, "na_image", None)
    seq_idx = getattr(node, "na_seq_index", 0)
    show_txt = getattr(node, "na_show_txt", True)
    show_img = getattr(node, "na_show_img", True)
    show_seq = getattr(node, "na_show_seq", True)
    # 跳过空注释
    if not (text and show_txt) and not (img and show_img) and not (seq_idx > 0 and show_seq):
        return
    # 颜色可见性检查
    bg_color = getattr(node, "na_txt_bg_color", DEFAULT_BG)
    visible_by_bg_color = check_color_visibility(bg_color)
    if not visible_by_bg_color and seq_idx == 0:
        return
    # 计算位置和尺寸
    node_info = _calculate_node_position(node, params)

    # 获取对齐和交换属性
    txt_align = getattr(node, "na_txt_pos", 'TOP')
    img_align = getattr(node, "na_img_pos", 'TOP')
    swap = getattr(node, "na_swap_content_order", False)
    
    # 检查是否堆叠
    is_stacked = (txt_align == img_align)
    
    # 计算文本和图像的尺寸
    scaled_zoom = node_info['scaled_zoom']
    pad = PADDING_X * scaled_zoom
    node_w_px = node_info['node_w_px']
    loc = node_info['loc']
    
    # 文本尺寸计算
    target_width_px = 0
    text_layer_height = 0
    lines = []
    if text and show_txt and visible_by_bg_color:
        fs = max(1, int(getattr(node, "na_font_size", 8) * scaled_zoom))
        txt_width_mode = getattr(node, "na_txt_width_mode", 'AUTO')
        
        # 计算目标宽度
        if txt_width_mode == 'FIT' and text:
            font_id = 0
            blf.size(font_id, fs)
            max_line_w = 0
            for line in text_split_lines(text):
                width = blf.dimensions(font_id, line)[0]
                if width > max_line_w:
                    max_line_w = width
            target_width_px = max_line_w + (pad*2)
        elif txt_width_mode == 'AUTO':
            min_w = view_to_region_scaled(loc.x + MIN_AUTO_WIDTH, loc.y)[0] - node_info['sx']
            target_width_px = max(node_w_px, min_w)
        else:
            manual_w = getattr(node, "na_txt_bg_width", 200)
            target_width_px = view_to_region_scaled(loc.x + manual_w, loc.y)[0] - node_info['sx']
        
        # 文本换行
        font_id = 0
        blf.size(font_id, fs)
        if txt_width_mode == 'FIT':
            lines = text_split_lines(text)
        else:
            lines = _wrap_text(font_id, text, txt_width_mode, target_width_px, pad)
        
        text_layer_height = (len(lines) * fs * 1.3) + pad*2 if lines else 0
    
    # 图像尺寸计算
    img_draw_w = 0
    img_draw_h = 0
    texture = None
    if img and show_img and visible_by_bg_color:
        img_width_mode = getattr(node, "na_img_width_mode", 'AUTO')
        ref_w = max(node_w_px, (view_to_region_scaled(loc.x + MIN_AUTO_WIDTH, loc.y)[0] - node_info['sx']))
        
        if img_width_mode == 'ORIGINAL':
            base_w = img.size[0] * scaled_zoom
        elif img_width_mode == 'AUTO':
            base_w = ref_w
        else:
            base_w = getattr(node, "na_img_width", 140) * scaled_zoom
        
        img_draw_w = base_w
        img_draw_h = base_w * (img.size[1] / img.size[0]) if img.size[0] > 0 else 0
        texture = get_gpu_texture(img) if img.size[0] > 0 else None
    
    # 计算位置(应用堆叠逻辑)
    if not is_stacked:
        # 非堆叠情况：各自独立计算位置
        if text and show_txt and visible_by_bg_color:
            offset = getattr(node, "na_txt_offset", (0, 0))
            txt_x, txt_y = _calculate_element_position(node_info, txt_align, offset, target_width_px, text_layer_height, scaled_zoom)
        else:
            txt_x, txt_y = 0, 0
            
        if img and show_img and visible_by_bg_color:
            img_off = getattr(node, "na_img_offset", (0, 0))
            img_x, img_y = _calculate_element_position(node_info, img_align, img_off, img_draw_w, img_draw_h, scaled_zoom)
        else:
            img_x, img_y = 0, 0
    else:
        # 堆叠情况：计算相对位置
        inner_w, inner_h, inner_off = (target_width_px, text_layer_height, getattr(node, "na_txt_offset", (0, 0))) if not swap else (img_draw_w, img_draw_h, getattr(node, "na_img_offset", (0, 0)))
        outer_w, outer_h, outer_off = (img_draw_w, img_draw_h, getattr(node, "na_img_offset", (0, 0))) if not swap else (target_width_px, text_layer_height, getattr(node, "na_txt_offset", (0, 0)))
        
        inner_x, inner_y = _calculate_element_position(node_info, txt_align, inner_off, inner_w, inner_h, scaled_zoom)
        outer_x, outer_y = inner_x, inner_y

        ox_scaled = outer_off[0] * scaled_zoom
        oy_scaled = outer_off[1] * scaled_zoom
        sy = node_info['sy']
        
        if txt_align == 'TOP':
            outer_x = inner_x + ox_scaled
            outer_y = inner_y + inner_h + oy_scaled
        elif txt_align == 'BOTTOM':
            outer_x = inner_x + ox_scaled
            outer_y = inner_y - outer_h + oy_scaled
        elif txt_align == 'LEFT':
            outer_x = inner_x - outer_w + ox_scaled
            outer_y = sy - outer_h + oy_scaled
        elif txt_align == 'RIGHT':
            outer_x = inner_x + inner_w + ox_scaled
            outer_y = sy - outer_h + oy_scaled
        
        if not swap:
            txt_x, txt_y = inner_x, inner_y
            img_x, img_y = outer_x, outer_y
        else:
            img_x, img_y = inner_x, inner_y
            txt_x, txt_y = outer_x, outer_y
    
    # 绘制文本
    if text and show_txt and visible_by_bg_color:
        _draw_text_note(node, text, bg_color, node_info, txt_x, txt_y, target_width_px, text_layer_height)
    
    # 绘制图像(包含居中校正)
    if img and show_img and visible_by_bg_color:
        # 居中校正
        if (is_stacked and txt_align in {'TOP', 'BOTTOM'}) or (not is_stacked and img_align in {'TOP', 'BOTTOM'}):
            center_correction = (node_w_px - img_draw_w) / 2
            img_x += center_correction
        _draw_image_note(node, img, img_x, img_y, img_draw_w, img_draw_h, texture)
    
    # 收集序号坐标
    if seq_idx > 0 and show_seq:
        _collect_sequence_coords(seq_idx, node_info, sequence_coords, params)

def _collect_sequence_coords(seq_idx: int, node_info: dict, sequence_coords: dict, params: dict) -> None:
    """收集序号坐标"""
    badge_x = node_info['sx']
    badge_y = node_info['sy']
    badge_radius = params['badge_radius']

    if seq_idx not in sequence_coords:
        sequence_coords[seq_idx] = []
    sequence_coords[seq_idx].append((badge_x, badge_y, badge_radius))

def _draw_sequence_lines(sequence_coords: dict, params: dict) -> None:
    """绘制序号连线"""
    if not pref().show_sequence_lines or len(sequence_coords) < 2: return
    line_points = []
    line_col: RGBA = pref().seq_line_color
    sorted_indices = sorted(sequence_coords.keys())
    max_idx = max(sorted_indices)
    arrow_size = params['arrow_size']

    for idx_a in sorted_indices:
        target_idx = None
        for next_idx in range(idx_a + 1, max_idx + 1):
            if next_idx in sequence_coords:
                target_idx = next_idx
                break
        if target_idx is not None:
            for p1 in sequence_coords[idx_a]:
                for p2 in sequence_coords[target_idx]:
                    line_points.append(p1[:2])
                    line_points.append(p2[:2])
                    retreat = p1[2]
                    draw_arrow_head(p1[:2], p2[:2], line_col, size=arrow_size, retreat=retreat)

    line_thickness = pref().seq_line_thickness
    draw_lines_batch(line_points, line_col, thickness=line_thickness)

def _draw_sequence_badges(sequence_coords: dict, params: dict) -> None:
    """绘制序号徽章(背景+文本)"""
    prefs = pref()
    badge_radius = params['badge_radius']
    base_font_size = params['base_font_size']
    seq_font_col = list(prefs.seq_font_color) if prefs else (1.0, 1.0, 1.0, 1.0)

    # 绘制背景圆
    for idx in sequence_coords:
        for badge_x, badge_y, badge_radius in sequence_coords[idx]:
            draw_circle_batch(badge_x, badge_y, badge_radius, tuple(prefs.seq_bg_color))

    # 绘制数字文本
    font_id = 0
    blf.size(font_id, int(base_font_size))
    blf.color(font_id, *seq_font_col)
    for idx in sequence_coords:
        for badge_x, badge_y, badge_radius in sequence_coords[idx]:
            num_str = str(idx)
            dims = blf.dimensions(font_id, num_str)
            blf.position(font_id, int(badge_x - dims[0] / 2), int(badge_y - dims[1] / 2.5), 0)
            blf.draw(font_id, num_str)

def _draw_sequence_notes(sequence_coords: dict, params: dict) -> None:
    # 绘制序列连线
    _draw_sequence_lines(sequence_coords, params)
    _draw_sequence_badges(sequence_coords, params)

def _calculate_element_position(node_info: dict, alignment: str, offset_vec: float2, self_w: float, self_h: float,
                                scaled_zoom: float) -> float2:
    """计算元素位置"""
    sx = node_info['sx']
    sy = node_info['sy']
    sy_b = node_info['sy_b']
    sx_r = node_info['sx_r']

    bx, by = sx, sy
    ox = offset_vec[0] * scaled_zoom
    oy = offset_vec[1] * scaled_zoom

    if alignment == 'TOP':
        bx = sx
        by = sy + MARGIN_BOTTOM*scaled_zoom
    elif alignment == 'BOTTOM':
        bx = sx
        by = sy_b - MARGIN_BOTTOM*scaled_zoom - self_h
    elif alignment == 'LEFT':
        bx = sx - MARGIN_BOTTOM*scaled_zoom - self_w
        by = sy - self_h
    elif alignment == 'RIGHT':
        bx = sx_r + MARGIN_BOTTOM*scaled_zoom
        by = sy - self_h

    return bx + ox, by + oy

def draw_callback_px() -> None:
    """主绘制回调函数"""
    space = bpy.context.space_data
    if space.type != 'NODE_EDITOR' or not pref().show_all_notes: return
    tree: NodeTree = space.edit_tree
    if not tree: return

    params = _get_draw_params()
    # 收集序号坐标
    sequence_coords: dict[int, list[tuple[float, float, float]]] = {}
    for node in tree.nodes:
        _process_and_draw_text_and_image_note(node, params, sequence_coords)
    _draw_sequence_notes(sequence_coords, params)

def register_draw_handler() -> None:
    global handler
    if not handler:
        handler = bpy.types.SpaceNodeEditor.draw_handler_add(draw_callback_px, (), 'WINDOW', 'POST_PIXEL')  # type: ignore

def unregister_draw_handler() -> None:
    global handler
    if handler:
        bpy.types.SpaceNodeEditor.draw_handler_remove(handler, 'WINDOW')
        handler = None
