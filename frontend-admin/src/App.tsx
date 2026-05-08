import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  App as AntApp,
  Badge,
  Button,
  Card,
  Descriptions,
  Drawer,
  Empty,
  Form,
  Layout,
  List,
  Modal,
  Progress,
  Select,
  Space,
  Statistic,
  Table,
  Tabs,
  Tag,
  Typography
} from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { api } from "./api";
import { statusColor, statusLabel, taskTypeLabel } from "./labels";
import type {
  AgentSuggestionItem,
  DashboardSummary,
  Task,
  TaskStatus,
  User,
  Visitor
} from "./types";

const { Header, Content } = Layout;
const { Title, Text } = Typography;

const statusOptions = [
  { label: "全部", value: "" },
  { label: "待分配", value: "pending_assignment" },
  { label: "已分配", value: "assigned" },
  { label: "进行中", value: "in_progress" },
  { label: "已完成", value: "completed" },
  { label: "异常", value: "exception" }
];

function formatTime(value?: string) {
  return value ? dayjs(value).format("YYYY-MM-DD HH:mm") : "-";
}

function StatusTag({ status }: { status: TaskStatus }) {
  return <Tag color={statusColor[status]}>{statusLabel[status]}</Tag>;
}

function DetailBlock({ value }: { value: Record<string, unknown> }) {
  const entries = Object.entries(value ?? {});
  if (!entries.length) return <Text type="secondary">无详情</Text>;
  return (
    <Space wrap>
      {entries.map(([key, item]) => (
        <Tag key={key}>
          {key}: {String(item)}
        </Tag>
      ))}
    </Space>
  );
}

export default function App() {
  return (
    <AntApp>
      <Shell />
    </AntApp>
  );
}

function Shell() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [visitors, setVisitors] = useState<Visitor[]>([]);
  const [staff, setStaff] = useState<User[]>([]);
  const [status, setStatus] = useState("");
  const [activeVisitor, setActiveVisitor] = useState<Visitor | null>(null);
  const [assigningVisitor, setAssigningVisitor] = useState<Visitor | null>(null);
  const [loading, setLoading] = useState(false);
  const { message } = AntApp.useApp();

  async function refresh(nextStatus = status) {
    setLoading(true);
    try {
      const [summaryData, visitorData, staffData] = await Promise.all([
        api.summary(),
        api.visitors(nextStatus || undefined),
        api.staff()
      ]);
      setSummary(summaryData);
      setVisitors(visitorData);
      setStaff(staffData);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh("");
  }, []);

  const completion = summary?.total_tasks
    ? Math.round((summary.completed_tasks / summary.total_tasks) * 100)
    : 0;

  const visitorColumns: ColumnsType<Visitor> = [
    {
      title: "客户",
      dataIndex: "name",
      render: (_: string, row: Visitor) => (
        <div>
          <strong>{row.name}</strong>
          <div className="muted">{row.company}</div>
        </div>
      )
    },
    { title: "到访时间", dataIndex: "visit_time", render: formatTime },
    { title: "人数", dataIndex: "people_count" },
    {
      title: "需求",
      render: (_: unknown, row: Visitor) => (
        <Space wrap>
          {row.requirements.map((item) => (
            <Tag key={item.id}>{taskTypeLabel[item.type]}</Tag>
          ))}
        </Space>
      )
    },
    { title: "状态", dataIndex: "status", render: (value: TaskStatus) => <StatusTag status={value} /> },
    {
      title: "操作",
      render: (_: unknown, row: Visitor) => (
        <Space>
          <Button size="small" onClick={() => setActiveVisitor(row)}>
            详情
          </Button>
          <Button size="small" type="primary" onClick={() => setAssigningVisitor(row)}>
            分配
          </Button>
        </Space>
      )
    }
  ];

  return (
    <Layout className="app-shell">
      <Header className="topbar">
        <div>
          <Text className="eyebrow">Reception Command</Text>
          <Title level={3}>客户接待管理台</Title>
        </div>
        <Space>
          <Badge status="processing" text="WorkBuddy Agent Ready" />
          <Button onClick={() => refresh()}>刷新</Button>
        </Space>
      </Header>
      <Content className="content">
        <Tabs
          items={[
            {
              key: "dashboard",
              label: (
                <span>
                  首页概览
                </span>
              ),
              children: (
                <>
                  <div className="metric-grid">
                    <Card><Statistic title="总客户数" value={summary?.total_visitors ?? 0} /></Card>
                    <Card><Statistic title="待分配" value={summary?.pending_assignment ?? 0} /></Card>
                    <Card><Statistic title="已完成" value={summary?.completed ?? 0} /></Card>
                    <Card><Statistic title="异常" value={summary?.exception ?? 0} /></Card>
                  </div>
                  <Card className="section-card">
                    <Space align="center" className="wide-space">
                      <div>
                        <Title level={4}>任务完成率</Title>
                        <Text type="secondary">
                          已完成 {summary?.completed_tasks ?? 0} / 总任务 {summary?.total_tasks ?? 0}
                        </Text>
                      </div>
                      <Progress type="circle" percent={completion} />
                    </Space>
                  </Card>
                  <div className="quick-grid">
                    <Card>客户需求集中管理</Card>
                    <Card>Agent 推荐接待人员</Card>
                    <Card>接待人员实时更新状态</Card>
                  </div>
                </>
              )
            },
            {
              key: "visitors",
              label: (
                <span>
                  需求管理
                </span>
              ),
              children: (
                <Card className="section-card">
                  <Space className="toolbar">
                    <Select
                      value={status}
                      options={statusOptions}
                      className="status-select"
                      onChange={(value) => {
                        setStatus(value);
                        refresh(value);
                      }}
                    />
                  </Space>
                  <Table
                    rowKey="id"
                    loading={loading}
                    columns={visitorColumns}
                    dataSource={visitors}
                    pagination={{ pageSize: 8 }}
                  />
                </Card>
              )
            },
            {
              key: "tasks",
              label: (
                <span>
                  我的任务
                </span>
              ),
              children: <MyTasks staff={staff} />
            }
          ]}
        />
      </Content>

      <VisitorDrawer visitor={activeVisitor} onClose={() => setActiveVisitor(null)} />
      <AssignModal
        visitor={assigningVisitor}
        staff={staff}
        onClose={() => setAssigningVisitor(null)}
        onDone={() => {
          setAssigningVisitor(null);
          refresh();
        }}
      />
    </Layout>
  );
}

