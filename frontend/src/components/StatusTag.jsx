import { Tag } from 'antd';

const COLOR_MAP = {
  active: 'green',
  inactive: 'default',
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
