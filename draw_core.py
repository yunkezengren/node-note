import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader
from bpy.types import Context, Scene, Node, Image
import array
import math
from .preference import pref, text_split_lines

float2 = tuple[float, float]
int2 = tuple[int, int]
int3 = tuple[int, int, int]
RGBA = tuple[float, float, float, float]
Rect = tuple[float, float, float, float]

PADDING_X = 2
PADDING_Y = 2
MARGIN_BOTTOM = 2
MIN_AUTO_WIDTH = 101
CORNER_RADIUS = 2.0
CORNER_SCALE_Y = 1.1
DEFAULT_BG = (0.2, 0.3, 0.5, 0.9)

_shader_cache: dict[str, gpu.types.GPUShader] = {}

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

_manual_texture_cache: dict[str, gpu.types.GPUTexture] = {}

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
        texture = gpu.types.GPUTexture((width, height), format='RGBA32F', data=pixel_data)
        _manual_texture_cache[cache_key] = texture
        return texture
    except:
        return None

def get_region_zoom(context: Context) -> float:
    view2d = context.region.view2d
    x0, y0 = view2d.view_to_region(0, 0, clip=False)
    x1, y1 = view2d.view_to_region(1000, 1000, clip=False)
    return 1.0 if x1 == x0 else math.sqrt((x1 - x0)**2 + (y1 - y0)**2) / 1000

def view_to_region_scaled(context: Context, x: float, y: float) -> int2:
    ui_scale = context.preferences.system.ui_scale
    return context.region.view2d.view_to_region(x * ui_scale, y * ui_scale, clip=False)

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
    theta_step = (2 * math.pi) / 16
    for i in range(17):
        px = x + math.cos(i * theta_step) * radius
        py = y + math.sin(i * theta_step) * radius
        vertices.append((px, py))
    for i in range(16):
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

def check_color_visibility(scene: Scene, bg_color: RGBA) -> bool:
    prefs = pref()
    if not prefs: return True
    r, g, b = bg_color[:3]
    preset_cols = {
        'red': prefs.col_preset_1,
        'green': prefs.col_preset_2,
        'blue': prefs.col_preset_3,
        'orange': prefs.col_preset_4,
        'purple': prefs.col_preset_5,
    }
    prefs = pref()
    for name, col_vec in preset_cols.items():
        if abs(r - col_vec[0]) + abs(g - col_vec[1]) + abs(b - col_vec[2]) < 0.05:
            return getattr(prefs, f"filter_{name}", True)
    return prefs.filter_other

def get_node_screen_rect(context: Context, node: Node) -> Rect:
    loc_x, loc_y = node.location.x, node.location.y
    width, height = node.width, node.dimensions.y
    x1, y1 = view_to_region_scaled(context, loc_x, loc_y)
    x2, y2 = view_to_region_scaled(context, loc_x + width, loc_y - height)
    return (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))

def is_rect_overlap(r1: Rect, r2: Rect) -> bool:
    return not (r1[2] < r2[0] or r1[0] > r2[2] or r1[3] < r2[1] or r1[1] > r2[3])

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

