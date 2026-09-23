---
name: weitoutiao-publisher
description: |
  头条号微头条快速发布技能。通过 CDP 操控已登录的 Chrome，完成"搜图→下载→验证→输入内容→上传配图→发布→验证"全流程，专门用于单独发布一条带配图的微头条。
  触发场景：用户要求发微头条、发布微头条、发一条微头条、快速发微头条、微头条发布、发个头条短文、发个微头条等。
  依赖：需先加载 web-access skill 并完成 CDP 连接（localhost:3456）。
  与 toutiao-operator 的区别：toutiao-operator 是文章+微头条全流程技能；本技能专注于微头条单渠道快速发布，流程更短、速度更快，适合"每2小时发1条"的高频场景。
  版本：v1.0（2026-09-23）— 基于实际发布验证，含 Pexels 搜图、JPEG 校验、去AI味写作、CDP 全流程选择器、发布后验证。
version: 1.0.0
---
# 微头条快速发布技能 (weitoutiao-publisher)

## 前置条件

1. **web-access skill 已加载**：CDP Proxy 已启动（localhost:3456）并连接用户 Chrome
2. **用户已登录头条号**：Chrome 中已登录 mp.toutiao.com 创作者平台
3. **CDP Proxy 运行中**：`GET http://localhost:3456/targets` 返回非空

## 核心能力

| 能力 | 说明 |
|------|------|
| Pexels 搜图 | 打开新标签页搜索 Pexels，提取图片 URL |
| 图片下载与验证 | 下载图片到本地，JPEG 头尾校验（0xFF 0xD8 / 0xFF 0xD9） |
| 内容输入 | Unicode 转义 + ProseMirror execCommand 输入 |
| 配图上传 | 点击图片按钮→本地上传→setFiles→选图→确定 |
| 一键发布 | 点击发布按钮，验证跳转到管理页 |
| 发布后验证 | 检查内容计数增加、无乱码、图片已附加 |

## 平台关键信息

| 项目 | 值 |
|------|-----|
| 微头条发布页 URL | `https://mp.toutiao.com/profile_v4/weitoutiao/publish` |
| 内容管理页 URL | `https://mp.toutiao.com/profile_v4/weitoutiao` |
| 每日发布上限 | 10 条/天（超限后仅推荐给粉丝） |
| 内容长度 | 200-400 字（含话题标签） |
| 图片限制 | 仅 1 张，附加在末尾 upload-box（非编辑器内） |
| 无标题 | 微头条没有标题字段 |
| 无封面 | 微头条没有封面概念，图片即附件 |
| 无预览确认 | 点击"发布"直接发布，无确认弹窗 |

## 工作流程

### 第一步：准备内容

#### 1.1 内容写作规则（去AI味·强制）

**禁用词汇**：此外、至关重要、综上所述、总而言之、由此可见、随着...的发展、不仅仅是...更是、首先...其次...最后、众所周知、毋庸置疑

**必须做到**：
- 开头直切主题，不废话（禁止"随着汽车工业的发展"式开头）
- 长短句交替，禁止全篇句子长度均匀
- 有具体数字（不说"多花不少钱"，说"多花12万"）
- 有个人体感或情绪温度（"说白了""你猜怎么着"）
- 结尾抛问题不升华（禁止"让我们共同期待"式结尾）
- 话题标签 ≥ 5 个，含 1 个活动话题 + 热门话题

**高点击率内容公式**（基于账号数据验证）：
```
反常识钩子（1-2句）+ 具体参数（3-5个数字）+ 竞品对比（1组）+ 结尾提问
```

**高点击率话题类型**（按展现量排序）：
1. 新车上市 + 价格冲击（展现 800-1100）
2. 新车对比 + 品牌争论（展现 470-820）
3. 避坑科普（展现 58-200，适合长文不适合微头条）

#### 1.2 生成 Unicode 转义 JS

中文内容必须转为 `\uXXXX` Unicode 转义，禁止直接发送中文字符串到 CDP。

