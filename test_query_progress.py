import requests
import json

# 测试 query_progress 接口
def test_query_progress():
    url = 'http://127.0.0.1:8888/query_progress'
    
    try:
        response = requests.post(url, timeout=30)
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        print("测试成功！")
    except Exception as e:
        print(f"测试失败: {str(e)}")

if __name__ == '__main__':
    test_query_progress()
