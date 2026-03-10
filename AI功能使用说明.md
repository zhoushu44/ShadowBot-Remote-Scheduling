# 查询进度功能使用说明

## 功能概述

新增了 AI 查询进度功能，可以通过 POST 请求查询当前屏幕状态，AI 会分析截图并返回进度信息。

## 新增功能

### 1. 桌面截图功能
- 自动截取当前屏幕
- 将截图转换为 base64 编码

### 2. AI API 调用
- 支持调用 OpenAI 兼容的 API（如 GPT-4 Vision）
- 将截图发送给 AI 进行分析
- 返回 AI 的分析结果

### 3. AI 配置界面
- 在主界面新增 "AI 配置" 按钮
- 可配置以下参数：
  - API URL：AI 服务的 API 地址
  - API Key：访问密钥
  - Model：使用的模型名称（如 gpt-4o, gpt-4-vision-preview）
  - 提示词：AI 分析时使用的提示词

### 4. 新增 API 接口

#### 查询进度接口
```
POST /query_progress
```

**请求示例：**
```bash
curl -X POST http://127.0.0.1:8888/query_progress
```

**响应示例：**
```json
{
  "code": 0,
  "msg": "查询成功",
  "screenshot": "iVBORw0KGgoAAAANSUhEUgAA...",
  "ai_analysis": "屏幕显示了一个进度条，当前进度为 75%..."
}
```

**响应字段说明：**
- `code`: 状态码（0=成功，1=失败）
- `msg`: 消息
- `screenshot`: base64 编码的截图（PNG 格式）
- `ai_analysis`: AI 的分析结果

## 使用步骤

### 1. 安装依赖
确保已安装以下 Python 库：
```bash
pip install Pillow requests
```

### 2. 配置 AI 参数
1. 启动程序
2. 点击主界面的 "AI 配置" 按钮
3. 填写以下信息：
   - API URL：例如 `https://api.openai.com/v1/chat/completions`
   - API Key：你的 OpenAI API Key
   - Model：例如 `gpt-4o` 或 `gpt-4-vision-preview`
   - 提示词：自定义 AI 分析的提示词
4. 点击 "保存配置"
5. 点击 "测试连接" 验证配置是否正确

### 3. 测试查询进度
**方法一：使用测试脚本**
```bash
python test_query_progress.py
```

**方法二：使用 curl**
```bash
curl -X POST http://127.0.0.1:8888/query_progress
```

**方法三：通过 FRP 远程访问**
```bash
curl -X POST http://117.72.35.239:6000/query_progress
```

### 4. 在程序中使用
```python
import requests

response = requests.post('http://127.0.0.1:8888/query_progress')
result = response.json()

if result['code'] == 0:
    print("AI 分析结果：")
    print(result['ai_analysis'])
```

## 配置示例

### OpenAI GPT-4 Vision
- API URL: `https://api.openai.com/v1/chat/completions`
- Model: `gpt-4o`
- 提示词: `请分析这张截图，描述当前屏幕上显示的内容和进度状态。`

### 国内兼容 API（如智谱 AI、通义千问等）
根据具体 API 文档填写相应的 URL 和参数。

## 注意事项

1. **API Key 安全**：API Key 会保存在 config.json 中，请勿泄露
2. **网络要求**：调用 AI API 需要网络连接
3. **超时设置**：默认超时时间为 30 秒，可根据需要调整
4. **费用**：使用 OpenAI 等 API 可能产生费用，请注意控制使用量
5. **截图质量**：截图为 PNG 格式，文件大小取决于屏幕分辨率

## 故障排除

### 问题：提示 "未安装 Pillow 库"
**解决方案：**
```bash
pip install Pillow
```

### 问题：提示 "未安装 requests 库"
**解决方案：**
```bash
pip install requests
```

### 问题：AI API 调用失败
**可能原因：**
1. API URL 错误
2. API Key 无效或过期
3. 网络连接问题
4. API 服务暂时不可用

**解决方案：**
1. 检查 API URL 是否正确
2. 验证 API Key 是否有效
3. 检查网络连接
4. 在 AI 配置窗口点击 "测试连接" 进行诊断

### 问题：连接超时
**可能原因：**
1. 网络延迟过高
2. AI API 响应慢
3. FRP 连接不稳定

**解决方案：**
1. 检查网络连接
2. 尝试使用本地地址测试
3. 检查 FRP 连接状态

## 原有功能保持不变

原有的 webhook 功能继续正常工作：
- POST `/webhook` 触发 BAT 脚本执行
- FRP 内网穿透功能
- BAT 目录设置
- 开机自启
- 测试连接工具

## 技术细节

### 截图实现
使用 `PIL.ImageGrab.grab()` 截取整个屏幕，保存为 PNG 格式，然后转换为 base64 编码。

### AI API 调用
使用 OpenAI Chat Completions API 格式，支持图片输入：
```json
{
  "model": "gpt-4o",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "提示词"
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/png;base64,{base64_image}"
          }
        }
      ]
    }
  ],
  "max_tokens": 1000
}
```

### 配置文件结构
```json
{
  "ai": {
    "api_url": "https://api.openai.com/v1/chat/completions",
    "api_key": "sk-xxx",
    "model": "gpt-4o",
    "prompt": "请分析这张截图，描述当前屏幕上显示的内容和进度状态。"
  }
}
```

## 更新日志

### v2.1 (2025-03-10)
- 新增：AI 查询进度功能
- 新增：桌面截图功能
- 新增：AI API 调用功能
- 新增：AI 配置界面
- 新增：`/query_progress` API 接口
- 改进：配置文件结构，增加 `ai` 配置项
