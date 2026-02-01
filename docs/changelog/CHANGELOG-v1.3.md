# AutoGeo v1.3 更新日志

**发布日期**: 2026-01-26
**版本**: v1.3
**主题**: 知乎发布修复 - 标题填充与图片上传

---

## 概述

修复了知乎文章发布器的两个核心问题：
1. **标题填充失败** - 原选择器单一，页面结构变化后失效
2. **图片完全缺失** - 原代码压根没有实现图片上传功能

---

## 问题分析

### 问题1：标题不填入

**根本原因**：
- 原代码仅使用2个选择器：`input[placeholder*='请输入标题']` 和 `input.Input`
- 知乎页面结构变化，这些选择器无法定位到标题输入框
- 没有验证机制，填充失败也返回成功

### 问题2：图片不填入

**根本原因**：
- 原代码完全没有图片处理逻辑
- 文章内容中的 `![alt](url)` Markdown图片语法被忽略
- 没有图片下载、上传到知乎编辑器的功能

---

## 核心改动

### 1. 标题填充增强 (`_fill_title` 方法)

**修改位置**: `backend/services/playwright/publishers/zhihu.py:60-101`

**多选择器策略**：
```python
selectors = [
    "input[placeholder*='请输入标题']",  # 主选择器
    "input[placeholder*='标题']",        # 备用1
    "input[class*='Title']",             # 备用2
    "input[class*='Input']",             # 备用3
    ".WriteIndexTitleInput",             # 备用4
    "input[type='text']",                # 兜底
]
```

**验证机制**：
```python
# 填充后验证是否成功
filled_value = await page.input_value(selector)
if filled_value == title:
    logger.info(f"✅ 知乎标题已填充: {title[:30]}...")
    return True
```

### 2. 图片上传功能 (全新实现)

#### 2.1 Markdown图片解析 (`_parse_markdown_content` 方法)

**修改位置**: `backend/services/playwright/publishers/zhihu.py:171-209`

**功能**：
- 解析 `![alt](url)` 格式的图片
- 按图片位置分割文本段落
- 返回 `(文本段落列表, 图片URL列表)`

**实现**：
```python
def _parse_markdown_content(self, content: str) -> Tuple[List[str], List[str]]:
    img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    images = re.findall(img_pattern, content)
    parts = re.split(img_pattern, content)
    # ... 处理逻辑
    return text_parts, image_urls
```

#### 2.2 图片下载 (`_download_image` 方法)

**修改位置**: `backend/services/playwright/publishers/zhihu.py:276-309`

**功能**：
- 使用项目现有的 `httpx` 下载图片（遵循DRY原则，不新增依赖）
- 识别图片类型（jpg/png/gif/webp）
- 保存到临时文件

**实现**：
```python
async def _download_image(self, url: str) -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url)
        if resp.status_code == 200:
            # 获取文件扩展名
            content_type = resp.headers.get('Content-Type', 'image/jpeg')
            ext = '.jpg' if 'jpeg' in content_type else ...
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
                f.write(resp.content)
                return f.name
```

#### 2.3 图片上传到知乎 (`_upload_image_to_zhihu` 方法)

**修改位置**: `backend/services/playwright/publishers/zhihu.py:211-274`

**功能**：
- 监听文件选择器（`page.expect_file_chooser()`）
- 点击知乎编辑器的图片上传按钮
- 选择下载的临时文件上传

**实现**：
```python
async def _upload_image_to_zhihu(self, page: Page, image_url: str) -> bool:
    # 1. 下载图片
    temp_file = await self._download_image(image_url)

    # 2. 监听文件选择器并点击上传按钮
    async with page.expect_file_chooser() as fc_info:
        upload_selectors = [
            "button[title='上传图片']",
            "button[aria-label='上传图片']",
            ".upload-image-button",
            "[class*='ImageUpload']",
        ]
        # 尝试点击上传按钮...

    # 3. 选择文件
    file_chooser = await fc_info.value
    await file_chooser.set_files(temp_file)
```

### 3. 正文输入优化 (`_fill_content_with_images` 方法)

**修改位置**: `backend/services/playwright/publishers/zhihu.py:103-169`

**改进**：
- 使用clipboard粘贴替代逐字输入（更快更稳定）
- 文本和图片按原始顺序混合上传
- 自动清理临时文件

---

## 文件修改清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/services/playwright/publishers/zhihu.py` | 重写 | 完全重写，新增图片上传功能 |
| `docs/overview/DEV_SUMMARY.md` | 修改 | 版本历史更新到 v1.3 |
| `docs/changelog/CHANGELOG-v1.3.md` | 新增 | 本次更新日志 |

---

## 技术总结

### 设计原则

1. **DRY（Don't Repeat Yourself）**
   - 使用项目现有的 `httpx` 下载图片，不引入 `aiohttp` 新依赖

2. **防御性编程**
   - 多选择器备份策略
   - 填充后验证机制
   - 异常处理和资源清理

3. **用户体验**
   - 详细的日志输出（✅成功 / ❌失败）
   - 临时文件自动清理

### 已知问题

1. **图片上传按钮选择器可能失效**
   - 知乎编辑器的上传按钮选择器需要实测验证
   - 如失效，使用浏览器开发者工具检查实际class名

2. **clipboard权限问题**
   - 部分环境可能需要用户授权clipboard访问
   - 备用方案是逐字输入（较慢）

---

## 下一步

- [ ] 实测知乎发布流程（含图片的文章）
- [ ] 根据实测结果调整选择器
- [ ] 为其他平台（搜狐、头条）添加类似的图片上传功能
- [ ] 统一图片上传逻辑到 `BasePublisher` 基类

---

## 测试建议

### 测试用例1：纯文本文章
```markdown
# 测试标题

这是正文内容，没有图片。
```

### 测试用例2：含图片文章
```markdown
# 测试标题

正文第一段

![图片描述](https://example.com/image.jpg)

正文第二段
```

### 验证点
- ✅ 标题正确填充
- ✅ 正文正确输入
- ✅ 图片正确上传并显示
- ✅ 临时文件被清理
