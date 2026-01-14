# Blender超级技术交流社窖藏 欢迎测试或加入你的巧妙工具 你可以任意复用或改写以下代码
# 不借助PIL的图像处理库 包含导入剪贴板、图像分辨率修改

import bpy
import ctypes
import ctypes.wintypes
import struct
import tempfile
import os
import sys
import subprocess
import zlib
import shutil
import urllib.parse
import datetime

def import_clipboard_image() -> bpy.types.Image | None:
    """
    Blender专用：跨平台读取剪贴板图像/图像文件，导入Blender数据并返回Image对象
    优先级：图像数据 > 图像文件 | 无外部库依赖 | 自动适配格式
    返回：Blender Image对象（已打包到数据块），失败返回None
    """
    # 隐藏Blender默认的多余输出（可选）
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')

    try:
        temp_dir = tempfile.gettempdir()
        target_path = None
        is_image_data = False
        supported_image_ext = (".png", ".jpg", ".jpeg", ".bmp", ".exr", ".webp", ".cin", ".sgi", ".rgb", ".bw", ".jp2", ".jp2", ".hdr",
                               ".tga", ".tif", ".tiff")

        # 验证临时目录可写性
        if not os.access(temp_dir, os.W_OK):
            print("❌ 临时目录不可写", file=old_stdout)
            return None

        def _is_supported_image_file(file_path: str) -> bool:
            #判断文件是否为支持的图像格式
            return os.path.isfile(file_path) and file_path.lower().endswith(supported_image_ext)

        # 跨平台剪贴板处理逻辑
        image_data = None
        file_paths = []
        if sys.platform == "win32":
            # Windows：CF_PNG/CF_DIB 图像数据 + CF_HDROP 文件路径
            CF_DIB = 8
            CF_PNG = 0x0000000B
            CF_HDROP = 15
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            shell32 = ctypes.WinDLL("shell32", use_last_error=True)

            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [
                    ("biSize", ctypes.wintypes.DWORD),
                    ("biWidth", ctypes.c_long),
                    ("biHeight", ctypes.c_long),
                    ("biPlanes", ctypes.wintypes.WORD),
                    ("biBitCount", ctypes.wintypes.WORD),
                    ("biCompression", ctypes.wintypes.DWORD),
                    ("biSizeImage", ctypes.wintypes.DWORD),
                    ("biXPelsPerMeter", ctypes.c_long),
                    ("biYPelsPerMeter", ctypes.c_long),
                    ("biClrUsed", ctypes.wintypes.DWORD),
                    ("biClrImportant", ctypes.wintypes.DWORD),
                ]

            # WinAPI函数签名
            user32.OpenClipboard.argtypes = [ctypes.wintypes.HWND]
            user32.OpenClipboard.restype = ctypes.wintypes.BOOL
            user32.CloseClipboard.argtypes = []
            user32.CloseClipboard.restype = ctypes.wintypes.BOOL
            user32.IsClipboardFormatAvailable.argtypes = [ctypes.c_uint]
            user32.IsClipboardFormatAvailable.restype = ctypes.wintypes.BOOL
            user32.GetClipboardData.argtypes = [ctypes.c_uint]
            user32.GetClipboardData.restype = ctypes.wintypes.HANDLE
            kernel32.GlobalLock.argtypes = [ctypes.wintypes.HGLOBAL]
            kernel32.GlobalLock.restype = ctypes.c_void_p
            kernel32.GlobalUnlock.argtypes = [ctypes.wintypes.HGLOBAL]
            kernel32.GlobalUnlock.restype = ctypes.wintypes.BOOL
            kernel32.GlobalSize.argtypes = [ctypes.wintypes.HGLOBAL]
            kernel32.GlobalSize.restype = ctypes.c_size_t
            shell32.DragQueryFileW.argtypes = [ctypes.c_void_p, ctypes.wintypes.UINT, ctypes.c_wchar_p, ctypes.wintypes.UINT]
            shell32.DragQueryFileW.restype = ctypes.wintypes.UINT

            if not user32.OpenClipboard(None):
                raise RuntimeError(f"无法打开剪贴板，错误码: {ctypes.get_last_error()}")

            try:
                # 优先获取PNG数据
                if user32.IsClipboardFormatAvailable(CF_PNG):
                    h_png = user32.GetClipboardData(CF_PNG)
                    if h_png:
                        p_png = kernel32.GlobalLock(h_png)
                        if p_png:
                            png_size = kernel32.GlobalSize(h_png)
                            image_data = ctypes.string_at(p_png, png_size)
                            kernel32.GlobalUnlock(h_png)
                            if image_data.startswith(b"\x89PNG\r\n\x1a\n"):
                                target_path = os.path.join(temp_dir, "blender_clipboard_image.png")
                                is_image_data = True
                # 无PNG则获取DIB
                if not is_image_data and user32.IsClipboardFormatAvailable(CF_DIB):
                    h_dib = user32.GetClipboardData(CF_DIB)
                    if h_dib:
                        p_dib = kernel32.GlobalLock(h_dib)
                        if p_dib:
                            dib_size = kernel32.GlobalSize(h_dib)
                            dib_data = ctypes.string_at(p_dib, dib_size)
                            kernel32.GlobalUnlock(h_dib)
                            if len(dib_data) >= ctypes.sizeof(BITMAPINFOHEADER):
                                bmih = BITMAPINFOHEADER.from_buffer_copy(dib_data)
                                if bmih.biSize == 40 and bmih.biPlanes == 1:
                                    BMP_SIGN = 0x4D42
                                    palette_size = 0
                                    if bmih.biBitCount <= 8:
                                        num_colors = bmih.biClrUsed if bmih.biClrUsed else (1 << bmih.biBitCount)
                                        palette_size = min(num_colors, 256) * 4
                                    bf_off = 14 + bmih.biSize + palette_size
                                    bf_size = 14 + len(dib_data)
                                    bmp_head = struct.pack("<HIHHI", BMP_SIGN, bf_size, 0, 0, bf_off)
                                    image_data = bmp_head + dib_data
                                    target_path = os.path.join(temp_dir, "blender_clipboard_image.bmp")
                                    is_image_data = True
                # 无图像数据则获取文件路径
                if not is_image_data and user32.IsClipboardFormatAvailable(CF_HDROP):
                    h_drop = user32.GetClipboardData(CF_HDROP)
                    if h_drop:
                        p_drop = kernel32.GlobalLock(h_drop)
                        if p_drop:
                            drop_files = ctypes.c_void_p(p_drop)
                            file_count = shell32.DragQueryFileW(drop_files, -1, None, 0)
                            for i in range(file_count):
                                buf = ctypes.create_unicode_buffer(1024)
                                shell32.DragQueryFileW(drop_files, i, buf, 1024)
                                file_path = buf.value
                                if _is_supported_image_file(file_path):
                                    file_paths.append(file_path)
                            kernel32.GlobalUnlock(h_drop)
                    # 复制第一个有效图像文件
                    if file_paths:
                        src_file = file_paths[0]
                        file_name = os.path.basename(src_file)
                        target_path = os.path.join(temp_dir, f"blender_clipboard_file_{file_name}")
                        shutil.copy2(src_file, target_path)
            finally:
                user32.CloseClipboard()

        elif sys.platform == "darwin":
            # macOS：图像数据 + 文件路径
            img_cmd = ["osascript", "-e", 'get the clipboard as «class PNGf»']
            img_result = subprocess.run(img_cmd, capture_output=True, text=False)
            if img_result.returncode == 0:
                png_raw = img_result.stdout[11:-3]
                if png_raw:
                    png_data = zlib.unhexlify(png_raw)
                    if png_data.startswith(b"\x89PNG\r\n\x1a\n"):
                        target_path = os.path.join(temp_dir, "blender_clipboard_image.png")
                        image_data = png_data
                        is_image_data = True
            # 无图像数据则获取文件路径
            if not is_image_data:
                file_cmd = ["osascript", "-e", 'tell application "Finder" to get POSIX path of (get the clipboard as alias list)']
                file_result = subprocess.run(file_cmd, capture_output=True, text=True)
                if file_result.returncode == 0:
                    file_paths = [p.strip() for p in file_result.stdout.split("\n") if p.strip()]
                    for file_path in file_paths:
                        if _is_supported_image_file(file_path):
                            file_name = os.path.basename(file_path)
                            target_path = os.path.join(temp_dir, f"blender_clipboard_file_{file_name}")
                            shutil.copy2(file_path, target_path)
                            break

        elif sys.platform.startswith("linux"):
            # Linux：图像数据 + 文件路径
            tool_img = None
            tool_file = None
            if shutil.which("xclip"):
                tool_img = ["xclip", "-selection", "clipboard", "-t", "image/png", "-o"]
                tool_file = ["xclip", "-selection", "clipboard", "-t", "text/uri-list", "-o"]
            elif shutil.which("wl-paste"):
                tool_img = ["wl-paste", "-t", "image/png"]
                tool_file = ["wl-paste", "-t", "text/uri-list"]
            if not tool_img:
                raise RuntimeError("请安装xclip（X11）或wl-paste（Wayland）")

            # 优先获取图像数据
            img_result = subprocess.run(tool_img, capture_output=True, text=False)
            if img_result.returncode == 0:
                png_data = img_result.stdout
                if png_data.startswith(b"\x89PNG\r\n\x1a\n"):
                    target_path = os.path.join(temp_dir, "blender_clipboard_image.png")
                    image_data = png_data
                    is_image_data = True
            # 无图像数据则获取文件路径
            if not is_image_data and tool_file:
                file_result = subprocess.run(tool_file, capture_output=True, text=True)
                if file_result.returncode == 0:
                    file_paths = []
                    for line in file_result.stdout.split("\n"):
                        line = line.strip()
                        if line.startswith("file://"):
                            file_path = line[7:]
                            file_path = urllib.parse.unquote(file_path)
                            if _is_supported_image_file(file_path):
                                file_paths.append(file_path)
                    if file_paths:
                        src_file = file_paths[0]
                        file_name = os.path.basename(src_file)
                        target_path = os.path.join(temp_dir, f"blender_clipboard_file_{file_name}")
                        shutil.copy2(src_file, target_path)
        else:
            raise RuntimeError(f"暂不支持的系统: {sys.platform}")

        # 写入临时文件（保持原有逻辑）
        if is_image_data and image_data and target_path:
            with open(target_path, "wb") as f:
                f.write(image_data)
        elif not target_path or not os.path.exists(target_path):
            raise RuntimeError("剪贴板中无支持的图像数据或图像文件")

        # 导入图像数据并创建Image对象
        if not target_path or not os.path.exists(target_path):
            print("❌ 无有效图像文件可导入Blender", file=old_stdout)
            return None

        # 导入图像文件到Blender数据块
        try:
            # bpy.data.images.load()：导入本地文件为Blender Image对象
            blender_image = bpy.data.images.load(filepath=target_path)
        except Exception as e:
            print(f"❌ 导入Blender失败: {e}", file=old_stdout)
            return None

        # 打包图像（嵌入到Blender文件中，不依赖外部临时文件）
        blender_image.pack()  # 关键：将图像数据打包到Blender数据块，删除外部依赖

        # 优化Image对象属性（可选，提升可用性）
        time_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S%f")[:-3]  # %f 是微秒，[:-3] 截取为毫秒
        blender_image.name = f"Clipboard_Image_{time_str}"
        blender_image.filepath_raw = ""  # 清空外部文件路径，标记为内嵌图像
        blender_image.source = 'FILE'  # 标记图像来源

        #  清理临时文件（可选，避免残留）
        if os.path.exists(target_path):
            os.remove(target_path)

        print(f"成功导入Blender，图像名称: {blender_image.name}", file=old_stdout)
        print(f"图像尺寸: {blender_image.size[0]} x {blender_image.size[1]}", file=old_stdout)
        return blender_image

    except Exception as e:
        print(f"❌ 整体流程失败: {type(e).__name__} - {str(e)}", file=old_stdout)
        return None

    finally:
        # 恢复标准输出
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = old_stdout
        sys.stderr = old_stderr

