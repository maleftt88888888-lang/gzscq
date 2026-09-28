import os
import sys
import webview

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

    # 创建应用窗口，使用 Windows 原生 Edge WebView2 引擎
    window = webview.create_window(
        title='多格式文档审批与图章工作台 v1.0.0',
        url=html_file,
        width=1360,
        height=880,
        min_size=(1024, 680),
        text_select=True,
        zoomable=True
    )

    # 启动应用
    webview.start(debug=False)

if __name__ == '__main__':
    main()
