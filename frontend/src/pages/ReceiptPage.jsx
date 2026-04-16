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
  Tag,
  message,
} from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import api from '../api/client';
import SectionCard from '../components/SectionCard';
import StatusTag from '../components/StatusTag';
import { formatCurrency, formatDateTime } from '../utils/format';

function ReceiptPage({ kind }) {
  const endpoint = kind === 'import' ? '/import-receipts' : '/export-receipts';
  const title = kind === 'import' ? 'Nhap kho' : 'Xuat kho';
  const partnerField = kind === 'import' ? 'supplier_id' : 'customer_id';
  const partnerEndpoint = kind === 'import' ? '/suppliers' : '/customers';
  const partnerLabel = kind === 'import' ? 'Nha cung cap' : 'Khach hang';

  const [items, setItems] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [locations, setLocations] = useState([]);
  const [products, setProducts] = useState([]);
  const [partners, setPartners] = useState([]);
  const [form] = Form.useForm();
  const [open, setOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const fetchAll = useCallback(async () => {
    try {
      const [listResponse, warehouseResponse, locationResponse, productResponse, partnerResponse] = await Promise.all([
        api.get(endpoint),
        api.get('/warehouses'),
        api.get('/locations'),
        api.get('/products'),
        api.get(partnerEndpoint),
      ]);
      setItems(listResponse.data.items || []);
      setWarehouses(warehouseResponse.data.items || []);
      setLocations(locationResponse.data.items || []);
      setProducts(productResponse.data.items || []);
      setPartners(partnerResponse.data.items || []);
    } catch (error) {
      message.error(error.response?.data?.message || `Khong tai duoc du lieu ${title.toLowerCase()}.`);
    }
  }, [endpoint, partnerEndpoint, title]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const partnerOptions = useMemo(
    () => partners.map((item) => ({
      label: item.supplier_name || item.customer_name,
      value: item.id,
    })),
    [partners],
  );

  return (
    <SectionCard
      title={title}
      subtitle={`Quan ly phieu ${kind === 'import' ? 'nhap' : 'xuat'} va xac nhan cap nhat ton kho.`}
      extra={(
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => {
            setEditingItem(null);
            form.resetFields();
            form.setFieldsValue({ items: [{ quantity: 1, unit_price: 0 }] });
            setOpen(true);
          }}
        >
          Tao phieu
        </Button>
      )}
    >
      <Table
        rowKey="id"
        dataSource={items}
        scroll={{ x: 1200 }}
        columns={[
          { title: 'Ma phieu', dataIndex: 'receipt_code' },
          { title: 'Kho', dataIndex: 'warehouse_name' },
          { title: partnerLabel, dataIndex: kind === 'import' ? 'supplier_name' : 'customer_name' },
          { title: 'Tong tien', dataIndex: 'total_amount', render: formatCurrency },
          { title: 'Ngay tao', dataIndex: kind === 'import' ? 'import_date' : 'export_date', render: formatDateTime },
          { title: 'Trang thai', dataIndex: 'status', render: (value) => <StatusTag value={value} /> },
          {
            title: 'Items',
            dataIndex: 'items',
            render: (value) => <Tag color="blue">{value?.length || 0} dong</Tag>,
          },
          {
            title: 'Thao tac',
            key: 'action',
            render: (_, record) => (
              <Space wrap>
                <Button
                  size="small"
                  onClick={() => {
                    setEditingItem(record);
                    form.setFieldsValue({
                      warehouse_id: record.warehouse_id,
                      [partnerField]: record[partnerField],
                      note: record.note,
                      items: record.items?.map((item) => ({
                        product_id: item.product_id,
                        location_id: item.location_id,
                        quantity: item.quantity,
                        unit_price: item.unit_price,
                      })),
                    });
                    setOpen(true);
                  }}
                  disabled={record.status !== 'draft'}
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
                      await api.post(`${endpoint}/${record.id}/confirm`);
                      message.success('Da xac nhan phieu.');
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
                      await api.post(`${endpoint}/${record.id}/cancel`);
                      message.success('Da huy phieu.');
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
        expandable={{
          expandedRowRender: (record) => (
            <Table
              rowKey="id"
              pagination={false}
              dataSource={record.items || []}
              columns={[
                { title: 'San pham', dataIndex: 'product_name' },
                { title: 'Vi tri', dataIndex: 'location_name' },
                { title: 'So luong', dataIndex: 'quantity' },
                { title: 'Don gia', dataIndex: 'unit_price', render: formatCurrency },
                { title: 'Thanh tien', dataIndex: 'total_price', render: formatCurrency },
              ]}
            />
          ),
        }}
      />

      <Modal
        title={editingItem ? `Cap nhat phieu ${title.toLowerCase()}` : `Tao phieu ${title.toLowerCase()}`}
        open={open}
        onCancel={() => setOpen(false)}
        footer={null}
        width={980}
        destroyOnHidden
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={async (values) => {
            setSubmitting(true);
            try {
              if (editingItem) {
                await api.put(`${endpoint}/${editingItem.id}`, values);
                message.success('Cap nhat phieu thanh cong.');
              } else {
                await api.post(endpoint, values);
                message.success('Tao phieu thanh cong.');
              }
              setOpen(false);
              fetchAll();
            } catch (error) {
              message.error(error.response?.data?.message || 'Khong luu duoc phieu.');
            } finally {
              setSubmitting(false);
            }
          }}
        >
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="warehouse_id" label="Kho" rules={[{ required: true }]}>
                <Select options={warehouses.map((item) => ({ label: item.warehouse_name, value: item.id }))} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name={partnerField} label={partnerLabel}>
                <Select allowClear options={partnerOptions} />
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
                  <Row gutter={12} key={field.key} align="middle">
                    <Col span={7}>
                      <Form.Item name={[field.name, 'product_id']} label="San pham" rules={[{ required: true }]}>
                        <Select options={products.map((item) => ({ label: item.product_name, value: item.id }))} />
                      </Form.Item>
                    </Col>
                    <Col span={6}>
                      <Form.Item name={[field.name, 'location_id']} label="Vi tri" rules={[{ required: true }]}>
                        <Select options={locations.map((item) => ({ label: `${item.warehouse_name} / ${item.bin_code}`, value: item.id }))} />
                      </Form.Item>
                    </Col>
                    <Col span={4}>
                      <Form.Item name={[field.name, 'quantity']} label="So luong" rules={[{ required: true }]}>
                        <InputNumber style={{ width: '100%' }} min={0.01} />
                      </Form.Item>
                    </Col>
                    <Col span={5}>
                      <Form.Item name={[field.name, 'unit_price']} label="Don gia" rules={[{ required: true }]}>
                        <InputNumber style={{ width: '100%' }} min={0} />
                      </Form.Item>
                    </Col>
                    <Col span={2}>
                      <Button danger onClick={() => remove(field.name)}>
                        Xoa
                      </Button>
                    </Col>
                  </Row>
                ))}
                <Button onClick={() => add({ quantity: 1, unit_price: 0 })}>Them dong</Button>
              </Space>
            )}
          </Form.List>

          <Space style={{ marginTop: 18 }}>
            <Button type="primary" htmlType="submit" loading={submitting}>
              Luu phieu
            </Button>
            <Button onClick={() => setOpen(false)}>Dong</Button>
          </Space>
        </Form>
      </Modal>
    </SectionCard>
  );
}

export default ReceiptPage;
