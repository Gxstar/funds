/**
 * 格式化工具函数
 */

/**
 * 格式化货币
 * @param {number} value 金额
 * @returns {string} 格式化后的金额字符串
 */
export function formatCurrency(value) {
  if (value === null || value === undefined) return '¥0.00'
  return '¥' + parseFloat(value).toLocaleString('zh-CN', { 
    minimumFractionDigits: 2, 
    maximumFractionDigits: 2 
  })
}

/**
 * 格式化百分比
 * @param {number} value 百分比值
 * @returns {string} 格式化后的百分比字符串
 */
export function formatPercent(value) {
  if (value === null || value === undefined) return '0.00%'
  const num = parseFloat(value)
  return (num > 0 ? '+' : '') + num.toFixed(2) + '%'
}

/**
 * 格式化日期
 * @param {string|Date} date 日期
 * @returns {string} 格式化后的日期字符串
 */
export function formatDate(date) {
  if (!date) return '-'
  const d = new Date(date)
  const month = d.getMonth() + 1
  const day = d.getDate()
  return `${month}月${day}日`
}

/**
 * 格式化日期时间
 * @param {string|Date} datetime 日期时间
 * @returns {string} 格式化后的日期时间字符串
 */
export function formatDateTime(datetime) {
  if (!datetime) return ''
  const d = new Date(datetime)
  const year = d.getFullYear()
  const month = (d.getMonth() + 1).toString().padStart(2, '0')
  const day = d.getDate().toString().padStart(2, '0')
  const hour = d.getHours().toString().padStart(2, '0')
  const minute = d.getMinutes().toString().padStart(2, '0')
  return `${year}-${month}-${day} ${hour}:${minute}`
}
