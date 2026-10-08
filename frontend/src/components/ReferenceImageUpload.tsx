import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, getErrorMessage } from '../lib/api'

export default function ReferenceImageUpload() {
  const queryClient = useQueryClient()
  const inputRef = useRef<HTMLInputElement>(null)
  const [labId, setLabId] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const labs = useQuery({ queryKey: ['environment-labs'], queryFn: async () => (await api.get('/api/v1/environment/labs')).data })
  const selectedLab = labs.data?.find((lab: any) => lab.id === labId)
  const upload = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error('请选择标准图片')
      if (file.size > 10 * 1024 * 1024) throw new Error('图片不得超过 10MB')
      const data = new FormData()
      data.append('file', file)
      return (await api.post(`/api/v1/environment/labs/${labId}/reference`, data, { headers: { 'Content-Type': 'multipart/form-data' } })).data
    },
    onSuccess: (lab) => {
      queryClient.setQueryData(['environment-labs'], (current: any[] | undefined) => current?.map((item) => item.id === lab.id ? lab : item))
      setFile(null)
      if (inputRef.current) inputRef.current.value = ''
    },
  })

  return <section className="railway-card p-5">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div><p className="eyebrow">REFERENCE IMAGE</p><h2 className="section-heading">环境检查标准图片</h2><p className="mt-1 text-sm text-text-muted">选择实训室，上传教师确认过的标准状态图片；后续检测会以该图片为对比基准。</p></div>
      {selectedLab?.reference_image_url && <img className="h-24 w-36 rounded border border-railway-600 object-cover" src={selectedLab.reference_image_url} alt={`${selectedLab.name}当前标准图片`} />}
    </div>
    <div className="mt-4 grid gap-3 md:grid-cols-[minmax(0,1fr)_auto_auto] md:items-end">
      <label className="text-sm text-text-secondary"><span className="mb-2 block">实训室</span><select aria-label="标准图片实训室" className="input-field" value={labId} onChange={(event) => { setLabId(event.target.value); setFile(null); upload.reset() }}><option value="">选择实训室</option>{labs.data?.map((lab: any) => <option key={lab.id} value={lab.id}>{lab.name}</option>)}</select></label>
      <input ref={inputRef} className="hidden" aria-label="标准图片文件" type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => { setFile(event.target.files?.[0] ?? null); upload.reset() }} />
      <button type="button" className="railway-button" disabled={!labId || upload.isPending} onClick={() => inputRef.current?.click()}>{file ? file.name : '选择标准图片'}</button>
      <button type="button" className="btn-primary" disabled={!labId || !file || upload.isPending} onClick={() => upload.mutate()}>{upload.isPending ? '上传中…' : '上传并设为标准图片'}</button>
    </div>
    {labs.isError && <p role="alert" className="mt-3 text-sm text-status-danger">实训室加载失败：{getErrorMessage(labs.error)}</p>}
    {upload.isError && <p role="alert" className="mt-3 text-sm text-status-danger">{getErrorMessage(upload.error)}</p>}
    {upload.isSuccess && <p role="status" className="mt-3 text-sm text-status-success">标准图片已更新，后续环境检查将使用新图片。</p>}
  </section>
}
