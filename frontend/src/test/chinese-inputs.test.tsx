import { useState } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import ChineseDateInput from '../components/ChineseDateInput'
import ChineseFileInput from '../components/ChineseFileInput'

function DateField({ initial = '', time = false }: { initial?: string; time?: boolean }) {
  const [value, setValue] = useState(initial)
  return <><ChineseDateInput aria-label="筛选日期" type={time ? 'datetime-local' : 'date'} value={value} onValueChange={setValue} /><output data-testid="value">{value}</output></>
}

describe('Chinese form controls', () => {
  it('shows a Chinese file prompt and the selected file while preserving upload callbacks', () => {
    const selected = vi.fn()
    render(<ChineseFileInput aria-label="现场图片" accept="image/png" onChange={selected} />)
    expect(screen.getByText('未选择文件')).toBeInTheDocument()
    const file = new File(['image'], '现场.png', { type: 'image/png' })
    fireEvent.change(screen.getByLabelText('现场图片'), { target: { files: [file] } })
    expect(screen.getByText('现场.png')).toBeInTheDocument()
    expect(selected.mock.calls[0][0].target.files[0]).toBe(file)
  })
  it('rejects impossible dates and accepts leap day without sending partial dates to filters', () => {
    render(<DateField />)
    const input = screen.getByLabelText('筛选日期')
    fireEvent.change(input, { target: { value: '2026-02-29' } })
    fireEvent.blur(input)
    expect(screen.getByRole('alert')).toHaveTextContent('请输入有效日期')
    expect(screen.getByTestId('value')).toBeEmptyDOMElement()
    fireEvent.change(input, { target: { value: '2028-02-29' } })
    expect(screen.getByTestId('value')).toHaveTextContent('2028-02-29')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
  it('supports calendar month navigation, selection and clearing', () => {
    render(<DateField initial="2026-10-30" />)
    fireEvent.click(screen.getByRole('button', { name: '筛选日期选择日期' }))
    fireEvent.click(screen.getByRole('button', { name: '下个月' }))
    fireEvent.click(screen.getByRole('button', { name: '2026-11-02' }))
    expect(screen.getByTestId('value')).toHaveTextContent('2026-11-02')
    fireEvent.click(screen.getByRole('button', { name: '筛选日期选择日期' }))
    fireEvent.click(screen.getByRole('button', { name: '清空' }))
    expect(screen.getByTestId('value')).toBeEmptyDOMElement()
  })
  it('keeps local date-time values intact and preserves time when choosing a new day', () => {
    render(<DateField initial="2026-10-30T09:30" time />)
    expect(screen.getByLabelText('筛选日期')).toHaveValue('2026-10-30 09:30')
    fireEvent.change(screen.getByLabelText('筛选日期'), { target: { value: '2026-10-30 25:00' } })
    fireEvent.blur(screen.getByLabelText('筛选日期'))
    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByTestId('value')).toHaveTextContent('2026-10-30T09:30')
    fireEvent.click(screen.getByRole('button', { name: '筛选日期选择日期' }))
    fireEvent.click(screen.getByRole('button', { name: '2026-10-31' }))
    expect(screen.getByTestId('value')).toHaveTextContent('2026-10-31T09:30')
  })
})
