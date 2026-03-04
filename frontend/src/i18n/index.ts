import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

const resources = {
  zh: {
    translation: {
      // Common
      app_name: '辽轨智能实训能力评估平台',
      loading: '加载中...',
      error: '出错了',
      retry: '重试',
      save: '保存',
      cancel: '取消',
      confirm: '确认',
      back: '返回',
      submit: '提交',
      search: '搜索',
      export: '导出',
      
      // Auth
      login: '登录',
      logout: '退出登录',
      username: '用户名',
      password: '密码',
      login_hint: '请输入账号密码登录系统',
      login_error: '用户名或密码错误',
      
      // Navigation
      nav: {
        dashboard: '数据大屏',
        my_scores: '我的成绩',
        ability_map: '能力图谱',
        reports: '诊断报告',
        env_check: '环境检查',
        class_manage: '班级管理',
        score_summary: '成绩汇总',
        batch_report: '批量报告',
      },
      
      // Student
      student: {
        score_history: '实训成绩',
        score_detail: '成绩详情',
        project: '实训项目',
        score: '得分',
        date: '日期',
        pass: '通过',
        fail: '未通过',
        view_detail: '查看详情',
        generate_report: '生成报告',
      },
      
      // Ability
      ability: {
        radar_chart: '能力雷达图',
        graduation_status: '毕业达标状态',
        ready: '已达标',
        not_ready: '待提升',
        strongest: '最强能力',
        weakest: '待加强',
        suggestions: '提升建议',
      },
      
      // Dashboard
      dashboard: {
        realtime: '实时统计',
        active_students: '当前在训学生',
        today_trainings: '今日实训次数',
        average_score: '平均分',
        pass_rate: '及格率',
        class_ranking: '班级排名',
        ability_dist: '能力分布',
        trend: '趋势图',
        lab_status: '实训室状态',
      },
      
      // Teacher
      teacher: {
        my_classes: '我的班级',
        students: '学生',
        view_scores: '查看成绩',
        view_abilities: '查看能力',
        generate_reports: '批量生成报告',
      },
      
      // Environment Check
      env_check: {
        title: '实训室环境检查',
        select_lab: '选择实训室',
        upload_photo: '上传照片',
        checking: '检测中...',
        result: '检查结果',
        equipment: '器材归位',
        cleanliness: '台面整洁',
        safety: '安全规范',
        hygiene: '环境卫生',
      },
    },
  },
  en: {
    translation: {
      // Common
      app_name: 'Liaoning Railway Training Platform',
      loading: 'Loading...',
      error: 'Error',
      retry: 'Retry',
      save: 'Save',
      cancel: 'Cancel',
      confirm: 'Confirm',
      back: 'Back',
      submit: 'Submit',
      search: 'Search',
      export: 'Export',
      
      // Auth
      login: 'Login',
      logout: 'Logout',
      username: 'Username',
      password: 'Password',
      login_hint: 'Enter your credentials to login',
      login_error: 'Invalid username or password',
      
      // Navigation
      nav: {
        dashboard: 'Dashboard',
        my_scores: 'My Scores',
        ability_map: 'Ability Map',
        reports: 'Reports',
        env_check: 'Env Check',
        class_manage: 'Class Manage',
        score_summary: 'Score Summary',
        batch_report: 'Batch Reports',
      },
      
      // Student
      student: {
        score_history: 'Training Scores',
        score_detail: 'Score Detail',
        project: 'Project',
        score: 'Score',
        date: 'Date',
        pass: 'Pass',
        fail: 'Fail',
        view_detail: 'View Detail',
        generate_report: 'Generate Report',
      },
      
      // Ability
      ability: {
        radar_chart: 'Ability Radar',
        graduation_status: 'Graduation Status',
        ready: 'Ready',
        not_ready: 'Need Improvement',
        strongest: 'Strongest',
        weakest: 'To Improve',
        suggestions: 'Suggestions',
      },
      
      // Dashboard
      dashboard: {
        realtime: 'Realtime Stats',
        active_students: 'Active Students',
        today_trainings: 'Today Trainings',
        average_score: 'Avg Score',
        pass_rate: 'Pass Rate',
        class_ranking: 'Class Ranking',
        ability_dist: 'Ability Distribution',
        trend: 'Trend',
        lab_status: 'Lab Status',
      },
      
      // Teacher
      teacher: {
        my_classes: 'My Classes',
        students: 'Students',
        view_scores: 'View Scores',
        view_abilities: 'View Abilities',
        generate_reports: 'Generate Reports',
      },
      
      // Environment Check
      env_check: {
        title: 'Lab Environment Check',
        select_lab: 'Select Lab',
        upload_photo: 'Upload Photo',
        checking: 'Checking...',
        result: 'Check Result',
        equipment: 'Equipment',
        cleanliness: 'Cleanliness',
        safety: 'Safety',
        hygiene: 'Hygiene',
      },
    },
  },
}

i18n.use(initReactI18next).init({
  resources,
  lng: 'zh',
  fallbackLng: 'zh',
  interpolation: {
    escapeValue: false,
  },
})

export default i18n
