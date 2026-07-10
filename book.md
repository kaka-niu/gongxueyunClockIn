# 工学云自动打卡系统实现原理

## 项目概述

工学云自动打卡系统是一个基于Python的自动化工具，用于自动完成工学云平台的每日打卡任务。该项目通过模拟真实用户操作，实现自动登录、获取计划信息、执行打卡以及发送邮件通知等功能。

---

## 使用方法

### 1. 环境准备

- Python 3.10+
- Windows / Linux / macOS

```bash
pip install -r requirements.txt
```

### 2. 配置文件

配置文件位于 `user/config.json`，支持**多用户**数组格式：

```json
[
  {
    "config": {
      "user": {
        "phone": "13800138000",
        "password": "your_password"
      },
      "clockIn": {
        "mode": "twice_daily",
        "location": {
          "address": "四川省 · 成都市 · 高新区 · xxx附近",
          "latitude": "30.559922",
          "longitude": "104.093023",
          "province": "四川省",
          "city": "成都市",
          "area": "高新区"
        },
        "holidaysClockIn": false,
        "customDays": [1, 2, 3, 4, 5],
        "time": {
          "start": "08:00",
          "float": 10
        }
      },
      "smtp": {
        "enable": true,
        "host": "smtp.qq.com",
        "port": 465,
        "username": "sender@qq.com",
        "password": "smtp_auth_code",
        "from": "gongxueyun",
        "to": ["receiver@qq.com"]
      },
      "device": "{brand: Xiaomi 17Pro, systemVersion: 16, Platform: Android, isPhysicalDevice: true, incremental: 25098PN5AC}"
    }
  }
]
```

| 配置项 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `user.phone` | string | ✅ | 工学云注册手机号 |
| `user.password` | string | ✅ | 工学云登录密码 |
| `clockIn.mode` | string | ✅ | 打卡模式：`single` / `twice_daily` / `everyday` |
| `clockIn.type` | string | 单次模式必填 | `START`（上班）/ `END`（下班）/ `HOLIDAY`（休息） |
| `clockIn.location` | object | ✅ | 打卡GPS坐标和地址 |
| `clockIn.time` | object | ✅ | `start` 打卡时间，`float` 随机浮动分钟数 |
| `clockIn.customDays` | array | 自定义模式必填 | 星期几打卡（1=周一，7=周日） |
| `clockIn.holidaysClockIn` | bool | — | 法定节假日是否打卡 |
| `smtp` | object | — | 邮件通知配置，`enable: false` 可关闭 |
| `device` | string | ✅ | 模拟设备信息 |

### 3. 打卡模式

| 模式 | 配置值 | 行为 |
|------|--------|------|
| 单次打卡 | `single` | 根据 `clockIn.type` 打一次卡 |
| 一天两次 | `twice_daily` | 依次打 START（上班）+ END（下班） |
| 每天一次 | `everyday` | 每天按 `clockIn.type` 打一次卡 |

### 4. 本地运行

```bash
# 方式一：直接运行（支持多用户，GUI 配置界面）
python gongxueyun.py

# 方式二：命令行运行（支持多用户，无 GUI）
python main.py
```

运行后程序会：
1. 读取 `user/config.json` 中的所有用户配置
2. 依次为每个用户登录、获取实习计划、执行打卡
3. 打卡结果通过邮件通知（如已配置 SMTP）
4. 日志输出到 `main.log`

### 5. GitHub Actions 自动运行（推荐）

项目已配置 `.github/workflows/clockIn.yml`，每天北京时间 7:00 和 17:00 自动执行。

**配置步骤：**

1. Fork 本项目到自己的 GitHub 仓库
2. 在仓库 Settings → Secrets and variables → Actions 中添加密钥
3. 值与 `user/config.json` 格式相同（多用户数组）
4. GitHub Actions 会自动按 cron 定时执行

### 6. 多用户配置

`user/config.json` 是一个**数组**，每个元素代表一个用户：

```json
[
  { "config": { "user": { "phone": "13800138000", ... }, ... } },
  { "config": { "user": { "phone": "13900139000", ... }, ... } }
]
```

程序会依次为每个用户独立执行登录和打卡，互不影响。

