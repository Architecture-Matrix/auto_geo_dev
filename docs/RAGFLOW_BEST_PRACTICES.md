# RAGFlow 高效利用指南

> ，这份指南是开发者我熬夜肝出来的，看不懂就来问我！

---

## 一、核心原则：选对分块方法（最重要！）

### 1.1 分块方法选择决策树

```
你的文档是什么类型？
│
├─ PDF/Word 普通文档 ────────→ naive（通用，90%场景）
├─ FAQ/问答对 ───────────────→ qa
├─ 论文/学术文献 ─────────────→ paper
├─ 电子书 ───────────────────→ book
├─ 法律条文 ─────────────────→ laws
├─ PPT 演示文稿 ─────────────→ presentation
├─ 表格密集型 ───────────────→ table
├─ 图片/扫描件 ──────────────→ picture
├─ 邮件 ─────────────────────→ email
└─ 需要精确控制 ─────────────→ manual
```

### 1.2 各方法详解

| 方法 | 适用场景 | chunk_token_num 建议 | 特点 |
|------|----------|---------------------|------|
| **naive** | 通用文档（推荐默认） | 512-1024 | 按分隔符切分，简单高效 |
| **qa** | FAQ、问答对 | 不适用 | 自动识别 Q&A 结构 |
| **paper** | 学术论文 | 1024-2048 | 保留章节结构 |
| **book** | 长篇书籍 | 2048-4096 | 按章节分块 |
| **laws** | 法律条文 | 256-512 | 条款级别切分 |
| **presentation** | PPT | 256-512 | 按页面分块 |
| **table** | 表格密集 | 不适用 | 保留表格结构 |
| **manual** | 手动控制 | 自定义 | 精确控制每个 chunk |

### 1.3 GEO_AUTO 场景推荐

```python
# 地理科普文章知识库配置
{
  "chunk_method": "naive",          # 通用文章用 naive
  "parser_config": {
    "chunk_token_num": 8192,        # 地理文章较长，用大 chunk
    "delimiter": "\\n\\n",          # 按段落分
    "layout_recognize": True,       # 保留格式
    "html4excel": False
  }
}

# 去重检测知识库配置
{
  "chunk_method": "naive",
  "parser_config": {
    "chunk_token_num": 512,         # 小 chunk 提高去重精度
    "delimiter": "\\n"
  }
}
```

---

## 二、向量模型选择（决定检索上限）

### 2.1 模型推荐

| 模型 | 适用语言 | 特点 | 推荐指数 |
|------|----------|------|----------|
| **BAAI/bge-large-zh-v1.5** | 中文 | 中文效果最好 | ⭐⭐⭐⭐⭐ |
| **BAAI/bge-m3** | 多语言 | 中英混合，支持长文本 | ⭐⭐⭐⭐ |
| **Qwen/Qwen3-Embedding-0.6B** | 中英 | 轻量，推理快 | ⭐⭐⭐⭐ |
| **BAAI/bge-small-en-v1.5** | 英文 | 英文专用 | ⭐⭐⭐ |

### 2.2 切换模型注意事项

⚠️ **，这个很重要！**

```bash
# 切换向量模型前必须：
1. 知识库 chunk_count = 0（空库）
2. 或者重建整个知识库

# 已有内容的知识库不能直接切换模型！
```

---

## 三、检索参数调优（效果关键）

### 3.1 核心参数速查

```python
POST /api/v1/retrieval
{
  "question": "你的问题",
  "dataset_ids": ["kb_id"],

  # ===== 最重要的三个参数 =====
  "similarity_threshold": 0.2,      # 相似度阈值
  "vector_similarity_weight": 0.3,  # 向量权重
  "top_k": 1024,                    # 候选数量

  # ===== 增强功能 =====
  "keyword": true,                  # 开启关键词检索
  "highlight": true,                # 高亮匹配词
  "rerank_id": "bge-reranker-v2-m3" # 重排序模型
}
```

### 3.2 参数调优指南

#### similarity_threshold（相似度阈值）

| 场景 | 推荐值 | 说明 |
|------|--------|------|
| **宽泛搜索** | 0.1 - 0.2 | 召回率高，但可能有噪音 |
| **平衡搜索** | 0.2 - 0.4 | 推荐，平衡召回和精度 |
| **精确搜索** | 0.5 - 0.7 | 只要高度相关的 |
| **去重检测** | 0.85 - 0.95 | 高阈值，严格判断 |

