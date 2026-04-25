import { EditOutlined, ReloadOutlined } from '@ant-design/icons';
import {
  Alert,
  Button,
  Card,
  Col,
  Empty,
  Form,
  Input,
  InputNumber,
  Row,
  Select,
  Space,
  Table,
  Tabs,
  Typography,
  message,
} from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import api from '../api/client';
import { useAuth } from '../auth/useAuth';
import SectionCard from '../components/SectionCard';
import StatusTag from '../components/StatusTag';
import { formatDateTime, formatNumber } from '../utils/format';

function InventoryPage() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission('inventory.manage');

  const [form] = Form.useForm();
  const watchedWarehouseId = Form.useWatch('warehouse_id', form);
  const watchedLocationId = Form.useWatch('location_id', form);
  const watchedProductId = Form.useWatch('product_id', form);
  const watchedActualQuantity = Form.useWatch('actual_quantity', form);

  const [loading, setLoading] = useState(false);
  const [adjusting, setAdjusting] = useState(false);
  const [inventory, setInventory] = useState([]);
  const [movements, setMovements] = useState([]);
  const [options, setOptions] = useState({
    warehouses: [],
    locations: [],
    products: [],
  });

  const fetchInventoryData = useCallback(async () => {
    setLoading(true);
    try {
      const [inventoryResponse, movementResponse] = await Promise.all([
        api.get('/inventory'),
        api.get('/inventory/movements'),
      ]);
      setInventory(inventoryResponse.data.items || []);
      setMovements(movementResponse.data.items || []);
    } catch (error) {
      message.error(error.response?.data?.message || 'Không tải được dữ liệu tồn kho.');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchOptions = useCallback(async () => {
    if (!canManage) {
      setOptions({
        warehouses: [],
        locations: [],
        products: [],
      });
      return;
    }

    try {
      const [warehouseResponse, locationResponse, productResponse] = await Promise.all([
        api.get('/warehouses', { params: { page: 1, page_size: 100 } }),
        api.get('/locations', { params: { page: 1, page_size: 100 } }),
        api.get('/products', { params: { page: 1, page_size: 100 } }),
      ]);

      setOptions({
        warehouses: warehouseResponse.data.items || [],
        locations: locationResponse.data.items || [],
        products: productResponse.data.items || [],
      });
    } catch (error) {
      message.error(error.response?.data?.message || 'Không tải được dữ liệu nền cho điều chỉnh tồn kho.');
    }
  }, [canManage]);

  useEffect(() => {
    fetchInventoryData();
  }, [fetchInventoryData]);

  useEffect(() => {
    fetchOptions();
  }, [fetchOptions]);

  useEffect(() => {
    form.setFieldValue('location_id', undefined);
  }, [form, watchedWarehouseId]);

  const summary = useMemo(() => {
    const warehouseCodes = new Set(inventory.map((item) => item.warehouse_code).filter(Boolean));
    const productCodes = new Set(inventory.map((item) => item.product_code).filter(Boolean));
    const totalQuantity = inventory.reduce((sum, item) => sum + Number(item.quantity || 0), 0);

    return {
      warehouseCount: warehouseCodes.size,
      productCount: productCodes.size,
      totalQuantity,
      movementCount: movements.length,
    };
  }, [inventory, movements]);

  const warehouseOptions = useMemo(
    () => options.warehouses.map((item) => ({
      label: `${item.warehouse_name} (${item.warehouse_code})`,
      value: item.id,
    })),
    [options.warehouses],
  );

  const locationOptions = useMemo(
    () => options.locations
      .filter((item) => !watchedWarehouseId || item.warehouse_id === watchedWarehouseId)
      .map((item) => ({
        label: `${item.location_name} (${item.location_code})`,
        value: item.id,
      })),
    [options.locations, watchedWarehouseId],
  );

  const productOptions = useMemo(
    () => options.products.map((item) => ({
      label: `${item.product_name} (${item.product_code})`,
      value: item.id,
    })),
    [options.products],
  );

  const selectedAdjustmentRow = useMemo(
    () => inventory.find((item) => (
      item.warehouse_id === watchedWarehouseId
      && item.location_id === watchedLocationId
      && item.product_id === watchedProductId
    )) || null,
    [inventory, watchedLocationId, watchedProductId, watchedWarehouseId],
  );

  const adjustmentPreview = useMemo(() => {
    if (!watchedWarehouseId || !watchedLocationId || !watchedProductId) {
      return null;
    }

    const currentQuantity = Number(selectedAdjustmentRow?.quantity || 0);
    const hasActualQuantity = watchedActualQuantity !== undefined && watchedActualQuantity !== null;
    const nextQuantity = hasActualQuantity ? Number(watchedActualQuantity) : null;
    const delta = hasActualQuantity ? nextQuantity - currentQuantity : null;

    return {
      currentQuantity,
      nextQuantity,
      delta,
    };
  }, [selectedAdjustmentRow, watchedActualQuantity, watchedLocationId, watchedProductId, watchedWarehouseId]);

  const handleAdjustmentSubmit = async (values) => {
    setAdjusting(true);
    try {
      await api.post('/inventory/adjustments', values);
      message.success('Đã ghi nhận điều chỉnh tồn kho thành công.');
      form.resetFields();
      await fetchInventoryData();
    } catch (error) {
      message.error(error.response?.data?.message || 'Không thể điều chỉnh tồn kho.');
    } finally {
      setAdjusting(false);
    }
  };

  const adjustmentTab = canManage ? {
    key: 'adjustment',
    label: 'Điều chỉnh tồn kho',
    children: (
      <Row gutter={[16, 16]}>
        <Col xs={24} xl={14}>
          <Card variant="borderless" style={{ background: '#fafafa' }}>
            <Space orientation="vertical" size={16} style={{ width: '100%' }}>
              <div>
                <Typography.Title level={4} style={{ marginBottom: 6 }}>
                  Ghi nhận chênh lệch kiểm kê
                </Typography.Title>
                <Typography.Text type="secondary">
                  Dùng khi số lượng thực tế khác với số đang ghi nhận trong hệ thống.
                </Typography.Text>
              </div>

              <Form
                form={form}
                layout="vertical"
                onFinish={handleAdjustmentSubmit}
                initialValues={{ actual_quantity: 0 }}
              >
                <Row gutter={[12, 0]}>
                  <Col xs={24} md={12}>
                    <Form.Item
                      label="Kho"
                      name="warehouse_id"
                      rules={[{ required: true, message: 'Vui lòng chọn kho.' }]}
                    >
                      <Select
                        showSearch
                        optionFilterProp="label"
                        placeholder="Chọn kho cần điều chỉnh"
                        options={warehouseOptions}
                      />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12}>
                    <Form.Item
                      label="Vị trí kho"
                      name="location_id"
                      rules={[{ required: true, message: 'Vui lòng chọn vị trí kho.' }]}
                    >
                      <Select
                        showSearch
                        optionFilterProp="label"
                        placeholder="Chọn vị trí lưu trữ"
                        options={locationOptions}
                      />
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={[12, 0]}>
                  <Col xs={24} md={12}>
                    <Form.Item
                      label="Sản phẩm"
                      name="product_id"
                      rules={[{ required: true, message: 'Vui lòng chọn sản phẩm.' }]}
                    >
                      <Select
                        showSearch
                        optionFilterProp="label"
                        placeholder="Chọn sản phẩm cần đối chiếu"
                        options={productOptions}
                      />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12}>
                    <Form.Item
                      label="Số lượng thực tế"
                      name="actual_quantity"
                      rules={[{ required: true, message: 'Vui lòng nhập số lượng thực tế.' }]}
                    >
                      <InputNumber
                        min={0}
                        precision={2}
                        style={{ width: '100%' }}
                        placeholder="Nhập số lượng sau kiểm kê"
                      />
                    </Form.Item>
                  </Col>
                </Row>

                <Form.Item label="Ghi chú" name="note">
                  <Input.TextArea
                    rows={3}
                    placeholder="Ví dụ: kiểm kê cuối ngày, phát hiện chênh lệch khi đối chiếu kệ A-01"
                  />
                </Form.Item>

                <Space wrap>
                  <Button
                    type="primary"
                    htmlType="submit"
                    icon={<EditOutlined />}
                    loading={adjusting}
                    disabled={!adjustmentPreview || adjustmentPreview.delta === 0}
                  >
                    Ghi nhận điều chỉnh
                  </Button>
                  <Button
                    icon={<ReloadOutlined />}
                    onClick={() => {
                      form.resetFields();
                    }}
                  >
                    Làm mới biểu mẫu
                  </Button>
                </Space>
              </Form>
            </Space>
          </Card>
        </Col>

        <Col xs={24} xl={10}>
          <Card variant="borderless" style={{ background: '#fffbe6' }}>
            <Space orientation="vertical" size={14} style={{ width: '100%' }}>
              <div>
                <Typography.Title level={4} style={{ marginBottom: 6 }}>
                  Xem trước điều chỉnh
                </Typography.Title>
                <Typography.Text type="secondary">
                  Hệ thống sẽ so sánh số thực tế bạn nhập với tồn kho hiện tại ở đúng kho, vị trí và sản phẩm đã chọn.
                </Typography.Text>
              </div>

              {!adjustmentPreview ? (
                <Alert
                  type="info"
                  showIcon
                  title="Chọn đủ kho, vị trí và sản phẩm để xem tồn kho hiện tại."
                />
              ) : (
                <Space orientation="vertical" size={10} style={{ width: '100%' }}>
                  <div>
                    <Typography.Text type="secondary">Tồn hiện tại</Typography.Text>
                    <div className="metric-value">{formatNumber(adjustmentPreview.currentQuantity)}</div>
                  </div>
                  <div>
                    <Typography.Text type="secondary">Số lượng thực tế</Typography.Text>
                    <div className="metric-value">
                      {adjustmentPreview.nextQuantity === null
                        ? '-'
                        : formatNumber(adjustmentPreview.nextQuantity)}
                    </div>
                  </div>
                  <div>
                    <Typography.Text type="secondary">Chênh lệch sẽ ghi nhận</Typography.Text>
                    <div className="metric-value">
                      {adjustmentPreview.delta === null
                        ? '-'
                        : `${adjustmentPreview.delta > 0 ? '+' : ''}${formatNumber(adjustmentPreview.delta)}`}
                    </div>
                  </div>

                  {adjustmentPreview.delta === 0 ? (
                    <Alert
                      type="warning"
                      showIcon
                      title="Số lượng mới đang bằng với tồn hiện tại, hệ thống sẽ không tạo biến động."
                    />
                  ) : (
                    <Alert
                      type="success"
                      showIcon
                      title="Khi xác nhận, hệ thống sẽ cập nhật tồn kho thật và ghi thêm một movement loại adjustment."
                    />
                  )}
                </Space>
              )}
            </Space>
          </Card>
        </Col>
      </Row>
    ),
  } : null;

  const tabItems = [
    {
      key: 'inventory',
      label: 'Tồn hiện tại',
      children: (
        <Table
          rowKey="id"
          loading={loading}
          dataSource={inventory}
          columns={[
            { title: 'Kho', dataIndex: 'warehouse_name' },
            { title: 'Vị trí', dataIndex: 'location_name' },
            { title: 'Mã hàng', dataIndex: 'product_code' },
            { title: 'Tên hàng', dataIndex: 'product_name' },
            {
              title: 'Số lượng',
              dataIndex: 'quantity',
              render: (value) => formatNumber(value),
            },
            {
              title: 'Cập nhật gần nhất',
              dataIndex: 'updated_at',
              render: formatDateTime,
            },
          ]}
          scroll={{ x: 1080 }}
          locale={{
            emptyText: (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="Chưa có dữ liệu tồn kho để hiển thị."
              />
            ),
          }}
        />
      ),
    },
    {
      key: 'movement',
      label: 'Lịch sử biến động',
      children: (
        <Table
          rowKey="id"
          loading={loading}
          dataSource={movements}
          columns={[
            { title: 'Thời gian', dataIndex: 'created_at', render: formatDateTime },
            { title: 'Kho', dataIndex: 'warehouse_name' },
            { title: 'Vị trí', dataIndex: 'location_name' },
            { title: 'Sản phẩm', dataIndex: 'product_name' },
            {
              title: 'Loại biến động',
              dataIndex: 'movement_type',
              render: (value) => <StatusTag value={value} />,
            },
            {
              title: 'Nguồn tham chiếu',
              dataIndex: 'reference_type',
              render: (value) => value || '-',
            },
            {
              title: 'Trước',
              dataIndex: 'quantity_before',
              render: (value) => formatNumber(value),
            },
            {
              title: 'Biến động',
              dataIndex: 'quantity_change',
              render: (value) => formatNumber(value),
            },
            {
              title: 'Sau',
              dataIndex: 'quantity_after',
              render: (value) => formatNumber(value),
            },
            {
              title: 'Người thực hiện',
              dataIndex: 'performer_name',
              render: (value) => value || '-',
            },
          ]}
          scroll={{ x: 1360 }}
          locale={{
            emptyText: (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="Chưa có lịch sử biến động kho."
              />
            ),
          }}
        />
      ),
    },
  ];

  if (adjustmentTab) {
    tabItems.push(adjustmentTab);
  }

  return (
    <Space orientation="vertical" size={18} style={{ width: '100%' }}>
      <Card className="page-card" styles={{ body: { padding: 28 } }}>
        <Space orientation="vertical" size={10} style={{ width: '100%' }}>
          <Typography.Text className="resource-eyebrow">
            Module 6 · Tồn kho, truy vết và điều chỉnh kiểm kê tối thiểu
          </Typography.Text>
          <Typography.Title level={2} className="page-title">
            Tồn kho và biến động kho
          </Typography.Title>
          <Typography.Paragraph className="page-subtitle" style={{ marginBottom: 0 }}>
            Theo dõi tồn kho theo từng vị trí lưu trữ, xem lại lịch sử biến động đã phát sinh và
            ghi nhận chênh lệch kiểm kê tối thiểu ngay trên dữ liệu demo hiện tại.
          </Typography.Paragraph>
        </Space>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12} xl={6}>
          <Card className="page-card" styles={{ body: { padding: 20 } }}>
            <Typography.Text type="secondary">Số kho có dữ liệu</Typography.Text>
            <div className="metric-value">{formatNumber(summary.warehouseCount)}</div>
            <Typography.Text type="secondary">Tính theo tồn kho hiện tại</Typography.Text>
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="page-card" styles={{ body: { padding: 20 } }}>
            <Typography.Text type="secondary">Sản phẩm có tồn</Typography.Text>
            <div className="metric-value">{formatNumber(summary.productCount)}</div>
            <Typography.Text type="secondary">Đã phân bổ vào vị trí kho</Typography.Text>
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="page-card" styles={{ body: { padding: 20 } }}>
            <Typography.Text type="secondary">Tổng số lượng đang lưu</Typography.Text>
            <div className="metric-value">{formatNumber(summary.totalQuantity)}</div>
            <Typography.Text type="secondary">Tổng cộng mọi dòng tồn kho</Typography.Text>
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="page-card" styles={{ body: { padding: 20 } }}>
            <Typography.Text type="secondary">Lịch sử biến động</Typography.Text>
            <div className="metric-value">{formatNumber(summary.movementCount)}</div>
            <Typography.Text type="secondary">Dùng để truy vết kiểm kê</Typography.Text>
          </Card>
        </Col>
      </Row>

      <SectionCard
        title="Theo dõi tồn kho"
        subtitle="Trang này đã có luồng điều chỉnh kiểm kê tối thiểu; nhập, xuất và điều chuyển vẫn được xử lý ở các trang nghiệp vụ riêng."
        extra={(
          <Button icon={<ReloadOutlined />} onClick={() => fetchInventoryData()}>
            Tải lại dữ liệu
          </Button>
        )}
      >
        <Tabs items={tabItems} />
      </SectionCard>
    </Space>
  );
}

export default InventoryPage;