### 7. 数据文件说明

| 文件 | 说明 |
|------|------|
| `user/config.json` | 用户配置（手动编辑） |
| `user/userInfo.json` | 登录后自动生成，存储 token 等信息 |
| `user/planInfo.json` | 自动生成，存储实习计划 |
| `main.log` | 运行日志 |

> 注意：`userInfo.json` 中的手机号会自动脱敏存储（如 `138****8000`），避免泄露。

---

## 项目架构

### 主要目录结构

```
.
├── manager/           # 配置和数据管理模块
│   ├── ConfigManager.py      # 系统配置管理
│   ├── PlanInfoManager.py    # 计划信息管理
│   └── UserInfoManager.py    # 用户信息管理
├── step/              # 执行步骤模块
│   ├── clockIn.py     # 打卡执行
│   ├── fetchPlan.py   # 获取计划
│   ├── login.py       # 登录
│   └── sendEmail.py   # 发送邮件
├── user/              # 用户数据存储
│   ├── config.json    # 用户配置文件
│   ├── planInfo.json  # 计划信息文件
│   └── userInfo.json  # 用户信息文件
├── util/              # 工具模块
│   ├── ApiService.py      # API服务接口
│   ├── CaptchaUtils.py    # 验证码处理
│   ├── CryptoUtils.py     # 加密解密工具
│   ├── EmailService.py    # 邮件服务
│   ├── HelperFunctions.py # 辅助函数
│   ├── image_utils.py     # 图像处理
│   └── ocr.py             # OCR识别
├── models/            # ONNX 模型文件
│   ├── ocr.onnx       # 文字识别模型
│   └── yolov5n.onnx   # 目标检测模型
├── ui/                # PyQt5 图形界面
│   ├── ui.py
│   └── ui.ui
├── gongxueyun.py      # GUI 主程序入口
├── main.py            # 命令行主程序入口
├── clockIn.py         # GitHub Actions 入口
├── config.json        # 系统配置文件
└── requirements.txt
```

## 核心模块详解

### 1. 配置管理模块 (manager/)

