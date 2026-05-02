import {
  CheckCircleOutlined,
  EditOutlined,
  MinusCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  StopOutlined,
} from '@ant-design/icons';
import {
  Alert,
  Button,
  Card,
  Col,
  Drawer,
  Empty,
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
import { useCallback, useEffect, useMemo, useState } from 'react';

import api from '../api/client';
import { useAuth } from '../auth/useAuth';
import SectionCard from '../components/SectionCard';
import StatusTag from '../components/StatusTag';
import { formatDateTime, formatNumber } from '../utils/format';

const STATUS_OPTIONS = [
  { label: 'Tất cả trạng thái', value: 'all' },
  { label: 'Nháp', value: 'draft' },
  { label: 'Đã xác nhận', value: 'confirmed' },
  { label: 'Đã hủy', value: 'cancelled' },
];

function buildInventoryKey(warehouseId, locationId, productId) {
  return `${warehouseId}-${locationId}-${productId}`;
}

function StocktakesPage() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission('inventory.manage');

  const [form] = Form.useForm();
  const watchedWarehouseId = Form.useWatch('warehouse_id', form);
  const watchedDetails = Form.useWatch('details', form) || [];

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [confirmingId, setConfirmingId] = useState(null);
  const [cancellingId, setCancellingId] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingStocktake, setEditingStocktake] = useState(null);
  const [stocktakes, setStocktakes] = useState([]);
  const [inventoryRows, setInventoryRows] = useState([]);
  const [stocktakeMovements, setStocktakeMovements] = useState([]);
  const [movementLoading, setMovementLoading] = useState(false);
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [warehouseFilter, setWarehouseFilter] = useState('all');
  const [selectedStocktakeId, setSelectedStocktakeId] = useState(null);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
  });
  const [options, setOptions] = useState({
    warehouses: [],
    locations: [],
    products: [],
  });

  const currentPage = pagination.current;
  const currentPageSize = pagination.pageSize;

  const inventoryLookup = useMemo(() => {
    const nextLookup = new Map();
    inventoryRows.forEach((item) => {
      nextLookup.set(buildInventoryKey(item.warehouse_id, item.location_id, item.product_id), item);
    });
    return nextLookup;
  }, [inventoryRows]);

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
    })),
    [options.products],
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
      message.error(error.response?.data?.message || 'Không tải được dữ liệu nền cho phiếu kiểm kê.');
    }
  }, []);

  const fetchInventoryRows = useCallback(async () => {
    try {
      const response = await api.get('/inventory', {
        params: {
          page: 1,
          per_page: 500,
          sort_by: 'updated_at',
          sort_order: 'desc',
        },
      });
      setInventoryRows(response.data.items || []);
    } catch (error) {
      message.error(error.response?.data?.message || 'Không tải được dữ liệu tồn kho để đối chiếu kiểm kê.');
    }
  }, []);

  const fetchStocktakes = useCallback(async (overrides = {}) => {
    setLoading(true);
    try {
      const page = overrides.page ?? currentPage;
      const pageSize = overrides.pageSize ?? currentPageSize;
      const nextSearch = overrides.search ?? searchQuery;
      const nextStatus = overrides.status ?? statusFilter;
      const nextWarehouse = overrides.warehouse ?? warehouseFilter;
      const params = {
        page,
        page_size: pageSize,
        sort_by: 'created_at',
        sort_order: 'desc',
      };

      if (nextSearch) {
        params.q = nextSearch;
      }
      if (nextStatus !== 'all') {
        params.status = nextStatus;
      }
      if (nextWarehouse !== 'all') {
        params.warehouse_id = nextWarehouse;
      }

      const response = await api.get('/stocktakes', { params });
      setStocktakes(response.data.items || []);
      setPagination({
        current: response.data.page || page,
        pageSize: response.data.page_size || pageSize,
        total: response.data.total || 0,
      });
    } catch (error) {
      message.error(error.response?.data?.message || 'Không tải được danh sách phiếu kiểm kê.');
    } finally {
      setLoading(false);
    }
  }, [currentPage, currentPageSize, searchQuery, statusFilter, warehouseFilter]);

  const fetchStocktakeMovements = useCallback(async (stocktakeId = selectedStocktakeId) => {
    if (!stocktakeId) {
      setStocktakeMovements([]);
      return;
    }

    setMovementLoading(true);
    try {
      const response = await api.get('/inventory/movements', {
        params: {
          reference_type: 'stocktake',
          reference_id: stocktakeId,
        },
      });
      setStocktakeMovements(response.data.items || []);
    } catch (error) {
      message.error(error.response?.data?.message || 'Không tải được lịch sử biến động của phiếu kiểm kê.');
      setStocktakeMovements([]);
    } finally {
      setMovementLoading(false);
    }
  }, [selectedStocktakeId]);

  useEffect(() => {
    fetchOptions();
  }, [fetchOptions]);

  useEffect(() => {
    fetchInventoryRows();
  }, [fetchInventoryRows]);

  useEffect(() => {
    fetchStocktakes();
  }, [fetchStocktakes]);

  useEffect(() => {
    fetchStocktakeMovements();
  }, [fetchStocktakeMovements]);

  useEffect(() => {
    if (!stocktakes.length) {
      if (selectedStocktakeId !== null) {
        setSelectedStocktakeId(null);
      }
      return;
    }

    const hasSelectedStocktake = stocktakes.some((item) => item.id === selectedStocktakeId);
    if (!hasSelectedStocktake) {
      setSelectedStocktakeId(stocktakes[0].id);
    }
  }, [selectedStocktakeId, stocktakes]);

  const selectedStocktake = useMemo(
    () => stocktakes.find((item) => item.id === selectedStocktakeId) || null,
    [selectedStocktakeId, stocktakes],
  );

  const selectedStocktakeAlert = useMemo(() => {
    if (!selectedStocktake) {
      return null;
    }

    if (selectedStocktake.status === 'confirmed') {
      return {
        type: 'success',
        title: 'Phiếu đã xác nhận và tồn kho đã được cập nhật theo số thực tế.',
        description: `Hệ thống đã đồng bộ ${formatNumber(selectedStocktake.detail_count)} dòng kiểm kê của phiếu ${selectedStocktake.stocktake_code}.`,
      };
    }

    if (selectedStocktake.status === 'cancelled') {
      return {
        type: 'info',
        title: 'Phiếu đã hủy, tồn kho không thay đổi.',
        description: 'Phiếu được giữ lại để đối chiếu lịch sử nhưng không thể chỉnh sửa hoặc xác nhận thêm.',
      };
    }

    return {
      type: 'warning',
      title: 'Phiếu đang ở trạng thái nháp, chưa làm thay đổi tồn kho thật.',
      description: 'Bạn có thể sửa số lượng thực tế trước khi xác nhận. Chỉ khi xác nhận hệ thống mới sinh movement và cập nhật tồn kho.',
    };
  }, [selectedStocktake]);

  const summary = useMemo(() => {
    const draftCount = stocktakes.filter((item) => item.status === 'draft').length;
    const confirmedCount = stocktakes.filter((item) => item.status === 'confirmed').length;
    const totalDifference = stocktakes.reduce(
      (sum, item) => sum + Number(item.total_difference_quantity || 0),
      0,
    );

    return {
      draftCount,
      confirmedCount,
      totalDifference,
    };
  }, [stocktakes]);

  const getSystemQuantity = useCallback((warehouseId, locationId, productId) => {
    if (!warehouseId || !locationId || !productId) {
      return 0;
    }
    const inventoryRow = inventoryLookup.get(buildInventoryKey(warehouseId, locationId, productId));
    return Number(inventoryRow?.quantity || 0);
  }, [inventoryLookup]);

  const openCreateDrawer = () => {
    setEditingStocktake(null);
    form.resetFields();
    form.setFieldsValue({
      warehouse_id: undefined,
      note: '',
      details: [{ product_id: undefined, location_id: undefined, actual_quantity: 0, note: '' }],
    });
    setDrawerOpen(true);
  };

  const openEditDrawer = (stocktake) => {
    setEditingStocktake(stocktake);
    form.resetFields();
    form.setFieldsValue({
      warehouse_id: stocktake.warehouse_id,
      note: stocktake.note || '',
      details: stocktake.details.map((detail) => ({
        product_id: detail.product_id,
        location_id: detail.location_id,
        actual_quantity: detail.actual_quantity,
        note: detail.note || '',
      })),
    });
    setDrawerOpen(true);
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
    setEditingStocktake(null);
    form.resetFields();
  };

  const handleSubmitDraft = async (values) => {
    const payload = {
      warehouse_id: values.warehouse_id,
      note: values.note?.trim() || null,
      details: values.details.map((item) => ({
        product_id: item.product_id,
        location_id: item.location_id,
        actual_quantity: Number(item.actual_quantity || 0),
        note: item.note?.trim() || null,
      })),
    };

    setSubmitting(true);
    try {
      const response = editingStocktake
        ? await api.put(`/stocktakes/${editingStocktake.id}`, payload)
        : await api.post('/stocktakes', payload);
      message.success(editingStocktake ? 'Đã cập nhật phiếu kiểm kê nháp.' : 'Đã tạo phiếu kiểm kê nháp.');
      setSelectedStocktakeId(response.data.item?.id || null);
      closeDrawer();
      await fetchStocktakes({ page: editingStocktake ? currentPage : 1 });
    } catch (error) {
      message.error(error.response?.data?.message || 'Không lưu được phiếu kiểm kê.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleConfirm = async (stocktake) => {
    const nextStatusFilter = statusFilter === 'draft' ? 'all' : statusFilter;

    setConfirmingId(stocktake.id);
    try {
      await api.post(`/stocktakes/${stocktake.id}/confirm`);
      message.success(`Đã xác nhận phiếu ${stocktake.stocktake_code} và cập nhật tồn kho thật.`);
      setSelectedStocktakeId(stocktake.id);

      if (nextStatusFilter !== statusFilter) {
        setStatusFilter(nextStatusFilter);
        setPagination((current) => ({ ...current, current: 1 }));
      }

      await Promise.all([
        fetchStocktakes({
          page: 1,
          status: nextStatusFilter,
          warehouse: warehouseFilter,
          search: searchQuery,
        }),
        fetchInventoryRows(),
        fetchStocktakeMovements(stocktake.id),
      ]);
    } catch (error) {
      message.error(error.response?.data?.message || 'Không xác nhận được phiếu kiểm kê.');
    } finally {
      setConfirmingId(null);
    }
  };

  const handleCancel = async (stocktake) => {
    const nextStatusFilter = statusFilter === 'draft' ? 'all' : statusFilter;

    setCancellingId(stocktake.id);
    try {
      await api.post(`/stocktakes/${stocktake.id}/cancel`);
      message.success(`Đã hủy phiếu ${stocktake.stocktake_code}. Tồn kho không thay đổi.`);
      setSelectedStocktakeId(stocktake.id);

      if (nextStatusFilter !== statusFilter) {
        setStatusFilter(nextStatusFilter);
        setPagination((current) => ({ ...current, current: 1 }));
      }

      await fetchStocktakes({
        page: 1,
        status: nextStatusFilter,
        warehouse: warehouseFilter,
        search: searchQuery,
      });
      setStocktakeMovements([]);
    } catch (error) {
      message.error(error.response?.data?.message || 'Không hủy được phiếu kiểm kê nháp.');
    } finally {
      setCancellingId(null);
    }
  };

  const detailColumns = [
    {
      title: 'Sản phẩm',
      dataIndex: 'product_name',
      render: (value, record) => `${value} (${record.product_code})`,
    },
    {
      title: 'Vị trí',
      dataIndex: 'location_name',
      render: (value, record) => `${value} (${record.location_code})`,
    },
    {
      title: 'Tồn hệ thống',
      dataIndex: 'system_quantity',
      render: formatNumber,
    },
    {
      title: 'Tồn thực tế',
      dataIndex: 'actual_quantity',
      render: formatNumber,
    },
    {
      title: 'Chênh lệch',
      dataIndex: 'difference_quantity',
      render: (value) => (
        <Typography.Text type={value === 0 ? 'secondary' : value > 0 ? 'success' : 'danger'}>
          {formatNumber(value)}
        </Typography.Text>
      ),
    },
    {
      title: 'Ghi chú',
      dataIndex: 'note',
      render: (value) => value || '-',
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
      title: 'Loại movement',
      dataIndex: 'movement_type',
      render: (value) => <StatusTag value={value} />,
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
    {
      title: 'Ghi chú',
      dataIndex: 'note',
      render: (value) => value || '-',
    },
  ];

  return (
    <Space orientation="vertical" size={18} style={{ width: '100%' }}>
      <Card className="page-card" styles={{ body: { padding: 28 } }}>
        <Space orientation="vertical" size={10} style={{ width: '100%' }}>
          <Typography.Text className="resource-eyebrow">
            Module 6.5 · Phiếu kiểm kê nhiều dòng
          </Typography.Text>
          <Typography.Title level={2} className="page-title">
            Kiểm kê kho
          </Typography.Title>
          <Typography.Paragraph className="page-subtitle" style={{ marginBottom: 0 }}>
            Tạo phiếu kiểm kê nhiều dòng, lưu nháp để rà soát chênh lệch và chỉ cập nhật tồn kho thật khi
            xác nhận phiếu.
          </Typography.Paragraph>
        </Space>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12} xl={6}>
          <Card className="page-card" styles={{ body: { padding: 20 } }}>
            <Typography.Text type="secondary">Tổng phiếu theo bộ lọc</Typography.Text>
            <div className="metric-value">{formatNumber(pagination.total)}</div>
            <Typography.Text type="secondary">Danh sách đang hiển thị theo server-side</Typography.Text>
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="page-card" styles={{ body: { padding: 20 } }}>
            <Typography.Text type="secondary">Phiếu nháp trên trang</Typography.Text>
            <div className="metric-value">{formatNumber(summary.draftCount)}</div>
            <Typography.Text type="secondary">Có thể sửa hoặc hủy trước khi xác nhận</Typography.Text>
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="page-card" styles={{ body: { padding: 20 } }}>
            <Typography.Text type="secondary">Phiếu đã xác nhận trên trang</Typography.Text>
            <div className="metric-value">{formatNumber(summary.confirmedCount)}</div>
            <Typography.Text type="secondary">Đã sinh movement stocktake vào tồn kho</Typography.Text>
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="page-card" styles={{ body: { padding: 20 } }}>
            <Typography.Text type="secondary">Tổng chênh lệch trên trang</Typography.Text>
            <div className="metric-value">{formatNumber(summary.totalDifference)}</div>
            <Typography.Text type="secondary">Giúp demo nhanh khối lượng điều chỉnh cần xử lý</Typography.Text>
          </Card>
        </Col>
      </Row>

      <SectionCard
        title="Danh sách phiếu kiểm kê"
        subtitle="Có thể tìm kiếm theo mã phiếu, ghi chú hoặc kho, sau đó theo dõi chi tiết và xác nhận phiếu nháp."
        extra={canManage ? (
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreateDrawer}>
            Thêm phiếu kiểm kê
          </Button>
        ) : null}
      >
        <div className="section-toolbar resource-toolbar">
          <Space wrap size={12}>
            <Input.Search
              allowClear
              enterButton="Tìm"
              placeholder="Tìm theo mã phiếu, ghi chú hoặc kho"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              onSearch={(value) => {
                setSearchInput(value);
                setSearchQuery(value.trim());
                setPagination((current) => ({ ...current, current: 1 }));
              }}
              style={{ width: 280 }}
            />
            <Select
              options={STATUS_OPTIONS}
              value={statusFilter}
              onChange={(value) => {
                setStatusFilter(value);
                setPagination((current) => ({ ...current, current: 1 }));
              }}
              style={{ width: 200 }}
            />
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="Lọc theo kho"
              options={warehouseOptions}
              value={warehouseFilter === 'all' ? undefined : warehouseFilter}
              onChange={(value) => {
                setWarehouseFilter(value ?? 'all');
                setPagination((current) => ({ ...current, current: 1 }));
              }}
              style={{ width: 240 }}
            />
          </Space>

          <Button
            icon={<ReloadOutlined />}
            onClick={() => Promise.all([fetchStocktakes(), fetchInventoryRows()])}
          >
            Làm mới
          </Button>
        </div>

        <Table
          rowKey="id"
          loading={loading}
          dataSource={stocktakes}
          expandable={{
            expandedRowRender: (record) => (
              <Space orientation="vertical" size={12} style={{ width: '100%' }}>
                {record.note ? (
                  <Alert
                    type="info"
                    showIcon
                    title="Ghi chú phiếu kiểm kê"
                    description={record.note}
                  />
                ) : null}
                <Table
                  rowKey="id"
                  size="small"
                  pagination={false}
                  dataSource={record.details}
                  columns={detailColumns}
                />
              </Space>
            ),
          }}
          columns={[
            {
              title: 'Mã phiếu',
              dataIndex: 'stocktake_code',
              render: (value) => <Typography.Text strong>{value}</Typography.Text>,
            },
            {
              title: 'Kho',
              dataIndex: 'warehouse_name',
              render: (value, record) => `${value} (${record.warehouse_code})`,
            },
            {
              title: 'Số dòng',
              dataIndex: 'detail_count',
              render: formatNumber,
            },
            {
              title: 'Tổng tồn thực tế',
              dataIndex: 'total_actual_quantity',
              render: formatNumber,
            },
            {
              title: 'Tổng chênh lệch',
              dataIndex: 'total_difference_quantity',
              render: formatNumber,
            },
            {
              title: 'Trạng thái',
              dataIndex: 'status',
              render: (value) => <StatusTag value={value} />,
            },
            {
              title: 'Người tạo',
              dataIndex: 'created_by_name',
              render: (value) => value || '-',
            },
            {
              title: 'Tạo lúc',
              dataIndex: 'created_at',
              render: formatDateTime,
            },
            {
              title: 'Thao tác',
              key: 'actions',
              width: 420,
              render: (_, record) => (
                <Space wrap>
                  <Button size="small" onClick={() => setSelectedStocktakeId(record.id)}>
                    Theo dõi phiếu
                  </Button>
                  {canManage && record.status === 'draft' ? (
                    <>
                      <Button
                        size="small"
                        icon={<EditOutlined />}
                        onClick={(event) => {
                          event.stopPropagation();
                          openEditDrawer(record);
                        }}
                      >
                        Chỉnh sửa
                      </Button>
                      <Button
                        size="small"
                        type="primary"
                        icon={<CheckCircleOutlined />}
                        loading={confirmingId === record.id}
                        onClick={(event) => {
                          event.stopPropagation();
                          handleConfirm(record);
                        }}
                      >
                        Xác nhận
                      </Button>
                      <Popconfirm
                        title="Hủy phiếu kiểm kê nháp?"
                        description="Phiếu sẽ chuyển sang trạng thái hủy và không làm thay đổi tồn kho."
                        okText="Hủy phiếu"
                        cancelText="Giữ lại"
                        okButtonProps={{ danger: true }}
                        onConfirm={() => handleCancel(record)}
                      >
                        <Button
                          danger
                          size="small"
                          icon={<StopOutlined />}
                          loading={cancellingId === record.id}
                          onClick={(event) => event.stopPropagation()}
                        >
                          Hủy phiếu
                        </Button>
                      </Popconfirm>
                    </>
                  ) : null}
                </Space>
              ),
            },
          ]}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: pagination.total,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '50'],
          }}
          onChange={(nextPagination) => {
            setPagination((current) => ({
              ...current,
              current: nextPagination.current || 1,
              pageSize: nextPagination.pageSize || current.pageSize,
            }));
          }}
          onRow={(record) => ({
            onClick: () => setSelectedStocktakeId(record.id),
          })}
          scroll={{ x: 1360 }}
          locale={{
            emptyText: (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="Chưa có phiếu kiểm kê nào phù hợp với bộ lọc hiện tại."
              />
            ),
          }}
        />
      </SectionCard>

      <SectionCard
        title={selectedStocktake ? `Phiếu đang theo dõi: ${selectedStocktake.stocktake_code}` : 'Chi tiết phiếu kiểm kê'}
        subtitle="Theo dõi chênh lệch từng dòng và lịch sử movement phát sinh sau khi xác nhận."
      >
        {!selectedStocktake ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="Chọn một phiếu kiểm kê để xem chi tiết và lịch sử biến động."
          />
        ) : (
          <Space orientation="vertical" size={16} style={{ width: '100%' }}>
            <Alert
              type={selectedStocktakeAlert.type}
              showIcon
              title={selectedStocktakeAlert.title}
              description={selectedStocktakeAlert.description}
            />

            <Card className="page-card" styles={{ body: { padding: 18 } }}>
              <Space orientation="vertical" size={12} style={{ width: '100%' }}>
                <Typography.Title level={5} style={{ margin: 0 }}>
                  Chi tiết dòng kiểm kê
                </Typography.Title>
                <Table
                  rowKey="id"
                  size="small"
                  pagination={false}
                  dataSource={selectedStocktake.details}
                  columns={detailColumns}
                />
              </Space>
            </Card>

            <Card className="page-card" styles={{ body: { padding: 18 } }}>
              <Space orientation="vertical" size={12} style={{ width: '100%' }}>
                <Typography.Title level={5} style={{ margin: 0 }}>
                  Lịch sử biến động
                </Typography.Title>
                <Typography.Text type="secondary">
                  Phiếu đã xác nhận sẽ sinh movement `stocktake_adjustment` cho từng dòng có chênh lệch thực tế.
                </Typography.Text>
                <Table
                  rowKey="id"
                  size="small"
                  loading={movementLoading}
                  pagination={false}
                  dataSource={stocktakeMovements}
                  columns={movementColumns}
                  scroll={{ x: 1240 }}
                  locale={{
                    emptyText: (
                      <Empty
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        description={selectedStocktake.status === 'confirmed'
                          ? 'Phiếu đã xác nhận nhưng chưa có movement nào phù hợp để hiển thị.'
                          : 'Phiếu nháp chưa phát sinh biến động tồn kho.'}
                      />
                    ),
                  }}
                />
              </Space>
            </Card>
          </Space>
        )}
      </SectionCard>

      <Drawer
        open={drawerOpen}
        onClose={closeDrawer}
        destroyOnClose
        size={900}
        title={editingStocktake ? `Chỉnh sửa phiếu ${editingStocktake.stocktake_code}` : 'Thêm phiếu kiểm kê nháp'}
      >
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          <Alert
            showIcon
            type={editingStocktake ? 'warning' : 'info'}
            title={editingStocktake ? 'Chỉnh sửa phiếu kiểm kê nháp trước khi xác nhận' : 'Tạo phiếu kiểm kê nhiều dòng cho demo'}
            description={editingStocktake
              ? 'Hệ thống sẽ tính lại tồn hệ thống khi bạn lưu nháp. Tồn kho thật chỉ thay đổi khi xác nhận phiếu.'
              : 'Bước này chỉ lưu phiếu nháp để rà soát chênh lệch. Sau khi xác nhận, hệ thống mới ghi movement và cập nhật tồn kho.'}
          />

          <Form
            form={form}
            layout="vertical"
            onFinish={handleSubmitDraft}
            onValuesChange={(changedValues, allValues) => {
              if (
                Object.prototype.hasOwnProperty.call(changedValues, 'warehouse_id')
                && Array.isArray(allValues.details)
              ) {
                form.setFieldsValue({
                  details: allValues.details.map((item) => ({
                    ...item,
                    location_id: undefined,
                  })),
                });
              }
            }}
          >
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item
                  label="Kho kiểm kê"
                  name="warehouse_id"
                  rules={[{ required: true, message: 'Vui lòng chọn kho kiểm kê.' }]}
                >
                  <Select
                    showSearch
                    optionFilterProp="label"
                    placeholder="Chọn kho cần kiểm kê"
                    options={warehouseOptions}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item label="Ghi chú phiếu" name="note">
                  <Input
                    allowClear
                    placeholder="Ví dụ: Kiểm kê cuối ngày ca chiều"
                  />
                </Form.Item>
              </Col>
            </Row>

            <Form.List
              name="details"
              rules={[
                {
                  validator: async (_, value) => {
                    if (!value || !value.length) {
                      throw new Error('Phiếu kiểm kê phải có ít nhất một dòng hàng.');
                    }
                  },
                },
              ]}
            >
              {(fields, { add, remove }, { errors }) => (
                <Space orientation="vertical" size={12} style={{ width: '100%' }}>
                  <Space align="center" style={{ justifyContent: 'space-between', width: '100%' }}>
                    <Typography.Title level={5} style={{ margin: 0 }}>
                      Dòng kiểm kê
                    </Typography.Title>
                    <Button
                      icon={<PlusOutlined />}
                      onClick={() => add({
                        product_id: undefined,
                        location_id: undefined,
                        actual_quantity: 0,
                        note: '',
                      })}
                    >
                      Thêm dòng kiểm kê
                    </Button>
                  </Space>

                  {fields.map((field, index) => {
                    const watchedItem = watchedDetails[field.name] || {};
                    const systemQuantity = getSystemQuantity(
                      watchedWarehouseId,
                      watchedItem.location_id,
                      watchedItem.product_id,
                    );
                    const differenceQuantity = Number(watchedItem.actual_quantity || 0) - systemQuantity;

                    return (
                      <Card key={field.key} className="page-card" styles={{ body: { padding: 18 } }}>
                        <Row gutter={16} align="middle">
                          <Col xs={24} md={6}>
                            <Form.Item
                              label={`Sản phẩm ${index + 1}`}
                              name={[field.name, 'product_id']}
                              rules={[{ required: true, message: 'Vui lòng chọn sản phẩm.' }]}
                            >
                              <Select
                                showSearch
                                optionFilterProp="label"
                                placeholder="Chọn sản phẩm"
                                options={productOptions}
                              />
                            </Form.Item>
                          </Col>
                          <Col xs={24} md={5}>
                            <Form.Item
                              label="Vị trí"
                              name={[field.name, 'location_id']}
                              rules={[{ required: true, message: 'Vui lòng chọn vị trí kho.' }]}
                            >
                              <Select
                                showSearch
                                optionFilterProp="label"
                                placeholder={watchedWarehouseId ? 'Chọn vị trí trong kho đã chọn' : 'Chọn kho trước'}
                                options={locationOptions}
                                disabled={!watchedWarehouseId}
                              />
                            </Form.Item>
                          </Col>
                          <Col xs={24} md={4}>
                            <Form.Item label="Tồn hệ thống">
                              <Input value={formatNumber(systemQuantity)} readOnly />
                            </Form.Item>
                          </Col>
                          <Col xs={24} md={4}>
                            <Form.Item
                              label="Tồn thực tế"
                              name={[field.name, 'actual_quantity']}
                              rules={[{ required: true, message: 'Vui lòng nhập tồn thực tế.' }]}
                            >
                              <InputNumber min={0} controls={false} style={{ width: '100%' }} />
                            </Form.Item>
                          </Col>
                          <Col xs={24} md={3}>
                            <Form.Item label="Chênh lệch">
                              <Input value={formatNumber(differenceQuantity)} readOnly />
                            </Form.Item>
                          </Col>
                          <Col xs={24} md={2}>
                            <Button
                              danger
                              type="text"
                              icon={<MinusCircleOutlined />}
                              disabled={fields.length === 1}
                              onClick={() => remove(field.name)}
                            >
                              Xóa
                            </Button>
                          </Col>
                          <Col span={24}>
                            <Form.Item
                              label="Ghi chú dòng kiểm kê"
                              name={[field.name, 'note']}
                            >
                              <Input.TextArea
                                rows={2}
                                allowClear
                                placeholder="Ví dụ: Kiện hàng đang chờ xử lý, phát hiện lệch sau đối chiếu thực tế"
                              />
                            </Form.Item>
                          </Col>
                        </Row>
                      </Card>
                    );
                  })}

                  {errors.length ? (
                    <Alert type="error" showIcon title={errors[0]} />
                  ) : null}
                </Space>
              )}
            </Form.List>

            <div className="resource-drawer-actions">
              <Button onClick={closeDrawer}>Đóng</Button>
              <Button type="primary" htmlType="submit" loading={submitting}>
                {editingStocktake ? 'Lưu phiếu nháp' : 'Tạo phiếu nháp'}
              </Button>
            </div>
          </Form>
        </Space>
      </Drawer>
    </Space>
  );
}

export default StocktakesPage;
