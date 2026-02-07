<template>
  <div class="scheduler-page">
    <!-- 头部 -->
    <header class="page-header">
      <div class="header-left">
        <div class="header-icon">
          <el-icon><Timer /></el-icon>
        </div>
        <div class="header-text">
          <h1 class="page-title">定时任务调度中心</h1>
          <p class="page-desc">动态管理后台任务频率，无需重启服务即刻生效</p>
        </div>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="loadTasks" :loading="loading">
          <el-icon class="mr-1"><Refresh /></el-icon> 刷新状态
        </el-button>
      </div>
    </header>

    <!-- 任务列表 -->
    <div class="tasks-section">
      <el-table
        :data="tasks"
        v-loading="loading"
        style="width: 100%"
        :header-cell-style="{ background: '#f9fafb', color: '#606266' }"
      >
        <el-table-column prop="name" label="任务名称" width="200">
          <template #default="{ row }">
            <span class="task-name">{{ row.name }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="description" label="功能描述" min-width="280">
          <template #default="{ row }">
            <span class="task-desc">{{ row.description }}</span>
          </template>
        </el-table-column>

        <el-table-column label="执行策略" width="180">
          <template #default="{ row }">
            <el-tag :type="getCronTagType(row.cron_expression)" class="strategy-tag">
              {{ getCronChinese(row.cron_expression) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="运行状态" width="140">
          <template #default="{ row }">
            <div class="status-cell">
              <div class="breathing-indicator" :class="{ active: row.is_active }"></div>
              <span class="status-text">{{ row.is_active ? '运行中' : '已停止' }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openEdit(row)">
              <el-icon class="mr-1"><Edit /></el-icon> 调整策略
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 修改频率对话框 -->
    <el-dialog
      v-model="showEditDialog"
      title="调整执行策略"
      width="520px"
      destroy-on-close
      class="strategy-dialog"
    >
      <el-form label-width="100px" class="edit-form">
        <el-form-item label="任务名称">
          <el-input v-model="currentTask.name" disabled />
        </el-form-item>

        <!-- 预设策略卡片 -->
        <el-form-item label="执行策略">
          <div class="preset-cards">
            <div
              v-for="preset in presetStrategies"
              :key="preset.value"
              class="preset-card"
              :class="{ active: currentStrategy === preset.value }"
              @click="selectStrategy(preset.value)"
            >
              <div class="card-icon">
                <el-icon>
                  <component :is="preset.icon" />
                </el-icon>
              </div>
              <div class="card-content">
                <div class="card-title">{{ preset.label }}</div>
                <div class="card-desc">{{ preset.desc }}</div>
              </div>
              <div class="card-check" v-if="currentStrategy === preset.value">
                <el-icon><Check /></el-icon>
              </div>
            </div>
          </div>
        </el-form-item>

        <!-- 开发者模式开关 -->
        <div class="dev-mode-section">
          <el-switch
            v-model="devMode"
            inline-prompt
            active-text="开发者模式"
            inactive-text="普通模式"
            size="small"
          />
          <span class="dev-hint">开启后可自定义 Cron 表达式</span>
        </div>

        <!-- 原始 Cron 输入框（仅开发者模式显示） -->
        <el-form-item label="Cron表达式" v-if="devMode">
          <el-input v-model="currentTask.cron_expression" placeholder="例如: */5 * * * *" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="saveCron" :loading="saving">保存并生效</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Timer, Refresh, Edit, Check, Lightning, Timer as TimerIcon, Moon } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

// 假设后端地址，如果配置了代理可以直接写 /api/...
const API_BASE = 'http://127.0.0.1:8001/api/scheduler'

interface Task {
  id: number
  name: string
  task_key: string
  cron_expression: string
  is_active: boolean
  description: string
}

interface StrategyPreset {
  value: string
  label: string
  desc: string
  icon: any
  type: string
}

const tasks = ref<Task[]>([])
const loading = ref(false)
const saving = ref(false)
const showEditDialog = ref(false)
const currentTask = ref<any>({})
const devMode = ref(false)

// 当前选择的策略
const currentStrategy = computed(() => {
  return currentTask.value.cron_expression || ''
})

// 预设策略配置
const presetStrategies: StrategyPreset[] = [
  {
    value: '*/1 * * * *',
    label: '极速模式',
    desc: '每分钟扫描',
    icon: Lightning,
    type: 'danger'
  },
  {
    value: '*/5 * * * *',
    label: '平衡模式',
    desc: '每5分钟扫描',
    icon: TimerIcon,
    type: 'warning'
  },
  {
    value: '0 * * * *',
    label: '稳健模式',
    desc: '每小时执行',
    icon: Moon,
    type: 'success'
  },
  {
    value: '0 9 * * *',
    label: '定时模式',
    desc: '每天09:00',
    icon: TimerIcon,
    type: 'info'
  },
  {
    value: '0 2 * * *',
    label: '深夜模式',
    desc: '每天凌晨02:00',
    icon: Moon,
    type: 'info'
  }
]

// 选择策略
const selectStrategy = (cron: string) => {
  currentTask.value.cron_expression = cron
}

// 加载任务列表
const loadTasks = async () => {
  loading.value = true
  try {
    const res = await axios.get(`${API_BASE}/jobs`)
    tasks.value = res.data
  } catch (error) {
    ElMessage.error('无法连接到调度中心')
  } finally {
    loading.value = false
  }
}

// 切换开关状态
const handleStatusChange = async (row: Task) => {
  try {
    await updateTaskApi(row)
    ElMessage.success(row.is_active ? `任务 [${row.name}] 已启动` : `任务 [${row.name}] 已暂停`)
  } catch (error) {
    row.is_active = !row.is_active // 失败则回滚UI状态
    ElMessage.error('状态更新失败')
  }
}

// 打开编辑
const openEdit = (row: Task) => {
  currentTask.value = { ...row }
  devMode.value = false // 重置开发者模式
  showEditDialog.value = true
}

// 保存 Cron 修改
const saveCron = async () => {
  saving.value = true
  try {
    await updateTaskApi(currentTask.value)
    ElMessage.success('执行策略已更新，下次执行将按新规则')
    showEditDialog.value = false
    loadTasks() // 刷新列表
  } catch (error) {
    ElMessage.error('更新失败，请检查设置')
  } finally {
    saving.value = false
  }
}

// 统一更新接口
const updateTaskApi = async (task: Task) => {
  const payload = {
    cron_expression: task.cron_expression,
    is_active: task.is_active
  }
  await axios.put(`${API_BASE}/jobs/${task.id}`, payload)
}

// Cron 转中文描述（完全隐藏原始 Cron）
const getCronChinese = (cron: string): string => {
  const descMap: Record<string, string> = {
    '*/1 * * * *': '每分钟扫描',
    '*/5 * * * *': '每5分钟',
    '0 * * * *': '每小时整点',
    '0 9 * * *': '每天09:00',
    '0 2 * * *': '每天02:00',
    '0 0 * * *': '每天00:00',
    '0 0 * * 1': '每周一00:00',
    '0 0 1 * *': '每月1号00:00'
  }

  // 精确匹配
  if (descMap[cron]) {
    return descMap[cron]
  }

  // 模式匹配
  if (cron.match(/^\*\/\d+ \* \* \* \*$/)) {
    const minutes = cron.match(/^\*\/(\d+)/)?.[1] || ''
    return `每${minutes}分钟`
  }
  if (cron.startsWith('0 */')) {
    const hours = cron.match(/0 \*\/(\d+)/)?.[1] || ''
    return `每${hours}小时`
  }
  if (cron.match(/^0 \d+ \* \* \*$/)) {
    const hour = cron.match(/^0 (\d+)/)?.[1] || ''
    return `每天${hour.padStart(2, '0')}:00`
  }

  return '自定义策略'
}

// 获取标签类型
const getCronTagType = (cron: string): string => {
  if (cron === '*/1 * * * *') return 'danger'      // 红色 - 极速
  if (cron === '*/5 * * * *') return 'warning'     // 橙色 - 平衡
  if (cron.startsWith('0 ') && !cron.includes('/')) return 'success'  // 绿色 - 定时
  if (cron.includes('*/')) return 'info'          // 蓝色 - 周期
  return 'info'                                   // 默认
}

onMounted(() => {
  loadTasks()
})
</script>

<style scoped lang="scss">
.scheduler-page {
  padding: 24px;
  background: #f3f4f6;
  min-height: 100vh;
}

/* 头部样式 */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  margin-bottom: 24px;

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;

    .header-icon {
      width: 48px;
      height: 48px;
      background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-size: 24px;
    }

    .page-title {
      margin: 0 0 4px 0;
      font-size: 20px;
      font-weight: 600;
      color: #1f2937;
    }

    .page-desc {
      margin: 0;
      font-size: 13px;
      color: #6b7280;
    }
  }
}

/* 任务列表区 */
.tasks-section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);

  .task-name {
    font-weight: 600;
    color: #374151;
  }

  .task-desc {
    color: #6b7280;
    font-size: 13px;
  }

  .strategy-tag {
    font-size: 13px;
    padding: 6px 12px;
    border-radius: 6px;
    font-weight: 500;
  }

  // 状态单元格
  .status-cell {
    display: flex;
    align-items: center;
    gap: 8px;

    .status-text {
      font-size: 13px;
      color: #6b7280;
    }

    // 呼吸灯效果
    .breathing-indicator {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: #d1d5db;
      transition: all 0.3s ease;

      &.active {
        background: #10b981;
        animation: breathe 2s ease-in-out infinite;
        box-shadow: 0 0 8px #10b981;
      }
    }
  }

  @keyframes breathe {
    0%, 100% {
      opacity: 1;
      transform: scale(1);
      box-shadow: 0 0 8px #10b981;
    }
    50% {
      opacity: 0.6;
      transform: scale(1.2);
      box-shadow: 0 0 16px #10b981;
    }
  }

  .mr-1 {
    margin-right: 4px;
  }
}