def draw_callback_px() -> None:
    context = bpy.context
    if not context.space_data or context.space_data.type != 'NODE_EDITOR': return
    prefs = pref()
    if not prefs.show_annotations: return

    tree = context.space_data.edit_tree
    if not tree: return
    scene = context.scene

    sys_ui_scale = context.preferences.system.ui_scale
    zoom = get_region_zoom(context)
    prefs_ui_scale = context.preferences.view.ui_scale
    scaled_zoom = zoom * prefs_ui_scale

    # 遮挡检测
    is_occlusion_enabled = prefs.use_occlusion
    occluders = []
    if is_occlusion_enabled and context.selected_nodes:
        occluders = [get_node_screen_rect(context, n) for n in context.selected_nodes]

    sequence_coords = {}

    for node in tree.nodes:
        text = getattr(node, "na_text", "").strip()
        img = getattr(node, "na_image", None)
        show_img = getattr(node, "na_show_img", True)
        seq_idx = getattr(node, "na_seq_index", 0)
        show_text_bg = getattr(node, "na_show_txt", True)
        show_seq = getattr(node, "na_show_seq", True)

        # 如果什么都没有，直接跳过
        if not text and not (img and show_img) and not (seq_idx > 0 and show_seq): continue

        # [修复 1] 颜色检查只控制文本/图片的“显示状态”，不再跳过循环（以免连坐序号）
        col = getattr(node, "na_txt_bg_color", DEFAULT_BG)
        is_visible_by_color = check_color_visibility(scene, col)

        # 性能优化：如果颜色不可见 且 没有序号要画，那确实可以跳过
        if not is_visible_by_color and seq_idx == 0:
            continue

        fs = max(1, int(getattr(node, "na_font_size", 8) * scaled_zoom))
        pad = PADDING_X * scaled_zoom

        align = getattr(node, "na_txt_pos", 'TOP')
        off = getattr(node, "na_txt_offset", (0, 0))
        img_align = getattr(node, "na_img_pos", 'TOP') if hasattr(node, "na_img_pos") else 'TOP'
        img_off = getattr(node, "na_img_offset", (0, 0)) if hasattr(node, "na_img_offset") else (0, 0)
        swap = getattr(node, "na_swap_content_order", False)

        loc = node.location
        h_logical = node.dimensions.y / sys_ui_scale
        logical_top_y = max(loc.y - (h_logical/2 + 9), loc.y + (h_logical/2 - 9)) if node.hide else loc.y
        logical_bottom_y = min(loc.y - (h_logical/2 + 9), loc.y + (h_logical/2 - 9)) if node.hide else (loc.y - h_logical)

        sx, sy = view_to_region_scaled(context, loc.x, logical_top_y)
        _, sy_b = view_to_region_scaled(context, loc.x, logical_bottom_y)
        sx_r, _ = view_to_region_scaled(context, loc.x + node.width + 1.0, loc.y)

        node_w_px = sx_r - sx
        node_h_px = sy - sy_b

        font_id = 0
        blf.size(font_id, fs)

        txt_width_mode = getattr(node, "na_txt_width_mode", 'AUTO')
        target_width_px = 0

        if txt_width_mode == 'FIT':
            max_line_w = 0
            if text:
                for line in text_split_lines(text):
                    w = blf.dimensions(font_id, line)[0]
                    if w > max_line_w: max_line_w = w
            target_width_px = max_line_w + (pad*2)
        elif txt_width_mode == 'AUTO':
            min_w = view_to_region_scaled(context, loc.x + MIN_AUTO_WIDTH, loc.y)[0] - sx
            target_width_px = max(node_w_px, min_w)
        else:
            manual_w = getattr(node, "na_txt_bg_width", 200)
            target_width_px = (view_to_region_scaled(context, loc.x + manual_w, loc.y)[0] - sx)

        lines = []
        if text:
            if txt_width_mode == 'FIT':
                lines = text_split_lines(text)
            else:
                lines = wrap_text_pure(font_id, text, max(1, target_width_px - pad*2))

        text_layer_height = (len(lines) * fs * 1.3) + pad*2 if lines else 0

        img_draw_w, img_draw_h, texture = 0, 0, None
        if img and show_img:
            img_width_mode = getattr(node, "na_img_width_mode", 'AUTO')
            ref_w = max(node_w_px, (view_to_region_scaled(context, loc.x + MIN_AUTO_WIDTH, loc.y)[0] - sx))
            if img_width_mode == 'ORIGINAL':
                base_w = img.size[0] * scaled_zoom
            elif img_width_mode == 'AUTO':
                base_w = ref_w
            else:
                base_w = getattr(node, "na_img_width", 150) * scaled_zoom
            if img.size[0] > 0:
                img_draw_w = base_w
                img_draw_h = base_w * (img.size[1] / img.size[0])
                texture = get_gpu_texture(img)

        def get_base_pos(alignment: str, offset_vec: float2, self_w: float, self_h: float) -> float2:
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

        txt_x, txt_y = 0, 0
        img_x, img_y = 0, 0
        is_stacked = (align == img_align)

        if not is_stacked:
            txt_x, txt_y = get_base_pos(align, off, target_width_px, text_layer_height)
            img_x, img_y = get_base_pos(img_align, img_off, img_draw_w, img_draw_h)
        else:
            inner_w, inner_h, inner_off = (target_width_px, text_layer_height, off) if not swap else (img_draw_w, img_draw_h, img_off)
            outer_w, outer_h, outer_off = (img_draw_w, img_draw_h, img_off) if not swap else (target_width_px, text_layer_height, off)
            inner_x, inner_y = get_base_pos(align, inner_off, inner_w, inner_h)
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

        seq_anchor_x, seq_anchor_y = sx, sy
        if seq_idx > 0:
            sequence_coords[seq_idx] = (seq_anchor_x, seq_anchor_y)

        is_occluded = False
        if is_occlusion_enabled and occluders and not node.select and node != context.active_node:
            min_x = min(txt_x, img_x)
            max_x = max(txt_x + target_width_px, img_x + img_draw_w)
            min_y = min(txt_y, img_y)
            max_y = max(txt_y + text_layer_height, img_y + img_draw_h)
            bbox = (min_x, min_y, max_x, max_y)
            if any(not (bbox[2] < o[0] or bbox[0] > o[2] or bbox[3] < o[1] or bbox[1] > o[3]) for o in occluders):
                is_occluded = True

        # [修复 2] 只有当 (没有被遮挡) 且 (颜色可见) 时，才绘制内容
        if not is_occluded and is_visible_by_color:
            if text and show_text_bg:
                draw_rounded_rect_batch(txt_x, txt_y, target_width_px, text_layer_height, col, CORNER_RADIUS * scaled_zoom)
                blf.color(font_id, *node.na_text_color)
                blf.disable(font_id, blf.SHADOW)
                blf.size(font_id, fs)
                py = txt_y + pad
                lh = fs * 1.3
                for i, l in enumerate(reversed(lines)):
                    blf.position(font_id, int(txt_x + pad), int(py + i*lh + fs*0.25), 0)
                    blf.draw(font_id, l)

            if img and show_img:
                final_img_x = img_x
                if (is_stacked and align in {'TOP', 'BOTTOM'}) or (not is_stacked and img_align in {'TOP', 'BOTTOM'}):
                    center_correction = (node_w_px-img_draw_w) / 2
                    final_img_x += center_correction
                if texture: 
                    draw_texture_batch(texture, final_img_x, img_y, img_draw_w, img_draw_h)
                else: 
                    draw_missing_placeholder(final_img_x, img_y, img_draw_w, img_draw_h)

        if seq_idx > 0 and show_seq:
            gpu.state.depth_test_set('NONE')
            seq_scale = prefs.seq_scale if prefs else 1.0
            badge_radius = (7.0 * seq_scale) * scaled_zoom
            badge_x = seq_anchor_x
            badge_y = seq_anchor_y

            # 序号颜色
            seq_col = getattr(node, "na_sequence_color", (0.8, 0.1, 0.1, 1.0))
            draw_circle_batch(badge_x, badge_y, badge_radius, seq_col)

            # 序号字号和颜色
            seq_font_col = list(prefs.seq_font_color) if prefs else (1.0, 1.0, 1.0, 1.0)
            base_font_size = 8 * seq_scale
            blf.size(font_id, int(base_font_size * scaled_zoom))
            blf.color(font_id, *seq_font_col)
            num_str = str(seq_idx)
            dims = blf.dimensions(font_id, num_str)
            blf.position(font_id, int(badge_x - dims[0] / 2), int(badge_y - dims[1] / 2.5), 0)
            blf.draw(font_id, num_str)

    if prefs.show_sequence_lines and len(sequence_coords) > 1:
        sorted_indices = sorted(sequence_coords.keys())
        line_points = []
        line_col = (1.0, 0.8, 0.2, 0.8)
        for i in range(len(sorted_indices) - 1):
            idx_a = sorted_indices[i]
            idx_b = sorted_indices[i + 1]
            p1 = sequence_coords[idx_a]
            p2 = sequence_coords[idx_b]
            line_points.append(p1)
            line_points.append(p2)
            arrow_sz = 8.0 * scaled_zoom
            retreat_dist = 6.0 * scaled_zoom
            draw_arrow_head(p1, p2, line_col, size=arrow_sz, retreat=retreat_dist)
        draw_lines_batch(line_points, line_col, thickness=2.0)

h = None

def register_draw_handler() -> None:
    global h
    if not h: 
        h = bpy.types.SpaceNodeEditor.draw_handler_add(draw_callback_px, (), 'WINDOW', 'POST_PIXEL')

def unregister_draw_handler() -> None:
    global h
    if h:
        bpy.types.SpaceNodeEditor.draw_handler_remove(h, 'WINDOW')
        h = None
