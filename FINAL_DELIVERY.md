# 成宁阀芯报价工作台 · Streamlit Cloud 生产版交付说明

作者：**Manus AI**  
日期：2026-05-15

## 一、交付结论

本次已将当前报价平台重构为符合 **Streamlit Community Cloud** 部署习惯的生产版本。程序入口为 `app.py`，产品数据统一由 `data/products.xlsx` 驱动，易变参数集中放入 `config.py`，登录账号密码通过 `st.secrets` 读取，不再写死在代码中。GitHub 官方文档说明，网页端可通过 **Add file → Upload files** 上传项目文件并提交到 `main` 分支；Streamlit 官方文档说明，准备好项目文件后可在 Community Cloud 点击 **Create app** 并按提示部署。[1] [2]

## 二、核心改造清单

| 改造项目 | 完成情况 | 说明 |
|---|---:|---|
| `requirements.txt` | 已完成 | 已补全 Streamlit、pandas、openpyxl、requests、BeautifulSoup、lxml、Pillow 等依赖。 |
| 相对路径标准化 | 已完成 | 应用通过 `Path(__file__).parent` 定位项目根目录，数据和图片均使用项目内相对路径。 |
| 登录权限控制 | 已完成 | 程序启动后先显示登录页，账号密码通过 `st.secrets["auth"]` 读取。 |
| 缓存优化 | 已完成 | 产品表读取、图片加载、行情抓取等函数已加入 `@st.cache_data`。 |
| 数据驱动架构 | 已完成 | 产品名称、系列、重量、加工费、利润等参数全部从 `products.xlsx` 读取。 |
| 动态 UI 渲染 | 已完成 | 产品卡片按 Excel 行数循环生成，新增产品只需新增 Excel 行。 |
| 配置中心化 | 已完成 | 默认铜价、汇率、费率、版本号、更新说明集中在 `config.py`。 |
| 代码模块化 | 已完成 | 登录、数据读取、行情抓取、计算、卡片渲染、侧边栏、导出逻辑均拆分为函数。 |
| 版本和日志 | 已完成 | 侧边栏底部显示版本号，并预留“更新说明”折叠框。 |
| 部署指南 | 已完成 | 已编写 `DEPLOY_STREAMLIT_CLOUD.md`，包含 GitHub 上传、Secrets 设置与 Streamlit 上线步骤。 |

## 三、最终文件结构

| 文件或目录 | 用途 |
|---|---|
| `app.py` | 完整生产版 Streamlit 应用代码。 |
| `config.py` | 配置中心，管理默认值、版本号、更新日志。 |
| `fetcher.py` | 实时铜价和汇率抓取模块。 |
| `requirements.txt` | Streamlit Cloud 自动安装依赖。 |
| `.streamlit/config.toml` | Streamlit 页面主题与运行配置。 |
| `.streamlit/secrets.example.toml` | Secrets 格式示例，不包含真实密码。 |
| `data/products.xlsx` | 产品参数唯一事实来源。 |
| `data/images/` | 产品图片资源。 |
| `DEPLOY_STREAMLIT_CLOUD.md` | 手把手部署指南。 |
| `FINAL_DELIVERY.md` | 本交付说明。 |

## 四、requirements.txt 内容

```txt
streamlit>=1.32.0
pandas>=2.0.0
openpyxl>=3.1.0
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
pillow>=10.0.0
```

## 五、Secrets 设置方法

生产环境请不要上传真实密码到 GitHub。Streamlit 官方文档明确说明，不应把未加密的 secrets 提交到 Git 仓库；本地开发可以使用 `.streamlit/secrets.toml`，部署时应在应用设置中填写 Secrets。[3]

在 Streamlit Cloud 的 **Settings → Secrets** 中粘贴以下内容，并替换为真实账号密码：

```toml
[auth]
username = "你的登录账号"
password = "你的强密码"
```

## 六、验证结果

本次已在沙箱内完成以下检查：生产版 `app.py`、`config.py`、`fetcher.py` 通过 Python 语法检查；`data/products.xlsx` 可通过相对路径读取，并识别到 25 行产品数据；最终发布目录不包含 `.streamlit/secrets.toml` 真实凭据文件；生产版文件未发现 `/home/ubuntu`、`/Users`、`C:\` 等本地绝对路径；Streamlit 服务健康检查返回 `ok`。

## 七、上线步骤摘要

请先在 GitHub 创建新仓库，建议命名为 `valve-quotation-production`，如果产品参数包含工厂成本，请选择私有仓库。随后进入仓库页面，点击 **Add file → Upload files**，把交付包中的全部文件上传到仓库根目录并提交到 `main` 分支。[1]

然后访问 [Streamlit Community Cloud](https://share.streamlit.io)，点击 **Create app** 或 **New app**，选择该 GitHub 仓库，分支选择 `main`，主文件路径填写 `app.py`。部署前或部署过程中进入 Secrets 设置，填写 `[auth]` 账号密码。确认后点击 **Deploy**，等待依赖安装和服务启动即可。[2] [3]

## References

[1]: https://docs.github.com/en/get-started/start-your-journey/uploading-a-project-to-github "Uploading a project to GitHub - GitHub Docs"
[2]: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app "Prep and deploy your app on Community Cloud - Streamlit Docs"
[3]: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management "Secrets management for your Community Cloud app - Streamlit Docs"
