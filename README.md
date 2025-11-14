# US Visa Bulletin Monitor (中国区域)

自动监控美国国务院签证排期公告，专注于中国大陆地区的排期变化，并通过短信实时通知。

## 功能特点

- 自动抓取最新的 Visa Bulletin（即将发布的公告）
- 专门解析中国大陆的签证排期数据（Employment-Based 职业移民）
- 对比上个月的排期，检测所有变动
- 生成高可读性的中文通知信息
- **多种通知方式**：
  - **Email 邮件通知**（推荐，默认）- 支持 Gmail、QQ邮箱、163邮箱等
  - **SMS 短信通知** - 通过 Twilio 发送
- 智能调度：美东时间工作日（周一至周五）9 AM - 11 PM 每 15 分钟检查一次
- 月度管理：当月抓取成功后自动停止，下月重新激活
- JSON 文件存储历史数据，易于查看和备份

## 目录结构

```
uswait/
├── main.py                 # 主程序入口
├── config.py              # 配置文件
├── requirements.txt       # Python 依赖
├── .env                   # 环境变量（需要创建）
├── .env.example          # 环境变量示例
├── .gitignore            # Git 忽略文件
├── README.md             # 本文件
├── src/                  # 源代码目录
│   ├── __init__.py
│   ├── scraper.py        # 网页抓取模块
│   ├── parser.py         # 数据解析模块
│   ├── comparator.py     # 变动检测模块
│   ├── notifier.py       # 短信通知模块
│   ├── storage.py        # 数据存储模块
│   ├── scheduler.py      # 定时调度模块
│   ├── orchestrator.py   # 主协调器
│   └── logger.py         # 日志配置
├── data/                 # 数据存储目录
│   ├── visa_bulletin_history.json  # 历史数据
│   └── scraper_state.json          # 运行状态
└── logs/                 # 日志目录
    └── visa_scraper.log  # 日志文件
```

## 安装步骤

### 1. 安装 Python

确保已安装 Python 3.8 或更高版本：

```bash
python --version
```

### 2. 克隆或下载项目

```bash
cd C:\work\claudecode\uswait
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置通知方式

项目支持两种通知方式，默认使用 **Email**。

#### 方式 1: Email 通知（推荐）

**Gmail 配置**（详细步骤见 [GMAIL_SETUP.md](GMAIL_SETUP.md)）：

1. 启用 Gmail 两步验证
2. 生成应用专用密码
3. 在 `.env` 中配置邮箱信息

**其他邮箱**：
- QQ邮箱：需要授权码，SMTP: smtp.qq.com:587
- 163邮箱：需要授权码，SMTP: smtp.163.com:465
- Outlook：使用账户密码，SMTP: smtp-mail.outlook.com:587

#### 方式 2: SMS 短信通知

1. 注册 Twilio 账号：https://www.twilio.com/try-twilio
2. 获取 Account SID、Auth Token 和电话号码
3. 在 `.env` 中设置 `NOTIFICATION_METHOD=sms`

### 5. 创建环境变量文件

复制示例文件并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置通知方式：

**使用 Email 通知（默认，推荐）：**
```env
NOTIFICATION_METHOD=email

# Email 配置
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=recipient@example.com
```

**使用 SMS 短信通知：**
```env
NOTIFICATION_METHOD=sms