function VisitorDrawer({
  visitor,
  onClose
}: {
  visitor: Visitor | null;
  onClose: () => void;
}) {
  return (
    <Drawer width={640} open={Boolean(visitor)} title="客户需求详情" onClose={onClose}>
      {visitor && (
        <Space direction="vertical" size="large" className="full-width">
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="客户">{visitor.name}</Descriptions.Item>
            <Descriptions.Item label="单位">{visitor.company}</Descriptions.Item>
            <Descriptions.Item label="电话">{visitor.phone}</Descriptions.Item>
            <Descriptions.Item label="人数">{visitor.people_count}</Descriptions.Item>
            <Descriptions.Item label="到访时间">{formatTime(visitor.visit_time)}</Descriptions.Item>
            <Descriptions.Item label="状态"><StatusTag status={visitor.status} /></Descriptions.Item>
            <Descriptions.Item label="备注" span={2}>{visitor.remark || "-"}</Descriptions.Item>
          </Descriptions>
          <List
            header="需求明细"
            dataSource={visitor.requirements}
            renderItem={(item) => (
              <List.Item>
                <List.Item.Meta
                  title={`${taskTypeLabel[item.type]} · ${statusLabel[item.status]}`}
                  description={<DetailBlock value={item.detail} />}
                />
              </List.Item>
            )}
          />
          <List
            header="任务分配"
            dataSource={visitor.tasks}
            renderItem={(item) => (
              <List.Item>
                <List.Item.Meta
                  title={`${taskTypeLabel[item.task_type]} #${item.id}`}
                  description={item.assignee ? `负责人：${item.assignee.name}` : "暂未分配"}
                />
                <StatusTag status={item.status} />
              </List.Item>
            )}
          />
        </Space>
      )}
    </Drawer>
  );
}

