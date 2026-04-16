import { Card, Space, Typography } from 'antd';

function SectionCard({ title, subtitle, extra, children }) {
  return (
    <Card
      className="page-card"
      extra={extra}
      styles={{ body: { padding: 20 } }}
      title={(
        <Space orientation="vertical" size={0}>
          <Typography.Title level={4} style={{ margin: 0 }}>
            {title}
          </Typography.Title>
          {subtitle ? <Typography.Text type="secondary">{subtitle}</Typography.Text> : null}
        </Space>
      )}
    >
      {children}
    </Card>
  );
}

export default SectionCard;
