import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import MappingManager from '../components/MappingManager'

const requests = vi.hoisted(() => ({ get: vi.fn(), put: vi.fn() }))
vi.mock('../lib/api', () => ({ api: requests, getErrorMessage: (e: any) => e.message }))
afterEach(() => { cleanup(); vi.clearAllMocks() })

it('edits per-step contribution points and preserves other rules when saving', async () => {
  const project = { id: 'p', name: '制动检查', steps: [{ id: 'one', name: '检查准备', score: 20 }, { id: 'two', name: '检查操作', score: 80 }],
    ability_mapping: { one: ['a'], two: ['a'] }, scoring_rules: { scoring_mode: 'absolute', repeat_mode: 'latest', ability_mapping_points: { one: { a: 15 }, two: { a: 85 } } } }
  requests.get.mockImplementation(async (path: string) => ({ data: path.endsWith('/projects') ? { items: [project] } : path.endsWith('/sub-abilities') ? { items: [{ id: 'a', name: '设备检查', major_ability_id: 'm' }] } : { items: [{ id: 'm', name: '设备能力' }] } }))
  requests.put.mockResolvedValue({ data: { scoring_rules: { version: 2 }, ability_mapping: project.ability_mapping } })
  render(<MappingManager />)
  await screen.findByRole('option', { name: '制动检查' })
  fireEvent.change(screen.getByRole('combobox', { name: '实训项目' }), { target: { value: 'p' } })
  const inputs = await screen.findAllByLabelText('设备检查贡献分值')
  expect(inputs[0]).toHaveValue(15)
  expect(inputs[1]).toHaveValue(85)
  fireEvent.change(inputs[0], { target: { value: '20' } })
  fireEvent.change(inputs[1], { target: { value: '80' } })
  fireEvent.click(screen.getByRole('button', { name: '保存映射配置' }))
  await waitFor(() => expect(requests.put).toHaveBeenCalledWith('/api/v1/release/catalog/projects/p', {
    ability_mapping: { one: ['a'], two: ['a'] }, scoring_rules: { ...project.scoring_rules, ability_mapping_points: { one: { a: 20 }, two: { a: 80 } } }
  }))
  const firstStep = screen.getByText('检查准备 · one').closest('article')!
  fireEvent.click(within(firstStep).getByRole('button', { name: '移除设备检查' }))
  expect(within(firstStep).queryByLabelText('设备检查贡献分值')).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: '保存映射配置' }))
  await waitFor(() => expect(requests.put).toHaveBeenLastCalledWith('/api/v1/release/catalog/projects/p', expect.objectContaining({
    scoring_rules: expect.objectContaining({ ability_mapping_points: { one: {}, two: { a: 80 } } })
  })))
})
