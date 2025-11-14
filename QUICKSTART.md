# 快速开始指南

## 5 分钟快速设置

### 步骤 1: 安装 Python 依赖

打开命令行（CMD 或 PowerShell），进入项目目录：

```bash
cd C:\work\claudecode\uswait
pip install -r requirements.txt
```

### 步骤 2: 选择通知方式

项目支持两种通知方式，**推荐使用 Email**（免费、格式美观）。

#### 方式 A: Email 通知（推荐）

**使用 Gmail：**

1. 启用 Gmail 两步验证：https://myaccount.google.com/security
2. 生成应用专用密码（在"安全性" → "应用专用密码"）
3. 复制生成的16位密码

**详细步骤**：查看 [GMAIL_SETUP.md](GMAIL_SETUP.md)

**其他邮箱**：QQ邮箱、163邮箱、Outlook 等也支持，参考 `.env.example`

#### 方式 B: SMS 短信通知

1. 访问 https://www.twilio.com/try-twilio
2. 注册免费试用账号（送 $15 试用金）
3. 验证手机号并获取 Twilio 电话号码

### 步骤 3: 配置环境变量

1. 复制 `.env.example` 为 `.env`
2. 打开 `.env` 文件，根据您选择的通知方式填入配置

**Email 配置（推荐）：**
```env
NOTIFICATION_METHOD=email

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_16_digit_app_password
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=recipient@example.com
```

**SMS 配置：**
```env
NOTIFICATION_METHOD=sms

TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_FROM_NUMBER=+12345678901
TWILIO_TO_NUMBER=+8613800138000
```

### 步骤 4: 测试通知功能

双击运行 `test.bat` 或在命令行执行：

```bash
python main.py --mode test
```

- **Email 模式**：检查您的邮箱（包括垃圾邮件文件夹）
- **SMS 模式**：检查手机是否收到短信

如果收到测试通知，说明配置成功！

### 步骤 5: 启动监控

双击运行 `start.bat` 或在命令行执行：

```bash
python main.py --mode schedule
```

完成！程序现在会自动监控签证排期并发送通知。

## 常用命令

| 操作 | 批处理文件 | 命令行 |
|------|-----------|--------|
| 测试短信 | 双击 `test.bat` | `python main.py --mode test` |
| 查看状态 | 双击 `status.bat` | `python main.py --mode status` |
| 启动监控 | 双击 `start.bat` | `python main.py --mode schedule` |
| 手动抓取一次 | - | `python main.py --mode once` |

## 运行时间说明

程序会在以下时间自动运行：
- **时区**: 美国东部时间 (ET)
- **工作日**: 周一至周五
- **时间段**: 上午 9:00 - 下午 5:00
- **频率**: 每 15 分钟检查一次

**为什么选择这个时间？**
- 美国国务院通常在工作日发布公告
- 避免频繁请求导致 IP 被封
- 节省 Twilio 短信费用

## 开机自启动（可选）

### 方法 1: 使用任务计划程序（推荐）

1. 按 `Win + R`，输入 `taskschd.msc`，回车
2. 右侧点击"创建基本任务"
3. 名称：`Visa Bulletin Monitor`
4. 触发器：选择"计算机启动时"
5. 操作：选择"启动程序"
   - 程序：`C:\work\claudecode\uswait\start.bat`
6. 完成

### 方法 2: 添加到启动文件夹

1. 按 `Win + R`，输入 `shell:startup`，回车
2. 在打开的文件夹中，创建 `start.bat` 的快捷方式

## 故障排查

### 问题 1: 收不到通知

**Email 模式：**
- [ ] 检查垃圾邮件文件夹
- [ ] 确认应用专用密码正确
- [ ] 运行 `test.bat` 测试
- [ ] 查看日志文件 `logs/visa_scraper.log`

**SMS 模式：**
- [ ] 运行 `test.bat` 测试短信功能
- [ ] 检查 Twilio 账户余额是否充足
- [ ] 确认手机号已在 Twilio 中验证（试用账户限制）
- [ ] 查看日志文件 `logs/visa_scraper.log`

### 问题 2: 程序无法启动

**检查清单：**
- [ ] Python 版本是否 >= 3.8？运行 `python --version`
- [ ] 依赖是否安装？运行 `pip install -r requirements.txt`
- [ ] `.env` 文件是否存在且配置正确？

### 问题 3: 如何查看日志？

日志文件位置：`logs/visa_scraper.log`

使用记事本或任何文本编辑器打开即可。

### 问题 4: 如何停止程序？

- 如果在命令行运行：按 `Ctrl + C`
- 如果通过任务计划程序运行：在任务管理器中结束 `python.exe` 进程

## 下一步

- 阅读完整的 [README.md](README.md) 了解更多功能
- 查看 `data/visa_bulletin_history.json` 了解历史数据
- 根据需要调整 `config.py` 中的配置

## 需要帮助？

如有任何问题，请查看 [README.md](README.md) 中的"常见问题"部分。
