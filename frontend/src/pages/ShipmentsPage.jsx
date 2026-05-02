import {
  CheckCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  RocketOutlined,
  StopOutlined,
} from '@ant-design/icons';
import {
  Alert,
  Button,
  Descriptions,
  Drawer,
  Empty,
  Form,
  Input,
  Row,
  Col,
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
  { label: 'Đã giao shipper', value: 'assigned' },
  { label: 'Đang giao', value: 'in_transit' },
  { label: 'Đã giao xong', value: 'delivered' },
  { label: 'Đã hủy', value: 'cancelled' },
];

function buildStatusActions(shipment, roleName, canManage) {
  if (!shipment || !canManage) {
    return [];
  }

  if (roleName === 'shipper') {
    if (shipment.status === 'assigned') {
      return [{ value: 'in_transit', label: 'Bắt đầu giao', icon: <RocketOutlined /> }];
    }
    if (shipment.status === 'in_transit') {
      return [{ value: 'delivered', label: 'Xác nhận đã giao', icon: <CheckCircleOutlined /> }];
    }
    return [];
  }

  if (shipment.status === 'assigned') {
    return [
      { value: 'in_transit', label: 'Chuyển sang đang giao', icon: <RocketOutlined /> },
      { value: 'delivered', label: 'Đánh dấu đã giao', icon: <CheckCircleOutlined /> },
      { value: 'cancelled', label: 'Hủy shipment', icon: <StopOutlined />, danger: true },
    ];
  }

  if (shipment.status === 'in_transit') {
    return [
      { value: 'delivered', label: 'Đánh dấu đã giao', icon: <CheckCircleOutlined /> },
      { value: 'cancelled', label: 'Hủy shipment', icon: <StopOutlined />, danger: true },
    ];
  }

  return [];
}

function buildShipmentAlert(shipment) {
  if (!shipment) {
    return null;
  }

  if (shipment.status === 'assigned') {
    return {
      type: 'info',
      message: 'Shipment đang chờ shipper nhận giao.',
      description: `Phiếu ${shipment.shipment_code} đã được tạo từ ${shipment.export_receipt_code}. Tồn kho đã trừ từ bước xác nhận phiếu xuất.`,
    };
  }

  if (shipment.status === 'in_transit') {
    return {
      type: 'warning',
      message: 'Shipment đang trên đường giao.',
      description: `Shipper ${shipment.shipper_name || '-'} đang xử lý đơn ${shipment.shipment_code}.`,
    };
  }

  if (shipment.status === 'delivered') {
    return {
      type: 'success',
      message: 'Shipment đã hoàn tất giao hàng.',
      description: `Đơn ${shipment.shipment_code} đã được đánh dấu giao xong cho khách hàng ${shipment.customer_name || 'không xác định'}.`,
    };
  }

  return {
    type: 'error',
    message: 'Shipment đã bị hủy.',
    description: `Đơn ${shipment.shipment_code} không tiếp tục luồng giao hàng.`,
  };
}

