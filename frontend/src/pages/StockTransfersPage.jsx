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

function StockTransfersPage() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission('stock_transfers.manage');
  const canViewInventory = hasPermission('inventory.view');

  const [form] = Form.useForm();
  const watchedSourceWarehouseId = Form.useWatch('source_warehouse_id', form);
  const watchedTargetWarehouseId = Form.useWatch('target_warehouse_id', form);

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [confirmingId, setConfirmingId] = useState(null);
  const [cancellingId, setCancellingId] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingTransfer, setEditingTransfer] = useState(null);
  const [transfers, setTransfers] = useState([]);
  const [inventoryRows, setInventoryRows] = useState([]);
  const [transferMovements, setTransferMovements] = useState([]);
  const [movementLoading, setMovementLoading] = useState(false);
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sourceWarehouseFilter, setSourceWarehouseFilter] = useState('all');
  const [targetWarehouseFilter, setTargetWarehouseFilter] = useState('all');
  const [selectedTransferId, setSelectedTransferId] = useState(null);
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

  const warehouseOptions = options.warehouses.map((item) => ({
    label: `${item.warehouse_name} (${item.warehouse_code})`,
    value: item.id,
  }));

  const productOptions = options.products.map((item) => ({
    label: `${item.product_name} (${item.product_code}) - tồn tổng ${formatNumber(item.quantity_total || 0)}`,
    value: item.id,
  }));

  const sourceLocationOptions = useMemo(
    () => options.locations
      .filter((item) => !watchedSourceWarehouseId || item.warehouse_id === watchedSourceWarehouseId)
      .map((item) => ({
        label: `${item.location_name} (${item.location_code})`,
        value: item.id,
      })),
    [options.locations, watchedSourceWarehouseId],
  );

  const targetLocationOptions = useMemo(
    () => options.locations
      .filter((item) => !watchedTargetWarehouseId || item.warehouse_id === watchedTargetWarehouseId)
      .map((item) => ({
        label: `${item.location_name} (${item.location_code})`,
        value: item.id,
      })),
    [options.locations, watchedTargetWarehouseId],
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
      message.error(error.response?.data?.message || 'Không tải được dữ liệu nền cho phiếu điều chuyển.');
    }
  }, []);

  const fetchTransfers = useCallback(async (overrides = {}) => {
    setLoading(true);
    try {
      const page = overrides.page ?? currentPage;
      const pageSize = overrides.pageSize ?? currentPageSize;
      const nextSearch = overrides.search ?? searchQuery;
      const nextStatus = overrides.status ?? statusFilter;
      const nextSourceWarehouse = overrides.sourceWarehouse ?? sourceWarehouseFilter;
      const nextTargetWarehouse = overrides.targetWarehouse ?? targetWarehouseFilter;
      const params = {
        page,
        page_size: pageSize,
        sort_by: 'created_at',
        sort_order: 'desc',
      };

      if (nextSearch) {
        params.search = nextSearch;
      }
      if (nextStatus !== 'all') {
        params.status = nextStatus;
      }
      if (nextSourceWarehouse !== 'all') {
        params.source_warehouse_id = nextSourceWarehouse;
      }
      if (nextTargetWarehouse !== 'all') {
        params.target_warehouse_id = nextTargetWarehouse;
      }

      const response = await api.get('/stock-transfers', { params });
      setTransfers(response.data.items || []);
      setPagination({
        current: response.data.page || page,
        pageSize: response.data.page_size || pageSize,
        total: response.data.total || 0,
      });
    } catch (error) {
      message.error(error.response?.data?.message || 'Không tải được danh sách phiếu điều chuyển.');
    } finally {
      setLoading(false);
    }
  }, [
    currentPage,
    currentPageSize,
    searchQuery,
    sourceWarehouseFilter,
    statusFilter,
    targetWarehouseFilter,
  ]);

  const fetchInventory = useCallback(async () => {
    if (!canViewInventory) {
      setInventoryRows([]);
      return;
    }

    try {
      const response = await api.get('/inventory');
      setInventoryRows(response.data.items || []);
    } catch (error) {
      message.error(error.response?.data?.message || 'Không tải được dữ liệu tồn kho liên quan.');
    }
  }, [canViewInventory]);

  const fetchTransferMovements = useCallback(async (transferId = selectedTransferId) => {
    if (!canViewInventory || !transferId) {
      setTransferMovements([]);
      return;
    }

    setMovementLoading(true);
    try {
      const response = await api.get('/inventory/movements', {
        params: {
          reference_type: 'stock_transfer',
          reference_id: transferId,
        },
      });
      setTransferMovements(response.data.items || []);
    } catch (error) {
      message.error(error.response?.data?.message || 'Không tải được lịch sử điều chuyển.');
      setTransferMovements([]);
    } finally {
      setMovementLoading(false);
    }
  }, [canViewInventory, selectedTransferId]);

  useEffect(() => {
    fetchOptions();
  }, [fetchOptions]);

  useEffect(() => {
    fetchTransfers();
  }, [fetchTransfers]);

  useEffect(() => {
    fetchInventory();
  }, [fetchInventory]);

  useEffect(() => {
    fetchTransferMovements();
  }, [fetchTransferMovements]);

  useEffect(() => {
    if (!transfers.length) {
      if (selectedTransferId !== null) {
        setSelectedTransferId(null);
      }
      return;
    }

    const hasSelectedTransfer = transfers.some((item) => item.id === selectedTransferId);
    if (!hasSelectedTransfer) {
      setSelectedTransferId(transfers[0].id);
    }
  }, [selectedTransferId, transfers]);

  const selectedTransfer = useMemo(
    () => transfers.find((item) => item.id === selectedTransferId) || null,
    [selectedTransferId, transfers],
  );

  const selectedInventoryRows = useMemo(() => {
    if (!selectedTransfer || !canViewInventory) {
      return [];
    }

    const matchedKeys = new Set();
    selectedTransfer.details.forEach((detail) => {
      matchedKeys.add(`${selectedTransfer.source_warehouse_id}-${detail.source_location_id}-${detail.product_id}`);
      matchedKeys.add(`${selectedTransfer.target_warehouse_id}-${detail.target_location_id}-${detail.product_id}`);
    });

    return inventoryRows.filter((row) => (
      matchedKeys.has(`${row.warehouse_id}-${row.location_id}-${row.product_id}`)
    ));
  }, [canViewInventory, inventoryRows, selectedTransfer]);

  const selectedTransferAlert = useMemo(() => {
    if (!selectedTransfer) {
      return null;
    }

    if (selectedTransfer.status === 'confirmed') {
      return {
        type: 'success',
        title: 'Phiếu đã xác nhận và tồn kho đã được điều chuyển.',
        description: `Hệ thống đã giảm kho ${selectedTransfer.source_warehouse_name} và tăng kho ${selectedTransfer.target_warehouse_name} với tổng ${formatNumber(selectedTransfer.total_quantity)} đơn vị.`,
      };
    }

    if (selectedTransfer.status === 'cancelled') {
      return {
        type: 'info',
        title: 'Phiếu đã hủy, tồn kho không thay đổi.',
        description: 'Phiếu này được giữ lại để đối chiếu lịch sử, nhưng không thể chỉnh sửa hoặc xác nhận thêm.',
      };
    }

    return {
      type: 'warning',
      title: 'Phiếu đang ở trạng thái nháp, tồn kho chưa thay đổi.',
      description: 'Khi bấm xác nhận, backend sẽ kiểm tra tồn kho nguồn; nếu đủ hàng thì ghi giảm nguồn, tăng đích và sinh movement để truy vết. Bạn cũng có thể hủy phiếu nếu tạo sai và chưa muốn tác động tồn kho thật.',
    };
  }, [selectedTransfer]);

  const summary = useMemo(() => {
    const draftCount = transfers.filter((item) => item.status === 'draft').length;
    const confirmedCount = transfers.filter((item) => item.status === 'confirmed').length;
    const selectedInventoryQuantity = selectedInventoryRows.reduce(
      (sum, item) => sum + Number(item.quantity || 0),
      0,
    );

    return {
      draftCount,
      confirmedCount,
      selectedInventoryQuantity,
    };
  }, [selectedInventoryRows, transfers]);

  const openCreateDrawer = () => {
    setEditingTransfer(null);
    form.resetFields();
    form.setFieldsValue({
      source_warehouse_id: undefined,
      target_warehouse_id: undefined,
      note: '',
      items: [{
        product_id: undefined,
        source_location_id: undefined,
        target_location_id: undefined,
        quantity: 1,
      }],
    });
    setDrawerOpen(true);
  };

  const openEditDrawer = (transfer) => {
    setEditingTransfer(transfer);
    form.resetFields();
    form.setFieldsValue({
      source_warehouse_id: transfer.source_warehouse_id,
      target_warehouse_id: transfer.target_warehouse_id,
      note: transfer.note || '',
      items: transfer.details.map((detail) => ({
        product_id: detail.product_id,
        source_location_id: detail.source_location_id,
        target_location_id: detail.target_location_id,
        quantity: detail.quantity,
      })),
    });
    setDrawerOpen(true);
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
    setEditingTransfer(null);
    form.resetFields();
  };

  const handleSubmitDraft = async (values) => {
    const payload = {
      source_warehouse_id: values.source_warehouse_id,
      target_warehouse_id: values.target_warehouse_id,
      note: values.note?.trim() || null,
      items: values.items.map((item) => ({
        product_id: item.product_id,
        source_location_id: item.source_location_id,
        target_location_id: item.target_location_id,
        quantity: Number(item.quantity || 0),
      })),
    };

    setSubmitting(true);
    try {
      const response = editingTransfer
        ? await api.put(`/stock-transfers/${editingTransfer.id}`, payload)
        : await api.post('/stock-transfers', payload);
      message.success(editingTransfer ? 'Đã cập nhật phiếu điều chuyển nháp.' : 'Đã tạo phiếu điều chuyển nháp.');
      setSelectedTransferId(response.data.item?.id || null);
      closeDrawer();
      await fetchTransfers({ page: editingTransfer ? currentPage : 1 });
    } catch (error) {
      message.error(error.response?.data?.message || 'Không lưu được phiếu điều chuyển.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleConfirm = async (transfer) => {
    const nextStatusFilter = statusFilter === 'draft' ? 'all' : statusFilter;

    setConfirmingId(transfer.id);
    try {
      await api.post(`/stock-transfers/${transfer.id}/confirm`);
      message.success(`Đã xác nhận phiếu ${transfer.transfer_code} và cập nhật tồn kho hai kho.`);
      setSelectedTransferId(transfer.id);

      if (nextStatusFilter !== statusFilter) {
        setStatusFilter(nextStatusFilter);
        setPagination((current) => ({ ...current, current: 1 }));
      }

      await Promise.all([
        fetchTransfers({
          page: 1,
          status: nextStatusFilter,
          sourceWarehouse: sourceWarehouseFilter,
          targetWarehouse: targetWarehouseFilter,
          search: searchQuery,
        }),
        fetchInventory(),
        fetchTransferMovements(transfer.id),
      ]);
    } catch (error) {
      message.error(error.response?.data?.message || 'Không xác nhận được phiếu điều chuyển.');
    } finally {
      setConfirmingId(null);
    }
  };

  const handleCancel = async (transfer) => {
    const nextStatusFilter = statusFilter === 'draft' ? 'all' : statusFilter;

    setCancellingId(transfer.id);
    try {
      await api.post(`/stock-transfers/${transfer.id}/cancel`);
      message.success(`Đã hủy phiếu ${transfer.transfer_code}. Tồn kho không thay đổi.`);
      setSelectedTransferId(transfer.id);

      if (nextStatusFilter !== statusFilter) {
        setStatusFilter(nextStatusFilter);
        setPagination((current) => ({ ...current, current: 1 }));
      }

      await fetchTransfers({
        page: 1,
        status: nextStatusFilter,
        sourceWarehouse: sourceWarehouseFilter,
        targetWarehouse: targetWarehouseFilter,
        search: searchQuery,
      });
      setTransferMovements([]);
    } catch (error) {
      message.error(error.response?.data?.message || 'Không hủy được phiếu điều chuyển nháp.');
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
      title: 'Vị trí nguồn',
      dataIndex: 'source_location_name',
      render: (value, record) => `${value} (${record.source_location_code})`,
    },
    {
      title: 'Vị trí đích',
      dataIndex: 'target_location_name',
      render: (value, record) => `${value} (${record.target_location_code})`,
    },
    {
      title: 'Số lượng điều chuyển',
      dataIndex: 'quantity',
      render: formatNumber,
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
      render: (value) => value || '-',
    },
    {
      title: 'Vị trí',
      dataIndex: 'location_name',
      render: (value) => value || '-',
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
  ];

  return (
    <Space orientation="vertical" size={18} style={{ width: '100%' }}>
      <Card className="page-card" styles={{ body: { padding: 28 } }}>
        <Space orientation="vertical" size={10} style={{ width: '100%' }}>
          <Typography.Text className="resource-eyebrow">
            Module 6 · Luồng điều chuyển kho tối thiểu
          </Typography.Text>
          <Typography.Title level={2} className="page-title">
            Điều chuyển kho
          </Typography.Title>
          <Typography.Paragraph className="page-subtitle" style={{ marginBottom: 0 }}>
            Tạo phiếu điều chuyển nháp, xác nhận phiếu và theo dõi ngay tác động giảm tồn kho nguồn,
            tăng tồn kho đích. Luồng này giúp demo rõ cách hàng hóa di chuyển giữa nhiều kho.
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
            <Typography.Text type="secondary">Chưa thay đổi tồn kho thật</Typography.Text>
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="page-card" styles={{ body: { padding: 20 } }}>
            <Typography.Text type="secondary">Phiếu đã xác nhận trên trang</Typography.Text>
            <div className="metric-value">{formatNumber(summary.confirmedCount)}</div>
            <Typography.Text type="secondary">Đã sinh movement giảm nguồn, tăng đích</Typography.Text>
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="page-card" styles={{ body: { padding: 20 } }}>
            <Typography.Text type="secondary">Tồn ở phiếu đang theo dõi</Typography.Text>
            <div className="metric-value">{formatNumber(summary.selectedInventoryQuantity)}</div>
            <Typography.Text type="secondary">Tổng các dòng nguồn và đích liên quan</Typography.Text>
          </Card>
        </Col>
      </Row>

      <SectionCard
        title="Danh sách phiếu điều chuyển"
        subtitle="Có thể tìm kiếm, lọc theo trạng thái, kho nguồn hoặc kho đích. Bấm Theo dõi để xem các dòng tồn kho liên quan."
        extra={canManage ? (
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreateDrawer}>
            Thêm phiếu điều chuyển nháp
          </Button>
        ) : null}
      >
        <div className="section-toolbar resource-toolbar">
          <Space wrap size={12}>
            <Input.Search
              allowClear
              enterButton="Tìm"
              placeholder="Tìm theo mã phiếu, ghi chú, kho nguồn hoặc kho đích"
              value={searchInput}
              onChange={(event) => {
                const nextValue = event.target.value;
                setSearchInput(nextValue);
                if (!nextValue) {
                  setSearchQuery('');
                  setPagination((current) => ({ ...current, current: 1 }));
                }
              }}
              onSearch={(value) => {
                setSearchQuery(value.trim());
                setPagination((current) => ({ ...current, current: 1 }));
              }}
              style={{ width: 340, maxWidth: '100%' }}
            />
            <Select
              value={statusFilter}
              onChange={(value) => {
                setStatusFilter(value);
                setPagination((current) => ({ ...current, current: 1 }));
              }}
              options={STATUS_OPTIONS}
              style={{ width: 180 }}
            />
            <Select
              allowClear
              value={sourceWarehouseFilter === 'all' ? undefined : sourceWarehouseFilter}
              onChange={(value) => {
                setSourceWarehouseFilter(value || 'all');
                setPagination((current) => ({ ...current, current: 1 }));
              }}
              placeholder="Lọc kho nguồn"
              options={warehouseOptions}
              style={{ width: 240 }}
            />
            <Select
              allowClear
              value={targetWarehouseFilter === 'all' ? undefined : targetWarehouseFilter}
              onChange={(value) => {
                setTargetWarehouseFilter(value || 'all');
                setPagination((current) => ({ ...current, current: 1 }));
              }}
              placeholder="Lọc kho đích"
              options={warehouseOptions}
              style={{ width: 240 }}
            />
            <Button icon={<ReloadOutlined />} onClick={() => {
              fetchTransfers();
              fetchInventory();
            }}
            >
              Làm mới
            </Button>
          </Space>
          <Typography.Text type="secondary">
            Xác nhận phiếu sẽ kiểm tra đủ tồn ở kho nguồn, sau đó sinh 2 movement để truy vết điều chuyển.
          </Typography.Text>
        </div>

        <Table
          rowKey="id"
          loading={loading}
          dataSource={transfers}
          expandable={{
            expandedRowRender: (record) => (
              <Space orientation="vertical" size={12} style={{ width: '100%' }}>
                {record.note ? (
                  <Alert
                    type="info"
                    showIcon
                    title="Ghi chú phiếu điều chuyển"
                    description={record.note}
                  />
                ) : null}
                <Table
                  rowKey="id"
                  pagination={false}
                  size="small"
                  columns={detailColumns}
                  dataSource={record.details}
                />
              </Space>
            ),
          }}
          columns={[
            {
              title: 'Mã phiếu',
              dataIndex: 'transfer_code',
              render: (value) => <Typography.Text strong>{value}</Typography.Text>,
            },
            {
              title: 'Kho nguồn',
              dataIndex: 'source_warehouse_name',
              render: (value, record) => `${value} (${record.source_warehouse_code})`,
            },
            {
              title: 'Kho đích',
              dataIndex: 'target_warehouse_name',
              render: (value, record) => `${value} (${record.target_warehouse_code})`,
            },
            {
              title: 'Tổng số lượng',
              dataIndex: 'total_quantity',
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
              width: 400,
              render: (_, record) => (
                <Space wrap>
                  <Button size="small" onClick={() => setSelectedTransferId(record.id)}>
                    Theo dõi tồn kho
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
                        title="Hủy phiếu điều chuyển nháp?"
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
            onClick: () => setSelectedTransferId(record.id),
          })}
          scroll={{ x: 1280 }}
          locale={{
            emptyText: (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="Chưa có phiếu điều chuyển nào phù hợp với bộ lọc hiện tại."
              />
            ),
          }}
        />
      </SectionCard>

      <SectionCard
        title={selectedTransfer ? `Phiếu đang theo dõi: ${selectedTransfer.transfer_code}` : 'Tồn kho phản ánh theo phiếu'}
        subtitle="Khu vực này cho thấy tồn kho hiện tại của các dòng nguồn và đích liên quan tới phiếu điều chuyển."
      >
        {!selectedTransfer ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="Chọn một phiếu điều chuyển để theo dõi tác động lên tồn kho."
          />
        ) : (
          <Space orientation="vertical" size={16} style={{ width: '100%' }}>
            <Alert
              type={selectedTransferAlert.type}
              showIcon
              title={selectedTransferAlert.title}
              description={selectedTransferAlert.description}
            />

            <Card className="page-card" styles={{ body: { padding: 18 } }}>
              <Space orientation="vertical" size={12} style={{ width: '100%' }}>
                <Typography.Title level={5} style={{ margin: 0 }}>
                  Chi tiết dòng hàng của phiếu
                </Typography.Title>
                <Table
                  rowKey="id"
                  size="small"
                  pagination={false}
                  dataSource={selectedTransfer.details}
                  columns={detailColumns}
                />
              </Space>
            </Card>

            {canViewInventory ? (
              <>
                <Card className="page-card" styles={{ body: { padding: 18 } }}>
                  <Space orientation="vertical" size={12} style={{ width: '100%' }}>
                    <Typography.Title level={5} style={{ margin: 0 }}>
                      Tồn kho hiện tại tại các vị trí nguồn và đích
                    </Typography.Title>
                    <Table
                      rowKey="id"
                      size="small"
                      pagination={false}
                      dataSource={selectedInventoryRows}
                      columns={[
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
                          render: (value, record) => `${value} (${record.product_code})`,
                        },
                        {
                          title: 'Tồn hiện tại',
                          dataIndex: 'quantity',
                          render: formatNumber,
                        },
                        {
                          title: 'Cập nhật gần nhất',
                          dataIndex: 'updated_at',
                          render: formatDateTime,
                        },
                      ]}
                      locale={{
                        emptyText: (
                          <Empty
                            image={Empty.PRESENTED_IMAGE_SIMPLE}
                            description="Chưa tìm thấy dòng tồn kho nào khớp với phiếu đang theo dõi."
                          />
                        ),
                      }}
                    />
                  </Space>
                </Card>

                <Card className="page-card" styles={{ body: { padding: 18 } }}>
                  <Space orientation="vertical" size={12} style={{ width: '100%' }}>
                    <Typography.Title level={5} style={{ margin: 0 }}>
                      Lịch sử điều chuyển đã ghi nhận
                    </Typography.Title>
                    <Typography.Text type="secondary">
                      Khi phiếu được xác nhận, hệ thống sẽ sinh 2 movement để truy vết: một dòng giảm ở kho nguồn và một dòng tăng ở kho đích.
                    </Typography.Text>
                    <Table
                      rowKey="id"
                      size="small"
                      loading={movementLoading}
                      pagination={false}
                      dataSource={transferMovements}
                      columns={movementColumns}
                      scroll={{ x: 1180 }}
                      locale={{
                        emptyText: (
                          <Empty
                            image={Empty.PRESENTED_IMAGE_SIMPLE}
                            description={selectedTransfer.status === 'confirmed'
                              ? 'Phiếu đã xác nhận nhưng chưa có movement nào khớp để hiển thị.'
                              : 'Phiếu chỉ sinh movement sau khi được xác nhận.'}
                          />
                        ),
                      }}
                    />
                  </Space>
                </Card>
              </>
            ) : null}
          </Space>
        )}
      </SectionCard>

      <Drawer
        open={drawerOpen}
        onClose={closeDrawer}
        destroyOnClose
        size={820}
        title={editingTransfer ? `Chỉnh sửa phiếu ${editingTransfer.transfer_code}` : 'Thêm phiếu điều chuyển nháp'}
      >
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          <Alert
            showIcon
            type={editingTransfer ? 'warning' : 'info'}
            title={editingTransfer ? 'Chỉnh sửa phiếu điều chuyển nháp trước khi xác nhận' : 'Tạo phiếu điều chuyển tối thiểu cho demo'}
            description={editingTransfer ? 'Bạn có thể sửa kho nguồn, kho đích, vị trí, sản phẩm hoặc số lượng khi phiếu còn nháp. Tồn kho vẫn chưa thay đổi cho đến khi xác nhận.' : 'Bước này chỉ tạo phiếu nháp. Tồn kho chỉ đổi thật khi bạn quay lại danh sách và bấm xác nhận phiếu.'}
          />

          <Form
            form={form}
            layout="vertical"
            onFinish={handleSubmitDraft}
            onValuesChange={(changedValues, allValues) => {
              if (!Array.isArray(allValues.items)) {
                return;
              }

              if (Object.prototype.hasOwnProperty.call(changedValues, 'source_warehouse_id')) {
                form.setFieldsValue({
                  items: allValues.items.map((item) => ({
                    ...item,
                    source_location_id: undefined,
                  })),
                });
              }

              if (Object.prototype.hasOwnProperty.call(changedValues, 'target_warehouse_id')) {
                form.setFieldsValue({
                  items: allValues.items.map((item) => ({
                    ...item,
                    target_location_id: undefined,
                  })),
                });
              }
            }}
          >
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item
                  label="Kho nguồn"
                  name="source_warehouse_id"
                  rules={[{ required: true, message: 'Vui lòng chọn kho nguồn.' }]}
                >
                  <Select
                    showSearch
                    optionFilterProp="label"
                    placeholder="Chọn kho xuất hàng đi"
                    options={warehouseOptions}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item
                  label="Kho đích"
                  name="target_warehouse_id"
                  rules={[{ required: true, message: 'Vui lòng chọn kho đích.' }]}
                >
                  <Select
                    showSearch
                    optionFilterProp="label"
                    placeholder="Chọn kho nhận hàng"
                    options={warehouseOptions}
                  />
                </Form.Item>
              </Col>
              <Col span={24}>
                <Form.Item label="Ghi chú" name="note">
                  <Input.TextArea
                    rows={3}
                    allowClear
                    placeholder="Ví dụ: Điều chuyển máy quét từ kho trung tâm sang kho miền Nam"
                  />
                </Form.Item>
              </Col>
            </Row>

            <Form.List
              name="items"
              rules={[
                {
                  validator: async (_, value) => {
                    if (!value || !value.length) {
                      throw new Error('Phiếu điều chuyển phải có ít nhất một dòng hàng.');
                    }
                  },
                },
              ]}
            >
              {(fields, { add, remove }, { errors }) => (
                <Space orientation="vertical" size={12} style={{ width: '100%' }}>
                  <Space align="center" style={{ justifyContent: 'space-between', width: '100%' }}>
                    <Typography.Title level={5} style={{ margin: 0 }}>
                      Dòng hàng điều chuyển
                    </Typography.Title>
                    <Button
                      icon={<PlusOutlined />}
                      onClick={() => add({
                        product_id: undefined,
                        source_location_id: undefined,
                        target_location_id: undefined,
                        quantity: 1,
                      })}
                    >
                      Thêm dòng hàng
                    </Button>
                  </Space>

                  {fields.map((field, index) => (
                    <Card key={field.key} className="page-card" styles={{ body: { padding: 18 } }}>
                      <Row gutter={16} align="middle">
                        <Col xs={24} md={6}>
                          <Form.Item
                            {...field}
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
                        <Col xs={24} md={6}>
                          <Form.Item
                            {...field}
                            label="Vị trí nguồn"
                            name={[field.name, 'source_location_id']}
                            rules={[{ required: true, message: 'Vui lòng chọn vị trí nguồn.' }]}
                          >
                            <Select
                              showSearch
                              optionFilterProp="label"
                              placeholder={watchedSourceWarehouseId ? 'Chọn vị trí nguồn' : 'Chọn kho nguồn trước'}
                              options={sourceLocationOptions}
                              disabled={!watchedSourceWarehouseId}
                            />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={6}>
                          <Form.Item
                            {...field}
                            label="Vị trí đích"
                            name={[field.name, 'target_location_id']}
                            rules={[{ required: true, message: 'Vui lòng chọn vị trí đích.' }]}
                          >
                            <Select
                              showSearch
                              optionFilterProp="label"
                              placeholder={watchedTargetWarehouseId ? 'Chọn vị trí đích' : 'Chọn kho đích trước'}
                              options={targetLocationOptions}
                              disabled={!watchedTargetWarehouseId}
                            />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={4}>
                          <Form.Item
                            {...field}
                            label="Số lượng"
                            name={[field.name, 'quantity']}
                            rules={[{ required: true, message: 'Vui lòng nhập số lượng.' }]}
                          >
                            <InputNumber style={{ width: '100%' }} min={1} controls={false} />
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
                      </Row>
                    </Card>
                  ))}

                  {errors.length ? (
                    <Alert
                      type="error"
                      showIcon
                      message={errors[0]}
                    />
                  ) : null}
                </Space>
              )}
            </Form.List>

            <div className="resource-drawer-actions">
              <Button onClick={closeDrawer}>Đóng</Button>
              <Button type="primary" htmlType="submit" loading={submitting}>
                {editingTransfer ? 'Lưu phiếu nháp' : 'Tạo phiếu nháp'}
              </Button>
            </div>
          </Form>
        </Space>
      </Drawer>
    </Space>
  );
}

export default StockTransfersPage;
