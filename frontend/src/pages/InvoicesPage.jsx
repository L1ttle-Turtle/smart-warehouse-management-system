import {
  DollarOutlined,
  FileTextOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import {
  Alert,
  Button,
  Col,
  Descriptions,
  Divider,
  Drawer,
  Empty,
  Form,
  Input,
  InputNumber,
  Row,
  Select,
  Space,
  Table,
  Typography,
  message,
} from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import api from '../api/client';
import SectionCard from '../components/SectionCard';
import StatusTag from '../components/StatusTag';
import { formatCurrency, formatDateTime, formatNumber } from '../utils/format';
import { useAuth } from '../auth/useAuth';

const STATUS_OPTIONS = [
  { label: 'Tất cả trạng thái', value: 'all' },
  { label: 'Chưa thanh toán', value: 'unpaid' },
  { label: 'Thanh toán một phần', value: 'partial' },
  { label: 'Đã thanh toán', value: 'paid' },
];

function buildInvoiceAlert(invoice) {
  if (!invoice) {
    return null;
  }

  if (invoice.status === 'unpaid') {
    return {
      type: 'warning',
      message: 'Hóa đơn đang chờ ghi nhận thanh toán.',
      description: `Hóa đơn ${invoice.invoice_code} đã được phát hành từ phiếu xuất ${invoice.export_receipt_code}.`,
    };
  }

  if (invoice.status === 'partial') {
    return {
      type: 'info',
      message: 'Hóa đơn đã được thanh toán một phần.',
      description: `Cần hoàn thiện bước ghi nhận công nợ cho ${invoice.invoice_code} ở các lượt sau.`,
    };
  }

  return {
    type: 'success',
    message: 'Hóa đơn đã thanh toán xong.',
    description: `Trạng thái doanh thu của ${invoice.invoice_code} đã hoàn tất.`,
  };
}

function getInvoicePaidAmount(invoice) {
  if (!invoice) {
    return 0;
  }

  if (invoice.paid_amount !== undefined && invoice.paid_amount !== null) {
    return Number(invoice.paid_amount || 0);
  }

  return (invoice.payments || []).reduce((sum, payment) => sum + Number(payment.amount || 0), 0);
}

function getInvoiceRemainingAmount(invoice) {
  if (!invoice) {
    return 0;
  }

  if (invoice.remaining_amount !== undefined && invoice.remaining_amount !== null) {
    return Number(invoice.remaining_amount || 0);
  }

  return Math.max(Number(invoice.total_amount || 0) - getInvoicePaidAmount(invoice), 0);
}

function InvoicesPage() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission('invoices.manage');

  const [form] = Form.useForm();
  const [paymentForm] = Form.useForm();
  const selectedReceiptId = Form.useWatch('export_receipt_id', form);

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [paymentSubmitting, setPaymentSubmitting] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [invoices, setInvoices] = useState([]);
  const [metaOptions, setMetaOptions] = useState({
    bankAccounts: [],
    exportReceipts: [],
  });
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedInvoiceId, setSelectedInvoiceId] = useState(null);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
  });

  const currentPage = pagination.current;
  const currentPageSize = pagination.pageSize;

  const selectedReceipt = useMemo(
    () => metaOptions.exportReceipts.find((item) => item.id === selectedReceiptId) || null,
    [metaOptions.exportReceipts, selectedReceiptId],
  );

  const invoiceAlert = useMemo(
    () => buildInvoiceAlert(invoices.find((item) => item.id === selectedInvoiceId) || null),
    [invoices, selectedInvoiceId],
  );

  const selectedInvoice = useMemo(
    () => invoices.find((item) => item.id === selectedInvoiceId) || null,
    [invoices, selectedInvoiceId],
  );

  const selectedInvoicePaidAmount = useMemo(
    () => getInvoicePaidAmount(selectedInvoice),
    [selectedInvoice],
  );

  const selectedInvoiceRemainingAmount = useMemo(
    () => getInvoiceRemainingAmount(selectedInvoice),
    [selectedInvoice],
  );

  const bankAccountOptions = useMemo(
    () => metaOptions.bankAccounts.map((item) => ({
      value: item.id,
      label: `${item.bank_name} - ${item.account_number}`,
    })),
    [metaOptions.bankAccounts],
  );

  const exportReceiptOptions = useMemo(
    () => metaOptions.exportReceipts.map((item) => ({
      value: item.id,
      label: `${item.receipt_code} - ${item.customer_name} - ${item.warehouse_name}`,
    })),
    [metaOptions.exportReceipts],
  );

  const fetchInvoices = useCallback(async (overrides = {}) => {
    setLoading(true);
    try {
      const page = overrides.page ?? currentPage;
      const pageSize = overrides.pageSize ?? currentPageSize;
      const nextSearch = overrides.search ?? searchQuery;
      const nextStatus = overrides.status ?? statusFilter;
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

      const response = await api.get('/invoices', { params });
      setInvoices(response.data.items || []);
      setPagination({
        current: response.data.page || page,
        pageSize: response.data.page_size || pageSize,
        total: response.data.total || 0,
      });
    } catch (error) {
      message.error(error.response?.data?.message || 'Không tải được danh sách hóa đơn.');
    } finally {
      setLoading(false);
    }
  }, [currentPage, currentPageSize, searchQuery, statusFilter]);

  const fetchMeta = useCallback(async () => {
    if (!canManage) {
      setMetaOptions({ bankAccounts: [], exportReceipts: [] });
      return;
    }

    try {
      const response = await api.get('/invoices/meta');
      setMetaOptions({
        bankAccounts: response.data.bank_accounts || [],
        exportReceipts: response.data.export_receipts || [],
      });
    } catch (error) {
      message.error(error.response?.data?.message || 'Không tải được dữ liệu tạo hóa đơn.');
    }
  }, [canManage]);

  useEffect(() => {
    fetchInvoices();
  }, [fetchInvoices]);

  useEffect(() => {
    fetchMeta();
  }, [fetchMeta]);

  useEffect(() => {
    if (!invoices.length) {
      if (selectedInvoiceId !== null) {
        setSelectedInvoiceId(null);
      }
      return;
    }

    const hasSelectedInvoice = invoices.some((item) => item.id === selectedInvoiceId);
    if (!hasSelectedInvoice) {
      setSelectedInvoiceId(invoices[0].id);
    }
  }, [invoices, selectedInvoiceId]);

  useEffect(() => {
    if (!selectedReceipt) {
      return;
    }

    const currentItems = form.getFieldValue('items') || [];
    const nextItems = selectedReceipt.details.map((detail) => {
      const existing = currentItems.find((item) => item.export_receipt_detail_id === detail.id);
      return {
        export_receipt_detail_id: detail.id,
        unit_price: existing?.unit_price ?? undefined,
      };
    });
    form.setFieldValue('items', nextItems);
  }, [form, selectedReceipt]);

  useEffect(() => {
    paymentForm.resetFields();
    if (selectedInvoice && selectedInvoice.status !== 'paid') {
      paymentForm.setFieldsValue({
        amount: selectedInvoiceRemainingAmount,
        payment_method: 'cash',
        bank_account_id: selectedInvoice.bank_account_id || undefined,
      });
    }
  }, [paymentForm, selectedInvoice, selectedInvoiceRemainingAmount]);

  const handleTableChange = (nextPagination) => {
    fetchInvoices({
      page: nextPagination.current,
      pageSize: nextPagination.pageSize,
    });
  };

  const handleApplyFilters = () => {
    const nextSearch = searchInput.trim();
    setSearchQuery(nextSearch);
    fetchInvoices({
      page: 1,
      search: nextSearch,
      status: statusFilter,
    });
  };

  const handleResetFilters = () => {
    setSearchInput('');
    setSearchQuery('');
    setStatusFilter('all');
    fetchInvoices({
      page: 1,
      search: '',
      status: 'all',
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

  const handleCreateInvoice = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      await api.post('/invoices', values);
      message.success('Đã tạo hóa đơn từ phiếu xuất đã xác nhận.');
      closeDrawer();
      await Promise.all([
        fetchInvoices({ page: 1 }),
        fetchMeta(),
      ]);
    } catch (error) {
      if (error?.errorFields) {
        return;
      }
      message.error(error.response?.data?.message || 'Không tạo được hóa đơn.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSetFullRemainingAmount = () => {
    paymentForm.setFieldsValue({ amount: selectedInvoiceRemainingAmount });
  };

  const handleRecordPayment = async () => {
    if (!selectedInvoice) {
      return;
    }

    try {
      const values = await paymentForm.validateFields();
      setPaymentSubmitting(true);
      await api.post('/payments', {
        ...values,
        invoice_id: selectedInvoice.id,
      });
      message.success('Đã ghi nhận thanh toán và cập nhật trạng thái hóa đơn.');
      paymentForm.resetFields();
      await fetchInvoices({ page: currentPage, pageSize: currentPageSize });
    } catch (error) {
      if (error?.errorFields) {
        return;
      }
      message.error(error.response?.data?.message || 'Không ghi nhận được thanh toán.');
    } finally {
      setPaymentSubmitting(false);
    }
  };

  const linePreviewRows = useMemo(() => {
    if (!selectedReceipt) {
      return [];
    }

    const currentItems = form.getFieldValue('items') || [];
    return selectedReceipt.details.map((detail) => {
      const pricing = currentItems.find((item) => item.export_receipt_detail_id === detail.id);
      const unitPrice = Number(pricing?.unit_price || 0);
      return {
        ...detail,
        unit_price: unitPrice,
        line_total: unitPrice * Number(detail.quantity || 0),
      };
    });
  }, [form, selectedReceipt]);

  const linePreviewTotal = useMemo(
    () => linePreviewRows.reduce((sum, item) => sum + Number(item.line_total || 0), 0),
    [linePreviewRows],
  );

  const columns = [
    {
      title: 'Mã hóa đơn',
      dataIndex: 'invoice_code',
      key: 'invoice_code',
      render: (_, record) => (
        <Space orientation="vertical" size={0}>
          <Typography.Text strong>{record.invoice_code}</Typography.Text>
          <Typography.Text type="secondary">{record.export_receipt_code}</Typography.Text>
        </Space>
      ),
    },
    {
      title: 'Khách hàng',
      dataIndex: 'customer_name',
      key: 'customer_name',
      render: (_, record) => (
        <Space orientation="vertical" size={0}>
          <Typography.Text>{record.customer_name}</Typography.Text>
          <Typography.Text type="secondary">{record.customer_code}</Typography.Text>
        </Space>
      ),
    },
    {
      title: 'Tổng SL',
      dataIndex: 'total_quantity',
      key: 'total_quantity',
      width: 100,
      render: (value) => formatNumber(value),
    },
    {
      title: 'Tổng tiền',
      dataIndex: 'total_amount',
      key: 'total_amount',
      width: 150,
      render: (value) => formatCurrency(value),
    },
    {
      title: 'Đã thu',
      dataIndex: 'paid_amount',
      key: 'paid_amount',
      width: 140,
      render: (value) => formatCurrency(value),
    },
    {
      title: 'Còn phải thu',
      dataIndex: 'remaining_amount',
      key: 'remaining_amount',
      width: 150,
      render: (value, record) => formatCurrency(value ?? getInvoiceRemainingAmount(record)),
    },
    {
      title: 'Trạng thái',
      dataIndex: 'status',
      key: 'status',
      width: 130,
      render: (value) => <StatusTag value={value} />,
    },
    {
      title: 'Phát hành',
      dataIndex: 'issued_at',
      key: 'issued_at',
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
      width: 100,
      render: (value) => formatNumber(value),
    },
    {
      title: 'Đơn giá',
      dataIndex: 'unit_price',
      key: 'unit_price',
      width: 150,
      render: (value) => formatCurrency(value),
    },
    {
      title: 'Thành tiền',
      dataIndex: 'line_total',
      key: 'line_total',
      width: 150,
      render: (value) => formatCurrency(value),
    },
  ];

  const paymentColumns = [
    {
      title: 'Mã thanh toán',
      dataIndex: 'payment_code',
      key: 'payment_code',
      render: (_, record) => (
        <Space orientation="vertical" size={0}>
          <Typography.Text strong>{record.payment_code}</Typography.Text>
          <Typography.Text type="secondary">{formatDateTime(record.paid_at)}</Typography.Text>
        </Space>
      ),
    },
    {
      title: 'Phương thức',
      dataIndex: 'payment_method',
      key: 'payment_method',
      width: 140,
      render: (value) => {
        const labels = {
          cash: 'Tiền mặt',
          bank_transfer: 'Chuyển khoản',
          other: 'Khác',
        };
        return labels[value] || value || '-';
      },
    },
    {
      title: 'Tài khoản nhận',
      dataIndex: 'bank_account_number',
      key: 'bank_account_number',
      render: (_, record) => (
        record.bank_name
          ? `${record.bank_name} - ${record.bank_account_number}`
          : 'Không gắn tài khoản'
      ),
    },
    {
      title: 'Số tiền',
      dataIndex: 'amount',
      key: 'amount',
      width: 150,
      render: (value) => formatCurrency(value),
    },
    {
      title: 'Ghi chú',
      dataIndex: 'note',
      key: 'note',
      render: (value) => value || '-',
    },
  ];

  return (
    <Space orientation="vertical" size={16} style={{ width: '100%' }}>
      <SectionCard
        title="Hóa đơn"
        subtitle="Lập hóa đơn từ phiếu xuất đã xác nhận để chốt doanh thu demo ở mức tối thiểu."
        extra={(
          <Space wrap>
            <Button icon={<ReloadOutlined />} onClick={() => fetchInvoices({ page: currentPage, pageSize: currentPageSize })}>
              Tải lại
            </Button>
            {canManage ? (
              <Button type="primary" icon={<PlusOutlined />} onClick={openCreateDrawer}>
                Tạo hóa đơn
              </Button>
            ) : null}
          </Space>
        )}
      >
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          <Row gutter={[12, 12]}>
            <Col xs={24} md={12} xl={10}>
              <Input
                allowClear
                placeholder="Tìm theo mã hóa đơn, phiếu xuất, khách hàng hoặc kho"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                onPressEnter={handleApplyFilters}
              />
            </Col>
            <Col xs={24} sm={12} md={8} xl={6}>
              <Select
                style={{ width: '100%' }}
                value={statusFilter}
                onChange={setStatusFilter}
                options={STATUS_OPTIONS}
              />
            </Col>
            <Col xs={24} sm={12} md={4} xl={8}>
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
            dataSource={invoices}
            pagination={{
              current: pagination.current,
              pageSize: pagination.pageSize,
              total: pagination.total,
              showSizeChanger: true,
            }}
            locale={{ emptyText: 'Chưa có hóa đơn nào phù hợp bộ lọc hiện tại.' }}
            rowSelection={{
              type: 'radio',
              selectedRowKeys: selectedInvoiceId ? [selectedInvoiceId] : [],
              onChange: (selectedRowKeys) => setSelectedInvoiceId(selectedRowKeys[0] || null),
            }}
            onRow={(record) => ({
              onClick: () => setSelectedInvoiceId(record.id),
            })}
            onChange={handleTableChange}
          />
        </Space>
      </SectionCard>

      <SectionCard
        title="Chi tiết hóa đơn"
        subtitle="Xem snapshot số lượng và đơn giá đã chốt tại thời điểm lập hóa đơn."
      >
        {!selectedInvoice ? (
          <Empty
            description="Chưa có hóa đơn nào để theo dõi."
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ) : (
          <Space orientation="vertical" size={16} style={{ width: '100%' }}>
            {invoiceAlert ? (
              <Alert
                type={invoiceAlert.type}
                showIcon
                title={invoiceAlert.message}
                description={invoiceAlert.description}
              />
            ) : null}

            <Descriptions bordered size="small" column={{ xs: 1, md: 2, xl: 3 }}>
              <Descriptions.Item label="Mã hóa đơn">{selectedInvoice.invoice_code}</Descriptions.Item>
              <Descriptions.Item label="Phiếu xuất">{selectedInvoice.export_receipt_code}</Descriptions.Item>
              <Descriptions.Item label="Trạng thái">
                <StatusTag value={selectedInvoice.status} />
              </Descriptions.Item>
              <Descriptions.Item label="Khách hàng">{selectedInvoice.customer_name}</Descriptions.Item>
              <Descriptions.Item label="Kho">{selectedInvoice.warehouse_name}</Descriptions.Item>
              <Descriptions.Item label="Tài khoản nhận">
                {selectedInvoice.bank_name
                  ? `${selectedInvoice.bank_name} - ${selectedInvoice.bank_account_number}`
                  : 'Chưa chọn'}
              </Descriptions.Item>
              <Descriptions.Item label="Tổng số dòng">{formatNumber(selectedInvoice.detail_count)}</Descriptions.Item>
              <Descriptions.Item label="Tổng số lượng">{formatNumber(selectedInvoice.total_quantity)}</Descriptions.Item>
              <Descriptions.Item label="Tổng tiền">{formatCurrency(selectedInvoice.total_amount)}</Descriptions.Item>
              <Descriptions.Item label="Đã thu">{formatCurrency(selectedInvoicePaidAmount)}</Descriptions.Item>
              <Descriptions.Item label="Còn phải thu">{formatCurrency(selectedInvoiceRemainingAmount)}</Descriptions.Item>
              <Descriptions.Item label="Phát hành lúc">{formatDateTime(selectedInvoice.issued_at)}</Descriptions.Item>
              <Descriptions.Item label="Người tạo">{selectedInvoice.created_by_name || '-'}</Descriptions.Item>
              <Descriptions.Item label="Ghi chú">{selectedInvoice.note || '-'}</Descriptions.Item>
            </Descriptions>

            {canManage ? (
              <SectionCard
                title="Ghi nhận thanh toán"
                subtitle="Nhập số tiền đã thu để chuyển trạng thái hóa đơn sang thanh toán một phần hoặc đã thanh toán."
              >
                {selectedInvoice.status === 'paid' ? (
                  <Alert
                    type="success"
                    showIcon
                    title="Hóa đơn đã thanh toán đủ."
                    description="Không cần ghi nhận thêm payment cho hóa đơn này."
                  />
                ) : (
                  <Form form={paymentForm} layout="vertical">
                    <Row gutter={[12, 12]} align="bottom">
                      <Col xs={24} md={8}>
                        <Form.Item
                          name="amount"
                          label="Số tiền thanh toán"
                          rules={[
                            { required: true, message: 'Vui lòng nhập số tiền thanh toán.' },
                            {
                              validator: (_, value) => {
                                const amount = Number(value || 0);
                                if (amount <= 0) {
                                  return Promise.reject(new Error('Số tiền phải lớn hơn 0.'));
                                }
                                if (amount > selectedInvoiceRemainingAmount) {
                                  return Promise.reject(
                                    new Error('Số tiền không được vượt quá số còn phải thu.'),
                                  );
                                }
                                return Promise.resolve();
                              },
                            },
                          ]}
                        >
                          <InputNumber
                            min={1}
                            max={selectedInvoiceRemainingAmount}
                            style={{ width: '100%' }}
                            placeholder="Nhập số tiền đã thu"
                            formatter={(value) => (value ? formatNumber(value) : '')}
                            parser={(value) => Number(String(value || '').replace(/[^\d.-]/g, ''))}
                          />
                        </Form.Item>
                      </Col>
                      <Col xs={24} md={6}>
                        <Form.Item
                          name="payment_method"
                          label="Phương thức"
                          rules={[{ required: true, message: 'Vui lòng chọn phương thức.' }]}
                        >
                          <Select
                            options={[
                              { label: 'Tiền mặt', value: 'cash' },
                              { label: 'Chuyển khoản', value: 'bank_transfer' },
                              { label: 'Khác', value: 'other' },
                            ]}
                          />
                        </Form.Item>
                      </Col>
                      <Col xs={24} md={6}>
                        <Form.Item name="bank_account_id" label="Tài khoản nhận">
                          <Select
                            allowClear
                            showSearch
                            optionFilterProp="label"
                            placeholder="Chọn nếu có"
                            options={bankAccountOptions}
                          />
                        </Form.Item>
                      </Col>
                      <Col xs={24} md={4}>
                        <Space wrap>
                          <Button onClick={handleSetFullRemainingAmount}>
                            Thu đủ
                          </Button>
                          <Button
                            type="primary"
                            icon={<DollarOutlined />}
                            loading={paymentSubmitting}
                            onClick={handleRecordPayment}
                          >
                            Ghi nhận
                          </Button>
                        </Space>
                      </Col>
                      <Col xs={24}>
                        <Form.Item name="note" label="Ghi chú thanh toán">
                          <Input.TextArea
                            rows={2}
                            placeholder="Ví dụ: khách chuyển khoản đợt 1, thu tiền mặt tại quầy..."
                          />
                        </Form.Item>
                      </Col>
                    </Row>
                  </Form>
                )}
              </SectionCard>
            ) : null}

            <Divider titlePlacement="left">Lịch sử thanh toán</Divider>
            <Table
              rowKey="id"
              columns={paymentColumns}
              dataSource={selectedInvoice.payments || []}
              pagination={false}
              locale={{ emptyText: 'Hóa đơn này chưa có payment nào được ghi nhận.' }}
            />

            <Table
              rowKey="id"
              columns={detailColumns}
              dataSource={selectedInvoice.details || []}
              pagination={false}
              locale={{ emptyText: 'Hóa đơn này chưa có dòng chi tiết nào.' }}
            />
          </Space>
        )}
      </SectionCard>

      <Drawer
        title="Tạo hóa đơn từ phiếu xuất đã xác nhận"
        placement="right"
        size={640}
        onClose={closeDrawer}
        open={drawerOpen}
        destroyOnHidden
        extra={(
          <Space>
            <Button onClick={closeDrawer}>Đóng</Button>
            <Button
              type="primary"
              icon={<FileTextOutlined />}
              loading={submitting}
              onClick={handleCreateInvoice}
              disabled={!metaOptions.exportReceipts.length}
            >
              Tạo hóa đơn
            </Button>
          </Space>
        )}
      >
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          {!metaOptions.exportReceipts.length ? (
            <Alert
              type="info"
              showIcon
              title="Chưa có phiếu xuất đủ điều kiện lập hóa đơn."
              description="Cần có phiếu xuất đã xác nhận và đã gắn khách hàng để tạo hóa đơn."
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
                placeholder="Chọn phiếu xuất cần lập hóa đơn"
                options={exportReceiptOptions}
              />
            </Form.Item>

            <Form.Item
              name="bank_account_id"
              label="Tài khoản ngân hàng nhận tiền"
            >
              <Select
                allowClear
                showSearch
                optionFilterProp="label"
                placeholder="Có thể bỏ trống nếu chưa muốn gắn tài khoản nhận"
                options={bankAccountOptions}
              />
            </Form.Item>

            <Form.Item name="note" label="Ghi chú hóa đơn">
              <Input.TextArea
                rows={3}
                placeholder="Ví dụ: hóa đơn phát hành cuối ngày, chờ kế toán xác nhận công nợ..."
              />
            </Form.Item>

            <Typography.Title level={5} style={{ marginBottom: 12 }}>
              Đơn giá theo từng dòng phiếu xuất
            </Typography.Title>

            {!selectedReceipt ? (
              <Empty
                description="Hãy chọn phiếu xuất để nhập đơn giá và xem trước hóa đơn."
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            ) : (
              <Space orientation="vertical" size={12} style={{ width: '100%' }}>
                {selectedReceipt.details.map((detail, index) => (
                  <Row gutter={[12, 12]} key={detail.id}>
                    <Col xs={24} md={10}>
                      <Space orientation="vertical" size={0}>
                        <Typography.Text strong>{detail.product_name}</Typography.Text>
                        <Typography.Text type="secondary">
                          {detail.product_code} · {detail.location_name} · SL {formatNumber(detail.quantity)}
                        </Typography.Text>
                      </Space>
                    </Col>
                    <Col xs={24} md={7}>
                      <Form.Item
                        name={['items', index, 'unit_price']}
                        label="Đơn giá"
                        rules={[{ required: true, message: 'Vui lòng nhập đơn giá.' }]}
                        style={{ marginBottom: 0 }}
                      >
                        <InputNumber
                          min={0}
                          style={{ width: '100%' }}
                          placeholder="Nhập đơn giá"
                          formatter={(value) => (value ? formatNumber(value) : '')}
                          parser={(value) => Number(String(value || '').replace(/[^\d.-]/g, ''))}
                        />
                      </Form.Item>
                      <Form.Item name={['items', index, 'export_receipt_detail_id']} hidden initialValue={detail.id}>
                        <Input />
                      </Form.Item>
                    </Col>
                    <Col xs={24} md={7}>
                      <Typography.Text type="secondary">Thành tiền dự kiến</Typography.Text>
                      <div style={{ paddingTop: 8 }}>
                        <Typography.Text strong>
                          {formatCurrency(
                            Number(linePreviewRows.find((item) => item.id === detail.id)?.line_total || 0),
                          )}
                        </Typography.Text>
                      </div>
                    </Col>
                  </Row>
                ))}

                <Alert
                  type="success"
                  showIcon
                  title="Tổng tiền dự kiến"
                  description={formatCurrency(linePreviewTotal)}
                />
              </Space>
            )}
          </Form>
        </Space>
      </Drawer>
    </Space>
  );
}

export default InvoicesPage;
