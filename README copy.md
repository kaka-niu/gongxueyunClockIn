# 工学云 (GongXueYun) 自动化脚本

基于 Python 的工学云实习平台自动化工具，支持自动登录、签到/签退、日报/周报/月报/实习总结提交。

## 目录

- [功能概览](#功能概览)
- [公共机制](#公共机制)
- [API 接口详解](#api-接口详解)
  - [1. 登录](#1-登录)
  - [2. 获取实习计划列表](#2-获取实习计划列表)
  - [3. 获取岗位信息](#3-获取岗位信息)
  - [4. 打卡（签到/签退）](#4-打卡签到签退)
  - [5. 查询打卡记录](#5-查询打卡记录)
  - [6. 获取点选验证码](#6-获取点选验证码)
  - [7. 校验点选验证码](#7-校验点选验证码)
  - [8. 查询是否已提交报告](#8-查询是否已提交报告)
  - [9. 提交日报/月报/总结](#9-提交日报月报总结)
  - [10. 获取当前周报周期](#10-获取当前周报周期)
  - [11. 获取周报问卷](#11-获取周报问卷)
  - [12. 提交周报](#12-提交周报)
  - [13. 获取图片上传 Token](#13-获取图片上传-token)
- [验证码识别流程](#验证码识别流程)
- [使用示例](#使用示例)
- [依赖项](#依赖项)
- [注意事项](#注意事项)

---

## 功能概览

| 功能 | 说明 |
|------|------|
| 自动登录 | 手机号 + 密码登录，AES-ECB 加密通信 |
| 自动打卡 | 支持上班签到 (START) 和下班签退 (END) |
| AI 验证码识别 | YOLOv5n 目标检测 + OCR 文字识别，自动通过点选验证码 |
| 日报提交 | AI 自动生成工作日报 |
| 周报提交 | AI 自动生成工作周报 |
| 月报提交 | AI 自动生成工作月报 |
| 实习总结 | AI 自动生成实习总结 |
| 打卡图片上传 | 支持上传打卡现场照片（七牛云存储） |
| GPS 定位 | 通过腾讯地图 API 获取打卡地点经纬度 |

---

## 公共机制

### 基础地址

```
https://api.moguding.net:9000
```

### 加密方式

所有请求使用 **AES-ECB (PKCS7 padding)** 加密，固定密钥：

```
AES_KEY = "23DbtQHR2UMbH6mJ"
```

### 公共请求头

```json
{
  "user-agent": "<随机移动端 UA>",
  "host": "api.moguding.net:9000",
  "content-type": "application/json; charset=utf-8",
  "version": "5.30.6",
  "X-Re-Os": "android",
  "X-Re-Version": "5.30.6"
}
```

> 版本号可通过环境变量 `GX_APP_VERSION` 覆盖，默认 `5.30.6`。

### 登录后追加的请求头

```json
{
  "userid": "<用户ID>",
  "rolekey": "<角色: student>",
  "authorization": "<JWT Token>"
}
```

### 时间戳参数 `t`

大部分接口需要携带 `t` 参数，值为当前毫秒时间戳的 AES-ECB 加密（hex 输出）：

```python
t = aes_ecb_encrypt(str(int(time.time() * 1000)))
```

### 签名算法 `sign`

部分接口需要 `sign` 签名，算法为 MD5：

```
sign = MD5( userId + roleKey + 业务参数... + "3478cbbc33f84bd00d75d7dfa69e0daa" )
```

不同接口的拼接规则见各接口说明。

---

## API 接口详解

---

### 1. 登录

模拟 Android App 登录，获取 Token 和用户信息。

| 项目 | 值 |
|------|-----|
| **URL** | `POST /session/user/v6/login` |
| **需要认证** | 否 |

#### 请求头

```json
{
  "user-agent": "<随机移动端 UA>",
  "content-type": "application/json; charset=utf-8",
  "host": "api.moguding.net:9000",
  "version": "5.30.6",
  "X-Re-Os": "android",
  "X-Re-Version": "5.30.6"
}
```

#### 请求体

```json
{
  "phone": "<AES-ECB加密的手机号, hex>",
  "password": "<AES-ECB加密的密码, hex>",
  "captcha": "<图形验证码识别结果>",
  "loginType": "android",
  "uuid": "<MD5(当前时间戳)>",
  "device": "android",
  "version": "5.30.6",
  "t": "<AES-ECB加密的毫秒时间戳, hex>"
}
```

> **注意**：`captcha` 字段来自外部 `Capcha` 模块的图形验证码识别结果。登录前需要先获取图形验证码并识别（由 `captcha.py` 模块处理，非本文件逻辑）。

#### 响应

成功时 `code=200`，`data` 字段是 AES-ECB 加密的 JSON 字符串，解密后得到：

```json
{
  "token": "eyJhbGciOiJIUzUxMiJ9...",
  "userId": "106156679",
  "roleKey": "student",
  "orgJson": {
    "snowFlakeId": "...",
    "name": "张三",
    "schoolName": "某某大学",
    "...": "..."
  }
}
```

#### 调用的代码位置

[gongxueyun.py - login()](file:///d:/disk/gkd/gongxueyun.py#L524-L606)

---

### 2. 获取实习计划列表

获取当前用户的所有实习计划。

| 项目 | 值 |
|------|-----|
| **URL** | `POST /practice/plan/v3/getPlanByStu` |
| **需要认证** | 是 |

#### 请求头

```json
{
  "user-agent": "<随机移动端 UA>",
  "userid": "<用户ID>",
  "rolekey": "student",
  "host": "api.moguding.net:9000",
  "authorization": "<JWT Token>",
  "content-type": "application/json; charset=utf-8",
  "sign": "<MD5签名>"
}
```

#### 签名规则

```
sign = MD5( userId + roleKey + "3478cbbc33f84bd00d75d7dfa69e0daa" )
```

#### 请求体

```json
{
  "pageSize": 999999,
  "t": "<AES-ECB加密的毫秒时间戳, hex>"
}
```

#### 响应

```json
{
  "code": 200,
  "data": [
    {
      "planId": "123456",
      "planName": "2024年实习计划"
    }
  ]
}
```

#### 调用的代码位置

[gongxueyun.py - get_plan_id()](file:///d:/disk/gkd/gongxueyun.py#L396-L428)

---

### 3. 获取岗位信息

获取指定实习计划下的岗位详情（公司名称、地址、岗位名称等）。

| 项目 | 值 |
|------|-----|
| **URL** | `POST /practice/personPractice/v1/getPracticeInfo` |
| **需要认证** | 是 |

#### 请求头

```json
{
  "user-agent": "<随机移动端 UA>",
  "userid": "<用户ID>",
  "rolekey": "student",
  "host": "api.moguding.net:9000",
  "authorization": "<JWT Token>",
  "content-type": "application/json; charset=utf-8"
}
```

#### 请求体

```json
{
  "t": "<AES-ECB加密的毫秒时间戳, hex>",
  "planId": "<实习计划ID>",
  "currPage": 1,
  "pageSize": 25
}
```

#### 响应

```json
{
  "code": 200,
  "data": [
    {
      "companyName": "某某科技有限公司",
      "address": "广东省深圳市南山区科技园",
      "jobName": "Java开发实习生",
      "startTime": "2024-01-01",
      "endTime": "2024-06-30",
      "jobStartTime": "09:00",
      "jobEndTime": "18:00",
      "jobId": "job_xxx",
      "jobContent": "参与后端开发..."
    }
  ]
}
```

#### 调用的代码位置

[gongxueyun.py - get_job_info()](file:///d:/disk/gkd/gongxueyun.py#L430-L478)

---

### 4. 打卡（签到/签退）

核心打卡接口，包含完整的签到/签退逻辑。

| 项目 | 值 |
|------|-----|
| **URL** | `POST /attendence/clock/v6/save` |
| **需要认证** | 是 |

#### 请求头

```json
{
  "user-agent": "<随机移动端 UA>",
  "userid": "<用户ID>",
  "rolekey": "student",
  "host": "api.moguding.net:9000",
  "authorization": "<JWT Token>",
  "content-type": "application/json; charset=utf-8",
  "version": "5.30.6",
  "X-Re-Os": "android",
  "X-Re-Version": "5.30.6",
  "X-Re-Device": "{brand: vivo V1824A, systemVersion: 9, Platform: Android, ...}",
  "sign": "<打卡签名>"
}
```

#### 签名规则

```
sign = MD5( device + state + planId + userId + address + "3478cbbc33f84bd00d75d7dfa69e0daa" )
```

其中：
- `device` — 设备信息字符串
- `state` — `"START"`（上班）或 `"END"`（下班）
- `planId` — 实习计划ID
- `userId` — 用户ID
- `address` — 完整地址字符串

#### 请求体

```json
{
  "distance": null,
  "address": "广东省 · 深圳市 · 南山区 科技园某某路",
  "content": null,
  "lastAddress": null,
  "lastDetailAddress": "广东省 · 深圳市 · 南山区 科技园某某路",
  "attendanceId": null,
  "city": "深圳市",
  "area": "南山区",
  "country": "中国",
  "createBy": null,
  "createTime": "2024-01-15 09:00:00",
  "description": null,
  "device": "{brand: vivo V1824A, ...}",
  "images": null,
  "isDeleted": null,
  "isReplace": null,
  "latitude": 22.5431,
  "longitude": 113.9544,
  "modifiedBy": null,
  "modifiedTime": null,
  "province": "广东省",
  "schoolId": null,
  "state": "NORMAL",
  "teacherId": null,
  "teacherNumber": null,
  "type": "START",
  "stuId": null,
  "planId": "<实习计划ID>",
  "version": "5.30.6",
  "attendanceType": null,
  "username": null,
  "attachments": null,
  "userId": "<用户ID>",
  "isSYN": null,
  "studentId": null,
  "applyState": null,
  "studentNumber": null,
  "memberNumber": null,
  "headImg": null,
  "attendenceTime": null,
  "depName": null,
  "majorName": null,
  "className": null,
  "logDtoList": null,
  "isBeyondFence": null,
  "practiceAddress": null,
  "tpJobId": null,
  "t": "<AES-ECB加密的毫秒时间戳, hex>"
}
```

> **关键字段说明**：
> - `type`: `"START"` 上班签到 / `"END"` 下班签退
> - `latitude` / `longitude`: 由腾讯地图 API 根据公司地址反查得到
> - `attachments`: 如果传了打卡图片，会先上传到七牛云，此处填图片 key
> - `appUuid` / `captcha`: 触发安全验证时追加的字段

#### 安全验证码处理

如果接口返回 `data` 中包含"安全验证"字样，需要走点选验证码流程（见接口 6、7），将结果追加到请求体重新提交：

```json
{
  "appUuid": "<验证码 clientUid>",
  "captcha": "<AES加密的验证码结果>"
}
```

#### 响应

```json
{
  "code": 200,
  "msg": "success"
}
```

#### 调用的代码位置

[gongxueyun.py - clock()](file:///d:/disk/gkd/gongxueyun.py#L665-L830)

---

### 5. 查询打卡记录

查询当前用户的打卡记录列表。

| 项目 | 值 |
|------|-----|
| **URL** | `POST /attendence/clock/v1/listSynchro` |
| **需要认证** | 是 |

#### 请求头

```json
{
  "accept-encoding": "gzip",
  "content-type": "application/json;charset=UTF-8",
  "rolekey": "student",
  "host": "api.moguding.net:9000",
  "authorization": "<JWT Token>",
  "user-agent": "<随机移动端 UA>"
}
```

#### 请求体

```json
{
  "t": "<AES-ECB加密的毫秒时间戳, hex>"
}
```

#### 调用的代码位置

[gongxueyun.py - check_clock()](file:///d:/disk/gkd/gongxueyun.py#L480-L494)

---

### 6. 获取点选验证码

打卡时触发安全验证后，获取点选验证码图片和文字列表。

| 项目 | 值 |
|------|-----|
| **URL** | `POST /attendence/clock/v1/get` |
| **需要认证** | 是 |

#### 请求头

使用已登录的 `HEADERS`（含 userid、rolekey、authorization）。

#### 请求体

```json
{
  "clientUid": "<UUID去横线>",
  "captchaType": "clickWord"
}
```

#### 响应

```json
{
  "code": 200,
  "data": {
    "originalImageBase64": "<验证码图片 base64>",
    "wordList": ["字", "符", "列", "表"],
    "token": "<验证码 token>",
    "secretKey": "<本次验证码的临时密钥>"
  }
}
```

#### 调用的代码位置

[gongxueyun.py - solve_click_word_captcha()](file:///d:/disk/gkd/gongxueyun.py#L215-L251)

---

### 7. 校验点选验证码

将 AI 识别出的点击坐标提交给服务端验证。

| 项目 | 值 |
|------|-----|
| **URL** | `POST /attendence/clock/v1/check` |
| **需要认证** | 是 |

#### 请求头

使用已登录的 `HEADERS`。

#### 请求体

```json
{
  "pointJson": "<AES-ECB加密的坐标JSON, base64输出, 使用secretKey加密>",
  "token": "<上一步返回的 token>",
  "captchaType": "clickWord"
}
```

> **`pointJson` 加密前的内容**是 AI 识别结果坐标的 JSON 字符串：
> ```json
> [{"x": 120, "y": 85}, {"x": 200, "y": 150}]
> ```
> 使用 `secretKey` 进行 AES-ECB 加密，base64 输出。

#### 响应

```json
{
  "code": 200,
  "msg": "success"
}
```

#### 验证成功后用于打卡的 `captcha` 字段

```python
captcha = aes_ecb_encrypt_v2(
    token + "---" + captcha_solution,
    secretKey
)
```

#### 调用的代码位置

[gongxueyun.py - solve_click_word_captcha()](file:///d:/disk/gkd/gongxueyun.py#L259-L275)

---

### 8. 查询是否已提交报告

在提交日报/周报/月报前，先查询当天/当周/当月是否已经提交过，避免重复。

| 项目 | 值 |
|------|-----|
| **URL** | `POST /practice/paper/v2/listByStu` |
| **需要认证** | 是 |

#### 签名规则

```
sign = MD5( userId + roleKey + reportType + "3478cbbc33f84bd00d75d7dfa69e0daa" )
```

#### 请求体

```json
{
  "reportType": "day",
  "currPage": 1,
  "t": "<AES-ECB加密的毫秒时间戳, hex>",
  "pageSize": 99999,
  "planId": "<实习计划ID>"
}
```

> `reportType` 可选值：`"day"`（日报）、`"week"`（周报）、`"month"`（月报）

#### 响应

```json
{
  "msg": "success",
  "data": [
    {
      "reportId": "xxx",
      "reportTime": "2024-01-15 18:00:00",
      "startTime": "2024-01-15 00:00:00",
      "endTime": "2024-01-21 23:59:59",
      "yearmonth": "2024-01"
    }
  ]
}
```

#### 判断逻辑

| 报告类型 | 判断条件 |
|---------|---------|
| `day` | `data` 中是否存在 `reportTime` 为当天的记录 |
| `week` | `data` 中是否存在 `startTime ≤ 今天 ≤ endTime` 的记录 |
| `month` | `data` 中是否存在 `yearmonth` 为当月的记录 |

#### 调用的代码位置

[gongxueyun.py - is_need_report()](file:///d:/disk/gkd/gongxueyun.py#L930-L975)

---

### 9. 提交日报/月报/总结

日报、月报、实习总结共用同一个接口，通过 `reportType` 区分。

| 项目 | 值 |
|------|-----|
| **URL** | `POST /practice/paper/v5/save` |
| **需要认证** | 是 |

#### 签名规则

```
# 日报
sign = MD5( userId + "day" + planId + title + "3478cbbc33f84bd00d75d7dfa69e0daa" )

# 月报
sign = MD5( userId + "month" + planId + title + "3478cbbc33f84bd00d75d7dfa69e0daa" )

# 总结
sign = MD5( userId + "summary" + planId + title + "3478cbbc33f84bd00d75d7dfa69e0daa" )
```

#### 请求体

```json
{
  "address": null,
  "applyId": null,
  "applyName": null,
  "attachmentList": null,
  "commentNum": null,
  "commentContent": null,
  "content": "<AI生成的报告内容, 长文本>",
  "createBy": null,
  "createTime": null,
  "depName": null,
  "reject": null,
  "endTime": null,
  "headImg": null,
  "yearmonth": null,
  "imageList": null,
  "isFine": null,
  "latitude": null,
  "gpmsSchoolYear": null,
  "longitude": null,
  "planId": "<实习计划ID>",
  "planName": null,
  "reportId": null,
  "reportType": "day",
  "reportTime": "2024-01-15 18:00:00",
  "isOnTime": null,
  "schoolId": null,
  "startTime": null,
  "state": null,
  "studentId": null,
  "studentNumber": null,
  "supportNum": null,
  "title": "今日工作内容",
  "url": null,
  "username": null,
  "weeks": null,
  "videoUrl": null,
  "videoTitle": null,
  "attachments": "",
  "companyName": null,
  "jobName": null,
  "jobId": "<岗位ID>",
  "score": null,
  "tpJobId": null,
  "starNum": null,
  "confirmDays": null,
  "isApply": null,
  "apply": null,
  "levelEntity": null,
  "t": "<AES-ECB加密的毫秒时间戳, hex>"
}
```

> **关键字段说明**：
> - `reportType`: `"day"` 日报 / `"month"` 月报 / `"summary"` 实习总结
> - `content`: 由 `mino.get_ai_response()` 根据公司名、岗位内容自动生成
> - `title`: 日报默认 `"今日工作内容"`，月报默认 `"本月工作内容"`，总结默认 `"实习总结"`
> - `yearmonth`: 仅月报需要，格式 `"2024-01"`
> - `reportTime`: 仅日报需要，格式 `"2024-01-15 18:00:00"`

#### AI 内容生成参数

| 报告类型 | 目标字数 |
|---------|---------|
| 日报 | 200 字 |
| 月报 | 1500 字 |
| 总结 | 600 字 |

#### 响应

```json
{
  "code": 200,
  "msg": "success"
}
```

#### 调用的代码位置

- 日报: [gongxueyun.py - handle_send_daily()](file:///d:/disk/gkd/gongxueyun.py#L862-L928)
- 月报: [gongxueyun.py - handle_send_monthly()](file:///d:/disk/gkd/gongxueyun.py#L1080-L1142)
- 总结: [gongxueyun.py - handle_send_summary()](file:///d:/disk/gkd/gongxueyun.py#L1144-L1206)

---

### 10. 获取当前周报周期

获取当前时间所在的周报周期（第几周、起止时间）。

| 项目 | 值 |
|------|-----|
| **URL** | `POST /practice/paper/v3/getWeeks1` |
| **需要认证** | 是 |

#### 请求体

```json
{
  "t": "<AES-ECB加密的毫秒时间戳, hex>"
}
```

#### 响应

```json
{
  "code": 200,
  "data": [
    {
      "isDefault": 1,
      "weeks": "第1周",
      "startTime": "2024-08-19 00:00:00",
      "endTime": "2024-08-25 23:59:59"
    }
  ]
}
```

> 代码会遍历返回的数组，找到 `startTime ≤ 当前时间 ≤ endTime` 的那一项。

#### 调用的代码位置

[gongxueyun.py - get_weeks()](file:///d:/disk/gkd/gongxueyun.py#L977-L1000)

---

### 11. 获取周报问卷

获取周报的问卷表单字段（填空题、选择题等）。

| 项目 | 值 |
|------|-----|
| **URL** | `POST /practice/paper/v2/info` |
| **需要认证** | 是 |

#### 请求体

```json
{
  "t": "<AES-ECB加密的毫秒时间戳, hex>",
  "reportId": "",
  "formType": 8,
  "isUpdate": 1
}
```

#### 响应

```json
{
  "code": 200,
  "data": {
    "formFieldDtoList": [
      {
        "fieldClass": "...",
        "fieldId": "...",
        "fromName": "问卷题目",
        "isMust": 1,
        "moduleId": "...",
        "moduleType": "...",
        "optionEntity": [...],
        "title": "题目文字",
        "warningPrompt": "...",
        "warningSetValue": "..."
      }
    ]
  }
}
```

> 代码会自动为每个选项随机选择 `"a"` 或 `"b"` 作为答案。

#### 调用的代码位置

[gongxueyun.py - get_week_question()](file:///d:/disk/gkd/gongxueyun.py#L1002-L1019)

---

### 12. 提交周报

周报使用独立的接口（v6），需要携带问卷答案和周期信息。

| 项目 | 值 |
|------|-----|
| **URL** | `POST /practice/paper/v6/save` |
| **需要认证** | 是 |

#### 签名规则

```
sign = MD5( userId + "week" + planId + title + "3478cbbc33f84bd00d75d7dfa69e0daa" )
```

#### 请求体

```json
{
  "content": "<AI生成的周报内容, 约800字>",
  "endTime": "2024-08-25 23:59:59",
  "fieldEntityList": [
    {
      "fieldClass": "...",
      "fieldId": "...",
      "fromName": "问卷题目",
      "isMust": 1,
      "moduleId": "...",
      "moduleType": "...",
      "optionEntity": [...],
      "title": "题目文字",
      "value": "a",
      "warningPrompt": "...",
      "warningSetValue": "..."
    }
  ],
  "imageList": [],
  "planId": "<实习计划ID>",
  "reportType": "week",
  "startTime": "2024-08-19 00:00:00",
  "t": "<AES-ECB加密的毫秒时间戳, hex>",
  "title": "本周工作内容",
  "weeks": "第1周"
}
```

> **关键字段说明**：
> - `fieldEntityList`: 从接口 11 获取的问卷字段，`value` 随机选择 `"a"` 或 `"b"`
> - `startTime` / `endTime` / `weeks`: 从接口 10 获取的当前周期信息
> - `content`: AI 生成，目标 800 字

#### 响应

```json
{
  "code": 200,
  "msg": "success"
}
```

#### 调用的代码位置

[gongxueyun.py - handle_send_weekly()](file:///d:/disk/gkd/gongxueyun.py#L1021-L1078)

---

### 13. 获取图片上传 Token

获取七牛云的上传 Token，用于打卡时上传现场照片。

| 项目 | 值 |
|------|-----|
| **URL** | `POST /session/upload/v1/token` |
| **需要认证** | 是 |

#### 请求体

```json
{
  "t": "<AES-ECB加密的毫秒时间戳, hex>"
}
```

#### 响应

```json
{
  "code": 200,
  "data": "<七牛云 upload token 字符串>"
}
```

#### 上传逻辑

获取 token 后，使用七牛 SDK 上传图片：

```python
key = f"{snowFlakeId}/{日期}/sign/{userId}_{时间戳}.png"
put_file(up_token, 'upload/' + key, localfile)
```

上传成功后，`key` 作为打卡请求中 `attachments` 字段的值。

#### 图片来源支持

- 本地文件路径
- HTTP/HTTPS URL（自动下载到临时文件）
- 字符串列表（随机选择一张）

#### 调用的代码位置

[gongxueyun.py - get_upload_image_key()](file:///d:/disk/gkd/gongxueyun.py#L627-L663)

---

## 验证码识别流程

```
打卡请求 → 返回"安全验证"
    │
    ▼
① POST /attendence/clock/v1/get
   获取验证码图片 (base64) + 目标文字列表 (wordList)
    │
    ▼
② YOLOv5n 目标检测 → 找到图片中所有文字区域坐标
    │
    ▼
③ OCR 文字识别 → 识别每个区域中的文字
    │
    ▼
④ 匹配 wordList 中的文字，取对应坐标
    │
    ▼
⑤ POST /attendence/clock/v1/check
   提交加密后的坐标 JSON
    │
    ▼
⑥ 验证通过 → 获取 captcha 加密串
    │
    ▼
⑦ 携带 appUuid + captcha 重新提交打卡请求
```

> 最多重试 **15 次**，每次间隔 1~2 秒。

---

## 使用示例

### 1. 仅登录

```python
from gongxueyun import GongXueYun

gxy = GongXueYun(
    proxies=None,
    username="13800138000",
    password="your_password",
    func_name="login"
)
result = gxy.run()
print(result)
```

### 2. 上班签到

```python
gxy = GongXueYun(
    proxies=None,
    username="13800138000",
    password="your_password",
    func_name="clock",
    clock_action_type=1  # 1=上班签到
)
result = gxy.run()
print(result)
```

### 3. 下班签退 + 自动提交日报

```python
gxy = GongXueYun(
    proxies=None,
    username="13800138000",
    password="your_password",
    func_name="clock",
    clock_action_type=2,  # 2=下班签退
    send_daily=True
)
result = gxy.run()
print(result)
```

### 4. 单独提交周报

```python
gxy = GongXueYun(
    proxies=None,
    username="13800138000",
    password="your_password",
    func_name="do_send_weekly"
)
result = gxy.run()
print(result)
```

### 5. 打卡 + 上传图片

```python
gxy = GongXueYun(
    proxies=None,
    username="13800138000",
    password="your_password",
    func_name="clock",
    clock_action_type=1,
    image="https://example.com/photo.jpg"  # 或本地路径
)
result = gxy.run()
print(result)
```

---

## 依赖项

### Python 包

| 包名 | 用途 |
|------|------|
| `requests` | HTTP 请求 |
| `numpy` | 图像数据处理 |
| `opencv-python` (cv2) | 图像处理、目标检测 |
| `onnxruntime` | ONNX 模型推理 |
| `pycryptodome` | AES 加密/解密 |
| `fake_useragent` | 随机 User-Agent |
| `qiniu` | 七牛云存储 SDK（可选，仅图片上传需要） |

### 外部模块

| 模块 | 用途 |
|------|------|
| `api.query_key` | Redis 查询键值 |
| `captcha.Capcha` | 图形验证码识别 |
| `mino.get_ai_response` | AI 生成报告内容 |
| `qqmap.get_position_by_address` | 地址转 GPS 经纬度（腾讯地图） |

### AI 模型（自动下载）

| 模型文件 | 用途 | 下载地址 |
|----------|------|---------|
| `yolov5n.onnx` | YOLOv5 Nano 目标检测 | [GitHub Releases](https://github.com/maserpoassr/automoguding-saas/releases/download/v0.0.1/yolov5n.onnx) |
| `ocr.onnx` | 中文 OCR 文字识别 | [GitHub Releases](https://github.com/maserpoassr/automoguding-saas/releases/download/v0.0.1/ocr.onnx) |

---

## 注意事项

1. **版本兼容**: 客户端版本号 `APP_CLIENT_VERSION` 默认 `5.30.6`，需与官方 App 大版本一致。可通过环境变量 `GX_APP_VERSION` 覆盖。
2. **代理设置**: 支持 HTTP 代理，格式如 `{"http": "http://proxy:port", "https": "http://proxy:port"}`。
3. **验证码识别**: 依赖 AI 模型，首次运行会自动下载模型文件到 `models_onnx/` 目录。
4. **多实习计划**: 如果有多个实习计划，`login()` 会返回计划列表供选择，不会自动选择。
5. **外部依赖**: `api`、`captcha`、`mino`、`qqmap` 等模块为外部依赖，需确保这些模块在 Python 路径中可用。
6. **报告去重**: 日报/周报/月报提交前会自动检查是否已提交，避免重复。
7. **请求超时**: 默认 HTTP 超时 5 秒，打卡请求 15 秒，报告提交 10 秒。
8. **安全验证码**: 打卡时可能触发点选验证码，脚本会自动使用 AI 识别并重试（最多 15 次）。

## 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `GX_APP_VERSION` | `5.30.6` | 客户端版本号，用于模拟 App 请求头 |

## 许可证

本项目仅供学习交流使用，请勿用于非法用途。