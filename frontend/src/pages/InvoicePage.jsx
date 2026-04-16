import { CreditCardOutlined, PlusOutlined, PrinterOutlined } from '@ant-design/icons';
import {
  Button,
  Col,
  Form,
  Input,
  InputNumber,
  Modal,
  Row,
  Select,
  Space,
  Table,
  Tabs,
  message,
} from 'antd';
import { useEffect, useState } from 'react';

import api from '../api/client';
import SectionCard from '../components/SectionCard';
import StatusTag from '../components/StatusTag';
import { formatCurrency, formatDateTime } from '../utils/format';

function InvoicePage() {
  const [invoices, setInvoices] = useState([]);
  const [payments, setPayments] = useState([]);
  const [receipts, setReceipts] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [bankAccounts, setBankAccounts] = useState([]);
  const [invoiceOpen, setInvoiceOpen] = useState(false);
  const [paymentOpen, setPaymentOpen] = useState(false);
  const [targetInvoice, setTargetInvoice] = useState(null);
  const [invoiceForm] = Form.useForm();
  const [paymentForm] = Form.useForm();

  const fetchAll = async () => {
    try {
      const [invoiceResponse, paymentResponse, receiptResponse, customerResponse, bankResponse] = await Promise.all([
        api.get('/invoices'),
        api.get('/payments'),
        api.get('/export-receipts'),
        api.get('/customers'),
        api.get('/bank-accounts'),
      ]);
      setInvoices(invoiceResponse.data.items || []);
      setPayments(paymentResponse.data.items || []);
      setReceipts((receiptResponse.data.items || []).filter((item) => item.status === 'confirmed'));
      setCustomers(customerResponse.data.items || []);
      setBankAccounts(bankResponse.data.items || []);
    } catch (error) {
      message.error(error.response?.data?.message || 'Khong tai duoc hoa don.');
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  return (
    <SectionCard
      title="Hoa don va thanh toan"
      subtitle="Lap hoa don tu phieu xuat va ghi nhan doi soat ngan hang thu cong."
      extra={(
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setInvoiceOpen(true)}>
          Tao hoa don
        </Button>
      )}
    >
      <Tabs
        items={[
          {
            key: 'invoices',
            label: 'Hoa don',
            children: (
              <Table
                rowKey="id"
                dataSource={invoices}
                scroll={{ x: 1100 }}
                columns={[
                  { title: 'Ma hoa don', dataIndex: 'invoice_code' },
                  { title: 'Phieu xuat', dataIndex: 'export_receipt_code' },
                  { title: 'Khach hang', dataIndex: 'customer_name' },
                  { title: 'Tong hang', dataIndex: 'total_amount', render: formatCurrency },
                  { title: 'Thue', dataIndex: 'tax_amount', render: formatCurrency },
                  { title: 'Tong thanh toan', dataIndex: 'final_amount', render: formatCurrency },
                  { title: 'Da thanh toan', dataIndex: 'paid_amount', render: formatCurrency },
                  { title: 'Trang thai', dataIndex: 'payment_status', render: (value) => <StatusTag value={value} /> },
                  {
                    title: 'Thao tac',
                    key: 'actions',
                    render: (_, record) => (
                      <Space>
                        <Button
                          icon={<CreditCardOutlined />}
                          onClick={() => {
                            setTargetInvoice(record);
                            paymentForm.resetFields();
                            paymentForm.setFieldsValue({ invoice_id: record.id, amount: record.remaining_amount });
                            setPaymentOpen(true);
                          }}
                        >
                          Ghi nhan thu tien
                        </Button>
                        <Button icon={<PrinterOutlined />} onClick={() => window.print()}>
                          In
                        </Button>
                      </Space>
                    ),
                  },
                ]}
              />
            ),
          },
          {
            key: 'payments',
            label: 'Thanh toan',
            children: (
              <Table
                rowKey="id"
                dataSource={payments}
                columns={[
                  { title: 'Hoa don', dataIndex: 'invoice_code' },
                  { title: 'Ngan hang', dataIndex: 'bank_name' },
                  { title: 'Ma giao dich', dataIndex: 'transfer_code' },
                  { title: 'So tien', dataIndex: 'amount', render: formatCurrency },
                  { title: 'Ngay ghi nhan', dataIndex: 'paid_at', render: formatDateTime },
                  { title: 'Trang thai', dataIndex: 'payment_status', render: (value) => <StatusTag value={value} /> },
                ]}
                scroll={{ x: 960 }}
              />
            ),
          },
        ]}
      />

      <Modal
        title="Tao hoa don"
        open={invoiceOpen}
        onCancel={() => setInvoiceOpen(false)}
        footer={null}
        destroyOnHidden
      >
        <Form
          form={invoiceForm}
          layout="vertical"
          onFinish={async (values) => {
            try {
              await api.post('/invoices', values);
              message.success('Da tao hoa don.');
              setInvoiceOpen(false);
              fetchAll();
            } catch (error) {
              message.error(error.response?.data?.message || 'Khong tao duoc hoa don.');
            }
          }}
        >
          <Form.Item name="export_receipt_id" label="Phieu xuat" rules={[{ required: true }]}>
            <Select options={receipts.map((item) => ({ label: `${item.receipt_code} - ${item.customer_name || 'Khach le'}`, value: item.id }))} />
          </Form.Item>
          <Form.Item name="customer_id" label="Khach hang" rules={[{ required: true }]}>
            <Select options={customers.map((item) => ({ label: item.customer_name, value: item.id }))} />
          </Form.Item>
          <Form.Item name="tax_rate" label="Ty le thue" initialValue={0.1}>
            <InputNumber min={0} max={1} step={0.05} style={{ width: '100%' }} />
          </Form.Item>
          <Space>
            <Button type="primary" htmlType="submit">Luu</Button>
            <Button onClick={() => setInvoiceOpen(false)}>Dong</Button>
          </Space>
        </Form>
      </Modal>

      <Modal
        title={`Ghi nhan thanh toan${targetInvoice ? ` - ${targetInvoice.invoice_code}` : ''}`}
        open={paymentOpen}
        onCancel={() => setPaymentOpen(false)}
        footer={null}
        destroyOnHidden
      >
        <Form
          form={paymentForm}
          layout="vertical"
          onFinish={async (values) => {
            try {
              await api.post('/payments', {
                ...values,
                paid_at: values.paid_at ? new Date(values.paid_at).toISOString() : null,
              });
              message.success('Da ghi nhan thanh toan.');
              setPaymentOpen(false);
              fetchAll();
            } catch (error) {
              message.error(error.response?.data?.message || 'Khong ghi nhan duoc thanh toan.');
            }
          }}
        >
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item name="invoice_id" hidden>
                <Input />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item name="bank_account_id" label="Tai khoan ngan hang" rules={[{ required: true }]}>
                <Select options={bankAccounts.map((item) => ({ label: `${item.bank_name} - ${item.account_number}`, value: item.id }))} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="transfer_code" label="Ma giao dich" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="amount" label="So tien" rules={[{ required: true }]}>
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item name="paid_at" label="Ngay thanh toan">
                <Input type="datetime-local" />
              </Form.Item>
            </Col>
          </Row>
          <Space>
            <Button type="primary" htmlType="submit">Luu</Button>
            <Button onClick={() => setPaymentOpen(false)}>Dong</Button>
          </Space>
        </Form>
      </Modal>
    </SectionCard>
  );
}

export default InvoicePage;
