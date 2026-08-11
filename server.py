#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
思嘉工作台 · 云同步后端
- GET  /api/sync        -> {"status":"ok","data":<json>}
- POST /api/sync        -> 保存请求体，返回 {"status":"ok","data":<json>}
- GET  /  (及 /index.html) -> 工作台 index.html
- 其余路径按静态文件返回（如有）

数据统一存到本目录的 data.json（与前端备份格式一致）。
仅做"整份覆盖 + 时间戳合并由前端 deepMerge 完成"，适合单人跨设备同步。
"""
import json
import os
import shutil
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(ROOT, "index.html")
# 数据文件路径可经环境变量覆盖（云主机请指向持久化磁盘，否则重启即丢）
DATA_FILE = os.path.abspath(os.environ.get("DATA_FILE", os.path.join(ROOT, "data.json")))
PORT = int(os.environ.get("PORT", "8765"))
BIND = os.environ.get("BIND", "0.0.0.0")  # 真实部署用 0.0.0.0；本机/沙箱测试可设 127.0.0.1

_lock = threading.Lock()


def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_data(d):
    parent = os.path.dirname(DATA_FILE)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    # 优先原子替换；Windows 下若目标被占用/回收站钩子干扰，退化为先删再改名
    try:
        os.replace(tmp, DATA_FILE)
    except OSError:
        try:
            if os.path.exists(DATA_FILE):
                os.remove(DATA_FILE)
        except OSError:
            pass
        os.rename(tmp, DATA_FILE)


class Handler(BaseHTTPRequestHandler):
    server_version = "SijiaWorkbenchSync/1.0"

    # ---- 响应辅助 ----
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def log_message(self, fmt, *args):  # 安静日志
        pass

    def log_error(self, fmt, *args):
        print("ERR:", fmt % args if args else fmt)

    # ---- 路由 ----
    def do_OPTIONS(self):
        self._send(204, b"")

    def do_GET(self):
        try:
            self._do_GET()
        except Exception:
            traceback.print_exc()
            try:
                self._send(500, json.dumps({"status": "error", "msg": "server error"}, ensure_ascii=False))
            except Exception:
                pass

    def _do_GET(self):
        p = urlparse(self.path).path
        if p == "/api/sync":
            with _lock:
                d = load_data()
            self._send(200, json.dumps({"status": "ok", "data": d}, ensure_ascii=False))
            return
        if p in ("/", "/index.html"):
            if os.path.exists(HTML_FILE):
                with open(HTML_FILE, "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
                return
        self._send(404, json.dumps({"status": "error", "msg": "not found"}, ensure_ascii=False))

    def do_POST(self):
        try:
            self._do_POST()
        except Exception:
            traceback.print_exc()
            try:
                self._send(500, json.dumps({"status": "error", "msg": "server error"}, ensure_ascii=False))
            except Exception:
                pass

    def _do_POST(self):
        p = urlparse(self.path).path
        if p != "/api/sync":
            self._send(404, json.dumps({"status": "error", "msg": "not found"}, ensure_ascii=False))
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
        except Exception:
            length = 0
        raw = self.rfile.read(length) if length else b"{}"
        try:
            d = json.loads(raw.decode("utf-8"))
        except Exception as e:
            self._send(400, json.dumps({"status": "error", "msg": "invalid json: %s" % e}, ensure_ascii=False))
            return
        if not isinstance(d, dict):
            self._send(400, json.dumps({"status": "error", "msg": "data must be object"}, ensure_ascii=False))
            return
        try:
            with _lock:
                save_data(d)
        except Exception as e:
            traceback.print_exc()
            self._send(500, json.dumps({"status": "error", "msg": "save failed: %s" % e}, ensure_ascii=False))
            return
        self._send(200, json.dumps({"status": "ok", "data": d}, ensure_ascii=False))


def main():
    # 仅在数据文件确实不存在时才初始化。
    # 若设置了 DATA_FILE（云主机持久磁盘）且磁盘为空，则从代码包内自带的 data.json 播种，
    # 避免把已有的「郝思嘉」数据丢掉；本地默认 DATA_FILE 即代码内 data.json，已存在则跳过。
    if not os.path.exists(DATA_FILE):
        seed = os.path.join(ROOT, "data.json")
        try:
            if os.path.exists(seed):
                parent = os.path.dirname(DATA_FILE)
                if parent:
                    os.makedirs(parent, exist_ok=True)
                shutil.copyfile(seed, DATA_FILE)
                print("已从内置备份初始化数据文件: %s" % DATA_FILE)
            else:
                save_data({})
        except Exception as e:
            print("初始化数据文件失败:", e)
    srv = ThreadingHTTPServer((BIND, PORT), Handler)
    print("思嘉工作台云同步已启动: http://%s:%d  (Ctrl+C 停止)" % (BIND, PORT))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
        srv.shutdown()


if __name__ == "__main__":
    main()
