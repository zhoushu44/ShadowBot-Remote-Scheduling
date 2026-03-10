import requests
import json

# 测试服务是否正常运行
def test_service():
    url = 'http://127.0.0.1:8888/test'
    
    try:
        response = requests.get(url, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        print("测试成功！服务正常运行")
    except Exception as e:
        print(f"测试失败: {str(e)}")

if __name__ == '__main__':
    test_service()
