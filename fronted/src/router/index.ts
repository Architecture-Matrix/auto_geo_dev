/**
 * 路由配置
 * 我用这个来管理应用路由！
 */

import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'

// 路由定义
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/views/layout/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      // ==================== 1. 首页 ====================
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/DashboardPage.vue'),
        meta: { title: '首页', icon: 'House', order: 1 },
      },

      // ==================== 2. 客户管理 ====================
      {
        path: 'clients',
        name: 'Clients',
        component: () => import('@/views/client/ClientPage.vue'),
        meta: { title: '客户管理', icon: 'OfficeBuilding', order: 2 },
      },

      // ==================== 3. 项目管理 (去除GEO前缀) ====================
      {
        path: 'projects',
        name: 'Projects',
        component: () => import('@/views/geo/Projects.vue'),
        meta: { title: '项目管理', icon: 'Grid', order: 3 },
      },

      // ==================== 4. 知识库管理 ====================
      {
        path: 'knowledge',
        name: 'Knowledge',
        component: () => import('@/views/knowledge/KnowledgePage.vue'),
        meta: { title: '知识库管理', icon: 'Reading', order: 4 },
      },

      // ==================== 5. 智能建站 ====================
      {
        path: 'site-builder',
        name: 'SiteBuilder',
        component: () => import('@/views/site-builder/ConfigWizard.vue'),
        meta: { title: '智能建站', icon: 'Platform', order: 5 },
      },

      // ==================== 6. 关键词蒸馏 ====================
      {
        path: 'keywords',
        name: 'Keywords',
        component: () => import('@/views/geo/Keywords.vue'),
        meta: { title: '关键词蒸馏', icon: 'MagicStick', order: 6 },
      },

      // ==================== 7. 文章生成 ====================
      {
        path: 'article-generate',
        name: 'ArticleGenerate',
        component: () => import('@/views/geo/Articles.vue'),
        meta: { title: '文章生成', icon: 'EditPen', order: 7 },
      },

      // ==================== 8. 文章管理 ====================
      {
        path: 'articles',
        name: 'Articles',
        component: () => import('@/views/article/ArticleList.vue'),
        meta: { title: '文章管理', icon: 'Document', order: 8 },
      },
      {
        path: 'articles/add',
        name: 'ArticleAdd',
        component: () => import('@/views/article/ArticleEdit.vue'),
        meta: { title: '新建文章', hidden: true},
      },
      {
        path: 'articles/edit/:id',
        name: 'ArticleEdit',
        component: () => import('@/views/article/ArticleEdit.vue'),
        meta: { title: '编辑文章', hidden: true },
      },

      // ==================== 9. 账号管理 ====================
      {
        path: 'accounts',
        name: 'Accounts',
        component: () => import('@/views/account/AccountList.vue'),
        meta: { title: '账号管理', icon: 'User', order: 9 },
      },
      {
        path: 'accounts/add',
        name: 'AccountAdd',
        component: () => import('@/views/account/AccountAdd.vue'),
        meta: { title: '添加账号', hidden: true },
      },

      // ==================== 10. 批量发布 ====================
      {
        path: 'publish',
        name: 'Publish',
        component: () => import('@/views/publish/PublishPage.vue'),
        meta: { title: '批量发布', icon: 'Promotion', order: 10 },
      },

      // ==================== 11. 发布记录 ====================
      {
        path: 'history',
        name: 'History',
        component: () => import('@/views/publish/PublishHistory.vue'),
        meta: { title: '发布记录', icon: 'Clock', order: 11 },
      },

      // ==================== 12. 收录监控 ====================
      {
        path: 'monitor',
        name: 'Monitor',
        component: () => import('@/views/geo/Monitor.vue'),
        meta: { title: '收录监控', icon: 'Monitor', order: 12 },
      },

      // ==================== 13. 数据报表 ====================
      {
        path: 'data-report',
        name: 'DataReport',
        component: () => import('@/views/report/DataReport.vue'),
        meta: { title: '数据报表', icon: 'DataAnalysis', order: 13 },
      },

      // ==================== 14. 定时任务 ====================
      {
        path: 'scheduler',
        name: 'Scheduler',
        component: () => import('@/views/scheduler/SchedulerPage.vue'),
        meta: { title: '定时任务', icon: 'Timer', order: 14 },
      },

      // ==================== 15. 系统设置 ====================
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/settings/SettingsPage.vue'),
        meta: { title: '系统设置', icon: 'Setting', order: 15 },
      },
    ],
  },
]

// 创建路由实例
const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

// 路由守卫
router.beforeEach((to, _from, next) => {
  // 设置页面标题
  if (to.meta?.title) {
    document.title = `${to.meta.title} - AutoGeo`
  }
  next()
})

export default router