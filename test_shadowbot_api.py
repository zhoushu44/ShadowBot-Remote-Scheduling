import requests
import json

# 测试影刀检测接口
def test_shadowbot_api():
    url = 'http://127.0.0.1:8888/check_shadowbot'
    
    try:
        response = requests.get(url, timeout=10)
        print(f"状态码: {response.status_code}")
        
        # 解析响应
        result = response.json()
        print(f"响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if result['code'] == 0:
            print(f"\n影刀运行状态: {'运行中' if result['running'] else '未运行'}")
            print(f"检测到 {result['process_count']} 个影刀进程")
            
            if result['processes']:
                print("\n进程详情:")
                for i, proc in enumerate(result['processes'], 1):
                    print(f"\n[{i}] 进程信息")
                    print(f"  PID: {proc['pid']}")
                    print(f"  名称: {proc['name']}")
                    print(f"  路径: {proc['exe_path']}")
                    print(f"  CPU 使用率: {proc['cpu_percent']}%")
                    print(f"  内存使用: {proc['memory_mb']} MB")
                    print(f"  状态: {proc['status']}")
        else:
            print(f"\n检测失败: {result['msg']}")
            
        print("\n测试成功！")
    except Exception as e:
        print(f"测试失败: {str(e)}")

if __name__ == '__main__':
    test_shadowbot_api()
