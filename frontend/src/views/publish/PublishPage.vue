<template>
  <div class="publish-page">
    <!-- 步骤指示器 -->
    <div class="steps">
      <div
        v-for="(step, index) in steps"
        :key="index"
        class="step-item"
        :class="{
          active: currentStep === index,
          completed: currentStep > index,
        }"
      >
        <div class="step-number">{{ index + 1 }}</div>
        <div class="step-label">{{ step }}</div>
        <div v-if="index < steps.length - 1" class="step-line"></div>
      </div>
    </div>

    <!-- 步骤内容 -->
    <div class="step-content">
      <!-- 步骤1: 选择文章 -->
      <div v-show="currentStep === 0" class="step-panel">
        <h2>选择要发布的文章</h2>
        <div class="filter-bar">
          <el-select
            v-model="filterProjectId"
            placeholder="全部项目"
            clearable
            style="width: 200px;"
            size="small"
            @change="loadArticles"
          >
            <!-- 🌟 修复：使用空字符串作为保底值，避免 null 导致渲染错误 -->
            <el-option label="全部项目" :value="''" />
            <el-option
              v-for="p in validProjects"
              :key="p.id"
              :label="p.name"
              :value="p?.id || 0"
            />
          </el-select>

          <el-button @click="loadArticles" size="small">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>

        <div v-loading="articlesLoading" class="article-selector">
          <div
            v-for="article in (articles || [])"
            :key="article?.id || Math.random()"
            class="article-option"
            :class="{
              selected: selectedArticles.includes(article?.id),
              disabled: !isPublishable(article),
              'is-published': article?.publish_status === 'published'
            }"
            @click="article?.id && toggleArticle(article.id)"
          >
            <el-checkbox :model-value="selectedArticles.includes(article?.id)" @click.stop :disabled="!isPublishable(article)" />
            <!-- 🌟 已发布锁定图标 -->
            <div v-if="article?.publish_status === 'published'" class="published-lock-icon">
              <el-icon><Lock /></el-icon>
            </div>
            <div class="article-info">
              <div class="article-header">
                <h4>{{ article?.title || '无标题' }}</h4>
                <div class="article-meta">
                  <el-tag :type="getGenerateStatusType(article?.publish_status)" size="small">
                    {{ getGenerateStatusText(article?.publish_status) }}
                  </el-tag>
                  <el-tag v-if="article?.quality_score" type="info" size="small">
                    评分: {{ article.quality_score }}
                  </el-tag>
                </div>
              </div>
              <p>{{ getPreview(article?.content) }}</p>
            </div>
          </div>
        </div>

        <div v-if="!articlesLoading && articles.length === 0" class="empty-state">
          <el-empty description="暂无可发布的文章" />
        </div>
      </div>

      <!-- 步骤2: 选择账号 -->
      <div v-show="currentStep === 1" class="step-panel">
        <h2>选择发布账号</h2>

        <!-- 无账号提示 -->
        <div v-if="accountsLoading" class="loading-tip">
          <el-icon class="is-loading"><Loading /></el-icon>
          加载账号中...
        </div>
        <div v-if="!accountsLoading && accounts.length === 0" class="empty-state">
          <el-empty description="暂无授权账号，请先去授权">
            <el-button type="primary" @click="router.push('/account')">
              去授权账号
            </el-button>
          </el-empty>
        </div>

        <el-collapse v-model="activeCollapseNames" accordion class="platform-collapse">
          <el-collapse-item
            v-for="platform in platformsWithAccounts"
            :key="platform.id"
            :name="platform.id"
            class="platform-collapse-item"
          >
            <template #title>
              <div class="platform-collapse-header">
                <div
                  class="platform-badge"
                  :style="{ background: platform.color }"
                >
                  {{ platform.code }}
                </div>
                <h3>{{ platform.name }}</h3>
                <span class="account-count">({{ platformAccounts(platform.id).length }})</span>
                <div class="header-actions">
                  <el-checkbox
                    :model-value="allAccountsSelected(platform.id)"
                    @change="(val: boolean) => togglePlatformAccounts(platform.id, val)"
                  >
                    全选
                  </el-checkbox>
                </div>
              </div>
            </template>

            <template #default>
              <div class="account-list-expanded">
                <div
                  v-for="account in platformAccounts(platform.id)"
                  :key="account.id"
                  class="account-option"
                  :class="{ selected: selectedAccounts.includes(account.id) }"
                  @click="toggleAccount(account.id)"
                >
                  <el-checkbox
                    :model-value="selectedAccounts.includes(account.id)"
                    @click.stop
                  />
                  <span class="account-name">{{ account.account_name }}</span>
                  <span v-if="account.remark" class="account-remark">({{ account.remark }})</span>
                </div>
              </div>
            </template>
          </el-collapse-item>
        </el-collapse>
      </div>

      <!-- 步骤3: 确认发布 -->
      <div v-show="currentStep === 2" class="step-panel">
        <h2>确认发布信息</h2>
        <div class="confirm-info">
          <div class="info-section">
            <h3>待发布文章 ({{ selectedArticleList?.length || 0 }})</h3>
            <ul>
              <li v-for="article in (selectedArticleList || [])" :key="article?.id || Math.random()">
                {{ article?.title || '无标题' }}
              </li>
            </ul>
          </div>
          <div class="info-section">
            <h3>目标账号 ({{ selectedAccounts?.length || 0 }})</h3>
            <div class="platform-summary">
              <div
                v-for="platform in (platformSummary || [])"
                :key="platform?.id || Math.random()"
                class="summary-item"
              >
                <span class="platform-name">{{ platform?.name || '未知' }}</span>
                <span class="account-count">{{ platform?.count || 0 }} 个账号</span>
              </div>
            </div>
          </div>
          <div class="info-section">
            <h3>预计生成 {{ (selectedArticleList?.length || 0) * (selectedAccounts?.length || 0) }} 个发布任务</h3>
          </div>
          <div class="info-section publish-mode-section">
            <h3>发布方式</h3>
            <el-radio-group v-model="publishMode" size="default">
              <el-radio value="immediate" border>
                <div class="publish-mode-option">
                  <div class="mode-title">立即发布</div>
                  <div class="mode-desc">点击后立即开始发布</div>
                </div>
              </el-radio>
              <el-radio value="scheduled" border>
                <div class="publish-mode-option">
                  <div class="mode-title">定时发布</div>
                  <div class="mode-desc">设置发布时间，系统自动执行</div>
                </div>
              </el-radio>
            </el-radio-group>
            <el-date-picker
              v-if="publishMode === 'scheduled'"
              v-model="scheduledTime"
              type="datetime"
              placeholder="选择定时发布时间"
              :disabled-date="disabledDate"
              :disabled-hours="disabledHours"
              :disabled-minutes="disabledMinutes"
              format="YYYY-MM-DD HH:mm:ss"
              value-format="YYYY-MM-DDTHH:mm:ss"
              style="margin-top: 16px; width: 100%;"
            />
          </div>
        </div>
      </div>

      <!-- 步骤4: 发布进度 -->
      <div v-show="currentStep === 3" class="step-panel">
        <h2>发布进度</h2>
        <div class="progress-summary">
          <div class="progress-stat">
            <span class="stat-value">{{ publishProgress?.completed || 0 }}</span>
            <span class="stat-label">已完成</span>
          </div>
          <div class="progress-stat">
            <span class="stat-value">{{ publishProgress?.total || 0 }}</span>
            <span class="stat-label">总数</span>
          </div>
          <div class="progress-stat">
            <span class="stat-value">{{ publishProgress?.failed || 0 }}</span>
            <span class="stat-label">失败</span>
          </div>
        </div>
        <el-progress
          :percentage="progressPercentage"
          :status="progressStatus"
          class="main-progress"
        />
        <div class="task-list">
          <div
            v-for="task in (publishTasks || [])"
            :key="task?.id || Math.random()"
            class="task-item"
            :class="`status-${task?.status}`"
          >
            <div class="task-info">
              <span class="task-article">{{ task?.articleTitle || '未知任务' }}</span>
              <span class="task-arrow">→</span>
              <el-tag :color="getPlatformColor(task?.platform)" size="small">
                {{ task?.platformName || '未知' }}
              </el-tag>
              <span class="task-account">{{ task?.accountName || '未知账号' }}</span>
            </div>
            <div class="task-status">
              <el-icon v-if="task?.status === 0" class="is-loading"><Loading /></el-icon>
              <el-icon v-else-if="task?.status === 2" color="#4caf50"><CircleCheck /></el-icon>
              <el-icon v-else-if="task?.status === 3" color="#f44336"><CircleClose /></el-icon>
              <span v-if="task?.errorMsg" class="error-msg">{{ task.errorMsg }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部操作栏 -->
    <div class="action-bar">
      <el-button v-if="currentStep > 0 && currentStep < 3" @click="prevStep">
        上一步
      </el-button>
      <div class="action-right">
        <el-button v-if="currentStep === 0" type="primary" :disabled="selectedArticles.length === 0" @click="nextStep">
          下一步 ({{ selectedArticles.length }})
        </el-button>
        <el-button v-if="currentStep === 1" type="primary" :disabled="selectedAccounts.length === 0" @click="nextStep">
          下一步 ({{ selectedAccounts.length }})
        </el-button>
        <el-button v-if="currentStep === 2" type="primary" @click="startPublish" :loading="publishing">
          开始发布
        </el-button>
        <el-button v-if="currentStep === 3" type="primary" @click="finishPublish">
          完成
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useWebSocket } from '@/composables/useWebSocket'
import { Loading, CircleCheck, CircleClose, Refresh, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { geoKeywordApi, geoArticleApi, publishApi, accountApi } from '@/services/api'
import { PLATFORMS } from '@/core/config/platform'

const router = useRouter()
const route = useRoute()

// WebSocket 连接
const { connect, disconnect, onPublishProgress } = useWebSocket()

// 平台列表（数组形式，方便遍历）
const PLATFORMS_LIST = Object.values(PLATFORMS)

// 步骤
const steps = ['选择文章', '选择账号', '确认发布', '发布进度']
const currentStep = ref(0)

// 选择状态
const selectedArticles = ref<number[]>([])
const selectedAccounts = ref<number[]>([])

// 文章数据
const articles = ref<any[]>([])
const articlesLoading = ref(false)
const projects = ref<any[]>([])

// 发布状态
const publishing = ref(false)
const publishProgress = ref({ completed: 0, total: 0, failed: 0 })
const publishTasks = ref<any[]>([])

// 发布方式：immediate=立即发布, scheduled=定时发布
const publishMode = ref<'immediate' | 'scheduled'>('immediate')
const scheduledTime = ref<string>('')

// 账号数据
const accounts = ref<any[]>([])
const accountsLoading = ref(false)

// 平台展开/收起状态（使用数组管理）
const activeCollapseNames = ref<string[]>([])

// 初始化：默认展开第一个有账号的平台
const initializeCollapsedStates = () => {
  activeCollapseNames.value = []
  PLATFORMS_LIST.forEach((platform: any) => {
    const platformAccounts = accounts.value.filter(a => a.platform === platform.id && a.status === 1)
    if (platformAccounts.length > 0) {
      activeCollapseNames.value.push(platform.id)
    }
  })
}

// 过滤
const filterProjectId = ref<number | null>(null)

// 平台列表
const platforms = Object.values(PLATFORMS)

// 平台 ID 映射：处理后端返回的 platform ID 与前端平台名的对应关系
// 例如：后端返回 'zhihu'，需要映射到 '知乎' 平台
const PLATFORM_ID_MAPPING: Record<string, string> = {
  'zhihu': 'zhihu',
  'sohu': 'sohu',
  'baijiahao': 'baijiahao',
  'toutiao': 'toutiao',
  'bilibili': 'bilibili',
  'xigua': 'xigua',
  'weibo': 'weibo',
  'dayu': 'dayu',
  'xueqiu': 'xueqiu',
  'iqiyi': 'iqiyi',
  'huxiu': 'huxiu',
  'douyin': 'douyin',
  'kuaishou': 'kuaishou',
  'haokan': 'haokan',
  'pipixia': 'pipixia',
  'meipai': 'meipai',
  'wenku': 'wenku',
  'douban': 'douban',
  'weixin': 'weixin',
  'douyin_company': 'douyin_company',
  '36kr': '36kr',
  'acfun': 'acfun',
  'video_account': 'video_account',
  'sohu_video': 'sohu_video',
  'jianshu': 'jianshu',
  'yidian': 'yidian',
  'chejia': 'chejia',
  'alipay': 'alipay',
  'xiaohongshu': 'xiaohongshu',
  'ximalaya': 'ximalaya',
  'meituan': 'meituan',
  'haokan_bili': 'haokan',
  'penguin': 'penguin',
  'woshipm': 'woshipm',
  'dafeng': 'dafeng'
}

// 规范化平台 ID：将后端返回的 platform ID 转换为前端平台名
const normalizePlatformId = (platformId: string | undefined): string => {
  if (!platformId || platformId === '') return ''
  return PLATFORM_ID_MAPPING[platformId] || platformId
}

// 监听账号列表变化，自动更新折叠状态
watch(accounts, () => {
  initializeCollapsedStates()
})

onMounted(async () => {
  // 连接 WebSocket
  connect()

  // 监听发布进度事件
  onPublishProgress((progressData: any) => {
    // === 显微镜日志 ===
    console.log("=== 收到WS原始消息 ===", progressData);
    // 🌟 修复：强制字符串对比，解决数字 vs 字符串 ID 匹配问题
    const target = articles.value.find(a => String(a.id) === String(progressData.article_id));
    console.log("=== 匹配到的文章对象 ===", target ? JSON.parse(JSON.stringify(target)) : null);
    // =================

    // 1. 更新对应的任务状态
    // 🌟 修复：强制字符串对比
    const taskIndex = publishTasks.value.findIndex(t =>
      String(t.articleId) === String(progressData.article_id) && String(t.accountId) === String(progressData.account_id)
    )

    if (taskIndex !== -1) {
      const task = publishTasks.value[taskIndex]
      const oldStatus = task.status

      // 更新任务状态
      task.status = progressData.status
      task.errorMsg = progressData.error_msg || null

      // 更新进度统计
      if (oldStatus === 0 && (progressData.status === 2 || progressData.status === 3)) {
        publishProgress.value.completed++
        if (progressData.status === 3) {
          publishProgress.value.failed++
        }
      }

      // 检查是否所有任务都已完成
      if (publishProgress.value.completed >= publishProgress.value.total) {
        publishing.value = false
      }
    }

    // 🌟 2. 同步更新 articles 数组中的文章状态
    // 这样"选择文章"列表中的标签会立即变色
    if (progressData.article_id) {
      // 🌟 修复：强制字符串对比
      const targetArticle = articles.value.find(a => String(a.id) === String(progressData.article_id))
      if (targetArticle) {
        const oldStatus = targetArticle.publish_status
        // 如果后端返回了 publish_status，使用它；否则根据 status 推断
        const newStatus = progressData.publish_status || (progressData.status === 2 ? 'published' : 'failed')
        targetArticle.publish_status = newStatus

        // 如果有 platform_url，也更新
        if (progressData.platform_url) {
          targetArticle.platform_url = progressData.platform_url
        }

        // 🌟 强制触发 Vue 深度响应式更新，确保标签立即变色
        articles.value = [...articles.value]

        console.log(`[PublishPage] 文章状态已同步: article_id=${progressData.article_id}, ${oldStatus} -> ${newStatus}`)

        // === 状态回滚补丁：失败时显示错误提示 ===
        if (progressData.status === 3 || newStatus === 'failed') {
          ElMessage.error('发布失败：' + (progressData.error_msg || '未知错误'))
        }
      }
    }

    // 🌟 3. 自动清理选中状态：当发布成功后，从 selectedArticles 中移除该文章
    if (progressData.status === 2 && progressData.article_id) {
      const selectedIndex = selectedArticles.value.indexOf(progressData.article_id)
      if (selectedIndex !== -1) {
        selectedArticles.value.splice(selectedIndex, 1)
        console.log(`[PublishPage] 已从选中列表移除已发布的文章: article_id=${progressData.article_id}`)
      }
    }
  })

  // 从路由参数中获取过滤条件
  if (route.query.projectId) {
    filterProjectId.value = Number(route.query.projectId) as number
  }
  await loadProjects()
  await loadArticles()
  await loadAccounts()
})

// 组件卸载时断开 WebSocket
onUnmounted(() => {
  disconnect()
})

// 计算属性
const validProjects = computed(() => {
  return (projects.value || []).filter(p => p?.id !== undefined && p?.id !== null)
})

const selectedArticleList = computed(() => {
  return articles.value.filter(a => selectedArticles.value.includes(a.id))
})

const selectedAccountList = computed(() => {
  return accounts.value.filter(a => selectedAccounts.value.includes(a.id))
})

const platformSummary = computed(() => {
  const summary: any[] = []
  selectedAccountList.value.forEach(account => {
    const platform = PLATFORMS[account.platform]
    const existing = summary.find(s => s.id === account.platform)
    if (existing) {
      existing.count++
    } else {
      summary.push({
        id: account.platform,
        name: platform?.name || account.platform,
        count: 1,
      })
    }
  })
  return summary
})

const progressPercentage = computed(() => {
  if (publishProgress.value.total === 0) return 0
  return Math.round((publishProgress.value.completed / publishProgress.value.total) * 100)
})

const progressStatus = computed(() => {
  if (publishProgress.value.failed > 0) return 'exception'
  if (progressPercentage.value === 100) return 'success'
  return undefined
})

// 判断文章是否可发布
// 🌟 允许 completed、scheduled 或 failed 状态的文章可以被勾选发布
// 已发布(published)或正在发布(publishing)的文章必须锁定，不可重复操作
// failed 状态的文章可以被重新勾选进行重试
const isPublishable = (article: any) => {
  if (!article) return false
  // 只允许 completed、scheduled 或 failed 状态的文章被勾选
  // published 或 publishing 状态的文章必须返回 false
  return ['completed', 'scheduled', 'failed'].includes(article.publish_status)
}

// 计算属性 - 获取有账号的平台列表
const platformsWithAccounts = computed(() => {
  const platformsWithData: any[] = []
  PLATFORMS_LIST.forEach((platform: any) => {
    const platformAccounts = accounts.value.filter((a: any) => {
      return a.platform === platform.id && a.status === 1
    })
    if (platformAccounts.length > 0) {
      platformsWithData.push(platform)
    }
  })
  return platformsWithData
})

// 方法
const platformAccounts = (platformId: string) => {
  return accounts.value.filter(a => {
    return a.platform === platformId && a.status === 1
  })
}

const allAccountsSelected = (platformId: string) => {
  const platformAccs = platformAccounts(platformId)
  return platformAccs.length > 0 && platformAccs.every(a => selectedAccounts.value.includes(a.id))
}

// 切换平台展开/收起状态（现在由 el-collapse 自动管理）
// const togglePlatformCollapse = (platformId: string) => {
//   collapsedPlatforms.value[platformId] = !collapsedPlatforms.value[platformId]
// }

// 加载数据
const loadProjects = async () => {
  try {
    const res: any = await geoKeywordApi.getProjects()
    projects.value = Array.isArray(res) ? res : (res?.data || [])
  } catch (error) {
    console.error('加载项目失败:', error)
    projects.value = [] // 确保始终是数组
  }
}

const loadArticles = async () => {
  articlesLoading.value = true
  try {
    // 获取状态为 completed、scheduled、published 或 failed 的文章
    // published 状态的文章也显示在列表中，方便用户查看发布状态
    // failed 状态的文章也需要显示，允许用户重新发布
    const params: any = { publish_status: ['completed', 'scheduled', 'published', 'failed'] }
    if (filterProjectId.value !== null) {
      // 传递 project_id 参数，后端通过 join Keyword 表进行过滤
      params.project_id = filterProjectId.value
    }
    const res: any = await geoArticleApi.getArticles(params)
    articles.value = Array.isArray(res) ? res : (res?.data || res?.items || [])
  } catch (error) {
    console.error('[PublishPage] 加载文章失败:', error)
    ElMessage.error('加载文章失败')
    articles.value = [] // 确保始终是数组
  } finally {
    articlesLoading.value = false
  }
}

const loadAccounts = async () => {
  accountsLoading.value = true
  try {
    const res: any = await accountApi.getList({ status: 1 })
    accounts.value = Array.isArray(res) ? res : (res?.data || [])
  } catch (error) {
    console.error('[PublishPage] 加载账号失败:', error)
    ElMessage.error('加载账号失败')
    accounts.value = [] // 确保始终是数组
  } finally {
    accountsLoading.value = false
  }
}

const toggleArticle = (id: number) => {
  const index = selectedArticles.value.indexOf(id)
  if (index === -1) {
    selectedArticles.value.push(id)
  } else {
    selectedArticles.value.splice(index, 1)
  }
}

const toggleAccount = (id: number) => {
  const index = selectedAccounts.value.indexOf(id)
  if (index === -1) {
    selectedAccounts.value.push(id)
  } else {
    selectedAccounts.value.splice(index, 1)
  }
}

const togglePlatformAccounts = (platformId: string, checked: boolean) => {
  const platformAccs = platformAccounts(platformId).filter(a => a.status === 1)
  platformAccs.forEach(account => {
    const index = selectedAccounts.value.indexOf(account.id)
    if (checked && index === -1) {
      selectedAccounts.value.push(account.id)
    } else if (!checked && index !== -1) {
      selectedAccounts.value.splice(index, 1)
    }
  })
}

const nextStep = () => {
  if (currentStep.value === 0 && selectedArticles.value.length === 0) {
    ElMessage.warning('请至少选择一篇文章')
    return
  }
  if (currentStep.value === 1 && selectedAccounts.value.length === 0) {
    ElMessage.warning('请至少选择一个账号')
    return
  }
  currentStep.value++
}

const prevStep = () => {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

const startPublish = async () => {
  if (selectedArticleList.value.length === 0 || selectedAccounts.value.length === 0) {
    ElMessage.warning('请先选择文章和账号')
    return
  }

  // 如果是定时发布，必须选择时间
  if (publishMode.value === 'scheduled' && !scheduledTime.value) {
    ElMessage.warning('请选择定时发布时间')
    return
  }

  publishing.value = true

  // 初始化发布任务
  const tasks: any[] = []
  selectedArticleList.value.forEach(article => {
    selectedAccountList.value.forEach(account => {
      tasks.push({
        id: `${article.id}-${account.id}`,
        articleId: article.id,
        articleTitle: article.title,
        accountId: account.id,
        accountName: account.account_name,
        platform: account.platform,
        platformName: PLATFORMS[account.platform]?.name || account.platform,
        status: 0, // 0=发布中, 2=成功, 3=失败
        errorMsg: null,
      })
    })
  })

  publishTasks.value = tasks
  publishProgress.value = { completed: 0, total: tasks.length, failed: 0 }

  currentStep.value = 3

  // 根据发布方式调用不同的 API
  try {
    let response: any
    let message = ''

    if (publishMode.value === 'immediate') {
      // 立即发布
      response = await publishApi.start({
        article_ids: selectedArticles.value,
        account_ids: selectedAccounts.value
      })
      message = '立即发布任务已创建，正在执行中'
    } else {
      // 定时发布
      response = await publishApi.schedule({
        article_ids: selectedArticles.value,
        account_ids: selectedAccounts.value,
        scheduled_time: scheduledTime.value
      })
      message = `定时发布已配置，将在 ${new Date(scheduledTime.value).toLocaleString('zh-CN')} 执行`
    }

    const data = response.data || response

    if (data.success !== false) {
      ElMessage.success(message)
      if (publishMode.value === 'immediate') {
        // 立即发布：监听 WebSocket 进度
        // 进度将由后端通过 publish_progress 事件实时推送
      } else {
        // 定时发布，直接完成
        publishing.value = false
        publishProgress.value = { completed: tasks.length, total: tasks.length, failed: 0 }
        publishTasks.value = tasks.map(t => ({ ...t, status: 2 }))
      }
    } else {
      ElMessage.error(data.message || '创建发布任务失败')
      publishing.value = false
      currentStep.value = 2
    }
  } catch (e: any) {
    console.error('发布失败:', e)
    ElMessage.error('发布失败，请检查后端服务')
    publishing.value = false
    currentStep.value = 2
  }
}

const finishPublish = () => {
  ElMessage.success('发布任务已完成')
  // 🌟 修复：路由路径是 /history（不是 /publish/history）
  // 或者跳转到 GEO 文章列表 /geo/articles
  router.push('/history')
}

const getPreview = (content: string) => {
  if (!content) return '暂无内容'
  const text = content.replace(/<[^>]*>/g, '')
  return text.length > 50 ? text.substring(0, 50) + '...' : text
}

const getPlatformColor = (platform: string) => {
  return PLATFORMS[platform]?.color || '#666'
}

const getGenerateStatusType = (s: string) => {
  const statusMap: Record<string, string> = {
    generating: 'warning',     // 生成中
    completed: 'success',      // 已生成/待分发
    scheduled: 'primary',      // 已配置定时发布
    failed: 'danger',         // 生成/发布失败
    publishing: 'primary',     // 发布中
    published: 'success',     // 已发布
    draft: 'info'              // 草稿
  }
  return statusMap[s] || 'info'
}

const getGenerateStatusText = (s: string) => {
  const textMap = {
    generating: '生成中',
    completed: '已生成/待分发',
    scheduled: '已配置定时发布',
    failed: '发布失败/待重试',
    publishing: '发布中',
    published: '已发布',
    draft: '草稿',
    0: '发布中',
    1: '排队中',
    2: '发布成功',
    3: '发布失败'
  }
  return textMap[s] || s || '未知状态'
}

// 日期选择器辅助方法 - 禁用过去日期
const disabledDate = (time: Date) => {
  // 不能选择今天之前的时间
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return time.getTime() < today.getTime()
}

// 日期选择器辅助方法 - 禁用过去的小时
const disabledHours = (hour: number) => {
  const now = new Date()
  const selectedDate = scheduledTime.value ? new Date(scheduledTime.value) : now
  // 如果选择的是今天，禁用已经过去的小时
  if (selectedDate.toDateString() === now.toDateString()) {
    return hour < now.getHours()
  }
  return []
}

// 日期选择器辅助方法 - 禁用过去的分钟
const disabledMinutes = (hour: number, minute: number) => {
  const now = new Date()
  const selectedDate = scheduledTime.value ? new Date(scheduledTime.value) : now
  // 如果选择的是今天且小时相同，禁用已经过去的分钟
  if (selectedDate.toDateString() === now.toDateString() && hour === now.getHours()) {
    return minute < now.getMinutes()
  }
  return []
}
</script>

<style scoped lang="scss">
.publish-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #1e1e1e;
  padding: 24px;
}

// 步骤指示器
.steps {
  display: flex;
  justify-content: center;
  padding: 24px 0;
  position: relative;

  .step-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    position: relative;
    flex: 1;

    .step-number {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: var(--bg-tertiary, #2a2a2a);
      border: 2px solid var(--border, #3a3a3a);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 600;
      z-index: 1;
      transition: all 0.3s;
    }

    .step-label {
      margin-top: 8px;
      font-size: 14px;
      color: var(--text-secondary, #6b7280);
    }

    .step-line {
      position: absolute;
      top: 20px;
      left: 50%;
      width: 100%;
      height: 2px;
      background: var(--border, #3a3a3a);
      z-index: 0;
    }

    &.active {
      .step-number {
        background: var(--primary, #1890ff);
        border-color: var(--primary, #1890ff);
        color: white;
      }

      .step-label {
        color: var(--primary, #1890ff);
      }
    }

    &.completed {
      .step-number {
        background: #4caf50;
        border-color: #4caf50;
        color: white;
      }
    }

    &:last-child .step-line {
      display: none;
    }
  }
}

// 步骤内容
.step-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px 0;
}

.step-panel {
  h2 {
    margin: 0 0 20px 0;
    font-size: 18px;
    color: var(--text-primary, #fff);
  }
}

// 过滤栏
.filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
}

// 文章选择器
.article-selector {
  display: flex;
  flex-direction: column;
  gap: 12px;

  .article-option {
    display: flex;
    align-items: flex-start;
    gap: 16px;
    background: var(--bg-secondary, #2a2a2a);
    border: 2px solid transparent;
    border-radius: 12px;
    padding: 16px;
    cursor: pointer;
    transition: all 0.2s;

    &:hover:not(.disabled) {
      background: var(--bg-tertiary, #3a3a3a);
    }

    &.selected {
      border-color: var(--primary, #1890ff);
      background: rgba(24, 144, 226, 0.1);
    }

    &.disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    // 🌟 已发布文章样式：半透明 + 锁定图标
    &.is-published {
      opacity: 0.7;
      background: rgba(76, 175, 80, 0.15);
      border-color: rgba(76, 175, 80, 0.3);
      position: relative;

      &:hover {
        background: rgba(76, 175, 80, 0.15);
      }
    }

    .published-lock-icon {
      position: absolute;
      top: 12px;
      right: 12px;
      width: 32px;
      height: 32px;
      background: rgba(76, 175, 80, 0.2);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 10;
      color: #4caf50;
    }

    .article-header {
      flex: 1;

      h4 {
        margin: 0 0 8px 0;
        color: var(--text-primary, #fff);
        font-weight: 500;
        font-size: 16px;
      }

      .article-meta {
        display: flex;
        gap: 8px;
        align-items: center;
      }
    }

    p {
      margin: 0;
      font-size: 14px;
      color: var(--text-secondary, #6b7280);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
}

.empty-state {
  padding: 40px 0;
  text-align: center;
}

.loading-tip {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text-secondary, #6b7280);
  padding: 40px 0;

  .is-loading {
    animation: rotate 1s linear infinite;
  }
}

// 平台分组折叠面板
.platform-collapse {
  margin-top: 8px;

  :deep(.el-collapse-item) {
    background: var(--bg-secondary, #2a2a2a);
    border-radius: 12px;
    margin-bottom: 12px;
    overflow: hidden;
    transition: all 0.3s;

    &:hover {
      background: var(--bg-tertiary, #3a3a3a);
    }

    &.is-active {
      border-color: var(--primary, #1890ff);
    }

    .el-collapse-item__header {
      height: auto;
      min-height: 60px;
      padding: 0;
      border: none;
      background: transparent;
    }

    .el-collapse-item__wrap {
      border: none;
    }
  }

  .platform-collapse-header {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    padding: 16px 20px;

    .platform-badge {
      width: 40px;
      height: 40px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
      font-weight: 600;
      color: white;
    }

    h3 {
      margin: 0;
      flex: 1;
      color: var(--text-primary, #fff);
      font-size: 16px;
    }

    .account-count {
      font-size: 13px;
      color: var(--text-secondary, #6b7280);
    }

    .header-actions {
      margin-left: auto;
    }
  }
}

// 展开的账号列表
.account-list-expanded {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 0 20px 20px;

  .account-option {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      background: var(--bg-tertiary, #3a3a3a);
    }

    &.selected {
      background: rgba(74, 144, 226, 0.15);
      border: 1px solid var(--primary, #1890ff);
    }

    .account-name {
      flex: 1;
      font-size: 14px;
      color: var(--text-primary, #fff);
    }

    .account-remark {
      font-size: 12px;
      color: var(--text-secondary, #6b7280);
    }

    :deep(.el-checkbox) {
      --el-checkbox-bg-color: transparent;
      --el-checkbox-border-color: var(--border, #3a3a3a);
      --el-checkbox-disabled-border-color: var(--border, #3a3a3a);
    }
  }
}

// 确认信息
.confirm-info {
  .info-section {
    background: var(--bg-secondary, #2a2a2a);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;

    h3 {
      margin: 0 0 12px 0;
      font-size: 16px;
      color: var(--text-primary, #fff);
    }

    ul {
      margin: 0;
      padding-left: 20px;
      color: var(--text-secondary, #6b7280);

      li {
        margin-bottom: 8px;
      }
    }

    .platform-summary {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;

      .summary-item {
        background: var(--bg-tertiary, #3a3a3a);
        border-radius: 8px;
        padding: 12px;
        text-align: center;

        .platform-name {
          display: block;
          font-size: 12px;
          color: var(--text-secondary, #6b7280);
          margin-bottom: 4px;
        }

        .account-count {
          display: block;
          font-size: 18px;
          font-weight: 600;
          color: var(--primary, #1890ff);
        }
      }
    }
  }

  // 发布方式选择
  .publish-mode-section {
    :deep(.el-radio-group) {
      display: flex;
      gap: 16px;
      width: 100%;
    }

    :deep(.el-radio.is-bordered) {
      flex: 1;
      height: auto;
      padding: 16px;
      border-color: var(--border, #3a3a3a);
      background: var(--bg-tertiary, #3a3a3a);
      transition: all 0.2s;

      &:hover {
        border-color: var(--primary, #1890ff);
      }

      &.is-checked {
        border-color: var(--primary, #1890ff);
        background: rgba(24, 144, 226, 0.1);
      }

      .el-radio__label {
        padding: 0;
        width: 100%;
      }
    }

    .publish-mode-option {
      display: flex;
      flex-direction: column;
      gap: 4px;

      .mode-title {
        font-size: 16px;
        font-weight: 600;
        color: var(--text-primary, #fff);
      }

      .mode-desc {
        font-size: 13px;
        color: var(--text-secondary, #6b7280);
      }
    }
  }
}

// 发布进度
.progress-summary {
  display: flex;
  gap: 40px;
  margin-bottom: 24px;

  .progress-stat {
    text-align: center;

    .stat-value {
      display: block;
      font-size: 32px;
      font-weight: 700;
      color: var(--primary, #1890ff);
    }

    .stat-label {
      font-size: 14px;
      color: var(--text-secondary, #6b7280);
    }
  }
}

.main-progress {
  margin-bottom: 24px;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 8px;

  .task-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: var(--bg-secondary, #2a2a2a);
    border-radius: 8px;
    padding: 12px 16px;

    .task-info {
      display: flex;
      align-items: center;
      gap: 12px;

      .task-article {
        font-weight: 500;
      }

      .task-arrow {
        color: var(--text-secondary, #6b7280);
      }

      .task-account {
        color: var(--text-secondary, #6b7280);
      }
    }

    .task-status {
      display: flex;
      align-items: center;
      gap: 8px;

      .error-msg {
        font-size: 12px;
        color: #f44336;
      }
    }

    &.status-2 {
      border-left: 3px solid #4caf50;
    }

    &.status-3 {
      border-left: 3px solid #f44336;
    }
  }
}

// 操作栏
.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 0;
  border-top: 1px solid var(--border, #3a3a3a);
}

.action-right {
  display: flex;
  gap: 12px;
}
</style>
