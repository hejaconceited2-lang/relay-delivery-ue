# 用 AI Agent 制作交互式协作网页 · 零成本教程

> 这套方案可以做出：多人实时协作页面（认领、勾选、投票等），无需服务器，永久免费。
> 你只需要跟 AI Agent 对话，它会帮你完成所有代码和配置。

---

## 一、整体架构

```
你 → AI Agent 写代码 → GitHub Pages 托管页面 → Firebase 存数据
                              ↑                        ↑
                         免费 · 自动部署          免费 · 实时同步
```

任何人打开网页 → 页面从 Firebase 读取/写入数据 → 所有人看到的内容实时同步。

---

## 二、准备工作（只做一次，10 分钟）

### 2.1 创建 GitHub 仓库

1. 打开 https://github.com ，登录你的账号
2. 右上角 `+` → `New repository`
3. 仓库名随意（比如 `my-project`），选 **Public**，勾选「Add a README file」
4. 点 `Create repository`

### 2.2 开启 GitHub Pages

1. 进入仓库 → `Settings` → 左侧 `Pages`
2. `Source` 选 `Deploy from a branch`
3. `Branch` 选 `main`（或 `master`），文件夹选 `/ (root)`
4. 点 `Save`
5. 等 1 分钟后，页面地址是 `https://你的用户名.github.io/仓库名/`

### 2.3 创建 Firebase 项目

1. 打开 https://console.firebase.google.com/ ，用 Google 账号登录
2. 点「添加项目」→ 项目名随意（如 `my-project-db`）→ 继续 → 继续
3. 左侧菜单 → **Realtime Database** → 创建数据库
4. 地点选 `us-central1`，安全规则选「以测试模式启动」
5. 创建后，点击「规则」标签，把规则替换为（防止数据被随意覆盖）：

```json
{
  "rules": {
    ".read": true,
    "points": {
      ".write": "!data.exists()",
      "$pointId": {
        ".write": "!data.exists() || data.child('claimed').val() == false",
        "scouting": {
          ".write": true
        }
      }
    }
  }
```

6. 点「发布」

### 2.4 获取 Firebase 配置

1. Firebase 控制台 → 项目首页 → 点击 `</>` 图标（添加 Web 应用）
2. 应用名随意填 → 注册
3. 复制弹窗中的 `firebaseConfig` 整段代码（包含 apiKey、projectId 等）
4. 保存好，后面要给 AI Agent

---

## 三、把本地项目连上 GitHub

在电脑上创建一个文件夹，用 Git 连上 GitHub 仓库。如果你还没装 Git，先装 https://git-scm.com/ 。

```bash
# 克隆你的仓库到本地
git clone https://github.com/你的用户名/仓库名.git
cd 仓库名
```

之后所有 AI Agent 生成的文件都放在这个文件夹里。

---

## 四、跟 AI Agent 对话，制作页面

### 第一步：描述你的需求

给 AI Agent 这样的指令：

> 帮我做一个网页，列出以下点位（可修改）：
> - 点位A（区域X）
> - 点位B（区域Y）
> - 点位C（区域Z）
>
> 需求：
> 1. 打开页面的人可以点击点位，输入自己的名字认领
> 2. 已认领的点位别人不能再选
> 3. 数据实时同步，所有人看到的都一样
> 4. 使用 Firebase Realtime Database 做后端
>
> 这是我的 Firebase 配置：
> （粘贴你在 2.4 步骤复制的 firebaseConfig）
>
> 页面部署在 GitHub Pages 上。

AI Agent 会生成一个 Python 脚本和 HTML 文件。

### 第二步：AI Agent 帮你生成和部署

AI Agent 生成文件后，在终端运行它给的命令（通常是 `py scripts/xxx.py` 生成 HTML），然后 AI Agent 会帮你 commit 和 push 到 GitHub。

等 30 秒，页面就在线了：`https://你的用户名.github.io/仓库名/output/xxx.html`

### 第三步：迭代修改

每次要改内容，直接告诉 AI Agent，比如：

> 把点位A改成已由张三认领
> 增加一个踩点评估功能：外卖柜有无、物业是否严格……
> 把表格颜色换成蓝色系

AI Agent 改完代码 → 重新生成 → 推送，页面自动更新。

---

## 五、整个技术栈总结

| 层 | 用什么 | 费用 |
|----|--------|------|
| 页面托管 | GitHub Pages | 免费 |
| 实时数据库 | Firebase Realtime Database | 免费（1GB 存储，够用） |
| 域名 | `github.io` 子域名 | 免费 |
| 代码生成 | AI Agent（Claude Code 等） | 你的 AI 订阅 |
| 版本管理 | Git + GitHub | 免费 |

**不需要买服务器，不需要写后端，不需要学编程。**

---

## 六、常见修改场景

### 增删点位

告诉 AI Agent：
> 在 POINTS 列表里增加「新点位名称」，「区域名」；删除「某点位」

AI Agent 会修改 Python 脚本中的 POINTS 数组，重新生成页面。

### 改认领规则

告诉 AI Agent：
> 把认领改成可以多人选同一个点位（去掉独占逻辑）
> 或者：增加一个取消认领的功能

### 改页面样式

告诉 AI Agent：
> 把配色改成深色模式
> 表格太宽了，手机上不好看，优化一下移动端显示

### 手动修改 Firebase 数据

去 https://console.firebase.google.com/ → 你的项目 → Realtime Database → 数据标签 → 直接编辑 JSON。

比如手动清除某个点位的认领状态，或者修正写错的名字。

---

## 七、注意事项

1. **Firebase 安全规则很重要**——如果选了「测试模式」但不设规则，30 天后 Firebase 会发邮件警告。按上面 2.3 的规则设置就不会过期。
2. **GitHub 仓库必须 Public**——GitHub Pages 免费版只支持公开仓库。
3. **Firebase 项目不要删**——删了所有数据就没了，页面也废了。
4. **API Key 暴露在网页上是正常的**——Firebase 的安全靠规则不靠密钥。只要规则设对了，别人看到 apiKey 也没法乱改数据。

---

## 八、你现在就可以开始

把这段话发给 AI Agent：

> 帮我搭建一个 GitHub Pages + Firebase 的协作网页。先等我创建好 GitHub 仓库和 Firebase 项目，我把配置给你。

然后按上面第二步操作，建好仓库和 Firebase 后，把 firebaseConfig 粘贴给 AI Agent，它就会帮你生成全部代码。