#### vector_similarity_weight（向量权重）

```
向量相似度权重 + 关键词权重 = 1

vector_similarity_weight = 0.3  →  向量30%，关键词70%
vector_similarity_weight = 0.7  →  向量70%，关键词30%
```

| 场景 | 推荐值 | 说明 |
|------|--------|------|
| **语义理解为主** | 0.5 - 0.7 | 向量为主，关键词为辅 |
| **精确匹配为主** | 0.2 - 0.3 | 关键词为主，向量为辅 |
| **专业术语多** | 0.2 - 0.4 | 术语匹配更重要 |

#### top_k（候选数量）

| 场景 | 推荐值 | 说明 |
|------|--------|------|
| **小知识库** | 512 - 1024 | 默认值 |
| **大知识库** | 2048 - 4096 | 增加候选 |
| **追求性能** | 256 - 512 | 减少计算 |

### 3.3 调优口诀

```
召回不够？ → similarity_threshold 降一点
结果不准？ → similarity_threshold 升一点
关键词重要？ → vector_similarity_weight 降一点
语义更重要？ → vector_similarity_weight 升一点
大库搜不到？ → top_k 升一点
响应太慢？   → top_k 降一点
```

---

## 四、高级功能：让检索更准

### 4.1 Rerank 重排序（强烈推荐！）

```python
# 开启 Rerank 可以显著提升 Top 结果质量
{
  "top_k": 1024,              # 先召回 1024 个
  "rerank_id": "bge-reranker-v2-m3"  # 重排序选出最好的
}
```

**效果提升：** Top-1 准确率可提升 20-40%

### 4.2 Auto-keyword / Auto-question

```
位置：知识库配置页面，Page rank 下方滑块

作用：
- Auto-keyword：自动为 chunk 生成关键词/同义词
- Auto-question：自动为 chunk 生成相关问题

适用场景：
- FAQ 检索 → 开启 Auto-question
- 术语多   → 开启 Auto-keyword
- 追求性能 → 关闭（需要额外 LLM 调用）
```

### 4.3 元数据过滤

```python
# 结合元数据精准过滤
{
  "question": "如何安装Docker",
  "dataset_ids": ["kb_id"],
  "metadata_condition": {
    "conditions": [
      {"name": "category", "comparison_operator": "=", "value": "技术文档"},
      {"name": "language", "comparison_operator": "=", "value": "zh"}
    ]
  }
}
```

---

## 五、GEO_AUTO 系统最佳配置

### 5.1 推荐架构

```
┌────────────────────────────────────────────────────────────┐
│                    GEO_AUTO 系统                           │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌─────────────────┐    ┌─────────────────┐              │
│  │  文章生成知识库  │    │  去重检测知识库  │              │
│  ├─────────────────┤    ├─────────────────┤              │
│  │ chunk_method:   │    │ chunk_method:   │              │
│  │   naive         │    │   naive         │              │
│  │ chunk_token_num:│    │ chunk_token_num:│              │
│  │   8192          │    │   512           │              │
│  │ 用途:           │    │ 用途:           │              │
│  │  参考内容生成   │    │  相似度检测     │              │
│  └─────────────────┘    └─────────────────┘              │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 5.2 完整配置示例

```python
# ========== 文章生成知识库 ==========
GENERATION_KB_CONFIG = {
    "name": "geo_article_generation",
    "chunk_method": "naive",
    "embedding_model": "BAAI/bge-large-zh-v1.5",
    "parser_config": {
        "chunk_token_num": 8192,        # 大 chunk 保留完整内容
        "delimiter": "\\n\\n",          # 按段落分
        "layout_recognize": True,
    },
    "similarity_threshold": 0.2,
    "vector_similarity_weight": 0.5,
    "top_k": 1024,
}

# ========== 去重检测知识库 ==========
DEDUPE_KB_CONFIG = {
    "name": "geo_article_dedupe",
    "chunk_method": "naive",
    "embedding_model": "BAAI/bge-large-zh-v1.5",
    "parser_config": {
        "chunk_token_num": 512,         # 小 chunk 提高检测精度
        "delimiter": "\\n",
    },
    "similarity_threshold": 0.85,       # 高阈值严格去重
    "vector_similarity_weight": 0.3,    # 关键词权重高
    "top_k": 1024,
}

