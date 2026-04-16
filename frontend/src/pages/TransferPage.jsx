import { CheckCircleOutlined, CloseCircleOutlined, PlusOutlined } from '@ant-design/icons';
import {
  Button,
  Col,
  Form,
  Input,
  InputNumber,
  Modal,
  Row,
  Select,
  Space,
  Table,
  message,
} from 'antd';
import { useEffect, useState } from 'react';

import api from '../api/client';
import SectionCard from '../components/SectionCard';
import StatusTag from '../components/StatusTag';
import { formatDateTime } from '../utils/format';

function TransferPage() {
  const [items, setItems] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [locations, setLocations] = useState([]);
  const [products, setProducts] = useState([]);
  const [form] = Form.useForm();
  const [open, setOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);

  const fetchAll = async () => {
    try {
      const [transferResponse, warehouseResponse, locationResponse, productResponse] = await Promise.all([
        api.get('/stock-transfers'),
        api.get('/warehouses'),
        api.get('/locations'),
        api.get('/products'),
      ]);
      setItems(transferResponse.data.items || []);
      setWarehouses(warehouseResponse.data.items || []);
      setLocations(locationResponse.data.items || []);
      setProducts(productResponse.data.items || []);
    } catch (error) {
      message.error(error.response?.data?.message || 'Khong tai duoc dieu chuyen kho.');
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  return (
    <SectionCard
      title="Dieu chuyen kho"
      subtitle="Theo doi luong hang di chuyen giua cac kho va cap nhat movement hai chieu."
      extra={(
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => {
            setEditingItem(null);
            form.resetFields();
            form.setFieldsValue({ items: [{ quantity: 1 }] });
            setOpen(true);
          }}
        >
          Tao phieu dieu chuyen
        </Button>
      )}
    >
      <Table
        rowKey="id"
        dataSource={items}
        scroll={{ x: 1100 }}
        columns={[
          { title: 'Ma phieu', dataIndex: 'transfer_code' },
          { title: 'Kho nguon', dataIndex: 'source_warehouse_name' },
          { title: 'Kho dich', dataIndex: 'destination_warehouse_name' },
          { title: 'Ngay tao', dataIndex: 'transfer_date', render: formatDateTime },
          { title: 'Trang thai', dataIndex: 'status', render: (value) => <StatusTag value={value} /> },
          {
            title: 'Thao tac',
            key: 'actions',
            render: (_, record) => (
              <Space>
                <Button
                  size="small"
                  disabled={record.status !== 'draft'}
                  onClick={() => {
                    setEditingItem(record);
                    form.setFieldsValue({
                      source_warehouse_id: record.source_warehouse_id,
                      destination_warehouse_id: record.destination_warehouse_id,
                      note: record.note,
                      items: record.items?.map((item) => ({
                        product_id: item.product_id,
                        source_location_id: item.source_location_id,
                        destination_location_id: item.destination_location_id,
                        quantity: item.quantity,
                      })),
                    });
                    setOpen(true);
                  }}
                >
                  Sua
                </Button>
                <Button
                  size="small"
                  type="primary"
                  icon={<CheckCircleOutlined />}
                  disabled={record.status !== 'draft'}
                  onClick={async () => {
                    try {
                      await api.post(`/stock-transfers/${record.id}/confirm`);
                      message.success('Da xac nhan dieu chuyen.');
                      fetchAll();
                    } catch (error) {
                      message.error(error.response?.data?.message || 'Khong xac nhan duoc phieu.');
                    }
                  }}
                >
                  Xac nhan
                </Button>
                <Button
                  size="small"
                  danger
                  icon={<CloseCircleOutlined />}
                  disabled={record.status !== 'draft'}
                  onClick={async () => {
                    try {
                      await api.post(`/stock-transfers/${record.id}/cancel`);
                      message.success('Da huy phieu dieu chuyen.');
                      fetchAll();
                    } catch (error) {
                      message.error(error.response?.data?.message || 'Khong huy duoc phieu.');
                    }
                  }}
                >
                  Huy
                </Button>
              </Space>
            ),
          },
        ]}
      />

      <Modal
        title={editingItem ? 'Cap nhat phieu dieu chuyen' : 'Tao phieu dieu chuyen'}
        open={open}
        onCancel={() => setOpen(false)}
        footer={null}
        width={960}
        destroyOnHidden
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={async (values) => {
            try {
              if (editingItem) {
                await api.put(`/stock-transfers/${editingItem.id}`, values);
              } else {
                await api.post('/stock-transfers', values);
              }
              message.success('Da luu phieu dieu chuyen.');
              setOpen(false);
              fetchAll();
            } catch (error) {
              message.error(error.response?.data?.message || 'Khong luu duoc phieu.');
            }
          }}
        >
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="source_warehouse_id" label="Kho nguon" rules={[{ required: true }]}>
                <Select options={warehouses.map((item) => ({ label: item.warehouse_name, value: item.id }))} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="destination_warehouse_id" label="Kho dich" rules={[{ required: true }]}>
                <Select options={warehouses.map((item) => ({ label: item.warehouse_name, value: item.id }))} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="note" label="Ghi chu">
                <Input />
              </Form.Item>
            </Col>
          </Row>

          <Form.List name="items">
            {(fields, { add, remove }) => (
              <Space orientation="vertical" style={{ width: '100%' }}>
                {fields.map((field) => (
                  <Row gutter={12} key={field.key}>
                    <Col span={6}>
                      <Form.Item name={[field.name, 'product_id']} label="San pham" rules={[{ required: true }]}>
                        <Select options={products.map((item) => ({ label: item.product_name, value: item.id }))} />
                      </Form.Item>
                    </Col>
                    <Col span={6}>
                      <Form.Item name={[field.name, 'source_location_id']} label="Vi tri nguon" rules={[{ required: true }]}>
                        <Select options={locations.map((item) => ({ label: `${item.warehouse_name} / ${item.bin_code}`, value: item.id }))} />
                      </Form.Item>
                    </Col>
                    <Col span={6}>
                      <Form.Item name={[field.name, 'destination_location_id']} label="Vi tri dich" rules={[{ required: true }]}>
                        <Select options={locations.map((item) => ({ label: `${item.warehouse_name} / ${item.bin_code}`, value: item.id }))} />
                      </Form.Item>
                    </Col>
                    <Col span={4}>
                      <Form.Item name={[field.name, 'quantity']} label="So luong" rules={[{ required: true }]}>
                        <InputNumber min={0.01} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    <Col span={2}>
                      <Button danger onClick={() => remove(field.name)}>
                        Xoa
                      </Button>
                    </Col>
                  </Row>
                ))}
                <Button onClick={() => add({ quantity: 1 })}>Them dong</Button>
              </Space>
            )}
          </Form.List>

          <Space style={{ marginTop: 18 }}>
            <Button type="primary" htmlType="submit">Luu</Button>
            <Button onClick={() => setOpen(false)}>Dong</Button>
          </Space>
        </Form>
      </Modal>
    </SectionCard>
  );
}

export default TransferPage;