使用辅助脚本 `scripts/gen_weitoutiao_js.py`：
```bash
python gen_weitoutiao_js.py --content "微头条正文内容" --output "C:\Users\28470\wt_content.js"
```

或手动构建 JS 表达式：
```javascript
(function(){
  var e=document.querySelector('.ProseMirror');
  if(!e) return JSON.stringify({error:'no editor'});
  e.focus();
  var text='\u5954\u9a70GLE\u56fd\u4ea7\u4e86...';  // Unicode 转义
  document.execCommand('insertText',false,text);
  return JSON.stringify({len:e.textContent.length,preview:e.textContent.substring(0,100)});
})()
```

### 第二步：搜索并下载配图

#### 2.1 Pexels 搜图流程

1. **打开新标签页**：
   ```
   POST http://localhost:3456/new
   Body: https://www.pexels.com/search/{关键词}/
   ```

2. **等待 5 秒后提取图片**：
   ```javascript
   (function(){
     var imgs = document.querySelectorAll('article img, img[src*="pexels"]');
     var results = [];
     for(var i=0; i<imgs.length; i++){
       var src = imgs[i].src || '';
       var alt = imgs[i].alt || '';
       if(src.indexOf('images.pexels.com') > -1 && alt.length > 3){
         results.push({src: src, alt: alt.substring(0, 60)});
       }
     }
     return JSON.stringify({count: results.length, items: results.slice(0, 8)});
   })()
   ```

3. **选择图片**：根据 alt 描述确认图片内容与微头条主题匹配

#### 2.2 下载并验证 JPEG

```powershell
# 下载（替换 {id} 为 Pexels photo ID）
$url = "https://images.pexels.com/photos/{id}/pexels-photo-{id}.jpeg?auto=compress&cs=tinysrgb&w=800"
Invoke-WebRequest -Uri $url -OutFile "C:\Users\28470\wt_image.jpg" -UseBasicParsing

# JPEG 验证（强制）
$bytes = [System.IO.File]::ReadAllBytes("C:\Users\28470\wt_image.jpg")
$header = "{0:X2} {1:X2}" -f $bytes[0], $bytes[1]    # 应为 FF D8
$footer = "{0:X2} {1:X2}" -f $bytes[-2], $bytes[-1]   # 应为 FF D9
# FF D8 开头 + FF D9 结尾 = 有效 JPEG
```

**JPEG 验证不通过则换另一张图片，不可跳过此步。**

#### 2.3 Pexels 搜索关键词策略

| 微头条主题 | 推荐搜索词 |
|-----------|-----------|
| 新车上市 | "{品牌} {车型}", "luxury car", "new car" |
| 价格对比 | "car price", "car dealership", "car sale" |
| 新能源 | "electric car charging", "ev battery", "tesla" |
| 保养维修 | "mechanic hands engine", "car oil change" |
| 通用汽车 | "mercedes benz", "car driving", "car interior" |

### 第三步：发布微头条

#### 3.1 导航到发布页

```
POST http://localhost:3456/navigate?target={targetId}
Body: https://mp.toutiao.com/profile_v4/weitoutiao/publish
```

等待 5 秒，确认 ProseMirror 编辑器加载：
```javascript
(function(){
  var e = document.querySelector('.ProseMirror');
  return JSON.stringify({found: !!e, url: location.href});
})()
```

#### 3.2 输入内容

读取生成的 JS 文件（UTF-8 编码），通过 CDP `/eval` 执行：

```powershell
$js = [System.IO.File]::ReadAllText("C:\Users\28470\wt_content.js", [System.Text.Encoding]::UTF8)
$jsBytes = [System.Text.Encoding]::UTF8.GetBytes($js)
$r = Invoke-RestMethod -Uri "http://localhost:3456/eval?target=$targetId" -Method Post -Body $jsBytes -ContentType "text/plain"
$r.value
# 应返回 {"len":xxx,"preview":"..."} 表示成功
```

#### 3.3 上传配图（关键流程·6步）

**第1步：点击"图片"按钮**