# ========== 检索配置 ==========
RETRIEVAL_CONFIG = {
    "generation": {
        "similarity_threshold": 0.2,
        "vector_similarity_weight": 0.5,
        "keyword": True,
        "rerank_id": "bge-reranker-v2-m3",  # 生成时用 rerank
    },
    "dedupe": {
        "similarity_threshold": 0.85,      # 去重用高阈值
        "vector_similarity_weight": 0.3,
        "keyword": True,
        "highlight": True,
    }
}
```

---

## 六、性能优化建议

### 6.1 知识库组织

| 策略 | 说明 | 效果 |
|------|------|------|
| **分类建库** | 按主题/类型分多个知识库 | 减少检索范围，提高速度 |
| **定期清理** | 删除过期/低质文档 | 提高检索质量 |
| **文档预处理** | 上传前清理格式 | 减少解析噪音 |

### 6.2 检索优化

```python
# ❌ 低效做法：检索所有知识库
{
  "dataset_ids": ["kb1", "kb2", "kb3", ...]  # 检索所有库
}

# ✅ 高效做法：只检索相关库
{
  "dataset_ids": ["geo_science_kb"],  # 精确指定
  "document_ids": ["doc1", "doc2"]     # 进一步缩小范围
}
```

### 6.3 缓存策略

```python
# 对常见问题做缓存
CACHE_ENABLED_QUESTIONS = [
    "什么是喀斯特地貌",
    "板块构造理论",
    # ...
]

def smart_retrieve(question):
    if question in CACHE:
        return CACHE[question]
    return ragflow_retrieve(question)
```

---

## 七、常见问题排查

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| **搜不到结果** | similarity_threshold 太高 | 降到 0.1-0.2 试试 |
| **结果不相关** | similarity_threshold 太低 | 升到 0.4-0.6 |
| **关键词匹配不准** | vector_similarity_weight 太高 | 降到 0.2-0.3 |
| **语义理解差** | vector_similarity_weight 太低 | 升到 0.6-0.8 |
| **响应太慢** | top_k 太大或 rerank 开启 | 减少 top_k 或关闭 rerank |
| **中文效果差** | 用了英文模型 | 换 bge-large-zh-v1.5 |

---

## 八、快速调参脚本

```python
# backend/services/ragflow_tuner.py（开发者送的）

class RAGFlowTuner:
    """RAGFlow 参数调优工具"""

    # 不同场景的推荐配置
    PRESETS = {
        "generation": {     # 文章生成
            "similarity_threshold": 0.2,
            "vector_similarity_weight": 0.5,
            "top_k": 1024,
            "keyword": True,
            "rerank_id": "bge-reranker-v2-m3"
        },
        "dedupe": {         # 去重检测
            "similarity_threshold": 0.85,
            "vector_similarity_weight": 0.3,
            "top_k": 1024,
            "keyword": True,
            "highlight": True
        },
        "faq": {            # FAQ 检索
            "similarity_threshold": 0.3,
            "vector_similarity_weight": 0.4,
            "top_k": 512,
            "keyword": True
        },
        "precise": {        # 精确搜索
            "similarity_threshold": 0.5,
            "vector_similarity_weight": 0.3,
            "top_k": 256,
            "keyword": True
        }
    }

    @classmethod
    def get_config(cls, scenario: str) -> dict:
        """获取场景配置"""
        return cls.PRESETS.get(scenario, cls.PRESETS["generation"])

# 使用示例
config = RAGFlowTuner.get_config("dedupe")
result = ragflow_client.retrieve(question, dataset_ids, **config)
```

---

## 九、开发者的终极建议

### 90% 的场景这样配置就够了：

```python
{
  "chunk_method": "naive",
  "chunk_token_num": 512,
  "embedding_model": "BAAI/bge-large-zh-v1.5",
  "similarity_threshold": 0.2,
  "vector_similarity_weight": 0.3,
  "top_k": 1024,
  "keyword": True
}
```

### 进阶优化三板斧：

1. **开 Rerank** → Top 结果质量提升明显
2. **调阈值** → 根据实际反馈微调 similarity_threshold
3. **分库管理** → 按主题分类，减少干扰

---

**文档版本**: v1.0
**最后更新**: 2025-01-13
**整理人**: 开发者
**备注**: ，这些都是实战经验，别tm瞎改！
