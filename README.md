# Procurement Copilot - 医疗设备采购智能协同助手

基于 CrewAI、FastAPI、Streamlit 和 MCP 微服务架构构建的医疗设备采购辅助系统。系统支持 PDF 或纯文本报价单解析、医疗器械库存查询、合规政策审查、多智能体协同审批、JWT 接口鉴权、SQLite 历史记录持久化和分析耗时统计。

## 核心功能

- 上传 PDF 采购报价单，使用 PyPDF2 提取文本
- 支持粘贴纯文本医疗设备报价单
- 通过 CrewAI 多智能体协作完成分析与审批
- MCP Server 提供库存和企业合规政策 REST 接口
- FastAPI 主后端提供分析和历史记录接口
- Streamlit 前端展示审批报告、耗时和历史采购记录
- SQLite 持久化采购分析记录
- `/api/analyze` 接口使用 Bearer Token 鉴权
- Docker Compose 一键启动全部微服务

## 系统架构

```text
Streamlit Frontend
        |
        | POST /api/analyze
        | GET  /api/history
        v
FastAPI Backend API :8000
        |
        | CrewAI 4-Agent Workflow
        | GET /api/inventory
        | GET /api/policy
        v
MCP Server :8001
        |
        +-- ERP 模拟库存
        +-- company_policy.txt 医疗采购政策
```

### 多智能体工作流

1. 医疗设备采购分析师：提取设备型号、数量、价格、供应商、保修期和资质信息。
2. 医疗设备库存与资产管理员：查询库存并评估采购数量和资产风险。
3. 医疗设备采购合规专家：核验许可证、注册资质、保修期和采购合规性。
4. 医疗设备采购总监：审查全部结论，给出“同意采购”或“驳回”意见。

## 项目结构

```text
.
├── app.py                 # Streamlit 前端
├── api.py                 # FastAPI 主后端
├── mcp_server.py          # MCP 微服务
├── agents.py              # CrewAI Agent、Task 与工具
├── database.py            # SQLite 数据库操作
├── company_policy.txt     # 医疗设备采购合规政策
├── requirements.txt       # Python 依赖
├── Dockerfile             # 应用镜像
├── docker-compose.yml     # 微服务编排
├── .env.example           # 环境变量模板
└── README.md
```

## 快速启动

### 方式一：Docker Compose

确保已安装 Docker 和 Docker Compose。

```powershell
docker-compose up --build
```

启动后访问：

- Streamlit 前端：http://localhost:8501
- 主后端 API：http://localhost:8000
- MCP Server：http://localhost:8001
- FastAPI 接口文档：http://localhost:8000/docs

停止服务：

```powershell
docker-compose down
```

### 方式二：本地运行

推荐使用 Python 3.10 或更高版本。

1. 创建并激活虚拟环境：

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. 安装依赖：

```powershell
python -m pip install -r requirements.txt
```

3. 配置环境变量：

复制 `.env.example` 为 `.env`，并填写 DeepSeek API Key：

```env
OPENAI_API_KEY=your_deepseek_api_key_here
OPENAI_API_BASE=https://api.deepseek.com/v1
OPENAI_MODEL_NAME=deepseek-chat
```

不要将真实 API Key 提交到 Git 仓库。

4. 启动 MCP Server：

```powershell
python -m uvicorn mcp_server:app --host 127.0.0.1 --port 8001
```

5. 新开终端启动主后端：

```powershell
python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

6. 新开终端启动 Streamlit：

```powershell
streamlit run app.py
```

## 接口说明

### 分析接口

```http
POST /api/analyze
Authorization: Bearer medical_admin_token
Content-Type: application/json
```

请求体：

```json
{
  "report_text": "供应商：华康医疗设备有限公司\nCT机 1 台，单价 800万元，原厂保修 5 年"
}
```

返回示例：

```json
{
  "success": true,
  "report": "采购总监审批报告...",
  "execution_time": 12.345
}
```

未携带正确 Bearer Token 时，接口返回：

```json
{
  "detail": "Unauthorized"
}
```

HTTP 状态码为 `401`。

### MCP 库存接口

```http
GET /api/inventory?product=CT机
```

支持的模拟医疗设备：

- 核磁共振仪：3 台
- 心电监护仪：50 台
- CT机：5 台
- 呼吸机：20 台

### MCP 合规政策接口

```http
GET /api/policy
```

### 历史记录接口

```http
GET /api/history
```

## 数据库

项目使用 SQLite，数据库文件默认为项目目录下的 `procurement.db`。

表结构：

```sql
procurement_records (
    id,
    supplier,
    total_amount,
    decision_summary,
    created_at
)
```

数据库文件、虚拟环境、测试文档和密钥文件已通过 `.gitignore` 排除。

## 安全说明

当前项目使用固定示例 Token `medical_admin_token`，仅用于演示和原型验证。生产环境应使用：

- 签名密钥和令牌过期时间
- 用户身份与角色管理
- HTTPS
- 密钥管理服务
- 更严格的接口限流和审计日志

## 技术栈

- Python
- CrewAI
- FastAPI
- Uvicorn
- Streamlit
- MCP 风格 REST 微服务
- SQLite
- PyPDF2
- OpenAI兼容接口 / DeepSeek
- Docker Compose
