import {
  CheckCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  SendOutlined,
} from '@ant-design/icons';
import {
  Alert,
  Button,
  Col,
  Form,
  Input,
  List,
  Modal,
  Row,
  Select,
  Space,
  Table,
  Tabs,
  Typography,
  message,
} from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import api from '../api/client';
import { useAuth } from '../auth/useAuth';
import SectionCard from '../components/SectionCard';
import StatusTag from '../components/StatusTag';
import { formatDateTime } from '../utils/format';

const TASK_STATUS_OPTIONS = [
  { label: 'Tất cả trạng thái', value: 'all' },
  { label: 'Cần làm', value: 'todo' },
  { label: 'Đang xử lý', value: 'in_progress' },
  { label: 'Hoàn thành', value: 'done' },
  { label: 'Đã hủy', value: 'cancelled' },
];

const TASK_PRIORITY_OPTIONS = [
  { label: 'Thấp', value: 'low' },
  { label: 'Trung bình', value: 'medium' },
  { label: 'Cao', value: 'high' },
];

const ROLE_OPTIONS = [
  { label: 'Admin', value: 'admin' },
  { label: 'Manager', value: 'manager' },
  { label: 'Staff', value: 'staff' },
  { label: 'Accountant', value: 'accountant' },
  { label: 'Shipper', value: 'shipper' },
];

