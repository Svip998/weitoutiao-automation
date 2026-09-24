# 微头条自动化发布工具 (weitoutiao-automation)

> 头条号微头条快速发布技能，通过 CDP 操控已登录的 Chrome 浏览器，完成"搜图→下载→验证→输入内容→上传配图→发布→验证"全流程自动化。

## 版本

**v1.1.0** (2026-09-24)

## 功能特性

- **自动搜图**：Pexels 免版权图片搜索 + 下载 + JPEG 校验
- **去AI味写作**：禁用模板词、长短句交替、具体数字、个人体感、结尾提问
- **CDP 全流程**：导航→清空→输入→上传配图→发布→验证，无需人工干预
- **间隔检验**（v1.1新增）：每次发布前检查距上一条是否满1小时，防止高频限流
- **发布后验证**：内容计数、乱码检查、配图检查三重验证
- **定时任务**：支持10个cron定时任务，每天自动发布10条微头条

## 环境要求

| 依赖 | 说明 |
|------|------|
| Chrome 浏览器 | 需开启远程调试端口 9222 |
| CDP Proxy | localhost:3456，提供 /navigate /eval /clickAt /setFiles /screenshot 接口 |
| Node.js | 用于生成 Unicode 转义 JS（gen_from_txt.js） |
| PowerShell | 用于图片下载（Invoke-WebRequest） |
| 头条号账号 | Chrome 中已登录 mp.toutiao.com 创作者平台 |

## 快速开始

### 1. 启动 Chrome（带调试端口）

```bash
# Windows
start_chrome_9222.bat
# 或手动启动
chrome.exe --remote-debugging-port=9222 --user-data-dir=C:\chrome-hermes-profile
```

### 2. 确认 CDP Proxy 运行

```bash
curl http://localhost:3456/health
# 应返回 {"status":"ok","connected":true}
```

### 3. 发布一条微头条

完整流程：
```
检查CDP → 搜索热点 → 写内容 → 搜图下载 → 导航发布页 →
清空编辑器 → 输入内容 → 开图片弹窗 → 本地上传 →
setFiles → 触发change → 选图确认 → 验证图片 → 发布 → 验证
```

## 工作流程

### 第零步：间隔检验（v1.1新增·强制）

每次执行前导航到管理页，检查最近一条微头条发布时间。距现在不足1小时则跳过不发布。

> 2026-09-24 因7-13分钟间隔连发20条导致平台限流、展现归零，此步骤为强制修复措施。

### 第一步：准备内容

- 去AI味写作规则：开头直切、长短句交替、具体数字、竞品对比、结尾提问
- 话题标签 ≥ 5 个，含活动话题 + 热门话题
- 内容长度 200-400 字
- 中文内容通过 gen_from_txt.js 转为 Unicode 转义

### 第二步：搜索并下载配图

- Pexels 搜图（web_search 搜 "pexels {关键词} photo" 提取 photo ID）
- PowerShell Invoke-WebRequest 下载到本地
- JPEG 头尾校验（0xFF 0xD8 / 0xFF 0xD9）

### 第三步：发布微头条

- 导航到 `https://mp.toutiao.com/profile_v4/weitoutiao/publish`
- 清空 ProseMirror 编辑器（clear_edit.js）
- 输入 Unicode 转义内容（wt_content_clean.js）
- 上传配图（deep_click.js → click_local.js → setFiles → trigger_change.js → select_confirm.js）
- 验证图片（verify_img.js）
- 点击发布（deep_publish.js）

### 第四步：发布后验证

- 跳转到管理页（verify_pub.js）
- 检查内容计数增加、无错误、无乱码

## 文件结构

```
weitoutiao-publisher/
├── SKILL.md              # 技能主文件（完整流程文档）
├── README.md             # 本文件
├── evolutions.json       # 技能演进记录
├── scripts/
│   └── gen_weitoutiao_js.py  # 中文→Unicode转义脚本
└── references/
    └── cdp-examples.md   # CDP 操作示例
```