# Twilio 配置
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_FROM_NUMBER=+1234567890
TWILIO_TO_NUMBER=+8613800138000
```

## 使用方法

### 测试通知功能

在开始监控前，先测试通知功能是否正常：

```bash
python main.py --mode test
```

- **Email 模式**：您会收到一封测试邮件
- **SMS 模式**：您会收到一条测试短信

如果收到测试通知，说明配置成功！

### 查看当前状态

```bash
python main.py --mode status
```

### 运行单次抓取

手动运行一次抓取（用于测试）：

```bash
python main.py --mode once
```

### 启动定时监控（推荐）

启动后台监控，按计划自动运行：

```bash
python main.py --mode schedule
```

程序将在以下时间段运行：
- 美东时间周一至周五
- 9:00 AM - 11:00 PM
- 每 15 分钟检查一次

按 `Ctrl+C` 停止程序。

## 运行模式说明

| 模式 | 说明 | 使用场景 |
|------|------|---------|
| `test` | 发送测试短信 | 验证 Twilio 配置 |
| `status` | 显示当前状态 | 查看上次运行情况 |
| `once` | 运行单次抓取 | 手动测试抓取功能 |
| `schedule` | 定时自动运行 | 长期监控（推荐） |

## 日志说明

- 日志文件位置：`logs/visa_scraper.log`
- 日志级别：可在 `.env` 中设置 `LOG_LEVEL`（DEBUG, INFO, WARNING, ERROR）
- 日志轮转：单个文件最大 10MB，保留最近 5 个备份

## 数据文件说明

### visa_bulletin_history.json

存储历史公告数据，格式：

```json
[
  {
    "bulletin_date": "2024-11",
    "scrape_timestamp": "2024-10-15T10:30:00",
    "final_action_dates": {
      "EB-1": "C",
      "EB-2": "01JAN2020",
      "EB-3": "15JUN2018"
    },
    "filing_dates": {
      "EB-1": "C",
      "EB-2": "01FEB2020",
      "EB-3": "01JUL2018"
    }
  }
]
```

### scraper_state.json

存储运行状态：

```json
{
  "last_successful_scrape": "2024-10-15T10:30:00",
  "last_bulletin_month": "2024-11",
  "monthly_scrape_completed": true
}
```

## 通知消息格式

### Email 通知（HTML 格式）

Email 通知采用美观的 HTML 格式，包含：
- 彩色标题和分组
- 清晰的表格布局
- Emoji 图标标识
- 中英文对照

### SMS 短信通知

当检测到排期变化时，会收到如下格式的短信：

```
美国签证排期更新 (中国大陆)
==============================
上期: 2024-10 → 本期: 2024-11

【最终裁定日期 Final Action】
  EB-2: 01JAN2020 → 15FEB2020 (📈 前进)
  EB-3: 15JUN2018 → 01JUN2018 (📉 倒退)

【递件日期 Filing Dates】
  EB-2: 01FEB2020 → C (✅ 有名额)

检测时间: 2024-10-15 10:30:00
```

## 常见问题

### 1. 如何保持程序持续运行？

**Windows:**

可以创建一个批处理文件 `start.bat`：

```batch
@echo off
cd C:\work\claudecode\uswait
python main.py --mode schedule
pause
```

双击运行，或设置为开机启动。

**使用任务计划程序（推荐）：**

1. 打开"任务计划程序"
2. 创建基本任务
3. 设置触发器为"计算机启动时"
4. 操作：启动程序 `python.exe`，参数：`main.py --mode schedule`，起始于：`C:\work\claudecode\uswait`

### 2. 程序没有发送通知怎么办？

检查以下几点：
- 运行 `python main.py --mode test` 测试通知功能
- 查看日志文件 `logs/visa_scraper.log`
- **Email 模式**：
  - 检查垃圾邮件文件夹
  - 确认应用专用密码正确
  - 确认 SMTP 服务器和端口配置正确
- **SMS 模式**：
  - 确认 Twilio 账户余额充足
  - 确认目标手机号格式正确（包含国际区号，如 +86）

### 3. 如何查看历史抓取记录？

直接打开 `data/visa_bulletin_history.json` 文件查看。

### 4. 每月会发送多少条短信？

正常情况下：
- 如果有变化：1-2 条短信（取决于消息长度）
- 如果无变化：0 条短信
- 当月抓取成功后自动停止，不会重复发送

### 5. 可以同时发送邮件和短信吗？

当前版本一次只能使用一种通知方式。如需同时使用，可以：
- 运行两个实例，使用不同的配置文件
- 或修改代码同时初始化两种通知器

### 6. 为什么推荐使用 Email 而不是 SMS？

- **Email 优势**：
  - 免费或成本极低
  - 支持 HTML 格式，更美观易读
  - 可以保存历史记录
  - 不受国际短信限制
- **SMS 优势**：
  - 实时性更强
  - 不依赖网络，只需手机信号

## 技术栈

- **Python 3.8+**
- **requests**: HTTP 请求
- **BeautifulSoup4**: HTML 解析
- **Twilio**: 短信发送
- **APScheduler**: 任务调度
- **pytz**: 时区处理

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题，请提交 Issue。
