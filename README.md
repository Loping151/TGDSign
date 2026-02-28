# TGDSign - 塔吉多签到插件

基于 gsuid_core 的塔吉多(Taygedo)APP签到插件，支持APP签到和游戏签到。

## 功能

- 短信验证码网页登录塔吉多账号
- 多角色绑定，登录时自动获取所有游戏角色
- 手动签到（APP签到 + 每个角色游戏签到）
- 定时自动签到
- 订阅签到结果推送（私聊/群聊）
- 全部签到（管理员为所有用户签到）
- Web 管理面板（绑定管理、用户管理）

## 指令

指令前缀: `tgd` / `yh` / `ht`

| 指令 | 权限 | 说明 |
|------|------|------|
| `{prefix}登录` | 玩家 | 网页短信登录，自动绑定所有角色 |
| `{prefix}签到` | 玩家 | 手动执行APP签到+游戏签到 |
| `{prefix}开启自动签到` | 玩家 | 开启每日自动签到 |
| `{prefix}关闭自动签到` | 玩家 | 关闭每日自动签到 |
| `{prefix}订阅签到结果` | 玩家 | 订阅自动签到结果推送 |
| `{prefix}取消订阅签到结果` | 玩家 | 取消订阅签到结果 |
| `{prefix}全部签到` | 主人 | 为所有用户签到 |
| `{prefix}帮助` | 玩家 | 显示帮助信息 |

## 安装依赖

在 gsuid_core 项目根目录下执行:

```bash
cd <你的gsuid_core目录>
uv pip install pycryptodome
```

- gsuid_core
- httpx
- pycryptodome (AES加密)

## Credits

本插件参考了以下项目的实现:

- [RoverSign](https://github.com/) - gsuid_core 插件架构、数据库模型、签到调度、全部签到等实现模式
- [nonebot-plugin-taygedo-helper](https://github.com/BraveCowardp/nonebot-plugin-taygedo-helper) - 塔吉多API接口、登录流程、签名加密算法、数据标准