function ShipmentsPage() {
  const { hasPermission, user } = useAuth();
  const canManage = hasPermission('shipments.manage');
  const roleName = user?.role || null;
  const canCreate = canManage && roleName !== 'shipper';

  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [statusUpdatingId, setStatusUpdatingId] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [shipments, setShipments] = useState([]);
  const [metaOptions, setMetaOptions] = useState({
    shippers: [],
    exportReceipts: [],
  });
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [warehouseFilter, setWarehouseFilter] = useState('all');
  const [selectedShipmentId, setSelectedShipmentId] = useState(null);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
  });

  const currentPage = pagination.current;
  const currentPageSize = pagination.pageSize;

  const warehouseOptions = useMemo(() => {
    const uniqueWarehouses = new Map();
    shipments.forEach((item) => {
      if (!uniqueWarehouses.has(item.warehouse_id)) {
        uniqueWarehouses.set(item.warehouse_id, {
          value: item.warehouse_id,
          label: `${item.warehouse_name} (${item.warehouse_code})`,
        });
      }
    });
    return Array.from(uniqueWarehouses.values());
  }, [shipments]);

  const shipperOptions = useMemo(
    () => metaOptions.shippers.map((item) => ({
      value: item.id,
      label: `${item.full_name} (${item.username})`,
    })),
    [metaOptions.shippers],
  );

  const exportReceiptOptions = useMemo(
    () => metaOptions.exportReceipts.map((item) => ({
      value: item.id,
      label: `${item.receipt_code} - ${item.warehouse_name} - ${item.customer_name || 'Khách lẻ'}`,
    })),
    [metaOptions.exportReceipts],
  );

  const fetchShipments = useCallback(async (overrides = {}) => {
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

      const response = await api.get('/shipments', { params });
      setShipments(response.data.items || []);
      setPagination({
        current: response.data.page || page,
        pageSize: response.data.page_size || pageSize,
        total: response.data.total || 0,
      });
    } catch (error) {
      message.error(error.response?.data?.message || 'Không tải được danh sách vận chuyển.');
    } finally {
      setLoading(false);
    }
  }, [currentPage, currentPageSize, searchQuery, statusFilter, warehouseFilter]);

  const fetchMeta = useCallback(async () => {
    if (!canCreate) {
      setMetaOptions({ shippers: [], exportReceipts: [] });
      return;
    }

    try {
      const response = await api.get('/shipments/meta');
      setMetaOptions({
        shippers: response.data.shippers || [],
        exportReceipts: response.data.export_receipts || [],
      });
    } catch (error) {
      message.error(error.response?.data?.message || 'Không tải được dữ liệu tạo shipment.');
    }
  }, [canCreate]);

  useEffect(() => {
    fetchShipments();
  }, [fetchShipments]);

  useEffect(() => {
    fetchMeta();
  }, [fetchMeta]);

  useEffect(() => {
    if (!shipments.length) {
      if (selectedShipmentId !== null) {
        setSelectedShipmentId(null);
      }
      return;
    }

    const hasSelectedShipment = shipments.some((item) => item.id === selectedShipmentId);
    if (!hasSelectedShipment) {
      setSelectedShipmentId(shipments[0].id);
    }
  }, [selectedShipmentId, shipments]);

  const selectedShipment = useMemo(
    () => shipments.find((item) => item.id === selectedShipmentId) || null,
    [selectedShipmentId, shipments],
  );

  const shipmentAlert = useMemo(
    () => buildShipmentAlert(selectedShipment),
    [selectedShipment],
  );

  const statusActions = useMemo(
    () => buildStatusActions(selectedShipment, roleName, canManage),
    [canManage, roleName, selectedShipment],
  );

  const handleTableChange = (nextPagination) => {
    fetchShipments({
      page: nextPagination.current,
      pageSize: nextPagination.pageSize,
    });
  };

  const handleApplyFilters = () => {
    setSearchQuery(searchInput.trim());
    fetchShipments({
      page: 1,
      search: searchInput.trim(),
      status: statusFilter,
      warehouse: warehouseFilter,
    });
  };

  const handleResetFilters = () => {
    setSearchInput('');
    setSearchQuery('');
    setStatusFilter('all');
    setWarehouseFilter('all');
    fetchShipments({
      page: 1,
      search: '',
      status: 'all',
      warehouse: 'all',
    });
  };

  const openCreateDrawer = () => {
    form.resetFields();
    setDrawerOpen(true);
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
    form.resetFields();
  };

  const handleCreateShipment = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      await api.post('/shipments', values);
      message.success('Đã tạo shipment và giao cho shipper.');
      closeDrawer();
      await Promise.all([
        fetchShipments({ page: 1 }),
        fetchMeta(),
      ]);
    } catch (error) {
      if (error?.errorFields) {
        return;
      }
      message.error(error.response?.data?.message || 'Không tạo được shipment.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleStatusUpdate = async (shipmentId, nextStatus) => {
    try {
      setStatusUpdatingId(shipmentId);
      await api.post(`/shipments/${shipmentId}/status`, { status: nextStatus });
      message.success('Đã cập nhật trạng thái shipment.');
      await fetchShipments({ page: currentPage, pageSize: currentPageSize });
    } catch (error) {
      message.error(error.response?.data?.message || 'Không cập nhật được trạng thái shipment.');
    } finally {
      setStatusUpdatingId(null);
    }
  };

  const columns = [
    {
      title: 'Mã shipment',
      dataIndex: 'shipment_code',
      key: 'shipment_code',
      render: (_, record) => (
        <Space orientation="vertical" size={0}>
          <Typography.Text strong>{record.shipment_code}</Typography.Text>
          <Typography.Text type="secondary">{record.export_receipt_code}</Typography.Text>
        </Space>
      ),
    },
    {
      title: 'Kho',
      dataIndex: 'warehouse_name',
      key: 'warehouse_name',
      render: (_, record) => (
        <Space orientation="vertical" size={0}>
          <Typography.Text>{record.warehouse_name}</Typography.Text>
          <Typography.Text type="secondary">{record.warehouse_code}</Typography.Text>
        </Space>
      ),
    },
    {
      title: 'Khách hàng',
      dataIndex: 'customer_name',
      key: 'customer_name',
      render: (value) => value || 'Khách lẻ',
    },
    {
      title: 'Shipper',
      dataIndex: 'shipper_name',
      key: 'shipper_name',
    },
    {
      title: 'Tổng SL',
      dataIndex: 'total_quantity',
      key: 'total_quantity',
      width: 110,
      render: (value) => formatNumber(value),
    },
    {
      title: 'Trạng thái',
      dataIndex: 'status',
      key: 'status',
      width: 140,
      render: (value) => <StatusTag value={value} />,
    },
    {
      title: 'Cập nhật',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 180,
      render: (value) => formatDateTime(value),
    },
  ];

  const detailColumns = [
    {
      title: 'Sản phẩm',
      dataIndex: 'product_name',
      key: 'product_name',
      render: (_, record) => (
        <Space orientation="vertical" size={0}>
          <Typography.Text>{record.product_name}</Typography.Text>
          <Typography.Text type="secondary">{record.product_code}</Typography.Text>
        </Space>
      ),
    },
    {
      title: 'Vị trí xuất',
      dataIndex: 'location_name',
      key: 'location_name',
      render: (_, record) => (
        <Space orientation="vertical" size={0}>
          <Typography.Text>{record.location_name}</Typography.Text>
          <Typography.Text type="secondary">{record.location_code}</Typography.Text>
        </Space>
      ),
    },
    {
      title: 'Số lượng',
      dataIndex: 'quantity',
      key: 'quantity',
      width: 120,
      render: (value) => formatNumber(value),
    },
  ];

  return (
    <Space orientation="vertical" size={16} style={{ width: '100%' }}>
      <SectionCard
        title="Vận chuyển"
        subtitle="Theo dõi shipment được tạo từ phiếu xuất đã xác nhận và cập nhật tiến độ giao hàng."
        extra={(
          <Space wrap>
            <Button icon={<ReloadOutlined />} onClick={() => fetchShipments({ page: currentPage, pageSize: currentPageSize })}>
              Tải lại
            </Button>
            {canCreate ? (
              <Button type="primary" icon={<PlusOutlined />} onClick={openCreateDrawer}>
                Tạo shipment
              </Button>
            ) : null}
          </Space>
        )}
      >
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          <Row gutter={[12, 12]}>
            <Col xs={24} md={10} xl={9}>
              <Input
                allowClear
                placeholder="Tìm theo mã shipment, phiếu xuất, kho hoặc shipper"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                onPressEnter={handleApplyFilters}
              />
            </Col>
            <Col xs={24} sm={12} md={7} xl={6}>
              <Select
                style={{ width: '100%' }}
                value={statusFilter}
                onChange={setStatusFilter}
                options={STATUS_OPTIONS}
              />
            </Col>
            <Col xs={24} sm={12} md={7} xl={5}>
              <Select
                style={{ width: '100%' }}
                value={warehouseFilter}
                onChange={setWarehouseFilter}
                options={[{ label: 'Tất cả kho', value: 'all' }, ...warehouseOptions]}
              />
            </Col>
            <Col xs={24} xl={4}>
              <Space wrap>
                <Button type="primary" onClick={handleApplyFilters}>
                  Lọc
                </Button>
                <Button onClick={handleResetFilters}>Xóa lọc</Button>
              </Space>
            </Col>
          </Row>

          <Table
            rowKey="id"
            loading={loading}
            columns={columns}
            dataSource={shipments}
            pagination={{
              current: pagination.current,
              pageSize: pagination.pageSize,
              total: pagination.total,
              showSizeChanger: true,
            }}
            locale={{ emptyText: 'Chưa có shipment nào phù hợp bộ lọc hiện tại.' }}
            rowSelection={{
              type: 'radio',
              selectedRowKeys: selectedShipmentId ? [selectedShipmentId] : [],
              onChange: (selectedRowKeys) => setSelectedShipmentId(selectedRowKeys[0] || null),
            }}
            onRow={(record) => ({
              onClick: () => setSelectedShipmentId(record.id),
            })}
            onChange={handleTableChange}
          />
        </Space>
      </SectionCard>

      <SectionCard
        title="Chi tiết shipment"
        subtitle="Xem danh sách sản phẩm đã xuất và cập nhật trạng thái giao hàng theo vai trò."
      >
        {!selectedShipment ? (
          <Empty
            description="Chưa có shipment nào để theo dõi."
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ) : (
          <Space orientation="vertical" size={16} style={{ width: '100%' }}>
            {shipmentAlert ? (
              <Alert
                type={shipmentAlert.type}
                showIcon
                title={shipmentAlert.message}
                description={shipmentAlert.description}
              />
            ) : null}

            <Descriptions bordered size="small" column={{ xs: 1, md: 2, xl: 3 }}>
              <Descriptions.Item label="Mã shipment">{selectedShipment.shipment_code}</Descriptions.Item>
              <Descriptions.Item label="Phiếu xuất">{selectedShipment.export_receipt_code}</Descriptions.Item>
              <Descriptions.Item label="Trạng thái">
                <StatusTag value={selectedShipment.status} />
              </Descriptions.Item>
              <Descriptions.Item label="Kho">{selectedShipment.warehouse_name}</Descriptions.Item>
              <Descriptions.Item label="Khách hàng">{selectedShipment.customer_name || 'Khách lẻ'}</Descriptions.Item>
              <Descriptions.Item label="Shipper">{selectedShipment.shipper_name || '-'}</Descriptions.Item>
              <Descriptions.Item label="Tổng số dòng">{formatNumber(selectedShipment.detail_count)}</Descriptions.Item>
              <Descriptions.Item label="Tổng số lượng">{formatNumber(selectedShipment.total_quantity)}</Descriptions.Item>
              <Descriptions.Item label="Ghi chú">{selectedShipment.note || '-'}</Descriptions.Item>
              <Descriptions.Item label="Tạo lúc">{formatDateTime(selectedShipment.created_at)}</Descriptions.Item>
              <Descriptions.Item label="Nhận giao lúc">{formatDateTime(selectedShipment.assigned_at)}</Descriptions.Item>
              <Descriptions.Item label="Đang giao lúc">{formatDateTime(selectedShipment.in_transit_at)}</Descriptions.Item>
              <Descriptions.Item label="Giao xong lúc">{formatDateTime(selectedShipment.delivered_at)}</Descriptions.Item>
              <Descriptions.Item label="Hủy lúc">{formatDateTime(selectedShipment.cancelled_at)}</Descriptions.Item>
              <Descriptions.Item label="Người tạo">{selectedShipment.created_by_name || '-'}</Descriptions.Item>
            </Descriptions>

            {statusActions.length ? (
              <Space wrap>
                {statusActions.map((action) => (
                  <Button
                    key={action.value}
                    type={action.danger ? 'default' : 'primary'}
                    danger={action.danger}
                    icon={action.icon}
                    loading={statusUpdatingId === selectedShipment.id}
                    onClick={() => handleStatusUpdate(selectedShipment.id, action.value)}
                  >
                    {action.label}
                  </Button>
                ))}
              </Space>
            ) : null}

            <Table
              rowKey="id"
              columns={detailColumns}
              dataSource={selectedShipment.details || []}
              pagination={false}
              locale={{ emptyText: 'Shipment này chưa có dòng sản phẩm nào.' }}
            />
          </Space>
        )}
      </SectionCard>

      <Drawer
        title="Tạo shipment từ phiếu xuất đã xác nhận"
        placement="right"
        size={520}
        onClose={closeDrawer}
        open={drawerOpen}
        destroyOnHidden
        extra={(
          <Space>
            <Button onClick={closeDrawer}>Đóng</Button>
            <Button
              type="primary"
              loading={submitting}
              onClick={handleCreateShipment}
              disabled={!metaOptions.exportReceipts.length || !metaOptions.shippers.length}
            >
              Tạo shipment
            </Button>
          </Space>
        )}
      >
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          {!metaOptions.exportReceipts.length ? (
            <Alert
              type="info"
              showIcon
              title="Chưa có phiếu xuất đủ điều kiện tạo shipment."
              description="Hãy xác nhận thêm phiếu xuất kho trước khi tạo đơn giao hàng mới."
            />
          ) : null}

          <Form form={form} layout="vertical">
            <Form.Item
              name="export_receipt_id"
              label="Phiếu xuất đã xác nhận"
              rules={[{ required: true, message: 'Vui lòng chọn phiếu xuất.' }]}
            >
              <Select
                showSearch
                optionFilterProp="label"
                placeholder="Chọn phiếu xuất để tạo shipment"
                options={exportReceiptOptions}
              />
            </Form.Item>

            <Form.Item
              name="shipper_id"
              label="Shipper phụ trách"
              rules={[{ required: true, message: 'Vui lòng chọn shipper.' }]}
            >
              <Select
                showSearch
                optionFilterProp="label"
                placeholder="Chọn shipper nhận đơn"
                options={shipperOptions}
              />
            </Form.Item>

            <Form.Item name="note" label="Ghi chú giao hàng">
              <Input.TextArea
                rows={4}
                placeholder="Ví dụ: giao ca chiều, ưu tiên khách hẹn trước 17h..."
              />
            </Form.Item>
          </Form>
        </Space>
      </Drawer>
    </Space>
  );
}

export default ShipmentsPage;
