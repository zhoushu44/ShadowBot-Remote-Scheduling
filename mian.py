#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Webhook 关键字 → 同文件夹下同名 bat 执行器

使用 PyQt5 重新设计界面
- 主窗口：BAT 目录设置、FRP 设置按钮、测试连接按钮、生成 curl 按钮
- FRP 设置窗口：独立窗口，支持多配置管理（TCP/UDP）
- 测试连接窗口：独立窗口，详细错误信息
- 服务自动启动（后台运行）
"""
import subprocess, logging, os, sys, json, threading, traceback, queue, random, string, time, base64, io
from flask import Flask, request, jsonify

try:
    from werkzeug.serving import make_server
except Exception:
    make_server = None

try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                                  QLabel, QLineEdit, QPushButton, QTextEdit, QListWidget, QDialog,
                                  QRadioButton, QButtonGroup, QMessageBox, QFileDialog, QCheckBox,
                                  QGroupBox, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView)
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject
    from PyQt5.QtGui import QFont, QClipboard
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    print('错误：未安装 PyQt5，请运行: pip install PyQt5')
    sys.exit(1)

# 尝试导入 requests，如果失败则使用 urllib
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# 尝试导入 PIL 用于截图
try:
    from PIL import ImageGrab
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print('警告：未安装 PIL，无法使用截图功能，请运行: pip install Pillow')

# ========== 默认配置 ==========
DEFAULT_BAT_FOLDER = r'D:\WebhookBats'
DEFAULT_LISTEN_PORT = 8888
# ===============================

CONFIG_PATH = os.path.join(os.path.dirname(sys.argv[0]), 'config.json')

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            logging.exception('读取配置失败，使用默认配置')
    return {
        'bat_folder': DEFAULT_BAT_FOLDER,
        'listen_port': DEFAULT_LISTEN_PORT,
        'autostart': False,
        'frp': {
            'frpc_path': '',
            'configs': {}
        },
        'ai': {
            'api_url': '',
            'api_key': '',
            'model': '',
            'prompt': '请分析这张截图，描述当前屏幕上显示的内容和进度状态。'
        }
    }

def save_config(cfg):
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        logging.exception('保存配置失败')

config = load_config()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

def get_bat_folder() -> str:
    return config.get('bat_folder') or DEFAULT_BAT_FOLDER

def get_listen_port() -> int:
    p = config.get('listen_port')
    try:
        return int(p)
    except Exception:
        return DEFAULT_LISTEN_PORT

def find_bat(key: str) -> str:
    """返回文件夹里与 key 完全同名（忽略大小写）的 bat 路径"""
    folder = get_bat_folder()
    if not folder or not os.path.isdir(folder):
        return ''
    try:
        for f in os.listdir(folder):
            if f.lower() == f'{key}.bat'.lower():
                return os.path.join(folder, f)
    except Exception:
        pass
    return ''

def run_bat(path: str):
    try:
        subprocess.Popen(['cmd', '/c', path], cwd=os.path.dirname(path))
        logging.info('bat 已启动：%s', path)
    except Exception:
        logging.error('启动失败：\n%s', traceback.format_exc())

def capture_screenshot() -> str:
    """截图并返回 base64 编码的图片"""
    if not HAS_PIL:
        raise Exception('未安装 Pillow 库，无法截图')
    try:
        screenshot = ImageGrab.grab()
        buffered = io.BytesIO()
        screenshot.save(buffered, format='JPEG', quality=85, optimize=True)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        logging.info(f'截图成功，大小: {len(img_str)} 字节')
        return img_str
    except Exception as e:
        logging.error('截图失败：\n%s', traceback.format_exc())
        raise Exception(f'截图失败: {str(e)}')

def extract_shadowbot_info(ai_result: str) -> dict:
    """从AI分析结果中提取影刀运行监控面板的关键信息"""
    try:
        # 初始化默认值
        info = {
            'project_name': '未命名的应用',
            'running_time': '未知',
            'status': '未知'
        }
        
        # 提取项目名称
        if '未命名的应用' in ai_result:
            info['project_name'] = '未命名的应用'
        elif '项目' in ai_result and '：' in ai_result:
            # 尝试提取项目名称
            lines = ai_result.split('\n')
            for line in lines:
                if '项目' in line and '：' in line:
                    parts = line.split('：')
                    if len(parts) >= 2:
                        info['project_name'] = parts[1].strip()
                        break
        
        # 提取运行时长
        if '运行时长' in ai_result or '运行了' in ai_result or '累计运行' in ai_result:
            import re
            # 查找时间格式，如 00:00:34 或 34秒
            time_pattern = r'(\d+:\d+:\d+)|(\d+)\s*秒'
            time_match = re.search(time_pattern, ai_result)
            if time_match:
                if ':' in time_match.group():
                    # 格式：00:00:34
                    parts = time_match.group().split(':')
                    if len(parts) == 3:
                        total_seconds = int(parts[0]) * 60 + int(parts[1])
                    elif len(parts) == 2:
                        total_seconds = int(parts[0]) * 60 + int(parts[1])
                    else:
                        total_seconds = int(parts[0])
                    minutes = total_seconds // 60
                    seconds = total_seconds % 60
                    info['running_time'] = f'{minutes}分{seconds}秒'
                else:
                    # 格式：34秒
                    total_seconds = int(time_match.group())
                    minutes = total_seconds // 60
                    seconds = total_seconds % 60
                    info['running_time'] = f'{minutes}分{seconds}秒'
        
        # 提取运行状态
        if '等待' in ai_result:
            info['status'] = '等待'
        elif '运行中' in ai_result:
            info['status'] = '运行中'
        elif '执行' in ai_result:
            info['status'] = '执行中'
        
        return info
        
    except Exception as e:
        logging.error(f'解析影刀信息失败：{str(e)}')
        return {
            'project_name': '未知',
            'running_time': '未知',
            'status': '未知'
        }

def call_ai_api(base64_image: str) -> str:
    """调用 AI API 分析截图"""
    ai_config = config.get('ai', {})
    api_key = ai_config.get('api_key', '').strip()
    model = ai_config.get('model', '').strip()
    prompt = ai_config.get('prompt', '分析屏幕内容').strip()

    if not api_key or not model:
        raise Exception('AI 配置不完整，请先配置 API Key 和 Model')

    if not HAS_REQUESTS:
        raise Exception('未安装 requests 库，无法调用 AI API')

    # 使用豆包AI API URL
    api_url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    def try_request(data, timeout, max_retries=3):
        for attempt in range(max_retries):
            try:
                response = requests.post(api_url, headers=headers, json=data, timeout=timeout)
                response.raise_for_status()
                result = response.json()
                
                # 打印响应内容，以便调试
                logging.info(f'AI API 响应内容: {json.dumps(result, ensure_ascii=False)}')
                
                # 处理豆包AI API的响应格式
                if 'choices' in result and len(result['choices']) > 0:
                    return result['choices'][0]['message']['content']
                
                # 处理火山引擎API的响应格式
                if 'output' in result:
                    outputs = result.get('output', [])
                    for item in outputs:
                        if item.get('type') == 'message' and item.get('role') == 'assistant':
                            content = item.get('content', [])
                            for content_item in content:
                                if content_item.get('type') == 'output_text':
                                    return content_item.get('text', '')
                    # 如果没有找到message类型的输出，尝试其他类型
                    for item in outputs:
                        if 'content' in item:
                            content = item.get('content', [])
                            for content_item in content:
                                if content_item.get('type') == 'output_text':
                                    return content_item.get('text', '')
                
                # 检查其他可能的响应格式
                if 'result' in result:
                    return result['result']
                elif 'text' in result:
                    return result['text']
                
                raise Exception('AI API 返回格式异常')
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    logging.warning(f'请求超时，重试 {attempt + 1}/{max_retries}...')
                    time.sleep(2)
                else:
                    raise
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 500:
                    raise
                else:
                    raise
            except Exception as e:
                if attempt < max_retries - 1:
                    logging.warning(f'请求失败，重试 {attempt + 1}/{max_retries}...')
                    time.sleep(2)
                else:
                    raise

    try:
        # 使用豆包AI API的请求格式
        data = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 2048
        }

        return try_request(data, timeout=90)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 500:
            logging.warning('图片 API 不可用，尝试使用纯文本模式')
            try:
                data = {
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": f'{prompt}\n\n注意：当前无法发送截图，请根据上下文提供一般性的进度分析建议。'
                        }
                    ],
                    "max_tokens": 2048
                }
                return try_request(data, timeout=60)
            except Exception as fallback_error:
                raise Exception(f'图片 API 和文本模式均失败: {str(fallback_error)}')
        else:
            raise Exception(f'AI API 请求失败: {str(e)}')
    except requests.exceptions.Timeout:
        raise Exception('AI API 请求超时，请检查网络连接或稍后重试')
    except requests.exceptions.RequestException as e:
        raise Exception(f'AI API 请求失败: {str(e)}')
    except Exception as e:
        logging.error('AI API 调用失败：\n%s', traceback.format_exc())
        raise Exception(f'AI API 调用失败: {str(e)}')

@app.route('/webhook', methods=['POST'])
def webhook():
    key = ''
    if request.is_json:
        data = request.get_json(silent=True) or {}
        key = data.get('key', '')
    if not key:
        key = request.form.get('key', '') or request.args.get('key', '')

    if not key:
        return jsonify({"code": 2, "msg": "缺少 key 字段"}), 400

    # 如果key为"查询"，则返回AI分析测试结果
    if key == '查询':
        try:
            logging.info('收到查询请求，开始AI分析')
            
            base64_image = capture_screenshot()
            logging.info('截图成功，正在调用 AI API...')
            
            ai_result = call_ai_api(base64_image)
            logging.info('AI 分析完成')
            
            response = app.response_class(
                json.dumps({
                    "code": 0,
                    "msg": "查询成功",
                    "screenshot": base64_image,
                    "ai_analysis": ai_result
                }, ensure_ascii=False),
                mimetype='application/json'
            )
            return response, 200
            
        except Exception as e:
            logging.error('查询进度失败：\n%s', traceback.format_exc())
            return jsonify({
                "code": 1,
                "msg": f"查询失败: {str(e)}"
            }), 500
    
    # 否则触发BAT文件执行
    bat_path = find_bat(key)
    if not bat_path:
        return jsonify({"code": 3, "msg": f"未找到 {key}.bat"}), 404

    run_bat(bat_path)
    return jsonify({"code": 0, "msg": f"{key}.bat 已触发"}), 200

@app.route('/query_progress', methods=['POST'])
def query_progress():
    """查询进度：截图并发送给 AI 分析"""
    try:
        logging.info('收到查询进度请求')
        
        base64_image = capture_screenshot()
        logging.info('截图成功，正在调用 AI API...')
        
        ai_result = call_ai_api(base64_image)
        logging.info('AI 分析完成')
        
        response = app.response_class(
            json.dumps({
                "code": 0,
                "msg": "查询成功",
                "screenshot": base64_image,
                "ai_analysis": ai_result
            }, ensure_ascii=False),
            mimetype='application/json'
        )
        return response, 200
        
    except Exception as e:
        logging.error('查询进度失败：\n%s', traceback.format_exc())
        return jsonify({
            "code": 1,
            "msg": f"查询失败: {str(e)}"
        }), 500

@app.route('/test', methods=['GET'])
def test():
    """测试接口：验证服务是否正常运行"""
    try:
        logging.info('收到测试请求')
        return jsonify({
            "code": 0,
            "msg": "服务正常运行",
            "timestamp": time.time(),
            "service": "Webhook Bat Executor"
        }), 200
    except Exception as e:
        logging.error('测试接口失败：\n%s', traceback.format_exc())
        return jsonify({
            "code": 1,
            "msg": f"测试失败: {str(e)}"
        }), 500


class ServerManager:
    """服务管理器 - 自动启动，不提供 GUI 控制"""
    def __init__(self):
        self._server = None
        self._thread = None
        self._auto_start()

    def _auto_start(self):
        """自动启动服务"""
        port = get_listen_port()
        if make_server is None:
            def target():
                app.run(host='0.0.0.0', port=port, threaded=True, use_reloader=False)
            self._thread = threading.Thread(target=target, daemon=True)
            self._thread.start()
            self._server = 'builtin'
            logging.info('服务自动启动（内置），端口 %s，bat 目录：%s', port, get_bat_folder())
            return

        http_server = make_server('0.0.0.0', port, app)
        self._server = http_server
        def serve_forever():
            logging.info('服务自动启动，端口 %s，bat 目录：%s', port, get_bat_folder())
            http_server.serve_forever()
        self._thread = threading.Thread(target=serve_forever, daemon=True)
        self._thread.start()

    def is_running(self) -> bool:
        return self._server is not None

    def stop(self):
        if not self.is_running():
            return
        if self._server == 'builtin':
            self._server = None
            self._thread = None
            logging.info('服务标记为停止（内置模式）')
            return
        try:
            self._server.shutdown()
            logging.info('服务已停止')
        except Exception:
            logging.error('停止失败：\n%s', traceback.format_exc())
        finally:
            self._server = None
            self._thread = None


def set_autostart(enabled: bool):
    """Windows 开机自启"""
    try:
        import winreg
    except Exception:
        logging.warning('无法控制开机自启（winreg 不可用）')
        return False

    app_name = 'WebhookBatService'
    if getattr(sys, 'frozen', False):
        exe_path = sys.executable
        cmd = f'"{exe_path}"'
    else:
        exe_path = sys.executable
        script_path = os.path.abspath(sys.argv[0])
        cmd = f'"{exe_path}" "{script_path}"'

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Run",
                            0, winreg.KEY_ALL_ACCESS) as key:
            if enabled:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
        return True
    except Exception:
        logging.error('设置开机自启失败：\n%s', traceback.format_exc())
        return False


def generate_random_name(length=8):
    """生成随机名字"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


