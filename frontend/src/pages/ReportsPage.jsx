import { Col, Row, Table, message } from 'antd';
import { Bar, BarChart, CartesianGrid, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useEffect, useState } from 'react';

import api from '../api/client';
import SectionCard from '../components/SectionCard';
import { formatCurrency } from '../utils/format';

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
        message.error(error.response?.data?.message || 'Khong tai duoc bao cao.');
      });
  }, []);

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={12}>
        <SectionCard title="Ton kho theo kho">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={inventoryData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="warehouse_name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="quantity" fill="#1f6f5f" />
            </BarChart>
          </ResponsiveContainer>
        </SectionCard>
      </Col>
      <Col xs={24} xl={12}>
        <SectionCard title="Nhap xuat theo thang">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={stockMovement}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="import_quantity" fill="#1f6f5f" />
              <Bar dataKey="export_quantity" fill="#d49727" />
            </BarChart>
          </ResponsiveContainer>
        </SectionCard>
      </Col>
      <Col xs={24} xl={12}>
        <SectionCard title="Ty le van don">
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={shipmentPerformance} dataKey="count" nameKey="status" outerRadius={100} fill="#2d8470" label />
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </SectionCard>
      </Col>
      <Col xs={24} xl={12}>
        <SectionCard title="Doanh thu">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={revenue}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip formatter={(value) => formatCurrency(value)} />
              <Bar dataKey="revenue" fill="#b86a3d" />
            </BarChart>
          </ResponsiveContainer>
        </SectionCard>
      </Col>
      <Col span={24}>
        <SectionCard title="Top hang hoa va thanh toan">
          <Row gutter={[16, 16]}>
            <Col xs={24} xl={14}>
              <Table
                rowKey="product_id"
                dataSource={topProducts}
                pagination={false}
                columns={[
                  { title: 'San pham', dataIndex: 'product_name' },
                  { title: 'So luong xuat', dataIndex: 'quantity' },
                ]}
              />
            </Col>
            <Col xs={24} xl={10}>
              <Table
                rowKey="status"
                dataSource={paymentStatus}
                pagination={false}
                columns={[
                  { title: 'Trang thai', dataIndex: 'status' },
                  { title: 'So hoa don', dataIndex: 'count' },
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
