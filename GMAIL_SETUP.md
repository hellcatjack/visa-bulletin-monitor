# Gmail 邮件通知配置指南

## 步骤 1: 启用两步验证

Gmail 要求使用应用专用密码（App Password）来通过 SMTP 发送邮件。

1. 访问 Google 账户：https://myaccount.google.com/
2. 点击左侧"安全性"（Security）
3. 在"登录 Google"部分，启用"两步验证"（2-Step Verification）
4. 按照提示完成两步验证设置

## 步骤 2: 生成应用专用密码

1. 返回"安全性"页面
2. 在"登录 Google"部分，点击"应用专用密码"（App passwords）
   - 如果没有看到此选项，确保已启用两步验证
3. 在"选择应用"下拉菜单中选择"邮件"
4. 在"选择设备"下拉菜单中选择"Windows 电脑"（或其他）
5. 点击"生成"
6. **复制生成的16位密码**（格式：xxxx xxxx xxxx xxxx）
   - 保存好这个密码，稍后需要用到
   - 这个密码只显示一次，请立即保存

## 步骤 3: 配置 .env 文件

编辑 `.env` 文件，设置以下内容：

```env
# 通知方式：使用邮件
NOTIFICATION_METHOD=email

# ===== Email Configuration =====
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password_here
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=recipient@example.com
```

**说明：**
- `SMTP_USER`: 您的 Gmail 邮箱地址
- `SMTP_PASSWORD`: 第2步生成的应用专用密码（移除空格）
- `EMAIL_FROM`: 发件人邮箱（通常和 SMTP_USER 相同）
- `EMAIL_TO`: 接收通知的邮箱地址（可以是任何邮箱）

**示例：**
```env
SMTP_USER=example@gmail.com
SMTP_PASSWORD=abcdabcdabcdabcd
EMAIL_FROM=example@gmail.com
EMAIL_TO=mywork@company.com
```

## 步骤 4: 测试邮件配置

配置完成后，运行测试：

```bash
python main.py --mode test
```

如果配置正确，您会收到一封测试邮件。

## 常见问题

### 1. 错误：SMTP Authentication Error

**原因**: 应用专用密码不正确

**解决方案**:
- 重新生成应用专用密码
- 确保密码中没有空格
- 确保使用的是应用专用密码，不是 Gmail 账户密码

### 2. 错误：Connection refused

**原因**: 端口或主机设置错误

**解决方案**:
- 确认 `SMTP_HOST=smtp.gmail.com`
- 确认 `SMTP_PORT=587`
- 确认 `SMTP_USE_TLS=true`

### 3. 未收到邮件

**检查项**:
- 查看垃圾邮件文件夹
- 检查 `EMAIL_TO` 地址是否正确
- 查看日志文件 `logs/visa_scraper.log`

### 4. 在中国大陆无法连接 Gmail

Gmail 在中国大陆可能无法访问。建议：
- 使用 VPN
- 或改用国内邮箱服务（QQ邮箱、163邮箱等）

## 安全提示

1. ✅ 应用专用密码只用于此应用
2. ✅ 不要与他人分享应用专用密码
3. ✅ 可以随时在 Google 账户中撤销应用专用密码
4. ✅ `.env` 文件已在 `.gitignore` 中，不会被提交到 Git

## 其他邮箱服务

如需使用其他邮箱服务，请参考 `.env.example` 中的配置说明。
