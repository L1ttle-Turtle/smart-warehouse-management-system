import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import {
  Alert,
  Button,
  Card,
  Col,
  Divider,
  Drawer,
  Empty,
  Form,
  Input,
  InputNumber,
  Popconfirm,
  Row,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';

import api from '../api/client';
import { useAuth } from '../auth/useAuth';
import SectionCard from '../components/SectionCard';
import StatusTag from '../components/StatusTag';
import { resourceConfig } from '../config/resources';

const STATUS_FILTER_OPTIONS = [
  { label: 'Tất cả trạng thái', value: 'all' },
  { label: 'Đang hoạt động', value: 'active' },
  { label: 'Ngừng hoạt động', value: 'inactive' },
];

function groupFields(fields) {
  return fields.reduce((sections, field) => {
    const sectionName = field.section || 'Thông tin chung';
    const section = sections.find((item) => item.title === sectionName);
    if (section) {
      section.fields.push(field);
      return sections;
    }

    sections.push({
      key: sectionName,
      title: sectionName,
      description: field.sectionDescription || null,
      fields: [field],
    });
    return sections;
  }, []);
}

function buildSelectOptions(field, optionsMap) {
  if (field.options?.static) {
    return field.options.static;
  }

  return (optionsMap[field.options?.endpoint] || []).map((item) => ({
    label: field.options?.labelFormatter
      ? field.options.labelFormatter(item)
      : item[field.options?.labelField || 'label'],
    value: item[field.options?.valueField || 'value'],
  }));
}

function CreatableSelectField({ field, optionsMap, onCreateOption }) {
  const [searchValue, setSearchValue] = useState('');
  const [creating, setCreating] = useState(false);
  const options = buildSelectOptions(field, optionsMap);
  const trimmedSearch = searchValue.trim();
  const hasExactOption = options.some((option) => (
    String(option.label).toLowerCase() === trimmedSearch.toLowerCase()
    || String(option.value).toLowerCase() === trimmedSearch.toLowerCase()
  ));
  const canCreate = Boolean(field.options?.createEndpoint && trimmedSearch && !hasExactOption);

  return (
    <Select
      allowClear
      showSearch
      optionFilterProp="label"
      placeholder={field.placeholder}
      options={options}
      onSearch={setSearchValue}
      popupRender={(menu) => (
        <>
          {menu}
          {canCreate ? (
            <>
              <Divider style={{ margin: '8px 0' }} />
              <Button
                block
                type="text"
                icon={<PlusOutlined />}
                loading={creating}
                onMouseDown={(event) => event.preventDefault()}
                onClick={async () => {
                  setCreating(true);
                  try {
                    const createdValue = await onCreateOption(field, trimmedSearch);
                    if (createdValue !== null && createdValue !== undefined) {
                      setSearchValue('');
                    }
                  } finally {
                    setCreating(false);
                  }
                }}
              >
                {field.options?.createLabel || 'Thêm lựa chọn mới'} "{trimmedSearch}"
              </Button>
            </>
          ) : null}
        </>
      )}
    />
  );
}

function renderField(field, optionsMap, onCreateOption) {
  if (field.type === 'textarea') {
    return <Input.TextArea rows={4} allowClear placeholder={field.placeholder} />;
  }

  if (field.type === 'number') {
    return <InputNumber style={{ width: '100%' }} min={0} controls={false} placeholder={field.placeholder} />;
  }

  if (field.type === 'password') {
    return <Input.Password placeholder={field.placeholder} />;
  }

  if (field.type === 'select') {
    if (field.options?.createEndpoint) {
      return (
        <CreatableSelectField
          field={field}
          optionsMap={optionsMap}
          onCreateOption={onCreateOption}
        />
      );
    }

    return (
      <Select
        allowClear
        showSearch
        optionFilterProp="label"
        placeholder={field.placeholder}
        options={buildSelectOptions(field, optionsMap)}
      />
    );
  }

  if (field.type === 'datetime') {
    return <Input type="datetime-local" placeholder={field.placeholder} />;
  }

  return <Input allowClear placeholder={field.placeholder} />;
}

function renderToolbarFilter(filter, value, onChange, optionsMap) {
  if (filter.type === 'select') {
    return (
      <Select
        allowClear
        value={value}
        onChange={(nextValue) => onChange(filter.name, nextValue)}
        options={buildSelectOptions(filter, optionsMap)}
        placeholder={filter.placeholder}
        style={{ width: filter.width || 220 }}
      />
    );
  }

  return null;
}

function ResourcePage({ resourceKey: resourceKeyProp = null }) {
  const { resourceKey: resourceKeyParam } = useParams();
  const { hasPermission } = useAuth();
  const resourceKey = resourceKeyProp || resourceKeyParam;
  const config = resourceConfig[resourceKey];
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [optionsMap, setOptionsMap] = useState({});
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [extraFilters, setExtraFilters] = useState({});
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: config?.defaultPageSize || 10,
    total: 0,
  });
  const [sorterState, setSorterState] = useState({
    field: config?.defaultSort?.field || null,
    order: config?.defaultSort?.order || null,
  });
  const [form] = Form.useForm();

  const managePermission = useMemo(() => {
    if (!config) {
      return null;
    }

    return config.managePermission
      || (config.permission.endsWith('.view') ? config.permission.replace('.view', '.manage') : config.permission);
  }, [config]);

  const canManage = useMemo(() => {
    if (!managePermission) {
      return false;
    }
    return hasPermission(managePermission);
  }, [hasPermission, managePermission]);

  const supportsStatusFilter = useMemo(
    () => Boolean(config?.fields.some((field) => field.name === 'status')),
    [config],
  );

  const formSections = useMemo(() => groupFields(config?.fields || []), [config]);
  const serverSide = Boolean(config?.serverSide);
  const toolbarFilters = useMemo(() => config?.listFilters || [], [config]);
  const currentPage = pagination.current;
  const currentPageSize = pagination.pageSize;

  const metricCards = useMemo(() => {
    if (!config) {
      return [];
    }
    if (serverSide) {
      return [
        {
          label: 'Tổng bản ghi',
          value: pagination.total,
          tone: 'primary',
          helper: 'Sau khi áp dụng bộ lọc hiện tại',
        },
        {
          label: 'Đang hiển thị',
          value: items.length,
          tone: 'success',
          helper: `Trang ${pagination.current}`,
        },
        {
          label: 'Kích thước trang',
          value: pagination.pageSize,
          tone: 'warning',
          helper: 'Số bản ghi mỗi lần tải',
        },
      ];
    }

    return (config.metrics || []).map((metric) => ({ ...metric, value: metric.getValue(items) }));
  }, [config, items, pagination, serverSide]);

  const defaultFormValues = useMemo(
    () => Object.fromEntries(
      (config?.fields || [])
        .filter((field) => Object.prototype.hasOwnProperty.call(field, 'initialValue'))
        .map((field) => [field.name, field.initialValue]),
    ),
    [config],
  );

  useEffect(() => {
    if (!config) {
      return;
    }

    const optionEndpoints = new Set();

    if (canManage) {
      config.fields
        .filter((field) => field.type === 'select' && field.options?.endpoint)
        .forEach((field) => optionEndpoints.add(field.options.endpoint));
    }

    toolbarFilters
      .filter((filter) => filter.type === 'select' && filter.options?.endpoint)
      .forEach((filter) => optionEndpoints.add(filter.options.endpoint));

    const endpoints = [...optionEndpoints];
    if (!endpoints.length) {
      setOptionsMap({});
      return;
    }

    Promise.all(endpoints.map((endpoint) => api.get(endpoint)))
      .then((responses) => {
        const nextOptions = {};
        endpoints.forEach((endpoint, index) => {
          nextOptions[endpoint] = responses[index].data.items || [];
        });
        setOptionsMap(nextOptions);
      })
      .catch(() => {
        message.error('Không tải được dữ liệu phụ trợ cho bộ lọc hoặc biểu mẫu.');
      });
  }, [canManage, config, toolbarFilters]);

  const handleCreateSelectOption = useCallback(async (field, label) => {
    try {
      const payloadKey = field.options?.createPayloadKey || 'name';
      const response = await api.post(field.options.createEndpoint, { [payloadKey]: label });
      const createdItem = response.data.item;
      const endpoint = field.options.endpoint;
      const valueField = field.options?.valueField || 'value';
      const createdValue = createdItem?.[valueField];

      setOptionsMap((current) => ({
        ...current,
        [endpoint]: [...(current[endpoint] || []), createdItem],
      }));
      form.setFieldsValue({ [field.name]: createdValue });
      message.success(`Đã thêm vai trò "${createdItem?.role_name || label}".`);
      return createdValue;
    } catch (error) {
      message.error(error.response?.data?.message || 'Không thể thêm lựa chọn mới.');
      return null;
    }
  }, [form]);

  const fetchItems = useCallback(async () => {
    if (!config) {
      return;
    }

    setLoading(true);
    try {
      const params = {};
      if (serverSide) {
        params.page = currentPage;
        params.page_size = currentPageSize;
        if (searchQuery) {
          params.search = searchQuery;
        }
        if (supportsStatusFilter && statusFilter !== 'all') {
          params.status = statusFilter;
        }
        toolbarFilters.forEach((filter) => {
          const value = extraFilters[filter.name];
          if (value !== undefined && value !== null && value !== '') {
            params[filter.name] = value;
          }
        });
        if (sorterState.field) {
          params.sort_by = sorterState.field;
        }
        if (sorterState.order) {
          params.sort_order = sorterState.order === 'ascend' ? 'asc' : 'desc';
        }
      }

      const response = await api.get(config.endpoint, { params });
      const nextItems = response.data.items || [];
      setItems(nextItems);

      if (serverSide) {
        setPagination((current) => ({
          ...current,
          total: response.data.total || 0,
          current: response.data.page || current.current,
          pageSize: response.data.page_size || current.pageSize,
        }));
      }
    } catch (error) {
      message.error(error.response?.data?.message || 'Không tải được dữ liệu.');
    } finally {
      setLoading(false);
    }
  }, [
    config,
    currentPage,
    currentPageSize,
    extraFilters,
    searchQuery,
    serverSide,
    sorterState.field,
    sorterState.order,
    statusFilter,
    supportsStatusFilter,
    toolbarFilters,
  ]);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  const handleCloseDrawer = () => {
    setOpen(false);
    setEditingItem(null);
    form.resetFields();
  };

  const handleCreate = () => {
    setEditingItem(null);
    form.resetFields();
    form.setFieldsValue(defaultFormValues);
    setOpen(true);
  };

  const handleEdit = (record) => {
    setEditingItem(record);
    form.setFieldsValue(
      Object.fromEntries(
        config.fields.map((field) => {
          let value = record[field.name];
          if (field.type === 'datetime' && value) {
            value = dayjs(value).format('YYYY-MM-DDTHH:mm');
          }
          return [field.name, value];
        }),
      ),
    );
    setOpen(true);
  };

  if (!config) {
    return <Typography.Text>Không tìm thấy cấu hình của trang này.</Typography.Text>;
  }

  const columns = [
    ...config.columns.map((column) => ({
      ...column,
      sorter: column.sortable ? true : false,
      render: column.type === 'status'
        ? (value) => <StatusTag value={value} />
        : column.render
          ? (value, record) => column.render(value, record)
          : undefined,
    })),
    ...(canManage
      ? [
          {
            title: 'Thao tác',
            key: 'action',
            width: 180,
            render: (_, record) => (
              <Space wrap>
                <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
                  Chỉnh sửa
                </Button>
                <Popconfirm
                  title="Xóa bản ghi này?"
                  description="Thao tác này không thể hoàn tác."
                  okText="Xóa"
                  cancelText="Hủy"
                  onConfirm={async () => {
                    try {
                      await api.delete(`${config.endpoint}/${record.id}`);
                      message.success('Đã xóa bản ghi.');
                      fetchItems();
                    } catch (error) {
                      message.error(error.response?.data?.message || 'Không thể xóa bản ghi.');
                    }
                  }}
                >
                  <Button size="small" danger icon={<DeleteOutlined />}>
                    Xóa
                  </Button>
                </Popconfirm>
              </Space>
            ),
          },
        ]
      : []),
  ];

  return (
    <Space orientation="vertical" size={18} style={{ width: '100%' }}>
      <Card className="page-card resource-hero" styles={{ body: { padding: 28 } }}>
        <div className="resource-hero__content">
          <div className="resource-hero__main">
            <Typography.Text className="resource-eyebrow">
              {config.eyebrow || 'Quản trị dữ liệu nội bộ'}
            </Typography.Text>
            <Typography.Title level={2} className="page-title">
              {config.title}
            </Typography.Title>
            <Typography.Paragraph className="page-subtitle">
              {config.subtitle}
            </Typography.Paragraph>
            {config.tips?.length ? (
              <Space wrap size={[8, 8]}>
                {config.tips.map((tip) => (
                  <Tag key={tip} className="resource-tip">
                    {tip}
                  </Tag>
                ))}
              </Space>
            ) : null}
          </div>
          {canManage ? (
            <Button type="primary" size="large" icon={<PlusOutlined />} onClick={handleCreate}>
              {config.createLabel || 'Tạo mới'}
            </Button>
          ) : null}
        </div>

        {metricCards.length ? (
          <Row gutter={[16, 16]} className="resource-stats">
            {metricCards.map((metric) => (
              <Col xs={24} md={8} key={metric.label}>
                <Card className={`page-card resource-stat resource-stat--${metric.tone || 'default'}`} styles={{ body: { padding: 20 } }}>
                  <Typography.Text type="secondary">{metric.label}</Typography.Text>
                  <div className="metric-value">{metric.value}</div>
                  {metric.helper ? (
                    <Typography.Text type="secondary">
                      {metric.helper}
                    </Typography.Text>
                  ) : null}
                </Card>
              </Col>
            ))}
          </Row>
        ) : null}
      </Card>

      <SectionCard
        title={config.listTitle || `Danh sách ${config.title.toLowerCase()}`}
        subtitle={serverSide ? `${pagination.total} bản ghi phù hợp` : `${items.length} bản ghi đang hiển thị`}
        extra={canManage ? (
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            {config.createLabel || 'Tạo mới'}
          </Button>
        ) : null}
      >
        <div className="section-toolbar resource-toolbar">
          <Space wrap size={12}>
            <Input.Search
              allowClear
              enterButton="Tìm"
              prefix={<SearchOutlined />}
              placeholder={config.searchPlaceholder || 'Tìm nhanh dữ liệu'}
              value={searchInput}
              onChange={(event) => {
                const value = event.target.value;
                setSearchInput(value);
                if (!value) {
                  setSearchQuery('');
                  setPagination((current) => ({ ...current, current: 1 }));
                }
              }}
              onSearch={(value) => {
                setSearchQuery(value.trim());
                setPagination((current) => ({ ...current, current: 1 }));
              }}
              style={{ width: 320, maxWidth: '100%' }}
            />
            {supportsStatusFilter ? (
              <Select
                value={statusFilter}
                onChange={(value) => {
                  setStatusFilter(value);
                  setPagination((current) => ({ ...current, current: 1 }));
                }}
                options={STATUS_FILTER_OPTIONS}
                style={{ width: 190 }}
              />
            ) : null}
            {toolbarFilters.map((filter) => (
              <div key={filter.name}>
                {renderToolbarFilter(
                  filter,
                  extraFilters[filter.name],
                  (name, value) => {
                    setExtraFilters((current) => ({ ...current, [name]: value }));
                    setPagination((current) => ({ ...current, current: 1 }));
                  },
                  optionsMap,
                )}
              </div>
            ))}
            <Button icon={<ReloadOutlined />} onClick={fetchItems}>
              Làm mới
            </Button>
          </Space>
          <Typography.Text type="secondary">
            {config.toolbarHint || 'Bạn có thể tìm kiếm nhanh theo từ khóa hoặc lọc theo trạng thái.'}
          </Typography.Text>
        </div>

        <Table
          rowKey="id"
          columns={columns}
          dataSource={items}
          loading={loading}
          scroll={{ x: 960 }}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: serverSide ? pagination.total : items.length,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '50', '100'],
          }}
          onChange={(nextPagination, _filters, sorter) => {
            setPagination((current) => ({
              ...current,
              current: nextPagination.current || 1,
              pageSize: nextPagination.pageSize || current.pageSize,
            }));

            const sorterObject = Array.isArray(sorter) ? sorter[0] : sorter;
            const sorterField = sorterObject?.column?.sorterKey || sorterObject?.field || null;
            const sorterOrder = sorterObject?.order || null;
            setSorterState({
              field: sorterField,
              order: sorterOrder,
            });
          }}
          locale={{
            emptyText: (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={config.emptyDescription || 'Chưa có dữ liệu phù hợp với bộ lọc hiện tại.'}
              />
            ),
          }}
        />
      </SectionCard>

      <Drawer
        open={open}
        onClose={handleCloseDrawer}
        size={760}
        destroyOnClose
        title={(
          <Space orientation="vertical" size={2}>
            <Typography.Title level={4} style={{ margin: 0 }}>
              {editingItem ? (config.editLabel || `Chỉnh sửa ${config.title.toLowerCase()}`) : (config.createLabel || `Tạo ${config.title.toLowerCase()}`)}
            </Typography.Title>
            <Typography.Text type="secondary">
              {editingItem
                ? 'Cập nhật thông tin và lưu lại để thay đổi có hiệu lực ngay.'
                : 'Điền đầy đủ thông tin cần thiết để tạo mới bản ghi.'}
            </Typography.Text>
          </Space>
        )}
      >
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          <Alert
            showIcon
            type={editingItem ? 'info' : 'success'}
            message={editingItem ? 'Bạn đang chỉnh sửa dữ liệu hiện có' : 'Bạn đang tạo mới dữ liệu'}
            description={config.drawerDescription || 'Các trường có dấu * là bắt buộc. Bạn có thể lưu ngay khi hoàn tất biểu mẫu.'}
          />

          <Form
            form={form}
            layout="vertical"
            onFinish={async (values) => {
              const payload = Object.fromEntries(
                Object.entries(values).map(([key, value]) => [key, value === undefined ? null : value]),
              );

              config.fields.forEach((field) => {
                if (field.type === 'datetime' && payload[field.name]) {
                  payload[field.name] = new Date(payload[field.name]).toISOString();
                }
              });

              setSubmitting(true);
              try {
                if (editingItem) {
                  await api.put(`${config.endpoint}/${editingItem.id}`, payload);
                  message.success('Cập nhật thành công.');
                } else {
                  await api.post(config.endpoint, payload);
                  message.success('Tạo mới thành công.');
                }
                handleCloseDrawer();
                fetchItems();
              } catch (error) {
                message.error(error.response?.data?.message || 'Không lưu được dữ liệu.');
              } finally {
                setSubmitting(false);
              }
            }}
          >
            <Space orientation="vertical" size={16} style={{ width: '100%' }}>
              {formSections.map((section) => (
                <Card key={section.key} className="page-card resource-form-card" size="small" title={section.title}>
                  {section.description ? (
                    <Typography.Paragraph type="secondary" style={{ marginTop: 0 }}>
                      {section.description}
                    </Typography.Paragraph>
                  ) : null}
                  <Row gutter={16}>
                    {section.fields.map((field) => (
                      <Col span={field.span || 12} key={field.name}>
                        <Form.Item
                          label={field.label}
                          name={field.name}
                          extra={field.help}
                          rules={field.required ? [{ required: true, message: `Vui lòng nhập ${field.label.toLowerCase()}.` }] : []}
                        >
                          {renderField(field, optionsMap, handleCreateSelectOption)}
                        </Form.Item>
                      </Col>
                    ))}
                  </Row>
                </Card>
              ))}

              <div className="resource-drawer-actions">
                <Button onClick={handleCloseDrawer}>Đóng</Button>
                <Button type="primary" htmlType="submit" loading={submitting}>
                  {editingItem ? 'Lưu thay đổi' : 'Tạo mới'}
                </Button>
              </div>
            </Space>
          </Form>
        </Space>
      </Drawer>
    </Space>
  );
}

export default ResourcePage;