用 /clickAt 点击工具栏图片按钮（必须用 /clickAt，JS .click() 不触发 Vue 事件）：
```
POST http://localhost:3456/clickAt?target={targetId}
Body: .weitoutiao-image-plugin
Content-Type: text/plain
```

等待 3 秒，确认弹窗出现（`.mp-ic-img-drawer` 可见）。

**第2步：点击"本地上传"标签**

```javascript
(function(){
  var btns = document.querySelectorAll('button,span,div');
  for(var i=0; i<btns.length; i++){
    if(btns[i].innerText.trim() === '本地上传' && btns[i].offsetParent !== null){
      btns[i].click();
      return 'clicked';
    }
  }
  return 'not found';
})()
```

等待 2 秒。

**第3步：setFiles 设置文件路径**

```
POST http://localhost:3456/setFiles?target={targetId}
Content-Type: application/json
Body: {"selector":".btn-upload-handle input","files":["C:\\Users\\28470\\wt_image.jpg"]}
```

**第4步：触发 change 事件**

```javascript
(function(){
  var inp = document.querySelector('.btn-upload-handle input');
  if(!inp) inp = document.querySelector('#upload-drag-input');
  if(!inp) return 'no input';
  inp.dispatchEvent(new Event('change', {bubbles: true}));
  return 'change dispatched';
})()
```

等待 4 秒让图片上传到 CDN 并出现在选择面板。

**第5步：选择图片并确认**

用 /clickAt 点击选择面板中的图片：
```
POST http://localhost:3456/clickAt?target={targetId}
Body: .pic-select-image-item img
Content-Type: text/plain
```

等待 2 秒，然后用 /clickAt 点击"确定"按钮：
```
POST http://localhost:3456/clickAt?target={targetId}
Body: .mp-ic-img-drawer button.byte-btn-primary.byte-btn-size-large
Content-Type: text/plain
```

等待 3 秒，弹窗关闭。

**第6步：验证图片已附加**

```javascript
(function(){
  var ub = document.querySelector('.upload-box');
  if(!ub) return JSON.stringify({error: 'no upload-box'});
  var html = ub.innerHTML;
  return JSON.stringify({
    hasBgImage: html.indexOf('background-image') > -1,
    hasUrl: html.indexOf('url(') > -1
  });
})()
// hasBgImage=true 且 hasUrl=true = 图片附加成功
```

**注意**：微头条图片在 `.upload-box` 中以 CSS `background-image` 形式存在，不是 `<img>` 标签。检查 `.ProseMirror img` 永远为 0，这是正常的。

#### 3.4 发布

**查找并标记发布按钮**：
```javascript
(function(){
  var btns = document.querySelectorAll('button');
  for(var i=0; i<btns.length; i++){
    if(btns[i].innerText.trim() === '发布' && !btns[i].disabled && btns[i].offsetParent !== null){
      btns[i].setAttribute('data-publish-btn', 'true');
      return JSON.stringify({found: true, disabled: btns[i].disabled});
    }
  }
  return JSON.stringify({found: false});
})()
```

**用 /clickAt 点击发布**：
```
POST http://localhost:3456/clickAt?target={targetId}
Body: [data-publish-btn]
Content-Type: text/plain
```

等待 3 秒。

### 第四步：发布后验证

#### 4.1 验证发布成功

```javascript
(function(){
  var body = document.body.innerText;
  var isManagePage = location.href.indexOf('profile_v4') > -1;
  var hasError = body.indexOf('发布失败') > -1 || body.indexOf('错误') > -1;
  var totalMatch = body.match(/共\s*(\d+)\s*条内容/);
  var total = totalMatch ? totalMatch[1] : 'unknown';
  return JSON.stringify({
    isManagePage: isManagePage,
    hasError: hasError,
    totalContent: total
  });
})()
```

**判定标准**：
- ✅ isManagePage=true（已跳转到管理页）
- ✅ hasError=false（无错误）
- ✅ totalContent 比发布前增加 1

#### 4.2 验证内容无乱码

