import { ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import { Button, Card, Input, Select, Space, Table, Tag, Typography, message } from 'antd';
import { useCallback, useEffect, useState } from 'react';

import api from '../api/client';

const actionOptions = [
  { label: 'Tất cả hành động', value: 'all' },
  { label: 'Đăng nhập thành công', value: 'auth.login_success' },
  { label: 'Đăng nhập thất bại', value: 'auth.login_failed' },
  { label: 'Cập nhật hồ sơ', value: 'auth.profile_updated' },
  { label: 'Tạo tài khoản', value: 'users.created' },
  { label: 'Cập nhật tài khoản', value: 'users.updated' },
  { label: 'Xóa tài khoản', value: 'users.deleted' },
  { label: 'Tạo nhân sự', value: 'employees.created' },
  { label: 'Cập nhật nhân sự', value: 'employees.updated' },
  { label: 'Xóa nhân sự', value: 'employees.deleted' },
  { label: 'Cấp ủy quyền', value: 'delegations.created' },
  { label: 'Kích hoạt lại ủy quyền', value: 'delegations.reactivated' },
  { label: 'Thu hồi ủy quyền', value: 'delegations.revoked' },
];

const entityTypeOptions = [
  { label: 'Tất cả đối tượng', value: 'all' },
  { label: 'User', value: 'user' },
  { label: 'Employee', value: 'employee' },
  { label: 'Delegation', value: 'delegation' },
];

function AuditLogsPage() {
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState([]);
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [actionFilter, setActionFilter] = useState('all');
  const [entityTypeFilter, setEntityTypeFilter] = useState('all');
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
  });
  const [sorter, setSorter] = useState({
    field: 'created_at',
    order: 'descend',
  });
  const currentPage = pagination.current;
  const currentPageSize = pagination.pageSize;

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
        page: currentPage,
        page_size: currentPageSize,
        sort_by: sorter.field,
        sort_order: sorter.order === 'ascend' ? 'asc' : 'desc',
      };
      if (searchQuery) {
        params.search = searchQuery;
      }
      if (actionFilter !== 'all') {
        params.action = actionFilter;
      }
      if (entityTypeFilter !== 'all') {
        params.entity_type = entityTypeFilter;
      }

      const response = await api.get('/audit-logs', { params });
      setItems(response.data.items || []);
      setPagination((current) => ({
        ...current,
        current: response.data.page || current.current,
        pageSize: response.data.page_size || current.pageSize,
        total: response.data.total || 0,
      }));
    } catch (error) {
      message.error(error.response?.data?.message || 'Không tải được audit log.');
    } finally {
      setLoading(false);
    }
  }, [actionFilter, currentPage, currentPageSize, entityTypeFilter, searchQuery, sorter.field, sorter.order]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  return (
    <Space orientation="vertical" size={20} style={{ width: '100%' }}>
      <Card className="page-card" styles={{ body: { padding: 28 } }}>
        <Typography.Title level={2} className="page-title">
          Audit log
        </Typography.Title>
        <Typography.Paragraph className="page-subtitle">
          Nhật ký thao tác dùng để truy vết thay đổi trên xác thực, người dùng, nhân sự và ủy quyền.
        </Typography.Paragraph>
      </Card>

      <Card className="page-card" styles={{ body: { padding: 28 } }}>
        <div className="section-toolbar resource-toolbar">
          <Space wrap size={12}>
            <Input.Search
              allowClear
              enterButton="Tìm"
              prefix={<SearchOutlined />}
              placeholder="Tìm theo mô tả, hành động hoặc đối tượng"
              value={searchInput}
              onChange={(event) => {
                const value = event.target.value;
                setSearchInput(value);
                if (!value) {
                  setSearchQuery('');
                  setPagination((current) => ({ ...current, current: 1 }));
                }
              }}
              onSearch={(value) => {
                setSearchQuery(value.trim());
                setPagination((current) => ({ ...current, current: 1 }));
              }}
              style={{ width: 320, maxWidth: '100%' }}
            />
            <Select
              value={actionFilter}
              onChange={(value) => {
                setActionFilter(value);
                setPagination((current) => ({ ...current, current: 1 }));
              }}
              options={actionOptions}
              style={{ width: 240 }}
            />
            <Select
              value={entityTypeFilter}
              onChange={(value) => {
                setEntityTypeFilter(value);
                setPagination((current) => ({ ...current, current: 1 }));
              }}
              options={entityTypeOptions}
              style={{ width: 180 }}
            />
            <Button icon={<ReloadOutlined />} onClick={fetchLogs}>
              Làm mới
            </Button>
          </Space>
          <Typography.Text type="secondary">
            Audit log đang dùng lọc, sort và phân trang ở phía server.
          </Typography.Text>
        </div>

        <Table
          rowKey="id"
          loading={loading}
          dataSource={items}
          scroll={{ x: 1100 }}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: pagination.total,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '50', '100'],
          }}
          onChange={(nextPagination, _filters, nextSorter) => {
            setPagination((current) => ({
              ...current,
              current: nextPagination.current || 1,
              pageSize: nextPagination.pageSize || current.pageSize,
            }));
            const sorterObject = Array.isArray(nextSorter) ? nextSorter[0] : nextSorter;
            setSorter({
              field: sorterObject?.field || 'created_at',
              order: sorterObject?.order || 'descend',
            });
          }}
          columns={[
            {
              title: 'Thời điểm',
              dataIndex: 'created_at',
              key: 'created_at',
              sorter: true,
              render: (value) => (value ? new Date(value).toLocaleString('vi-VN') : '-'),
            },
            {
              title: 'Hành động',
              dataIndex: 'action',
              key: 'action',
              sorter: true,
              render: (value) => <Tag color="blue">{value}</Tag>,
            },
            {
              title: 'Đối tượng',
              dataIndex: 'entity_type',
              key: 'entity_type',
              sorter: true,
              render: (value) => <Tag color="purple">{value}</Tag>,
            },
            {
              title: 'Nhãn đối tượng',
              dataIndex: 'entity_label',
              key: 'entity_label',
              render: (value) => value || '-',
            },
            {
              title: 'Người thao tác',
              dataIndex: 'actor_user_name',
              key: 'actor_user_name',
              render: (value, record) => value || record.actor_username || '-',
            },
            {
              title: 'Người bị tác động',
              dataIndex: 'target_user_name',
              key: 'target_user_name',
              render: (value, record) => value || record.target_username || '-',
            },
            {
              title: 'Mô tả',
              dataIndex: 'description',
              key: 'description',
            },
          ]}
        />
      </Card>
    </Space>
  );
}

export default AuditLogsPage;
