import {
  BankOutlined,
  CheckCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import {
  Button,
  Col,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import api from '../api/client';
import SectionCard from '../components/SectionCard';
import { useAuth } from '../auth/useAuth';
import { formatCurrency, formatDateTime } from '../utils/format';

const STATUS_OPTIONS = [
  { label: 'Tất cả trạng thái', value: 'all' },
  { label: 'Chờ kiểm tra', value: 'pending' },
  { label: 'Đã khớp hóa đơn', value: 'matched' },
  { label: 'Đã đối soát', value: 'reconciled' },
  { label: 'Bỏ qua', value: 'ignored' },
];

const STATUS_META = {
  pending: { label: 'Chờ kiểm tra', color: 'gold' },
  matched: { label: 'Đã khớp hóa đơn', color: 'blue' },
  reconciled: { label: 'Đã đối soát', color: 'green' },
  ignored: { label: 'Bỏ qua', color: 'default' },
};

function BankStatusTag({ value }) {
  const meta = STATUS_META[value] || { label: value || '-', color: 'default' };
  return <Tag color={meta.color}>{meta.label}</Tag>;
}

function BankReconciliationPage() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission('invoices.manage');
  const [form] = Form.useForm();

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [transactions, setTransactions] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [bankAccounts, setBankAccounts] = useState([]);
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [invoiceFilter, setInvoiceFilter] = useState('all');
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
  });
  const currentPage = pagination.current;
  const currentPageSize = pagination.pageSize;

  const invoiceOptions = useMemo(
    () => invoices.map((item) => ({
      value: item.id,
      label: `${item.invoice_code} - ${item.customer_name} - ${formatCurrency(item.remaining_amount)}`,
      invoiceCode: item.invoice_code,
    })),
    [invoices],
  );

  const simulateInvoiceOptions = useMemo(
    () => invoices.map((item) => ({
      value: item.invoice_code,
      label: `${item.invoice_code} - ${item.customer_name} - còn ${formatCurrency(item.remaining_amount)}`,
      invoice: item,
    })),
    [invoices],
  );

  const bankAccountOptions = useMemo(
    () => bankAccounts.map((item) => ({
      value: item.id,
      label: `${item.bank_name} - ${item.account_number}`,
    })),
    [bankAccounts],
  );

  const fetchMeta = useCallback(async () => {
    try {
      const invoiceResponse = await api.get('/invoices', {
        params: {
          page: 1,
          page_size: 100,
          sort_by: 'created_at',
          sort_order: 'desc',
        },
      });
      setInvoices(invoiceResponse.data.items || []);

      if (canManage) {
        const metaResponse = await api.get('/invoices/meta');
        setBankAccounts(metaResponse.data.bank_accounts || []);
      } else {
        setBankAccounts([]);
      }
    } catch (error) {
      message.error(error.response?.data?.message || 'Không tải được dữ liệu đối soát.');
    }
  }, [canManage]);

  const fetchTransactions = useCallback(async (overrides = {}) => {
    setLoading(true);
    try {
      const page = overrides.page ?? currentPage;
      const pageSize = overrides.pageSize ?? currentPageSize;
      const nextSearch = overrides.search ?? searchQuery;
      const nextStatus = overrides.status ?? statusFilter;
      const nextInvoice = overrides.invoiceId ?? invoiceFilter;
      const params = {
        page,
        page_size: pageSize,
        sort_by: 'received_at',
        sort_order: 'desc',
      };

      if (nextSearch) {
        params.search = nextSearch;
      }
      if (nextStatus !== 'all') {
        params.status = nextStatus;
      }
      if (nextInvoice !== 'all') {
        params.invoice_id = nextInvoice;
      }

      const response = await api.get('/bank-transactions', { params });
      setTransactions(response.data.items || []);
      setPagination({
        current: response.data.page || page,
        pageSize: response.data.page_size || pageSize,
        total: response.data.total || 0,
      });
    } catch (error) {
      message.error(error.response?.data?.message || 'Không tải được giao dịch ngân hàng.');
    } finally {
      setLoading(false);
    }
  }, [currentPage, currentPageSize, invoiceFilter, searchQuery, statusFilter]);

  useEffect(() => {
    fetchMeta();
  }, [fetchMeta]);

  useEffect(() => {
    fetchTransactions();
  }, [fetchTransactions]);

  const handleApplyFilters = () => {
    const nextSearch = searchInput.trim();
    setSearchQuery(nextSearch);
    fetchTransactions({
      page: 1,
      search: nextSearch,
      status: statusFilter,
      invoiceId: invoiceFilter,
    });
  };

  const handleResetFilters = () => {
    setSearchInput('');
    setSearchQuery('');
    setStatusFilter('all');
    setInvoiceFilter('all');
    fetchTransactions({
      page: 1,
      search: '',
      status: 'all',
      invoiceId: 'all',
    });
  };

  const handleOpenSimulate = () => {
    form.resetFields();
    form.setFieldsValue({
      bank_account_id: bankAccountOptions[0]?.value,
      description: '',
    });
    setModalOpen(true);
  };

  const handleInvoiceCodeChange = (invoiceCode) => {
    const invoice = invoices.find((item) => item.invoice_code === invoiceCode);
    if (!invoice) {
      return;
    }
    form.setFieldsValue({
      amount: Math.max(Number(invoice.remaining_amount || 0), 0),
      description: `Khách chuyển khoản cho ${invoice.invoice_code}`,
    });
  };

  const handleSimulate = async () => {
    const values = await form.validateFields();
    setSubmitting(true);
    try {
      await api.post('/bank-transactions/simulate', values);
      message.success('Đã mô phỏng giao dịch ngân hàng.');
      setModalOpen(false);
      fetchTransactions({ page: 1 });
      fetchMeta();
    } catch (error) {
      message.error(error.response?.data?.message || 'Không thể mô phỏng giao dịch ngân hàng.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleReconcile = async (transaction) => {
    setSubmitting(true);
    try {
      await api.post(`/bank-transactions/${transaction.id}/reconcile`, {
        note: `Đối soát từ giao dịch ${transaction.transaction_code}`,
      });
      message.success('Đã đối soát và ghi nhận thanh toán.');
      fetchTransactions();
      fetchMeta();
    } catch (error) {
      message.error(error.response?.data?.message || 'Không thể đối soát giao dịch này.');
    } finally {
      setSubmitting(false);
    }
  };

  const columns = [
    {
      title: 'Giao dịch',
      dataIndex: 'transaction_code',
      key: 'transaction_code',
      render: (_, record) => (
        <Space orientation="vertical" size={0}>
          <Typography.Text strong>{record.transaction_code}</Typography.Text>
          <Typography.Text type="secondary">{formatDateTime(record.received_at)}</Typography.Text>
        </Space>
      ),
    },
    {
      title: 'Hóa đơn khớp',
      dataIndex: 'invoice_code',
      key: 'invoice_code',
      render: (_, record) => (
        record.invoice_code ? (
          <Space orientation="vertical" size={0}>
            <Typography.Text>{record.invoice_code}</Typography.Text>
            <Typography.Text type="secondary">{record.invoice_status || '-'}</Typography.Text>
          </Space>
        ) : (
          <Typography.Text type="secondary">Chưa khớp hóa đơn</Typography.Text>
        )
      ),
    },
    {
      title: 'Trạng thái',
      dataIndex: 'status',
      key: 'status',
      width: 150,
      render: (value) => <BankStatusTag value={value} />,
    },
    {
      title: 'Số tiền',
      dataIndex: 'amount',
      key: 'amount',
      width: 150,
      render: (value) => formatCurrency(value),
    },
    {
      title: 'Tài khoản nhận',
      dataIndex: 'bank_account_number',
      key: 'bank_account_number',
      render: (_, record) => (
        record.bank_name
          ? `${record.bank_name} - ${record.bank_account_number}`
          : 'Chưa gắn tài khoản'
      ),
    },
    {
      title: 'Nội dung',
      dataIndex: 'description',
      key: 'description',
      render: (_, record) => (
        <Space orientation="vertical" size={0}>
          <Typography.Text>{record.description}</Typography.Text>
          {record.note ? <Typography.Text type="secondary">{record.note}</Typography.Text> : null}
        </Space>
      ),
    },
    {
      title: 'Thao tác',
      key: 'actions',
      width: 150,
      render: (_, record) => {
        const canReconcile = canManage && record.status === 'matched' && record.invoice_id;
        return canReconcile ? (
          <Popconfirm
            title="Đối soát giao dịch này?"
            description="Hệ thống sẽ tạo payment thật và cập nhật trạng thái hóa đơn."
            okText="Đối soát"
            cancelText="Để sau"
            onConfirm={() => handleReconcile(record)}
          >
            <Button size="small" type="primary" icon={<CheckCircleOutlined />} loading={submitting}>
              Đối soát
            </Button>
          </Popconfirm>
        ) : (
          <Typography.Text type="secondary">Không có thao tác</Typography.Text>
        );
      },
    },
  ];

  return (
    <>
      <SectionCard
        title="Đối soát ngân hàng"
        subtitle="Mô phỏng giao dịch chuyển khoản, khớp với hóa đơn và ghi nhận thanh toán để demo Module 12."
        extra={(
          <Space wrap>
            {canManage ? (
              <Button type="primary" icon={<PlusOutlined />} onClick={handleOpenSimulate}>
                Mô phỏng giao dịch
              </Button>
            ) : null}
            <Button icon={<ReloadOutlined />} onClick={() => fetchTransactions()}>
              Tải lại
            </Button>
          </Space>
        )}
      >
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          <Row gutter={[12, 12]}>
            <Col xs={24} md={8}>
              <Input
                allowClear
                value={searchInput}
                placeholder="Tìm mã giao dịch, hóa đơn hoặc nội dung chuyển khoản"
                onChange={(event) => setSearchInput(event.target.value)}
                onPressEnter={handleApplyFilters}
              />
            </Col>
            <Col xs={24} md={5}>
              <Select
                style={{ width: '100%' }}
                value={statusFilter}
                options={STATUS_OPTIONS}
                onChange={setStatusFilter}
              />
            </Col>
            <Col xs={24} md={7}>
              <Select
                showSearch
                optionFilterProp="label"
                style={{ width: '100%' }}
                value={invoiceFilter}
                options={[{ label: 'Tất cả hóa đơn', value: 'all' }, ...invoiceOptions]}
                onChange={setInvoiceFilter}
              />
            </Col>
            <Col xs={24} md={4}>
              <Space wrap>
                <Button type="primary" onClick={handleApplyFilters}>Lọc</Button>
                <Button onClick={handleResetFilters}>Xóa lọc</Button>
              </Space>
            </Col>
          </Row>

          <Table
            rowKey="id"
            loading={loading}
            columns={columns}
            dataSource={transactions}
            pagination={{
              current: pagination.current,
              pageSize: pagination.pageSize,
              total: pagination.total,
              showSizeChanger: true,
            }}
            locale={{ emptyText: 'Chưa có giao dịch ngân hàng phù hợp bộ lọc hiện tại.' }}
            onChange={(nextPagination) => fetchTransactions({
              page: nextPagination.current,
              pageSize: nextPagination.pageSize,
            })}
          />
        </Space>
      </SectionCard>

      <Modal
        title="Mô phỏng giao dịch ngân hàng"
        open={modalOpen}
        forceRender
        okText="Lưu giao dịch"
        cancelText="Đóng"
        confirmLoading={submitting}
        onOk={handleSimulate}
        onCancel={() => setModalOpen(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item label="Hóa đơn muốn khớp" name="invoice_code">
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="Chọn hóa đơn hoặc để trống nếu chưa rõ"
              options={simulateInvoiceOptions}
              onChange={handleInvoiceCodeChange}
            />
          </Form.Item>
          <Form.Item label="Tài khoản ngân hàng nhận tiền" name="bank_account_id">
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="Chọn tài khoản nhận"
              options={bankAccountOptions}
            />
          </Form.Item>
          <Form.Item
            label="Số tiền giao dịch"
            name="amount"
            rules={[{ required: true, message: 'Nhập số tiền giao dịch.' }]}
          >
            <InputNumber min={1} style={{ width: '100%' }} placeholder="Nhập số tiền VND" />
          </Form.Item>
          <Form.Item
            label="Nội dung chuyển khoản"
            name="description"
            rules={[{ required: true, message: 'Nhập nội dung chuyển khoản.' }]}
          >
            <Input prefix={<BankOutlined />} placeholder="Ví dụ: Thanh toán INV-DEMO-002" />
          </Form.Item>
          <Form.Item label="Ghi chú nội bộ" name="note">
            <Input.TextArea rows={3} placeholder="Ghi chú cho kế toán nếu cần" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}

export default BankReconciliationPage;
