import { PlusOutlined } from '@ant-design/icons';
import {
  Button,
  Col,
  Form,
  Input,
  Modal,
  Row,
  Select,
  Space,
  Table,
  message,
} from 'antd';
import { useEffect, useState } from 'react';

import api from '../api/client';
import { useAuth } from '../auth/useAuth';
import SectionCard from '../components/SectionCard';
import StatusTag from '../components/StatusTag';
import { formatDateTime } from '../utils/format';

function ShipmentPage() {
  const { hasPermission } = useAuth();
  const [items, setItems] = useState([]);
  const [receipts, setReceipts] = useState([]);
  const [users, setUsers] = useState([]);
  const [form] = Form.useForm();
  const [open, setOpen] = useState(false);

  const canManage = hasPermission('shipments.manage');

  const fetchAll = async () => {
    try {
      const [shipmentResponse, receiptResponse, userResponse] = await Promise.all([
        api.get('/shipments'),
        api.get('/export-receipts'),
        api.get('/directory/users'),
      ]);
      setItems(shipmentResponse.data.items || []);
      setReceipts((receiptResponse.data.items || []).filter((item) => item.status === 'confirmed'));
      setUsers(userResponse.data.items || []);
    } catch (error) {
      message.error(error.response?.data?.message || 'Khong tai duoc du lieu van chuyen.');
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  return (
    <SectionCard
      title="Van don va giao hang"
      subtitle="Tao don tu phieu xuat da duyet va cap nhat trang thai giao hang."
      extra={canManage ? (
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => {
            form.resetFields();
            setOpen(true);
          }}
        >
          Tao van don
        </Button>
      ) : null}
    >
      <Table
        rowKey="id"
        dataSource={items}
        scroll={{ x: 1200 }}
        columns={[
          { title: 'Ma van don', dataIndex: 'shipment_code' },
          { title: 'Phieu xuat', dataIndex: 'export_receipt_code' },
          { title: 'Nguoi giao', dataIndex: 'assigned_to_name' },
          { title: 'Dia chi giao', dataIndex: 'delivery_address' },
          { title: 'Du kien', dataIndex: 'expected_delivery_at', render: formatDateTime },
          { title: 'Da giao', dataIndex: 'delivered_at', render: formatDateTime },
          { title: 'Trang thai', dataIndex: 'shipping_status', render: (value) => <StatusTag value={value} /> },
          {
            title: 'Cap nhat nhanh',
            key: 'actions',
            render: (_, record) => (
              <Select
                value={record.shipping_status}
                style={{ width: 180 }}
                options={[
                  'pending',
                  'preparing',
                  'delivering',
                  'delivered',
                  'failed',
                  'returned',
                ].map((value) => ({ label: value, value }))}
                onChange={async (value) => {
                  try {
                    await api.patch(`/shipments/${record.id}/status`, { shipping_status: value });
                    message.success('Da cap nhat van don.');
                    fetchAll();
                  } catch (error) {
                    message.error(error.response?.data?.message || 'Khong cap nhat duoc van don.');
                  }
                }}
              />
            ),
          },
        ]}
      />

      <Modal
        title="Tao van don"
        open={open}
        onCancel={() => setOpen(false)}
        footer={null}
        destroyOnHidden
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={async (values) => {
            try {
              await api.post('/shipments', {
                ...values,
                expected_delivery_at: values.expected_delivery_at
                  ? new Date(values.expected_delivery_at).toISOString()
                  : null,
              });
              message.success('Da tao van don.');
              setOpen(false);
              fetchAll();
            } catch (error) {
              message.error(error.response?.data?.message || 'Khong tao duoc van don.');
            }
          }}
        >
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item name="export_receipt_id" label="Phieu xuat" rules={[{ required: true }]}>
                <Select options={receipts.map((item) => ({ label: `${item.receipt_code} - ${item.customer_name || 'Khach le'}`, value: item.id }))} />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item name="assigned_to" label="Nguoi giao">
                <Select allowClear options={users.map((item) => ({ label: `${item.full_name} (${item.role})`, value: item.id }))} />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item name="delivery_address" label="Dia chi giao" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="expected_delivery_at" label="Du kien giao">
                <Input type="datetime-local" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="note" label="Ghi chu">
                <Input />
              </Form.Item>
            </Col>
          </Row>
          <Space>
            <Button type="primary" htmlType="submit">Luu</Button>
            <Button onClick={() => setOpen(false)}>Dong</Button>
          </Space>
        </Form>
      </Modal>
    </SectionCard>
  );
}

export default ShipmentPage;
