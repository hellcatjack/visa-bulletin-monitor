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
sudo git clone <your-repo-url> visa-bulletin-monitor

# 方法 2: 使用 scp 从本地复制
# 在本地机器上运行：
# scp -r /path/to/visa-bulletin-monitor username@your-server:/tmp/
# 在服务器上运行：
# sudo mv /tmp/visa-bulletin-monitor /opt/

# 设置目录权限
sudo chown -R visa-monitor:visa-monitor /opt/visa-bulletin-monitor
sudo chmod -R 755 /opt/visa-bulletin-monitor
```

### 4. 安装 Python 依赖

**重要提示**：请使用系统 Python（`/usr/bin/python3`），不要使用 pyenv 或用户目录下的 Python。

```bash
cd /opt/visa-bulletin-monitor

# 确认使用系统 Python（应该显示 /usr/bin/python3）
which python3
python3 --version

# 如果显示的是 pyenv 路径，临时禁用 pyenv
# export PATH="/usr/bin:$PATH"

# 创建虚拟环境（推荐）
sudo -u visa-monitor python3 -m venv .venv

# 验证虚拟环境使用的是系统 Python
readlink -f .venv/bin/python3  # 应该指向 /usr/bin/python3.*

# 激活虚拟环境并安装依赖
sudo -u visa-monitor bash -c "source .venv/bin/activate && pip install -r requirements.txt"
```

**说明**：
- 使用系统 Python 避免 systemd 服务权限问题
- pyenv Python 位于用户 home 目录，systemd 默认无法访问
- 系统 Python 位于 `/usr/bin/`，所有用户都可访问

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
cd /opt/visa-bulletin-monitor
source .venv/bin/activate

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
sudo nano /opt/visa-bulletin-monitor/visa-monitor.service
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
WorkingDirectory=/opt/visa-bulletin-monitor
Environment="PATH=/opt/visa-bulletin-monitor/.venv/bin:/usr/bin:/usr/local/bin"
ExecStart=/opt/visa-bulletin-monitor/.venv/bin/python3 /opt/visa-bulletin-monitor/main.py --mode schedule
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
ReadWritePaths=/opt/visa-bulletin-monitor/data /opt/visa-bulletin-monitor/logs

[Install]
WantedBy=multi-user.target
```

**重要修改点：**
- `User` 和 `Group`: 改为您创建的用户名（默认 `visa-monitor`）
- `WorkingDirectory`: 改为您的应用实际路径（默认 `/opt/visa-bulletin-monitor`）
- `Environment`: 设置虚拟环境的 PATH（使用 `.venv`）
- `ExecStart`: 使用虚拟环境中的 Python（`.venv/bin/python3`）
- `ReadWritePaths`: 确保应用可以写入 data 和 logs 目录

#### 7.2 安装并启动服务

```bash
# 复制服务文件到 systemd 目录
sudo cp /opt/visa-bulletin-monitor/visa-monitor.service /etc/systemd/system/

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
sudo tail -f /opt/visa-bulletin-monitor/logs/visa_scraper.log
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
/opt/visa-bulletin-monitor/logs/*.log {
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
   ls -la /opt/visa-bulletin-monitor
   ls -la /opt/visa-bulletin-monitor/.env
   ls -la /opt/visa-bulletin-monitor/data
   ls -la /opt/visa-bulletin-monitor/logs
   ```

3. **手动运行测试**：
   ```bash
   sudo -u visa-monitor bash
   cd /opt/visa-bulletin-monitor
   source .venv/bin/activate
   python3 main.py --mode once
   ```

### 权限执行错误（status=203/EXEC）

如果日志显示 `Failed to execute ... Permission denied` 和 `status=203/EXEC`：

**原因分析**：

1. **systemd 安全设置过严**：
   - `ProtectSystem=strict` 将 `/opt` 目录设为只读
   - `ProtectHome=read-only` 阻止访问用户 home 目录

2. **pyenv Python 位置问题**（常见）：
   - 如果虚拟环境使用了 pyenv 安装的 Python（位于 `/home/username/.pyenv/`）
   - systemd 的 `ProtectHome` 限制会阻止访问该 Python 解释器
   - 检查方法：`readlink -f /opt/visa-bulletin-monitor/.venv/bin/python3`
   - 如果路径包含 `/home/` 或 `.pyenv`，则存在此问题

**解决方案**：

**方案 1：使用系统 Python 重建虚拟环境（推荐）**

这是最佳实践，避免依赖用户目录：

