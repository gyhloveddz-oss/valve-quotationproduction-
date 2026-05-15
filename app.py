"""
成宁阀芯报价工作台 · Streamlit Cloud 生产版

本文件是面向 Streamlit Cloud 的完整单文件入口。设计重点如下：
1. 页面主工作区强制使用 st.columns([1, 2.3, 1.4])，保证左侧参数栏、中间产品矩阵、右侧报价栏比例稳定。
2. 所有业务页面切换均由 st.session_state.page 管理，禁止任何外部页面跳转，避免云端重复登录。
3. 面包屑、系列卡片、产品卡片均使用 st.button 触发内部状态切换并 st.rerun()。
4. 产品与成本参数只从 data/products.xlsx 读取；账号密码只从 Streamlit Secrets 读取。
"""

from __future__ import annotations

import base64
import hmac
import html
import io
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import streamlit as st

from config import (
    APP_NAME,
    APP_SUBTITLE,
    APP_VERSION,
    CHANGELOG,
    CURRENCY_SYMBOLS,
    DEFAULT_COPPER_PRICE,
    DEFAULT_RATES,
    EXCHANGE_RATE_MARGIN,
    FREIGHT_RATES,
    OPTIONAL_PRODUCT_COLUMNS,
    PACKAGING_FEES,
    PLATING_RATES,
    REQUIRED_PRODUCT_COLUMNS,
)
from fetcher import get_all_rates, get_copper_price


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
IMG_DIR = DATA_DIR / "images"
UPLOAD_DIR = DATA_DIR / "uploads"
DEFAULT_PRODUCTS_FILE = DATA_DIR / "products.xlsx"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


