import requests
import json

# 测试webhook接口的查询功能
def test_webhook_query():
    url = 'http://127.0.0.1:8888/webhook'
    data = {"key": "查询"}
    
    try:
        print("正在发送查询请求到webhook接口...")
        response = requests.post(url, json=data, timeout=120)
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            print("\n测试成功！webhook接口已经支持查询功能！")
        else:
            print("\n测试失败！")
            
    except Exception as e:
        print(f"测试失败: {str(e)}")

if __name__ == '__main__':
    test_webhook_query()