检查管理页列表中是否包含微头条内容的关键词（如价格数字、品牌名等），中文显示正常无 `?` 乱码。

#### 4.3 验证报告格式

```
微头条发布验证报告：
[1] 发布状态：✅ 成功（总内容数 794→795）
[2] 乱码检验：✅ 通过（中文正常显示）
[3] 配图检验：✅ 通过（upload-box 含 background-image）
全部验证通过，微头条已成功发布。
```

## CDP 技术要点

### /clickAt vs JS .click()

Vue/React 事件需要真实 DOM 事件，`element.click()` 可能不触发。`/clickAt` 使用 `Input.dispatchMouseEvent` 模拟真实点击，更可靠。

**必须用 /clickAt 的场景**：
- 点击"图片"按钮（打开上传弹窗）
- 选择面板中的图片
- 点击"确定"按钮
- 点击"发布"按钮

### /clickAt 请求格式

```
POST http://localhost:3456/clickAt?target={targetId}
Content-Type: text/plain
Body: CSS选择器（纯文本，不是JSON）
```

**注意**：Body 是纯文本 CSS 选择器，不是 JSON。发送 JSON 会报 "not a valid selector" 错误。

### /setFiles 请求格式

```
POST http://localhost:3456/setFiles?target={targetId}
Content-Type: application/json
Body: {"selector":"CSS选择器","files":["绝对路径"]}
```

文件路径中的反斜杠需要双转义：`C:\\\\Users\\\\28470\\\\image.jpg`

### 中文编码

通过 PowerShell 向 CDP 发送中文时**必须**使用 Unicode 转义（`\uXXXX`），禁止直接发送中文字符串。流程：

1. Python 脚本将中文转为 `\uXXXX` 转义
2. 写入 .js 文件（UTF-8 编码）
3. PowerShell 用 `[System.IO.File]::ReadAllText` UTF-8 读取
4. 发送至 CDP `/eval`

## 常见问题排障

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `no editor` | 页面未加载或导航错误 | 重新导航到 weitoutiao/publish，等待 5 秒 |
| `not found`（本地上传） | 弹窗未打开 | 用 /clickAt 而非 JS .click() 点击"图片"按钮 |
| setFiles 报"未找到元素" | file input 不存在 | 必须先点击"图片"按钮创建 file input |
| upload-box 为空 | 未点"确定"确认 | 上传后必须点击确定按钮，图片才从选择面板移入 upload-box |
| 发布后无图片 | 图片在 ProseMirror 而非 upload-box | 微头条图片在 upload-box（background-image），不在编辑器内 |
| 内容乱码 | PowerShell 中文编码问题 | 必须用 Unicode 转义，禁止直接发中文 |
| `not a valid selector` | /clickAt body 格式错误 | body 是纯文本 CSS 选择器，不是 JSON |

## 辅助脚本

| 脚本 | 用途 |
|------|------|
| `scripts/gen_weitoutiao_js.py` | 将中文内容转为 Unicode 转义 JS 表达式 |

## 注意事项

1. **每日上限 10 条**：超过后仅推荐给粉丝，不发新内容
2. **必须带图**：无图点击率 <2%，有图 3-5%。账号数据验证 100% 带图
3. **仅 1 张图**：微头条只能附加 1 张图片
4. **图片在 upload-box**：不在 ProseMirror 编辑器内，以 background-image 形式存在
5. **无标题无封面**：微头条没有标题和封面概念
6. **无预览确认**：点击发布直接发布，无确认弹窗
7. **去AI味**（强制）：平台检测到 AI 生成会限流降权
8. **话题标签 ≥5**：含 1 个活动话题 + 热门话题，格式 `#话题名#`
9. **JPEG 验证**（强制）：下载后必须验证头尾字节，不通过则换图
10. **频率控制**：避免短时间内密集操作，防止触发平台风控

## Directory layout
```
weitoutiao-publisher/
├── scripts/
│   └── gen_weitoutiao_js.py
├── references/
│   └── cdp-examples.md
└── SKILL.md
```