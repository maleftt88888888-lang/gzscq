#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量图片体积压缩与瘦身工坊 (Batch Image Compressor)
核心特性：
1. 默认自动保存到每张图片的本身目录 (原图在哪，压缩图就保存在哪)
2. 严格限制导出体积不超过 10MB (自适应画质二分法 + 分辨率降采样)
3. 纯本地离线处理，支持 PyWebView 原生桌面窗体与系统浏览器双模式
4. 保存后自动在 Windows 资源管理器中打开目标目录
"""

import os
import sys
import io
import json
import base64
import argparse
import time
import subprocess
import threading
import mimetypes
from urllib.parse import urlparse, parse_qs, unquote
from http.server import HTTPServer, SimpleHTTPRequestHandler
from PIL import Image, ImageOps

# 解决 Windows 控制台 GBK 编码输出问题
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 基础目录定位
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT_DIR = os.path.join(BASE_DIR, "压缩导出图片")
DEFAULT_MAX_MB = 10.0
SAFETY_MARGIN = 0.98


def format_bytes(size_bytes):
    """格式化字节显示"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def open_folder_in_explorer(folder_path):
    """在 Windows 资源管理器中打开指定目录并聚焦"""
    if not folder_path or not os.path.exists(folder_path):
        return
    try:
        if sys.platform == "win32":
            os.startfile(folder_path)
        else:
            subprocess.Popen(["xdg-open", folder_path])
    except Exception as e:
        try:
            subprocess.Popen(f'explorer "{folder_path}"')
        except Exception:
            print(f"无法自动打开文件夹: {e}")


