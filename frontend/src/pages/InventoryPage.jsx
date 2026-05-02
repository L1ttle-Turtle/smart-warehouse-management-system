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
  Tag,
  Typography,
  message,
} from 'antd';
import { FilterOutlined, ReloadOutlined, SearchOutlined, WarningOutlined } from '@ant-design/icons';
import { useCallback, useEffect, useMemo, useState } from 'react';

import api from '../api/client';
import { useAuth } from '../auth/useAuth';
import SectionCard from '../components/SectionCard';
import StatusTag from '../components/StatusTag';
import { formatDateTime, formatNumber } from '../utils/format';

const DEFAULT_FILTERS = {
  q: '',
  warehouse_id: null,
  location_id: null,
  product_id: null,
  category_id: null,
  stock_status: null,
  low_stock_only: false,
};

const STOCK_STATUS_OPTIONS = [
  { label: 'Đủ hàng', value: 'in_stock' },
  { label: 'Tồn thấp', value: 'low_stock' },
  { label: 'Hết hàng', value: 'out_of_stock' },
];

const STOCK_STATUS_COLORS = {
  in_stock: 'green',
  low_stock: 'gold',
  out_of_stock: 'red',
};

function StockStatusTag({ status, label }) {
  return <Tag color={STOCK_STATUS_COLORS[status] || 'default'}>{label || status}</Tag>;
}

