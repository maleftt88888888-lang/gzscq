import os
import sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# 确保 Windows 终端中文正常输出
sys.stdout.reconfigure(encoding='utf-8')

def create_sample_image(path="test_sample.jpg"):
    """自动生成一张测试图片用于算法演示"""
    img = np.full((300, 600, 3), (245, 245, 245), dtype=np.uint8)
    
    # 绘制背景装饰框
    cv2.rectangle(img, (20, 20), (580, 280), (210, 210, 210), 2)
    cv2.rectangle(img, (25, 25), (575, 275), (230, 230, 230), 1)
    
    # 转换到 PIL 绘制原测试文字
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    
    try:
        font_large = ImageFont.truetype("msyh.ttc", 26)
        font_small = ImageFont.truetype("msyh.ttc", 18)
    except IOError:
        font_large = font_small = ImageFont.load_default()
        
    draw.text((60, 60), "活动出入证模板 (测试图)", font=font_large, fill=(30, 58, 138))
    draw.text((60, 130), "姓名：李晓明", font=font_small, fill=(50, 50, 50))
    draw.text((60, 180), "编号：NO.2026099", font=font_small, fill=(70, 70, 70))
    
    result_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    cv2.imwrite(path, result_bgr)
    print(f"已生成演示原图: {os.path.abspath(path)}")
    return path


def sample_average_color(image_bgr, x, y, radius=3):
    """通用取色算法：计算 (x, y) 坐标周围半径内的平均 RGB 颜色"""
    h, w, _ = image_bgr.shape
    x1, x2 = max(0, x - radius), min(w, x + radius + 1)
    y1, y2 = max(0, y - radius), min(h, y + radius + 1)
    
    region = image_bgr[y1:y2, x1:x2]
    avg_b = int(np.mean(region[:, :, 0]))
    avg_g = int(np.mean(region[:, :, 1]))
    avg_r = int(np.mean(region[:, :, 2]))
    return (avg_r, avg_g, avg_b)


def inpaint_text_region(image_bgr, rect):
    """图像修复算法：使用 OpenCV Telea 算法抹除文字区域并还原背景"""
    x, y, w, h = rect
    mask = np.zeros(image_bgr.shape[:2], dtype=np.uint8)
    mask[y:y+h, x:x+w] = 255
    inpainted = cv2.inpaint(image_bgr, mask, inpaintRadius=4, flags=cv2.INPAINT_TELEA)
    return inpainted


def render_text_on_image(image_bgr, text, position, font_name, font_size, text_color):
    """使用 PIL 高质量抗锯齿渲染新文本"""
    img_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb)
    draw = ImageDraw.Draw(pil_img)
    
    try:
        font = ImageFont.truetype(font_name, font_size)
    except IOError:
        font = ImageFont.load_default()
        
    draw.text(position, text, font=font, fill=text_color)
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def main():
    print("======================================================")
    print("正在运行图像文字擦除与重绘算法演示...")
    print("======================================================")
    
    input_img_path = "test_sample.jpg"
    output_img_path = "test_output.jpg"
    
    # 1. 准备测试原图
    create_sample_image(input_img_path)
    img = cv2.imread(input_img_path)
    
    # 2. 确定要修改的区域：例如修改“李晓明”位置 (x=115, y=125, w=90, h=30)
    name_rect = (115, 125, 90, 30)
    
    # 3. 取色：从原文字区域采样颜色
    text_color = sample_average_color(img, 130, 138, radius=2)
    print(f"[1] 自动采样得到的原文字颜色 (RGB): {text_color}")
    
    # 4. 抹除旧文字
    print("[2] 正在执行背景修复 (Telea Inpainting)...")
    cleaned_img = inpaint_text_region(img, name_rect)
    
    # 5. 绘制新文字（例如替换为“王大力”）
    new_name = "王大力"
    print(f"[3] 正在将文字替换为: '{new_name}' ...")
    final_img = render_text_on_image(
        image_bgr=cleaned_img,
        text=new_name,
        position=(name_rect[0], name_rect[1] + 3),
        font_name="msyh.ttc", # 微软雅黑
        font_size=18,
        text_color=text_color
    )
    
    # 6. 保存结果
    cv2.imwrite(output_img_path, final_img)
    print(f"[4] 处理完成！输出文件: {os.path.abspath(output_img_path)}")
    print("======================================================")

if __name__ == "__main__":
    main()
