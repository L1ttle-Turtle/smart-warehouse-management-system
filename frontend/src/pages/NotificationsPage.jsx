import { SendOutlined } from '@ant-design/icons';
import { Button, Form, Input, List, Modal, Select, Space, Typography, message } from 'antd';
import { useEffect, useMemo, useState } from 'react';

import api from '../api/client';
import { useAuth } from '../auth/useAuth';
import SectionCard from '../components/SectionCard';
import StatusTag from '../components/StatusTag';
import { formatDateTime } from '../utils/format';

const roleOptions = [
  { label: 'Admin', value: 'admin' },
  { label: 'Manager', value: 'manager' },
  { label: 'Staff', value: 'staff' },
  { label: 'Accountant', value: 'accountant' },
  { label: 'Shipper', value: 'shipper' },
];

function NotificationsPage() {
  const { socket, hasPermission } = useAuth();
  const [items, setItems] = useState([]);
  const [users, setUsers] = useState([]);
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();

  const canBroadcast = hasPermission('notifications.manage');

  const fetchData = async () => {
    try {
      const [notificationResponse, userResponse] = await Promise.all([
        api.get('/notifications'),
        api.get('/directory/users'),
      ]);
      setItems(notificationResponse.data.items || []);
      setUsers(userResponse.data.items || []);
    } catch (error) {
      message.error(error.response?.data?.message || 'Khong tai duoc thong bao.');
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (!socket) {
      return undefined;
    }
    const onPush = (payload) => setItems((current) => [payload, ...current]);
    socket.on('notification:push', onPush);
    return () => {
      socket.off('notification:push', onPush);
    };
  }, [socket]);

  const userOptions = useMemo(
    () => users.map((item) => ({ label: `${item.full_name} (${item.role})`, value: item.id })),
    [users],
  );

  return (
    <SectionCard
      title="Thong bao noi bo"
      subtitle="Nhan thong bao realtime va gui thong diep cho user hoac vai tro."
      extra={canBroadcast ? (
        <Button type="primary" icon={<SendOutlined />} onClick={() => setOpen(true)}>
          Gui thong bao
        </Button>
      ) : null}
    >
      <List
        dataSource={items}
        renderItem={(item) => (
          <List.Item
            actions={[
              item.is_read ? <StatusTag key="read" value="paid" /> : (
                <Button
                  key="mark-read"
                  size="small"
                  onClick={async () => {
                    await api.patch(`/notifications/${item.id}/read`);
                    fetchData();
                  }}
                >
                  Danh dau da doc
                </Button>
              ),
            ]}
          >
            <List.Item.Meta
              title={(
                <Space>
                  <Typography.Text strong>{item.title}</Typography.Text>
                  <StatusTag value={item.type} />
                </Space>
              )}
              description={(
                <Space orientation="vertical" size={4}>
                  <Typography.Text>{item.content}</Typography.Text>
                  <Typography.Text type="secondary">
                    {item.sender_name || 'System'} | {formatDateTime(item.created_at)}
                  </Typography.Text>
                </Space>
              )}
            />
          </List.Item>
        )}
      />

      <Modal title="Gui thong bao" open={open} onCancel={() => setOpen(false)} footer={null} destroyOnHidden>
        <Form
          form={form}
          layout="vertical"
          onFinish={async (values) => {
            try {
              await api.post('/notifications/broadcast', values);
              message.success('Da gui thong bao.');
              setOpen(false);
              form.resetFields();
              fetchData();
            } catch (error) {
              message.error(error.response?.data?.message || 'Khong gui duoc thong bao.');
            }
          }}
        >
          <Form.Item name="title" label="Tieu de" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="content" label="Noi dung" rules={[{ required: true }]}>
            <Input.TextArea rows={4} />
          </Form.Item>
          <Form.Item name="role_names" label="Gui theo vai tro">
            <Select mode="multiple" options={roleOptions} />
          </Form.Item>
          <Form.Item name="receiver_ids" label="Gui cho user cu the">
            <Select mode="multiple" options={userOptions} />
          </Form.Item>
          <Space>
            <Button type="primary" htmlType="submit">Gui</Button>
            <Button onClick={() => setOpen(false)}>Dong</Button>
          </Space>
        </Form>
      </Modal>
    </SectionCard>
  );
}

export default NotificationsPage;
