import { useState, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '../../lib/api'

interface Lab {
  id: string
  name: string
  building: string
  floor: number
  capacity: number
  status: string
}

interface CheckResult {
  id: string
  lab_id: string
  lab_name: string
  total_score: number
  max_score: number
  details: {
    equipment_placement: { score: number; max_score: number; issues: string[] }
    surface_cleanliness: { score: number; max_score: number; issues: string[] }
    safety_compliance: { score: number; max_score: number; issues: string[] }
    environmental_hygiene: { score: number; max_score: number; issues: string[] }
  }
  summary: string
  checked_at: string
}

function CategoryScore({ 
  name, 
  icon,
  data 
}: { 
  name: string
  icon: string
  data: { score: number; max_score: number; issues: string[] }
}) {
  const percentage = (data.score / data.max_score) * 100
  const isGood = percentage >= 80
  
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      className="glass-panel p-4"
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xl">{icon}</span>
          <h4 className="font-display font-semibold text-text-primary">{name}</h4>
        </div>
        <span className={`font-mono font-bold
          ${isGood ? 'text-status-success' : 'text-status-warning'}`}
        >
          {data.score}/{data.max_score}
        </span>
      </div>
      
      {/* Progress bar */}
      <div className="h-2 bg-railway-700 rounded-full overflow-hidden mb-3">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.8 }}
          className={`h-full rounded-full
            ${isGood ? 'bg-gradient-to-r from-status-success to-accent-cyan' : 
              'bg-gradient-to-r from-status-warning to-accent-blue'}`}
        />
      </div>
      
      {/* Issues */}
      {data.issues.length > 0 && (
        <div className="space-y-1">
          {data.issues.map((issue, i) => (
            <p key={i} className="text-xs text-text-muted flex items-start gap-2">
              <span className="text-status-warning">!</span>
              {issue}
            </p>
          ))}
        </div>
      )}
    </motion.div>
  )
}

