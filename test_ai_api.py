import requests
import json
import base64
from PIL import ImageGrab
import io
import traceback

# 测试AI API连接和图片识别
def test_ai_api():
    # 先截图
    print("正在截图...")
    try:
        screenshot = ImageGrab.grab()
        buffered = io.BytesIO()
        screenshot.save(buffered, format='JPEG', quality=85, optimize=True)
        base64_image = base64.b64encode(buffered.getvalue()).decode()
        print(f"截图成功，大小: {len(base64_image)} 字节")
        print(f"截图尺寸: {screenshot.size}")
    except Exception as e:
        print(f"截图失败: {str(e)}")
        print(f"详细错误: {traceback.format_exc()}")
        return
    
    # 测试AI API
    print("正在测试AI API...")
    url = 'http://127.0.0.1:8888/query_progress'
    
    try:
        print("发送请求到API...")
        response = requests.post(url, timeout=120)  # 增加超时时间到120秒
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            print("\nAPI测试成功！")
            result = response.json()
            if 'ai_analysis' in result:
                print(f"AI分析结果: {result['ai_analysis']}")
        else:
            print("\nAPI测试失败！")
    except requests.exceptions.Timeout:
        print(f"测试失败: 请求超时")
        print(f"详细错误: {traceback.format_exc()}")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        print(f"详细错误: {traceback.format_exc()}")

if __name__ == '__main__':
    test_ai_api()
