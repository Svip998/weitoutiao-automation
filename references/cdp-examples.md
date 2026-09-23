# CDP 操作示例

## 目录
1. [检查 CDP 状态](#检查-cdp-状态)
2. [Pexels 搜图](#pexels-搜图)
3. [导航到发布页](#导航到发布页)
4. [输入内容](#输入内容)
5. [上传配图完整流程](#上传配图完整流程)
6. [发布](#发布)
7. [验证](#验证)

## 检查 CDP 状态

```powershell
$targets = Invoke-RestMethod -Uri "http://localhost:3456/targets" -Method Get
$targets | ForEach-Object { Write-Output "$($_.targetId) - $($_.title) - $($_.url)" }
```

## Pexels 搜图

```powershell
# 打开新标签页
$response = Invoke-RestMethod -Uri "http://localhost:3456/new" -Method Post -Body "https://www.pexels.com/search/mercedes%20benz/" -ContentType "text/plain"
$plexusId = $response.targetId
Start-Sleep -Seconds 5

# 提取图片 URL
$js = "(function(){var imgs=document.querySelectorAll('article img, img[src*=\"pexels\"]');var r=[];for(var i=0;i<imgs.length;i++){var s=imgs[i].src||'';var a=imgs[i].alt||'';if(s.indexOf('images.pexels.com')>-1&&a.length>3){r.push({src:s,alt:a.substring(0,60)})}}return JSON.stringify({count:r.length,items:r.slice(0,8)})})()"
$jsBytes = [System.Text.Encoding]::UTF8.GetBytes($js)
$r = Invoke-RestMethod -Uri "http://localhost:3456/eval?target=$plexusId" -Method Post -Body $jsBytes -ContentType "text/plain"
$r.value
```

## 导航到发布页

```powershell
$targetId = "你的头条号targetId"
$navBytes = [System.Text.Encoding]::UTF8.GetBytes("https://mp.toutiao.com/profile_v4/weitoutiao/publish")
Invoke-RestMethod -Uri "http://localhost:3456/navigate?target=$targetId" -Method Post -Body $navBytes -ContentType "text/plain"
Start-Sleep -Seconds 5

# 确认编辑器加载
$checkJs = "(function(){var e=document.querySelector('.ProseMirror');return JSON.stringify({found:!!e,url:location.href})})()"
$checkBytes = [System.Text.Encoding]::UTF8.GetBytes($checkJs)
Invoke-RestMethod -Uri "http://localhost:3456/eval?target=$targetId" -Method Post -Body $checkBytes -ContentType "text/plain"
```

## 输入内容

```powershell
# 读取 Unicode 转义 JS 文件
$js = [System.IO.File]::ReadAllText("C:\Users\28470\wt_content.js", [System.Text.Encoding]::UTF8)
$jsBytes = [System.Text.Encoding]::UTF8.GetBytes($js)
$r = Invoke-RestMethod -Uri "http://localhost:3456/eval?target=$targetId" -Method Post -Body $jsBytes -ContentType "text/plain"
$r.value
# 返回 {"len":313,"preview":"奔驰GLE国产了..."} 表示成功
```

## 上传配图完整流程

```powershell
# 1. 点击"图片"按钮（用 /clickAt，不用 JS .click()）
$selector = ".weitoutiao-image-plugin"
$selBytes = [System.Text.Encoding]::UTF8.GetBytes($selector)
Invoke-RestMethod -Uri "http://localhost:3456/clickAt?target=$targetId" -Method Post -Body $selBytes -ContentType "text/plain"
Start-Sleep -Seconds 3

# 2. 点击"本地上传"
$localJs = "(function(){var b=document.querySelectorAll('button,span,div');for(var i=0;i<b.length;i++){if(b[i].innerText.trim()==='本地上传'&&b[i].offsetParent!==null){b[i].click();return 'clicked'}}return 'not found'})()"
$localBytes = [System.Text.Encoding]::UTF8.GetBytes($localJs)
Invoke-RestMethod -Uri "http://localhost:3456/eval?target=$targetId" -Method Post -Body $localBytes -ContentType "text/plain"
Start-Sleep -Seconds 2

# 3. setFiles 设置图片路径
$setFilesBody = '{"selector":".btn-upload-handle input","files":["C:\\\\Users\\\\28470\\\\wt_image.jpg"]}'
$sfBytes = [System.Text.Encoding]::UTF8.GetBytes($setFilesBody)
Invoke-RestMethod -Uri "http://localhost:3456/setFiles?target=$targetId" -Method Post -Body $sfBytes -ContentType "application/json"
Start-Sleep -Seconds 1

# 4. 触发 change 事件
$changeJs = "(function(){var i=document.querySelector('.btn-upload-handle input');if(!i)i=document.querySelector('#upload-drag-input');if(!i)return 'no input';i.dispatchEvent(new Event('change',{bubbles:true}));return 'ok'})()"
$changeBytes = [System.Text.Encoding]::UTF8.GetBytes($changeJs)
Invoke-RestMethod -Uri "http://localhost:3456/eval?target=$targetId" -Method Post -Body $changeBytes -ContentType "text/plain"
Start-Sleep -Seconds 4

# 5. 选择图片（/clickAt）
$imgSelector = ".pic-select-image-item img"
$imgBytes = [System.Text.Encoding]::UTF8.GetBytes($imgSelector)
Invoke-RestMethod -Uri "http://localhost:3456/clickAt?target=$targetId" -Method Post -Body $imgBytes -ContentType "text/plain"
Start-Sleep -Seconds 2

# 6. 点击"确定"（/clickAt）
$confirmSelector = ".mp-ic-img-drawer button.byte-btn-primary.byte-btn-size-large"
$confirmBytes = [System.Text.Encoding]::UTF8.GetBytes($confirmSelector)
Invoke-RestMethod -Uri "http://localhost:3456/clickAt?target=$targetId" -Method Post -Body $confirmBytes -ContentType "text/plain"
Start-Sleep -Seconds 3

# 7. 验证图片已附加
$verifyJs = "(function(){var u=document.querySelector('.upload-box');if(!u)return JSON.stringify({error:'no box'});var h=u.innerHTML;return JSON.stringify({hasBg:h.indexOf('background-image')>-1,hasUrl:h.indexOf('url(')>-1})})()"
$vBytes = [System.Text.Encoding]::UTF8.GetBytes($verifyJs)
Invoke-RestMethod -Uri "http://localhost:3456/eval?target=$targetId" -Method Post -Body $vBytes -ContentType "text/plain"
# 返回 {"hasBg":true,"hasUrl":true} = 成功
```

## 发布

```powershell
# 标记发布按钮
$markJs = "(function(){var b=document.querySelectorAll('button');for(var i=0;i<b.length;i++){if(b[i].innerText.trim()==='发布'&&!b[i].disabled&&b[i].offsetParent!==null){b[i].setAttribute('data-publish-btn','true');return 'found'}}return 'not found'})()"
$markBytes = [System.Text.Encoding]::UTF8.GetBytes($markJs)
Invoke-RestMethod -Uri "http://localhost:3456/eval?target=$targetId" -Method Post -Body $markBytes -ContentType "text/plain"

# 点击发布（/clickAt）
$pubSelector = "[data-publish-btn]"
$pubBytes = [System.Text.Encoding]::UTF8.GetBytes($pubSelector)
Invoke-RestMethod -Uri "http://localhost:3456/clickAt?target=$targetId" -Method Post -Body $pubBytes -ContentType "text/plain"
Start-Sleep -Seconds 3
```

## 验证

```powershell
$verifyJs = "(function(){var b=document.body.innerText;var m=b.match(/共\s*(\d+)\s*条内容/);return JSON.stringify({isManage:location.href.indexOf('profile_v4')>-1,hasError:b.indexOf('发布失败')>-1,total:m?m[1]:'unknown'})})()"
$vBytes = [System.Text.Encoding]::UTF8.GetBytes($verifyJs)
Invoke-RestMethod -Uri "http://localhost:3456/eval?target=$targetId" -Method Post -Body $vBytes -ContentType "text/plain"
# 返回 {"isManage":true,"hasError":false,"total":"795"} = 发布成功
```