export default function StudentEnvCheck() {
  const { t } = useTranslation()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [selectedLab, setSelectedLab] = useState<string>('')
  const [previewImage, setPreviewImage] = useState<string | null>(null)
  const [result, setResult] = useState<CheckResult | null>(null)
  
  // Fetch labs
  const { data: labs } = useQuery<Lab[]>({
    queryKey: ['labs'],
    queryFn: async () => {
      const res = await api.get('/api/v1/environment/labs')
      return res.data
    },
  })
  
  // Check mutation
  const checkMutation = useMutation({
    mutationFn: async (imageBase64: string) => {
      const res = await api.post('/api/v1/environment/check', {
        lab_id: selectedLab,
        image_base64: imageBase64,
      })
      return res.data
    },
    onSuccess: (data) => {
      setResult(data)
    },
  })
  
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    
    const reader = new FileReader()
    reader.onload = () => {
      const base64 = reader.result as string
      setPreviewImage(base64)
    }
    reader.readAsDataURL(file)
  }
  
  const handleCheck = () => {
    if (!previewImage || !selectedLab) return
    
    // Extract base64 data (remove data:image/xxx;base64, prefix)
    const base64Data = previewImage.split(',')[1]
    checkMutation.mutate(base64Data)
  }
  
  const reset = () => {
    setPreviewImage(null)
    setResult(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-display text-2xl font-bold text-gradient">
          {t('env_check.title')}
        </h1>
        <p className="text-text-muted mt-1">
          上传实训室照片，AI 将自动检测环境规范情况
        </p>
      </div>
      
      {!result ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left - Upload */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="glass-panel p-6 space-y-6"
          >
            {/* Lab selection */}
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                {t('env_check.select_lab')}
              </label>
              <select
                value={selectedLab}
                onChange={(e) => setSelectedLab(e.target.value)}
                className="input-field"
              >
                <option value="">请选择实训室</option>
                {labs?.map(lab => (
                  <option key={lab.id} value={lab.id}>
                    {lab.name} ({lab.building} {lab.floor}F)
                  </option>
                ))}
              </select>
            </div>
            
            {/* Image upload */}
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                {t('env_check.upload_photo')}
              </label>
              
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileChange}
                className="hidden"
              />
              
              <div
                onClick={() => fileInputRef.current?.click()}
                className={`
                  relative aspect-video rounded-lg border-2 border-dashed cursor-pointer
                  transition-all duration-300 overflow-hidden
                  ${previewImage 
                    ? 'border-accent-blue' 
                    : 'border-railway-500 hover:border-accent-blue/50'
                  }
                `}
              >
                {previewImage ? (
                  <img
                    src={previewImage}
                    alt="Preview"
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="absolute inset-0 flex flex-col items-center justify-center text-text-muted">
                    <div className="text-4xl mb-2">📷</div>
                    <p className="text-sm">点击或拖拽上传照片</p>
                    <p className="text-xs mt-1">支持 JPG, PNG 格式</p>
                  </div>
                )}
              </div>
            </div>
            
            {/* Actions */}
            <div className="flex gap-3">
              <button
                onClick={handleCheck}
                disabled={!selectedLab || !previewImage || checkMutation.isPending}
                className="btn-primary flex-1 flex items-center justify-center gap-2"
              >
                {checkMutation.isPending ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>{t('env_check.checking')}</span>
                  </>
                ) : (
                  <>
                    <span>🔍</span>
                    <span>开始检测</span>
                  </>
                )}
              </button>
              
              {previewImage && (
                <button
                  onClick={reset}
                  className="btn-secondary"
                >
                  重新上传
                </button>
              )}
            </div>
          </motion.div>
          
          {/* Right - Instructions */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="glass-panel p-6"
          >
            <h3 className="font-display text-lg font-semibold text-accent-cyan mb-4">
              📋 检测说明
            </h3>
            
            <div className="space-y-4">
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-lg bg-railway-700 flex items-center justify-center text-accent-cyan font-bold">1</div>
                <div>
                  <p className="font-semibold text-text-primary">选择实训室</p>
                  <p className="text-sm text-text-muted">选择你完成实训的实训室</p>
                </div>
              </div>
              
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-lg bg-railway-700 flex items-center justify-center text-accent-cyan font-bold">2</div>
                <div>
                  <p className="font-semibold text-text-primary">拍摄照片</p>
                  <p className="text-sm text-text-muted">拍摄实训台及周边环境的全景照片</p>
                </div>
              </div>
              
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-lg bg-railway-700 flex items-center justify-center text-accent-cyan font-bold">3</div>
                <div>
                  <p className="font-semibold text-text-primary">AI 检测</p>
                  <p className="text-sm text-text-muted">系统自动对比标准照片并给出评分</p>
                </div>
              </div>
            </div>
            
            <div className="mt-6 p-4 bg-railway-700/30 rounded-lg">
              <h4 className="font-semibold text-text-primary mb-2">检测项目</h4>
              <ul className="space-y-2 text-sm text-text-muted">
                <li>🔧 器材归位 (30分)</li>
                <li>🧹 台面整洁 (30分)</li>
                <li>⚡ 安全规范 (20分)</li>
                <li>🌿 环境卫生 (20分)</li>
              </ul>
            </div>
          </motion.div>
        </div>
      ) : (
        /* Result Display */
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="space-y-6"
        >
          {/* Score Header */}
          <div className="glass-panel-bright p-8 text-center">
            <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-gradient-to-br from-accent-blue to-accent-cyan mb-4 shadow-glow-lg">
              <span className="font-display text-4xl font-bold text-white">
                {result.total_score}
              </span>
            </div>
            <h2 className="font-display text-xl font-semibold text-text-primary">
              环境检查完成
            </h2>
            <p className="text-text-muted mt-2">{result.summary}</p>
          </div>
          
          {/* Category Scores */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <CategoryScore
              name={t('env_check.equipment')}
              icon="🔧"
              data={result.details.equipment_placement}
            />
            <CategoryScore
              name={t('env_check.cleanliness')}
              icon="🧹"
              data={result.details.surface_cleanliness}
            />
            <CategoryScore
              name={t('env_check.safety')}
              icon="⚡"
              data={result.details.safety_compliance}
            />
            <CategoryScore
              name={t('env_check.hygiene')}
              icon="🌿"
              data={result.details.environmental_hygiene}
            />
          </div>
          
          {/* Actions */}
          <div className="flex justify-center">
            <button
              onClick={reset}
              className="btn-primary"
            >
              进行新的检测
            </button>
          </div>
        </motion.div>
      )}
    </div>
  )
}
