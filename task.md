我想要单独生成一个文件 用作工作流部署 名字叫auto.py
D:\disk\new\main.py 已经实现了一天签到上班卡和下班卡

我们需要一个自动部署的脚本 部署在action上
下面是一个名为 `auto.py` 的脚本示例，用于在 GitHub Actions 上自动执行签到任务。这个脚本将参考 `main.py` 来完成上班卡和下班卡的签到操作。

实现定时打卡
早上7点和下午5点执行上班和下班卡
还有手动执行的功能 main.py现在实现的就是手动运行的理想效果
运行就执行签到，判断改打上班卡还是下班卡即可。
你还需要满足多用户配置
在action的secret 上我会添加一个变量，这个变量是user，格式是json格式的，里面包含用户信息，包括手机号和密码 smtp...。
单用户模板：
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
      "customDays": [
        1,
        2,
        3,
        4,
        5
      ],
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
      "from": "gongxueyun",
      "to": [
        "2154335573@qq.com"      
      ]
    },
    "device": "{brand: iOOZ9 Turbo, systemVersion: 15, Platform: Android, isPhysicalDevice: true, incremental: V2352A}"
  }
}

多用户模板：
[
  {
    "config": {
      "user": {
        "phone": "工学云手机号",
        "password": "工学云密码"
      },
      "clockIn": {
        "mode": "daily",
        "location": {
          "address": "四川省 · 成都市 · 高新区 · 在科创十一街附近",
          "latitude": "30.559922",
          "longitude": "104.093023",
          "province": "四川省",
          "city": "成都市",
          "area": "高新区"
        },
        "imageCount": 0,
        "description": [
          "今天天气不错",
          "今天天气很好",
          "今天天气不太好"
        ],
        "specialClockIn": false,
        "customDays": [
          1,
          3,
          5
        ]
      },
      "reportSettings": {
        "daily": {
          "enabled": false,
          "imageCount": 0
        },
        "weekly": {
          "enabled": true,
          "imageCount": 0,
          "submitTime": 4
        },
        "monthly": {
          "enabled": false,
          "imageCount": 0,
          "submitTime": 29
        }
      },
      "ai": {
        "model": "gpt-4o-mini",
        "apikey": "sk-osdhgosdipghpsdgjiosfvinoips",
        "apiUrl": "https://api.openai.com/"
      },
      "pushNotifications": [
        {
          "type": "Server",
          "enabled": true,
          "sendKey": "your_key"
        },
        {
          "type": "PushPlus",
          "enabled": true,
          "token": "your_token"
        },
        {
          "type": "AnPush",
          "enabled": true,
          "token": "your_token",
          "channel": "通道ID,多个用英文逗号隔开",
          "to": "根据官方文档获取"
        },
        {
          "type": "WxPusher",
          "enabled": true,
          "spt": "your_spt"
        },
        {
          "type": "SMTP",
          "enabled": true,
          "host": "smtp服务地址",
          "port": 465,
          "username": "发件人邮箱",
          "password": "smtp密码",
          "from": "发件人名称",
          "to": "收件人邮箱"
        }
      ],
      "device": "{brand: TA J20, systemVersion: 17, Platform: Android, isPhysicalDevice: true, incremental: K23V10A}"
    }
  },
  {
    "config": {
      "user": {
        "phone": "工学云手机号",
        "password": "工学云密码"
      },
      "clockIn": {
        "mode": "daily",
        "location": {
          "address": "四川省 · 成都市 · 高新区 · 在科创十一街附近",
          "latitude": "30.559922",
          "longitude": "104.093023",
          "province": "四川省",
          "city": "成都市",
          "area": "高新区"
        },
        "imageCount": 0,
        "description": [
          "今天天气不错",
          "今天天气很好",
          "今天天气不太好"
        ],
        "specialClockIn": false,
        "customDays": [
          1,
          3,
          5
        ]
      },
      "reportSettings": {
        "daily": {
          "enabled": false,
          "imageCount": 0
        },
        "weekly": {
          "enabled": true,
          "imageCount": 0,
          "submitTime": 4
        },
        "monthly": {
          "enabled": false,
          "imageCount": 0,
          "submitTime": 29
        }
      },
      "ai": {
        "model": "gpt-4o-mini",
        "apikey": "sk-osdhgosdipghpsdgjiosfvinoips",
        "apiUrl": "https://api.openai.com/"
      },
      "pushNotifications": [
        {
          "type": "Server",
          "enabled": true,
          "sendKey": "your_key"
        },
        {
          "type": "PushPlus",
          "enabled": true,
          "token": "your_token"
        },
        {
          "type": "AnPush",
          "enabled": true,
          "token": "your_token",
          "channel": "通道ID,多个用英文逗号隔开",
          "to": "根据官方文档获取"
        },
        {
          "type": "WxPusher",
          "enabled": true,
          "spt": "your_spt"
        },
        {
          "type": "SMTP",
          "enabled": true,
          "host": "smtp服务地址",
          "port": 465,
          "username": "发件人邮箱",
          "password": "smtp密码",
          "from": "发件人名称",
          "to": "收件人邮箱"
        }
      ],
      "device": "{brand: TA J20, systemVersion: 17, Platform: Android, isPhysicalDevice: true, incremental: K23V10A}"
    }
  }
]
任务实现进度：
✅ 已完成：
1. 创建了auto.py文件，实现了多用户配置的自动签到脚本
   - 支持从环境变量或配置文件加载用户配置
   - 为每个用户创建独立的临时配置目录
   - 执行登录-获取计划-打卡-发送邮件的完整流程
   - 支持手动/定时（上班/下班）打卡模式

2. 创建了GitHub Actions工作流文件(.github/workflows/auto-checkin.yml)
   - 支持手动触发（manual/morning/evening模式）
   - 设置定时任务（UTC 23点/9点对应北京时间7点/17点）
   - 使用ubuntu-latest环境，Python 3.10
   - 从secrets获取USERS环境变量

3. 更新了auto.yaml示例配置文件
   - 包含用户信息（手机号、密码）
   - 打卡设置（twice_daily模式、地理位置、时间参数）
   - SMTP邮件配置
   - 设备信息

4. 更新了requirements.txt，添加了PyYAML>=6.0依赖

5. 创建了README_GITHUB.md文档
   - GitHub Actions部署专用说明
   - 包含功能特点、部署步骤、工作流程等
   - 配置说明和故障排除指南

🔄 下一步：
1. 测试auto.py脚本在本地环境中的运行情况
2. 验证GitHub Actions工作流是否正常执行
3. 根据测试结果进行必要的调整和优化