# AI 智学系统 · Windows Server 原生部署指南

> 适用：Windows Server 2019/2022（部署方式与本机 Windows 验证过的方案一致，不用 Docker）
> 目标：服务器上跑起 前端(5173) + backend(8000) + ai-tutor(8001)，评委访问 http://服务器IP:5173

---

## 一、服务器要装的软件（2 个）

1. **Python 3.11+**（装的时候**务必勾选 "Add Python to PATH"**）
   - 下载：https://www.python.org/downloads/
2. **Node.js 18+ LTS**
   - 下载：https://nodejs.org/zh-cn（选 LTS 版，一路下一步）

装完验证（打开 CMD 或 PowerShell）：
```powershell
python --version
node --version
```

---

## 二、把代码传到服务器

在你本机（9/3 跑通的源码目录）打包三个目录（**不要打包 node_modules，太大**）：

```powershell
# 在你本机源码目录执行：打包 backend + ai-tutor + frontend（frontend 去掉 node_modules）
Compress-Archive -Path backend, ai-tutor -DestinationPath 服务端代码.zip
cd frontend
Compress-Archive -Path * -DestinationPath ../前端代码.zip -Exclude node_modules
```

> 前端目录大是因为 node_modules，排除后很小。服务器上重新 `npm install` 即可。

传到服务器：远程桌面（RDP）登录后，把两个 zip 复制到服务器 `C:\deploy\`（建议建个 D:\ 或非系统盘目录，服务器 C 盘可能也紧张，**建议放 D:\deploy**），解压：

```powershell
# 服务器上
mkdir D:\deploy
cd D:\deploy
Expand-Archive -Path .\服务端代码.zip -DestinationPath .
Expand-Archive -Path .\前端代码.zip -DestinationPath .\frontend
```

---

## 三、服务器上装依赖

```powershell
# 1. backend 依赖（在 D:\deploy\backend）
cd D:\deploy\backend
pip install -r requirements.txt

# 2. ai-tutor 核心依赖（在 D:\deploy\ai-tutor）
#    只装运行必需的核心包（跳过 manim/moviepy 等视频生成重依赖，不影响对话/资源生成）
cd D:\deploy\ai-tutor
pip install fastapi uvicorn pydantic pydantic-settings sqlalchemy aiosqlite redis chromadb openai apscheduler python-dotenv sse-starlette httpx "pydantic>=2.5"

# 3. 前端依赖（在 D:\deploy\frontend，需要几分钟）
cd D:\deploy\frontend
npm install
```

---

## 四、配置 API Key

创建/编辑 `D:\deploy\backend\.env`：
```ini
GLM_API_KEY=sk-你的DeepSeekKey
GLM_MODEL=deepseek-chat
GLM_BASE_URL=https://api.deepseek.com
JWT_SECRET=随机长字符串
DATABASE_URL=sqlite+aiosqlite:///./data.db
```

创建/编辑 `D:\deploy\ai-tutor\.env`：
```ini
DEEPSEEK_API_KEY=sk-你的DeepSeekKey
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DATABASE_TYPE=sqlite
```

---

## 五、启动三个服务（3 个窗口）

**窗口 1 - backend**（端口 8000）：
```powershell
cd D:\deploy\backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**窗口 2 - ai-tutor**（端口 8001）：
```powershell
cd D:\deploy\ai-tutor
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

**窗口 3 - 前端**（端口 5173）：
```powershell
cd D:\deploy\frontend
npm run dev
```

> 三个窗口都要保持开着（最小化即可）。服务器重启后需重新启动——见第六节做开机自启。

---

## 六、（可选）防火墙开放端口

评委要访问，必须在服务器防火墙放行：

```powershell
# 管理员 PowerShell
netsh advfirewall firewall add rule name="backend8000" dir=in action=allow protocol=TCP localport=8000
netsh advfirewall firewall add rule name="ai-tutor8001" dir=in action=allow protocol=TCP localport=8001
netsh advfirewall firewall add rule name="frontend5173" dir=in action=allow protocol=TCP localport=5173
```

> 如果服务器在云上（阿里云/腾讯云等），还要去**云控制台安全组**放行这三个端口（重要！光改服务器防火墙不够）。

---

## 七、验证

```powershell
# 服务器本地测试
curl http://localhost:8000/api/v1/health
# 期望 {"status":"ok"}

curl http://localhost:8001/api/audit/decisions?limit=1
# 期望 JSON

curl -I http://localhost:5173
# 期望 HTTP 200
```

**评委访问地址**：`http://服务器公网IP:5173`
**测试账号**：学生 `demo_student` / `demo123456`；管理员注册邀请码 `ADM2026`

---

## 八、（进阶）开机自启 - NSSM 注册服务

服务器重启后不想手动开 3 个窗口，用 NSSM（免费）把三个进程注册成 Windows 服务：

1. 下载 NSSM：https://nssm.cc/download （解压 nssm.exe）
2. 管理员 CMD，注册三个服务（示例 backend）：
```cmd
C:\nssm\nssm.exe install AIBackend "C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe" "-m uvicorn app.main:app --host 0.0.0.0 --port 8000"
C:\nssm\nssm.exe set AIBackend AppDirectory D:\deploy\backend
C:\nssm\nssm.exe start AIBackend
```
3. ai-tutor 和前端同理注册（前端可用 npm 的 cmd 包装，或直接用 `node node_modules/vite/bin/vite.js`）

---

## 九、常见问题

| 问题 | 处理 |
|---|---|
| 端口被占用 | 8000/8001/5173 分别被占用时：`netstat -ano | findstr 端口` 找 PID → `taskkill /F /PID xx` |
| AI 对话报错 | DeepSeek key 欠费或未填 → 充值/检查 .env 后重启对应服务 |
| 外部访问不了 | ① 云安全组放行了吗？② 服务器防火墙放行了吗？③ 服务起来了窗口别关 |
| npm install 慢/失败 | 用国内镜像：`npm config set registry https://registry.npmmirror.com` 后重试 |
| pip 装包慢 | `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple 包名` |
