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

function ImportReceiptsPage() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission('import_receipts.manage');
  const canViewInventory = hasPermission('inventory.view');
  const canViewSuppliers = hasPermission('suppliers.view');

  const [form] = Form.useForm();
  const watchedWarehouseId = Form.useWatch('warehouse_id', form);

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [confirmingId, setConfirmingId] = useState(null);
  const [cancellingId, setCancellingId] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingReceipt, setEditingReceipt] = useState(null);
  const [receipts, setReceipts] = useState([]);
  const [inventoryRows, setInventoryRows] = useState([]);
  const [receiptMovements, setReceiptMovements] = useState([]);
  const [movementLoading, setMovementLoading] = useState(false);
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [warehouseFilter, setWarehouseFilter] = useState('all');
  const [selectedReceiptId, setSelectedReceiptId] = useState(null);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
  });
  const [options, setOptions] = useState({
    warehouses: [],
    locations: [],
    products: [],
    suppliers: [],
  });
  const currentPage = pagination.current;
  const currentPageSize = pagination.pageSize;

  const warehouseOptions = options.warehouses.map((item) => ({
    label: `${item.warehouse_name} (${item.warehouse_code})`,
    value: item.id,
  }));
  const productOptions = options.products.map((item) => ({
    label: `${item.product_name} (${item.product_code})`,
    value: item.id,
  }));
  const supplierOptions = options.suppliers.map((item) => ({
    label: `${item.supplier_name} (${item.supplier_code})`,
    value: item.id,
  }));

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
      const requests = [
        api.get('/warehouses', { params: { page: 1, page_size: 100 } }),
        api.get('/locations', { params: { page: 1, page_size: 100 } }),
        api.get('/products', { params: { page: 1, page_size: 100 } }),
      ];

      if (canViewSuppliers) {
        requests.push(api.get('/suppliers', { params: { page: 1, page_size: 100, status: 'active' } }));
      }

      const responses = await Promise.all(requests);
      const [warehouseResponse, locationResponse, productResponse, supplierResponse] = responses;

      setOptions({
        warehouses: warehouseResponse.data.items || [],
        locations: locationResponse.data.items || [],
        products: productResponse.data.items || [],
        suppliers: supplierResponse?.data.items || [],
      });
    } catch (error) {
      message.error(error.response?.data?.message || 'Không tải được dữ liệu nền cho phiếu nhập.');
    }
  }, [canViewSuppliers]);

  const fetchReceipts = useCallback(async (overrides = {}) => {
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
        params.search = nextSearch;
      }
      if (nextStatus !== 'all') {
        params.status = nextStatus;
      }
      if (nextWarehouse !== 'all') {
        params.warehouse_id = nextWarehouse;
      }

      const response = await api.get('/import-receipts', { params });
      setReceipts(response.data.items || []);
      setPagination({
        current: response.data.page || page,
        pageSize: response.data.page_size || pageSize,
        total: response.data.total || 0,
      });
    } catch (error) {
      message.error(error.response?.data?.message || 'Không tải được danh sách phiếu nhập.');
    } finally {
      setLoading(false);
    }
  }, [currentPage, currentPageSize, searchQuery, statusFilter, warehouseFilter]);

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

  const fetchReceiptMovements = useCallback(async (receiptId = selectedReceiptId) => {
    if (!canViewInventory || !receiptId) {
      setReceiptMovements([]);
      return;
    }

    setMovementLoading(true);
    try {
      const response = await api.get('/inventory/movements', {
        params: {
          reference_type: 'import_receipt',
          reference_id: receiptId,
        },
      });
      setReceiptMovements(response.data.items || []);
    } catch (error) {
      message.error(error.response?.data?.message || 'Không tải được lịch sử nhập kho.');
      setReceiptMovements([]);
    } finally {
      setMovementLoading(false);
    }
  }, [canViewInventory, selectedReceiptId]);

  useEffect(() => {
    fetchOptions();
  }, [fetchOptions]);

  useEffect(() => {
    fetchReceipts();
  }, [fetchReceipts]);

  useEffect(() => {
    fetchInventory();
  }, [fetchInventory]);

  useEffect(() => {
    fetchReceiptMovements();
  }, [fetchReceiptMovements]);

  useEffect(() => {
    if (!receipts.length) {
      if (selectedReceiptId !== null) {
        setSelectedReceiptId(null);
      }
      return;
    }

    const hasSelectedReceipt = receipts.some((item) => item.id === selectedReceiptId);
    if (!hasSelectedReceipt) {
      setSelectedReceiptId(receipts[0].id);
    }
  }, [receipts, selectedReceiptId]);

  const selectedReceipt = useMemo(
    () => receipts.find((item) => item.id === selectedReceiptId) || null,
    [receipts, selectedReceiptId],
  );

  const selectedInventoryRows = useMemo(() => {
    if (!selectedReceipt || !canViewInventory) {
      return [];
    }

    const matchedKeys = new Set(
      selectedReceipt.details.map((detail) => `${detail.product_id}-${detail.location_id}`),
    );

    return inventoryRows.filter((row) => (
      row.warehouse_id === selectedReceipt.warehouse_id
      && matchedKeys.has(`${row.product_id}-${row.location_id}`)
    ));
  }, [canViewInventory, inventoryRows, selectedReceipt]);

  const selectedReceiptAlert = useMemo(() => {
    if (!selectedReceipt) {
      return null;
    }

    if (selectedReceipt.status === 'confirmed') {
      return {
        type: 'success',
        title: 'Phiếu đã xác nhận và tồn kho đã được cập nhật.',
        description: `Kho ${selectedReceipt.warehouse_name} đã nhận thêm ${formatNumber(selectedReceipt.total_quantity)} đơn vị hàng từ phiếu này.`,
      };
    }

    if (selectedReceipt.status === 'cancelled') {
      return {
        type: 'info',
        title: 'Phiếu đã hủy, tồn kho không thay đổi.',
        description: 'Phiếu này được giữ lại để đối chiếu lịch sử, nhưng không thể chỉnh sửa hoặc xác nhận thêm.',
      };
    }

    return {
      type: 'warning',
      title: 'Phiếu đang ở trạng thái nháp, tồn kho chưa tăng cho tới khi bạn xác nhận.',
      description: 'Bạn có thể chỉnh sửa nếu nhập sai, hoặc hủy phiếu nếu không muốn ghi nhận vào tồn kho thật.',
    };
  }, [selectedReceipt]);

  const summary = useMemo(() => {
    const draftCount = receipts.filter((item) => item.status === 'draft').length;
    const confirmedCount = receipts.filter((item) => item.status === 'confirmed').length;
    const selectedInventoryQuantity = selectedInventoryRows.reduce(
      (sum, item) => sum + Number(item.quantity || 0),
      0,
    );

    return {
      draftCount,
      confirmedCount,
      selectedInventoryQuantity,
    };
  }, [receipts, selectedInventoryRows]);

  const openCreateDrawer = () => {
    setEditingReceipt(null);
    form.resetFields();
    form.setFieldsValue({
      warehouse_id: undefined,
      supplier_id: undefined,
      note: '',
      items: [{ product_id: undefined, location_id: undefined, quantity: 1 }],
    });
    setDrawerOpen(true);
  };

  const openEditDrawer = (receipt) => {
    setEditingReceipt(receipt);
    form.resetFields();
    form.setFieldsValue({
      warehouse_id: receipt.warehouse_id,
      supplier_id: receipt.supplier_id || undefined,
      note: receipt.note || '',
      items: receipt.details.map((detail) => ({
        product_id: detail.product_id,
        location_id: detail.location_id,
        quantity: detail.quantity,
      })),
    });
    setDrawerOpen(true);
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
    setEditingReceipt(null);
    form.resetFields();
  };

  const handleSubmitDraft = async (values) => {
    const payload = {
      warehouse_id: values.warehouse_id,
      supplier_id: canViewSuppliers ? values.supplier_id || null : editingReceipt?.supplier_id || null,
      note: values.note?.trim() || null,
      items: values.items.map((item) => ({
        product_id: item.product_id,
        location_id: item.location_id,
        quantity: Number(item.quantity || 0),
      })),
    };

    setSubmitting(true);
    try {
      const response = editingReceipt
        ? await api.put(`/import-receipts/${editingReceipt.id}`, payload)
        : await api.post('/import-receipts', payload);
      message.success(editingReceipt ? 'Đã cập nhật phiếu nhập nháp.' : 'Đã tạo phiếu nhập nháp.');
      setSelectedReceiptId(response.data.item?.id || null);
      closeDrawer();
      await fetchReceipts({ page: editingReceipt ? currentPage : 1 });
    } catch (error) {
      message.error(error.response?.data?.message || 'Không lưu được phiếu nhập.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleConfirm = async (receipt) => {
    const nextStatusFilter = statusFilter === 'draft' ? 'all' : statusFilter;

    setConfirmingId(receipt.id);
    try {
      await api.post(`/import-receipts/${receipt.id}/confirm`);
      message.success(`Đã xác nhận phiếu ${receipt.receipt_code} và cập nhật tồn kho.`);
      setSelectedReceiptId(receipt.id);

      if (nextStatusFilter !== statusFilter) {
        setStatusFilter(nextStatusFilter);
        setPagination((current) => ({ ...current, current: 1 }));
      }

      await Promise.all([
        fetchReceipts({
          page: 1,
          status: nextStatusFilter,
          warehouse: warehouseFilter,
          search: searchQuery,
        }),
        fetchInventory(),
        fetchReceiptMovements(receipt.id),
      ]);
    } catch (error) {
      message.error(error.response?.data?.message || 'Không xác nhận được phiếu nhập.');
    } finally {
      setConfirmingId(null);
    }
  };

  const handleCancel = async (receipt) => {
    const nextStatusFilter = statusFilter === 'draft' ? 'all' : statusFilter;

    setCancellingId(receipt.id);
    try {
      await api.post(`/import-receipts/${receipt.id}/cancel`);
      message.success(`Đã hủy phiếu ${receipt.receipt_code}. Tồn kho không thay đổi.`);
      setSelectedReceiptId(receipt.id);

      if (nextStatusFilter !== statusFilter) {
        setStatusFilter(nextStatusFilter);
        setPagination((current) => ({ ...current, current: 1 }));
      }

      await Promise.all([
        fetchReceipts({
          page: 1,
          status: nextStatusFilter,
          warehouse: warehouseFilter,
          search: searchQuery,
        }),
        fetchInventory(),
      ]);
      setReceiptMovements([]);
    } catch (error) {
      message.error(error.response?.data?.message || 'Không hủy được phiếu nhập nháp.');
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
      title: 'Số lượng nhập',
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
            Module 6 · Luồng nhập kho tối thiểu
          </Typography.Text>
          <Typography.Title level={2} className="page-title">
            Nhập kho
          </Typography.Title>
          <Typography.Paragraph className="page-subtitle" style={{ marginBottom: 0 }}>
            Tạo phiếu nhập nháp, xác nhận phiếu và theo dõi ngay tác động lên tồn kho thật từ
            dữ liệu demo hiện tại. Đây là bước đầu tiên để hoàn thiện luồng nghiệp vụ kho có thể
            demo được end-to-end.
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
            <Typography.Text type="secondary">Có thể chỉnh nội dung và chờ xác nhận</Typography.Text>
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="page-card" styles={{ body: { padding: 20 } }}>
            <Typography.Text type="secondary">Phiếu đã xác nhận trên trang</Typography.Text>
            <div className="metric-value">{formatNumber(summary.confirmedCount)}</div>
            <Typography.Text type="secondary">Đã ghi tăng tồn kho thật trong hệ thống</Typography.Text>
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="page-card" styles={{ body: { padding: 20 } }}>
            <Typography.Text type="secondary">Tồn kho ở phiếu đang theo dõi</Typography.Text>
            <div className="metric-value">{formatNumber(summary.selectedInventoryQuantity)}</div>
            <Typography.Text type="secondary">Cập nhật lại ngay sau khi xác nhận phiếu</Typography.Text>
          </Card>
        </Col>
      </Row>

      <SectionCard
        title="Danh sách phiếu nhập"
        subtitle="Có thể tìm kiếm, lọc theo trạng thái hoặc kho. Bấm Theo dõi để xem chi tiết tồn kho liên quan."
        extra={canManage ? (
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreateDrawer}>
            Thêm phiếu nhập nháp
          </Button>
        ) : null}
      >
        <div className="section-toolbar resource-toolbar">
          <Space wrap size={12}>
            <Input.Search
              allowClear
              enterButton="Tìm"
              placeholder="Tìm theo mã phiếu, ghi chú, kho hoặc nhà cung cấp"
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
              value={warehouseFilter === 'all' ? undefined : warehouseFilter}
              onChange={(value) => {
                setWarehouseFilter(value || 'all');
                setPagination((current) => ({ ...current, current: 1 }));
              }}
              placeholder="Lọc theo kho"
              options={warehouseOptions}
              style={{ width: 260 }}
            />
            <Button icon={<ReloadOutlined />} onClick={() => {
              fetchReceipts();
              fetchInventory();
            }}
            >
              Làm mới
            </Button>
          </Space>
          <Typography.Text type="secondary">
            Phiếu xác nhận sẽ tăng tồn kho thật và xuất hiện ngay ở khối phản ánh tồn kho phía dưới.
          </Typography.Text>
        </div>

        <Table
          rowKey="id"
          loading={loading}
          dataSource={receipts}
          expandable={{
            expandedRowRender: (record) => (
              <Space orientation="vertical" size={12} style={{ width: '100%' }}>
                {record.note ? (
                  <Alert
                    type="info"
                    showIcon
                    title="Ghi chú phiếu nhập"
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
              dataIndex: 'receipt_code',
              render: (value) => <Typography.Text strong>{value}</Typography.Text>,
            },
            {
              title: 'Kho',
              dataIndex: 'warehouse_name',
              render: (value, record) => `${value} (${record.warehouse_code})`,
            },
            {
              title: 'Nhà cung cấp',
              dataIndex: 'supplier_name',
              render: (value, record) => (
                value ? `${value} (${record.supplier_code})` : 'Không gắn nhà cung cấp'
              ),
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
              width: 420,
              render: (_, record) => (
                <Space wrap>
                  <Button size="small" onClick={() => setSelectedReceiptId(record.id)}>
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
                        title="Hủy phiếu nhập nháp?"
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
            onClick: () => setSelectedReceiptId(record.id),
          })}
          scroll={{ x: 1320 }}
          locale={{
            emptyText: (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="Chưa có phiếu nhập nào phù hợp với bộ lọc hiện tại."
              />
            ),
          }}
        />
      </SectionCard>

      <SectionCard
        title={selectedReceipt ? `Phiếu đang theo dõi: ${selectedReceipt.receipt_code}` : 'Tồn kho phản ánh theo phiếu'}
        subtitle="Khi chọn hoặc xác nhận một phiếu nhập, khu vực này sẽ cho thấy các dòng hàng liên quan và số lượng tồn hiện tại tại đúng kho, đúng vị trí."
      >
        {!selectedReceipt ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="Chọn một phiếu nhập để theo dõi tác động lên tồn kho."
          />
        ) : (
          <Space orientation="vertical" size={16} style={{ width: '100%' }}>
            <Alert
              type={selectedReceiptAlert.type}
              showIcon
              title={selectedReceiptAlert.title}
              description={selectedReceiptAlert.description}
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
                  dataSource={selectedReceipt.details}
                  columns={detailColumns}
                  locale={{
                    emptyText: (
                      <Empty
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        description="Phiếu này chưa có dòng hàng."
                      />
                    ),
                  }}
                />
              </Space>
            </Card>

            {canViewInventory ? (
              <>
                <Card className="page-card" styles={{ body: { padding: 18 } }}>
                  <Space orientation="vertical" size={12} style={{ width: '100%' }}>
                    <Typography.Title level={5} style={{ margin: 0 }}>
                      Tồn kho hiện tại tại các dòng hàng liên quan
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
                      Lịch sử nhập kho đã ghi nhận
                    </Typography.Title>
                    <Typography.Text type="secondary">
                      Khi phiếu được xác nhận, hệ thống sinh movement tăng tồn kho thật để phục vụ kiểm kê và truy vết.
                    </Typography.Text>
                    <Table
                      rowKey="id"
                      size="small"
                      loading={movementLoading}
                      pagination={false}
                      dataSource={receiptMovements}
                      columns={movementColumns}
                      scroll={{ x: 1180 }}
                      locale={{
                        emptyText: (
                          <Empty
                            image={Empty.PRESENTED_IMAGE_SIMPLE}
                            description={selectedReceipt.status === 'confirmed'
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
        size={760}
        title={editingReceipt ? `Chỉnh sửa phiếu ${editingReceipt.receipt_code}` : 'Thêm phiếu nhập nháp'}
      >
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          <Alert
            showIcon
            type={editingReceipt ? 'warning' : 'info'}
            title={editingReceipt ? 'Chỉnh sửa phiếu nháp trước khi xác nhận' : 'Tạo phiếu nhập tối thiểu cho demo'}
            description={editingReceipt
              ? 'Bạn có thể sửa kho, ghi chú và các dòng hàng khi phiếu vẫn ở trạng thái nháp. Sau khi xác nhận, hệ thống sẽ khóa chỉnh sửa để bảo toàn lịch sử tồn kho.'
              : 'Bước này chỉ tạo phiếu nháp. Tồn kho chỉ tăng thật khi bạn quay lại danh sách và bấm xác nhận phiếu.'}
          />

          <Form
            form={form}
            layout="vertical"
            onFinish={handleSubmitDraft}
            onValuesChange={(changedValues, allValues) => {
              if (!Object.prototype.hasOwnProperty.call(changedValues, 'warehouse_id')) {
                return;
              }

              if (!Array.isArray(allValues.items)) {
                return;
              }

              form.setFieldsValue({
                items: allValues.items.map((item) => ({
                  ...item,
                  location_id: undefined,
                })),
              });
            }}
          >
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item
                  label="Kho nhập"
                  name="warehouse_id"
                  rules={[{ required: true, message: 'Vui lòng chọn kho nhập.' }]}
                >
                  <Select
                    showSearch
                    optionFilterProp="label"
                    placeholder="Chọn kho nhận hàng"
                    options={warehouseOptions}
                  />
                </Form.Item>
              </Col>
              {canViewSuppliers ? (
                <Col xs={24} md={12}>
                  <Form.Item label="Nhà cung cấp" name="supplier_id">
                    <Select
                      allowClear
                      showSearch
                      optionFilterProp="label"
                      placeholder="Có thể để trống trong demo tối thiểu"
                      options={supplierOptions}
                    />
                  </Form.Item>
                </Col>
              ) : null}
              <Col span={24}>
                <Form.Item label="Ghi chú" name="note">
                  <Input.TextArea
                    rows={3}
                    allowClear
                    placeholder="Ví dụ: Nhập bổ sung hàng cho khu vực nhận nhanh"
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
                      throw new Error('Phiếu nhập phải có ít nhất một dòng hàng.');
                    }
                  },
                },
              ]}
            >
              {(fields, { add, remove }, { errors }) => (
                <Space orientation="vertical" size={12} style={{ width: '100%' }}>
                  <Space align="center" style={{ justifyContent: 'space-between', width: '100%' }}>
                    <Typography.Title level={5} style={{ margin: 0 }}>
                      Dòng hàng nhập kho
                    </Typography.Title>
                    <Button
                      icon={<PlusOutlined />}
                      onClick={() => add({ product_id: undefined, location_id: undefined, quantity: 1 })}
                    >
                      Thêm dòng hàng
                    </Button>
                  </Space>

                  {fields.map((field, index) => (
                    <Card key={field.key} className="page-card" styles={{ body: { padding: 18 } }}>
                      <Row gutter={16} align="middle">
                        <Col xs={24} md={8}>
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
                        <Col xs={24} md={8}>
                          <Form.Item
                            {...field}
                            label="Vị trí kho"
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
                        <Col xs={24} md={6}>
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
                {editingReceipt ? 'Lưu phiếu nháp' : 'Tạo phiếu nháp'}
              </Button>
            </div>
          </Form>
        </Space>
      </Drawer>
    </Space>
  );
}

export default ImportReceiptsPage;
