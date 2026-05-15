"""
成宁阀芯报价工作台 · 生产版配置中心

本文件只存放易变的业务配置，不存放任何账号、密码或工厂机密。
账号密码必须通过 Streamlit 的 st.secrets 配置。
"""

APP_VERSION = "v9-fixed-header-home-cleanup"
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
    "v9：顶部页眉改为 fixed 固定在视口最上方，并为主内容增加顶部间距，滚动时页眉不再离开屏幕。",
    "v9：首页中间区域移除‘请选择左侧产品系列’大空卡，只保留产品系列入口，降低视觉噪音。",
    "v9：快开/慢开系列入口卡片放大并更新文案，作为首页核心入口展示。",
    "v8：修复卡片 CSS 选择器作用范围过宽，普通同步按钮、批量报价按钮和面包屑不再被放大成卡片。",
    "v8：产品选中态改为只作用于 marker 后相邻按钮，点击一个产品不再导致所有产品卡片同时勾选。",
    "v8：保留单页面 page 状态机和右侧报价栏 sticky 结构，仅隔离按钮样式作用域。",
    "v7：按图三 SaaS 工作台重构为 st.columns([1, 2.3, 1.4]) 三列布局，右侧报价栏 sticky 置顶。",
    "v7：路由统一改为 st.session_state.page（home/collection/product），禁止外部页面跳转与重复登录。",
    "v7：移除左侧重复系列导航，首页和系列页均通过整卡按钮与面包屑完成内部切换。",
    "v7：报价金额改为 28px 等宽字体左对齐，上传区居中，数量输入框保持原生可编辑。",
    "v6：顶部工作台导航改为图4式窄条样式，减少大块导航占位。",
    "v6：快开/慢开系列内产品小卡片改为原生整卡按钮，后排卡片也可直接点击。",
    "v5：修复首页系列卡片点击无响应，改为可见大卡片按钮并保留会话状态导航。",
    "v5：恢复三段式工作台布局，右侧报价栏保持最小 350px，金额左对齐。",
    "v5：修复面包屑可点击、侧边栏上传区居中、Material Symbols 图标字体保护。",
    "生产版 v1.0：增加 st.secrets 登录保护，产品参数完全从 data/products.xlsx 读取。",
]
