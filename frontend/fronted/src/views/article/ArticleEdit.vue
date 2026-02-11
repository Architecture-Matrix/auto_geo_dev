<template>
  <div class="article-edit-page">
    <div class="toolbar">
      <el-button @click="$router.back()">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
      <div class="toolbar-center">
        <el-tag v-if="articleId && articleId !== 'add'" type="info">
          {{ article.status === 1 ? '已发布' : '草稿' }}
        </el-tag>
      </div>
      <div class="toolbar-right">
        <el-button @click="saveDraft">保存草稿</el-button>
        <el-button type="primary" @click="publish">发布</el-button>
      </div>
    </div>

    <div class="editor-container">
      <el-input
        v-model="article.title"
        placeholder="请输入文章标题"
        size="large"
        class="title-input"
      />

      <div class="editor-wrapper">
        <WangEditor
          v-model="article.content"
          height="100%"
          @change="handleContentChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useArticleStore } from '@/stores/modules/article'
import WangEditor from '@/components/business/editor/WangEditor.vue'

const router = useRouter()
const route = useRoute()
const articleStore = useArticleStore()

const articleId = ref<string>('')
const article = ref({
  title: '',
  content: '',
  tags: '',
  category: '',
})

onMounted(async () => {
  const id = route.params.id as string
  articleId.value = id
  if (id && id !== 'add') {
    await articleStore.loadArticleDetail(Number(id))
    if (articleStore.currentArticle.id) {
      article.value = {
        title: articleStore.currentArticle.title || '',
        content: articleStore.currentArticle.content || '',
        tags: articleStore.currentArticle.tags || '',
        category: articleStore.currentArticle.category || '',
      }
    }
  }
})

const handleContentChange = (value: string) => {
  article.value.content = value
}

const saveDraft = async () => {
  if (!article.value.title) {
    ElMessage.warning('请输入标题')
    return
  }
  const isEdit = articleId.value && articleId.value !== 'add'
  const result = isEdit
    ? await articleStore.updateArticle(Number(articleId.value), { ...article.value, status: 0 })
    : await articleStore.createArticle({ ...article.value, status: 0 })

  if (result.success) {
    ElMessage.success(isEdit ? '更新成功' : '保存成功')
    if (!isEdit) {
      router.push('/articles')
    }
  }
}

const publish = async () => {
  if (!article.value.title || !article.value.content) {
    ElMessage.warning('请填写标题和内容')
    return
  }
  const isEdit = articleId.value && articleId.value !== 'add'
  const result = isEdit
    ? await articleStore.updateArticle(Number(articleId.value), { ...article.value, status: 1 })
    : await articleStore.createArticle({ ...article.value, status: 1 })

  if (result.success) {
    ElMessage.success(isEdit ? '发布成功' : '保存成功')
    router.push('/articles')
  }
}
</script>

<style scoped lang="scss">
.article-edit-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 24px;

  .toolbar-center {
    display: flex;
    align-items: center;
  }
}

.editor-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 0;

  .title-input {
    :deep(.el-input__wrapper) {
      background: transparent;
      border: none;
      border-bottom: 2px solid var(--border);
      border-radius: 0;
      padding: 12px 0;

      input {
        font-size: 24px;
        font-weight: 500;
      }
    }
  }

  .editor-wrapper {
    flex: 1;
    min-height: 0;
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid var(--border);
  }
}
</style>
