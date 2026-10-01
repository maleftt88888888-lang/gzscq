import os
import sys
import webbrowser
import http.server
import socketserver
import threading

PORT = 8765
HTML_FILE = "image_text_replacer.html"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def log_message(self, format, *args):
        # 保持控制台干净，不输出频繁的静态请求日志
        pass

def start_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), QuietHandler) as httpd:
        print(f"======================================================")
        print(f"✨ 智能图片同款改字程序已启动！")
        print(f"🌐 本地访问地址: http://localhost:{PORT}/{HTML_FILE}")
        print(f"======================================================")
        httpd.serve_forever()

def main():
    # 启动后台服务
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    url = f"http://localhost:{PORT}/{HTML_FILE}"

    # 尝试使用 pywebview 唤起独立原生桌面窗口
    try:
        import webview
        print("🚀 正在以独立桌面窗口运行...")
        webview.create_window(
            title="智能图片改字大师 (原字体与排版保持一致)",
            url=url,
            width=1280,
            height=850,
            min_size=(960, 640)
        )
        webview.start()
    except Exception:
        # 回退到默认浏览器自动打开
        print("🌐 正在为您打开默认浏览器...")
        webbrowser.open(url)
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n程序已关闭。")

if __name__ == "__main__":
    main()