function InventoryPage() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission('inventory.manage');

  const [adjustmentForm] = Form.useForm();
  const watchedAdjustmentWarehouseId = Form.useWatch('warehouse_id', adjustmentForm);

  const [inventoryLoading, setInventoryLoading] = useState(false);
  const [movementLoading, setMovementLoading] = useState(false);
  const [submittingAdjustment, setSubmittingAdjustment] = useState(false);
  const [inventoryRows, setInventoryRows] = useState([]);
  const [movementRows, setMovementRows] = useState([]);
  const [draftFilters, setDraftFilters] = useState(DEFAULT_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState(DEFAULT_FILTERS);
  const [inventoryPagination, setInventoryPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
  });
  const [options, setOptions] = useState({
    warehouses: [],
    locations: [],
    products: [],
  });
  const inventoryPage = inventoryPagination.current;
  const inventoryPageSize = inventoryPagination.pageSize;

  const warehouseOptions = useMemo(
    () => options.warehouses.map((item) => ({
      label: `${item.warehouse_name} (${item.warehouse_code})`,
      value: item.id,
    })),
    [options.warehouses],
  );

  const productOptions = useMemo(
    () => options.products.map((item) => ({
      label: `${item.product_name} (${item.product_code})`,
      value: item.id,
      category_id: item.category_id,
      category_name: item.category_name,
    })),
    [options.products],
  );

  const categoryOptions = useMemo(() => {
    const uniqueCategories = new Map();
    options.products.forEach((item) => {
      if (item.category_id && item.category_name && !uniqueCategories.has(item.category_id)) {
        uniqueCategories.set(item.category_id, {
          label: item.category_name,
          value: item.category_id,
        });
      }
    });
    return Array.from(uniqueCategories.values());
  }, [options.products]);

  const filterLocationOptions = useMemo(
    () => options.locations
      .filter((item) => !draftFilters.warehouse_id || item.warehouse_id === draftFilters.warehouse_id)
      .map((item) => ({
        label: `${item.location_name} (${item.location_code})`,
        value: item.id,
      })),
    [draftFilters.warehouse_id, options.locations],
  );

  const adjustmentLocationOptions = useMemo(
    () => options.locations
      .filter((item) => !watchedAdjustmentWarehouseId || item.warehouse_id === watchedAdjustmentWarehouseId)
      .map((item) => ({
        label: `${item.location_name} (${item.location_code})`,
        value: item.id,
      })),
    [options.locations, watchedAdjustmentWarehouseId],
  );

  const fetchOptions = useCallback(async () => {
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
      message.error(error.response?.data?.message || 'Không tải được dữ liệu nền cho tồn kho.');
    }
  }, []);

  const fetchInventory = useCallback(async () => {
    setInventoryLoading(true);
    try {
      const params = {
        page: inventoryPage,
        per_page: inventoryPageSize,
        sort_by: 'updated_at',
        sort_order: 'desc',
      };

      if (appliedFilters.q) {
        params.q = appliedFilters.q;
      }
      if (appliedFilters.warehouse_id) {
        params.warehouse_id = appliedFilters.warehouse_id;
      }
      if (appliedFilters.location_id) {
        params.location_id = appliedFilters.location_id;
      }
      if (appliedFilters.product_id) {
        params.product_id = appliedFilters.product_id;
      }
      if (appliedFilters.category_id) {
        params.category_id = appliedFilters.category_id;
      }
      if (appliedFilters.stock_status) {
        params.stock_status = appliedFilters.stock_status;
      }
      if (appliedFilters.low_stock_only) {
        params.low_stock_only = true;
      }

      const response = await api.get('/inventory', { params });
      setInventoryRows(response.data.items || []);
      setInventoryPagination((current) => {
        const nextState = {
          current: response.data.page || current.current,
          pageSize: response.data.page_size || current.pageSize,
          total: response.data.total || 0,
        };
        if (
          nextState.current === current.current
          && nextState.pageSize === current.pageSize
          && nextState.total === current.total
        ) {
          return current;
        }
        return nextState;
      });
    } catch (error) {
      message.error(error.response?.data?.message || 'Không tải được danh sách tồn kho.');
    } finally {
      setInventoryLoading(false);
    }
  }, [appliedFilters, inventoryPage, inventoryPageSize]);

  const fetchMovements = useCallback(async () => {
    setMovementLoading(true);
    try {
      const response = await api.get('/inventory/movements');
      setMovementRows(response.data.items || []);
    } catch (error) {
      message.error(error.response?.data?.message || 'Không tải được lịch sử biến động tồn kho.');
    } finally {
      setMovementLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOptions();
  }, [fetchOptions]);

  useEffect(() => {
    fetchInventory();
  }, [fetchInventory]);

  useEffect(() => {
    fetchMovements();
  }, [fetchMovements]);

  useEffect(() => {
    if (
      draftFilters.warehouse_id
      && draftFilters.location_id
      && !options.locations.some(
        (item) => item.id === draftFilters.location_id && item.warehouse_id === draftFilters.warehouse_id,
      )
    ) {
      setDraftFilters((current) => ({ ...current, location_id: null }));
    }
  }, [draftFilters.location_id, draftFilters.warehouse_id, options.locations]);

  const handleApplyFilters = () => {
    setAppliedFilters({
      ...draftFilters,
      q: draftFilters.q.trim(),
    });
    setInventoryPagination((current) => ({ ...current, current: 1 }));
  };

  const handleResetFilters = () => {
    setDraftFilters(DEFAULT_FILTERS);
    setAppliedFilters(DEFAULT_FILTERS);
    setInventoryPagination((current) => ({ ...current, current: 1 }));
  };

  const handleToggleLowStock = () => {
    const nextFilters = {
      ...draftFilters,
      low_stock_only: !draftFilters.low_stock_only,
      stock_status: draftFilters.low_stock_only ? draftFilters.stock_status : null,
    };
    setDraftFilters(nextFilters);
    setAppliedFilters({
      ...nextFilters,
      q: nextFilters.q.trim(),
    });
    setInventoryPagination((current) => ({ ...current, current: 1 }));
  };

  const handleAdjustmentSubmit = async (values) => {
    setSubmittingAdjustment(true);
    try {
      await api.post('/inventory/adjustments', {
        warehouse_id: values.warehouse_id,
        location_id: values.location_id,
        product_id: values.product_id,
        actual_quantity: Number(values.actual_quantity || 0),
        note: values.note?.trim() || null,
      });
      message.success('Đã điều chỉnh tồn kho và ghi nhận movement kiểm kê.');
      adjustmentForm.resetFields();
      await Promise.all([fetchInventory(), fetchMovements()]);
    } catch (error) {
      message.error(error.response?.data?.message || 'Không điều chỉnh được tồn kho.');
    } finally {
      setSubmittingAdjustment(false);
    }
  };

  const summary = useMemo(() => {
    const lowStockCount = inventoryRows.filter((item) => item.stock_status === 'low_stock').length;
    const outOfStockCount = inventoryRows.filter((item) => item.stock_status === 'out_of_stock').length;
    const totalQuantity = inventoryRows.reduce((sum, item) => sum + Number(item.quantity || 0), 0);
    const warehouseCount = new Set(inventoryRows.map((item) => item.warehouse_id)).size;

    return {
      lowStockCount,
      outOfStockCount,
      totalQuantity,
      warehouseCount,
    };
  }, [inventoryRows]);

  const inventoryColumns = [
    {
      title: 'Kho',
      dataIndex: 'warehouse_name',
      render: (value, record) => `${value} (${record.warehouse_code})`,
    },
    {
      title: 'Vị trí',
      dataIndex: 'location_name',
      render: (value, record) => `${value} (${record.location_code})`,
    },
    {
      title: 'Sản phẩm',
      dataIndex: 'product_name',
      render: (value, record) => (
        <Space orientation="vertical" size={0}>
          <Typography.Text strong>{value}</Typography.Text>
          <Typography.Text type="secondary">{record.product_code}</Typography.Text>
        </Space>
      ),
    },
    {
      title: 'Nhóm hàng',
      dataIndex: 'category_name',
      render: (value) => value || 'Chưa gắn nhóm hàng',
    },
    {
      title: 'Tồn hiện tại',
      dataIndex: 'quantity',
      render: formatNumber,
    },
    {
      title: 'Tồn tối thiểu',
      dataIndex: 'min_stock',
      render: formatNumber,
    },
    {
      title: 'Trạng thái',
      dataIndex: 'stock_status',
      render: (_, record) => (
        <Space orientation="vertical" size={4}>
          <StockStatusTag status={record.stock_status} label={record.stock_status_label} />
          {record.is_low_stock && record.shortage_quantity > 0 ? (
            <Typography.Text type="secondary">
              Thiếu {formatNumber(record.shortage_quantity)}
            </Typography.Text>
          ) : null}
        </Space>
      ),
    },
    {
      title: 'Cập nhật gần nhất',
      dataIndex: 'updated_at',
      render: formatDateTime,
    },
  ];

  const movementColumns = [
    {
      title: 'Thời gian',
      dataIndex: 'created_at',
      render: formatDateTime,
    },
    {
      title: 'Kho',
      dataIndex: 'warehouse_name',
      render: (value, record) => `${value || '-'}${record.warehouse_code ? ` (${record.warehouse_code})` : ''}`,
    },
    {
      title: 'Vị trí',
      dataIndex: 'location_name',
      render: (value, record) => `${value || '-'}${record.location_code ? ` (${record.location_code})` : ''}`,
    },
    {
      title: 'Sản phẩm',
      dataIndex: 'product_name',
      render: (value, record) => `${value || '-'}${record.product_code ? ` (${record.product_code})` : ''}`,
    },
    {
      title: 'Loại biến động',
      dataIndex: 'movement_type',
      render: (value) => <StatusTag value={value} />,
    },
    {
      title: 'Nguồn chứng từ',
      dataIndex: 'reference_type',
      render: (value, record) => (
        <Typography.Text>{value ? `${value}${record.reference_id ? ` #${record.reference_id}` : ''}` : '-'}</Typography.Text>
      ),
    },
    {
      title: 'Trước',
      dataIndex: 'quantity_before',
      render: formatNumber,
    },
    {
      title: 'Biến động',
      dataIndex: 'quantity_change',
      render: formatNumber,
    },
    {
      title: 'Sau',
      dataIndex: 'quantity_after',
      render: formatNumber,
    },
    {
      title: 'Người thực hiện',
      dataIndex: 'performer_name',
      render: (value) => value || '-',
    },
  ];

  return (
    <Space orientation="vertical" size={18} style={{ width: '100%' }}>
      <Card className="page-card" styles={{ body: { padding: 28 } }}>
        <Space orientation="vertical" size={10} style={{ width: '100%' }}>
          <Typography.Text className="resource-eyebrow">
            Module 6.5 · Inventory hardening và stocktake
          </Typography.Text>
          <Typography.Title level={2} className="page-title">
            Tồn kho
          </Typography.Title>
          <Typography.Paragraph className="page-subtitle" style={{ marginBottom: 0 }}>
            Theo dõi tồn kho theo từng kho và vị trí, nhận diện nhanh hàng tồn thấp hoặc hết hàng,
            đồng thời vẫn giữ được luồng điều chỉnh tồn kho tối thiểu đang dùng cho demo hiện tại.
          </Typography.Paragraph>
        </Space>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12} xl={6}>
          <Card className="page-card" styles={{ body: { padding: 20 } }}>
            <Typography.Text type="secondary">Tổng dòng tồn đang hiển thị</Typography.Text>
            <div className="metric-value">{formatNumber(inventoryPagination.total)}</div>
            <Typography.Text type="secondary">Đã áp dụng lọc và phân trang từ server</Typography.Text>
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="page-card" styles={{ body: { padding: 20 } }}>
            <Typography.Text type="secondary">Kho xuất hiện trên trang</Typography.Text>
            <div className="metric-value">{formatNumber(summary.warehouseCount)}</div>
            <Typography.Text type="secondary">Giúp rà soát nhanh phạm vi dữ liệu đang xem</Typography.Text>
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="page-card" styles={{ body: { padding: 20 } }}>
            <Typography.Text type="secondary">Dòng tồn thấp</Typography.Text>
            <div className="metric-value">{formatNumber(summary.lowStockCount)}</div>
            <Typography.Text type="secondary">Cần ưu tiên nhập bù hoặc kiểm tra thực tế</Typography.Text>
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="page-card" styles={{ body: { padding: 20 } }}>
            <Typography.Text type="secondary">Dòng hết hàng</Typography.Text>
            <div className="metric-value">{formatNumber(summary.outOfStockCount)}</div>
            <Typography.Text type="secondary">Đang bằng 0 hoặc thấp hơn 0 theo dữ liệu hệ thống</Typography.Text>
          </Card>
        </Col>
      </Row>

      <Tabs
        items={[
          {
            key: 'inventory',
            label: 'Tồn hiện tại',
            children: (
              <SectionCard
                title="Tồn kho theo kho và vị trí"
                subtitle="Lọc nhanh theo sản phẩm, kho, vị trí, nhóm hàng và trạng thái tồn để phục vụ demo kiểm kê."
              >
                <Space orientation="vertical" size={16} style={{ width: '100%' }}>
                  <Alert
                    showIcon
                    type={appliedFilters.low_stock_only ? 'warning' : 'info'}
                    icon={<WarningOutlined />}
                    title={appliedFilters.low_stock_only
                      ? 'Đang bật chế độ chỉ xem tồn thấp và hết hàng.'
                      : 'Có thể bật nhanh bộ lọc tồn thấp để ưu tiên các dòng cần kiểm kê.'}
                  />

                  <div className="section-toolbar resource-toolbar">
                    <Space wrap size={12}>
                      <Input
                        allowClear
                        prefix={<SearchOutlined />}
                        placeholder="Tìm theo mã hoặc tên sản phẩm"
                        style={{ width: 260 }}
                        value={draftFilters.q}
                        onChange={(event) => setDraftFilters((current) => ({ ...current, q: event.target.value }))}
                        onPressEnter={handleApplyFilters}
                      />
                      <Select
                        allowClear
                        showSearch
                        optionFilterProp="label"
                        placeholder="Chọn kho"
                        style={{ width: 220 }}
                        options={warehouseOptions}
                        value={draftFilters.warehouse_id}
                        onChange={(value) => {
                          setDraftFilters((current) => ({
                            ...current,
                            warehouse_id: value ?? null,
                            location_id: value ? current.location_id : null,
                          }));
                        }}
                      />
                      <Select
                        allowClear
                        showSearch
                        optionFilterProp="label"
                        placeholder="Chọn vị trí"
                        style={{ width: 220 }}
                        options={filterLocationOptions}
                        value={draftFilters.location_id}
                        onChange={(value) => setDraftFilters((current) => ({ ...current, location_id: value ?? null }))}
                      />
                      <Select
                        allowClear
                        showSearch
                        optionFilterProp="label"
                        placeholder="Chọn sản phẩm"
                        style={{ width: 240 }}
                        options={productOptions}
                        value={draftFilters.product_id}
                        onChange={(value) => setDraftFilters((current) => ({ ...current, product_id: value ?? null }))}
                      />
                      <Select
                        allowClear
                        showSearch
                        optionFilterProp="label"
                        placeholder="Chọn nhóm hàng"
                        style={{ width: 220 }}
                        options={categoryOptions}
                        value={draftFilters.category_id}
                        onChange={(value) => setDraftFilters((current) => ({ ...current, category_id: value ?? null }))}
                      />
                      <Select
                        allowClear
                        placeholder="Trạng thái tồn"
                        style={{ width: 180 }}
                        options={STOCK_STATUS_OPTIONS}
                        value={draftFilters.stock_status}
                        onChange={(value) => {
                          setDraftFilters((current) => ({
                            ...current,
                            stock_status: value ?? null,
                            low_stock_only: value ? false : current.low_stock_only,
                          }));
                        }}
                      />
                    </Space>

                    <Space wrap>
                      <Button icon={<FilterOutlined />} type="primary" onClick={handleApplyFilters}>
                        Lọc
                      </Button>
                      <Button onClick={handleResetFilters}>Xóa lọc</Button>
                      <Button
                        type={appliedFilters.low_stock_only ? 'primary' : 'default'}
                        danger={appliedFilters.low_stock_only}
                        icon={<WarningOutlined />}
                        onClick={handleToggleLowStock}
                      >
                        Chỉ tồn thấp
                      </Button>
                      <Button icon={<ReloadOutlined />} onClick={() => Promise.all([fetchInventory(), fetchMovements()])}>
                        Làm mới
                      </Button>
                    </Space>
                  </div>

                  <Table
                    rowKey="id"
                    loading={inventoryLoading}
                    dataSource={inventoryRows}
                    columns={inventoryColumns}
                    rowClassName={(record) => {
                      if (record.stock_status === 'out_of_stock') {
                        return 'inventory-row-out-of-stock';
                      }
                      if (record.stock_status === 'low_stock') {
                        return 'inventory-row-low-stock';
                      }
                      return '';
                    }}
                    pagination={{
                      current: inventoryPagination.current,
                      pageSize: inventoryPagination.pageSize,
                      total: inventoryPagination.total,
                      showSizeChanger: true,
                      pageSizeOptions: ['10', '20', '50'],
                    }}
                    onChange={(nextPagination) => {
                      setInventoryPagination((current) => ({
                        ...current,
                        current: nextPagination.current || 1,
                        pageSize: nextPagination.pageSize || current.pageSize,
                      }));
                    }}
                    scroll={{ x: 1320 }}
                    locale={{
                      emptyText: (
                        <Empty
                          image={Empty.PRESENTED_IMAGE_SIMPLE}
                          description="Không có dòng tồn kho nào phù hợp với bộ lọc hiện tại."
                        />
                      ),
                    }}
                  />
                </Space>
              </SectionCard>
            ),
          },
          {
            key: 'movements',
            label: 'Lịch sử biến động',
            children: (
              <SectionCard
                title="Lịch sử biến động tồn kho"
                subtitle="Danh sách movement giúp giải thích vì sao số lượng tồn kho thay đổi theo từng chứng từ."
              >
                <Table
                  rowKey="id"
                  loading={movementLoading}
                  dataSource={movementRows}
                  columns={movementColumns}
                  scroll={{ x: 1380 }}
                  locale={{
                    emptyText: (
                      <Empty
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        description="Chưa có lịch sử biến động tồn kho để hiển thị."
                      />
                    ),
                  }}
                />
              </SectionCard>
            ),
          },
          ...(canManage
            ? [{
              key: 'adjustment',
              label: 'Điều chỉnh tồn kho',
              children: (
                <SectionCard
                  title="Điều chỉnh tồn kho tối thiểu"
                  subtitle="Dùng khi cần sửa nhanh một dòng tồn kho sau kiểm tra thực tế hoặc trước khi chuyển sang phiếu kiểm kê nhiều dòng."
                >
                  <Space orientation="vertical" size={16} style={{ width: '100%' }}>
                    <Alert
                      showIcon
                      type="warning"
                      title="Luồng này chỉ điều chỉnh một dòng tồn kho. Với kiểm kê nhiều dòng, hãy dùng trang Kiểm kê kho mới."
                    />

                    <Form
                      form={adjustmentForm}
                      layout="vertical"
                      onFinish={handleAdjustmentSubmit}
                      onValuesChange={(changedValues, allValues) => {
                        if (
                          Object.prototype.hasOwnProperty.call(changedValues, 'warehouse_id')
                          && allValues.location_id
                          && !options.locations.some(
                            (item) => item.id === allValues.location_id && item.warehouse_id === changedValues.warehouse_id,
                          )
                        ) {
                          adjustmentForm.setFieldValue('location_id', undefined);
                        }
                      }}
                    >
                      <Row gutter={16}>
                        <Col xs={24} md={8}>
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
                        <Col xs={24} md={8}>
                          <Form.Item
                            label="Vị trí"
                            name="location_id"
                            rules={[{ required: true, message: 'Vui lòng chọn vị trí kho.' }]}
                          >
                            <Select
                              showSearch
                              optionFilterProp="label"
                              placeholder={watchedAdjustmentWarehouseId ? 'Chọn vị trí trong kho đã chọn' : 'Chọn kho trước'}
                              options={adjustmentLocationOptions}
                              disabled={!watchedAdjustmentWarehouseId}
                            />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={8}>
                          <Form.Item
                            label="Sản phẩm"
                            name="product_id"
                            rules={[{ required: true, message: 'Vui lòng chọn sản phẩm.' }]}
                          >
                            <Select
                              showSearch
                              optionFilterProp="label"
                              placeholder="Chọn sản phẩm cần điều chỉnh"
                              options={productOptions}
                            />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={8}>
                          <Form.Item
                            label="Tồn thực tế"
                            name="actual_quantity"
                            rules={[{ required: true, message: 'Vui lòng nhập tồn thực tế.' }]}
                          >
                            <InputNumber min={0} controls={false} style={{ width: '100%' }} />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={16}>
                          <Form.Item label="Ghi chú" name="note">
                            <Input.TextArea
                              rows={3}
                              allowClear
                              placeholder="Ví dụ: Điều chỉnh sau kiểm kê cuối ngày hoặc sau đối chiếu chứng từ"
                            />
                          </Form.Item>
                        </Col>
                      </Row>

                      <div className="resource-drawer-actions">
                        <Button onClick={() => adjustmentForm.resetFields()}>Xóa nhập liệu</Button>
                        <Button type="primary" htmlType="submit" loading={submittingAdjustment}>
                          Ghi nhận điều chỉnh
                        </Button>
                      </div>
                    </Form>
                  </Space>
                </SectionCard>
              ),
            }]
            : []),
        ]}
      />
    </Space>
  );
}

export default InventoryPage;
