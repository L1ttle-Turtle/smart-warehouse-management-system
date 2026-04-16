import { Button, Card, Result } from 'antd';
import { useNavigate } from 'react-router-dom';

function ForbiddenPage() {
  const navigate = useNavigate();

  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 24 }}>
      <Card className="page-card" styles={{ body: { padding: 28, width: 'min(100%, 680px)' } }}>
        <Result
          status="403"
          title="403"
          subTitle="Tài khoản hiện tại không có quyền truy cập màn hình này."
          extra={[
            <Button key="home" type="primary" onClick={() => navigate('/')}>
              Quay về tổng quan
            </Button>,
          ]}
        />
      </Card>
    </div>
  );
}

export default ForbiddenPage;
