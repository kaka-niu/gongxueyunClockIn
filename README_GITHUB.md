# 工学云自动签到 - GitHub Actions部署

这是一个基于GitHub Actions的工学云自动签到系统，支持多用户配置，可以自动执行上班卡和下班卡的签到操作。

## 功能特点

- ✅ 支持多用户配置
- ✅ 自动判断打卡类型（上班卡/下班卡）
- ✅ 定时执行（早上7点和下午5点）
- ✅ 手动触发执行
- ✅ 邮件通知功能
- ✅ 免服务器运行

## 部署步骤

### 1. Fork 本仓库

点击右上角的"Fork"按钮，将本仓库复制到你的GitHub账户下。

### 2. 配置GitHub Secrets

在你的Fork仓库中，进入`Settings` -> `Secrets and variables` -> `Actions`，添加以下Secret：

- `USERS`: 用户配置JSON字符串

#### 用户配置格式

**单用户配置示例：**
```json
[
  {
    "config": {
      "user": {
        "phone": "15808462201",
        "password": "123456Qw"
      },
      "clockIn": {
        "mode": "twice_daily",
        "location": {
          "address": "四川省 · 资阳市 · 乐至县 · 友谊路南段与川西环线交叉口东北300米",
          "latitude": "30.428727249834488",
          "longitude": "104.90286311986283",
          "province": "四川省",
          "city": "资阳市",
          "area": "乐至县"
        },
        "holidaysClockIn": false,
        "customDays": [1, 2, 3, 4, 5],
        "time": { 
          "start": "7:00",
          "end": "17:00",
          "float": 1
        }
      },
      "smtp": {
        "enable": true,
        "host": "smtp.qq.com",
        "port": 465,
        "username": "2154335573@qq.com",
        "password": "yjociyslhygwebgc",
        "from": "工学云签到通知",
        "to": ["2154335573@qq.com"]
      },
      "device": "{brand: iOOZ9 Turbo, systemVersion: 15, Platform: Android, isPhysicalDevice: true, incremental: V2352A}"
    }
  }
]
```

**多用户配置示例：**
```json
[
  {
    "config": {
      "user": {
        "phone": "工学云手机号1",
        "password": "工学云密码1"
      },
      "clockIn": {
        "mode": "twice_daily",
        "location": {
          "address": "四川省 · 成都市 · 高新区 · 在科创十一街附近",
          "latitude": "30.559922",
          "longitude": "104.093023",
          "province": "四川省",
          "city": "成都市",
          "area": "高新区"
        },
        "holidaysClockIn": false,
        "customDays": [1, 2, 3, 4, 5],
        "time": { 
          "start": "7:00",
          "end": "17:00",
          "float": 1
        }
      },
      "smtp": {
        "enable": true,
        "host": "smtp.qq.com",
        "port": 465,
        "username": "your_email@qq.com",
        "password": "your_smtp_password",
        "from": "工学云签到通知",
        "to": ["your_email@qq.com"]
      },
      "device": "{brand: TA J20, systemVersion: 17, Platform: Android, isPhysicalDevice: true, incremental: K23V10A}"
    }
  },
  {
    "config": {
      "user": {
        "phone": "工学云手机号2",
        "password": "工学云密码2"
      },
      "clockIn": {
        "mode": "twice_daily",
        "location": {
          "address": "四川省 · 成都市 · 高新区 · 在科创十一街附近",
          "latitude": "30.559922",
          "longitude": "104.093023",
          "province": "四川省",
          "city": "成都市",
          "area": "高新区"
        },
        "holidaysClockIn": false,
        "customDays": [1, 2, 3, 4, 5],
        "time": { 
          "start": "7:00",
          "end": "17:00",
          "float": 1
        }
      },
      "smtp": {
        "enable": true,
        "host": "smtp.qq.com",
        "port": 465,
        "username": "your_email@qq.com",
        "password": "your_smtp_password",
        "from": "工学云签到通知",
        "to": ["your_email@qq.com"]
      },
      "device": "{brand: TA J20, systemVersion: 17, Platform: Android, isPhysicalDevice: true, incremental: K23V10A}"
    }
  }
]
```

### 3. 启用GitHub Actions

在你的Fork仓库中，进入`Actions`选项卡，点击"I understand my workflows, go ahead and enable them"按钮启用GitHub Actions。

## 工作流程

### 定时执行

- **早上7点**（UTC时间23点）：自动执行上班卡签到
- **下午5点**（UTC时间9点）：自动执行下班卡签到

### 手动执行

你也可以手动触发签到任务：

1. 进入你的Fork仓库的`Actions`选项卡
2. 选择"工学云自动签到"工作流
3. 点击"Run workflow"按钮
4. 选择打卡模式：
   - `manual`: 根据当前时间自动判断打卡类型
   - `morning`: 强制执行上班卡
   - `evening`: 强制执行下班卡
5. 点击"Run workflow"开始执行

## 配置说明

### 打卡模式

- `everyday`: 每天打卡
- `weekday`: 仅工作日打卡
- `customize`: 自定义星期几打卡
- `twice_daily`: 一天打两次卡（上班卡和下班卡）

### 邮件通知

配置SMTP信息后，打卡成功或失败都会发送邮件通知。

### 设备信息

设备信息用于模拟手机登录，可以使用默认值或自定义。

## 本地测试

如果你想本地测试，可以：

1. 克隆仓库到本地
2. 安装依赖：`pip install -r requirements.txt`
3. 创建`auto.yaml`配置文件（参考`auto.yaml`示例）
4. 运行：`python auto.py`

## 注意事项

1. **安全提醒**：不要将包含敏感信息的配置文件提交到公开仓库，务必使用GitHub Secrets存储用户配置。
2. **时区问题**：GitHub Actions使用UTC时间，定时任务已转换为北京时间。
3. **频率限制**：GitHub Actions有使用限制，免费账户每月有2000分钟的使用时间。
4. **日志查看**：你可以在Actions页面查看每次执行的详细日志。

## 故障排除

如果打卡失败，可以：

1. 检查Actions页面的执行日志
2. 确认用户配置是否正确
3. 检查网络连接是否正常
4. 尝试手动执行一次

## 更新日志

- v1.0.0: 初始版本，支持基本的自动签到功能
- v1.1.0: 添加多用户支持
- v1.2.0: 添加手动触发功能
- v1.3.0: 优化打卡逻辑和错误处理

## 许可证

本项目采用MIT许可证，详情请参阅[LICENSE](LICENSE)文件。