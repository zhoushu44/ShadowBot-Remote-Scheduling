import pyautogui
import time

# 设置安全暂停时间（秒）
pyautogui.PAUSE = 0.5

# 目标图片文件名
target_image = "Pause.png"

print(f"正在搜索：{target_image}")

try:
    # 在屏幕上查找图片
    location = pyautogui.locateOnScreen(target_image, confidence=0.8)
    
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
        print("提示：请确保 Pause.png 与屏幕上要点击的图标完全一致")
        
except FileNotFoundError:
    print(f"错误：找不到 {target_image} 文件")
    print("请先截取目标图标并保存为 Pause.png")
except Exception as e:
    import traceback
    print(f"发生错误：{e}")
    print(f"详细错误：{traceback.format_exc()}")