#### ConfigManager.py
- 负责管理 [config.json](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/config.json) 配置文件
- 提供 [get](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/manager/ConfigManager.py#L57-L72) 和 [set](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/manager/ConfigManager.py#L74-L84) 方法访问任意层级的配置项
- 支持嵌套键访问，如 `ConfigManager.get("clockIn", "location", "address")`
- 缓存配置数据，避免重复读取文件

#### UserInfoManager.py
- 管理用户信息，包括登录凭证、token等
- 将用户数据存储在 [userInfo.json](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/user/userInfo.json) 文件中
- 提供对用户信息的缓存访问，支持嵌套键访问

#### PlanInfoManager.py
- 管理实习计划信息，存储在 [planInfo.json](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/user/planInfo.json) 文件中
- 实现大小写不敏感的键访问，提高容错性

### 2. 执行步骤模块 (step/)

#### login.py
- 实现登录流程，首先检查本地是否已有有效token
- 如果本地token存在且用户信息一致，则跳过登录
- 否则调用 [ApiService](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/util/ApiService.py#L32-L435) 执行登录操作
- 登录成功后将用户信息保存到 [userInfo.json](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/user/userInfo.json)

#### fetchPlan.py
- 获取用户的实习计划信息
- 检查本地是否已有计划信息，如有则跳过获取
- 调用 [ApiService.fetch_plan()](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/util/ApiService.py#L322-L353) 获取计划并保存到 [planInfo.json](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/user/planInfo.json)

#### clockIn.py
- 执行打卡操作的核心模块
- 根据配置和时间判断打卡类型（上班/下班/节假日）
- 避免重复打卡，检查当日是否已完成相应打卡
- 调用 [ApiService.submit_clock_in()](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/util/ApiService.py#L377-L434) 提交打卡信息

#### sendEmail.py
- 可选的邮件通知功能
- 根据配置决定是否启用邮件通知
- 发送打卡成功或失败的通知邮件

### 3. 工具模块 (util/)

#### ApiService.py
- 项目的核心网络请求模块
- 封装了与工学云服务器的所有API交互
- 处理登录、获取计划、打卡等操作
- 实现了自动处理滑块验证码和点选验证码的功能
- 包含重试机制和Token失效处理

#### CaptchaUtils.py
- 验证码识别工具
- 实现滑块拼图验证码和点选文字验证码的自动识别

#### CryptoUtils.py
- 加解密工具
- 实现AES加密解密和签名算法
- 用于处理工学云API的加密需求

#### HelperFunctions.py
- 提供辅助功能函数
- 包括工作日判断、姓名脱敏、手机号脱敏、获取当前月份信息等

## 核心功能实现

### 1. 多用户打卡机制

[main.py](file:///d%3A/disk/auto/main.py) 实现了多用户遍历打卡：

- 读取 `user/config.json` 中的所有用户配置
- 依次为每个用户独立执行登录 → 获取计划 → 打卡 → 邮件通知
- 支持 `single`（单次）、`twice_daily`（一天两次）、`everyday`（每天）三种打卡模式
- 打乱用户顺序，随机延时执行，避免同时请求

### 2. 验证码处理

项目实现了对工学云平台验证码的自动处理：

- **滑块拼图验证码**（登录时）：通过 ONNX 模型 + OpenCV 图像识别定位滑块位置
- **点选文字验证码**（打卡时触发）：通过 ONNX OCR 模型识别图片中的文字，返回坐标并模拟点击

### 3. 安全验证绕过（msg=304）

打卡接口返回 `msg=304`（支付宝安全验证）时，`_handle_verification` 方法自动处理，无需人工干预。

**处理流程：**

```
打卡请求 → 返回 msg=304
    ↓
调用 solve_click_word_captcha() 获取点选验证码
    ↓
拿到 captcha（加密后的验证结果）和 clientUid（客户端标识）
    ↓
将 clientUid 映射 填入请求体
    ↓
携带数据 重新请求打卡接口
    ↓
返回打卡结果
```

**关键字段映射：**

| 验证码接口返回 | 打卡请求体字段 |
|----------------|----------------|
| `clientUid` | `appUuid` |
| `captcha`（加密结果） | `captcha` |

**代码位置：**
- [ApiService._handle_verification](file:///d%3A/disk/auto/util/ApiService.py#L504-L512) — 核心处理逻辑
- [ApiService.submit_clock_in](file:///d%3A/disk/auto/util/ApiService.py#L494-L495) — 触发入口（`elif responses.get("msg") == "304"`）

### 4. 加密机制

- AES-ECB-PKCS5Padding 加密（默认密钥 `23DbtQHR2UMbH6mJ`）
- MD5 签名（拼接关键字段 + 盐值 `3478cbbc33f84bd00d75d7dfa69e0daa`）

### 5. 防检测机制

- 随机打卡时间（在配置时间基础上 ± 浮动分钟数）
- 模拟真实用户设备信息
- 智能处理验证码
- 多用户随机延时执行

### 6. 数据脱敏

日志和文件中自动脱敏敏感信息：

| 类型 | 规则 | 示例 |
|------|------|------|
| 手机号 | 保留前3位和后4位 | `138****8000` |
| 姓名 | 保留首尾字 | `孙*周` |
| 地址 | 保留省市 | `四川省 · 成都市 · ***` |

## 运行流程

1. 读取 `user/config.json` 中的所有用户
2. 依次为每个用户执行：
   - 登录（检查本地 token 是否有效，无效则重新登录）
   - 获取实习计划信息
   - 根据打卡模式确定打卡类型
   - 提交打卡（自动处理验证码/安全验证）
   - 发送邮件通知（如已配置）
3. 汇总所有用户执行结果
4. 日志输出到 `main.log`
5. 记录操作日志

## 安全性考虑

- 用户密码使用 AES 加密传输
- 请求参数加密处理，签名防篡改
- 自动处理滑块/点选验证码
- 本地存储的 `userInfo.json` 中手机号自动脱敏（`138****8000`）
- 日志输出中手机号、姓名、地址自动脱敏

## 扩展性

- 模块化设计，易于扩展功能
- 配置化管理，灵活调整参数
- 支持多用户独立配置
- 日志记录完整，便于调试
- 支持本地运行和 GitHub Actions 两种部署方式