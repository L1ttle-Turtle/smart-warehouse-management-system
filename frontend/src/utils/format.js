export const currencyFormatter = new Intl.NumberFormat('vi-VN', {
  style: 'currency',
  currency: 'VND',
  maximumFractionDigits: 0,
});

export const numberFormatter = new Intl.NumberFormat('vi-VN');

export function formatCurrency(value) {
  return currencyFormatter.format(Number(value || 0));
}

export function formatNumber(value) {
  return numberFormatter.format(Number(value || 0));
}

export function formatDateTime(value) {
  if (!value) {
    return '-';
  }
  return new Date(value).toLocaleString('vi-VN');
}
