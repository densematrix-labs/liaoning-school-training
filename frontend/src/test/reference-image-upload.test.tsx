import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, expect, it, vi } from 'vitest'
import ReferenceImageUpload from '../components/ReferenceImageUpload'

const calls = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }))
vi.mock('../lib/api', () => ({ api: calls, getErrorMessage: (error: any) => error.message }))

beforeEach(() => {
  vi.clearAllMocks()
  calls.get.mockResolvedValue({ data: [{ id: 'lab-1', name: '机车模拟驾驶室', reference_image_url: '/old.jpg' }] })
  calls.post.mockResolvedValue({ data: { id: 'lab-1', name: '机车模拟驾驶室', reference_image_url: '/new.jpg' } })
})

it('uploads a selected standard image for the selected lab', async () => {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })}><ReferenceImageUpload /></QueryClientProvider>)
  await screen.findByText('机车模拟驾驶室')
  fireEvent.change(screen.getByLabelText('标准图片实训室'), { target: { value: 'lab-1' } })
  fireEvent.change(screen.getByLabelText('标准图片文件'), { target: { files: [new File(['pixels'], 'standard.png', { type: 'image/png' })] } })
  fireEvent.click(screen.getByText('上传并设为标准图片'))
  await waitFor(() => expect(calls.post).toHaveBeenCalledWith('/api/v1/environment/labs/lab-1/reference', expect.any(FormData), expect.any(Object)))
  expect(await screen.findByRole('status')).toHaveTextContent('标准图片已更新')
})
