# 成宁阀芯报价工作台

> Streamlit Cloud 生产版 · 登录保护 · 数据驱动 · 配置中心化

本项目是面向阀芯出口贸易的实时报价平台。生产版已完成 Streamlit Cloud 部署适配，支持公网登录保护、Excel 产品数据库驱动、相对路径资源读取、缓存加速和模块化计算逻辑。

## 快速启动

```bash
pip install -r requirements.txt
streamlit run app.py
```

本地运行前，请创建 `.streamlit/secrets.toml`：

```toml
[auth]
username = "admin"
password = "your_password"
```

## 部署

详见 `DEPLOY_STREAMLIT_CLOUD.md`。