st.set_page_config(
    page_title=f"{APP_NAME} · SaaS",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ═══════════════════════════════════════════════════════════
# 视觉系统：浅灰白专业 SaaS 布局
# ═══════════════════════════════════════════════════════════
def inject_css() -> None:
    """注入浅灰白 SaaS 视觉系统，并稳定三栏比例和卡片按钮点击区域。"""
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600;14..32,700;14..32,800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,400,0,0&display=block');

:root {
  --bg-base:#F8F9FA;
  --bg-panel:#FFFFFF;
  --bg-soft:#F3F5F8;
  --border:#E6E9EF;
  --border-strong:#D7DCE5;
  --text:#111827;
  --muted:#667085;
  --subtle:#98A2B3;
  --disabled:#C0C6D0;
  --purple:#6D5DFB;
  --purple-soft:#F1EFFF;
  --green:#12B76A;
  --yellow:#F79009;
  --red:#F04438;
  --blue:#2E90FA;
  --shadow:0 12px 34px rgba(15,23,42,.07);
  --shadow-soft:0 6px 18px rgba(15,23,42,.045);
  --radius-card:18px;
  --radius-control:12px;
  --font:'Inter',-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei','Hiragino Sans GB',sans-serif;
  --mono:'JetBrains Mono','SF Mono','Consolas',monospace;
}

*, *::before, *::after { box-sizing:border-box; font-family:var(--font) !important; }
span[data-testid="stIconMaterial"], span[translate="no"], span[class*="material"], i[class*="material"], .material-icons, .material-symbols-rounded, .material-symbols-outlined {
  font-family:'Material Symbols Rounded','Material Symbols Outlined','Material Icons' !important;
  font-weight:normal !important; font-style:normal !important; line-height:1 !important;
  letter-spacing:normal !important; text-transform:none !important; white-space:nowrap !important;
  -webkit-font-feature-settings:'liga' !important; font-feature-settings:'liga' !important;
  -webkit-font-smoothing:antialiased !important;
}

.stApp { background:var(--bg-base) !important; color:var(--text) !important; overflow-x:hidden !important; }
#MainMenu, footer, header[data-testid="stHeader"], .stDeployButton, [data-testid="stToolbar"] { display:none !important; }
.main .block-container { max-width:none !important; padding:0 1.2rem 1.8rem 1.2rem !important; overflow-x:hidden !important; }
hr { border-color:var(--border) !important; margin:1rem 0 !important; }

/* 全局输入控件 */
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div:first-child, textarea {
  background:var(--bg-panel) !important; border:1px solid var(--border) !important; border-radius:var(--radius-control) !important;
  box-shadow:0 1px 2px rgba(15,23,42,.03) !important;
}
div[data-baseweb="input"] input, .stNumberInput input, textarea { color:var(--text) !important; font-family:var(--mono) !important; }
label, [data-testid="stWidgetLabel"] { color:var(--muted) !important; font-weight:650 !important; }

/* 顶部窄条导航 */
.vc-header {
  display:flex; align-items:center; justify-content:space-between; gap:1rem;
  min-height:48px; padding:9px 18px; margin:0 -1.2rem 18px -1.2rem;
  background:rgba(255,255,255,.94); border-bottom:1px solid var(--border);
  box-shadow:0 1px 0 rgba(15,23,42,.04); backdrop-filter:blur(12px); position:sticky; top:0; z-index:20;
}
.vc-brand { display:flex; align-items:center; gap:10px; min-width:0; }
.vc-logo { width:26px; height:26px; border-radius:8px; display:flex; align-items:center; justify-content:center; color:#fff; font-size:.78rem; font-weight:800; background:linear-gradient(135deg,#7C3AED,#4F46E5); box-shadow:0 8px 20px rgba(109,93,251,.22); }
.vc-title { color:var(--text); font-size:.92rem; font-weight:800; letter-spacing:-.02em; white-space:nowrap; }
.vc-subtitle { display:none; }
.status-row { display:flex; align-items:center; justify-content:flex-end; gap:8px; flex-wrap:nowrap; overflow-x:auto; }
.status-chip { display:inline-flex; align-items:center; gap:6px; padding:5px 10px; border-radius:999px; border:1px solid var(--border); background:var(--bg-panel); color:#344054; font-size:.68rem; font-weight:650; white-space:nowrap; box-shadow:0 1px 2px rgba(15,23,42,.035); }
.dot { width:7px; height:7px; border-radius:999px; display:inline-block; }
.dot-green { background:var(--green); box-shadow:0 0 0 3px rgba(18,183,106,.11); }
.dot-yellow { background:var(--yellow); box-shadow:0 0 0 3px rgba(247,144,9,.11); }

	/* 主三栏：用户指定比例 st.columns([1, 2.3, 1.4]) */
.layout-marker { display:none; }
div[data-testid="stHorizontalBlock"]:has(.layout-marker) { align-items:flex-start !important; gap:1.25rem !important; }
.left-pane, .workbench-pane, .quote-pane { width:100%; max-width:100%; min-width:0; }
.left-pane { padding-right:.1rem; }
.workbench-pane { padding:0 .45rem; overflow:hidden; }
.quote-pane { min-width:320px; padding-left:.1rem; }
div[data-testid="stVerticalBlock"]:has(.quote-column-marker) { position:sticky !important; top:1rem !important; align-self:start !important; min-width:320px !important; overflow:visible !important; }
.quote-column-marker, .cat-card-marker, .prod-card-marker, .crumb-marker { display:none; }

/* 左侧参数栏 */
.side-panel { background:var(--bg-panel); border:1px solid var(--border); border-radius:var(--radius-card); padding:16px; box-shadow:var(--shadow-soft); }
.side-title { font-size:.95rem; font-weight:800; color:var(--text); margin-bottom:2px; }
.side-sub { color:var(--muted); font-size:.72rem; line-height:1.55; margin-bottom:14px; }
.sb-label { display:block; color:#475467; font-size:.72rem; font-weight:800; letter-spacing:.04em; margin:.72rem 0 .38rem; }
.sb-hint { color:var(--muted); font-size:.7rem; line-height:1.55; margin:.38rem 0 .15rem; }
.box-hint { text-align:center; font-family:var(--mono) !important; padding:8px 10px; border-radius:10px; background:var(--bg-soft); border:1px solid var(--border); color:#667085; }

/* Upload 居中 */
.upload-center { width:100%; display:flex; justify-content:center; align-items:center; }
.stFileUploader,
div[data-testid="stVerticalBlock"]:has(.upload-center) [data-testid="stFileUploader"] { width:100% !important; margin:0 auto !important; }
div[data-testid="stVerticalBlock"]:has(.upload-center) [data-testid="stFileUploader"] section,
div[data-testid="stVerticalBlock"]:has(.upload-center) [data-testid="stFileUploaderDropzone"] {
  display:flex !important; align-items:center !important; justify-content:center !important; text-align:center !important;
  min-height:86px !important; border:1px dashed var(--border-strong) !important; border-radius:14px !important; background:#FBFCFE !important;
}
div[data-testid="stVerticalBlock"]:has(.upload-center) [data-testid="stFileUploader"] * { text-align:center !important; margin-left:auto !important; margin-right:auto !important; }
div[data-testid="stVerticalBlock"]:has(.upload-center) [data-testid="stFileUploader"] small { display:block !important; text-align:center !important; width:100% !important; }
.version-box { margin-top:16px; padding:12px; border:1px solid var(--border); border-radius:14px; background:var(--bg-soft); text-align:center; }
.version-text { color:#344054; font-family:var(--mono) !important; font-size:.72rem; font-weight:800; }

/* 按钮基础 */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
  border-radius:var(--radius-control) !important; border:1px solid var(--border) !important; background:var(--bg-panel) !important;
  color:#344054 !important; font-weight:750 !important; transition:all .16s ease !important; box-shadow:0 1px 2px rgba(15,23,42,.035) !important;
}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
  border-color:#B8BDFD !important; color:var(--purple) !important; background:#FBFAFF !important; transform:translateY(-1px);
}

/* 工作台标题和面包屑 */
.page-title { font-size:1.05rem; font-weight:850; color:var(--text); letter-spacing:-.025em; margin:.15rem 0 .35rem; }
.page-sub { color:var(--muted); font-size:.78rem; line-height:1.65; margin-bottom:1rem; }
.breadcrumb-row { display:flex; align-items:center; gap:6px; flex-wrap:wrap; margin-bottom:18px; }
div[data-testid="stMarkdownContainer"]:has(.crumb-marker) + div[data-testid="stButton"] > button,
div[data-testid="stMarkdownContainer"]:has(.crumb-marker) + div.stButton > button,
div[data-testid="stMarkdownContainer"]:has(.crumb-marker) ~ div[data-testid="stButton"] > button { min-height:32px !important; padding:6px 10px !important; border-radius:9px !important; font-size:.72rem !important; box-shadow:none !important; }
.crumb-current { display:inline-flex; min-height:32px; align-items:center; padding:7px 10px; border-radius:9px; border:1px solid var(--border); background:var(--purple-soft); color:var(--purple); font-size:.72rem; font-weight:850; }
.crumb-sep { display:inline-flex; align-items:center; min-height:32px; color:#98A2B3; font-size:.78rem; }



/* 首页系列卡片：整卡即按钮，不再额外放置小按钮 */
div[data-testid="stMarkdownContainer"]:has(.cat-card-marker) + div[data-testid="stButton"] > button,
div[data-testid="stMarkdownContainer"]:has(.cat-card-marker) + div.stButton > button,
div[data-testid="stMarkdownContainer"]:has(.cat-card-marker) ~ div[data-testid="stButton"] > button {
  width:100% !important; min-height:178px !important; padding:24px !important; text-align:left !important; justify-content:flex-start !important; align-items:flex-start !important;
  white-space:pre-line !important; line-height:1.58 !important; border-radius:var(--radius-card) !important;
  background:var(--bg-panel) !important; border:1px solid var(--border) !important; box-shadow:var(--shadow-soft) !important;
  color:var(--text) !important; font-size:.86rem !important;
}
div[data-testid="stMarkdownContainer"]:has(.cat-card-marker) + div[data-testid="stButton"] > button:hover,
div[data-testid="stMarkdownContainer"]:has(.cat-card-marker) + div.stButton > button:hover,
div[data-testid="stMarkdownContainer"]:has(.cat-card-marker) ~ div[data-testid="stButton"] > button:hover { border-color:var(--purple) !important; box-shadow:0 16px 34px rgba(109,93,251,.12) !important; background:#FFFFFF !important; }

/* 产品 Grid 容器：必须 padding，防止向左溢出遮挡边栏 */
.products-shell { background:var(--bg-panel); border:1px solid var(--border); border-radius:22px; padding:18px; box-shadow:var(--shadow-soft); overflow:hidden; }
.products-grid-note { color:var(--muted); font-size:.72rem; margin-bottom:12px; }

/* 产品小卡片：原生整卡按钮，避免透明覆盖层导致后排点击失效 */
div[data-testid="stMarkdownContainer"]:has(.prod-card-marker) + div[data-testid="stButton"] > button,
div[data-testid="stMarkdownContainer"]:has(.prod-card-marker) + div.stButton > button,
div[data-testid="stMarkdownContainer"]:has(.prod-card-marker) ~ div[data-testid="stButton"] > button {
  width:100% !important; min-height:172px !important; padding:16px 12px 14px !important; display:flex !important;
  align-items:flex-end !important; justify-content:center !important; position:relative !important; text-align:center !important;
  white-space:pre-line !important; line-height:1.28 !important; color:var(--text) !important; font-size:.78rem !important; font-weight:850 !important;
  background:linear-gradient(180deg,#FFFFFF 0%,#FFFFFF 70%,#F7F8FB 100%) !important;
  border:1px solid var(--border) !important; border-radius:18px !important; box-shadow:var(--shadow-soft) !important; cursor:pointer !important; overflow:hidden !important;
}
div[data-testid="stMarkdownContainer"]:has(.prod-card-marker) + div[data-testid="stButton"] > button::before,
div[data-testid="stMarkdownContainer"]:has(.prod-card-marker) + div.stButton > button::before,
div[data-testid="stMarkdownContainer"]:has(.prod-card-marker) ~ div[data-testid="stButton"] > button::before {
  content:""; position:absolute; top:20px; left:50%; transform:translateX(-50%); width:92px; height:92px; border-radius:50%;
  background:radial-gradient(circle at center,#E9FBF1 0%,#E9FBF1 54%,transparent 55%), linear-gradient(135deg,#DFF7E9,#F3FFF8);
  border:1px solid #D7F0E1;
}
div[data-testid="stMarkdownContainer"]:has(.prod-card-marker) + div[data-testid="stButton"] > button::after,
div[data-testid="stMarkdownContainer"]:has(.prod-card-marker) + div.stButton > button::after,
div[data-testid="stMarkdownContainer"]:has(.prod-card-marker) ~ div[data-testid="stButton"] > button::after {
  content:"◇"; position:absolute; top:54px; left:50%; transform:translateX(-50%); color:#15A46A; font-size:1.45rem; font-weight:400;
}
div[data-testid="stMarkdownContainer"]:has(.prod-card-marker) + div[data-testid="stButton"] > button:hover,
div[data-testid="stMarkdownContainer"]:has(.prod-card-marker) + div.stButton > button:hover,
div[data-testid="stMarkdownContainer"]:has(.prod-card-marker) ~ div[data-testid="stButton"] > button:hover { border-color:var(--purple) !important; box-shadow:0 18px 34px rgba(109,93,251,.14) !important; transform:translateY(-2px); }
div[data-testid="stMarkdownContainer"]:has(.prod-card-marker.selected) + div[data-testid="stButton"] > button,
div[data-testid="stMarkdownContainer"]:has(.prod-card-marker.selected) + div.stButton > button,
div[data-testid="stMarkdownContainer"]:has(.prod-card-marker.selected) ~ div[data-testid="stButton"] > button { border:2px solid var(--purple) !important; box-shadow:0 0 0 4px rgba(109,93,251,.10),0 18px 36px rgba(109,93,251,.16) !important; }
div[data-testid="stMarkdownContainer"]:has(.prod-card-marker.selected) + div[data-testid="stButton"] > button::after,
div[data-testid="stMarkdownContainer"]:has(.prod-card-marker.selected) + div.stButton > button::after,
div[data-testid="stMarkdownContainer"]:has(.prod-card-marker.selected) ~ div[data-testid="stButton"] > button::after { content:"✓"; top:14px; left:auto; right:14px; transform:none; width:22px; height:22px; display:flex; align-items:center; justify-content:center; border-radius:999px; background:var(--purple); color:#fff; font-size:.78rem; font-weight:900; }

/* 规格条和中间报价参数 */
.spec-strip { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin:16px 0; }
.spec-cell { background:var(--bg-panel); border:1px solid var(--border); border-radius:14px; padding:14px; box-shadow:0 1px 2px rgba(15,23,42,.03); }
.sc-label { color:var(--muted); font-size:.68rem; font-weight:800; margin-bottom:4px; }
.sc-val { color:var(--text); font-family:var(--mono) !important; font-weight:850; font-size:1.05rem; }
.sc-sub { color:var(--subtle); font-size:.7rem; margin-top:4px; }
.warn-bar { color:#B54708; background:#FFFAEB; border:1px solid #FEDF89; border-radius:12px; padding:10px 12px; font-size:.76rem; margin:12px 0; }
.controls-card { background:var(--bg-panel); border:1px solid var(--border); border-radius:18px; padding:16px; box-shadow:var(--shadow-soft); margin-top:14px; }
.empty-card { min-height:360px; display:flex; align-items:center; justify-content:center; text-align:center; background:var(--bg-panel); border:1px solid var(--border); border-radius:22px; padding:24px; box-shadow:var(--shadow-soft); }
.empty-icon { width:52px; height:52px; display:inline-flex; align-items:center; justify-content:center; border-radius:16px; background:var(--purple-soft); color:var(--purple); margin-bottom:12px; font-weight:900; }

/* 右侧报价栏：足够宽度，金额和成本行不换行挤压 */
.quote-card { background:var(--bg-panel); border:1px solid var(--border); border-radius:22px; padding:18px; box-shadow:var(--shadow); min-width:320px; overflow:hidden; }
.panel-kicker { display:flex; align-items:center; justify-content:space-between; gap:8px; color:var(--muted); font-size:.66rem; font-weight:800; letter-spacing:.06em; margin-bottom:10px; }
.panel-product { font-size:1.05rem; font-weight:850; color:var(--text); margin-bottom:12px; }
.price-hero { border:1px solid #E8E7FF; border-radius:18px; padding:18px; background:linear-gradient(135deg,#FFFFFF 0%,#F7F6FF 100%); box-shadow:inset 0 1px 0 rgba(255,255,255,.9); }
.ph-row { display:flex; align-items:center; justify-content:space-between; gap:10px; }
.ph-label, .ot-label, .mt-label { color:var(--muted); font-size:.66rem; font-weight:800; letter-spacing:.04em; }
.ph-currency { color:#667085; font-size:.72rem; white-space:nowrap; }
.ph-amount { margin-top:8px; color:#101828; font-family:var(--mono) !important; font-size:28px; font-weight:850; letter-spacing:-.04em; line-height:1.08; white-space:nowrap; overflow:visible; text-align:left; }
.ph-rmb { margin-top:7px; color:#344054; font-family:var(--mono) !important; font-size:.88rem; font-weight:800; white-space:nowrap; }
.ph-sub { margin-top:12px; padding-top:10px; border-top:1px solid var(--border); color:#667085; font-size:.66rem; line-height:1.55; }
.metric-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin:12px 0; }
.metric-tile { background:#FBFCFE; border:1px solid var(--border); border-radius:16px; padding:14px; min-width:0; }
.mt-val { margin-top:6px; color:#101828; font-family:var(--mono) !important; font-size:1.04rem; font-weight:850; white-space:nowrap; }
.mt-sub { color:var(--subtle); font-size:.66rem; margin-top:3px; }
.order-total { background:linear-gradient(135deg,#F7F5FF,#FFFFFF); border:1px solid #E4E0FF; border-radius:18px; padding:16px; margin-bottom:12px; }
.ot-val { color:var(--purple); font-family:var(--mono) !important; font-size:1.45rem; font-weight:850; white-space:nowrap; margin-top:6px; }
.ot-sub { color:#667085; font-family:var(--mono) !important; font-size:.66rem; margin-top:4px; white-space:nowrap; }
.margin-row { display:flex; align-items:center; justify-content:space-between; gap:8px; padding:12px 0; border-top:1px solid var(--border); }
.margin-label { color:#475467; font-size:.76rem; font-weight:800; }
.margin-pill { display:inline-flex; align-items:center; padding:5px 10px; border-radius:999px; font-family:var(--mono) !important; font-size:.72rem; font-weight:850; white-space:nowrap; }
.mp-good { color:#067647; background:#ECFDF3; border:1px solid #ABEFC6; }
.mp-warn { color:#B54708; background:#FFFAEB; border:1px solid #FEDF89; }
.mp-danger { color:#B42318; background:#FEF3F2; border:1px solid #FECDCA; }
.cost-row { display:grid; grid-template-columns:8px minmax(64px,1fr) 76px 42px; gap:8px; align-items:center; padding:8px 0; border-bottom:1px solid var(--border); }
.cost-dot { width:8px; height:8px; border-radius:999px; }
.cost-name { color:#475467; font-size:.72rem; font-weight:700; white-space:nowrap; }
.cost-val { color:#101828; font-family:var(--mono) !important; font-size:.72rem; text-align:right; white-space:nowrap; }
.cost-pct { color:#98A2B3; font-size:.66rem; text-align:right; white-space:nowrap; }
.formula { font-family:var(--mono) !important; color:#475467; font-size:.7rem; line-height:1.7; white-space:pre-wrap; }
.tool-card { background:var(--bg-panel); border:1px solid var(--border); border-radius:22px; padding:18px; box-shadow:var(--shadow-soft); margin-top:18px; }
.login-shell { max-width:420px; margin:12vh auto 1.5rem; padding:30px; border:1px solid var(--border); border-radius:22px; background:var(--bg-panel); box-shadow:var(--shadow); }
.login-title { font-size:1.2rem; font-weight:850; color:var(--text); margin-bottom:4px; }
.login-sub { color:var(--muted); font-size:.82rem; line-height:1.65; }
[data-testid="stDataFrame"] * { font-family:var(--mono) !important; }

@media (max-width: 1280px) {
  .quote-pane, .quote-card, div[data-testid="stVerticalBlock"]:has(.quote-column-marker) { min-width:300px !important; }
	  .ph-amount { font-size:28px; }
}
@media (max-width: 980px) {
  div[data-testid="stHorizontalBlock"]:has(.layout-marker) { flex-direction:column !important; }
  .quote-pane, .quote-card, div[data-testid="stVerticalBlock"]:has(.quote-column-marker) { min-width:100% !important; position:relative !important; top:auto !important; }
  .spec-strip, .metric-grid { grid-template-columns:1fr; }
  .vc-header { position:relative; flex-direction:column; align-items:flex-start; }
}
</style>
        """,
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════
# 访问权限控制
# ═══════════════════════════════════════════════════════════
def read_auth_secrets() -> tuple[str | None, str | None]:
    """从 Streamlit Secrets 读取账号与密码。"""
    try:
        auth = st.secrets.get("auth", {})
        return auth.get("username"), auth.get("password")
    except Exception:
        return None, None


def verify_password(input_user: str, input_password: str, secret_user: str, secret_password: str) -> bool:
    """使用常量时间比较，降低密码比较时序泄露风险。"""
    return hmac.compare_digest(input_user, secret_user) and hmac.compare_digest(input_password, secret_password)


def require_login() -> None:
    """公网部署前置登录界面。未登录时停止渲染业务页面。"""
    if st.session_state.get("authenticated"):
        return

    secret_user, secret_password = read_auth_secrets()
    st.markdown(
        f"""
        <div class="login-shell">
          <div class="vc-brand" style="margin-bottom:18px;">
            <div class="vc-logo">成</div>
            <div>
              <div class="login-title">{APP_NAME}</div>
              <div class="login-sub">公网生产版本已启用访问保护。请输入授权账号后继续。</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("账号", placeholder="请输入账号")
        password = st.text_input("密码", type="password", placeholder="请输入密码")
        submitted = st.form_submit_button("登录", use_container_width=True)

    if not secret_user or not secret_password:
        st.error("尚未配置登录凭据。请在 Streamlit Cloud 的 Secrets 中配置 [auth] username 与 password。")
        st.stop()

    if submitted:
        if verify_password(username, password, secret_user, secret_password):
            st.session_state.authenticated = True
            st.rerun()
        st.error("账号或密码不正确。")
        st.stop()
    st.stop()


# ═══════════════════════════════════════════════════════════
# 数据处理层
# ═══════════════════════════════════════════════════════════
def safe_filename(name: str) -> str:
    """根据产品名称生成安全的图片文件名候选。"""
    return re.sub(r"[/\\°\s]+", "_", str(name)).strip("_")


def resolve_relative_path(path_text: str | Path | None) -> Path | None:
    """将 Excel 中的图片路径标准化为项目内相对路径。"""
    if path_text is None or str(path_text).strip() == "" or str(path_text).lower() == "nan":
        return None
    raw = Path(str(path_text).strip())
    if raw.is_absolute():
        return IMG_DIR / raw.name
    return (BASE_DIR / raw).resolve()


@st.cache_data(show_spinner=False)
def image_to_base64(image_path: str) -> str:
    """读取图片并转为 Base64。保留能力，供后续需要图片卡片时复用。"""
    path = Path(image_path)
    if not path.exists() or not path.is_file():
        return ""
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def find_product_image(product_row: pd.Series) -> str:
    """按 Excel 图片路径或产品名称自动寻找产品图片。"""
    explicit_path = resolve_relative_path(product_row.get("图片路径", ""))
    candidates: list[Path] = []
    if explicit_path:
        candidates.append(explicit_path)
    product_name = str(product_row.get("产品名称", ""))
    for stem in [safe_filename(product_name), product_name]:
        for suffix in [".png", ".jpg", ".jpeg", ".webp"]:
            candidates.append(IMG_DIR / f"{stem}{suffix}")
    for candidate in candidates:
        if candidate.exists():
            return image_to_base64(str(candidate))
    return ""


def normalize_product_table(df: pd.DataFrame) -> pd.DataFrame:
    """校验并标准化产品表，确保计算列存在且类型正确。"""
    missing = [col for col in REQUIRED_PRODUCT_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"products.xlsx 缺少必要列：{', '.join(missing)}")

    for col in OPTIONAL_PRODUCT_COLUMNS:
        if col not in df.columns:
            df[col] = "" if col in {"图片路径", "总重是否已称量"} else 0

    numeric_cols = ["产品总重_g", "配件重量_g", "加工费_元", "利润_元", "净铜重_g"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if df["净铜重_g"].isna().any():
        df["净铜重_g"] = df["净铜重_g"].fillna(df["产品总重_g"] - df["配件重量_g"])

    df["产品名称"] = df["产品名称"].astype(str).str.strip()
    df["系列"] = df["系列"].astype(str).str.strip()
    df = df.dropna(subset=["产品名称", "系列"]).reset_index(drop=True)
    return df


@st.cache_data(show_spinner=False)
def load_products(product_file: str = str(DEFAULT_PRODUCTS_FILE)) -> pd.DataFrame:
    """从 Excel 加载产品数据库。默认路径为 ./data/products.xlsx。"""
    path = Path(product_file)
    if not path.exists():
        raise FileNotFoundError(f"未找到产品数据库：{path}")
    return normalize_product_table(pd.read_excel(path))


@st.cache_data(ttl=60 * 30, show_spinner=False)
def cached_copper_price() -> dict[str, Any]:
    """缓存实时铜价请求，避免多人访问时频繁抓取外部网站。"""
    return get_copper_price()


@st.cache_data(ttl=60 * 30, show_spinner=False)
def cached_exchange_rates() -> dict[str, Any]:
    """缓存实时汇率请求。"""
    return get_all_rates()


# ═══════════════════════════════════════════════════════════
# 核心计算层
# ═══════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def calculate_quote_values(
    net_g: float,
    processing_fee: float,
    profit_fee: float,
    copper_price: float,
    plating_rate: float,
    packaging_total: float,
    quantity: int,
    freight_rate: float,
    currency: str,
    exchange_rate: float,
    box_l: float,
    box_w: float,
    box_h: float,
    units_per_box: int,
) -> dict[str, float]:
    """纯参数报价引擎。"""
    material = net_g * copper_price / 1_000_000
    plating_fee = net_g * plating_rate / 1_000_000
    cbm = box_l * box_w * box_h / 1_000_000
    freight = (freight_rate * cbm / units_per_box * exchange_rate) if units_per_box > 0 else 0
    rmb = material + processing_fee + plating_fee + packaging_total + freight + profit_fee
    effective_rate = exchange_rate * EXCHANGE_RATE_MARGIN
    foreign = (rmb / effective_rate) if currency != "RMB" and effective_rate > 0 else rmb
    margin = round(profit_fee / rmb * 100, 1) if rmb > 0 else 0.0
    return {
        "原材料": round(material, 4),
        "加工配件": round(processing_fee, 4),
        "电镀": round(plating_fee, 4),
        "包装": round(packaging_total, 4),
        "运费": round(freight, 4),
        "利润": round(profit_fee, 4),
        "rmb": round(rmb, 4),
        "fgn": round(foreign, 4),
        "total": round(foreign * quantity, 2),
        "margin": margin,
        "eff_rate": round(effective_rate, 4),
        "net_g": round(net_g, 4),
        "cbm": round(cbm, 4),
    }


def calculate_quote(
    product_row: pd.Series,
    copper_price: float,
    plating: str,
    packaging: Iterable[str],
    quantity: int,
    destination: str,
    currency: str,
    exchange_rate: float,
    box_l: float,
    box_w: float,
    box_h: float,
    units_per_box: int,
) -> dict[str, float]:
    """把产品行转换为纯参数，再调用缓存计算函数。"""
    packaging_total = sum(PACKAGING_FEES.get(option, 0.0) for option in packaging)
    return calculate_quote_values(
        net_g=float(product_row["净铜重_g"]),
        processing_fee=float(product_row["加工费_元"]),
        profit_fee=float(product_row["利润_元"]),
        copper_price=float(copper_price),
        plating_rate=float(PLATING_RATES.get(plating, 0.0)),
        packaging_total=float(packaging_total),
        quantity=int(quantity),
        freight_rate=float(FREIGHT_RATES.get(destination, 0.0)),
        currency=currency,
        exchange_rate=float(exchange_rate),
        box_l=float(box_l),
        box_w=float(box_w),
        box_h=float(box_h),
        units_per_box=int(units_per_box),
    )


# ═══════════════════════════════════════════════════════════
# 状态机：禁止外部跳转，全部内部刷新
# ═══════════════════════════════════════════════════════════
def init_session_state() -> None:
    defaults = {
        "authenticated": False,
        "page": "home",  # home / collection / product
        "selected_cat": None,
        "selected_prod": None,
        "copper_price": DEFAULT_COPPER_PRICE,
        "copper_source": "默认值",
        "rates": {**DEFAULT_RATES, "_source": "默认值", "_success": False},
        "custom_excel_path": None,
        "plating": "无电镀",
        "packaging": [],
        "quantity": 500,
        "destination": "义乌（免运费）",
        "currency": "USD",
        "exchange_rate": DEFAULT_RATES["USD"],
        "box_l": 40.0,
        "box_w": 30.0,
        "box_h": 25.0,
        "units_per_box": 200,
    }
    legacy_view = st.session_state.pop("view", None)
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
    if legacy_view and st.session_state.page == "home":
        st.session_state.page = "home" if legacy_view == "all" else legacy_view
    if st.session_state.page not in {"home", "collection", "product"}:
        st.session_state.page = "home"


def reset_to_home() -> None:
    st.session_state.page = "home"
    st.session_state.selected_cat = None
    st.session_state.selected_prod = None
    st.rerun()


def open_collection(category: str, df: pd.DataFrame, select_first: bool = False) -> None:
    st.session_state.page = "collection"
    st.session_state.selected_cat = category
    if select_first:
        cat_df = df[df["系列"].astype(str) == str(category)].reset_index(drop=True)
        st.session_state.selected_prod = str(cat_df.iloc[0]["产品名称"]) if len(cat_df) else None
    st.rerun()


def open_product(category: str, product_name: str) -> None:
    st.session_state.page = "product"
    st.session_state.selected_cat = category
    st.session_state.selected_prod = product_name
    st.rerun()


def ensure_valid_selection(df: pd.DataFrame) -> None:
    """确保 session_state 中的系列和产品仍存在于当前 Excel 数据库。"""
    categories = set(df["系列"].dropna().astype(str))
    products = set(df["产品名称"].dropna().astype(str))
    if st.session_state.selected_cat and st.session_state.selected_cat not in categories:
        st.session_state.selected_cat = None
        st.session_state.selected_prod = None
        st.session_state.page = "home"
    if st.session_state.selected_prod and st.session_state.selected_prod not in products:
        st.session_state.selected_prod = None
        if st.session_state.selected_cat:
            st.session_state.page = "collection"
        else:
            st.session_state.page = "home"


# ═══════════════════════════════════════════════════════════
# UI 渲染层
# ═══════════════════════════════════════════════════════════
def render_sidebar_controls() -> dict[str, Any]:
    """渲染左侧窄屏参数栏。"""
    st.markdown('<div class="left-pane"><div class="side-panel"><div class="side-title">报价参数</div><div class="side-sub">铜价、汇率与箱规在此统一管理。</div>', unsafe_allow_html=True)

    st.markdown('<span class="sb-label">铜价（元/吨）</span>', unsafe_allow_html=True)
    copper_price = st.number_input(
        "铜价",
        min_value=40000,
        max_value=150000,
        value=int(st.session_state.copper_price),
        step=100,
        label_visibility="collapsed",
    )
    st.session_state.copper_price = copper_price
    if st.button("同步实时铜价", key="sync_copper", use_container_width=True, icon=":material/sync:"):
        with st.spinner("同步铜价中..."):
            result = cached_copper_price()
            st.session_state.copper_price = float(result.get("price", DEFAULT_COPPER_PRICE))
            st.session_state.copper_source = result.get("source", "实时源")
        st.rerun()

    st.divider()
    st.markdown('<span class="sb-label">报价货币</span>', unsafe_allow_html=True)
    currency_options = ["USD", "EUR", "AED", "SAR", "MYR", "BRL", "NGN", "RMB"]
    currency_labels = {
        "USD": "$ USD · 美元",
        "EUR": "€ EUR · 欧元",
        "AED": "AED · 迪拉姆",
        "SAR": "SAR · 里亚尔",
        "MYR": "RM MYR · 林吉特",
        "BRL": "R$ BRL · 雷亚尔",
        "NGN": "₦ NGN · 奈拉",
        "RMB": "¥ RMB · 人民币",
    }
    currency = st.selectbox(
        "报价货币",
        currency_options,
        format_func=lambda item: currency_labels.get(item, item),
        index=currency_options.index(st.session_state.currency) if st.session_state.currency in currency_options else 0,
        label_visibility="collapsed",
    )
    st.session_state.currency = currency
    default_rate = st.session_state.rates.get(currency, DEFAULT_RATES.get(currency, 1.0)) if currency != "RMB" else 1.0
    exchange_rate = st.number_input(
        "汇率",
        min_value=0.0001,
        max_value=100.0,
        value=float(default_rate),
        step=0.01,
        format="%.4f",
        disabled=(currency == "RMB"),
        label_visibility="collapsed",
    )
    st.session_state.exchange_rate = exchange_rate
    if currency != "RMB":
        effective_rate = round(exchange_rate * EXCHANGE_RATE_MARGIN, 4)
        st.markdown(f'<p class="sb-hint">报价汇率 = {exchange_rate} × {EXCHANGE_RATE_MARGIN} = <b>{effective_rate}</b></p>', unsafe_allow_html=True)
    if st.button("同步实时汇率", key="sync_rates", use_container_width=True, icon=":material/currency_exchange:"):
        with st.spinner("同步汇率中..."):
            st.session_state.rates = cached_exchange_rates()
        st.rerun()

    st.divider()
    st.markdown('<span class="sb-label">标准箱规格</span>', unsafe_allow_html=True)
    col_l, col_w, col_h = st.columns(3, gap="small")
    with col_l:
        box_l = st.number_input("长cm", value=int(st.session_state.box_l), step=1, format="%d", label_visibility="collapsed")
    with col_w:
        box_w = st.number_input("宽cm", value=int(st.session_state.box_w), step=1, format="%d", label_visibility="collapsed")
    with col_h:
        box_h = st.number_input("高cm", value=int(st.session_state.box_h), step=1, format="%d", label_visibility="collapsed")
    units_per_box = st.number_input("每箱数量", min_value=1, value=int(st.session_state.units_per_box), step=10, label_visibility="collapsed")
    cbm_val = round(box_l * box_w * box_h / 1_000_000, 4)
    st.markdown(f'<p class="sb-hint box-hint">{box_l:.0f}×{box_w:.0f}×{box_h:.0f} cm · {cbm_val} CBM · {units_per_box} 只/箱</p>', unsafe_allow_html=True)
    st.session_state.box_l, st.session_state.box_w, st.session_state.box_h = box_l, box_w, box_h
    st.session_state.units_per_box = units_per_box

    st.divider()
    st.markdown('<span class="sb-label">数据管理</span>', unsafe_allow_html=True)
    st.markdown('<div class="upload-center"></div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("上传产品明细表", type=["xlsx"], label_visibility="collapsed")
    if uploaded:
        saved_path = UPLOAD_DIR / uploaded.name
        saved_path.write_bytes(uploaded.getbuffer())
        st.session_state.custom_excel_path = str(saved_path)
        st.cache_data.clear()
        st.rerun()
    if st.session_state.custom_excel_path:
        st.markdown(f'<p class="sb-hint">当前数据：{Path(st.session_state.custom_excel_path).name}</p>', unsafe_allow_html=True)
        if st.button("恢复默认数据", key="reset_data", use_container_width=True):
            st.session_state.custom_excel_path = None
            st.cache_data.clear()
            st.rerun()

    render_version_block()
    st.markdown('</div></div>', unsafe_allow_html=True)

    return {
        "copper_price": copper_price,
        "currency": currency,
        "exchange_rate": exchange_rate,
        "box_l": box_l,
        "box_w": box_w,
        "box_h": box_h,
        "units_per_box": units_per_box,
    }


def render_version_block() -> None:
    st.markdown(
        f"""
        <div class="version-box">
          <div class="version-text">{APP_VERSION}</div>
          <div style="color:#98A2B3;font-size:.66rem;margin-top:4px;">Streamlit Cloud Ready</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("更新说明", expanded=False):
        for item in CHANGELOG:
            st.markdown(f"<p class='sb-hint'>• {html.escape(str(item))}</p>", unsafe_allow_html=True)


def render_header(df: pd.DataFrame, params: dict[str, Any]) -> None:
    now = datetime.now().strftime("%H:%M")
    copper_dot = "dot-green" if st.session_state.copper_source != "默认值" else "dot-yellow"
    rate_dot = "dot-green" if st.session_state.rates.get("_success") else "dot-yellow"
    st.markdown(
        f"""
        <div class="vc-header">
          <div class="vc-brand">
            <div class="vc-logo">成</div>
            <div>
              <div class="vc-title">{APP_NAME}</div>
              <div class="vc-subtitle">{APP_SUBTITLE}</div>
            </div>
          </div>
          <div class="status-row">
            <span class="status-chip"><span class="dot {copper_dot}"></span>铜价 ¥{params['copper_price']:,.0f}</span>
            <span class="status-chip"><span class="dot {rate_dot}"></span>{params['currency']} {params['exchange_rate']}</span>
            <span class="status-chip"><span class="dot dot-green"></span>{len(df)} 产品 · {now}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_series_navigation(df: pd.DataFrame) -> None:
    st.markdown('<div class="page-title">系列导航</div><div class="page-sub">点击系列后，中间区域显示产品卡片。</div>', unsafe_allow_html=True)
    all_selected = st.session_state.page == "home"
    st.markdown(f'<div class="side-nav-marker {"selected" if all_selected else ""}"></div>', unsafe_allow_html=True)
    if st.button("所有系列", key="nav_all", use_container_width=True):
        reset_to_home()

    categories = list(df["系列"].dropna().astype(str).unique())
    for idx, category in enumerate(categories):
        count = int((df["系列"].astype(str) == str(category)).sum())
        selected = st.session_state.selected_cat == category and st.session_state.page in {"collection", "product"}
        st.markdown(f'<div class="side-nav-marker {"selected" if selected else ""}"></div>', unsafe_allow_html=True)
        if st.button(f"{category}系列 · {count}款", key=f"nav_cat_{idx}_{category}", use_container_width=True):
            open_collection(category, df, select_first=False)


def render_breadcrumb(df: pd.DataFrame, product: pd.Series | None = None) -> None:
    selected_cat = st.session_state.selected_cat
    st.markdown('<div class="breadcrumb-row breadcrumb-marker">', unsafe_allow_html=True)
    crumb_cols = st.columns([0.82, 0.12, 0.86, 0.12, 1.2, 4.2], gap="small")
    with crumb_cols[0]:
        st.markdown('<div class="crumb-marker"></div>', unsafe_allow_html=True)
        if st.button("所有系列", key="crumb_all", use_container_width=True):
            reset_to_home()
    with crumb_cols[1]:
        st.markdown('<span class="crumb-sep">/</span>', unsafe_allow_html=True)
    with crumb_cols[2]:
        if selected_cat:
            st.markdown('<div class="crumb-marker"></div>', unsafe_allow_html=True)
            if st.button(f"{selected_cat}系列", key="crumb_collection", use_container_width=True):
                st.session_state.page = "collection"
                st.rerun()
        else:
            st.markdown('<span class="crumb-current">未选系列</span>', unsafe_allow_html=True)
    with crumb_cols[3]:
        st.markdown('<span class="crumb-sep">/</span>', unsafe_allow_html=True)
    with crumb_cols[4]:
        if product is not None:
            st.markdown(f'<span class="crumb-current">{html.escape(str(product["产品名称"]))}</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="crumb-current">产品列表</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_category_selector(df: pd.DataFrame) -> None:
    st.markdown('<div class="page-title">选择产品系列</div><div class="page-sub">选择阀芯类型，进入产品选择与实时报价工作台。</div>', unsafe_allow_html=True)
    categories = list(df["系列"].dropna().astype(str).unique())
    cols = st.columns(max(1, min(2, len(categories))), gap="large")
    for idx, category in enumerate(categories):
        count = int((df["系列"].astype(str) == str(category)).sum())
        with cols[idx % len(cols)]:
            icon_text = ":material/bolt:" if "快" in category else ":material/settings:"
            st.markdown('<div class="cat-card-marker"></div>', unsafe_allow_html=True)
            card_label = f"{icon_text}\n\n{category}系列\n\n来自 products.xlsx 的动态产品系列。新增系列后这里会自动出现入口。\n\n◆ {count} 款产品"
            if st.button(card_label, key=f"cat_card_{idx}_{category}", use_container_width=True):
                open_collection(category, df, select_first=False)


def get_selected_product(df: pd.DataFrame) -> pd.Series | None:
    product_name = st.session_state.selected_prod
    if not product_name:
        return None
    matched = df[df["产品名称"].astype(str) == str(product_name)]
    return matched.iloc[0] if len(matched) else None


def render_product_grid(df: pd.DataFrame) -> None:
    selected_cat = st.session_state.selected_cat
    if not selected_cat:
        render_category_selector(df)
        return

    selected_product = get_selected_product(df)
    render_breadcrumb(df, selected_product if st.session_state.page == "product" else None)
    st.markdown('<div class="products-shell">', unsafe_allow_html=True)
    st.markdown(f'<div class="products-grid-note">当前系列：<b>{html.escape(str(selected_cat))}</b>。点击任意产品卡片将在右侧刷新报价，不打开新网页。</div>', unsafe_allow_html=True)

    cat_df = df[df["系列"].astype(str) == str(selected_cat)].reset_index(drop=True)
    columns_per_row = 4
    for start in range(0, len(cat_df), columns_per_row):
        row_df = cat_df.iloc[start : start + columns_per_row]
        cols = st.columns(columns_per_row, gap="medium")
        for offset, (_, product) in enumerate(row_df.iterrows()):
            product_name = str(product["产品名称"])
            selected_class = "selected" if st.session_state.selected_prod == product_name else ""
            with cols[offset]:
                st.markdown(f'<div class="prod-card-marker product-card-marker {selected_class}"></div>', unsafe_allow_html=True)
                if st.button(product_name, key=f"prod_card_{start}_{offset}_{product_name}", use_container_width=True, icon=":material/arrow_forward:"):
                    open_product(str(selected_cat), product_name)
    st.markdown('</div>', unsafe_allow_html=True)


def render_product_empty_state(df: pd.DataFrame) -> None:
    category_count = df["系列"].nunique()
    product_count = len(df)
    st.markdown(
        f"""
        <div class="empty-card">
          <div>
            <div class="empty-icon">◆</div>
            <div class="page-title">请选择左侧产品系列</div>
            <div class="page-sub" style="max-width:520px;margin:0 auto;">当前数据库包含 {category_count} 个系列、{product_count} 款产品。选择系列后，中间区域会显示产品卡片；点击任意卡片即可在右侧生成实时报价。</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_product_specs(product: pd.Series) -> None:
    st.markdown(
        f"""
        <div class="spec-strip">
          <div class="spec-cell"><div class="sc-label">净铜重</div><div class="sc-val">{float(product['净铜重_g']):.1f}g</div><div class="sc-sub">总重 {float(product['产品总重_g']):.1f}g</div></div>
          <div class="spec-cell"><div class="sc-label">加工+配件</div><div class="sc-val">¥{float(product['加工费_元']):.2f}</div><div class="sc-sub">配件 {float(product['配件重量_g']):.1f}g</div></div>
          <div class="spec-cell"><div class="sc-label">利润</div><div class="sc-val">¥{float(product['利润_元']):.2f}</div><div class="sc-sub">{html.escape(str(product.get('系列', '—')))} 系列</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if "⚠" in str(product.get("总重是否已称量", "")):
        st.markdown('<div class="warn-bar">产品总重为估算值，请向车间确认后更新 products.xlsx 以提高报价精度。</div>', unsafe_allow_html=True)


def render_quote_controls() -> None:
    st.markdown('<div class="controls-card"><div class="page-sub" style="margin-bottom:.7rem;">报价参数</div>', unsafe_allow_html=True)
    col_a, col_b = st.columns(2, gap="small")
    with col_a:
        plating_options = list(PLATING_RATES.keys())
        current_plating = st.session_state.plating if st.session_state.plating in plating_options else plating_options[0]
        st.session_state.plating = st.selectbox("表面处理", plating_options, index=plating_options.index(current_plating), key="cfg_plating")
    with col_b:
        st.session_state.quantity = st.number_input("订单数量（只）", min_value=1, value=int(st.session_state.quantity), step=100, key="cfg_quantity")
    col_c, col_d = st.columns(2, gap="small")
    with col_c:
        st.session_state.packaging = st.multiselect("包装附加", list(PACKAGING_FEES.keys()), default=st.session_state.packaging, key="cfg_packaging")
    with col_d:
        destination_options = list(FREIGHT_RATES.keys())
        current_dest = st.session_state.destination if st.session_state.destination in destination_options else destination_options[0]
        st.session_state.destination = st.selectbox("目的地", destination_options, index=destination_options.index(current_dest), key="cfg_destination")
    st.markdown('</div>', unsafe_allow_html=True)


def render_quote_panel(product: pd.Series | None, params: dict[str, Any]) -> None:
    if product is None:
        title = "开始报价" if st.session_state.page == "home" else "选择产品"
        desc = "先选择产品系列，然后选择具体产品。" if st.session_state.page == "home" else "点击中间任意产品卡片后，报价结果将在这里实时显示。"
        st.markdown(
            f"""
            <div class="quote-card">
              <div style="min-height:420px;display:flex;align-items:center;justify-content:center;text-align:center;">
                <div>
                  <div class="empty-icon">◆</div>
                  <div style="font-size:1rem;font-weight:850;color:#111827;margin-bottom:8px;">{title}</div>
                  <div style="font-size:.78rem;color:#667085;line-height:1.65;">{desc}</div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    quote = calculate_quote(
        product,
        copper_price=params["copper_price"],
        plating=st.session_state.plating,
        packaging=st.session_state.packaging,
        quantity=int(st.session_state.quantity),
        destination=st.session_state.destination,
        currency=params["currency"],
        exchange_rate=params["exchange_rate"],
        box_l=params["box_l"],
        box_w=params["box_w"],
        box_h=params["box_h"],
        units_per_box=int(params["units_per_box"]),
    )
    currency = params["currency"]
    symbol = CURRENCY_SYMBOLS.get(currency, "")
    margin = float(quote["margin"])
    if margin >= 15:
        pill_class, trend = "mp-good", "↑"
    elif margin >= 8:
        pill_class, trend = "mp-warn", "→"
    else:
        pill_class, trend = "mp-danger", "↓"

    safe_product_name = html.escape(str(product["产品名称"]))
    st.markdown(
        f"""
        <div class="quote-card">
          <div class="panel-kicker"><span>实时报价</span><span><span class="dot dot-green"></span> 实时汇率已应用</span></div>
          <div class="panel-product">{safe_product_name}</div>
          <div class="price-hero">
            <div class="ph-row"><div class="ph-label">单件报价</div><div class="ph-currency">{currency} / 只</div></div>
            <div class="ph-amount">{symbol}{quote['fgn']:.4f}</div>
            <div class="ph-rmb">¥{quote['rmb']:.4f} RMB</div>
            <div class="ph-sub">汇率 {params['exchange_rate']} × {EXCHANGE_RATE_MARGIN} = {quote['eff_rate']} · 含 2% 安全边际</div>
          </div>
          <div class="metric-grid">
            <div class="metric-tile"><div class="mt-label">人民币单价</div><div class="mt-val">¥{quote['rmb']:.4f}</div><div class="mt-sub">元 / 只</div></div>
            <div class="metric-tile"><div class="mt-label">净铜重</div><div class="mt-val">{quote['net_g']:.1f}g</div><div class="mt-sub">铜价 ¥{params['copper_price']:,.0f}</div></div>
          </div>
          <div class="order-total">
            <div class="ph-row"><div class="ot-label">订单总价</div><div style="color:#667085;font-size:.66rem;font-family:JetBrains Mono,monospace;white-space:nowrap;">{int(st.session_state.quantity):,} 只</div></div>
            <div class="ot-val">{symbol}{quote['total']:,.2f}</div>
            <div class="ot-sub">{symbol}{quote['fgn']:.4f} × {int(st.session_state.quantity):,} {currency}</div>
          </div>
          <div class="margin-row"><span class="margin-label">利润率</span><span class="margin-pill {pill_class}">{trend} {margin}%</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("成本构成明细", expanded=False, icon=":material/format_list_bulleted:"):
        cost_items = [
            ("原材料", quote["原材料"], "#6D5DFB"),
            ("加工+配件", quote["加工配件"], "#12B76A"),
            ("电镀", quote["电镀"], "#F79009"),
            ("包装", quote["包装"], "#7A5AF8"),
            ("运费", quote["运费"], "#2E90FA"),
            ("利润", quote["利润"], "#F04438"),
        ]
        for name, value, color in cost_items:
            pct = round(value / quote["rmb"] * 100, 1) if quote["rmb"] else 0
            st.markdown(
                f"<div class='cost-row'><span class='cost-dot' style='background:{color}'></span><span class='cost-name'>{name}</span><span class='cost-val'>¥{value:.3f}</span><span class='cost-pct'>{pct}%</span></div>",
                unsafe_allow_html=True,
            )

    with st.expander("查看计算公式", expanded=False, icon=":material/functions:"):
        formula = (
            f"原材料 = {quote['net_g']}g × {params['copper_price']:,.0f} / 1,000,000 = ¥{quote['原材料']}\n"
            f"电镀   = {quote['net_g']}g × {PLATING_RATES.get(st.session_state.plating, 0):,} / 1,000,000 = ¥{quote['电镀']}\n"
            f"运费   = {FREIGHT_RATES.get(st.session_state.destination, 0)} $/CBM × {quote['cbm']} CBM / {params['units_per_box']} × {params['exchange_rate']} = ¥{quote['运费']}\n"
            f"{'─' * 30}\n"
            f"RMB    = {quote['原材料']} + {quote['加工配件']} + {quote['电镀']} + {quote['包装']} + {quote['运费']} + {quote['利润']} = ¥{quote['rmb']}\n"
            f"{currency} = ¥{quote['rmb']} / {quote['eff_rate']} = {symbol}{quote['fgn']}"
        )
        st.markdown(f"<div class='formula'>{formula}</div>", unsafe_allow_html=True)


def render_workbench(df: pd.DataFrame, params: dict[str, Any]) -> dict[str, Any]:
    """渲染生产三段式工作台：左参数与导航 / 中间产品 / 右报价。"""
    st.markdown('<div class="layout-marker"></div>', unsafe_allow_html=True)
    left_col, mid_col, right_col = st.columns([1, 2.3, 1.4], gap="large")

    with left_col:
        params = render_sidebar_controls()

    with mid_col:
        st.markdown('<div class="workbench-pane">', unsafe_allow_html=True)
        if st.session_state.page == "home" or not st.session_state.selected_cat:
            render_category_selector(df)
            render_product_empty_state(df)
        else:
            render_product_grid(df)
            selected = get_selected_product(df)
            if selected is not None:
                render_product_specs(selected)
                render_quote_controls()
        st.markdown('</div>', unsafe_allow_html=True)

    with right_col:
        st.markdown('<div class="quote-column-marker"></div><div class="quote-pane">', unsafe_allow_html=True)
        render_quote_panel(get_selected_product(df), params)
        st.markdown('</div>', unsafe_allow_html=True)
    return params


def render_bottom_tools(df: pd.DataFrame, params: dict[str, Any]) -> None:
    """渲染批量报价、产品数据库和 Excel 模板。"""
    st.markdown('<div class="tool-card">', unsafe_allow_html=True)
    tab_batch, tab_data, tab_template = st.tabs(["批量报价", "产品数据库", "Excel 模板"])

    with tab_batch:
        st.markdown('<p class="page-sub">以当前全局参数对所有产品生成报价汇总表。</p>', unsafe_allow_html=True)
        col_1, col_2, col_3 = st.columns(3, gap="small")
        with col_1:
            batch_plating = st.selectbox("电镀", list(PLATING_RATES.keys()), key="batch_plating")
        with col_2:
            batch_destination = st.selectbox("目的地", list(FREIGHT_RATES.keys()), key="batch_destination")
        with col_3:
            batch_quantity = st.number_input("数量", min_value=1, value=500, key="batch_quantity")
        if st.button("生成全产品报价表", key="batch_generate", icon=":material/table_view:"):
            rows = []
            for _, product in df.iterrows():
                quote = calculate_quote(
                    product,
                    copper_price=params["copper_price"],
                    plating=batch_plating,
                    packaging=[],
                    quantity=int(batch_quantity),
                    destination=batch_destination,
                    currency=params["currency"],
                    exchange_rate=params["exchange_rate"],
                    box_l=params["box_l"],
                    box_w=params["box_w"],
                    box_h=params["box_h"],
                    units_per_box=int(params["units_per_box"]),
                )
                rows.append(
                    {
                        "产品名称": product["产品名称"],
                        "系列": product["系列"],
                        "净铜重(g)": product["净铜重_g"],
                        "原材料(元)": quote["原材料"],
                        "加工+配件(元)": quote["加工配件"],
                        "电镀(元)": quote["电镀"],
                        "运费(元)": quote["运费"],
                        "利润(元)": quote["利润"],
                        "RMB单价": quote["rmb"],
                        f"{params['currency']}单价": quote["fgn"],
                        "利润率(%)": quote["margin"],
                    }
                )
            batch_df = pd.DataFrame(rows)
            st.dataframe(batch_df, use_container_width=True, hide_index=True)
            csv = batch_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("下载 CSV", data=csv, file_name=f"阀芯报价_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv")

    with tab_data:
        display_cols = ["产品名称", "系列", "产品总重_g", "配件重量_g", "净铜重_g", "加工费_元", "利润_元"]
        if "图片路径" in df.columns:
            display_cols.append("图片路径")
        if "总重是否已称量" in df.columns:
            display_cols.append("总重是否已称量")
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

    with tab_template:
        st.markdown('<p class="page-sub">下载模板后只需新增或修改 Excel 行，网页会按表格内容动态渲染产品卡片。</p>', unsafe_allow_html=True)
        template = pd.DataFrame(
            {
                "产品名称": ["示例产品A", "示例产品B"],
                "系列": ["快开", "慢开"],
                "产品总重_g": [65, 50],
                "配件重量_g": [7, 2],
                "净铜重_g": [58, 48],
                "加工费_元": [0.75, 0.60],
                "利润_元": [0.50, 0.40],
                "图片路径": ["data/images/示例产品A.png", ""],
                "总重是否已称量": ["已称量", "估算值"],
            }
        )
        buffer = io.BytesIO()
        template.to_excel(buffer, index=False)
        st.download_button(
            "下载 Excel 模板",
            data=buffer.getvalue(),
            file_name="产品明细表_模板.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.dataframe(template, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_footer() -> None:
    st.markdown(
        f"<div style='text-align:center;color:#98A2B3;font-size:.66rem;padding:1.2rem 0;'>ValveCore Pricing {APP_VERSION} · 产品参数来自 ./data/products.xlsx · 汇率含 {int((1-EXCHANGE_RATE_MARGIN)*100)}% 安全边际</div>",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════
# 应用入口
# ═══════════════════════════════════════════════════════════
def main() -> None:
    inject_css()
    init_session_state()
    require_login()

    data_file = st.session_state.custom_excel_path or str(DEFAULT_PRODUCTS_FILE)
    try:
        products_df = load_products(data_file)
    except Exception as exc:
        st.error(f"产品数据库加载失败：{exc}")
        st.stop()

    ensure_valid_selection(products_df)
    header_params = {
        "copper_price": st.session_state.copper_price,
        "currency": st.session_state.currency,
        "exchange_rate": st.session_state.exchange_rate,
    }
    render_header(products_df, header_params)
    # 左侧参数栏会返回最新参数，因此工作台主体在 render_workbench 内统一渲染。
    params = {
        "copper_price": st.session_state.copper_price,
        "currency": st.session_state.currency,
        "exchange_rate": st.session_state.exchange_rate,
        "box_l": st.session_state.box_l,
        "box_w": st.session_state.box_w,
        "box_h": st.session_state.box_h,
        "units_per_box": st.session_state.units_per_box,
    }
    params = render_workbench(products_df, params)
    render_bottom_tools(products_df, params)
    render_footer()


if __name__ == "__main__":
    main()
