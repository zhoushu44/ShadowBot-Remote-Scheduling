import subprocess
import sys

# 自动安装 pyautogui
try:
    import pyautogui
except ImportError:
    print("正在安装 pyautogui...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyautogui", "opencv-python"])
    import pyautogui

import time

# 设置安全暂停时间（秒）
pyautogui.PAUSE = 0.5

# 检查命令行参数
if len(sys.argv) < 2:
    print("用法: python click_image.py <image_name>")
    print("例如: python click_image.py start.png")
    sys.exit(1)

# 获取目标图片文件名
target_image = sys.argv[1]

print(f"正在搜索：{target_image}")

try:
    # 在屏幕上查找图片
    location = pyautogui.locateOnScreen(target_image, confidence=0.7)
    
    # 如果没找到，尝试不同的置信度
    if not location:
        print("降低置信度重试...")
        location = pyautogui.locateOnScreen(target_image, confidence=0.6)
    
    if location:
        # 获取图片中心坐标
        center = pyautogui.center(location)
        click_x, click_y = center
        
        print(f"找到目标！坐标：({click_x}, {click_y})")
        print(f"区域大小：{location.width}x{location.height}")
        
        # 移动到目标位置并点击
        pyautogui.moveTo(click_x, click_y, duration=0.3)
        pyautogui.click()
        
        print("已点击!")
    else:
        print("未找到目标图片")
        print(f"提示：请确保 {target_image} 与屏幕上要点击的图标完全一致")
        
except FileNotFoundError:
    print(f"错误：找不到 {target_image} 文件")
    print(f"请先截取目标图标并保存为 {target_image}")
except Exception as e:
    import traceback
    print(f"发生错误：{e}")
    print(f"详细错误：{traceback.format_exc()}")
