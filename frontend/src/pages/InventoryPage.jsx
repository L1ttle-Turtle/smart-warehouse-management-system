import { Tabs, Table, message } from 'antd';
import { useEffect, useState } from 'react';

import api from '../api/client';
import SectionCard from '../components/SectionCard';
import StatusTag from '../components/StatusTag';
import { formatDateTime } from '../utils/format';

function InventoryPage() {
  const [inventory, setInventory] = useState([]);
  const [lowStock, setLowStock] = useState([]);
  const [movements, setMovements] = useState([]);

  useEffect(() => {
    Promise.all([
      api.get('/inventory'),
      api.get('/inventory/low-stock'),
      api.get('/inventory/movements'),
    ])
      .then(([inventoryResponse, lowStockResponse, movementResponse]) => {
        setInventory(inventoryResponse.data.items || []);
        setLowStock(lowStockResponse.data.items || []);
        setMovements(movementResponse.data.items || []);
      })
      .catch((error) => {
        message.error(error.response?.data?.message || 'Khong tai duoc ton kho.');
      });
  }, []);

  return (
    <SectionCard
      title="Ton kho theo vi tri"
      subtitle="Theo doi ton hien tai, hang can bo sung va lich su bien dong kho."
    >
      <Tabs
        items={[
          {
            key: 'inventory',
            label: 'Ton hien tai',
            children: (
              <Table
                rowKey="id"
                dataSource={inventory}
                columns={[
                  { title: 'Kho', dataIndex: 'warehouse_name' },
                  { title: 'Vi tri', dataIndex: 'location_name' },
                  { title: 'Ma hang', dataIndex: 'product_code' },
                  { title: 'Ten hang', dataIndex: 'product_name' },
                  { title: 'So luong', dataIndex: 'quantity' },
                ]}
                scroll={{ x: 960 }}
              />
            ),
          },
          {
            key: 'low-stock',
            label: 'Canh bao ton thap',
            children: (
              <Table
                rowKey="id"
                dataSource={lowStock}
                columns={[
                  { title: 'Ma hang', dataIndex: 'product_code' },
                  { title: 'Ten hang', dataIndex: 'product_name' },
                  { title: 'Ton tong', dataIndex: 'quantity_total' },
                  { title: 'Min stock', dataIndex: 'min_stock' },
                  { title: 'Trang thai', dataIndex: 'status', render: (value) => <StatusTag value={value} /> },
                ]}
                scroll={{ x: 900 }}
              />
            ),
          },
          {
            key: 'movement',
            label: 'Lich su movement',
            children: (
              <Table
                rowKey="id"
                dataSource={movements}
                columns={[
                  { title: 'Thoi gian', dataIndex: 'created_at', render: formatDateTime },
                  { title: 'Kho', dataIndex: 'warehouse_name' },
                  { title: 'Vi tri', dataIndex: 'location_name' },
                  { title: 'San pham', dataIndex: 'product_name' },
                  { title: 'Loai', dataIndex: 'movement_type', render: (value) => <StatusTag value={value} /> },
                  { title: 'Truoc', dataIndex: 'quantity_before' },
                  { title: 'Bien dong', dataIndex: 'quantity_change' },
                  { title: 'Sau', dataIndex: 'quantity_after' },
                ]}
                scroll={{ x: 1100 }}
              />
            ),
          },
        ]}
      />
    </SectionCard>
  );
}

export default InventoryPage;
