import requests
import json

# 测试 webhook 接口
def test_webhook():
    url = 'http://127.0.0.1:8888/webhook'
    payload = {"key": "test"}
    
    try:
        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=5)
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        print("测试成功！")
    except Exception as e:
        print(f"测试失败: {str(e)}")

if __name__ == '__main__':
    test_webhook()