function NotificationsPage() {
  const { hasPermission } = useAuth();
  const canManageTasks = hasPermission('tasks.manage');
  const canBroadcast = hasPermission('notifications.manage');

  const [taskForm] = Form.useForm();
  const [broadcastForm] = Form.useForm();

  const [tasks, setTasks] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [taskModalOpen, setTaskModalOpen] = useState(false);
  const [broadcastModalOpen, setBroadcastModalOpen] = useState(false);
  const [taskStatusFilter, setTaskStatusFilter] = useState('all');

  const userOptions = useMemo(
    () => users.map((item) => ({
      value: item.id,
      label: `${item.full_name} (${item.role_name || item.role || item.username})`,
    })),
    [users],
  );

  const fetchModule9Data = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
        page: 1,
        page_size: 20,
      };
      if (taskStatusFilter !== 'all') {
        params.status = taskStatusFilter;
      }

      const [taskResponse, notificationResponse, metaResponse] = await Promise.all([
        api.get('/tasks', { params }),
        api.get('/notifications', { params: { page: 1, page_size: 20 } }),
        api.get('/tasks/meta'),
      ]);

      setTasks(taskResponse.data.items || []);
      setNotifications(notificationResponse.data.items || []);
      setUsers(metaResponse.data.users || []);
    } catch (error) {
      message.error(error.response?.data?.message || 'Không tải được công việc và thông báo.');
    } finally {
      setLoading(false);
    }
  }, [taskStatusFilter]);

  useEffect(() => {
    fetchModule9Data();
  }, [fetchModule9Data]);

  const handleCreateTask = async () => {
    try {
      const values = await taskForm.validateFields();
      await api.post('/tasks', values);
      message.success('Đã tạo công việc và gửi thông báo cho người phụ trách.');
      setTaskModalOpen(false);
      taskForm.resetFields();
      await fetchModule9Data();
    } catch (error) {
      if (error?.errorFields) {
        return;
      }
      message.error(error.response?.data?.message || 'Không tạo được công việc.');
    }
  };

  const handleBroadcast = async () => {
    try {
      const values = await broadcastForm.validateFields();
      await api.post('/notifications/broadcast', values);
      message.success('Đã gửi thông báo nội bộ.');
      setBroadcastModalOpen(false);
      broadcastForm.resetFields();
      await fetchModule9Data();
    } catch (error) {
      if (error?.errorFields) {
        return;
      }
      message.error(error.response?.data?.message || 'Không gửi được thông báo.');
    }
  };

  const handleUpdateTaskStatus = async (taskId, status) => {
    try {
      await api.patch(`/tasks/${taskId}/status`, { status });
      message.success('Đã cập nhật trạng thái công việc.');
      await fetchModule9Data();
    } catch (error) {
      message.error(error.response?.data?.message || 'Không cập nhật được công việc.');
    }
  };

  const handleMarkRead = async (notificationId) => {
    try {
      await api.patch(`/notifications/${notificationId}/read`);
      message.success('Đã đánh dấu thông báo là đã đọc.');
      await fetchModule9Data();
    } catch (error) {
      message.error(error.response?.data?.message || 'Không cập nhật được thông báo.');
    }
  };

  const taskColumns = [
    {
      title: 'Công việc',
      dataIndex: 'title',
      key: 'title',
      render: (_, record) => (
        <Space orientation="vertical" size={0}>
          <Typography.Text strong>{record.title}</Typography.Text>
          <Typography.Text type="secondary">{record.task_code}</Typography.Text>
          {record.description ? (
            <Typography.Text type="secondary">{record.description}</Typography.Text>
          ) : null}
        </Space>
      ),
    },
    {
      title: 'Người phụ trách',
      dataIndex: 'assigned_to_name',
      key: 'assigned_to_name',
      width: 180,
      render: (_, record) => (
        <Space orientation="vertical" size={0}>
          <Typography.Text>{record.assigned_to_name}</Typography.Text>
          <Typography.Text type="secondary">{record.assigned_to_role}</Typography.Text>
        </Space>
      ),
    },
    {
      title: 'Ưu tiên',
      dataIndex: 'priority',
      key: 'priority',
      width: 120,
      render: (value) => <StatusTag value={value} />,
    },
    {
      title: 'Trạng thái',
      dataIndex: 'status',
      key: 'status',
      width: 150,
      render: (value) => <StatusTag value={value} />,
    },
    {
      title: 'Hạn xử lý',
      dataIndex: 'due_at',
      key: 'due_at',
      width: 170,
      render: (value) => formatDateTime(value),
    },
    {
      title: 'Cập nhật',
      key: 'actions',
      width: 190,
      render: (_, record) => (
        <Select
          style={{ width: '100%' }}
          value={record.status}
          options={TASK_STATUS_OPTIONS.filter((item) => item.value !== 'all')}
          onChange={(status) => handleUpdateTaskStatus(record.id, status)}
        />
      ),
    },
  ];

  return (
    <Space orientation="vertical" size={16} style={{ width: '100%' }}>
      <SectionCard
        title="Công việc & thông báo"
        subtitle="Module 9 tối thiểu: giao việc nội bộ, nhận thông báo và theo dõi trạng thái xử lý."
        extra={(
          <Space wrap>
            <Button icon={<ReloadOutlined />} onClick={fetchModule9Data}>
              Tải lại
            </Button>
            {canBroadcast ? (
              <Button icon={<SendOutlined />} onClick={() => setBroadcastModalOpen(true)}>
                Gửi thông báo
              </Button>
            ) : null}
            {canManageTasks ? (
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setTaskModalOpen(true)}>
                Tạo công việc
              </Button>
            ) : null}
          </Space>
        )}
      >
        <Tabs
          items={[
            {
              key: 'tasks',
              label: 'Công việc',
              children: (
                <Space orientation="vertical" size={16} style={{ width: '100%' }}>
                  <Alert
                    type="info"
                    showIcon
                    title="Tạo công việc sẽ tự sinh thông báo cho người phụ trách."
                    description="Nhân sự được giao việc có thể tự chuyển trạng thái để demo luồng phối hợp nội bộ."
                  />
                  <Row gutter={[12, 12]}>
                    <Col xs={24} sm={12} md={8}>
                      <Select
                        style={{ width: '100%' }}
                        value={taskStatusFilter}
                        options={TASK_STATUS_OPTIONS}
                        onChange={setTaskStatusFilter}
                      />
                    </Col>
                  </Row>
                  <Table
                    rowKey="id"
                    loading={loading}
                    columns={taskColumns}
                    dataSource={tasks}
                    pagination={false}
                    locale={{ emptyText: 'Chưa có công việc nào phù hợp bộ lọc hiện tại.' }}
                  />
                </Space>
              ),
            },
            {
              key: 'notifications',
              label: 'Thông báo',
              children: (
                <List
                  loading={loading}
                  dataSource={notifications}
                  locale={{ emptyText: 'Chưa có thông báo nào.' }}
                  renderItem={(item) => (
                    <List.Item
                      actions={[
                        item.is_read ? (
                          <StatusTag key="read" value="done" />
                        ) : (
                          <Button
                            key="mark-read"
                            size="small"
                            icon={<CheckCircleOutlined />}
                            onClick={() => handleMarkRead(item.id)}
                          >
                            Đánh dấu đã đọc
                          </Button>
                        ),
                      ]}
                    >
                      <List.Item.Meta
                        title={(
                          <Space wrap>
                            <Typography.Text strong>{item.title}</Typography.Text>
                            <StatusTag value={item.type} />
                          </Space>
                        )}
                        description={(
                          <Space orientation="vertical" size={4}>
                            <Typography.Text>{item.content}</Typography.Text>
                            <Typography.Text type="secondary">
                              {item.sender_name || 'System'} · {formatDateTime(item.created_at)}
                            </Typography.Text>
                          </Space>
                        )}
                      />
                    </List.Item>
                  )}
                />
              ),
            },
          ]}
        />
      </SectionCard>

      <Modal
        title="Tạo công việc nội bộ"
        open={taskModalOpen}
        onCancel={() => setTaskModalOpen(false)}
        onOk={handleCreateTask}
        okText="Tạo công việc"
        cancelText="Đóng"
        destroyOnHidden
      >
        <Form form={taskForm} layout="vertical" initialValues={{ priority: 'medium' }}>
          <Form.Item
            name="title"
            label="Tiêu đề"
            rules={[{ required: true, message: 'Vui lòng nhập tiêu đề công việc.' }]}
          >
            <Input placeholder="Ví dụ: kiểm tra tồn thấp trước ca xuất hàng" />
          </Form.Item>
          <Form.Item
            name="assigned_to_id"
            label="Người phụ trách"
            rules={[{ required: true, message: 'Vui lòng chọn người phụ trách.' }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              placeholder="Chọn user nhận việc"
              options={userOptions}
            />
          </Form.Item>
          <Form.Item name="priority" label="Mức ưu tiên">
            <Select options={TASK_PRIORITY_OPTIONS} />
          </Form.Item>
          <Form.Item name="description" label="Mô tả">
            <Input.TextArea rows={3} placeholder="Ghi rõ việc cần làm để nhân sự dễ nghiệm thu." />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Gửi thông báo nội bộ"
        open={broadcastModalOpen}
        onCancel={() => setBroadcastModalOpen(false)}
        onOk={handleBroadcast}
        okText="Gửi thông báo"
        cancelText="Đóng"
        destroyOnHidden
      >
        <Form form={broadcastForm} layout="vertical" initialValues={{ type: 'system' }}>
          <Form.Item
            name="title"
            label="Tiêu đề"
            rules={[{ required: true, message: 'Vui lòng nhập tiêu đề thông báo.' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="content"
            label="Nội dung"
            rules={[{ required: true, message: 'Vui lòng nhập nội dung thông báo.' }]}
          >
            <Input.TextArea rows={4} />
          </Form.Item>
          <Form.Item name="type" label="Loại thông báo">
            <Select
              options={[
                { label: 'Hệ thống', value: 'system' },
                { label: 'Công việc', value: 'task' },
                { label: 'Tồn kho', value: 'inventory' },
                { label: 'Vận chuyển', value: 'shipment' },
                { label: 'Thanh toán', value: 'payment' },
              ]}
            />
          </Form.Item>
          <Form.Item name="receiver_ids" label="Gửi cho user cụ thể">
            <Select
              mode="multiple"
              showSearch
              optionFilterProp="label"
              placeholder="Có thể chọn nhiều user"
              options={userOptions}
            />
          </Form.Item>
          <Form.Item name="role_names" label="Hoặc gửi theo vai trò">
            <Select mode="multiple" options={ROLE_OPTIONS} />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}

export default NotificationsPage;