class FRPConfigManager:
    """管理多个 FRP 配置"""
    def __init__(self, config_ref: dict):
        self._config_ref = config_ref
        self._processes = {}
        self._log_queues = {}

    def get_frpc_path(self) -> str:
        frp_cfg = self._config_ref.get('frp') or {}
        return (frp_cfg.get('frpc_path') or '').strip()

    def set_frpc_path(self, path: str):
        if 'frp' not in self._config_ref:
            self._config_ref['frp'] = {}
        self._config_ref['frp']['frpc_path'] = path
        if 'configs' not in self._config_ref['frp']:
            self._config_ref['frp']['configs'] = {}

    def get_configs(self) -> dict:
        frp_cfg = self._config_ref.get('frp') or {}
        return frp_cfg.get('configs') or {}

    def save_config_item(self, name: str, cfg: dict):
        if 'frp' not in self._config_ref:
            self._config_ref['frp'] = {}
        if 'configs' not in self._config_ref['frp']:
            self._config_ref['frp']['configs'] = {}
        self._config_ref['frp']['configs'][name] = cfg.copy()
        save_config(self._config_ref)

    def delete_config_item(self, name: str):
        configs = self.get_configs()
        if name in configs:
            self.stop_config(name)
            del configs[name]
            if 'frp' in self._config_ref:
                self._config_ref['frp']['configs'] = configs
            save_config(self._config_ref)

    def _build_ini(self, cfg: dict) -> str:
        server_addr = cfg.get('server_addr', '').strip()
        server_port = int(cfg.get('server_port') or 7000)
        token = (cfg.get('token') or '').strip()
        cfg_type = cfg.get('type', 'tcp').lower()
        cfg_name = cfg.get('name', 'default')
        local_ip = cfg.get('local_ip', '127.0.0.1').strip()
        local_port = int(cfg.get('local_port') or 8888)
        remote_port = int(cfg.get('remote_port') or 0)

        if not server_addr or remote_port <= 0:
            raise ValueError('FRP 配置不完整（server_addr/remote_port）')

        lines = ['[common]', f'server_addr = {server_addr}', f'server_port = {server_port}']
        if token:
            lines.append(f'token = {token}')
        lines += [
            '', f'[{cfg_name}]', f'type = {cfg_type}',
            f'local_ip = {local_ip}', f'local_port = {local_port}',
            f'remote_port = {remote_port}'
        ]
        return "\n".join(lines)

    def start_config(self, name: str):
        if name in self._processes and self._processes[name]['proc'].poll() is None:
            return

        configs = self.get_configs()
        if name not in configs:
            raise ValueError(f'配置 {name} 不存在')

        frpc_path = self.get_frpc_path()
        if not frpc_path or not os.path.isfile(frpc_path):
            raise FileNotFoundError('未找到 frpc 可执行文件，请先选择 frpc.exe')

        cfg = configs[name]
        ini_content = self._build_ini(cfg)
        import tempfile
        fd, tmp_path = tempfile.mkstemp(prefix=f'frpc_{name}_', suffix='.ini')
        os.close(fd)
        with open(tmp_path, 'w', encoding='utf-8') as f:
            f.write(ini_content)

        log_queue = queue.Queue()
        try:
            proc = subprocess.Popen(
                [frpc_path, '-c', tmp_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW,
                text=True,
                bufsize=1
            )
            self._processes[name] = {
                'proc': proc,
                'ini_path': tmp_path,
                'log_queue': log_queue
            }
            self._log_queues[name] = log_queue

            def read_log():
                if proc.stdout:
                    for line in iter(proc.stdout.readline, ''):
                        if not line:
                            break
                        log_queue.put(f"[{name}] {line.rstrip()}")
                    log_queue.put(f"[{name}] 进程已退出")
            threading.Thread(target=read_log, daemon=True).start()

            logging.info('frpc 配置 %s 已启动，配置：%s', name, tmp_path)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    def stop_config(self, name: str):
        if name not in self._processes:
            return
        proc_info = self._processes[name]
        try:
            proc_info['proc'].terminate()
            try:
                proc_info['proc'].wait(timeout=5)
            except Exception:
                proc_info['proc'].kill()
        finally:
            if os.path.exists(proc_info['ini_path']):
                try:
                    os.remove(proc_info['ini_path'])
                except Exception:
                    pass
            if name in self._log_queues:
                del self._log_queues[name]
            del self._processes[name]

    def stop_all(self):
        for name in list(self._processes.keys()):
            self.stop_config(name)

    def is_config_running(self, name: str) -> bool:
        if name not in self._processes:
            return False
        proc = self._processes[name]['proc']
        return proc.poll() is None

    def get_log_queue(self, name: str) -> queue.Queue:
        return self._log_queues.get(name, queue.Queue())


class TestConnectionThread(QThread):
    """测试连接的线程"""
    result_signal = pyqtSignal(str)

    def __init__(self, url: str, key: str):
        super().__init__()
        self.url = url
        self.key = key

    def run(self):
        try:
            payload = {"key": self.key}
            self.result_signal.emit(f"正在测试连接: {self.url}\n")
            self.result_signal.emit(f"发送数据: {json.dumps(payload, ensure_ascii=False)}\n\n")

            # 如果是FRP地址（不是127.0.0.1），先检查本地服务
            if '127.0.0.1' not in self.url and 'localhost' not in self.url.lower():
                self.result_signal.emit(f"检测到FRP地址，先检查本地服务...\n")
                local_url = f'http://127.0.0.1:{get_listen_port()}/webhook'
                if HAS_REQUESTS:
                    try:
                        check_response = requests.post(
                            local_url,
                            json=payload,
                            headers={'Content-Type': 'application/json'},
                            timeout=5,
                            verify=False
                        )
                        self.result_signal.emit(f"✅ 本地服务正常（端口 {get_listen_port()}）\n")
                        self.result_signal.emit(f"   状态码: {check_response.status_code}\n\n")
                    except Exception as local_e:
                        self.result_signal.emit(f"⚠️ 本地服务检查失败: {str(local_e)}\n")
                        self.result_signal.emit(f"   请确认本地服务在端口 {get_listen_port()} 上运行\n\n")
                else:
                    self.result_signal.emit(f"⚠️ 无法检查本地服务（缺少 requests 库）\n\n")

            if HAS_REQUESTS:
                # 使用 requests 库
                try:
                    import urllib3
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # 禁用SSL警告
                except ImportError:
                    pass  # urllib3 不可用时忽略
                
                start_time = time.time()
                try:
                    # 禁用代理，直接连接
                    session = requests.Session()
                    session.trust_env = False  # 不信任环境变量中的代理设置
                    
                    response = session.post(
                        self.url,
                        json=payload,
                        headers={'Content-Type': 'application/json'},
                        timeout=(10, 60),  # (连接超时, 读取超时) - 增加到60秒
                        verify=False,  # 如果是 HTTPS 但不信任证书
                        allow_redirects=True,
                        proxies={}  # 明确禁用代理
                    )
                    elapsed = time.time() - start_time

                    self.result_signal.emit(f"✅ 连接成功！\n")
                    self.result_signal.emit(f"状态码: {response.status_code}\n")
                    self.result_signal.emit(f"响应时间: {elapsed:.2f} 秒\n")
                    self.result_signal.emit(f"响应头: {dict(response.headers)}\n")
                    self.result_signal.emit(f"响应内容: {response.text}\n")
                    if response.status_code == 200:
                        self.result_signal.emit(f"\n✅ 测试成功：webhook 已触发\n")
                    else:
                        self.result_signal.emit(f"\n⚠️ 警告：状态码不是 200\n")
                except requests.exceptions.Timeout as e:
                    self.result_signal.emit(f"\n❌ 连接超时\n")
                    self.result_signal.emit(f"超时类型: {type(e).__name__}\n")
                    self.result_signal.emit(f"错误详情: {str(e)}\n\n")
                    
                    # 检查是否是ReadTimeout（读取超时）
                    if 'Read timeout' in str(e) or 'read timeout' in str(e).lower():
                        self.result_signal.emit(f"⚠️ 这是读取超时（ReadTimeout），说明：\n")
                        self.result_signal.emit(f"  - 连接已建立（FRP 连接正常）\n")
                        self.result_signal.emit(f"  - 但服务器未在60秒内返回响应\n\n")
                        self.result_signal.emit(f"可能原因：\n")
                        self.result_signal.emit(f"  1. ⚠️ 本地端口配置错误！\n")
                        self.result_signal.emit(f"     - 检查FRP配置中的'本地端口'是否为 {get_listen_port()}（webhook服务端口）\n")
                        self.result_signal.emit(f"     - 当前配置可能是3389（RDP端口）或其他错误端口\n")
                        self.result_signal.emit(f"  2. 本地webhook服务未启动或响应慢\n")
                        self.result_signal.emit(f"  3. 本地服务处理请求时间过长\n")
                        self.result_signal.emit(f"  4. 网络延迟导致响应超时\n\n")
                        self.result_signal.emit(f"解决方案：\n")
                        self.result_signal.emit(f"  1. 在FRP设置中，将'本地端口'改为 {get_listen_port()}\n")
                        self.result_signal.emit(f"  2. 确认本地服务在端口 {get_listen_port()} 上运行\n")
                        self.result_signal.emit(f"  3. 先用本地地址测试: http://127.0.0.1:{get_listen_port()}/webhook\n")
                    else:
                        self.result_signal.emit(f"可能原因：\n")
                        self.result_signal.emit(f"  1. 服务器未启动或端口错误\n")
                        self.result_signal.emit(f"  2. FRP 配置未启动或连接失败\n")
                        self.result_signal.emit(f"  3. 防火墙阻止连接\n")
                        self.result_signal.emit(f"  4. 网络不通或延迟过高（超过10秒连接超时）\n")
                        self.result_signal.emit(f"  5. FRP 服务端网络不稳定\n")
                except requests.exceptions.ConnectionError as e:
                    self.result_signal.emit(f"\n❌ 连接失败\n")
                    self.result_signal.emit(f"错误类型: {type(e).__name__}\n")
                    self.result_signal.emit(f"错误详情: {str(e)}\n\n")
                    # 提取更详细的错误信息
                    if hasattr(e, 'args') and e.args:
                        for arg in e.args:
                            self.result_signal.emit(f"  错误参数: {arg}\n")
                    self.result_signal.emit(f"\n可能原因：\n")
                    self.result_signal.emit(f"  1. 无法解析域名或 IP 地址错误\n")
                    self.result_signal.emit(f"  2. 目标端口未开放或被防火墙阻止\n")
                    self.result_signal.emit(f"  3. FRP 服务端未运行或配置错误\n")
                    self.result_signal.emit(f"  4. FRP 客户端未连接成功（检查FRP日志）\n")
                    self.result_signal.emit(f"  5. 本地服务未启动（端口 {get_listen_port()}）\n")
                    self.result_signal.emit(f"  6. 目标服务器拒绝连接\n")
                    self.result_signal.emit(f"  7. 网络路由问题\n")
                    self.result_signal.emit(f"\n调试建议：\n")
                    self.result_signal.emit(f"  - 检查FRP客户端日志是否显示连接成功\n")
                    self.result_signal.emit(f"  - 尝试在浏览器中访问: {self.url}\n")
                    self.result_signal.emit(f"  - 检查防火墙是否允许该端口\n")
                    self.result_signal.emit(f"  - 确认FRP服务端配置正确\n")
                except requests.exceptions.RequestException as e:
                    self.result_signal.emit(f"\n❌ 请求异常\n")
                    self.result_signal.emit(f"错误类型: {type(e).__name__}\n")
                    self.result_signal.emit(f"错误信息: {str(e)}\n")
                    self.result_signal.emit(f"详细错误:\n{traceback.format_exc()}\n")
            else:
                # 使用 urllib（备用方案）
                import urllib.request
                import urllib.parse
                start_time = time.time()
                try:
                    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
                    req = urllib.request.Request(
                        self.url,
                        data=data,
                        headers={'Content-Type': 'application/json'}
                    )
                    with urllib.request.urlopen(req, timeout=30) as response:
                        elapsed = time.time() - start_time
                        response_text = response.read().decode('utf-8')
                        self.result_signal.emit(f"✅ 连接成功！\n")
                        self.result_signal.emit(f"状态码: {response.getcode()}\n")
                        self.result_signal.emit(f"响应时间: {elapsed:.2f} 秒\n")
                        self.result_signal.emit(f"响应内容: {response_text}\n")
                        if response.getcode() == 200:
                            self.result_signal.emit(f"\n✅ 测试成功：webhook 已触发\n")
                        else:
                            self.result_signal.emit(f"\n⚠️ 警告：状态码不是 200\n")
                except urllib.error.URLError as e:
                    self.result_signal.emit(f"\n❌ 连接失败\n")
                    self.result_signal.emit(f"错误详情：{str(e)}\n\n")
                    self.result_signal.emit(f"可能原因：\n")
                    self.result_signal.emit(f"  1. 无法解析域名或 IP 地址错误\n")
                    self.result_signal.emit(f"  2. 目标端口未开放或被防火墙阻止\n")
                    self.result_signal.emit(f"  3. FRP 服务端未运行或配置错误\n")
                    self.result_signal.emit(f"  4. FRP 客户端未连接成功\n")
                    self.result_signal.emit(f"  5. 本地服务未启动（端口 {get_listen_port()}）\n")
                except Exception as e:
                    self.result_signal.emit(f"\n❌ 未知错误\n")
                    self.result_signal.emit(f"错误信息: {str(e)}\n")
                    self.result_signal.emit(f"详细错误: {traceback.format_exc()}\n")

        except Exception as e:
            self.result_signal.emit(f"\n❌ 未知错误\n")
            self.result_signal.emit(f"错误信息: {str(e)}\n")
            self.result_signal.emit(f"详细错误: {traceback.format_exc()}\n")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.server = ServerManager()  # 自动启动服务
        self.frp_manager = FRPConfigManager(config)
        self.frp_window = None
        self.test_window = None
        self.curl_window = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Webhook → 同名 BAT 执行器')
        self.setGeometry(100, 100, 700, 400)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # BAT 目录
        folder_group = QGroupBox('BAT 目录设置')
        folder_layout = QHBoxLayout()
        folder_label = QLabel('bat 目录：')
        self.folder_edit = QLineEdit(get_bat_folder())
        self.folder_edit.setReadOnly(True)
        browse_btn = QPushButton('浏览...')
        browse_btn.clicked.connect(self.browse_folder)
        folder_layout.addWidget(folder_label)
        folder_layout.addWidget(self.folder_edit)
        folder_layout.addWidget(browse_btn)
        folder_group.setLayout(folder_layout)
        layout.addWidget(folder_group)

        # 开机自启
        autostart_group = QGroupBox('系统设置')
        autostart_layout = QHBoxLayout()
        self.autostart_check = QCheckBox('开机自启')
        self.autostart_check.setChecked(bool(config.get('autostart')))
        apply_btn = QPushButton('应用')
        apply_btn.clicked.connect(self.apply_autostart)
        autostart_layout.addWidget(self.autostart_check)
        autostart_layout.addWidget(apply_btn)
        autostart_layout.addStretch()
        autostart_group.setLayout(autostart_layout)
        layout.addWidget(autostart_group)

        # FRP 状态和按钮
        frp_group = QGroupBox('FRP 内网穿透')
        frp_layout = QHBoxLayout()
        self.frp_status_label = QLabel('未连接')
        self.frp_status_label.setStyleSheet("color: red; font-weight: bold;")
        frp_settings_btn = QPushButton('FRP 设置')
        frp_settings_btn.clicked.connect(self.open_frp_settings)
        frp_layout.addWidget(QLabel('状态：'))
        frp_layout.addWidget(self.frp_status_label)
        frp_layout.addStretch()
        frp_layout.addWidget(frp_settings_btn)
        frp_group.setLayout(frp_layout)
        layout.addWidget(frp_group)

        # AI 设置
        ai_group = QGroupBox('AI 设置')
        ai_layout = QHBoxLayout()
        ai_settings_btn = QPushButton('AI 配置')
        ai_settings_btn.clicked.connect(self.open_ai_settings)
        ai_layout.addStretch()
        ai_layout.addWidget(ai_settings_btn)
        ai_group.setLayout(ai_layout)
        layout.addWidget(ai_group)

        # 测试连接按钮
        test_group = QGroupBox('测试与工具')
        test_layout = QHBoxLayout()
        test_btn = QPushButton('测试连接')
        test_btn.clicked.connect(self.open_test_window)
        curl_btn = QPushButton('生成 curl 命令')
        curl_btn.clicked.connect(self.generate_curl)
        test_layout.addWidget(test_btn)
        test_layout.addWidget(curl_btn)
        test_layout.addStretch()
        test_group.setLayout(test_layout)
        layout.addWidget(test_group)

        layout.addStretch()

        # 定时器更新状态
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(1000)

        self.update_status()

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, '选择 bat 所在文件夹')
        if folder:
            self.folder_edit.setText(folder)
            config['bat_folder'] = folder
            save_config(config)

    def apply_autostart(self):
        ok = set_autostart(self.autostart_check.isChecked())
        if ok:
            config['autostart'] = self.autostart_check.isChecked()
            save_config(config)
            QMessageBox.information(self, '提示', '已更新开机自启设置')
        else:
            QMessageBox.warning(self, '提示', '更新开机自启失败，请以管理员运行或检查系统策略')

    def update_status(self):
        configs = self.frp_manager.get_configs()
        running_count = sum(1 for name in configs.keys() if self.frp_manager.is_config_running(name))
        total_count = len(configs)
        if running_count > 0:
            self.frp_status_label.setText(f'运行中 ({running_count}/{total_count})')
            self.frp_status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.frp_status_label.setText('未连接' if total_count == 0 else f'已停止 ({total_count} 个配置)')
            self.frp_status_label.setStyleSheet("color: red; font-weight: bold;")

    def open_frp_settings(self):
        if self.frp_window is None or not self.frp_window.isVisible():
            self.frp_window = FRPSettingsWindow(self, self.frp_manager)
            self.frp_window.setGeometry(self.geometry())  # 与主窗口同样大小
        self.frp_window.show()
        self.frp_window.raise_()
        self.frp_window.activateWindow()

    def open_ai_settings(self):
        if not hasattr(self, 'ai_window') or self.ai_window is None or not self.ai_window.isVisible():
            self.ai_window = AISettingsWindow(self)
            self.ai_window.setGeometry(self.geometry())  # 与主窗口同样大小
        self.ai_window.show()
        self.ai_window.raise_()
        self.ai_window.activateWindow()

    def open_test_window(self):
        if self.test_window is None or not self.test_window.isVisible():
            self.test_window = TestConnectionWindow(self, self.frp_manager)
            self.test_window.setGeometry(self.geometry())  # 与主窗口同样大小
        self.test_window.show()
        self.test_window.raise_()
        self.test_window.activateWindow()

    def generate_curl(self):
        """打开 curl 生成窗口"""
        if self.curl_window is None or not self.curl_window.isVisible():
            self.curl_window = CurlWindow(self, self.frp_manager)
            self.curl_window.setGeometry(self.geometry())  # 与主窗口同样大小
        self.curl_window.show()
        self.curl_window.raise_()
        self.curl_window.activateWindow()

    def closeEvent(self, event):
        self.server.stop()
        self.frp_manager.stop_all()
        event.accept()


