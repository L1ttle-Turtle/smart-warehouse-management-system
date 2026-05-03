import { Col, Row, Table, message } from 'antd';
import { Bar, BarChart, CartesianGrid, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useEffect, useState } from 'react';

import api from '../api/client';
import SectionCard from '../components/SectionCard';
import { formatCurrency } from '../utils/format';

const chartColors = {
  primary: '#7c3aed',
  success: '#10b981',
  warning: '#f59e0b',
  danger: '#ef4444',
  teal: '#14b8a6',
};

const paymentStatusLabels = {
  unpaid: 'Chưa thanh toán',
  partial: 'Thanh toán một phần',
  paid: 'Đã thanh toán',
  cancelled: 'Đã hủy',
};

function getPaymentStatusLabel(status) {
  return paymentStatusLabels[status] || status || '-';
}

function ReportsPage() {
  const [inventoryData, setInventoryData] = useState([]);
  const [stockMovement, setStockMovement] = useState([]);
  const [topProducts, setTopProducts] = useState([]);
  const [shipmentPerformance, setShipmentPerformance] = useState([]);
  const [revenue, setRevenue] = useState([]);
  const [paymentStatus, setPaymentStatus] = useState([]);

  useEffect(() => {
    Promise.all([
      api.get('/reports/inventory-by-warehouse'),
      api.get('/reports/stock-movement'),
      api.get('/reports/top-products'),
      api.get('/reports/shipment-performance'),
      api.get('/reports/revenue'),
    ])
      .then(([inventoryResponse, stockResponse, topResponse, shipmentResponse, revenueResponse]) => {
        setInventoryData(inventoryResponse.data.items || []);
        setStockMovement(stockResponse.data.items || []);
        setTopProducts(topResponse.data.items || []);
        setShipmentPerformance(shipmentResponse.data.items || []);
        setRevenue(revenueResponse.data.revenue || []);
        setPaymentStatus(revenueResponse.data.payment_status || []);
      })
      .catch((error) => {
        message.error(error.response?.data?.message || 'Không tải được dữ liệu báo cáo.');
      });
  }, []);

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={12}>
        <SectionCard
          title="Tồn kho theo kho"
          subtitle="Tổng số lượng tồn hiện tại, gom theo từng kho để nhìn nhanh năng lực lưu trữ."
        >
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={inventoryData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="warehouse_name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="quantity" fill={chartColors.primary} />
            </BarChart>
          </ResponsiveContainer>
        </SectionCard>
      </Col>
      <Col xs={24} xl={12}>
        <SectionCard
          title="Nhập xuất theo tháng"
          subtitle="Tổng biến động tăng/giảm tồn kho từ movement history theo từng tháng."
        >
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={stockMovement}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="import_quantity" name="Nhập/tăng tồn" fill={chartColors.success} />
              <Bar dataKey="export_quantity" name="Xuất/giảm tồn" fill={chartColors.warning} />
            </BarChart>
          </ResponsiveContainer>
        </SectionCard>
      </Col>
      <Col xs={24} xl={12}>
        <SectionCard
          title="Trạng thái vận chuyển"
          subtitle="Tỷ lệ shipment theo trạng thái hiện tại để demo luồng giao hàng."
        >
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={shipmentPerformance}
                dataKey="count"
                nameKey="status_label"
                outerRadius={100}
                fill={chartColors.teal}
                label
              />
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </SectionCard>
      </Col>
      <Col xs={24} xl={12}>
        <SectionCard
          title="Doanh thu hóa đơn"
          subtitle="Tổng giá trị hóa đơn theo tháng, phục vụ câu chuyện demo Module 8."
        >
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={revenue}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip formatter={(value) => formatCurrency(value)} />
              <Bar dataKey="revenue" name="Doanh thu" fill={chartColors.danger} />
            </BarChart>
          </ResponsiveContainer>
        </SectionCard>
      </Col>
      <Col span={24}>
        <SectionCard
          title="Top hàng hóa và thanh toán"
          subtitle="Bảng tóm tắt sản phẩm xuất nhiều nhất và trạng thái thu tiền của hóa đơn."
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} xl={14}>
              <Table
                rowKey="product_id"
                dataSource={topProducts}
                pagination={false}
                columns={[
                  { title: 'Sản phẩm', dataIndex: 'product_name' },
                  { title: 'Số lượng xuất', dataIndex: 'quantity' },
                ]}
              />
            </Col>
            <Col xs={24} xl={10}>
              <Table
                rowKey="status"
                dataSource={paymentStatus}
                pagination={false}
                columns={[
                  {
                    title: 'Trạng thái',
                    dataIndex: 'status',
                    render: (value) => getPaymentStatusLabel(value),
                  },
                  { title: 'Số hóa đơn', dataIndex: 'count' },
                ]}
              />
            </Col>
          </Row>
        </SectionCard>
      </Col>
    </Row>
  );
}

export default ReportsPage;
