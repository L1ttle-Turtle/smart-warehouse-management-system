import { Tag } from 'antd';

const COLOR_MAP = {
  active: 'green',
  assigned: 'gold',
  inactive: 'default',
  in_transit: 'blue',
  draft: 'gold',
  confirmed: 'green',
  cancelled: 'red',
  pending: 'gold',
  preparing: 'blue',
  delivering: 'cyan',
  delivered: 'green',
  failed: 'red',
  returned: 'volcano',
  unpaid: 'red',
  partial: 'orange',
  paid: 'green',
  todo: 'gold',
  done: 'green',
  low: 'default',
  medium: 'blue',
  high: 'red',
  system: 'blue',
  task: 'purple',
  inventory: 'cyan',
  shipment: 'geekblue',
  payment: 'green',
};

function prettify(value) {
  return String(value || '-')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function StatusTag({ value }) {
  return <Tag color={COLOR_MAP[value] || 'default'}>{prettify(value)}</Tag>;
}

export default StatusTag;