class TestConnectionWindow(QMainWindow):
    """测试连接窗口"""
    def __init__(self, parent, frp_manager):
        super().__init__(parent)
        self.frp_manager = frp_manager
        self.test_thread = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('测试连接')
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 输入区域
        input_group = QGroupBox('测试参数')
        input_layout = QVBoxLayout()

        # 文件名
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel('文件名（不含扩展名）：'))
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText('输入文件名，支持中文、英文、数字')
        key_layout.addWidget(self.key_edit)
        input_layout.addLayout(key_layout)

        # URL
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel('测试 URL：'))
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText('http://127.0.0.1:8888/webhook 或 http://frps地址:端口/webhook')
        url_layout.addWidget(self.url_edit)
        input_layout.addLayout(url_layout)

        # 快速选择按钮
        quick_layout = QHBoxLayout()
        local_btn = QPushButton('使用本地地址')
        local_btn.clicked.connect(lambda: self.url_edit.setText(f'http://127.0.0.1:{get_listen_port()}/webhook'))
        frp_btn = QPushButton('使用第一个运行中的 FRP')
        frp_btn.clicked.connect(self.use_first_frp)
        quick_layout.addWidget(local_btn)
        quick_layout.addWidget(frp_btn)
        quick_layout.addStretch()
        input_layout.addLayout(quick_layout)

        test_btn = QPushButton('开始测试')
        test_btn.clicked.connect(self.start_test)
        input_layout.addWidget(test_btn)

        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # 结果显示
        result_group = QGroupBox('测试结果')
        result_layout = QVBoxLayout()
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        result_layout.addWidget(self.result_text)
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

    def use_first_frp(self):
        """使用第一个运行中的 FRP 配置"""
        configs = self.frp_manager.get_configs()
        for cfg_name, cfg in configs.items():
            if self.frp_manager.is_config_running(cfg_name):
                server_addr = (cfg.get('server_addr') or '').strip()
                try:
                    remote_port = int(cfg.get('remote_port') or 0)
                except Exception:
                    remote_port = 0
                if server_addr and remote_port > 0:
                    self.url_edit.setText(f'http://{server_addr}:{remote_port}/webhook')
                    QMessageBox.information(self, '提示', f'已使用 FRP 配置: {cfg_name}')
                    return
        QMessageBox.warning(self, '提示', '没有运行中的 FRP 配置')

    def start_test(self):
        key = self.key_edit.text().strip()
        if not key:
            QMessageBox.warning(self, '提示', '请输入文件名（关键字）')
            return

        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, '提示', '请填写测试 URL')
            return

        self.result_text.clear()
        self.result_text.append(f"开始测试连接...\n")
        self.result_text.append(f"URL: {url}\n")
        self.result_text.append(f"文件名: {key}\n")
        self.result_text.append("-" * 50 + "\n")

        # 启动测试线程
        if self.test_thread and self.test_thread.isRunning():
            QMessageBox.warning(self, '提示', '测试正在进行中，请稍候...')
            return

        self.test_thread = TestConnectionThread(url, key)
        self.test_thread.result_signal.connect(self.result_text.append)
        self.test_thread.start()


