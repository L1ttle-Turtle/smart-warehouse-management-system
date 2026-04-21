import {
  Alert,
  Button,
  Card,
  Col,
  DatePicker,
  Empty,
  Input,
  Row,
  Segmented,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import api from '../api/client';

function statusColor(status) {
  if (status === 'active') return 'green';
  if (status === 'expired') return 'orange';
  if (status === 'revoked') return 'red';
  return 'default';
}

function PermissionCard({ item, column, onDragStart, onDelegate, onRevoke }) {
  return (
    <div
      className="permission-card"
      draggable
      onDragStart={(event) => onDragStart(event, item, column)}
    >
      <Space orientation="vertical" size={8} style={{ width: '100%' }}>
        <div>
          <Tag color={column === 'available' ? 'blue' : 'gold'}>{item.permission_name}</Tag>
          {column !== 'available' ? <Tag color={statusColor(item.status)}>{item.status}</Tag> : null}
        </div>
        <Typography.Text type="secondary">
          {column === 'available'
            ? item.description || 'Quyền hiện bạn đang có và có thể ủy quyền.'
            : `Cấp bởi ${item.grantor_user_name} (${item.grantor_role_name})`}
        </Typography.Text>
        {item.expires_at ? (
          <Typography.Text type="secondary">
            Hạn dùng: {new Date(item.expires_at).toLocaleString('vi-VN')}
          </Typography.Text>
        ) : null}
        {column === 'available' ? (
          <Button size="small" type="primary" onClick={() => onDelegate(item.permission_id)}>
            Ủy quyền
          </Button>
        ) : (
          <Button size="small" danger disabled={item.status !== 'active'} onClick={() => onRevoke(item.id)}>
            Thu hồi
          </Button>
        )}
      </Space>
    </div>
  );
}

function DelegationPage() {
  const [metaLoading, setMetaLoading] = useState(true);
  const [usersLoading, setUsersLoading] = useState(false);
  const [delegationsLoading, setDelegationsLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [meta, setMeta] = useState({
    grantor: null,
    target_roles: [],
    grantable_permissions: [],
  });
  const [usersResult, setUsersResult] = useState({
    items: [],
    total: 0,
    page: 1,
    page_size: 10,
  });
  const [selectedRoleFilter, setSelectedRoleFilter] = useState('all');
  const [selectedTargetUserId, setSelectedTargetUserId] = useState(null);
  const [selectedTargetUser, setSelectedTargetUser] = useState(null);
  const [selectedUserDelegations, setSelectedUserDelegations] = useState([]);
  const [delegationStatusFilter, setDelegationStatusFilter] = useState('all');
  const [userSearch, setUserSearch] = useState('');
  const [userQuery, setUserQuery] = useState('');
  const [userPage, setUserPage] = useState(1);
  const [userPageSize, setUserPageSize] = useState(10);
  const [delegationNote, setDelegationNote] = useState('');
  const [expiresAt, setExpiresAt] = useState(null);

  const loadDelegations = useCallback(async (targetUserId, status = delegationStatusFilter) => {
    if (!targetUserId) {
      setSelectedUserDelegations([]);
      return;
    }

    setDelegationsLoading(true);
    try {
      const response = await api.get('/delegations', {
        params: { target_user_id: targetUserId, status },
      });
      setSelectedUserDelegations(response.data.items || []);
    } catch (requestError) {
      message.error(
        requestError.response?.data?.message || 'Không tải được lịch sử ủy quyền của user đã chọn.',
      );
    } finally {
      setDelegationsLoading(false);
    }
  }, [delegationStatusFilter]);

  useEffect(() => {
    const loadMeta = async () => {
      setMetaLoading(true);
      setError('');
      try {
        const response = await api.get('/delegations/meta');
        setMeta(response.data);
      } catch (requestError) {
        setError(requestError.response?.data?.message || 'Không tải được dữ liệu ủy quyền.');
      } finally {
        setMetaLoading(false);
      }
    };

    loadMeta();
  }, []);

  useEffect(() => {
    const loadUsers = async () => {
      setUsersLoading(true);
      try {
        const params = {
          search: userQuery,
          page: userPage,
          page_size: userPageSize,
          status: 'active',
        };
        if (selectedRoleFilter !== 'all') {
          params.role_id = Number(selectedRoleFilter);
        }

        const response = await api.get('/delegations/users', { params });
        const nextUsers = response.data;
        setUsersResult(nextUsers);

        const nextSelectedUser = nextUsers.items.find((item) => item.id === selectedTargetUserId)
          || nextUsers.items[0]
          || null;

        setSelectedTargetUser(nextSelectedUser);
        setSelectedTargetUserId(nextSelectedUser?.id ?? null);
        if (!nextSelectedUser) {
          setSelectedUserDelegations([]);
        }
      } catch (requestError) {
        message.error(
          requestError.response?.data?.message || 'Không tải được danh sách user có thể nhận ủy quyền.',
        );
      } finally {
        setUsersLoading(false);
      }
    };

    loadUsers();
  }, [selectedRoleFilter, selectedTargetUserId, userPage, userPageSize, userQuery]);

  useEffect(() => {
    loadDelegations(selectedTargetUserId, delegationStatusFilter);
  }, [delegationStatusFilter, loadDelegations, selectedTargetUserId]);

  const ownDelegations = useMemo(
    () => selectedUserDelegations.filter(
      (item) => item.grantor_user_id === meta.grantor?.user_id && item.status === 'active',
    ),
    [meta.grantor?.user_id, selectedUserDelegations],
  );

  const delegatedPermissionIds = useMemo(
    () => new Set(ownDelegations.map((item) => item.permission_id)),
    [ownDelegations],
  );

  const availablePermissions = useMemo(
    () => meta.grantable_permissions.filter((item) => {
      if (delegatedPermissionIds.has(item.id)) {
        return false;
      }
      if (
        item.permission_name === 'delegations.manage'
        && selectedTargetUser
        && !selectedTargetUser.can_receive_delegation_manage
      ) {
        return false;
      }
      return true;
    }),
    [meta.grantable_permissions, delegatedPermissionIds, selectedTargetUser],
  );

  const roleFilterOptions = useMemo(
    () => [
      { label: 'Tất cả', value: 'all' },
      ...meta.target_roles.map((role) => ({
        label: role.role_name,
        value: String(role.id),
      })),
    ],
    [meta.target_roles],
  );

  const handleSelectUser = (user) => {
    setSelectedTargetUser(user);
    setSelectedTargetUserId(user?.id ?? null);
  };

  const handleDelegate = async (permissionId) => {
    if (!selectedTargetUserId) {
      message.warning('Hãy chọn một user trước khi ủy quyền.');
      return;
    }

    setSaving(true);
    try {
      await api.post('/delegations', {
        target_user_id: selectedTargetUserId,
        permission_id: permissionId,
        note: delegationNote,
        expires_at: expiresAt ? expiresAt.toISOString() : null,
      });
      await loadDelegations(selectedTargetUserId, delegationStatusFilter);
      setDelegationNote('');
      setExpiresAt(null);
      message.success('Ủy quyền thành công.');
    } catch (requestError) {
      message.error(requestError.response?.data?.message || 'Không thể ủy quyền quyền này.');
    } finally {
      setSaving(false);
    }
  };

  const handleRevoke = async (delegationId) => {
    setSaving(true);
    try {
      await api.delete(`/delegations/${delegationId}`, {
        data: { revoke_reason: 'Thu hồi từ giao diện quản trị' },
      });
      await loadDelegations(selectedTargetUserId, delegationStatusFilter);
      message.success('Thu hồi ủy quyền thành công.');
    } catch (requestError) {
      message.error(requestError.response?.data?.message || 'Không thể thu hồi ủy quyền này.');
    } finally {
      setSaving(false);
    }
  };

  const handleDrop = async (event, targetColumn) => {
    event.preventDefault();
    const payload = event.dataTransfer.getData('application/json');
    if (!payload) {
      return;
    }
    const parsed = JSON.parse(payload);
    if (parsed.column === targetColumn) {
      return;
    }
    if (targetColumn === 'delegated') {
      await handleDelegate(parsed.item.permission_id);
      return;
    }
    await handleRevoke(parsed.item.id);
  };

  const onDragStart = (event, item, column) => {
    event.dataTransfer.setData('application/json', JSON.stringify({ item, column }));
  };

  return (
    <Space orientation="vertical" size={20} style={{ width: '100%' }}>
      <Card className="page-card" styles={{ body: { padding: 28 } }}>
        <Typography.Title level={2} className="page-title">
          Ủy quyền quyền hạn theo từng user
        </Typography.Title>
        <Typography.Paragraph className="page-subtitle">
          Vai trò cấp trên chỉ cấp quyền cho đúng user cần dùng, không cấp tràn cho cả role.
          Mỗi lần ủy quyền đều được lưu lại ai cấp, cấp quyền gì, cho user nào, có hạn dùng hay không
          và đã bị thu hồi hay hết hạn ra sao.
        </Typography.Paragraph>
      </Card>

      {error ? (
        <Alert
          type="error"
          showIcon
          message="Không tải được dữ liệu ủy quyền"
          description={error}
        />
      ) : null}

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card className="page-card" styles={{ body: { padding: 24 } }}>
            <Typography.Text type="secondary">Người đang ủy quyền</Typography.Text>
            <div className="metric-value">{meta.grantor?.full_name || '-'}</div>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card className="page-card" styles={{ body: { padding: 24 } }}>
            <Typography.Text type="secondary">Vai trò hiện tại</Typography.Text>
            <div className="metric-value">{meta.grantor?.role_name || '-'}</div>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card className="page-card" styles={{ body: { padding: 24 } }}>
            <Typography.Text type="secondary">Số quyền có thể ủy quyền</Typography.Text>
            <div className="metric-value">{meta.grantable_permissions.length}</div>
          </Card>
        </Col>
      </Row>

      <Card className="page-card" styles={{ body: { padding: 28 } }}>
        <div className="section-toolbar" style={{ marginBottom: 20, alignItems: 'flex-start' }}>
          <div>
            <Typography.Title level={4} style={{ marginTop: 0, marginBottom: 6 }}>
              Chọn user nhận ủy quyền
            </Typography.Title>
            <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
              Dùng bộ lọc và tìm kiếm để tìm đúng user trong danh sách lớn, sau đó chọn một dòng để
              cấp quyền riêng cho tài khoản đó.
            </Typography.Paragraph>
          </div>
          <Input.Search
            allowClear
            enterButton="Tìm kiếm"
            placeholder="Tìm theo username, họ tên hoặc email"
            style={{ maxWidth: 320 }}
            value={userSearch}
            onChange={(event) => {
              const value = event.target.value;
              setUserSearch(value);
              if (!value) {
                setUserPage(1);
                setUserQuery('');
              }
            }}
            onSearch={(value) => {
              setUserPage(1);
              setUserQuery(value.trim());
            }}
          />
        </div>

        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          <Segmented
            block
            options={roleFilterOptions}
            value={selectedRoleFilter}
            onChange={(value) => {
              setSelectedRoleFilter(value);
              setUserPage(1);
            }}
          />

          <Table
            rowKey="id"
            loading={metaLoading || usersLoading}
            dataSource={usersResult.items}
            locale={{ emptyText: 'Không có user nào phù hợp với bộ lọc hiện tại.' }}
            rowSelection={{
              type: 'radio',
              selectedRowKeys: selectedTargetUserId ? [selectedTargetUserId] : [],
              onChange: (_selectedRowKeys, selectedRows) => {
                handleSelectUser(selectedRows[0] || null);
              },
            }}
            onRow={(record) => ({
              onClick: () => handleSelectUser(record),
            })}
            pagination={{
              current: userPage,
              pageSize: userPageSize,
              total: usersResult.total,
              showSizeChanger: true,
              pageSizeOptions: ['10', '20', '50'],
              onChange: (page, nextPageSize) => {
                setUserPage(page);
                setUserPageSize(nextPageSize);
              },
            }}
            columns={[
              { title: 'Username', dataIndex: 'username', key: 'username' },
              { title: 'Họ tên', dataIndex: 'full_name', key: 'full_name', render: (value) => value || '-' },
              { title: 'Email', dataIndex: 'email', key: 'email', render: (value) => value || '-' },
              { title: 'Vai trò', dataIndex: 'role_name', key: 'role_name', render: (value) => <Tag color="cyan">{value}</Tag> },
              {
                title: 'Trạng thái',
                dataIndex: 'status',
                key: 'status',
                render: (value) => (
                  <Tag color={value === 'active' ? 'green' : 'default'}>
                    {value === 'active' ? 'Đang hoạt động' : 'Ngừng hoạt động'}
                  </Tag>
                ),
              },
            ]}
          />
        </Space>
      </Card>

      <Card className="page-card" styles={{ body: { padding: 28 } }}>
        {selectedTargetUser ? (
          <Space orientation="vertical" size={18} style={{ width: '100%' }}>
            <div>
              <Typography.Title level={4} style={{ marginTop: 0, marginBottom: 6 }}>
                Bảng kéo thả ủy quyền cho user đã chọn
              </Typography.Title>
              <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
                Bạn đang thao tác cho <strong>{selectedTargetUser.full_name}</strong> ({selectedTargetUser.username}).
                Kéo quyền từ cột trái sang cột phải để cấp riêng cho user này, hoặc kéo ngược lại để thu hồi.
              </Typography.Paragraph>
            </div>

            <Row gutter={[16, 16]}>
              <Col xs={24} md={8}>
                <Card className="glass-panel" styles={{ body: { padding: 20 } }}>
                  <Typography.Text type="secondary">User đang chọn</Typography.Text>
                  <div className="metric-value" style={{ fontSize: '1.6rem' }}>
                    {selectedTargetUser.full_name}
                  </div>
                  <Space wrap>
                    <Tag color="blue">@{selectedTargetUser.username}</Tag>
                    <Tag color="cyan">{selectedTargetUser.role_name}</Tag>
                  </Space>
                </Card>
              </Col>
              <Col xs={24} md={8}>
                <Card className="glass-panel" styles={{ body: { padding: 20 } }}>
                  <Typography.Text type="secondary">Email</Typography.Text>
                  <div className="metric-value" style={{ fontSize: '1.2rem' }}>
                    {selectedTargetUser.email || '-'}
                  </div>
                </Card>
              </Col>
              <Col xs={24} md={8}>
                <Card className="glass-panel" styles={{ body: { padding: 20 } }}>
                  <Typography.Text type="secondary">Số quyền bạn đã cấp riêng</Typography.Text>
                  <div className="metric-value" style={{ fontSize: '1.6rem' }}>
                    {ownDelegations.length}
                  </div>
                </Card>
              </Col>
            </Row>

            <Row gutter={[16, 16]}>
              <Col xs={24} lg={12}>
                <Input
                  allowClear
                  placeholder="Ghi chú khi cấp quyền (tuỳ chọn)"
                  value={delegationNote}
                  onChange={(event) => setDelegationNote(event.target.value)}
                />
              </Col>
              <Col xs={24} lg={12}>
                <DatePicker
                  showTime
                  allowClear
                  style={{ width: '100%' }}
                  placeholder="Chọn hạn dùng ủy quyền (tuỳ chọn)"
                  value={expiresAt}
                  onChange={setExpiresAt}
                />
              </Col>
            </Row>

            <div className="delegation-grid">
              <section
                className="permission-dropzone"
                onDragOver={(event) => event.preventDefault()}
                onDrop={(event) => handleDrop(event, 'available')}
              >
                <Typography.Title level={5} style={{ marginTop: 0 }}>
                  Quyền bạn đang có
                </Typography.Title>
                <Typography.Text type="secondary">
                  Những quyền bạn có thể cấp riêng cho user này.
                </Typography.Text>
                <div className="permission-list">
                  {availablePermissions.length ? availablePermissions.map((item) => (
                    <PermissionCard
                      key={item.id}
                      item={{
                        permission_id: item.id,
                        permission_name: item.permission_name,
                        description: item.description,
                      }}
                      column="available"
                      onDragStart={onDragStart}
                      onDelegate={handleDelegate}
                      onRevoke={handleRevoke}
                    />
                  )) : (
                    <Empty
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      description="Không còn quyền nào để ủy quyền thêm cho user này."
                    />
                  )}
                </div>
              </section>

              <section
                className="permission-dropzone permission-dropzone--active"
                onDragOver={(event) => event.preventDefault()}
                onDrop={(event) => handleDrop(event, 'delegated')}
              >
                <Typography.Title level={5} style={{ marginTop: 0 }}>
                  Quyền bạn đã cấp riêng
                </Typography.Title>
                <Typography.Text type="secondary">
                  Đây là các quyền do chính bạn cấp riêng cho user đang chọn và vẫn còn hiệu lực.
                </Typography.Text>
                <div className="permission-list">
                  {ownDelegations.length ? ownDelegations.map((item) => (
                    <PermissionCard
                      key={item.id}
                      item={item}
                      column="delegated"
                      onDragStart={onDragStart}
                      onDelegate={handleDelegate}
                      onRevoke={handleRevoke}
                    />
                  )) : (
                    <Empty
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      description="Bạn chưa cấp quyền riêng nào còn hiệu lực cho user này."
                    />
                  )}
                </div>
              </section>
            </div>
          </Space>
        ) : (
          <Empty description="Hãy chọn một user ở bảng bên trên để bắt đầu ủy quyền." />
        )}
      </Card>

      <Card className="page-card" styles={{ body: { padding: 28 } }}>
        <div className="section-toolbar" style={{ marginBottom: 20 }}>
          <div>
            <Typography.Title level={4} style={{ marginTop: 0, marginBottom: 6 }}>
              Lịch sử ủy quyền của user đã chọn
            </Typography.Title>
            <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
              Dùng để truy vết ai đã cấp quyền nào, lúc nào, có hạn dùng hay đã bị thu hồi/hết hạn chưa.
            </Typography.Paragraph>
          </div>
          <Select
            value={delegationStatusFilter}
            onChange={setDelegationStatusFilter}
            style={{ width: 180 }}
            options={[
              { label: 'Tất cả trạng thái', value: 'all' },
              { label: 'Đang hiệu lực', value: 'active' },
              { label: 'Đã hết hạn', value: 'expired' },
              { label: 'Đã thu hồi', value: 'revoked' },
            ]}
          />
        </div>
        <Table
          rowKey="id"
          loading={delegationsLoading || saving}
          pagination={false}
          dataSource={selectedUserDelegations}
          locale={{ emptyText: 'Chưa có bản ghi ủy quyền nào cho user này.' }}
          columns={[
            {
              title: 'Quyền',
              dataIndex: 'permission_name',
              key: 'permission_name',
              render: (value) => <Tag color="gold">{value}</Tag>,
            },
            { title: 'Người cấp', dataIndex: 'grantor_user_name', key: 'grantor_user_name' },
            { title: 'Vai trò cấp', dataIndex: 'grantor_role_name', key: 'grantor_role_name' },
            {
              title: 'Trạng thái',
              dataIndex: 'status',
              key: 'status',
              render: (value) => <Tag color={statusColor(value)}>{value}</Tag>,
            },
            {
              title: 'Hạn dùng',
              dataIndex: 'expires_at',
              key: 'expires_at',
              render: (value) => (value ? new Date(value).toLocaleString('vi-VN') : 'Không giới hạn'),
            },
            {
              title: 'Thu hồi lúc',
              dataIndex: 'revoked_at',
              key: 'revoked_at',
              render: (value) => (value ? new Date(value).toLocaleString('vi-VN') : '-'),
            },
            { title: 'Thu hồi bởi', dataIndex: 'revoked_by_user_name', key: 'revoked_by_user_name', render: (value) => value || '-' },
            { title: 'Ghi chú', dataIndex: 'note', key: 'note', render: (value) => value || '-' },
          ]}
        />
      </Card>
    </Space>
  );
}

export default DelegationPage;