function AssignModal({
  visitor,
  staff,
  onClose,
  onDone
}: {
  visitor: Visitor | null;
  staff: User[];
  onClose: () => void;
  onDone: () => void;
}) {
  const [form] = Form.useForm<Record<string, number>>();
  const [suggestions, setSuggestions] = useState<AgentSuggestionItem[]>([]);
  const [loading, setLoading] = useState(false);
  const { message } = AntApp.useApp();

  useEffect(() => {
    form.resetFields();
    setSuggestions([]);
  }, [visitor?.id]);

  async function suggest() {
    if (!visitor) return;
    setLoading(true);
    try {
      const data = await api.suggest(visitor.id);
      setSuggestions(data.suggestions);
      const fields = Object.fromEntries(
        data.suggestions
          .filter((item) => item.suggested_assignee_id)
          .map((item) => [`task_${item.task_id}`, item.suggested_assignee_id])
      );
      form.setFieldsValue(fields);
      message.success(data.summary);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "推荐失败");
    } finally {
      setLoading(false);
    }
  }

  async function submit() {
    if (!visitor) return;
    const values = await form.validateFields();
    const assignments = visitor.tasks.map((task) => ({
      task_id: task.id,
      assignee_id: values[`task_${task.id}`]
    }));
    setLoading(true);
    try {
      await api.assign(assignments);
      message.success("任务已分配");
      onDone();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "分配失败");
    } finally {
      setLoading(false);
    }
  }

  const suggestionMap = useMemo(
    () => new Map(suggestions.map((item) => [item.task_id, item])),
    [suggestions]
  );

  return (
    <Modal
      width={720}
      open={Boolean(visitor)}
      title="接待任务分配"
      onCancel={onClose}
      onOk={submit}
      confirmLoading={loading}
      okText="确认分配"
    >
      {visitor ? (
        <Space direction="vertical" className="full-width">
          <Alert
            type="info"
            showIcon
            message="可先调用 WorkBuddy Agent 生成推荐，再由管理员确认生效。"
          />
          <Button loading={loading} onClick={suggest}>
            Agent 推荐分配
          </Button>
          <Form form={form} layout="vertical">
            {visitor.tasks.map((task) => {
              const suggestion = suggestionMap.get(task.id);
              return (
                <Card key={task.id} size="small" className="task-card">
                  <Form.Item
                    name={`task_${task.id}`}
                    label={`${taskTypeLabel[task.task_type]}任务 #${task.id}`}
                    rules={[{ required: true, message: "请选择接待人员" }]}
                  >
                    <Select
                      placeholder="选择接待人员"
                      options={staff.map((item) => ({
                        label: `${item.name} · ${item.department ?? "接待"}`,
                        value: item.id
                      }))}
                    />
                  </Form.Item>
                  {suggestion && <Text type="secondary">{suggestion.reason}</Text>}
                </Card>
              );
            })}
          </Form>
        </Space>
      ) : null}
    </Modal>
  );
}

function MyTasks({ staff }: { staff: User[] }) {
  const [assigneeId, setAssigneeId] = useState<number | undefined>();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const { message } = AntApp.useApp();

  async function load(id = assigneeId) {
    if (!id) return;
    setLoading(true);
    try {
      setTasks(await api.myTasks(id));
    } catch (error) {
      message.error(error instanceof Error ? error.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function update(task: Task, status: TaskStatus) {
    setLoading(true);
    try {
      await api.updateTask(task.id, status);
      message.success("状态已更新");
      load();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "更新失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="section-card">
      <Space className="toolbar">
        <Select
          placeholder="选择接待人员"
          className="staff-select"
          value={assigneeId}
          options={staff.map((item) => ({
            label: `${item.name} · ${item.department ?? "接待"}`,
            value: item.id
          }))}
          onChange={(value) => {
            setAssigneeId(value);
            load(value);
          }}
        />
        <Button onClick={() => load()} disabled={!assigneeId}>
          刷新任务
        </Button>
      </Space>
      {!assigneeId ? (
        <Empty description="请选择接待人员查看任务" />
      ) : (
        <Table
          rowKey="id"
          loading={loading}
          dataSource={tasks}
          pagination={{ pageSize: 8 }}
          columns={[
            {
              title: "客户",
              render: (_: unknown, row: Task) => (
                <div>
                  <strong>{row.visitor?.name ?? `#${row.visitor_id}`}</strong>
                  <div className="muted">{row.visitor?.company ?? "-"}</div>
                </div>
              )
            },
            {
              title: "任务",
              dataIndex: "task_type",
              render: (value: Task["task_type"]) => taskTypeLabel[value]
            },
            { title: "截止时间", dataIndex: "deadline", render: formatTime },
            {
              title: "状态",
              dataIndex: "status",
              render: (value: TaskStatus) => <StatusTag status={value} />
            },
            {
              title: "操作",
              render: (_: unknown, row: Task) => (
                <Space>
                  <Button size="small" onClick={() => update(row, "in_progress")}>
                    开始
                  </Button>
                  <Button size="small" type="primary" onClick={() => update(row, "completed")}>
                    完成
                  </Button>
                  <Button size="small" danger onClick={() => update(row, "exception")}>
                    异常
                  </Button>
                </Space>
              )
            }
          ]}
        />
      )}
    </Card>
  );
}
