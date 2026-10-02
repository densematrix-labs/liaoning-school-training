import { fireEvent,render,screen,waitFor } from '@testing-library/react'
import { QueryClient,QueryClientProvider } from '@tanstack/react-query'
import EnvironmentUpload from '../components/EnvironmentUpload'
import { beforeEach,it,expect,vi } from 'vitest'
const calls=vi.hoisted(()=>({get:vi.fn(),post:vi.fn()}))
vi.mock('../lib/api',()=>({api:calls,getErrorMessage:(e:any)=>e.message}))
beforeEach(()=>{vi.clearAllMocks();calls.get.mockImplementation(async(url:string)=>({data:url.endsWith('/labs')?[{id:'lab',name:'实训室'}]:url.includes('/tasks/')?{status:'failed',error_message:'AI 未配置'}:{scores:[{id:'score',project_name:'制动检查',calculated_at:'2026-10-01'}]}}));calls.post.mockResolvedValue({data:{id:'task',status:'pending'}})})
it('uploads real bytes with a selected owned record and shows asynchronous failure',async()=>{
  render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><EnvironmentUpload studentId="student"/></QueryClientProvider>)
  await screen.findByText(/制动检查/)
  fireEvent.change(screen.getByLabelText('关联实训'),{target:{value:'score'}})
  fireEvent.change(screen.getByLabelText('对应实训室'),{target:{value:'lab'}})
  fireEvent.change(screen.getByLabelText('现场图片'),{target:{files:[new File(['pixels'],'photo.png',{type:'image/png'})]}})
  fireEvent.click(screen.getByText('提交环境检查'))
  await waitFor(()=>expect(calls.post).toHaveBeenCalledWith('/api/v1/environment/tasks',expect.objectContaining({student_id:'student',score_id:'score',lab_id:'lab',image_base64:expect.stringContaining('data:image/png;base64,')})))
  await screen.findByText(/AI 未配置/)
  calls.post.mockRejectedValueOnce(new Error('网络断开'))
  fireEvent.click(screen.getByText('提交环境检查'))
  expect(await screen.findByRole('alert')).toHaveTextContent('网络断开')
})