class FRPSettingsWindow(QMainWindow):
    def __init__(self, parent, frp_manager):
        super().__init__(parent)
        self.frp_manager = frp_manager
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('FRP 设置')
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # frpc 路径
        path_group = QGroupBox('frpc.exe 路径')
        path_layout = QHBoxLayout()
        self.frpc_path_edit = QLineEdit(self.frp_manager.get_frpc_path())
        path_browse_btn = QPushButton('浏览...')
        path_browse_btn.clicked.connect(self.browse_frpc)
        path_layout.addWidget(self.frpc_path_edit)
        path_layout.addWidget(path_browse_btn)
        path_group.setLayout(path_layout)
        layout.addWidget(path_group)

        # 配置列表
        config_group = QGroupBox('FRP 配置列表')
        config_layout = QVBoxLayout()
        btn_layout = QHBoxLayout()
        add_btn = QPushButton('添加配置')
        edit_btn = QPushButton('编辑')
        delete_btn = QPushButton('删除')
        start_btn = QPushButton('启动')
        stop_btn = QPushButton('停止')
        refresh_btn = QPushButton('刷新')

        add_btn.clicked.connect(self.add_config)
        edit_btn.clicked.connect(self.edit_config)
        delete_btn.clicked.connect(self.delete_config)
        start_btn.clicked.connect(self.start_config)
        stop_btn.clicked.connect(self.stop_config)
        refresh_btn.clicked.connect(self.refresh_list)

        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(start_btn)
        btn_layout.addWidget(stop_btn)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addStretch()

        self.config_list = QListWidget()
        config_layout.addLayout(btn_layout)
        config_layout.addWidget(self.config_list)
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # 日志
        log_group = QGroupBox('日志')
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # 定时器更新日志
        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.update_logs)
        self.log_timer.start(500)

        self.refresh_list()

    def browse_frpc(self):
        path, _ = QFileDialog.getOpenFileName(self, '选择 frpc.exe', '', 'frpc.exe;;可执行文件 (*.exe);;所有文件 (*.*)')
        if path:
            self.frpc_path_edit.setText(path)
            self.frp_manager.set_frpc_path(path)
            save_config(config)

    def refresh_list(self):
        self.config_list.clear()
        configs = self.frp_manager.get_configs()
        for name in sorted(configs.keys()):
            status = '●运行中' if self.frp_manager.is_config_running(name) else '○已停止'
            self.config_list.addItem(f'{status} - {name}')

    def get_selected_config_name(self):
        items = self.config_list.selectedItems()
        if not items:
            return None
        item_text = items[0].text()
        return item_text.split(' - ', 1)[-1] if ' - ' in item_text else item_text.replace('●运行中 ', '').replace('○已停止 ', '')

    def add_config(self):
        dialog = ConfigDialog(self, self.frp_manager)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_list()

    def edit_config(self):
        name = self.get_selected_config_name()
        if not name:
            QMessageBox.warning(self, '提示', '请先选择一个配置')
            return
        configs = self.frp_manager.get_configs()
        if name not in configs:
            QMessageBox.critical(self, '错误', '配置不存在')
            return
        dialog = ConfigDialog(self, self.frp_manager, name, configs[name])
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_list()

    def delete_config(self):
        name = self.get_selected_config_name()
        if not name:
            QMessageBox.warning(self, '提示', '请先选择一个配置')
            return
        if QMessageBox.question(self, '确认删除', f'确定要删除配置 {name} 吗？') == QMessageBox.Yes:
            self.frp_manager.delete_config_item(name)
            self.refresh_list()

    def start_config(self):
        name = self.get_selected_config_name()
        if not name:
            QMessageBox.warning(self, '提示', '请先选择一个配置')
            return
        try:
            self.frp_manager.start_config(name)
            self.refresh_list()
            QMessageBox.information(self, '成功', f'配置 {name} 已启动')
        except Exception as e:
            QMessageBox.critical(self, '错误', str(e))

    def stop_config(self):
        name = self.get_selected_config_name()
        if not name:
            QMessageBox.warning(self, '提示', '请先选择一个配置')
            return
        self.frp_manager.stop_config(name)
        self.refresh_list()
        QMessageBox.information(self, '成功', f'配置 {name} 已停止')

    def update_logs(self):
        configs = self.frp_manager.get_configs()
        for name in configs.keys():
            log_queue = self.frp_manager.get_log_queue(name)
            try:
                while True:
                    line = log_queue.get_nowait()
                    self.log_text.append(line)
            except queue.Empty:
                pass
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


