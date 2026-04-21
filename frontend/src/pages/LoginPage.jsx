import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { Button, Card, Form, Input, Space, Typography, message } from 'antd';
import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/useAuth';

function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  const [loading, setLoading] = useState(false);

  return (
    <div className="auth-shell">
      <section className="auth-hero">
        <div>
          <div className="brand-mark">Warehouse IQ</div>
          <Typography.Title style={{ color: '#fff5e5', marginTop: 24, fontFamily: '"Space Grotesk", sans-serif' }}>
            Đăng nhập một lần, vào đúng màn hình, thấy đúng quyền.
          </Typography.Title>
          <Typography.Paragraph style={{ color: 'rgba(255, 245, 229, 0.8)', fontSize: 16 }}>
            Hệ thống hiện đã có xác thực JWT, phân quyền theo vai trò, ủy quyền theo từng user,
            đổi mật khẩu theo policy và dashboard riêng cho từng nhóm người dùng.
          </Typography.Paragraph>
        </div>

        <Space orientation="vertical" size={8}>
          <Typography.Text style={{ color: 'rgba(255, 245, 229, 0.82)' }}>
            Tài khoản seed: admin, manager, staff, accountant, shipper
          </Typography.Text>
          <Typography.Text style={{ color: 'rgba(255, 245, 229, 0.7)' }}>
            Mật khẩu mặc định: Admin@123, Manager@123, Staff@123, Accountant@123, Shipper@123
          </Typography.Text>
        </Space>
      </section>

      <section className="auth-panel">
        <Card className="auth-card glass-panel" variant="borderless">
          <Typography.Title level={2} style={{ marginBottom: 0, fontFamily: '"Space Grotesk", sans-serif' }}>
            Đăng nhập hệ thống
          </Typography.Title>
          <Typography.Paragraph type="secondary">
            Nhập tài khoản để kiểm tra quyền truy cập theo vai trò.
          </Typography.Paragraph>

          <Form
            layout="vertical"
            onFinish={async (values) => {
              setLoading(true);
              try {
                const nextUser = await login(values);
                if (nextUser?.must_change_password) {
                  navigate('/profile?forcePasswordReset=1', { replace: true });
                  return;
                }
                navigate(location.state?.from?.pathname || '/', { replace: true });
              } catch (error) {
                message.error(error.response?.data?.message || 'Đăng nhập thất bại.');
              } finally {
                setLoading(false);
              }
            }}
            initialValues={{ username: 'admin', password: 'Admin@123' }}
          >
            <Form.Item
              name="username"
              label="Tên đăng nhập"
              rules={[{ required: true, message: 'Nhập tên đăng nhập' }]}
            >
              <Input prefix={<UserOutlined />} size="large" />
            </Form.Item>
            <Form.Item
              name="password"
              label="Mật khẩu"
              rules={[{ required: true, message: 'Nhập mật khẩu' }]}
            >
              <Input.Password prefix={<LockOutlined />} size="large" />
            </Form.Item>
            <Button type="primary" htmlType="submit" size="large" block loading={loading}>
              Đăng nhập
            </Button>
          </Form>
        </Card>
      </section>
    </div>
  );
}

export default LoginPage;
