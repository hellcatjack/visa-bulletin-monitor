# Ubuntu 24.04 Server 部署指南

本指南将帮助您在 Ubuntu 24.04 Server 上部署 US Visa Bulletin Monitor，并配置为系统服务长期运行。

## 系统要求

- Ubuntu 24.04 LTS Server
- Python 3.8 或更高版本
- 网络连接（用于抓取签证排期和发送通知）
- 足够的磁盘空间（用于日志和数据文件）

## 部署步骤

### 1. 安装系统依赖

```bash
# 更新系统包
sudo apt update && sudo apt upgrade -y

# 安装 Python 3 和 pip
sudo apt install -y python3 python3-pip python3-venv git

# 验证 Python 版本
python3 --version  # 应该是 3.8 或更高
```

### 2. 创建应用用户（推荐）

为了安全起见，建议创建一个专用用户来运行该服务：

```bash
# 创建系统用户（无登录权限）
sudo useradd -r -s /bin/false visa-monitor

# 或创建普通用户（可登录）
sudo useradd -m -s /bin/bash visa-monitor
```

### 3. 部署应用代码

```bash
# 切换到应用目录
cd /opt

# 克隆或复制项目到服务器
# 方法 1: 使用 git（如果项目在 git 仓库）
sudo git clone <your-repo-url> uswait

# 方法 2: 使用 scp 从本地复制
# 在本地机器上运行：
# scp -r C:\work\claudecode\uswait username@your-server:/tmp/
# 在服务器上运行：
# sudo mv /tmp/uswait /opt/

# 设置目录权限
sudo chown -R visa-monitor:visa-monitor /opt/uswait
sudo chmod -R 755 /opt/uswait
```

### 4. 安装 Python 依赖

```bash
cd /opt/uswait

# 创建虚拟环境（推荐）
sudo -u visa-monitor python3 -m venv venv

# 激活虚拟环境并安装依赖
sudo -u visa-monitor bash -c "source venv/bin/activate && pip install -r requirements.txt"
```

### 5. 配置环境变量

```bash
# 复制配置文件模板
sudo cp .env.example .env

# 编辑配置文件
sudo nano .env
```

填写以下配置（Email 通知示例）：

```env
NOTIFICATION_METHOD=email

# Email 配置
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_specific_password
EMAIL_FROM=your_email@gmail.com

# 多个收件人：用逗号分隔
EMAIL_TO=recipient1@example.com,recipient2@example.com,recipient3@example.com

# 日志级别
LOG_LEVEL=INFO
```

保存并设置权限：

```bash
sudo chown visa-monitor:visa-monitor .env
sudo chmod 600 .env  # 仅所有者可读写（保护密码）
```

### 6. 测试应用

在配置为系统服务之前，先测试应用是否正常工作：

```bash
# 切换到应用用户（如果使用专用用户）
sudo -u visa-monitor bash

# 激活虚拟环境
cd /opt/uswait
source venv/bin/activate

# 测试通知功能
python3 main.py --mode test

# 测试单次抓取
python3 main.py --mode once

# 查看状态
python3 main.py --mode status

# 退出测试
exit
```

### 7. 配置 systemd 服务

#### 7.1 编辑服务文件

编辑项目中的 `visa-monitor.service` 文件：

```bash
sudo nano /opt/uswait/visa-monitor.service
```

修改以下内容：

```ini
[Unit]
Description=US Visa Bulletin Monitor Service
After=network.target

[Service]
Type=simple
User=visa-monitor
Group=visa-monitor
WorkingDirectory=/opt/uswait
Environment="PATH=/opt/uswait/venv/bin:/usr/bin:/usr/local/bin"
ExecStart=/opt/uswait/venv/bin/python3 /opt/uswait/main.py --mode schedule
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=visa-monitor

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/opt/uswait/data /opt/uswait/logs

[Install]
WantedBy=multi-user.target
```

**重要修改点：**
- `User` 和 `Group`: 改为您创建的用户名（默认 `visa-monitor`）
- `WorkingDirectory`: 改为您的应用实际路径（默认 `/opt/uswait`）
- `ExecStart`: 使用虚拟环境中的 Python
- `ReadWritePaths`: 确保应用可以写入 data 和 logs 目录

#### 7.2 安装并启动服务

```bash
# 复制服务文件到 systemd 目录
sudo cp /opt/uswait/visa-monitor.service /etc/systemd/system/

# 重新加载 systemd 配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start visa-monitor

# 检查服务状态
sudo systemctl status visa-monitor

# 设置开机自启动
sudo systemctl enable visa-monitor
```

### 8. 管理服务

```bash
# 查看服务状态
sudo systemctl status visa-monitor

# 启动服务
sudo systemctl start visa-monitor

# 停止服务
sudo systemctl stop visa-monitor

# 重启服务
sudo systemctl restart visa-monitor

# 查看日志（实时）
sudo journalctl -u visa-monitor -f

# 查看最近 100 行日志
sudo journalctl -u visa-monitor -n 100

# 查看今天的日志
sudo journalctl -u visa-monitor --since today

# 查看应用日志文件
sudo tail -f /opt/uswait/logs/visa_scraper.log
```

### 9. 日志管理

#### 9.1 配置日志轮转

为了防止日志文件过大，应用已内置日志轮转（10MB，保留 5 个备份）。