class ConfigDialog(QDialog):
    def __init__(self, parent, frp_manager, name=None, cfg=None):
        super().__init__(parent)
        self.frp_manager = frp_manager
        self.edit_name = name
        self.init_ui(cfg)

    def init_ui(self, cfg):
        self.setWindowTitle('添加 FRP 配置' if not cfg else f'编辑 FRP 配置: {self.edit_name}')
        self.setModal(True)
        layout = QVBoxLayout(self)

        # 服务器设置
        srv_group = QGroupBox('服务器设置')
        srv_layout = QVBoxLayout()
        srv_row1 = QHBoxLayout()
        srv_row1.addWidget(QLabel('frps 地址：'))
        self.srv_addr_edit = QLineEdit(cfg.get('server_addr', '') if cfg else '')
        srv_row1.addWidget(self.srv_addr_edit)
        srv_row1.addWidget(QLabel('端口：'))
        self.srv_port_edit = QLineEdit(str(cfg.get('server_port', 7000)) if cfg else '7000')
        self.srv_port_edit.setMaximumWidth(100)
        srv_row1.addWidget(self.srv_port_edit)
        srv_layout.addLayout(srv_row1)
        srv_row2 = QHBoxLayout()
        srv_row2.addWidget(QLabel('token：'))
        self.token_edit = QLineEdit(cfg.get('token', '') if cfg else '')
        srv_row2.addWidget(self.token_edit)
        srv_layout.addLayout(srv_row2)
        srv_group.setLayout(srv_layout)
        layout.addWidget(srv_group)

        # 映射设置
        map_group = QGroupBox('映射设置')
        map_layout = QVBoxLayout()
        type_row = QHBoxLayout()
        type_row.addWidget(QLabel('链接方式：'))
        self.type_group = QButtonGroup()
        self.tcp_radio = QRadioButton('TCP')
        self.udp_radio = QRadioButton('UDP')
        self.type_group.addButton(self.tcp_radio, 0)
        self.type_group.addButton(self.udp_radio, 1)
        if cfg:
            if cfg.get('type', 'tcp').lower() == 'udp':
                self.udp_radio.setChecked(True)
            else:
                self.tcp_radio.setChecked(True)
        else:
            self.tcp_radio.setChecked(True)
        type_row.addWidget(self.tcp_radio)
        type_row.addWidget(self.udp_radio)
        type_row.addStretch()
        map_layout.addLayout(type_row)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel('名字：'))
        self.name_edit = QLineEdit(cfg.get('name', generate_random_name()) if cfg else generate_random_name())
        random_btn = QPushButton('随机名字')
        random_btn.clicked.connect(lambda: self.name_edit.setText(generate_random_name()))
        name_row.addWidget(self.name_edit)
        name_row.addWidget(random_btn)
        map_layout.addLayout(name_row)

        local_ip_row = QHBoxLayout()
        local_ip_row.addWidget(QLabel('本地地址：'))
        self.local_ip_edit = QLineEdit(cfg.get('local_ip', '127.0.0.1') if cfg else '127.0.0.1')
        local_ip_row.addWidget(self.local_ip_edit)
        map_layout.addLayout(local_ip_row)

        local_port_row = QHBoxLayout()
        local_port_row.addWidget(QLabel('本地端口：'))
        self.local_port_edit = QLineEdit(str(cfg.get('local_port', get_listen_port())) if cfg else str(get_listen_port()))
        local_port_row.addWidget(self.local_port_edit)
        map_layout.addLayout(local_port_row)

        remote_port_row = QHBoxLayout()
        remote_port_row.addWidget(QLabel('映射服务器端口：'))
        self.remote_port_edit = QLineEdit(str(cfg.get('remote_port', 0)) if cfg else '')
        remote_port_row.addWidget(self.remote_port_edit)
        map_layout.addLayout(remote_port_row)

        map_group.setLayout(map_layout)
        layout.addWidget(map_group)

        # 按钮
        btn_layout = QHBoxLayout()
        save_btn = QPushButton('保存')
        cancel_btn = QPushButton('取消')
        save_btn.clicked.connect(self.save_config)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def save_config(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.critical(self, '错误', '名字不能为空')
            return

        try:
            cfg = {
                'server_addr': self.srv_addr_edit.text().strip(),
                'server_port': int(self.srv_port_edit.text()),
                'token': self.token_edit.text().strip(),
                'type': 'udp' if self.udp_radio.isChecked() else 'tcp',
                'name': name,
                'local_ip': self.local_ip_edit.text().strip(),
                'local_port': int(self.local_port_edit.text()),
                'remote_port': int(self.remote_port_edit.text())
            }
            if not cfg['server_addr'] or cfg['remote_port'] <= 0:
                QMessageBox.critical(self, '错误', '请填写完整信息（服务器地址、映射服务器端口）')
                return

            if self.edit_name and name != self.edit_name:
                self.frp_manager.delete_config_item(self.edit_name)

            self.frp_manager.save_config_item(name, cfg)
            QMessageBox.information(self, '成功', f'配置 {name} 已保存')
            self.accept()

        except ValueError:
            QMessageBox.critical(self, '错误', '端口必须是数字')
        except Exception as e:
            QMessageBox.critical(self, '错误', str(e))


class CurlWindow(QMainWindow):
    """curl 生成窗口"""
    def __init__(self, parent, frp_manager):
        super().__init__(parent)
        self.frp_manager = frp_manager
        self.send_thread = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('生成 curl 命令')
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 输入区域
        input_group = QGroupBox('参数设置')
        input_layout = QVBoxLayout()

        # 关键词输入
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel('关键词（文件名，不含扩展名）：'))
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText('输入文件名，支持中文、英文、数字')
        self.key_edit.returnPressed.connect(self.generate_curl_cmd)  # 回车键生成
        key_layout.addWidget(self.key_edit)
        input_layout.addLayout(key_layout)

        # URL 选择
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel('目标地址：'))
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText('自动使用运行中的FRP或本地地址')
        url_layout.addWidget(self.url_edit)
        input_layout.addLayout(url_layout)

        # 快速选择按钮
        quick_layout = QHBoxLayout()
        local_btn = QPushButton('使用本地地址')
        local_btn.clicked.connect(lambda: self.url_edit.setText(f'http://127.0.0.1:{get_listen_port()}/webhook'))
        frp_btn = QPushButton('使用第一个运行中的 FRP')
        frp_btn.clicked.connect(self.use_first_frp)
        quick_layout.addWidget(local_btn)
        quick_layout.addWidget(frp_btn)
        quick_layout.addStretch()
        input_layout.addLayout(quick_layout)

        # 按钮区域
        btn_layout = QHBoxLayout()
        generate_btn = QPushButton('生成 curl 命令')
        generate_btn.clicked.connect(self.generate_curl_cmd)
        copy_btn = QPushButton('复制到剪贴板')
        copy_btn.clicked.connect(self.copy_to_clipboard)
        send_btn = QPushButton('远程发送（执行）')
        send_btn.clicked.connect(self.send_request)
        send_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        btn_layout.addWidget(generate_btn)
        btn_layout.addWidget(copy_btn)
        btn_layout.addWidget(send_btn)
        btn_layout.addStretch()
        input_layout.addLayout(btn_layout)

        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # curl 命令显示
        curl_group = QGroupBox('curl 命令')
        curl_layout = QVBoxLayout()
        self.curl_text = QTextEdit()
        self.curl_text.setReadOnly(True)
        self.curl_text.setMaximumHeight(100)
        curl_layout.addWidget(self.curl_text)
        curl_group.setLayout(curl_layout)
        layout.addWidget(curl_group)

        # 执行结果
        result_group = QGroupBox('执行结果')
        result_layout = QVBoxLayout()
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        result_layout.addWidget(self.result_text)
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        # 自动填充URL
        self.auto_fill_url()

    def auto_fill_url(self):
        """自动填充URL（优先使用运行中的FRP）"""
        configs = self.frp_manager.get_configs()
        for cfg_name, cfg in configs.items():
            if self.frp_manager.is_config_running(cfg_name):
                server_addr = (cfg.get('server_addr') or '').strip()
                try:
                    remote_port = int(cfg.get('remote_port') or 0)
                except Exception:
                    remote_port = 0
                if server_addr and remote_port > 0:
                    self.url_edit.setText(f'http://{server_addr}:{remote_port}/webhook')
                    return
        # 如果没有运行中的FRP，使用本地地址
        self.url_edit.setText(f'http://127.0.0.1:{get_listen_port()}/webhook')

    def use_first_frp(self):
        """使用第一个运行中的 FRP 配置"""
        configs = self.frp_manager.get_configs()
        for cfg_name, cfg in configs.items():
            if self.frp_manager.is_config_running(cfg_name):
                server_addr = (cfg.get('server_addr') or '').strip()
                try:
                    remote_port = int(cfg.get('remote_port') or 0)
                except Exception:
                    remote_port = 0
                if server_addr and remote_port > 0:
                    self.url_edit.setText(f'http://{server_addr}:{remote_port}/webhook')
                    QMessageBox.information(self, '提示', f'已使用 FRP 配置: {cfg_name}')
                    return
        QMessageBox.warning(self, '提示', '没有运行中的 FRP 配置')

    def generate_curl_cmd(self):
        """生成 curl 命令"""
        key = self.key_edit.text().strip()
        if not key:
            QMessageBox.warning(self, '提示', '请输入关键词（文件名）')
            return

        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, '提示', '请填写目标地址')
            return

        # 使用单引号包裹 JSON，不需要转义
        payload = json.dumps({"key": key}, ensure_ascii=False)
        # 多行格式，使用反斜杠换行
        curl = f'curl -X POST "{url}" \\\n     -H "Content-Type: application/json" \\\n     -d \'{payload}\''

        self.curl_text.setPlainText(curl)
        QMessageBox.information(self, '成功', 'curl 命令已生成！')

    def copy_to_clipboard(self):
        """复制 curl 命令到剪贴板"""
        curl = self.curl_text.toPlainText().strip()
        if not curl:
            QMessageBox.warning(self, '提示', '请先生成 curl 命令')
            return

        clipboard = QApplication.clipboard()
        clipboard.setText(curl)
        QMessageBox.information(self, '成功', 'curl 命令已复制到剪贴板！')

    def send_request(self):
        """远程发送请求（执行curl命令）"""
        key = self.key_edit.text().strip()
        if not key:
            QMessageBox.warning(self, '提示', '请输入关键词（文件名）')
            return

        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, '提示', '请填写目标地址')
            return

        self.result_text.clear()
        self.result_text.append(f"正在发送请求...\n")
        self.result_text.append(f"URL: {url}\n")
        self.result_text.append(f"关键词: {key}\n")
        self.result_text.append("-" * 50 + "\n")

        # 启动发送线程
        if self.send_thread and self.send_thread.isRunning():
            QMessageBox.warning(self, '提示', '请求正在进行中，请稍候...')
            return

        self.send_thread = SendRequestThread(url, key)
        self.send_thread.result_signal.connect(self.result_text.append)
        self.send_thread.start()


