# 客户接待助手工程

本目录包含三个工程：

- `backend`：Python FastAPI + MySQL 后端，含 WorkBuddy Agent 适配层。
- `frontend-customer`：客户自助填报端，React + TypeScript + Ant Design。
- `frontend-admin`：管理员 + 接待人员 Web 端，React + TypeScript + Ant Design。

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
D:\conda\conda\python.exe -m pip install -r requirements.txt
D:\conda\conda\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
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

后端已预留 WorkBuddy HTTP 适配器。配置以下变量后，`/api/agent/assign-suggest` 会调用 WorkBuddy；未配置或调用失败时，会使用本地规则推荐，便于演示。

```env
WORKBUDDY_BASE_URL=
WORKBUDDY_API_KEY=
WORKBUDDY_ASSIGN_AGENT_ID=
WORKBUDDY_TIMEOUT_SECONDS=12
```

推荐 Agent 输入包含客户、任务、接待人员及技能数据；输出建议格式：

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

## 已实现流程

1. 客户提交接站、送站、住宿、用餐需求。
2. 后端自动生成对应接待任务。
3. 管理员查看客户需求和任务详情。
4. 管理员调用 WorkBuddy Agent 获取分配建议。
5. 管理员确认接待人员分配。
6. 接待人员在“我的任务”更新进行中、已完成或异常状态。
7. 首页展示客户数、待分配、完成率、异常数等核心指标。