如需进一步配置系统日志轮转：

```bash
sudo nano /etc/logrotate.d/visa-monitor
```

添加以下内容：

```
/opt/uswait/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0644 visa-monitor visa-monitor
}
```

#### 9.2 限制 systemd 日志大小

```bash
sudo nano /etc/systemd/journald.conf
```

添加或修改：

```ini
[Journal]
SystemMaxUse=500M
SystemMaxFileSize=50M
```

重启日志服务：

```bash
sudo systemctl restart systemd-journald
```

## 故障排查

### 服务无法启动

1. **检查服务状态和日志**：
   ```bash
   sudo systemctl status visa-monitor
   sudo journalctl -u visa-monitor -n 50
   ```

2. **检查文件权限**：
   ```bash
   ls -la /opt/uswait
   ls -la /opt/uswait/.env
   ls -la /opt/uswait/data
   ls -la /opt/uswait/logs
   ```

3. **手动运行测试**：
   ```bash
   sudo -u visa-monitor bash
   cd /opt/uswait
   source venv/bin/activate
   python3 main.py --mode once
   ```

### 无法发送通知

1. **检查网络连接**：
   ```bash
   ping -c 4 smtp.gmail.com
   ```

2. **检查 .env 配置**：
   ```bash
   sudo cat /opt/uswait/.env
   ```

3. **测试通知功能**：
   ```bash
   sudo -u visa-monitor bash
   cd /opt/uswait
   source venv/bin/activate
   python3 main.py --mode test
   ```

### 权限问题

如果遇到权限错误：

```bash
# 修复目录权限
sudo chown -R visa-monitor:visa-monitor /opt/uswait
sudo chmod -R 755 /opt/uswait

# .env 文件应该是 600 权限
sudo chmod 600 /opt/uswait/.env

# data 和 logs 目录需要写入权限
sudo chmod -R 755 /opt/uswait/data
sudo chmod -R 755 /opt/uswait/logs
```

## 安全建议

1. **使用专用系统用户**：不要使用 root 运行服务
2. **保护敏感文件**：`.env` 文件应设置为 600 权限
3. **定期更新**：保持系统和 Python 包更新
4. **防火墙配置**：如果启用防火墙，确保允许 SMTP 出站连接
5. **监控日志**：定期检查日志以发现异常

## 更新应用

```bash
# 停止服务
sudo systemctl stop visa-monitor

# 备份数据和配置
sudo cp -r /opt/uswait/data /opt/uswait/data.backup
sudo cp /opt/uswait/.env /opt/uswait/.env.backup

# 拉取最新代码（如果使用 git）
cd /opt/uswait
sudo -u visa-monitor git pull

# 或使用 scp 覆盖文件
# scp -r C:\work\claudecode\uswait/* username@your-server:/tmp/uswait-new/
# sudo cp -r /tmp/uswait-new/* /opt/uswait/

# 更新依赖（如果 requirements.txt 有变化）
sudo -u visa-monitor bash -c "source venv/bin/activate && pip install -r requirements.txt"

# 恢复配置文件
sudo cp /opt/uswait/.env.backup /opt/uswait/.env

# 重新加载并启动服务
sudo systemctl daemon-reload
sudo systemctl start visa-monitor

# 检查状态
sudo systemctl status visa-monitor
```

## 卸载

```bash
# 停止并禁用服务
sudo systemctl stop visa-monitor
sudo systemctl disable visa-monitor

# 删除服务文件
sudo rm /etc/systemd/system/visa-monitor.service
sudo systemctl daemon-reload

# 删除应用文件（谨慎操作）
sudo rm -rf /opt/uswait

# 删除用户（如果创建了专用用户）
sudo userdel -r visa-monitor
```

## 备份和恢复

### 备份

```bash
# 创建备份目录
sudo mkdir -p /backup/visa-monitor

# 备份数据和配置
sudo tar -czf /backup/visa-monitor/backup-$(date +%Y%m%d).tar.gz \
  -C /opt/uswait data logs .env

# 查看备份
ls -lh /backup/visa-monitor/
```

### 恢复

```bash
# 解压备份
sudo tar -xzf /backup/visa-monitor/backup-YYYYMMDD.tar.gz -C /opt/uswait

# 恢复权限
sudo chown -R visa-monitor:visa-monitor /opt/uswait/data
sudo chown -R visa-monitor:visa-monitor /opt/uswait/logs
sudo chmod 600 /opt/uswait/.env

# 重启服务
sudo systemctl restart visa-monitor
```

## 常见问题

### 1. Python 版本不兼容

如果系统默认 Python 版本过低：

```bash
# 安装 Python 3.11
sudo apt install -y python3.11 python3.11-venv

# 使用指定版本创建虚拟环境
python3.11 -m venv venv
```

### 2. 时区设置

确保服务器时区正确（程序使用美东时间调度）：

```bash
# 查看当前时区
timedatectl

# 设置时区（可选，程序会自动处理）
sudo timedatectl set-timezone America/New_York
```

### 3. 内存不足

如果运行在低内存服务器上（如 512MB VPS）：

```bash
# 添加 swap 空间
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 联系支持

如有问题，请查看：
- 应用日志: `/opt/uswait/logs/visa_scraper.log`
- 系统日志: `sudo journalctl -u visa-monitor`
- 项目 README: `/opt/uswait/README.md`
