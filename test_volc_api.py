import requests
import json

# 测试火山引擎AI API
def test_volc_api():
    url = 'https://ark.cn-beijing.volces.com/api/v3/responses'
    headers = {
        'Authorization': 'Bearer 96d739dd-5f53-4a6d-b89d-1779f27be846',
        'Content-Type': 'application/json'
    }
    
    data = {
        "model": "doubao-seed-2-0-pro-260215",
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_image",
                        "image_url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/ark_demo_img_1.png"
                    },
                    {
                        "type": "input_text",
                        "text": "你看见了什么？"
                    }
                ]
            }
        ]
    }
    
    try:
        print("正在测试火山引擎AI API...")
        response = requests.post(url, headers=headers, json=data, timeout=30)
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            print("\nAPI测试成功！")
        else:
            print("\nAPI测试失败！")
            
    except Exception as e:
        print(f"测试失败: {str(e)}")

if __name__ == '__main__':
    test_volc_api()
