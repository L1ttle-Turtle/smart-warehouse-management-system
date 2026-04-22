import { Card, Col, Empty, Row, Space, Table, Tabs, Typography, message } from 'antd';
import { useEffect, useMemo, useState } from 'react';

import api from '../api/client';
import SectionCard from '../components/SectionCard';
import StatusTag from '../components/StatusTag';
import { formatDateTime, formatNumber } from '../utils/format';

function InventoryPage() {
  const [loading, setLoading] = useState(false);
  const [inventory, setInventory] = useState([]);
  const [movements, setMovements] = useState([]);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.get('/inventory'),
      api.get('/inventory/movements'),
    ])
      .then(([inventoryResponse, movementResponse]) => {
        setInventory(inventoryResponse.data.items || []);
        setMovements(movementResponse.data.items || []);
      })
      .catch((error) => {
        message.error(error.response?.data?.message || 'Không tải được dữ liệu tồn kho.');
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const summary = useMemo(() => {
    const warehouseCodes = new Set(inventory.map((item) => item.warehouse_code).filter(Boolean));
    const productCodes = new Set(inventory.map((item) => item.product_code).filter(Boolean));
    const totalQuantity = inventory.reduce((sum, item) => sum + Number(item.quantity || 0), 0);

    return {
      warehouseCount: warehouseCodes.size,
      productCount: productCodes.size,
      totalQuantity,
      movementCount: movements.length,
    };
  }, [inventory, movements]);

  return (
    <Space direction="vertical" size={18} style={{ width: '100%' }}>
      <Card className="page-card" styles={{ body: { padding: 28 } }}>
        <Space direction="vertical" size={10} style={{ width: '100%' }}>
          <Typography.Text className="resource-eyebrow">
            Module 5-6 · Tồn kho đọc dữ liệu thật
          </Typography.Text>
          <Typography.Title level={2} className="page-title">
            Tồn kho và biến động kho
          </Typography.Title>
          <Typography.Paragraph className="page-subtitle" style={{ marginBottom: 0 }}>
            Theo dõi nhanh tình hình tồn kho theo từng vị trí lưu trữ và xem lại lịch sử biến động
            đã phát sinh từ dữ liệu demo thực tế trong hệ thống.
          </Typography.Paragraph>
        </Space>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12} xl={6}>
          <Card className="page-card" styles={{ body: { padding: 20 } }}>
            <Typography.Text type="secondary">Số kho có dữ liệu</Typography.Text>
            <div className="metric-value">{formatNumber(summary.warehouseCount)}</div>
            <Typography.Text type="secondary">Tính theo tồn kho hiện tại</Typography.Text>
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="page-card" styles={{ body: { padding: 20 } }}>
            <Typography.Text type="secondary">Sản phẩm có tồn</Typography.Text>
            <div className="metric-value">{formatNumber(summary.productCount)}</div>
            <Typography.Text type="secondary">Đã phân bổ vào vị trí kho</Typography.Text>
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="page-card" styles={{ body: { padding: 20 } }}>
            <Typography.Text type="secondary">Tổng số lượng đang lưu</Typography.Text>
            <div className="metric-value">{formatNumber(summary.totalQuantity)}</div>
            <Typography.Text type="secondary">Tổng cộng mọi dòng tồn kho</Typography.Text>
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="page-card" styles={{ body: { padding: 20 } }}>
            <Typography.Text type="secondary">Lịch sử biến động</Typography.Text>
            <div className="metric-value">{formatNumber(summary.movementCount)}</div>
            <Typography.Text type="secondary">Dùng để truy vết kiểm kê</Typography.Text>
          </Card>
        </Col>
      </Row>

      <SectionCard
        title="Theo dõi tồn kho"
        subtitle="Trang này chỉ đọc dữ liệu từ hệ thống hiện tại, chưa mở write flow nhập, xuất hay điều chuyển."
      >
        <Tabs
          items={[
            {
              key: 'inventory',
              label: 'Tồn hiện tại',
              children: (
                <Table
                  rowKey="id"
                  loading={loading}
                  dataSource={inventory}
                  columns={[
                    { title: 'Kho', dataIndex: 'warehouse_name' },
                    { title: 'Vị trí', dataIndex: 'location_name' },
                    { title: 'Mã hàng', dataIndex: 'product_code' },
                    { title: 'Tên hàng', dataIndex: 'product_name' },
                    {
                      title: 'Số lượng',
                      dataIndex: 'quantity',
                      render: (value) => formatNumber(value),
                    },
                    {
                      title: 'Cập nhật gần nhất',
                      dataIndex: 'updated_at',
                      render: formatDateTime,
                    },
                  ]}
                  scroll={{ x: 1080 }}
                  locale={{
                    emptyText: (
                      <Empty
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        description="Chưa có dữ liệu tồn kho để hiển thị."
                      />
                    ),
                  }}
                />
              ),
            },
            {
              key: 'movement',
              label: 'Lịch sử biến động',
              children: (
                <Table
                  rowKey="id"
                  loading={loading}
                  dataSource={movements}
                  columns={[
                    { title: 'Thời gian', dataIndex: 'created_at', render: formatDateTime },
                    { title: 'Kho', dataIndex: 'warehouse_name' },
                    { title: 'Vị trí', dataIndex: 'location_name' },
                    { title: 'Sản phẩm', dataIndex: 'product_name' },
                    {
                      title: 'Loại biến động',
                      dataIndex: 'movement_type',
                      render: (value) => <StatusTag value={value} />,
                    },
                    {
                      title: 'Nguồn tham chiếu',
                      dataIndex: 'reference_type',
                      render: (value) => value || '-',
                    },
                    {
                      title: 'Trước',
                      dataIndex: 'quantity_before',
                      render: (value) => formatNumber(value),
                    },
                    {
                      title: 'Biến động',
                      dataIndex: 'quantity_change',
                      render: (value) => formatNumber(value),
                    },
                    {
                      title: 'Sau',
                      dataIndex: 'quantity_after',
                      render: (value) => formatNumber(value),
                    },
                    {
                      title: 'Người thực hiện',
                      dataIndex: 'performer_name',
                      render: (value) => value || '-',
                    },
                  ]}
                  scroll={{ x: 1360 }}
                  locale={{
                    emptyText: (
                      <Empty
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        description="Chưa có lịch sử biến động kho."
                      />
                    ),
                  }}
                />
              ),
            },
          ]}
        />
      </SectionCard>
    </Space>
  );
}

export default InventoryPage;