## 辅助脚本（运行时生成）

| 文件 | 用途 |
|------|------|
| `gen_from_txt.js` | 读取 wt_content.txt → Unicode 转义 → 生成 wt_content_clean.js |
| `wt_content.txt` | 纯文本内容文件 |
| `wt_content_clean.js` | Unicode 转义后的 JS 表达式 |
| `wt_image.jpg` | 配图文件 |
| `clear_edit.js` | 清空 ProseMirror 编辑器 |
| `deep_click.js` | JS 鼠标事件打开图片弹窗 |
| `click_local.js` | 点击"本地上传"按钮 |
| `trigger_change.js` | 触发 file input change 事件 |
| `select_confirm.js` | 合并选图+确认为一个 JS 执行 |
| `deep_publish.js` | JS 鼠标事件点击发布按钮 |
| `verify_img.js` | 验证 upload-box 含 background-image |
| `verify_pub.js` | 验证发布成功（管理页+无错误+总内容数） |

## 定时任务配置

10个 cron 定时任务，每天自动发布10条微头条：

| 时间 | cron 表达式 | 时区 |
|------|------------|------|
| 11:20 | `20 11 * * *` | Asia/Shanghai |
| 12:30 | `30 12 * * *` | Asia/Shanghai |
| 14:00 | `0 14 * * *` | Asia/Shanghai |
| 15:30 | `30 15 * * *` | Asia/Shanghai |
| 17:00 | `0 17 * * *` | Asia/Shanghai |
| 19:00 | `0 19 * * *` | Asia/Shanghai |
| 20:00 | `0 20 * * *` | Asia/Shanghai |
| 21:00 | `0 21 * * *` | Asia/Shanghai |
| 22:00 | `0 22 * * *` | Asia/Shanghai |
| 23:00 | `0 23 * * *` | Asia/Shanghai |

每个任务均含 Step 0 间隔检验，确保每条间隔 ≥ 1小时。

## CDP API 说明

| 接口 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/targets` | GET | 获取标签页列表 |
| `/navigate?target=ID` | POST | 导航到 URL（body=纯文本URL） |
| `/eval?target=ID` | POST | 执行 JS（body=JS表达式） |
| `/clickAt?target=ID` | POST | 点击元素（body=CSS选择器） |
| `/setFiles?target=ID` | POST | 设置文件（body=JSON） |
| `/screenshot?target=ID` | GET | 截图 |

> targetId 通过 `?target=xxx` 查询参数传递，不是 JSON body。

## 去AI味写作规则

**禁用词**：此外、至关重要、综上所述、总而言之、由此可见、随着...的发展、不仅仅是...更是、首先...其次...最后、众所周知、毋庸置疑

**必须做到**：
- 开头直切主题，不废话
- 长短句交替，禁止全篇句子长度均匀
- 有具体数字（不说"多花不少钱"，说"多花12万"）
- 有个人体感或情绪温度
- 结尾抛问题不升华
- 话题标签 ≥ 5 个

**高点击率公式**：反常识钩子 + 具体参数(3-5个数字) + 竞品对比 + 结尾提问

## 更新日志

### v1.1.0 (2026-09-24)
- 新增第零步：间隔检验（强制），距上一条不足1小时则跳过
- 背景：2026-09-24 因高频连发（7-13分钟间隔）导致平台限流、展现归零
- 更新注意事项第11条

### v1.0.0 (2026-09-23)
- 初始版本
- 含 Pexels 搜图、JPEG 校验、去AI味写作、CDP 全流程选择器、发布后验证

## 账号信息

| 项目 | 值 |
|------|-----|
| 头条号 | 花生选车 |
| 创作天数 | 2871+ |
| 信用分 | 100 |
| 累计收益 | 680.72 元 |
| 每日上限 | 10 条微头条 |

## License

MIT