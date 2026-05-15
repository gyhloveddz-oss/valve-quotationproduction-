# 成宁阀芯报价工作台 · Streamlit Cloud 生产部署指南

本指南用于把本次重构后的报价平台部署为可长期访问的 **Streamlit Community Cloud** 生产应用。GitHub 官方文档建议每个项目使用独立仓库管理代码，且网页端可通过 **Add file → Upload files** 上传项目文件并提交到 `main` 分支。[1] Streamlit 官方文档说明，应用准备完毕后可在 Community Cloud 工作区点击 **Create app**，按提示填写仓库、分支和主入口文件后点击 **Deploy** 完成部署。[2]

## 一、交付文件结构

请将以下文件和目录上传到 GitHub 仓库根目录。主入口文件必须放在根目录，并命名为 `app.py`。

| 路径 | 是否必须 | 说明 |
|---|---:|---|
| `app.py` | 是 | Streamlit 主程序，已加入登录、缓存、相对路径与模块化结构。 |
| `config.py` | 是 | 配置中心，集中存放默认铜价、汇率、费率、版本号和更新说明。 |
| `fetcher.py` | 是 | 实时铜价与汇率抓取模块。 |
| `requirements.txt` | 是 | Streamlit Cloud 自动安装 Python 依赖。 |
| `.streamlit/config.toml` | 建议 | Streamlit 深色主题和运行配置。 |
| `.streamlit/secrets.example.toml` | 可选 | 仅作格式示例，不包含真实密码。 |
| `data/products.xlsx` | 是 | 产品参数唯一事实来源。未来新增产品只需新增 Excel 行。 |
| `data/images/` | 建议 | 产品图片目录。图片名称可与产品名称一致，也可在 Excel 的 `图片路径` 列填写相对路径。 |
| `data/阀芯报价参考.xlsx` | 可选 | 历史报价参考表。当前生产版主程序不依赖它启动。 |

## 二、如何在 GitHub 上创建新仓库

请登录 [GitHub](https://github.com)，点击右上角的 **+**，选择 **New repository**。仓库名称建议使用 `valve-quotation-production`。如果该报价平台包含工厂成本和底价信息，建议先选择 **Private** 私有仓库；确认无敏感数据后再考虑公开。

GitHub 官方步骤要求填写仓库名、描述，选择 Public 或 Private，然后点击 **Create repository**。[1] 本项目建议先使用私有仓库，因为 `data/products.xlsx` 内包含净铜重、加工费、利润等敏感经营数据。

## 三、如何把文件上传到 GitHub

仓库创建完成后，进入仓库首页，点击 **Add file → Upload files**。然后把本次交付包中的全部文件拖入浏览器上传区。上传时请确保 `app.py`、`config.py`、`fetcher.py`、`requirements.txt` 位于仓库根目录，而不是多套一层文件夹。

文件上传完成后，在页面底部的 **Commit changes** 区域填写提交说明，例如 `Initial production Streamlit deployment`，选择 **Commit directly to the main branch**，然后点击 **Commit changes**。GitHub 官方文档也明确说明，可通过拖拽全部文件和文件夹到浏览器，然后提交到 `main` 分支。[1]

## 四、如何设置 Streamlit 机密凭据

生产版登录账号密码从 `st.secrets` 读取，不能写进 Python 代码，也不能提交到 GitHub。Streamlit 官方文档说明，未加密的 secrets 不应存入 Git 仓库；本地开发可以使用 `.streamlit/secrets.toml`，部署时应将同样内容粘贴到应用设置或高级设置的 Secrets 区域。[3]

在 Streamlit Cloud 的应用管理页面进入 **Settings → Secrets**，填写以下内容：

```toml
[auth]
username = "你的登录账号"
password = "你的强密码"
```

本地测试时可以创建 `.streamlit/secrets.toml` 并填入同样内容。该文件已经在 `.gitignore` 中排除，不能上传到 GitHub。交付包内的 `.streamlit/secrets.example.toml` 只是格式示例，不应直接作为真实密码使用。

## 五、如何连接 Streamlit Community Cloud 并上线

请访问 [Streamlit Community Cloud](https://share.streamlit.io)，使用 GitHub 账号登录。进入工作区后点击 **Create app** 或 **New app**，选择刚创建的 GitHub 仓库，分支通常选择 `main`，主文件路径填写 `app.py`。Streamlit 官方文档说明，应用具备运行所需文件后，即可按提示填写应用信息并点击 **Deploy**。[2]

首次部署时，Streamlit Cloud 会自动读取 `requirements.txt` 并安装依赖。安装完成后，应用会启动并显示登录界面。输入你在 Secrets 中设置的账号和密码后，即可进入报价工作台。

## 六、后续如何进化产品数据

如果要新增产品，请直接编辑 `data/products.xlsx`，至少填写以下列：`产品名称`、`系列`、`产品总重_g`、`配件重量_g`、`加工费_元`、`利润_元`。如果已经知道净铜重，可以填写 `净铜重_g`；如果留空，程序会自动用 `产品总重_g - 配件重量_g` 计算。

如果要新增图片，请将图片放入 `data/images/`，并让图片文件名与产品名称一致，例如 `大巴西.png`。也可以在 Excel 的 `图片路径` 列写入相对路径，例如 `data/images/大巴西.png`。程序会优先读取 Excel 的相对路径；如果没有填写，则按产品名称在 `data/images/` 中自动寻找 `.png`、`.jpg`、`.jpeg` 或 `.webp` 图片。

## 七、故障排查

| 现象 | 可能原因 | 解决方式 |
|---|---|---|
| 页面提示未配置登录凭据 | Streamlit Secrets 没有填写 `[auth]` | 到 Settings → Secrets 填写账号密码后重启应用。 |
| 部署时依赖安装失败 | `requirements.txt` 缺失或包名拼写错误 | 使用本次交付的 `requirements.txt`。 |
| 产品图片不显示 | 图片文件名和产品名不一致，或 Excel 图片路径不是相对路径 | 将图片放入 `data/images/`，并在 Excel 中填写相对路径。 |
| 新产品没有显示 | Excel 未上传到 GitHub，或列名不匹配 | 确认 `products.xlsx` 已更新并包含必要列。 |
| 实时铜价或汇率失败 | 外部行情网站在云端访问不稳定 | 可以手动输入铜价和汇率，程序会继续正常报价。 |

## References

[1]: https://docs.github.com/en/get-started/start-your-journey/uploading-a-project-to-github "Uploading a project to GitHub - GitHub Docs"
[2]: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app "Prep and deploy your app on Community Cloud - Streamlit Docs"
[3]: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management "Secrets management for your Community Cloud app - Streamlit Docs"
