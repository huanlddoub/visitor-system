import { useState } from "react";
import {
  Button,
  Checkbox,
  DatePicker,
  Form,
  Input,
  InputNumber,
  Result,
  Typography,
  message
} from "antd";
import dayjs from "dayjs";
import { createVisitor } from "./api";
import type { RequirementCreate, RequirementType, VisitorCreate, VisitorOut } from "./types";

const { Title } = Typography;

const requirementOptions = [
  { label: "接站", value: "pickup" },
  { label: "送站", value: "dropoff" },
  { label: "住宿", value: "hotel" },
  { label: "用餐", value: "meal" }
];

type FormValues = {
  name: string;
  company: string;
  phone: string;
  visit_time: dayjs.Dayjs;
  people_count: number;
  remark?: string;
  requirementTypes: RequirementType[];
  pickup?: Record<string, unknown>;
  dropoff?: Record<string, unknown>;
  hotel?: Record<string, unknown>;
  meal?: Record<string, unknown>;
};

type CheckboxValue = string | number | boolean;

function buildRequirements(values: FormValues): RequirementCreate[] {
  return values.requirementTypes.map((type) => ({
    type,
    detail: (values[type] ?? {}) as Record<string, unknown>
  }));
}

export default function App() {
  const [form] = Form.useForm<FormValues>();
  const [selected, setSelected] = useState<RequirementType[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [created, setCreated] = useState<VisitorOut | null>(null);

  async function handleFinish(values: FormValues) {
    const payload: VisitorCreate = {
      name: values.name,
      company: values.company,
      phone: values.phone,
      visit_time: values.visit_time.toISOString(),
      people_count: values.people_count,
      remark: values.remark,
      requirements: buildRequirements(values)
    };

    setSubmitting(true);
    try {
      const visitor = await createVisitor(payload);
      setCreated(visitor);
      message.success("需求已提交");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "提交失败");
    } finally {
      setSubmitting(false);
    }
  }

  if (created) {
    return (
      <main className="page">
        <Result
          status="success"
          title="接待需求已提交"
          subTitle={`接待编号 #${created.id}，当前状态：待分配`}
          extra={[
            <Button key="again" type="primary" onClick={() => setCreated(null)}>
              继续提交
            </Button>
          ]}
        />
      </main>
    );
  }

  return (
    <main className="page">
      <header className="app-header">
        <Title level={1}>客户接待助手</Title>
      </header>

      <section className="form-shell">
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            people_count: 1,
            requirementTypes: [],
            visit_time: dayjs().add(1, "day").hour(9).minute(0)
          }}
          onFinish={handleFinish}
          onValuesChange={(_: Partial<FormValues>, values: FormValues) =>
            setSelected(values.requirementTypes ?? [])
          }
        >
          <h2 className="section-title">基本信息</h2>
          <div className="grid two">
            <Form.Item name="name" label="客户姓名" rules={[{ required: true }]}>
              <Input placeholder="请输入姓名" />
            </Form.Item>
            <Form.Item name="company" label="来访单位" rules={[{ required: true }]}>
              <Input placeholder="请输入单位名称" />
            </Form.Item>
            <Form.Item name="phone" label="联系电话" rules={[{ required: true }]}>
              <Input placeholder="请输入手机号" />
            </Form.Item>
            <Form.Item name="people_count" label="来访人数" rules={[{ required: true }]}>
              <InputNumber min={1} max={500} className="full" />
            </Form.Item>
            <Form.Item name="visit_time" label="到访时间" rules={[{ required: true }]}>
              <DatePicker showTime className="full" />
            </Form.Item>
          </div>

          <h2 className="section-title">接待需求</h2>
          <Form.Item name="requirementTypes" className="requirements-item">
            <Checkbox.Group
              options={requirementOptions}
              onChange={(values: CheckboxValue[]) => setSelected(values as RequirementType[])}
            />
          </Form.Item>

          <div className="detail-grid">
            {selected.includes("pickup") && (
              <section className="detail-panel">
                <h3>接站详情</h3>
                <Form.Item name={["pickup", "station"]} label="到达站点">
                  <Input placeholder="机场 / 高铁站 / 车站" />
                </Form.Item>
                <Form.Item name={["pickup", "arrival_no"]} label="航班或车次">
                  <Input placeholder="如 CA1234 / G88" />
                </Form.Item>
                <Form.Item name={["pickup", "arrival_time"]} label="到达时间">
                  <DatePicker showTime className="full" />
                </Form.Item>
              </section>
            )}
            {selected.includes("dropoff") && (
              <section className="detail-panel">
                <h3>送站详情</h3>
                <Form.Item name={["dropoff", "station"]} label="出发站点">
                  <Input placeholder="机场 / 高铁站 / 车站" />
                </Form.Item>
                <Form.Item name={["dropoff", "departure_time"]} label="出发时间">
                  <DatePicker showTime className="full" />
                </Form.Item>
              </section>
            )}
            {selected.includes("hotel") && (
              <section className="detail-panel">
                <h3>住宿详情</h3>
                <Form.Item name={["hotel", "room_count"]} label="房间数">
                  <InputNumber min={1} className="full" />
                </Form.Item>
                <Form.Item name={["hotel", "preference"]} label="住宿偏好">
                  <Input placeholder="如大床房、双床房、近会场" />
                </Form.Item>
              </section>
            )}
            {selected.includes("meal") && (
              <section className="detail-panel">
                <h3>用餐详情</h3>
                <Form.Item name={["meal", "meal_time"]} label="用餐时间">
                  <DatePicker showTime className="full" />
                </Form.Item>
                <Form.Item name={["meal", "preference"]} label="餐饮偏好">
                  <Input placeholder="如清淡、素食、商务餐" />
                </Form.Item>
              </section>
            )}
          </div>

          <Form.Item name="remark" label="补充说明">
            <Input.TextArea rows={4} placeholder="特殊行程、随行人员或其他注意事项" />
          </Form.Item>

          <div className="actions">
            <Button
              onClick={() => {
                form.resetFields();
                setSelected([]);
              }}
            >
              重置
            </Button>
            <Button type="primary" htmlType="submit" loading={submitting}>
              提交需求
            </Button>
          </div>
        </Form>
      </section>
    </main>
  );
}