class SendRequestThread(QThread):
    """发送请求的线程"""
    result_signal = pyqtSignal(str)

    def __init__(self, url: str, key: str):
        super().__init__()
        self.url = url
        self.key = key

    def run(self):
        try:
            payload = {"key": self.key}
            
            if HAS_REQUESTS:
                try:
                    import urllib3
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                except ImportError:
                    pass

                start_time = time.time()
                try:
                    session = requests.Session()
                    session.trust_env = False
                    
                    response = session.post(
                        self.url,
                        json=payload,
                        headers={'Content-Type': 'application/json'},
                        timeout=(10, 60),
                        verify=False,
                        allow_redirects=True,
                        proxies={}
                    )
                    elapsed = time.time() - start_time

                    self.result_signal.emit(f"✅ 请求发送成功！\n")
                    self.result_signal.emit(f"状态码: {response.status_code}\n")
                    self.result_signal.emit(f"响应时间: {elapsed:.2f} 秒\n")
                    self.result_signal.emit(f"响应内容: {response.text}\n")
                    if response.status_code == 200:
                        self.result_signal.emit(f"\n✅ 成功！webhook 已触发，BAT 文件已执行\n")
                    else:
                        self.result_signal.emit(f"\n⚠️ 警告：状态码不是 200\n")
                except requests.exceptions.Timeout as e:
                    self.result_signal.emit(f"\n❌ 请求超时\n")
                    self.result_signal.emit(f"错误详情: {str(e)}\n")
                except requests.exceptions.ConnectionError as e:
                    self.result_signal.emit(f"\n❌ 连接失败\n")
                    self.result_signal.emit(f"错误详情: {str(e)}\n")
                except Exception as e:
                    self.result_signal.emit(f"\n❌ 请求失败\n")
                    self.result_signal.emit(f"错误信息: {str(e)}\n")
            else:
                self.result_signal.emit(f"\n❌ 错误：缺少 requests 库，无法发送请求\n")
                self.result_signal.emit(f"请安装: pip install requests\n")

        except Exception as e:
            self.result_signal.emit(f"\n❌ 未知错误\n")
            self.result_signal.emit(f"错误信息: {str(e)}\n")
            self.result_signal.emit(f"详细错误: {traceback.format_exc()}\n")


