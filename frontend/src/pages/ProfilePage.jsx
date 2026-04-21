import { Alert, Button, Card, Col, Form, Input, Row, Space, Tag, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';

import { useAuth } from '../auth/useAuth';

const passwordRules = [
  'Tối thiểu 8 ký tự',
  'Có ít nhất 1 chữ hoa',
  'Có ít nhất 1 chữ thường',
  'Có ít nhất 1 chữ số',
  'Có ít nhất 1 ký tự đặc biệt',
];

function ProfilePage() {
  const { user, updateProfile } = useAuth();
  const location = useLocation();
  const [profileForm] = Form.useForm();
  const [passwordForm] = Form.useForm();
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);

  useEffect(() => {
    profileForm.setFieldsValue({
      email: user?.email || '',
      phone: user?.phone || '',
    });
  }, [profileForm, user]);

  const forcePasswordReset = user?.must_change_password || new URLSearchParams(location.search).get('forcePasswordReset') === '1';

  return (
    <Space orientation="vertical" size={20} style={{ width: '100%' }}>
      <Card className="page-card" styles={{ body: { padding: 28 } }}>
        <Typography.Title level={2} className="page-title">
          Hồ sơ cá nhân
        </Typography.Title>
        <Typography.Paragraph className="page-subtitle">
          Trang này cho phép bạn tự cập nhật thông tin liên hệ và đổi mật khẩu mà không chạm sang
          các module quản trị tài khoản phía sau.
        </Typography.Paragraph>
      </Card>

      {forcePasswordReset ? (
        <Alert
          type="warning"
          showIcon
          message="Tài khoản này cần đổi mật khẩu trước khi tiếp tục sử dụng hệ thống"
          description="Bạn vẫn có thể cập nhật email hoặc số điện thoại, nhưng vui lòng đổi mật khẩu ngay để gỡ trạng thái bắt buộc này."
        />
      ) : null}

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card className="page-card" styles={{ body: { padding: 24 } }}>
            <Typography.Text type="secondary">Họ tên</Typography.Text>
            <div className="metric-value">{user?.full_name || '-'}</div>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card className="page-card" styles={{ body: { padding: 24 } }}>
            <Typography.Text type="secondary">Tên đăng nhập</Typography.Text>
            <div className="metric-value">{user?.username || '-'}</div>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card className="page-card" styles={{ body: { padding: 24 } }}>
            <Typography.Text type="secondary">Vai trò</Typography.Text>
            <div style={{ marginTop: 12 }}>
              <Tag color="cyan">{user?.role || '-'}</Tag>
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card className="page-card" styles={{ body: { padding: 28 } }}>
            <Typography.Title level={4} style={{ marginTop: 0 }}>
              Cập nhật thông tin liên hệ
            </Typography.Title>
            <Typography.Paragraph type="secondary">
              Bạn có thể chỉnh lại email và số điện thoại đang dùng cho tài khoản hiện tại.
            </Typography.Paragraph>

            <Form
              form={profileForm}
              layout="vertical"
              onFinish={async (values) => {
                setSavingProfile(true);
                try {
                  await updateProfile(values);
                  message.success('Đã cập nhật thông tin cá nhân.');
                } catch (error) {
                  message.error(error.response?.data?.message || 'Không thể cập nhật hồ sơ.');
                } finally {
                  setSavingProfile(false);
                }
              }}
            >
              <Form.Item
                name="email"
                label="Email"
                rules={[
                  { required: true, message: 'Nhập email' },
                  { type: 'email', message: 'Email không hợp lệ' },
                ]}
              >
                <Input size="large" />
              </Form.Item>
              <Form.Item
                name="phone"
                label="Số điện thoại"
                rules={[{ max: 20, message: 'Số điện thoại quá dài' }]}
              >
                <Input size="large" />
              </Form.Item>
              <Button type="primary" htmlType="submit" loading={savingProfile}>
                Lưu thông tin
              </Button>
            </Form>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card className="page-card" styles={{ body: { padding: 28 } }}>
            <Typography.Title level={4} style={{ marginTop: 0 }}>
              Đổi mật khẩu
            </Typography.Title>
            <Typography.Paragraph type="secondary">
              Mật khẩu mới phải đáp ứng policy bảo mật bên dưới.
            </Typography.Paragraph>

            <Space orientation="vertical" size={8} style={{ width: '100%', marginBottom: 20 }}>
              {passwordRules.map((rule) => (
                <Typography.Text key={rule} type="secondary">
                  {`• ${rule}`}
                </Typography.Text>
              ))}
            </Space>

            <Form
              form={passwordForm}
              layout="vertical"
              onFinish={async (values) => {
                setSavingPassword(true);
                try {
                  await updateProfile({
                    current_password: values.current_password,
                    new_password: values.new_password,
                  });
                  passwordForm.resetFields();
                  message.success('Đổi mật khẩu thành công.');
                } catch (error) {
                  message.error(error.response?.data?.message || 'Không thể đổi mật khẩu.');
                } finally {
                  setSavingPassword(false);
                }
              }}
            >
              <Form.Item
                name="current_password"
                label="Mật khẩu hiện tại"
                rules={[{ required: true, message: 'Nhập mật khẩu hiện tại' }]}
              >
                <Input.Password size="large" />
              </Form.Item>
              <Form.Item
                name="new_password"
                label="Mật khẩu mới"
                rules={[
                  { required: true, message: 'Nhập mật khẩu mới' },
                  { min: 8, message: 'Mật khẩu mới tối thiểu 8 ký tự' },
                  {
                    validator(_, value) {
                      if (!value) {
                        return Promise.resolve();
                      }
                      const hasUpper = /[A-Z]/.test(value);
                      const hasLower = /[a-z]/.test(value);
                      const hasDigit = /\d/.test(value);
                      const hasSpecial = /[^A-Za-z0-9]/.test(value);
                      if (hasUpper && hasLower && hasDigit && hasSpecial) {
                        return Promise.resolve();
                      }
                      return Promise.reject(new Error('Mật khẩu mới chưa đạt policy bảo mật.'));
                    },
                  },
                ]}
              >
                <Input.Password size="large" />
              </Form.Item>
              <Form.Item
                name="confirm_password"
                label="Nhập lại mật khẩu mới"
                dependencies={['new_password']}
                rules={[
                  { required: true, message: 'Nhập lại mật khẩu mới' },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!value || getFieldValue('new_password') === value) {
                        return Promise.resolve();
                      }
                      return Promise.reject(new Error('Mật khẩu nhập lại chưa khớp.'));
                    },
                  }),
                ]}
              >
                <Input.Password size="large" />
              </Form.Item>
              <Button type="primary" htmlType="submit" loading={savingPassword}>
                Đổi mật khẩu
              </Button>
            </Form>
          </Card>
        </Col>
      </Row>
    </Space>
  );
}

export default ProfilePage;
