import { Card, Space, Typography } from 'antd';

function SectionCard({ title, subtitle, extra, children }) {
  return (
    <Card
      className="page-card"
      extra={extra}
      styles={{ body: { padding: 22 } }}
      title={(
        <Space className="section-card-heading" orientation="vertical" size={2}>
          <Typography.Title className="section-card-title" level={4}>
            {title}
          </Typography.Title>
          {subtitle ? <Typography.Text className="section-card-subtitle">{subtitle}</Typography.Text> : null}
        </Space>
      )}
    >
      {children}
    </Card>
  );
}

export default SectionCard;
