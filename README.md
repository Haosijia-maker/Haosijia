# 思嘉工作台 · 云同步 运行说明

单文件网页应用 + 一个 Python 同步后端，让**两台电脑**改同一个数据（财务、生日、计划……）自动保持一致。

## 文件
- `index.html` —— 工作台页面（已开启云同步 `HAS_API=true`）
- `server.py` —— 同步后端（只用到 Python 标准库，**无需安装任何依赖**）
- `data.json` —— 当前共享数据（每次保存自动覆盖，相当于"云端那份"）

## 在本机跑起来
```bash
cd workbench-sync
python server.py
# 默认监听 0.0.0.0:8765，浏览器打开 http://<这台电脑的IP>:8765
```
常用环境变量：
- `PORT=9000` 改端口
- `BIND=127.0.0.1` 只允许本机（默认 0.0.0.0，允许同局域网其他电脑访问）

## 两台电脑怎么同步
1. 选一台**一直开着的电脑**（或任意可访问的服务器）运行 `server.py`。
2. 两台电脑都用浏览器打开 `http://<那台电脑的IP>:<端口>/`。
3. 在任意一台上改动 → 自动上传到 `data.json`；另一台打开/刷新即拉取最新数据。
   - 同步逻辑按时间戳合并：同一字段以"较新修改"为准，不会简单互相覆盖。

## 首次启用的重要提醒（避免覆盖）
- 启用同步前，先在**两台电脑本地的旧工作台**各点一次"导出备份"，留底。
- 以"数据最新/最全的那台"为主设备，**先打开**同步地址并随便改一下（触发上传），
  再在另一台打开同步地址拉取，这样不会把旧数据覆盖了主设备。

## 手动备份 / 迁移
- 页面里"导出备份"按钮 → 下载 `.json`；"导入备份"按钮 → 选文件恢复。
- 服务端 `data.json` 就是同一份数据，直接复制它也能迁移。

## 改成公网可访问（跨网络的两台电脑）
- 最简单：在这台运行 server.py 的电脑上用内网穿透（如 Cloudflare Tunnel / ngrok）把端口暴露出去，
  两台电脑都访问穿透得到的公网地址。
- 或把 `server.py` + `index.html` + `data.json` 部署到任意支持 Python 的云主机/Serverless。
- 注意：`index.html` 必须由这个 server.py 同源托管（同步接口是 `同域名/api/sync`），不要用 file:// 直接打开 html。

## 部署到云主机（Render / Railway 等）
已附带零依赖部署文件：`requirements.txt`（空，纯标准库）、`Procfile`（`web: python server.py`）、`runtime.txt`（python-3.13）。

**关键：数据持久化。** 云主机的容器文件系统一般是临时的，重启/重新部署会清空 `data.json`，导致数据丢失。
务必把数据写到挂载的持久磁盘，并用环境变量 `DATA_FILE` 指向它：
- Render：建 Disk 挂到 `/var/data`，设环境变量 `DATA_FILE=/var/data/data.json`。
- Railway：建 Volume 挂到 `/data`，设 `DATA_FILE=/data/data.json`。
- 不挂磁盘也能跑，但每次重启数据会回到初始备份（仓库内 `data.json`）。

**首次部署会自动播种：** 当 `DATA_FILE` 指向的磁盘为空时，服务端会自动把仓库内自带的 `data.json`（即你现在的「郝思嘉」备份）复制进去作为初始数据，无需手动上传。之后所有改动都写进该磁盘，重启不丢。若你想用别的初始数据，部署前替换仓库里的 `data.json` 即可。

**部署步骤（以 Render 为例）：**
1. 把 `workbench-sync/` 整个目录推到 GitHub 新仓库。
2. Render 新建 Web Service → 连该仓库 → Runtime 选 Python → Build 留空（无需 pip install）→ Start：`python server.py`。
3. 在 Render 里建一个 Disk（挂载 `/var/data`），并设环境变量 `DATA_FILE=/var/data/data.json`。
4. 部署完成后首次访问，服务端会自动把内置的「郝思嘉」备份播种到磁盘，无需手动上传。
5. 两台电脑都用浏览器打开 Render 分配的地址（如 `https://xxx.onrender.com/`），即可跨网络实时同步。
- Railway 同理：新建 Project → 部署该目录 → 设 Start `python server.py`、挂载 Volume、设 `DATA_FILE`。
- 端口：服务已读取 `$PORT`（云主机自动注入），无需手动指定。
