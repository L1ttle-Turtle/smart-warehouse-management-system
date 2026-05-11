import { ReloadOutlined } from '@ant-design/icons';
import {
  Button,
  Col,
  Input,
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
import { formatCurrency, formatDateTime } from '../utils/format';

const PAYMENT_METHOD_OPTIONS = [
  { label: 'Tất cả phương thức', value: 'all' },
  { label: 'Tiền mặt', value: 'cash' },
  { label: 'Chuyển khoản', value: 'bank_transfer' },
  { label: 'Khác', value: 'other' },
];

function PaymentsPage() {
  const [loading, setLoading] = useState(false);
  const [payments, setPayments] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [methodFilter, setMethodFilter] = useState('all');
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
      label: `${item.invoice_code} - ${item.customer_name} - ${formatCurrency(item.total_amount)}`,
    })),
    [invoices],
  );

  const fetchInvoices = useCallback(async () => {
    try {
      const response = await api.get('/invoices', {
        params: {
          page: 1,
          page_size: 100,
          sort_by: 'created_at',
          sort_order: 'desc',
        },
      });
      setInvoices(response.data.items || []);
    } catch (error) {
      message.error(error.response?.data?.message || 'Không tải được danh sách hóa đơn để lọc thanh toán.');
    }
  }, []);

  const fetchPayments = useCallback(async (overrides = {}) => {
    setLoading(true);
    try {
      const page = overrides.page ?? currentPage;
      const pageSize = overrides.pageSize ?? currentPageSize;
      const nextSearch = overrides.search ?? searchQuery;
      const nextMethod = overrides.paymentMethod ?? methodFilter;
      const nextInvoice = overrides.invoiceId ?? invoiceFilter;
      const params = {
        page,
        page_size: pageSize,
        sort_by: 'paid_at',
        sort_order: 'desc',
      };

      if (nextSearch) {
        params.search = nextSearch;
      }
      if (nextMethod !== 'all') {
        params.payment_method = nextMethod;
      }
      if (nextInvoice !== 'all') {
        params.invoice_id = nextInvoice;
      }

      const response = await api.get('/payments', { params });
      setPayments(response.data.items || []);
      setPagination({
        current: response.data.page || page,
        pageSize: response.data.page_size || pageSize,
        total: response.data.total || 0,
      });
    } catch (error) {
      message.error(error.response?.data?.message || 'Không tải được lịch sử thanh toán.');
    } finally {
      setLoading(false);
    }
  }, [currentPage, currentPageSize, invoiceFilter, methodFilter, searchQuery]);

  useEffect(() => {
    fetchInvoices();
  }, [fetchInvoices]);

  useEffect(() => {
    fetchPayments();
  }, [fetchPayments]);

  const handleApplyFilters = () => {
    const nextSearch = searchInput.trim();
    setSearchQuery(nextSearch);
    fetchPayments({
      page: 1,
      search: nextSearch,
      paymentMethod: methodFilter,
      invoiceId: invoiceFilter,
    });
  };

  const handleResetFilters = () => {
    setSearchInput('');
    setSearchQuery('');
    setMethodFilter('all');
    setInvoiceFilter('all');
    fetchPayments({
      page: 1,
      search: '',
      paymentMethod: 'all',
      invoiceId: 'all',
    });
  };

  const columns = [
    {
      title: 'Thanh toán',
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
      title: 'Hóa đơn',
      dataIndex: 'invoice_code',
      key: 'invoice_code',
      render: (_, record) => (
        <Space orientation="vertical" size={0}>
          <Typography.Text>{record.invoice_code}</Typography.Text>
          <StatusTag value={record.invoice_status} />
        </Space>
      ),
    },
    {
      title: 'Phương thức',
      dataIndex: 'payment_method',
      key: 'payment_method',
      width: 150,
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
      width: 160,
      render: (value) => formatCurrency(value),
    },
    {
      title: 'Người ghi nhận',
      dataIndex: 'created_by_name',
      key: 'created_by_name',
      width: 180,
      render: (value) => value || '-',
    },
    {
      title: 'Ghi chú',
      dataIndex: 'note',
      key: 'note',
      render: (value) => value || '-',
    },
  ];

  return (
    <SectionCard
      title="Thanh toán"
      subtitle="Theo dõi toàn bộ payment thủ công đã ghi nhận cho hóa đơn, hỗ trợ lọc theo hóa đơn và phương thức."
      extra={(
        <Button icon={<ReloadOutlined />} onClick={() => fetchPayments()}>
          Tải lại
        </Button>
      )}
    >
      <Space orientation="vertical" size={16} style={{ width: '100%' }}>
        <Row gutter={[12, 12]}>
          <Col xs={24} md={9}>
            <Input
              allowClear
              value={searchInput}
              placeholder="Tìm theo mã thanh toán, hóa đơn, khách hàng hoặc ghi chú"
              onChange={(event) => setSearchInput(event.target.value)}
              onPressEnter={handleApplyFilters}
            />
          </Col>
          <Col xs={24} md={5}>
            <Select
              style={{ width: '100%' }}
              value={methodFilter}
              options={PAYMENT_METHOD_OPTIONS}
              onChange={setMethodFilter}
            />
          </Col>
          <Col xs={24} md={6}>
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
          dataSource={payments}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: pagination.total,
            showSizeChanger: true,
          }}
          locale={{ emptyText: 'Chưa có payment nào phù hợp bộ lọc hiện tại.' }}
          onChange={(nextPagination) => fetchPayments({
            page: nextPagination.current,
            pageSize: nextPagination.pageSize,
          })}
        />
      </Space>
    </SectionCard>
  );
}

export default PaymentsPage;
