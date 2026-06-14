# 工学云自动打卡系统实现原理

## 项目概述

工学云自动打卡系统是一个基于Python的自动化工具，用于自动完成工学云平台的每日打卡任务。该项目通过模拟真实用户操作，实现自动登录、获取计划信息、执行打卡以及发送邮件通知等功能。

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
│   ├── planInfo.json  # 计划信息文件
│   └── userInfo.json  # 用户信息文件
├── util/              # 工具模块
│   ├── ApiService.py      # API服务接口
│   ├── CaptchaUtils.py    # 验证码处理
│   ├── CryptoUtils.py     # 加密解密工具
│   └── HelperFunctions.py # 辅助函数
├── config.json        # 系统配置文件
├── gong_xue_yun.py    # 主程序入口（带定时功能）
├── main.py           # 主执行流程
└── README.md
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
- 包括工作日判断、姓名脱敏、获取当前月份信息等

## 核心功能实现

### 1. 定时打卡机制

[gong_xue_yun.py](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/gong_xue_yun.py) 文件实现了定时打卡功能：

- 支持三种打卡模式：[weekday](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/util/HelperFunctions.py#L147-L147)（法定工作日）、[everyday](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/util/HelperFunctions.py#L150-L150)（每天）、[customize](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/util/HelperFunctions.py#L153-L153)（自定义）
- 使用 [schedule](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/main.py#L9-L9) 库进行任务调度
- 每天生成随机打卡时间（在配置时间基础上增加随机分钟数）

### 2. 验证码处理

项目实现了对工学云平台验证码的自动处理：

- 滑块拼图验证码：通过图像识别技术定位滑块位置
- 点选文字验证码：识别图片中的文字并返回坐标

### 3. 加密机制

项目使用了复杂的加密机制来模拟真实用户请求：

- AES加密用于处理密码、请求参数等
- 签名算法确保请求的合法性

### 4. 防检测机制

- 随机打卡时间，避免在固定时间点打卡
- 模拟真实用户设备信息
- 智能处理验证码，确保请求的合法性

## 配置说明

[config.json](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/config.json) 文件包含以下配置项：

1. **用户信息**：手机号和密码
2. **打卡设置**：
   - 打卡模式（工作日/每天/自定义）
   - 打卡位置信息（经纬度、地址等）
   - 打卡时间设置
3. **邮件通知**：SMTP服务器配置
4. **设备信息**：模拟设备信息

## 运行流程

1. 检查是否需要在当天执行任务
2. 生成随机打卡时间
3. 执行 [main.py](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/main.py) 中的 [execute_tasks()](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/main.py#L27-L48) 函数
4. 依次执行登录、获取计划、打卡、发送邮件等步骤
5. 记录操作日志

## 安全性考虑

- 用户密码使用AES加密存储
- 请求参数加密处理
- 自动处理各种验证机制
- 本地存储敏感信息，避免泄露

## 扩展性

- 模块化设计，易于扩展功能
- 配置化管理，灵活调整参数
- 日志记录完整，便于调试

