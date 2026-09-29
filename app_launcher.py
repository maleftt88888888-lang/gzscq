import base64
import os
import subprocess
import sys
import webview

class DocumentApi:
    def __init__(self):
        self._window = None

    def set_window(self, window):
        self._window = window

    def save_image(self, base64_data, filename):
        """
        接收前端 Canvas 导出的 base64 图片数据，弹出原生另存为对话框并保存到磁盘。
        """
        try:
            if not base64_data:
                return {'success': False, 'error': '图片数据为空'}

            if ',' in base64_data:
                base64_data = base64_data.split(',', 1)[1]

            image_bytes = base64.b64decode(base64_data)

            # 获取桌面作为默认起始目录
            desktop_dir = os.path.join(os.path.expanduser('~'), 'Desktop')
            if not os.path.exists(desktop_dir):
                desktop_dir = os.path.expanduser('~')

            save_path = None
            cancelled = False

            # 使用 tkinter 弹出原生 Windows "另存为" 对话框
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                selected = filedialog.asksaveasfilename(
                    title="另存为签批文档图片",
                    initialfile=filename,
                    initialdir=desktop_dir,
                    filetypes=[("PNG 图片 (*.png)", "*.png"), ("所有文件 (*.*)", "*.*")],
                    defaultextension=".png"
                )
                root.destroy()
                if selected:
                    save_path = selected
                else:
                    cancelled = True
            except Exception as tk_err:
                print(f"Tkinter dialog error: {tk_err}")

            if cancelled:
                return {'success': False, 'cancelled': True, 'msg': '已取消保存'}

            # 如果对话框异常且未显式取消，采用桌面默认路径作为保底
            if not save_path:
                save_path = os.path.join(desktop_dir, filename)

            if not save_path.lower().endswith('.png'):
                save_path += '.png'

            save_path = os.path.abspath(save_path)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            with open(save_path, 'wb') as f:
                f.write(image_bytes)

            # 导出成功后，自动唤起 Windows 资源管理器并高亮选中保存的文件
            try:
                subprocess.Popen(f'explorer /select,"{save_path}"')
            except Exception:
                pass

            return {'success': True, 'path': save_path}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}

def get_resource_path(relative_path):
    """
    获取静态资源在运行时的绝对路径。
    在 PyInstaller 单文件模式下，资源会被解压到 sys._MEIPASS 临时目录。
    """
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

def main():
    # 定位 HTML 页面路径
    html_file = get_resource_path('integrated_doc_stamplab.html')
    
    if not os.path.exists(html_file):
        print(f"错误：未能找到核心文件 {html_file}")
        return

    # 初始化原生 JS Bridge API
    api = DocumentApi()

    # 创建应用窗口，使用 Windows 原生 Edge WebView2 引擎
    window = webview.create_window(
        title='多格式文档审批与图章工作台 v1.0.0',
        url=html_file,
        js_api=api,
        width=1360,
        height=880,
        min_size=(1024, 680),
        text_select=True,
        zoomable=True
    )
    api.set_window(window)

    # 启动应用
    webview.start(debug=False)

if __name__ == '__main__':
    main()
