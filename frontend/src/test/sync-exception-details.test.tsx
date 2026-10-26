import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import SyncExceptionDetails from '../components/SyncExceptionDetails'

beforeEach(() => {
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', '') }
})
afterEach(cleanup)

it('locates the failing source row and shows its cause and original fields', () => {
  const onClose = vi.fn()
  render(<SyncExceptionDetails batch={2} startedAt="2026-09-04T09:08:49" onClose={onClose} exceptions={[
    { id: 'a', row_number: 6, source_record_id: 'DEMO-INVALID-001', reason: '步骤标识无法匹配演示项目', raw_data: { student_no: '2023010101', step_id: 'UNKNOWN', duplicate: '', invalid: null, extra: { passed: false } } },
    { id: 'b', row_number: 12, reason: '缺少源记录唯一标识' },
  ]} />)
  expect(screen.getByRole('dialog', { name: '第 2 批 · 导入异常明细' })).toBeVisible()
  const search = screen.getByRole('textbox', { name: '定位异常记录' })
  expect(search).toHaveFocus()
  expect(screen.getByText('失败原因：步骤标识无法匹配演示项目')).toBeInTheDocument()
  fireEvent.change(search, { target: { value: '2023010101' } })
  expect(screen.getByRole('status')).toHaveTextContent('显示 1 / 2 条异常')
  expect(screen.getByText('原始文件第 6 行')).toBeVisible()
  expect(screen.queryByText('原始文件第 12 行')).not.toBeInTheDocument()
  fireEvent.click(screen.getByText('查看原始记录'))
  expect(screen.getByText('UNKNOWN')).toBeVisible()
  expect(screen.getAllByText('（空）')).toHaveLength(2)
  expect(screen.getByText('{"passed":false}')).toBeVisible()
  fireEvent.change(search, { target: { value: 'demo-invalid-001' } })
  expect(screen.getByRole('status')).toHaveTextContent('显示 1 / 2 条异常')
  fireEvent.change(search, { target: { value: '12' } })
  expect(screen.getByText('源记录：未提供')).toBeInTheDocument()
  fireEvent.click(screen.getByText('查看原始记录'))
  expect(screen.getByText(/该记录未保存原始字段/)).toBeVisible()
  fireEvent.change(search, { target: { value: '缺少源记录' } })
  expect(screen.getByRole('status')).toHaveTextContent('显示 1 / 2 条异常')
  fireEvent.change(search, { target: { value: '不存在的编号' } })
  expect(screen.getByText(/未找到匹配的异常记录/)).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: '关闭' }))
  expect(onClose).toHaveBeenCalledOnce()
  fireEvent(screen.getByRole('dialog'), new Event('cancel', { cancelable: true }))
  expect(onClose).toHaveBeenCalledTimes(2)
})

it('shows an explicit empty state and returns focus to the opener', () => {
  const opener = document.createElement('button')
  document.body.append(opener)
  opener.focus()
  const view = render(<SyncExceptionDetails batch={1} startedAt="2026-09-04T09:08:49" onClose={vi.fn()} exceptions={[]} />)
  expect(screen.getByText('该批次暂无可展示的异常明细。')).toBeVisible()
  view.unmount()
  expect(opener).toHaveFocus()
  opener.remove()
})
