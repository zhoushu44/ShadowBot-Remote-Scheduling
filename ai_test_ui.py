import tkinter as tk
from tkinter import scrolledtext, messagebox
import requests
import json
import threading
from PIL import ImageGrab
import io
import base64

class AITestUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AI界面测试")
        self.root.geometry("800x600")
        
        # 创建界面元素
        self.create_widgets()
        
    def create_widgets(self):
        # 标题
        title_label = tk.Label(self.root, text="AI界面测试", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # 测试按钮
        self.test_button = tk.Button(self.root, text="点击测试", command=self.start_test, 
                                font=("Arial", 12), bg="#4CAF50", fg="white", 
                                padx=20, pady=10)
        self.test_button.pack(pady=10)
        
        # 进度条
        self.progress_label = tk.Label(self.root, text="", font=("Arial", 10))
        self.progress_label.pack(pady=5)
        
        # 结果显示区域
        result_label = tk.Label(self.root, text="测试结果：", font=("Arial", 12, "bold"))
        result_label.pack(pady=5)
        
        self.result_text = scrolledtext.ScrolledText(self.root, width=80, height=25, 
                                             font=("Arial", 10))
        self.result_text.pack(pady=10, padx=10)
        
        # 状态栏
        self.status_label = tk.Label(self.root, text="准备就绪", font=("Arial", 10), 
                               fg="blue")
        self.status_label.pack(pady=5)
        
    def start_test(self):
        # 禁用按钮，防止重复点击
        self.test_button.config(state=tk.DISABLED)
        
        # 清空结果区域
        self.result_text.delete(1.0, tk.END)
        
        # 在新线程中执行测试，避免界面卡死
        thread = threading.Thread(target=self.run_test)
        thread.daemon = True
        thread.start()
        
    def run_test(self):
        try:
            # 更新状态
            self.update_status("正在截图...")
            self.update_progress("●")
            self.append_result("开始测试...\n")
            
            # 截图
            screenshot = ImageGrab.grab()
            buffered = io.BytesIO()
            screenshot.save(buffered, format='JPEG', quality=85, optimize=True)
            base64_image = base64.b64encode(buffered.getvalue()).decode()
            
            self.append_result(f"截图成功，大小: {len(base64_image)} 字节\n")
            self.append_result(f"截图尺寸: {screenshot.size}\n")
            
            # 更新状态
            self.update_status("正在发送给AI...")
            self.update_progress("●●")
            self.append_result("正在发送给AI分析...\n")
            
            # 发送给AI
            url = 'http://127.0.0.1:8888/query_progress'
            response = requests.post(url, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                
                # 更新状态
                self.update_status("AI分析完成")
                self.update_progress("●●●")
                self.append_result("AI分析完成！\n\n")
                
                # 显示结果
                if 'ai_analysis' in result:
                    self.append_result(f"AI分析结果:\n{result['ai_analysis']}\n")
                else:
                    self.append_result("未收到AI分析结果\n")
                    
                if 'screenshot' in result:
                    self.append_result(f"\n截图数据: {len(result['screenshot'])} 字节\n")
                    
            else:
                self.update_status("请求失败")
                self.update_progress("●●✗")
                self.append_result(f"请求失败，状态码: {response.status_code}\n")
                self.append_result(f"响应内容: {response.text}\n")
                
        except requests.exceptions.Timeout:
            self.update_status("请求超时")
            self.update_progress("●●✗")
            self.append_result("请求超时，请检查网络连接或稍后重试\n")
        except Exception as e:
            self.update_status("测试失败")
            self.update_progress("●●✗")
            self.append_result(f"测试失败: {str(e)}\n")
        finally:
            # 重新启用按钮
            self.root.after(0, lambda: self.test_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.update_progress(""))
            
    def update_status(self, message):
        self.root.after(0, lambda: self.status_label.config(text=message))
        
    def update_progress(self, progress):
        self.root.after(0, lambda: self.progress_label.config(text=progress))
        
    def append_result(self, message):
        self.root.after(0, lambda: self.result_text.insert(tk.END, message))
        self.root.after(0, lambda: self.result_text.see(tk.END))

def main():
    root = tk.Tk()
    app = AITestUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()