/* 弹窗样式 */
.strategy-dialog {
  .edit-form {
    .preset-cards {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
      width: 100%;

      .preset-card {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        border: 2px solid #e5e7eb;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s ease;
        position: relative;

        &:hover {
          border-color: #6366f1;
          background: rgba(99, 102, 241, 0.05);
        }

        &.active {
          border-color: #6366f1;
          background: rgba(99, 102, 241, 0.1);

          .card-icon {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            color: white;
          }

          .card-title {
            color: #6366f1;
          }
        }

        .card-icon {
          width: 40px;
          height: 40px;
          background: #f3f4f6;
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #6b7280;
          font-size: 18px;
          transition: all 0.2s;
        }

        .card-content {
          flex: 1;

          .card-title {
            font-size: 14px;
            font-weight: 600;
            color: #374151;
            margin-bottom: 2px;
          }

          .card-desc {
            font-size: 12px;
            color: #9ca3af;
          }
        }

        .card-check {
          width: 20px;
          height: 20px;
          background: #6366f1;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-size: 14px;
        }
      }
    }

    .dev-mode-section {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      background: #f9fafb;
      border-radius: 8px;
      margin-top: 8px;

      .dev-hint {
        font-size: 12px;
        color: #9ca3af;
      }
    }
  }
}
</style>