class AISettingsWindow(QMainWindow):
    """AI 配置窗口"""
    def __init__(self, parent):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('AI 配置')
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # API URL
        url_group = QGroupBox('API 设置')
        url_layout = QVBoxLayout()
        
        url_row = QHBoxLayout()
        url_row.addWidget(QLabel('API URL：'))
        self.api_url_edit = QLineEdit()
        ai_config = config.get('ai', {})
        self.api_url_edit.setText(ai_config.get('api_url', ''))
        self.api_url_edit.setPlaceholderText('例如: https://api.openai.com/v1/chat/completions')
        url_row.addWidget(self.api_url_edit)
        url_layout.addLayout(url_row)

        key_row = QHBoxLayout()
        key_row.addWidget(QLabel('API Key：'))
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setText(ai_config.get('api_key', ''))
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText('输入你的 API Key')
        key_row.addWidget(self.api_key_edit)
        url_layout.addLayout(key_row)

        model_row = QHBoxLayout()
        model_row.addWidget(QLabel('Model：'))
        self.model_edit = QLineEdit()
        self.model_edit.setText(ai_config.get('model', ''))
        self.model_edit.setPlaceholderText('例如: gpt-4o, gpt-4-vision-preview')
        model_row.addWidget(self.model_edit)
        url_layout.addLayout(model_row)

        url_group.setLayout(url_layout)
        layout.addWidget(url_group)

        # 提示词
        prompt_group = QGroupBox('提示词')
        prompt_layout = QVBoxLayout()
        prompt_label = QLabel('AI 分析截图时使用的提示词：')
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlainText(ai_config.get('prompt', '请分析这张截图，描述当前屏幕上显示的内容和进度状态。'))
        self.prompt_edit.setMaximumHeight(100)
        prompt_layout.addWidget(prompt_label)
        prompt_layout.addWidget(self.prompt_edit)
        prompt_group.setLayout(prompt_layout)
        layout.addWidget(prompt_group)

        # 按钮
        btn_layout = QHBoxLayout()
        save_btn = QPushButton('保存配置')
        save_btn.clicked.connect(self.save_config)
        test_btn = QPushButton('测试连接')
        test_btn.clicked.connect(self.test_connection)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(test_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 测试结果
        result_group = QGroupBox('测试结果')
        result_layout = QVBoxLayout()
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        result_layout.addWidget(self.result_text)
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

    def save_config(self):
        if 'ai' not in config:
            config['ai'] = {}
        
        config['ai']['api_url'] = self.api_url_edit.text().strip()
        config['ai']['api_key'] = self.api_key_edit.text().strip()
        config['ai']['model'] = self.model_edit.text().strip()
        config['ai']['prompt'] = self.prompt_edit.toPlainText().strip()
        
        save_config(config)
        QMessageBox.information(self, '成功', 'AI 配置已保存')

    def test_connection(self):
        """测试 AI 连接"""
        self.result_text.clear()
        self.result_text.append('正在测试 AI 连接...\n')
        
        if not HAS_PIL:
            self.result_text.append('❌ 错误：未安装 Pillow 库\n')
            self.result_text.append('请运行: pip install Pillow\n')
            return
        
        if not HAS_REQUESTS:
            self.result_text.append('❌ 错误：未安装 requests 库\n')
            self.result_text.append('请运行: pip install requests\n')
            return
        
        api_url = self.api_url_edit.text().strip()
        api_key = self.api_key_edit.text().strip()
        model = self.model_edit.text().strip()
        
        if not api_url or not api_key or not model:
            self.result_text.append('❌ 错误：请填写完整的 API URL、Key 和 Model\n')
            return
        
        try:
            self.result_text.append('正在截图...\n')
            base64_image = capture_screenshot()
            self.result_text.append('✅ 截图成功\n')
            self.result_text.append('正在调用 AI API...\n')
            
            ai_result = call_ai_api(base64_image)
            self.result_text.append('✅ AI API 调用成功\n\n')
            self.result_text.append('AI 分析结果：\n')
            self.result_text.append('-' * 50 + '\n')
            self.result_text.append(ai_result)
            
        except Exception as e:
            self.result_text.append(f'\n❌ 测试失败: {str(e)}\n')
            self.result_text.append(f'详细错误:\n{traceback.format_exc()}\n')


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'serve':
        port = get_listen_port()
        logging.info('服务启动，端口 %s，bat 目录：%s', port, get_bat_folder())
        app.run(host='0.0.0.0', port=port, threaded=True)
        return

    qapp = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(qapp.exec_())


if __name__ == '__main__':
    main()
