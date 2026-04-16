import { Card, Space, Typography } from 'antd';

function MetricCard({ title, value, suffix, description }) {
  return (
    <Card className="page-card" styles={{ body: { padding: 20 } }}>
      <Space orientation="vertical" size={4}>
        <Typography.Text className="metric-label">{title}</Typography.Text>
        <Typography.Text className="metric-value">
          {value}
          {suffix ? ` ${suffix}` : ''}
        </Typography.Text>
        {description ? <Typography.Text type="secondary">{description}</Typography.Text> : null}
      </Space>
    </Card>
  );
}

export default MetricCard;