```bash
# 1. 停止服务
sudo systemctl stop visa-monitor

# 2. 备份当前虚拟环境
sudo mv /opt/visa-bulletin-monitor/.venv /opt/visa-bulletin-monitor/.venv.backup

# 3. 检查系统 Python 版本（需要 >= 3.8）
python3 --version
which python3  # 应该显示 /usr/bin/python3

# 4. 使用系统 Python 创建虚拟环境
sudo -u visa-monitor python3 -m venv /opt/visa-bulletin-monitor/.venv

# 5. 安装依赖
sudo -u visa-monitor bash -c "source /opt/visa-bulletin-monitor/.venv/bin/activate && pip install -r /opt/visa-bulletin-monitor/requirements.txt"

# 6. 验证 Python 路径（应该指向 /usr/bin/python3）
readlink -f /opt/visa-bulletin-monitor/.venv/bin/python3

# 7. 启动服务
sudo systemctl start visa-monitor
sudo systemctl status visa-monitor
```

**方案 2：调整 systemd 安全设置（临时方案）**

如果必须使用 pyenv Python，修改服务文件：

```bash
# 编辑服务文件
sudo nano /etc/systemd/system/visa-monitor.service
```

修改安全设置部分：
```ini
# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
# 移除 ProtectHome=read-only 这一行
```

重新加载并启动：
```bash
sudo systemctl daemon-reload
sudo systemctl restart visa-monitor
sudo systemctl status visa-monitor
```

**方案 3：修复文件权限**（基本检查）

```bash
# 确保所有文件归 visa-monitor 用户所有
sudo chown -R visa-monitor:visa-monitor /opt/visa-bulletin-monitor

# 设置正确的权限
sudo chmod -R 755 /opt/visa-bulletin-monitor

# 确保虚拟环境可执行文件有执行权限
sudo chmod +x /opt/visa-bulletin-monitor/.venv/bin/*
```

**推荐流程**：

1. 先执行方案 3 修复基本权限
2. 如果仍有问题，检查是否使用了 pyenv Python
3. 如果使用了 pyenv，优先执行方案 1（重建虚拟环境）
4. 如果方案 1 不可行，使用方案 2（调整安全设置）

### 无法发送通知

1. **检查网络连接**：
   ```bash
   ping -c 4 smtp.gmail.com
   ```

2. **检查 .env 配置**：
   ```bash
   sudo cat /opt/visa-bulletin-monitor/.env
   ```

3. **测试通知功能**：
   ```bash
   sudo -u visa-monitor bash
   cd /opt/visa-bulletin-monitor
   source .venv/bin/activate
   python3 main.py --mode test
   ```

### 权限问题

如果遇到权限错误：

```bash
# 修复目录权限
sudo chown -R visa-monitor:visa-monitor /opt/visa-bulletin-monitor
sudo chmod -R 755 /opt/visa-bulletin-monitor

# .env 文件应该是 600 权限
sudo chmod 600 /opt/visa-bulletin-monitor/.env

# data 和 logs 目录需要写入权限
sudo chmod -R 755 /opt/visa-bulletin-monitor/data
sudo chmod -R 755 /opt/visa-bulletin-monitor/logs
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
sudo cp -r /opt/visa-bulletin-monitor/data /opt/visa-bulletin-monitor/data.backup
sudo cp /opt/visa-bulletin-monitor/.env /opt/visa-bulletin-monitor/.env.backup

# 拉取最新代码（如果使用 git）
cd /opt/visa-bulletin-monitor
sudo -u visa-monitor git pull

# 或使用 scp 覆盖文件
# scp -r /path/to/visa-bulletin-monitor/* username@your-server:/tmp/visa-bulletin-monitor-new/
# sudo cp -r /tmp/visa-bulletin-monitor-new/* /opt/visa-bulletin-monitor/

# 更新依赖（如果 requirements.txt 有变化）
sudo -u visa-monitor bash -c "source .venv/bin/activate && pip install -r requirements.txt"

# 恢复配置文件
sudo cp /opt/visa-bulletin-monitor/.env.backup /opt/visa-bulletin-monitor/.env

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
sudo rm -rf /opt/visa-bulletin-monitor

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
  -C /opt/visa-bulletin-monitor data logs .env

# 查看备份
ls -lh /backup/visa-monitor/
```

### 恢复

```bash
# 解压备份
sudo tar -xzf /backup/visa-monitor/backup-YYYYMMDD.tar.gz -C /opt/visa-bulletin-monitor

# 恢复权限
sudo chown -R visa-monitor:visa-monitor /opt/visa-bulletin-monitor/data
sudo chown -R visa-monitor:visa-monitor /opt/visa-bulletin-monitor/logs
sudo chmod 600 /opt/visa-bulletin-monitor/.env

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
python3.11 -m venv .venv
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
- 应用日志: `/opt/visa-bulletin-monitor/logs/visa_scraper.log`
- 系统日志: `sudo journalctl -u visa-monitor`
- 项目 README: `/opt/visa-bulletin-monitor/README.md`
