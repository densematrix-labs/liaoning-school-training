import {useQuery} from '@tanstack/react-query'
import {api} from '../lib/api'
export default function OperationsEvidence(){
 const q=useQuery({queryKey:['operations-evidence'],queryFn:async()=>(await api.get('/api/v1/release/operations-evidence')).data})
 const d=q.data
 return <section className="railway-card space-y-4 p-5" aria-label="运行及备份明细"><h2 className="section-heading">运行状态与备份恢复记录</h2><button className="btn-secondary" onClick={()=>q.refetch()}>刷新运行与备份记录</button>{d&&<><p>检查时间（UTC）：{d.checked_at} · 应用：{d.application} · 数据库：{d.database}</p><h3>同步任务</h3><p>状态：{d.sync?.status} · 批次ID：{d.sync?.id||'无'} · 开始：{d.sync?.started_at||'尚未执行'} · 完成：{d.sync?.completed_at||'未完成'}</p><p>异常原因：{d.sync?.reason||'无已记录异常'}</p><h3>AI连通检查</h3><p>时间：{d.connectivity?.time||'尚未检查'} · {d.connectivity?.ai?.reachable?'可连通':'未连通或尚未检查'}</p><h3>加密备份</h3><p>时间：{d.backup?.time||'无记录'} · 文件：{d.backup?.filename} · 状态：{d.backup?.status} · 大小：{d.backup?.size??d.backup?.size_bytes} 字节</p><p className="break-all">SHA256：{d.backup?.sha256}</p><h3>恢复到独立目录</h3><p>任务ID：{d.restore?.id||'旧记录未分配ID'} · 时间：{d.restore?.time} · 文件：{d.restore?.filename} · 结果：{d.restore?.verified?'通过':'无已验证结果'}</p><p>数据库完整性/外键：{d.restore?.foreign_keys_verified?'通过':'未留存'} · 系统配置：{d.restore?.configuration_verified?'通过':'未留存'} · 成绩数：{d.restore?.counts?.scores}</p></>}</section>
}