def _resize_image(image: bpy.types.Image, newsize: tuple[int, int]) -> bpy.types.Image | None:
    """
    通用图像分辨率调整模块：将传入的Blender Image对象调整为指定分辨率
    参数：
        image: 待调整分辨率的Blender Image对象
        newsize: 目标分辨率元组 (width, height)，如 (1920, 1080)
    返回：
        调整分辨率后的Blender Image对象（新数据块），失败返回None
    """
    # 输入参数合法性校验
    if not isinstance(image, bpy.types.Image):
        print("不是有效的Blender Image对象")
        return None
    if not isinstance(newsize, tuple) or len(newsize) != 2:
        print("newsize必须是包含2个整数的元组 (width, height)")
        return None
    new_w, new_h = newsize
    if not isinstance(new_w, int) or not isinstance(new_h, int) or new_w <= 0 or new_h <= 0:
        print("分辨率必须为正整数")
        return None

    orig_w, orig_h = image.size
    # 若目标分辨率与原分辨率一致，直接返回原图像（避免无意义操作）
    if (new_w, new_h) == (orig_w, orig_h):
        print(f"目标分辨率与原图像一致，无需调整")
        return image.copy()

    try:
        # 复制原图像，避免修改原始图像数据
        resized_img = image.copy()

        # 核心：调整图像分辨率（Blender Image内置scale方法）
        resized_img.scale(new_w, new_h)

        # 优化新图像名称，标记分辨率信息
        orig_name = os.path.splitext(resized_img.name)[0]
        resized_img.name = f"{orig_name}_resized_{new_w}x{new_h}"

        # 处理图像打包状态（保持与原图一致的打包属性）
        if image.packed_file is not None:
            # 若原图已打包，新图也打包（内嵌到Blender文件）
            resized_img.pack()
            # 清理临时文件（若存在）
            try:
                if os.path.exists(bpy.path.abspath(resized_img.filepath_raw)):
                    os.remove(bpy.path.abspath(resized_img.filepath_raw))
            except Exception as e:
                print(f"清理临时文件失败: {e}")

        print(f"图像分辨率调整成功：{orig_w}x{orig_h} → {new_w}x{new_h}")
        return resized_img

    except Exception as e:
        print(f"图像分辨率调整失败: {type(e).__name__} - {str(e)}")
        # 清理异常情况下创建的无效图像
        if 'resized_img' in locals() and resized_img in bpy.data.images:
            bpy.data.images.remove(resized_img)
        return None

# Blender中调用示例（可直接在Blender脚本编辑器运行）
if __name__ == "__main__":
    # 调用函数并获取Blender Image对象
    imported_image = import_clipboard_image()

    # 验证返回结果（可选）
    if imported_image:
        print(f"\n✅ 返回的Blender Image对象: {imported_image}")
        print(f"📋 图像属性: 尺寸={imported_image.size}, 格式={imported_image.file_format}")
    else:
        print("\n❌ 未成功获取Blender Image对象")
