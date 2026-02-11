<template>
  <div class="project-manager">
    <!-- 头部 -->
    <div class="manager-header">
      <div class="header-left">
        <div class="header-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 3h18v18H3zM9 3v18M15 3v18M3 9h18M3 15h18"/>
          </svg>
        </div>
        <div>
          <h3 class="header-title">GEO 项目</h3>
          <span class="header-count">{{ projects.length }} 个项目</span>
        </div>
      </div>
      <el-button
        type="primary"
        size="small"
        :icon="PlusIcon"
        @click="showCreateDialog = true"
      >
        新建
      </el-button>
    </div>

    <!-- 项目列表 -->
    <div class="project-list">
      <div
        v-for="project in projects"
        :key="project.id"
        class="project-card"
        :class="{ active: modelValue === project.id, loading: project.loading }"
        @click="selectProject(project)"
      >
        <!-- 项目名称 -->
        <div class="card-header">
          <div class="project-badge">
            {{ getProjectInitial(project.name) }}
          </div>
          <div class="project-info">
            <h4 class="project-name">{{ project.name }}</h4>
            <span class="project-company">{{ project.company_name }}</span>
          </div>
          <el-dropdown trigger="click" @click.stop>
            <div class="more-btn">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="1"/>
                <circle cx="12" cy="5" r="1"/>
                <circle cx="12" cy="19" r="1"/>
              </svg>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click.stop="editProject(project)">
                  <el-icon><Edit /></el-icon>
                  编辑
                </el-dropdown-item>
                <el-dropdown-item divided @click.stop="deleteProject(project)">
                  <el-icon><Delete /></el-icon>
                  删除
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <!-- 关键词标签 -->
        <div class="card-keywords">
          <div class="keyword-tag-main">
            <svg viewBox="0 0 16 16" fill="currentColor" width="12">
              <path d="M8 2L2 8l6 6 6-6-6-6zm0 2.83L11.17 8 8 11.17 4.83 8 8 4.83z"/>
            </svg>
            <span>{{ project.domain_keyword || '未设置关键词' }}</span>
          </div>
        </div>

        <!-- 底部信息 -->
        <div class="card-footer">
          <div class="footer-stats">
            <span class="stat-item">
              <svg viewBox="0 0 16 16" fill="currentColor" width="12">
                <path d="M8 2a6 6 0 100 12A6 6 0 008 2zm0 10a4 4 0 110-8 4 4 0 010 8z"/>
              </svg>
              {{ getKeywordCount(project.id) }} 个关键词
            </span>
            <span v-if="project.industry" class="stat-industry">{{ project.industry }}</span>
          </div>
          <div v-if="modelValue === project.id" class="active-indicator">
            <span class="indicator-dot"></span>
            <span>当前</span>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="!loading && projects.length === 0" class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M9 17h6M9 13h6M9 9h6M5 21h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2z"/>
        </svg>
        <p>还没有项目</p>
        <el-button size="small" @click="showCreateDialog = true">创建第一个项目</el-button>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading && projects.length === 0" class="loading-state">
        <div v-for="i in 3" :key="i" class="skeleton-card">
          <div class="skeleton-header">
            <div class="skeleton-badge"></div>
            <div class="skeleton-text"></div>
          </div>
          <div class="skeleton-keyword"></div>
        </div>
      </div>
    </div>

    <!-- 创建/编辑项目对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingProject ? '编辑GEO项目' : '创建GEO项目'"
      width="480px"
      :close-on-click-modal="false"
      class="project-dialog"
    >
      <el-form :model="projectForm" label-position="top" @submit.prevent="saveProject">
        <el-form-item label="项目名称" required>
          <el-input
            v-model="projectForm.name"
            placeholder="如：绿阳环保无人机清洗"
            clearable
            size="large"
          >
            <template #prefix>
              <svg viewBox="0 0 16 16" fill="currentColor" width="16">
                <path d="M4 2h8a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V4a2 2 0 012-2z"/>
              </svg>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item label="公司名称" required>
          <el-input
            v-model="projectForm.company_name"
            placeholder="如：绿阳环保科技有限公司"
            clearable
            size="large"
          >
            <template #prefix>
              <svg viewBox="0 0 16 16" fill="currentColor" width="16">
                <path d="M8 1a4 4 0 00-4 4v2H2v2h2v6a2 2 0 002 2h4a2 2 0 002-2V9h2V7h-2V5a4 4 0 00-4-4zm0 2a2 2 0 012 2v2H6V5a2 2 0 012-2z"/>
              </svg>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item label="领域关键词" required>
          <el-input
            v-model="projectForm.domain_keyword"
            placeholder="如：无人机清洗"
            clearable
            size="large"
          >
            <template #prefix>
              <svg viewBox="0 0 16 16" fill="currentColor" width="16">
                <path d="M6.5 2a.5.5 0 01.5.5v1a.5.5 0 01-.5.5h-1a.5.5 0 01-.5-.5v-1a.5.5 0 01.5-.5h1zm3 0a.5.5 0 01.5.5v1a.5.5 0 01-.5.5h-1a.5.5 0 01-.5-.5v-1a.5.5 0 01.5-.5h1zM3 5.5A.5.5 0 013.5 5h9a.5.5 0 010 1h-9a.5.5 0 01-.5-.5zM6.5 7a.5.5 0 01.5.5v1a.5.5 0 01-.5.5h-1a.5.5 0 01-.5-.5v-1a.5.5 0 01.5-.5h1zm3 0a.5.5 0 01.5.5v1a.5.5 0 01-.5.5h-1a.5.5 0 01-.5-.5v-1a.5.5 0 01.5-.5h1z"/>
              </svg>
            </template>
          </el-input>
          <div class="form-tip">此关键词将用于AI蒸馏生成提问句</div>
        </el-form-item>

        <el-form-item label="所属行业">
          <el-select
            v-model="projectForm.industry"
            placeholder="选择行业"
            allow-create
            filterable
            style="width: 100%"
            size="large"
          >
            <el-option
              v-for="ind in industries"
              :key="ind"
              :label="ind"
              :value="ind"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="项目描述">
          <el-input
            v-model="projectForm.description"
            type="textarea"
            :rows="2"
            placeholder="简要描述项目背景和目标（可选）"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveProject">
          {{ editingProject ? '保存修改' : '创建项目' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Edit, Delete, Plus as PlusIcon } from '@element-plus/icons-vue'
import { geoKeywordApi } from '@/services/api'

// 行业列表
const industries = [
  'SaaS软件',
  '环保工程',
  '工业清洗',
  '无人机服务',
  '电商',
  '教育培训',
  '金融服务',
  '医疗健康',
  '制造业',
  '房地产',
  '餐饮美食',
  '旅游出行',
  '物流运输',
  '新能源',
  '化工行业',
  '建筑工程',
  '其他',
]

// ==================== 类型定义 ====================
interface Project {
  id: number
  name: string
  company_name: string
  domain_keyword?: string
  description?: string
  industry?: string
  status: number
  loading?: boolean
  created_at: string
}

// ==================== Props ====================
const modelValue = defineModel<number>()

// ==================== 状态 ====================
const projects = ref<Project[]>([])
const loading = ref(false)
const saving = ref(false)
const showCreateDialog = ref(false)
const editingProject = ref<Project | null>(null)

const projectForm = ref({
  name: '',
  company_name: '',
  domain_keyword: '',
  industry: '',
  description: '',
})

// ==================== 方法 ====================

// 加载项目列表
const loadProjects = async () => {
  loading.value = true
  try {
    const result = await geoKeywordApi.getProjects()
    projects.value = (result || []).map((p: Project) => ({ ...p, loading: false }))

    // 默认选中第一个项目
    if (projects.value.length > 0 && !modelValue.value) {
      modelValue.value = projects.value[0].id
    }
  } catch (error) {
    console.error('加载项目失败:', error)
  } finally {
    loading.value = false
  }
}

// 选择项目
const selectProject = (project: Project) => {
  modelValue.value = project.id
}

// 获取项目首字母
const getProjectInitial = (name: string) => {
  return name.charAt(0).toUpperCase()
}

// 获取项目关键词数量（从父组件传递的数据中获取）
const getKeywordCount = (projectId: number) => {
  // 这里需要从父组件或store中获取
  return 0
}

// 编辑项目
const editProject = (project: Project) => {
  editingProject.value = project
  projectForm.value = {
    name: project.name,
    company_name: project.company_name,
    domain_keyword: project.domain_keyword || '',
    industry: project.industry || '',
    description: project.description || '',
  }
  showCreateDialog.value = true
}

// 删除项目
const deleteProject = async (project: Project) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除项目"${project.name}"吗？删除后关联的关键词和文章也将被删除！`,
      '确认删除',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
    )

    await geoKeywordApi.deleteProject(project.id)
    projects.value = projects.value.filter(p => p.id !== project.id)

    // 如果删除的是当前选中的项目，选中第一个
    if (modelValue.value === project.id && projects.value.length > 0) {
      modelValue.value = projects.value[0].id
    } else if (projects.value.length === 0) {
      modelValue.value = null
    }

    ElMessage.success('项目已删除')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除项目失败:', error)
      ElMessage.error('删除项目失败')
    }
  }
}

// 保存项目
const saveProject = async () => {
  // 验证表单
  if (!projectForm.value.name?.trim()) {
    ElMessage.warning('请输入项目名称')
    return
  }
  if (!projectForm.value.company_name?.trim()) {
    ElMessage.warning('请输入公司名称')
    return
  }
  if (!projectForm.value.domain_keyword?.trim()) {
    ElMessage.warning('请输入领域关键词')
    return
  }

  saving.value = true
  try {
    if (editingProject.value) {
      // 更新项目
      await geoKeywordApi.updateProject(editingProject.value.id, {
        name: projectForm.value.name,
        company_name: projectForm.value.company_name,
        industry: projectForm.value.industry,
        description: projectForm.value.description,
      })
      const index = projects.value.findIndex(p => p.id === editingProject.value!.id)
      if (index !== -1) {
        projects.value[index] = {
          ...projects.value[index],
          name: projectForm.value.name,
          company_name: projectForm.value.company_name,
          industry: projectForm.value.industry,
          description: projectForm.value.description,
        }
      }
      ElMessage.success('项目已更新')
    } else {
      // 创建项目
      const result = await geoKeywordApi.createProject({
        name: projectForm.value.name,
        company_name: projectForm.value.company_name,
        industry: projectForm.value.industry,
        description: projectForm.value.description,
      })
      // 添加 domain_keyword 到结果
      const newProject = { ...result, domain_keyword: projectForm.value.domain_keyword }
      projects.value.unshift(newProject)
      modelValue.value = result.id
      ElMessage.success('项目创建成功')
    }

    showCreateDialog.value = false
    resetForm()
  } catch (error) {
    console.error('保存项目失败:', error)
    ElMessage.error('保存项目失败')
  } finally {
    saving.value = false
  }
}

// 重置表单
const resetForm = () => {
  editingProject.value = null
  projectForm.value = {
    name: '',
    company_name: '',
    domain_keyword: '',
    industry: '',
    description: '',
  }
}

// 刷新项目列表
const refresh = () => {
  loadProjects()
}

// 暴露方法给父组件
defineExpose({ refresh, projects })

// ==================== 生命周期 ====================
onMounted(() => {
  loadProjects()
})
</script>

<style scoped lang="scss">
.project-manager {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f8f9fc;
}

// 头部
.manager-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: white;
  border-bottom: 1px solid #e8ecf1;

  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;

    .header-icon {
      width: 40px;
      height: 40px;
      border-radius: 10px;
      background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;

      svg {
        width: 20px;
        height: 20px;
      }
    }

    .header-title {
      margin: 0;
      font-size: 15px;
      font-weight: 600;
      color: #1a1f36;
    }

    .header-count {
      font-size: 12px;
      color: #6b7280;
    }
  }
}

// 项目列表
.project-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

// 项目卡片
.project-card {
  background: white;
  border-radius: 12px;
  padding: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 2px solid transparent;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);

  &:hover {
    border-color: #4a90e2;
    box-shadow: 0 4px 12px rgba(74, 144, 226, 0.15);
    transform: translateY(-1px);
  }

  &.active {
    border-color: #4a90e2;
    background: linear-gradient(135deg, rgba(74, 144, 226, 0.05) 0%, rgba(74, 144, 226, 0.02) 100%);

    .project-badge {
      background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%);
    }
  }

  .card-header {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 10px;

    .project-badge {
      width: 36px;
      height: 36px;
      border-radius: 8px;
      background: linear-gradient(135deg, #e8ecf1 0%, #d4d9e1 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 600;
      font-size: 14px;
      color: #4a90e2;
      flex-shrink: 0;
      transition: all 0.2s ease;
    }

    .project-info {
      flex: 1;
      min-width: 0;

      .project-name {
        margin: 0 0 4px 0;
        font-size: 14px;
        font-weight: 500;
        color: #1a1f36;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .project-company {
        font-size: 12px;
        color: #6b7280;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }

    .more-btn {
      width: 24px;
      height: 24px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #9ca3af;
      cursor: pointer;
      transition: all 0.2s;

      &:hover {
        background: #f3f4f6;
        color: #4a90e2;
      }

      svg {
        width: 14px;
        height: 14px;
      }
    }
  }

  .card-keywords {
    margin-bottom: 10px;

    .keyword-tag-main {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 10px;
      background: linear-gradient(135deg, rgba(74, 144, 226, 0.1) 0%, rgba(74, 144, 226, 0.05) 100%);
      border-radius: 6px;
      font-size: 12px;
      color: #4a90e2;
      font-weight: 500;
    }
  }

  .card-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;

    .footer-stats {
      display: flex;
      align-items: center;
      gap: 10px;

      .stat-item {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 11px;
        color: #9ca3af;

        svg {
          flex-shrink: 0;
        }
      }

      .stat-industry {
        padding: 2px 8px;
        background: #f3f4f6;
        border-radius: 4px;
        font-size: 11px;
        color: #6b7280;
      }
    }

    .active-indicator {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 11px;
      color: #4a90e2;

      .indicator-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #4a90e2;
        animation: pulse 2s infinite;
      }
    }
  }
}

// 空状态
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;

  svg {
    width: 48px;
    height: 48px;
    color: #d1d5db;
    margin-bottom: 12px;
  }

  p {
    margin: 0 0 16px 0;
    font-size: 14px;
    color: #9ca3af;
  }
}

// 加载骨架屏
.loading-state {
  display: flex;
  flex-direction: column;
  gap: 10px;

  .skeleton-card {
    background: white;
    border-radius: 12px;
    padding: 14px;

    .skeleton-header {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 10px;

      .skeleton-badge {
        width: 36px;
        height: 36px;
        border-radius: 8px;
        background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
        background-size: 200% 100%;
        animation: shimmer 1.5s infinite;
      }

      .skeleton-text {
        flex: 1;
        height: 14px;
        border-radius: 4px;
        background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
        background-size: 200% 100%;
        animation: shimmer 1.5s infinite;
      }
    }

    .skeleton-keyword {
      width: 60%;
      height: 24px;
      border-radius: 6px;
      background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
      background-size: 200% 100%;
      animation: shimmer 1.5s infinite;
    }
  }
}

// 表单提示
.form-tip {
  margin-top: 6px;
  font-size: 12px;
  color: #9ca3af;
}

// 滚动条样式
.project-list::-webkit-scrollbar {
  width: 4px;
}

.project-list::-webkit-scrollbar-track {
  background: transparent;
}

.project-list::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 2px;

  &:hover {
    background: #9ca3af;
  }
}

// 动画
@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

// 对话框样式
:deep(.project-dialog) {
  .el-dialog__header {
    padding: 20px 20px 10px;

    .el-dialog__title {
      font-size: 16px;
      font-weight: 600;
      color: #1a1f36;
    }
  }

  .el-dialog__body {
    padding: 20px;
  }

  .el-dialog__footer {
    padding: 16px 20px 20px;
    border-top: 1px solid #e8ecf1;
  }

  .el-form-item__label {
    font-weight: 500;
    color: #374151;
  }

  .el-input__wrapper,
  .el-textarea__inner {
    border-radius: 8px;
    transition: all 0.2s;

    &:hover {
      box-shadow: 0 0 0 1px #4a90e2 inset;
    }

    &.is-focus {
      box-shadow: 0 0 0 1px #4a90e2 inset;
    }
  }
}
</style>
