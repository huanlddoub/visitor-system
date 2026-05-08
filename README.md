# 客户接待助手 — 多 Agent 协同系统

基于多 Agent 协同架构的智能客户接待管理平台，4 个专业 Agent 各司其职，覆盖从信息收集到汇报总结的全流程。

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                   管理员端 (frontend-admin)               │
│              Agent 协同面板 · 任务看板 · 日报              │
└──────────────────────┬──────────────────────────────────┘
                       │ REST API
┌──────────────────────▼──────────────────────────────────┐
│                   FastAPI 后端 (backend)                  │
│  /agent/collect  /agent/assign-suggest  /agent/track-alerts  /agent/daily-report  │
└───────┬──────────┬──────────┬──────────┬───────────────┘
        │          │          │          │
   ┌────▼───┐ ┌───▼────┐ ┌──▼───┐ ┌───▼────┐
   │ 信息收集 │ │ 智能分配 │ │进度跟踪│ │汇报总结│
   │ Agent  │ │ Agent  │ │Agent │ │ Agent │
   └────────┘ └────────┘ └──────┘ └───────┘
        WorkBuddy 平台托管的 4 个独立 Agent
```

## 四大 Agent 职责

| Agent | 名称 | 职责 | API 端点 |
|-------|------|------|----------|
| Agent 1 | 信息收集 | 多轮对话收集访客需求，结构化提取来宾信息 | `/api/agent/collect` |
| Agent 2 | 智能分配 | 根据技能匹配、工作负载推荐最佳接待人员 | `/api/agent/assign-suggest` |
| Agent 3 | 进度跟踪 | 扫描超时/异常任务，生成告警提醒 | `/api/agent/track-alerts` |
| Agent 4 | 汇报总结 | 生成接待日报、数据洞察和统计报告 | `/api/agent/daily-report` |

> **降级策略**：未配置 Agent ID 或 WorkBuddy 调用失败时，系统自动回退到本地规则引擎，确保基本功能可用。

## 工程结构

```
visitor-system/
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── agent/
│   │   │   └── workbuddy.py  # 多 Agent 客户端（按类型路由到不同 Agent）
│   │   ├── database.py       # 数据库 + 4 个 Agent ID 配置
│   │   ├── main.py           # API 路由（含 Agent 协同接口）
│   │   ├── models.py         # SQLAlchemy 模型
│   │   ├── schemas.py        # Pydantic 模型（含 TrackAlert / DailyReport）
│   │   └── services.py       # 业务逻辑
│   ├── sql/init.sql          # 数据库初始化脚本
│   └── .env.example          # 环境变量模板
├── frontend-admin/           # 管理员 + 接待人员 Web 端
│   └── src/
│       ├── App.tsx           # 含 Agent 协同面板
│       ├── api.ts            # 含 Agent API 方法
│       └── types.ts          # 含 Agent 相关类型定义
├── frontend-customer/        # 客户自助填报端
└── README.md
```

## 本地启动

### 1. 初始化 MySQL

先使用你本机可登录的 MySQL 账号执行：

```bash
mysql -u<user> -p < backend/sql/init.sql
```

如果不是 `root/password`，复制环境变量模板并修改连接串：

```bash
cd backend
copy .env.example .env
```

`.env` 示例：

```env
DATABASE_URL=mysql+pymysql://root:你的密码@127.0.0.1:3306/visitor_system?charset=utf8mb4
CORS_ORIGINS=http://localhost:5173,http://localhost:5174
```

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端启动时会自动创建表，并在没有接待人员时写入 3 条演示人员数据。

### 3. 启动客户填报端

```bash
cd frontend-customer
npm install
npm run dev
```

访问：`http://localhost:5173`

### 4. 启动管理员 + 接待端

```bash
cd frontend-admin
npm install
npm run dev
```

访问：`http://localhost:5174`

## WorkBuddy Agent 配置

在 WorkBuddy 平台创建 4 个独立 Agent 后，将 Agent ID 填入后端 `.env`：

```env
# WorkBuddy 平台连接
WORKBUDDY_BASE_URL=https://api.workbuddy.cn
WORKBUDDY_API_KEY=your_api_key
WORKBUDDY_TIMEOUT_SECONDS=15

# 4 个 Agent ID（在 WorkBuddy 平台创建后填入）
WORKBUDDY_COLLECT_AGENT_ID=agent_collect_xxxx     # 信息收集 Agent
WORKBUDDY_ASSIGN_AGENT_ID=agent_assign_xxxx       # 智能分配 Agent
WORKBUDDY_TRACK_AGENT_ID=agent_track_xxxx         # 进度跟踪 Agent
WORKBUDDY_REPORT_AGENT_ID=agent_report_xxxx       # 汇报总结 Agent
```

### Agent System Prompt 参考

**信息收集 Agent**：引导访客多轮对话，结构化提取姓名、单位、来访事由、接待需求等信息。

**智能分配 Agent**：输入客户需求 + 接待人员技能与负载，输出分配建议：

```json
{
  "suggestions": [
    {
      "task_id": 1,
      "task_type": "pickup",
      "suggested_assignee_id": 1,
      "suggested_assignee_name": "张敏",
      "reason": "具备交通接待经验且当前可用"
    }
  ]
}
```

**进度跟踪 Agent**：扫描超时未完成的任务，生成告警列表，提醒管理员关注。

**汇报总结 Agent**：按日期汇总接待数据，生成日报（完成数、异常数、效率指标等）。

## 业务流程

1. **信息收集**：客户提交接站、送站、住宿、用餐需求 → 信息收集 Agent 结构化提取。
2. **任务生成**：后端根据需求自动创建对应接待任务。
3. **智能分配**：管理员调用智能分配 Agent → 获取人员匹配建议 → 确认分配。
4. **进度跟踪**：进度跟踪 Agent 自动扫描超时/异常任务 → 生成告警。
5. **状态更新**：接待人员在"我的任务"更新进行中、已完成或异常状态。
6. **汇报总结**：汇报总结 Agent 生成接待日报和数据洞察。
7. **数据看板**：首页展示客户数、待分配、完成率、异常数等核心指标。

## Agent 协同面板

管理员端内置 Agent 协同面板，提供：

- **4 个 Agent 状态卡片**：实时显示各 Agent 连接状态和在线信息
- **对话交互区域**：选择任意 Agent 进行对话式交互
- **一键操作**：快速触发分配建议、进度告警、日报生成
