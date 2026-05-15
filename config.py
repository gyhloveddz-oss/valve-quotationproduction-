"""
成宁阀芯报价工作台 · 生产版配置中心

本文件只存放易变的业务配置，不存放任何账号、密码或工厂机密。
账号密码必须通过 Streamlit 的 st.secrets 配置。
"""

APP_VERSION = "v6-nav-card-fix"
APP_NAME = "成宁阀芯报价工作台"
APP_SUBTITLE = "ValveCore Pricing · Streamlit Cloud Production"

DEFAULT_COPPER_PRICE = 78500.0
EXCHANGE_RATE_MARGIN = 0.98

DEFAULT_RATES = {
    "USD": 7.25,
    "EUR": 7.85,
    "AED": 1.97,
    "SAR": 1.93,
    "MYR": 1.60,
    "BRL": 1.35,
    "NGN": 0.0046,
}

CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "AED": "AED ",
    "SAR": "SAR ",
    "MYR": "RM ",
    "BRL": "R$",
    "NGN": "₦",
    "RMB": "¥",
}

PLATING_RATES = {
    "无电镀": 0,
    "镀铬": 3000,
    "镀镍（滚镀）": 2500,
    "镀镍（吊镀）": 2750,
}

PACKAGING_FEES = {
    "唛头印刷": 0.05,
    "单个PE袋": 0.03,
}

FREIGHT_RATES = {
    "义乌（免运费）": 0.0,
    "中东": 50.0,
    "东南亚": 35.0,
    "非洲": 120.0,
    "南美": 160.0,
}

REQUIRED_PRODUCT_COLUMNS = [
    "产品名称",
    "系列",
    "产品总重_g",
    "配件重量_g",
    "加工费_元",
    "利润_元",
]

OPTIONAL_PRODUCT_COLUMNS = [
    "净铜重_g",
    "图片路径",
    "总重是否已称量",
]

CHANGELOG = [
    "v6：顶部工作台导航改为图4式窄条样式，减少大块导航占位。",
    "v6：快开/慢开系列内产品小卡片改为原生整卡按钮，后排卡片也可直接点击。",
    "v5：修复首页系列卡片点击无响应，改为可见大卡片按钮并保留会话状态导航。",
    "v5：恢复三段式工作台布局，右侧报价栏保持最小 350px，金额左对齐。",
    "v5：修复面包屑可点击、侧边栏上传区居中、Material Symbols 图标字体保护。",
    "生产版 v1.0：增加 st.secrets 登录保护，产品参数完全从 data/products.xlsx 读取。",
]