# ==========================================
# 原生 PyWebView 桌面 JS-API 桥接对象
# ==========================================
class CompressDesktopApi:
    def __init__(self, base_dir, default_output_dir):
        self._base_dir = base_dir
        self._default_output_dir = default_output_dir
        self._window = None

    def set_window(self, window):
        self._window = window

    def get_paths_info(self):
        """返回环境信息与默认目录"""
        return {
            "base_dir": self._base_dir,
            "default_output_dir": self._default_output_dir,
            "is_desktop": True,
            "default_mode": "own_dir"  # 默认保存到图片本身目录
        }

    def select_files(self):
        """原生文件选择器，获取图片完整真实路径"""
        if not self._window:
            return []
        try:
            import webview
            files = self._window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=True,
                file_types=("图片文件 (*.jpg;*.jpeg;*.png;*.webp;*.bmp;*.gif)", "所有文件 (*.*)")
            )
            if not files:
                return []
            res = []
            for f in files:
                if os.path.isfile(f):
                    res.append({
                        "path": os.path.abspath(f),
                        "name": os.path.basename(f),
                        "dir": os.path.dirname(os.path.abspath(f)),
                        "size": os.path.getsize(f)
                    })
            return res
        except Exception as e:
            print(f"select_files 出错: {e}")
            return []

    def select_folder(self):
        """原生文件夹选择器，递归扫描其中所有图片并保留真实路径"""
        if not self._window:
            return []
        try:
            import webview
            folders = self._window.create_file_dialog(webview.FOLDER_DIALOG)
            if not folders or len(folders) == 0:
                return []
            folder_path = folders[0] if isinstance(folders, (list, tuple)) else folders
            if not os.path.isdir(folder_path):
                return []

            valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
            res = []
            for root, _, files in os.walk(folder_path):
                for file in files:
                    if os.path.splitext(file)[1].lower() in valid_exts:
                        fp = os.path.join(root, file)
                        res.append({
                            "path": os.path.abspath(fp),
                            "name": os.path.basename(fp),
                            "dir": os.path.abspath(root),
                            "size": os.path.getsize(fp)
                        })
            return res
        except Exception as e:
            print(f"select_folder 出错: {e}")
            return []

    def read_image_data(self, file_path):
        """读取指定图片的 Base64 数据供前端 Canvas 压缩"""
        try:
            if not os.path.exists(file_path):
                return {"success": False, "error": "文件不存在"}
            mime, _ = mimetypes.guess_type(file_path)
            if not mime:
                mime = "image/jpeg"
            with open(file_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            return {"success": True, "data_url": f"data:{mime};base64,{b64}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def save_images_to_local(self, items, save_mode="own_dir"):
        """
        接收前端批量生成的 Base64 图片，并保存到目标位置
        :param items: [{'name': 'pic_compressed.jpg', 'src_path': 'D:/photos/pic.jpg', 'base64': '...'}, ...]
        :param save_mode: 'own_dir' (图片本身目录，默认) 或 'web_dir' (网页同级目录)
        """
        try:
            saved_count = 0
            affected_dirs = set()
            saved_paths = []

            for item in items:
                name = item.get("name", f"img_{int(time.time()*1000)}.jpg")
                src_path = item.get("src_path", "")
                b64 = item.get("base64", "")
                if "," in b64:
                    b64 = b64.split(",", 1)[1]
                raw_bytes = base64.b64decode(b64)

                # 判定保存目标目录：如果 save_mode 是 own_dir 且知道原图目录，则直接保存在原图目录中！
                if save_mode == "own_dir" and src_path and os.path.isdir(os.path.dirname(src_path)):
                    target_dir = os.path.dirname(os.path.abspath(src_path))
                else:
                    target_dir = self._default_output_dir

                os.makedirs(target_dir, exist_ok=True)
                target_file = os.path.join(target_dir, name)

                with open(target_file, "wb") as f:
                    f.write(raw_bytes)

                saved_count += 1
                saved_paths.append(target_file)
                affected_dirs.add(target_dir)

            # 打开输出目录
            for d in affected_dirs:
                open_folder_in_explorer(d)
                break  # 打开首个保存目录

            return {
                "success": True,
                "saved_count": saved_count,
                "affected_dirs": list(affected_dirs),
                "saved_paths": saved_paths
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_directory(self, dir_path=None):
        """打开指定目录"""
        target = dir_path or self._default_output_dir
        open_folder_in_explorer(target)
        return {"success": True}


# ==========================================
# 本地 HTTP API 桥接服务 (供系统浏览器调用)
# ==========================================
class LocalBridgeServer(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/info":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            resp = {
                "base_dir": BASE_DIR,
                "default_output_dir": DEFAULT_OUTPUT_DIR,
                "default_mode": "own_dir",
                "connected": True
            }
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode("utf-8"))
            return

        elif parsed.path == "/api/open_folder":
            qs = parse_qs(parsed.query)
            target = qs.get("dir", [DEFAULT_OUTPUT_DIR])[0]
            open_folder_in_explorer(target)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
            return

        elif parsed.path == "/api/file":
            # 读取本地文件并返回内容
            qs = parse_qs(parsed.query)
            file_path = qs.get("path", [""])[0]
            file_path = unquote(file_path)
            if file_path and os.path.isfile(file_path):
                mime, _ = mimetypes.guess_type(file_path)
                mime = mime or "application/octet-stream"
                try:
                    with open(file_path, "rb") as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", mime)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                except Exception as e:
                    self.send_response(500)
                    self.end_headers()
                    return
            self.send_response(404)
            self.end_headers()
            return

        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/save":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                items = data.get("items", [])
                save_mode = data.get("save_mode", "own_dir")

                saved_count = 0
                affected_dirs = set()

                for item in items:
                    name = item.get("name")
                    src_path = item.get("src_path", "")
                    b64 = item.get("base64", "")
                    if "," in b64:
                        b64 = b64.split(",", 1)[1]
                    raw_bytes = base64.b64decode(b64)

                    # 判定保存目标目录：如果 save_mode 是 own_dir 且知道原图目录，则直接保存在原图目录中！
                    if save_mode == "own_dir" and src_path and os.path.isdir(os.path.dirname(src_path)):
                        target_dir = os.path.dirname(os.path.abspath(src_path))
                    else:
                        target_dir = DEFAULT_OUTPUT_DIR

                    os.makedirs(target_dir, exist_ok=True)
                    target_file = os.path.join(target_dir, name)
                    with open(target_file, "wb") as f:
                        f.write(raw_bytes)
                    saved_count += 1
                    affected_dirs.add(target_dir)

                for d in affected_dirs:
                    open_folder_in_explorer(d)
                    break

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                resp = {
                    "success": True,
                    "saved_count": saved_count,
                    "affected_dirs": list(affected_dirs)
                }
                self.wfile.write(json.dumps(resp, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            return
        super().do_POST()

    def log_message(self, format, *args):
        pass


def run_http_bridge(port=8765):
    """启动本地轻量 HTTP 桥接服务"""
    try:
        class ReusableServer(HTTPServer):
            allow_reuse_address = True

        server = ReusableServer(("127.0.0.1", port), LocalBridgeServer)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        return server
    except Exception as e:
        print(f"提示：HTTP 桥接服务启动跳过 ({e})")
        return None


# ==========================================
# 核心压缩函数 (Python CLI 备用)
# ==========================================
def compress_single_image(
    input_path: str,
    output_path: str,
    max_mb: float = DEFAULT_MAX_MB,
    target_format: str = "AUTO",
    initial_quality: int = 85,
    max_dimension: int = None
):
    """确保单张输出体积 <= max_mb"""
    try:
        orig_size = os.path.getsize(input_path)
        target_max_bytes = int(max_mb * 1024 * 1024 * SAFETY_MARGIN)

        with Image.open(input_path) as img:
            img = ImageOps.exif_transpose(img)
            orig_format = (img.format or "").upper()
            ext = os.path.splitext(output_path)[1].lower()

            if target_format == "AUTO":
                if ext in [".jpg", ".jpeg"]:
                    save_format = "JPEG"
                elif ext == ".png":
                    save_format = "PNG"
                elif ext == ".webp":
                    save_format = "WEBP"
                else:
                    save_format = orig_format if orig_format in ["JPEG", "PNG", "WEBP"] else "JPEG"
            else:
                save_format = target_format.upper()

            has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
            if save_format == "JPEG" and has_alpha:
                bg = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode != "RGBA":
                    img = img.convert("RGBA")
                bg.paste(img, mask=img.split()[3])
                img = bg
            elif save_format == "JPEG" and img.mode != "RGB":
                img = img.convert("RGB")

            w, h = img.size
            if max_dimension and max(w, h) > max_dimension:
                scale = max_dimension / max(w, h)
                w, h = max(1, int(w * scale)), max(1, int(h * scale))
                img = img.resize((w, h), Image.Resampling.LANCZOS)

            current_img = img.copy()

            def test_export(test_image, quality_val, fmt):
                buf = io.BytesIO()
                save_kwargs = {"optimize": True}
                if fmt in ["JPEG", "WEBP"]:
                    save_kwargs["quality"] = quality_val
                elif fmt == "PNG":
                    save_kwargs["compress_level"] = 9
                test_image.save(buf, format=fmt, **save_kwargs)
                return buf.getvalue()

            best_data = None
            current_w, current_h = w, h

            for scale_round in range(5):
                if save_format in ["JPEG", "WEBP"]:
                    low_q = 25
                    high_q = min(initial_quality, 95)
                    best_round_data = None

                    data = test_export(current_img, high_q, save_format)
                    if len(data) <= target_max_bytes:
                        best_data = data
                        break

                    while low_q <= high_q:
                        mid_q = (low_q + high_q) // 2
                        data = test_export(current_img, mid_q, save_format)
                        if len(data) <= target_max_bytes:
                            best_round_data = data
                            low_q = mid_q + 1
                        else:
                            high_q = mid_q - 1

                    if best_round_data is not None:
                        best_data = best_round_data
                        break
                else:
                    data = test_export(current_img, None, "PNG")
                    if len(data) <= target_max_bytes:
                        best_data = data
                        break
                    quantized = current_img.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
                    data = test_export(quantized, None, "PNG")
                    if len(data) <= target_max_bytes:
                        best_data = data
                        break

                current_w = max(100, int(current_w * 0.75))
                current_h = max(100, int(current_h * 0.75))
                current_img = img.resize((current_w, current_h), Image.Resampling.LANCZOS)

            if best_data is None or len(best_data) > target_max_bytes:
                for q in [50, 30, 20]:
                    buf = io.BytesIO()
                    current_img.save(buf, format="WEBP", quality=q, optimize=True)
                    if len(buf.getvalue()) <= target_max_bytes or q == 20:
                        best_data = buf.getvalue()
                        break

            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(best_data)

            final_size = len(best_data)
            saved_pct = ((orig_size - final_size) / orig_size) * 100 if orig_size > 0 else 0
            return {
                "success": True,
                "input": input_path,
                "output": output_path,
                "original_size": orig_size,
                "compressed_size": final_size,
                "saved_pct": saved_pct,
                "width": current_w,
                "height": current_h,
                "within_limit": final_size <= (max_mb * 1024 * 1024),
            }
    except Exception as e:
        return {"success": False, "input": input_path, "error": str(e)}


def start_gui_app():
    """启动图形界面 (原生桌面窗口模式，支持真实路径读取与原目录保存)"""
    html_file = os.path.join(BASE_DIR, "batch_image_compressor.html")
    if not os.path.exists(html_file):
        print(f"错误：未找到网页文件 {html_file}")
        return

    run_http_bridge(port=8765)

    try:
        import webview
        api = CompressDesktopApi(base_dir=BASE_DIR, default_output_dir=DEFAULT_OUTPUT_DIR)
        window = webview.create_window(
            title="批量图片体积压缩瘦身工坊 (自动保存至原图目录 · 严格 ≤ 10MB)",
            url=html_file,
            js_api=api,
            width=1380,
            height=900,
            min_size=(1080, 700),
            text_select=True,
            zoomable=True
        )
        api.set_window(window)
        print("💡 已启动原生桌面窗口...")
        print(f"📁 默认输出目标：自动保存到每张图片的本身目录")
        webview.start(debug=False)
    except Exception as e:
        print(f"提示：桌面原生引擎跳过 ({e})，正在通过系统浏览器打开...")
        import webbrowser
        webbrowser.open(f"file:///{html_file.replace(os.sep, '/')}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


def main():
    parser = argparse.ArgumentParser(description="批量图片体积压缩瘦身工具 (自动保存到图片本身目录)")
    parser.add_argument("-i", "--input", nargs="*", help="输入图片路径或文件夹")
    parser.add_argument("-o", "--output", default=None, help="输出文件夹 (默认: 保存到图片各自的本身目录)")
    parser.add_argument("-m", "--max-mb", type=float, default=10.0, help="单张最大允许体积(MB)")
    parser.add_argument("-f", "--format", choices=["AUTO", "JPEG", "WEBP", "PNG"], default="AUTO", help="目标格式")
    parser.add_argument("-q", "--quality", type=int, default=85, help="画质基准 (1-100)")
    parser.add_argument("-d", "--max-dim", type=int, default=None, help="最大长边限制")
    parser.add_argument("--gui", action="store_true", help="启动图形界面")

    args = parser.parse_args()

    if args.gui or len(sys.argv) == 1:
        start_gui_app()
        return

    valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
    input_files = []
    for item in args.input or []:
        if os.path.isdir(item):
            for root, _, files in os.walk(item):
                for f in files:
                    if os.path.splitext(f)[1].lower() in valid_exts:
                        input_files.append(os.path.join(root, f))
        elif os.path.isfile(item) and os.path.splitext(item)[1].lower() in valid_exts:
            input_files.append(item)

    if not input_files:
        start_gui_app()
        return

    print(f"\n🚀 开始批量压缩 {len(input_files)} 张图片...")
    if args.output:
        print(f"📁 统一输出目录：{os.path.abspath(args.output)}")
    else:
        print(f"📁 输出目录：自动保存到每张图片的【本身所在目录】")
    print("-" * 60)

    affected_dirs = set()
    for i, p in enumerate(input_files, 1):
        name, ext = os.path.splitext(os.path.basename(p))
        if args.format == "WEBP":
            ext = ".webp"
        elif args.format == "JPEG":
            ext = ".jpg"
        elif args.format == "PNG":
            ext = ".png"
        out_name = f"{name}_compressed{ext}"

        # 默认保存到图片本身的目录
        if args.output:
            target_dir = args.output
        else:
            target_dir = os.path.dirname(os.path.abspath(p))

        out_p = os.path.join(target_dir, out_name)
        res = compress_single_image(p, out_p, args.max_mb, args.format, args.quality, args.max_dim)
        if res["success"]:
            affected_dirs.add(target_dir)
            print(f"[{i}/{len(input_files)}] ✅ {out_name} -> {target_dir} ({format_bytes(res['original_size'])} -> {format_bytes(res['compressed_size'])}, -{res['saved_pct']:.1f}%)")
        else:
            print(f"[{i}/{len(input_files)}] ❌ {os.path.basename(p)}: {res.get('error')}")

    for d in affected_dirs:
        open_folder_in_explorer(d)
        break

    print("\n🎉 压缩完成！已自动打开输出目录。")


if __name__ == "__main__":
    main()
