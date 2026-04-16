import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import {
  Button,
  Col,
  Drawer,
  Form,
  Input,
  InputNumber,
  Popconfirm,
  Row,
  Select,
  Space,
  Table,
  Typography,
  message,
} from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';

import api from '../api/client';
import SectionCard from '../components/SectionCard';
import StatusTag from '../components/StatusTag';
import { useAuth } from '../auth/useAuth';
import { resourceConfig } from '../config/resources';

function renderField(field, optionsMap) {
  if (field.type === 'textarea') {
    return <Input.TextArea rows={4} />;
  }
  if (field.type === 'number') {
    return <InputNumber style={{ width: '100%' }} min={0} />;
  }
  if (field.type === 'password') {
    return <Input.Password />;
  }
  if (field.type === 'select') {
    const options = field.options?.static || (optionsMap[field.options?.endpoint] || []).map((item) => ({
      label: item[field.options?.labelField || 'label'],
      value: item[field.options?.valueField || 'value'],
    }));
    return <Select allowClear options={options} />;
  }
  if (field.type === 'datetime') {
    return <Input type="datetime-local" />;
  }
  return <Input />;
}

function ResourcePage() {
  const { resourceKey } = useParams();
  const { hasPermission } = useAuth();
  const config = resourceConfig[resourceKey];
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [optionsMap, setOptionsMap] = useState({});
  const [form] = Form.useForm();

  const canManage = useMemo(() => {
    if (!config) {
      return false;
    }
    const managePermission = config.managePermission
      || (config.permission.endsWith('.view') ? config.permission.replace('.view', '.manage') : config.permission);
    return hasPermission(managePermission);
  }, [config, hasPermission]);

  useEffect(() => {
    if (!config) {
      return;
    }
    const optionEndpoints = [...new Set(
      config.fields
        .filter((field) => field.type === 'select' && field.options?.endpoint)
        .map((field) => field.options.endpoint),
    )];

    Promise.all(optionEndpoints.map((endpoint) => api.get(endpoint)))
      .then((responses) => {
        const nextOptions = {};
        optionEndpoints.forEach((endpoint, index) => {
          nextOptions[endpoint] = responses[index].data.items || [];
        });
        setOptionsMap(nextOptions);
      })
      .catch(() => {
        message.error('Khong tai duoc du lieu phu tro.');
      });
  }, [config]);

  const fetchItems = useCallback(async () => {
    if (!config) {
      return;
    }
    setLoading(true);
    try {
      const response = await api.get(config.endpoint);
      setItems(response.data.items || []);
    } catch (error) {
      message.error(error.response?.data?.message || 'Khong tai duoc du lieu.');
    } finally {
      setLoading(false);
    }
  }, [config]);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  if (!config) {
    return <Typography.Text>Khong tim thay cau hinh module.</Typography.Text>;
  }

  const columns = [
    ...config.columns.map((column) => ({
      ...column,
      render: column.type === 'status'
        ? (value) => <StatusTag value={value} />
        : column.render
          ? (value) => column.render(value)
          : undefined,
    })),
    ...(canManage
      ? [
          {
            title: 'Thao tac',
            key: 'action',
            render: (_, record) => (
              <Space>
                <Button
                  size="small"
                  onClick={() => {
                    setEditingItem(record);
                    form.setFieldsValue(
                      Object.fromEntries(
                        config.fields.map((field) => {
                          let value = record[field.name];
                          if (field.type === 'datetime' && value) {
                            value = dayjs(value).format('YYYY-MM-DDTHH:mm');
                          }
                          return [field.name, value];
                        }),
                      ),
                    );
                    setOpen(true);
                  }}
                >
                  Sua
                </Button>
                <Popconfirm
                  title="Xoa ban ghi nay?"
                  onConfirm={async () => {
                    try {
                      await api.delete(`${config.endpoint}/${record.id}`);
                      message.success('Da xoa ban ghi.');
                      fetchItems();
                    } catch (error) {
                      message.error(error.response?.data?.message || 'Khong the xoa ban ghi.');
                    }
                  }}
                >
                  <Button size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>
              </Space>
            ),
          },
        ]
      : []),
  ];

  return (
    <Space orientation="vertical" size={18} style={{ width: '100%' }}>
      <div>
        <h1 className="page-title">{config.title}</h1>
        <p className="page-subtitle">{config.subtitle}</p>
      </div>
      <SectionCard
        title={config.title}
        subtitle={`${items.length} ban ghi`}
        extra={canManage ? (
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingItem(null);
              form.resetFields();
              setOpen(true);
            }}
          >
            Tao moi
          </Button>
        ) : null}
      >
        <Table rowKey="id" columns={columns} dataSource={items} loading={loading} scroll={{ x: 960 }} />
      </SectionCard>

      <Drawer
        title={editingItem ? `Cap nhat ${config.title}` : `Tao ${config.title}`}
        open={open}
        onClose={() => setOpen(false)}
        size="large"
        destroyOnHidden
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={async (values) => {
            const payload = Object.fromEntries(
              Object.entries(values).map(([key, value]) => [key, value === undefined ? null : value]),
            );
            config.fields.forEach((field) => {
              if (field.type === 'datetime' && payload[field.name]) {
                payload[field.name] = new Date(payload[field.name]).toISOString();
              }
            });
            try {
              if (editingItem) {
                await api.put(`${config.endpoint}/${editingItem.id}`, payload);
                message.success('Cap nhat thanh cong.');
              } else {
                await api.post(config.endpoint, payload);
                message.success('Tao moi thanh cong.');
              }
              setOpen(false);
              form.resetFields();
              fetchItems();
            } catch (error) {
              message.error(error.response?.data?.message || 'Khong luu duoc du lieu.');
            }
          }}
        >
          <Row gutter={16}>
            {config.fields.map((field) => (
              <Col span={12} key={field.name}>
                <Form.Item
                  label={field.label}
                  name={field.name}
                  rules={field.required ? [{ required: true, message: `Nhap ${field.label.toLowerCase()}` }] : []}
                >
                  {renderField(field, optionsMap)}
                </Form.Item>
              </Col>
            ))}
          </Row>
          <Space>
            <Button type="primary" htmlType="submit">
              Luu
            </Button>
            <Button onClick={() => setOpen(false)}>Dong</Button>
          </Space>
        </Form>
      </Drawer>
    </Space>
  );
}

export default ResourcePage;
