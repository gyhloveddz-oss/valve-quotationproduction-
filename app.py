"""
成宁阀芯报价工作台 · Streamlit Cloud 生产版

本文件是面向 Streamlit Cloud 的完整单文件入口。设计重点如下：
1. 页面主工作区强制使用 st.columns([1.1, 3.0, 1.4])，保证左侧参数栏、中间产品矩阵、右侧报价栏比例稳定。
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
    """注入 Linear / Notion 风格的灰白专业视觉系统。"""
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,400;14..32,500;14..32,600;14..32,700;14..32,800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&display=swap');

:root {
  --bg:#F8F9FA;
  --panel:#FFFFFF;
  --soft:#F3F5F8;
  --line:#E6E9EF;
  --line-strong:#D8DEE8;
  --text:#1F2937;
  --muted:#667085;
  --subtle:#98A2B3;
  --purple:#6D5DFB;
  --purple-soft:#F1EFFF;
  --green:#12B76A;
  --yellow:#F79009;
  --red:#F04438;
  --shadow:0 2px 8px rgba(0,0,0,0.05);
  --shadow-hover:0 14px 30px rgba(15,23,42,0.09);
  --radius:18px;
  --font:'Inter','PingFang SC','Microsoft YaHei',-apple-system,BlinkMacSystemFont,sans-serif;
  --mono:'JetBrains Mono','SF Mono','Consolas',monospace;
}
*, *::before, *::after { box-sizing:border-box; }
html, body, .stApp, .main, button, input, textarea, select, label, p, div, span { font-family:var(--font); }
[data-testid="stIconMaterial"], .material-icons, .material-symbols-rounded, .material-symbols-outlined, span[class*="material"], i[class*="material"] { font-family:'Material Symbols Rounded','Material Symbols Outlined','Material Icons' !important; font-weight:normal !important; font-style:normal !important; font-size:18px !important; line-height:1 !important; letter-spacing:normal !important; text-transform:none !important; display:inline-flex !important; white-space:nowrap !important; word-wrap:normal !important; direction:ltr !important; -webkit-font-feature-settings:'liga' !important; -webkit-font-smoothing:antialiased !important; }
.stApp { background:var(--bg) !important; color:var(--text) !important; overflow-x:hidden !important; }
#MainMenu, footer, header[data-testid="stHeader"], .stDeployButton, [data-testid="stToolbar"] { display:none !important; }
.main .block-container { max-width:none !important; padding:82px 2.1rem 1.8rem 2.1rem !important; }
hr { border-color:var(--line) !important; margin:1rem 0 !important; }

/* 固定顶部页眉 */
.vc-header { position:fixed; z-index:1000; top:0; left:0; right:0; height:56px; display:flex; align-items:center; justify-content:space-between; padding:0 2rem; background:rgba(255,255,255,.96); border-bottom:1px solid var(--line); box-shadow:var(--shadow); backdrop-filter:blur(14px); }
.vc-brand { display:flex; align-items:center; gap:10px; min-width:0; }
.vc-logo { width:28px; height:28px; border-radius:9px; display:flex; align-items:center; justify-content:center; color:#fff; font-size:.82rem; font-weight:800; background:linear-gradient(135deg,#7C3AED,#4F46E5); box-shadow:0 8px 18px rgba(109,93,251,.22); }
.vc-title { color:var(--text); font-size:.95rem; font-weight:800; letter-spacing:-.02em; white-space:nowrap; }
.vc-subtitle { display:none; }
.status-row { display:flex; gap:8px; align-items:center; overflow-x:auto; }
.status-chip { display:inline-flex; align-items:center; gap:6px; padding:5px 10px; border:1px solid var(--line); border-radius:999px; background:#fff; color:#344054; font-size:.68rem; font-weight:650; white-space:nowrap; box-shadow:0 1px 2px rgba(15,23,42,.035); }
.dot { width:7px; height:7px; border-radius:999px; display:inline-block; }
.dot-green { background:var(--green); box-shadow:0 0 0 3px rgba(18,183,106,.11); }
.dot-yellow { background:var(--yellow); box-shadow:0 0 0 3px rgba(247,144,9,.11); }

/* 三段式布局：用户指定比例由 st.columns([1.1, 3.0, 1.4]) 实现 */
.left-pane, .workbench-pane, .quote-pane { width:100%; max-width:100%; min-width:0; }
.workbench-pane { padding:0 .4rem; overflow:visible; }
.quote-pane { min-width:330px; position:sticky; top:74px; align-self:flex-start; }
div[data-testid="stHorizontalBlock"] { align-items:flex-start !important; }

/* 基础控件：绝不禁用 pointer-events，确保数量输入可手动编辑 */
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div:first-child, textarea { background:#fff !important; border:1px solid var(--line) !important; border-radius:12px !important; box-shadow:0 1px 2px rgba(15,23,42,.03) !important; }
div[data-baseweb="input"] input, .stNumberInput input, textarea { color:var(--text) !important; font-family:var(--mono) !important; pointer-events:auto !important; user-select:text !important; }
label, [data-testid="stWidgetLabel"] { color:var(--muted) !important; font-weight:650 !important; }
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button { border-radius:12px !important; border:1px solid var(--line) !important; background:#fff !important; color:#344054 !important; font-weight:750 !important; box-shadow:0 1px 2px rgba(15,23,42,.035) !important; transition:all .16s ease !important; }
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover { border-color:#B8BDFD !important; color:var(--purple) !important; background:#FBFAFF !important; transform:translateY(-1px); }

/* 左侧参数 */
.side-panel { background:#fff; border:1px solid var(--line); border-radius:18px; padding:16px; box-shadow:var(--shadow); }
.side-title { font-size:.95rem; font-weight:800; color:var(--text); margin-bottom:2px; }
.side-sub { color:var(--muted); font-size:.72rem; line-height:1.55; margin-bottom:14px; }
.sb-label { display:block; color:#475467; font-size:.72rem; font-weight:800; letter-spacing:.04em; margin:.72rem 0 .38rem; }
.sb-hint { color:var(--muted); font-size:.7rem; line-height:1.55; margin:.38rem 0 .15rem; }
.box-hint { text-align:center; font-family:var(--mono) !important; padding:8px 10px; border-radius:10px; background:var(--soft); border:1px solid var(--line); color:#667085; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.upload-center { width:100%; display:flex; justify-content:center; align-items:center; }
div[data-testid="stVerticalBlock"]:has(.upload-center) [data-testid="stFileUploaderDropzone"] { display:flex !important; align-items:center !important; justify-content:center !important; text-align:center !important; min-height:86px !important; border:1px dashed var(--line-strong) !important; border-radius:14px !important; background:#FBFCFE !important; }
div[data-testid="stVerticalBlock"]:has(.upload-center) [data-testid="stFileUploaderDropzone"] svg, div[data-testid="stVerticalBlock"]:has(.upload-center) [data-testid="stFileUploaderDropzone"] [data-testid="stIconMaterial"] { display:none !important; }
.version-box { margin-top:16px; padding:12px; border:1px solid var(--line); border-radius:14px; background:var(--soft); text-align:center; }
.version-text { color:#344054; font-family:var(--mono) !important; font-size:.72rem; font-weight:800; }

/* 中间工作区 */
.page-title { font-size:1.15rem; font-weight:850; color:var(--text); letter-spacing:-.025em; margin:.15rem 0 .35rem; }
.page-sub { color:var(--muted); font-size:.8rem; line-height:1.65; margin-bottom:1rem; }
.section-card { background:#fff; border:1px solid var(--line); border-radius:22px; padding:18px; box-shadow:var(--shadow); }
	.breadcrumb-anchor { width:0; height:0; overflow:hidden; }
	div[data-testid="stVerticalBlock"]:has(.breadcrumb-anchor) [data-testid="stHorizontalBlock"] { align-items:center !important; }
	div[data-testid="stVerticalBlock"]:has(.breadcrumb-anchor) [data-testid="column"] { display:flex !important; align-items:center !important; min-height:36px !important; padding-top:0 !important; padding-bottom:0 !important; }
	div[data-testid="stVerticalBlock"]:has(.breadcrumb-anchor) .stButton { margin:0 !important; width:100% !important; }
	div[data-testid="stVerticalBlock"]:has(.breadcrumb-anchor) .stButton > button,
	.breadcrumb-current-text { height:34px !important; min-height:34px !important; padding:0 14px !important; margin:0 !important; display:inline-flex !important; align-items:center !important; justify-content:center !important; line-height:34px !important; font-size:14px !important; color:#475467 !important; background:#FFFFFF !important; border:1px solid var(--line-strong) !important; border-radius:12px !important; transform:none !important; box-shadow:0 1px 2px rgba(15,23,42,.035) !important; font-weight:750 !important; white-space:nowrap !important; vertical-align:middle !important; box-sizing:border-box !important; }
	div[data-testid="stVerticalBlock"]:has(.breadcrumb-anchor) .stButton > button:hover { transform:none !important; color:#475467 !important; border-color:var(--line-strong) !important; background:#FFFFFF !important; }
	.breadcrumb-current-text { width:100%; overflow:hidden; text-overflow:ellipsis; }
	.breadcrumb-current-text p, .breadcrumb-sep-text p { margin:0 !important; padding:0 !important; line-height:34px !important; }
	.breadcrumb-sep-text { display:inline-flex !important; align-items:center !important; justify-content:center !important; height:34px !important; min-height:34px !important; color:#667085 !important; font-weight:750 !important; font-size:14px !important; line-height:34px !important; text-align:center !important; padding:0 !important; margin:0 !important; vertical-align:middle !important; }

/* 首页系列卡 */
.series-card { min-height:210px; display:flex; flex-direction:column; justify-content:center; align-items:center; gap:10px; text-align:center; background:#fff; border:1px solid var(--line); border-radius:22px; padding:26px; box-shadow:var(--shadow); transition:none; }
.series-card:hover { border-color:var(--line); box-shadow:var(--shadow); transform:none; }
.series-icon { width:44px; height:44px; border-radius:15px; display:flex; align-items:center; justify-content:center; background:var(--purple-soft); color:var(--purple); font-size:1.2rem; font-weight:900; }
.series-title { font-size:1.15rem; font-weight:850; color:var(--text); }
.series-desc { color:#475467; font-size:.84rem; line-height:1.6; max-width:300px; }
.series-count { color:var(--text); font-size:.82rem; font-weight:800; }
div[data-testid="stMarkdownContainer"]:has(.series-hit-marker) + div.stButton > button, div[data-testid="stMarkdownContainer"]:has(.series-hit-marker) + div[data-testid="stButton"] > button { margin-top:10px !important; height:40px !important; min-height:40px !important; opacity:1 !important; position:relative !important; z-index:1 !important; }

/* 产品卡网格 */
.products-note { color:var(--muted); font-size:.78rem; margin-bottom:14px; }
.product-card { min-height:212px; background:#fff; border:1px solid var(--line); border-radius:20px; padding:14px; box-shadow:var(--shadow); transition:none; overflow:hidden; }
.product-card:hover { border-color:var(--line); box-shadow:var(--shadow); transform:none; }
.product-card.selected { border:2px solid var(--purple); box-shadow:0 0 0 4px rgba(109,93,251,.10), var(--shadow-hover); }
.product-img-wrap { height:148px; border-radius:16px; background:linear-gradient(135deg,#F7F8FB,#FFFFFF); border:1px solid var(--line); display:flex; align-items:center; justify-content:center; overflow:hidden; }
.product-img { width:100%; height:100%; object-fit:contain; display:block; }
.product-name { margin-top:12px; color:var(--text); font-size:.94rem; font-weight:850; line-height:1.3; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; text-align:center; }
.product-check { position:absolute; top:10px; right:10px; width:22px; height:22px; border-radius:999px; display:flex; align-items:center; justify-content:center; background:var(--purple); color:#fff; font-size:.72rem; font-weight:900; }
div[data-testid="stVerticalBlock"]:has(.product-card) .stButton > button { margin-top:10px !important; height:40px !important; min-height:40px !important; font-size:.86rem !important; justify-content:center !important; display:flex !important; align-items:center !important; color:#4F46E5 !important; background:#FFFFFF !important; border:1px solid #B8BDFD !important; border-radius:12px !important; font-weight:850 !important; opacity:1 !important; visibility:visible !important; box-shadow:0 1px 3px rgba(79,70,229,.10) !important; }

div[data-testid="stVerticalBlock"]:has(.product-card) .stButton > button:hover { color:#FFFFFF !important; background:var(--purple) !important; border-color:var(--purple) !important; }

div[data-testid="stVerticalBlock"]:has(.side-panel) .stButton > button { color:#475467 !important; background:#FFFFFF !important; border:1px solid var(--line-strong) !important; opacity:1 !important; visibility:visible !important; font-weight:800 !important; }

/* 规格、控制、报价 */
.spec-strip { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin:16px 0; }
.spec-cell, .metric-tile { background:#FBFCFE; border:1px solid var(--line); border-radius:16px; padding:14px; box-shadow:0 1px 2px rgba(15,23,42,.03); }
.sc-label, .mt-label, .ot-label, .ph-label { color:var(--muted); font-size:.66rem; font-weight:800; letter-spacing:.04em; }
.sc-val, .mt-val { margin-top:5px; color:#101828; font-family:var(--mono) !important; font-size:1.02rem; font-weight:850; white-space:nowrap; }
.sc-sub, .mt-sub { color:var(--subtle); font-size:.66rem; margin-top:3px; }
.controls-card { background:#fff; border:1px solid var(--line); border-radius:18px; padding:16px; box-shadow:var(--shadow); margin-top:14px; }
.quote-card { background:#fff; border:1px solid var(--line); border-radius:22px; padding:18px; box-shadow:0 16px 34px rgba(15,23,42,.07); min-width:330px; overflow:hidden; }
.empty-quote { min-height:360px; display:flex; align-items:center; justify-content:center; text-align:center; }
.empty-icon { width:52px; height:52px; display:inline-flex; align-items:center; justify-content:center; border-radius:16px; background:var(--purple-soft); color:var(--purple); margin-bottom:12px; font-weight:900; }
.panel-kicker { display:flex; justify-content:space-between; gap:8px; color:var(--muted); font-size:.66rem; font-weight:800; letter-spacing:.06em; margin-bottom:10px; }
.panel-product { font-size:1.05rem; font-weight:850; color:var(--text); margin-bottom:12px; }
.price-hero { border:1px solid #E8E7FF; border-radius:18px; padding:18px; background:linear-gradient(135deg,#FFFFFF 0%,#F7F6FF 100%); }
.ph-row { display:flex; align-items:center; justify-content:space-between; gap:10px; }
.ph-currency { color:#667085; font-size:.72rem; white-space:nowrap; }
.ph-amount { margin-top:8px; color:#101828; font-family:var(--mono) !important; font-size:28px; font-weight:850; letter-spacing:-.04em; line-height:1.08; white-space:nowrap; text-align:left !important; }
.ph-rmb { margin-top:7px; color:#344054; font-family:var(--mono) !important; font-size:.88rem; font-weight:800; text-align:left !important; }
.ph-sub { margin-top:12px; padding-top:10px; border-top:1px solid var(--line); color:#667085; font-size:.66rem; line-height:1.55; }
.metric-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin:12px 0; }
.order-total { background:linear-gradient(135deg,#F7F5FF,#FFFFFF); border:1px solid #E4E0FF; border-radius:18px; padding:16px; margin-bottom:12px; text-align:left !important; }
.ot-val { color:var(--purple); font-family:var(--mono) !important; font-size:1.45rem; font-weight:850; white-space:nowrap; margin-top:6px; text-align:left !important; }
.ot-sub { color:#667085; font-family:var(--mono) !important; font-size:.66rem; margin-top:4px; white-space:nowrap; text-align:left !important; }
.margin-row { display:flex; align-items:center; justify-content:space-between; gap:8px; padding:12px 0; border-top:1px solid var(--line); }
.margin-label { color:#475467; font-size:.76rem; font-weight:800; }
.margin-pill { display:inline-flex; padding:5px 10px; border-radius:999px; font-family:var(--mono) !important; font-size:.72rem; font-weight:850; white-space:nowrap; }
.mp-good { color:#067647; background:#ECFDF3; border:1px solid #ABEFC6; }
.mp-warn { color:#B54708; background:#FFFAEB; border:1px solid #FEDF89; }
.mp-danger { color:#B42318; background:#FEF3F2; border:1px solid #FECDCA; }
.cost-row { display:grid; grid-template-columns:8px minmax(64px,1fr) 76px 42px; gap:8px; align-items:center; padding:8px 0; border-bottom:1px solid var(--line); }
.cost-dot { width:8px; height:8px; border-radius:999px; }
.cost-name { color:#475467; font-size:.72rem; font-weight:700; white-space:nowrap; }
.cost-val { color:#101828; font-family:var(--mono) !important; font-size:.72rem; text-align:right; white-space:nowrap; }
.cost-pct { color:#98A2B3; font-size:.66rem; text-align:right; white-space:nowrap; }
.formula { padding:12px; border:1px solid var(--line); border-radius:12px; background:#fff; color:#475467; font-size:.72rem; font-weight:500; line-height:1.65; white-space:normal; }
.formula-title { color:#101828; font-size:.76rem; font-weight:850; margin-bottom:8px; }
.formula-line { display:flex; justify-content:space-between; gap:12px; padding:6px 0; border-bottom:1px dashed #EAECF0; }
.formula-line:last-child { border-bottom:0; }
.formula-label { color:#667085; white-space:nowrap; }
.formula-value { color:#101828; font-family:var(--mono) !important; font-weight:800; text-align:right; }
.formula-eq { margin-top:8px; padding:10px; border-radius:10px; background:#F9FAFB; color:#344054; font-family:var(--mono) !important; font-size:.68rem; line-height:1.7; }
div[data-testid="stExpander"]:has(.formula) { margin-top:10px !important; border:1px solid var(--line) !important; border-radius:14px !important; background:#fff !important; box-shadow:0 1px 2px rgba(15,23,42,.03) !important; }
div[data-testid="stExpander"]:has(.formula) summary { font-size:.76rem !important; font-weight:850 !important; color:#475467 !important; }
.tool-card { background:#fff; border:1px solid var(--line); border-radius:22px; padding:18px; box-shadow:var(--shadow); margin-top:18px; }
.login-shell { max-width:420px; margin:12vh auto 1.5rem; padding:30px; border:1px solid var(--line); border-radius:22px; background:#fff; box-shadow:var(--shadow); }
.login-title { font-size:1.2rem; font-weight:850; color:var(--text); margin-bottom:4px; }
.login-sub { color:var(--muted); font-size:.82rem; line-height:1.65; }
[data-baseweb="tag"] { background:#FFFFFF !important; background-color:#FFFFFF !important; color:#475467 !important; border:1px solid var(--line-strong) !important; border-radius:8px !important; box-shadow:0 1px 2px rgba(15,23,42,.03) !important; }
[data-baseweb="tag"] > span,
[data-baseweb="tag"] span { color:#475467 !important; font-weight:700 !important; }
[data-baseweb="tag"] svg,
[data-baseweb="tag"] path { color:#667085 !important; fill:#667085 !important; }
[data-testid="stDataFrame"] * { font-family:var(--mono) !important; }
@media (max-width: 1180px) { .main .block-container { padding-left:1rem !important; padding-right:1rem !important; } .quote-pane, .quote-card { min-width:300px; } .product-img-wrap { height:120px; } }
@media (max-width: 980px) { .quote-pane { position:relative; top:auto; min-width:100%; } .spec-strip, .metric-grid { grid-template-columns:1fr; } .vc-header { padding:0 1rem; } }
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
# UI 渲染层：单页面专业生产力工作台
# ═══════════════════════════════════════════════════════════
def render_sidebar_controls() -> dict[str, Any]:
    """渲染左侧报价参数栏，保留所有输入框手动编辑能力。"""
    st.markdown('<div class="left-pane"><div class="side-panel"><div class="side-title">报价参数</div><div class="side-sub">铜价、汇率与箱规在此统一管理。</div>', unsafe_allow_html=True)

    st.markdown('<span class="sb-label">铜价（元/吨）</span>', unsafe_allow_html=True)
    copper_price = st.number_input("铜价", min_value=40000, max_value=150000, value=int(st.session_state.copper_price), step=100, label_visibility="collapsed")
    st.session_state.copper_price = copper_price
    if st.button("更新铜价", key="sync_copper", use_container_width=True):
        with st.spinner("同步铜价中..."):
            result = cached_copper_price()
            st.session_state.copper_price = float(result.get("price", DEFAULT_COPPER_PRICE))
            st.session_state.copper_source = result.get("source", "实时源")
        st.rerun()

    st.divider()
    st.markdown('<span class="sb-label">报价货币</span>', unsafe_allow_html=True)
    currency_options = ["USD", "EUR", "AED", "SAR", "MYR", "BRL", "NGN", "RMB"]
    currency_labels = {"USD":"$ USD · 美元","EUR":"€ EUR · 欧元","AED":"AED · 迪拉姆","SAR":"SAR · 里亚尔","MYR":"RM MYR · 林吉特","BRL":"R$ BRL · 雷亚尔","NGN":"₦ NGN · 奈拉","RMB":"¥ RMB · 人民币"}
    currency = st.selectbox("报价货币", currency_options, format_func=lambda item: currency_labels.get(item, item), index=currency_options.index(st.session_state.currency) if st.session_state.currency in currency_options else 0, label_visibility="collapsed")
    st.session_state.currency = currency
    default_rate = st.session_state.rates.get(currency, DEFAULT_RATES.get(currency, 1.0)) if currency != "RMB" else 1.0
    exchange_rate = st.number_input("汇率", min_value=0.0001, max_value=100.0, value=float(default_rate), step=0.01, format="%.4f", disabled=(currency == "RMB"), label_visibility="collapsed")
    st.session_state.exchange_rate = exchange_rate
    if currency != "RMB":
        effective_rate = round(exchange_rate * EXCHANGE_RATE_MARGIN, 4)
        st.markdown(f'<p class="sb-hint">报价汇率 = {exchange_rate} × {EXCHANGE_RATE_MARGIN} = <b>{effective_rate}</b></p>', unsafe_allow_html=True)
    if st.button("更新汇率", key="sync_rates", use_container_width=True):
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
    st.markdown('<span class="sb-label">数据管理</span><div class="upload-center"></div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("上传 XLSX 产品表", type=["xlsx"], label_visibility="collapsed")
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

    st.markdown('</div></div>', unsafe_allow_html=True)
    return {"copper_price": copper_price, "currency": currency, "exchange_rate": exchange_rate, "box_l": box_l, "box_w": box_w, "box_h": box_h, "units_per_box": units_per_box}


def render_header(df: pd.DataFrame, params: dict[str, Any]) -> None:
    now = datetime.now().strftime("%H:%M")
    copper_dot = "dot-green" if st.session_state.copper_source != "默认值" else "dot-yellow"
    rate_dot = "dot-green" if st.session_state.rates.get("_success") else "dot-yellow"
    st.markdown(f"""
    <div class="vc-header">
      <div class="vc-brand"><div class="vc-logo">成</div><div><div class="vc-title">{APP_NAME}</div><div class="vc-subtitle">{APP_SUBTITLE}</div></div></div>
      <div class="status-row">
        <span class="status-chip"><span class="dot {copper_dot}"></span>铜价 ¥{params['copper_price']:,.0f}</span>
        <span class="status-chip"><span class="dot {rate_dot}"></span>{params['currency']} {params['exchange_rate']}</span>
        <span class="status-chip"><span class="dot dot-green"></span>{len(df)} 产品 · {now}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_breadcrumb(product: pd.Series | None = None) -> None:
    """渲染可点击面包屑，允许从产品页返回当前系列或所有系列。"""
    selected_cat = st.session_state.selected_cat
    product_label = html.escape(str(product["产品名称"])) if product is not None else "产品列表"
    cat_label = f"{selected_cat}系列" if selected_cat else "选择系列"

    st.markdown('<div class="breadcrumb-anchor"></div>', unsafe_allow_html=True)
    crumb_cols = st.columns([0.90, 0.08, 0.95, 0.08, 2.20, 5.00], gap="small")
    with crumb_cols[0]:
        if st.button("所有系列", key="crumb_all_click", use_container_width=True):
            reset_to_home()
    with crumb_cols[1]:
        st.markdown('<div class="breadcrumb-sep-text">/</div>', unsafe_allow_html=True)
    with crumb_cols[2]:
        if st.button(cat_label, key="crumb_cat_click", use_container_width=True, disabled=not bool(selected_cat)):
            st.session_state.page = "collection"
            st.session_state.selected_prod = None
            st.rerun()
    with crumb_cols[3]:
        st.markdown('<div class="breadcrumb-sep-text">/</div>', unsafe_allow_html=True)
    with crumb_cols[4]:
        st.markdown(f'<div class="breadcrumb-current-text">{product_label}</div>', unsafe_allow_html=True)


def product_image_src(product_row: pd.Series) -> str:
    explicit_path = resolve_relative_path(product_row.get("图片路径", ""))
    candidates: list[Path] = []
    if explicit_path:
        candidates.append(explicit_path)
    product_name = str(product_row.get("产品名称", ""))
    for stem in [safe_filename(product_name), product_name]:
        for suffix in [".png", ".jpg", ".jpeg", ".webp"]:
            candidates.append(IMG_DIR / f"{stem}{suffix}")
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            mime = "image/png"
            if candidate.suffix.lower() in {".jpg", ".jpeg"}:
                mime = "image/jpeg"
            elif candidate.suffix.lower() == ".webp":
                mime = "image/webp"
            encoded = base64.b64encode(candidate.read_bytes()).decode("utf-8")
            return f"data:{mime};base64,{encoded}"
    name = html.escape(product_name[:8] or "产品")
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="320" height="220" viewBox="0 0 320 220"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#F7F8FB"/><stop offset="1" stop-color="#EEF2F7"/></linearGradient></defs><rect width="320" height="220" rx="24" fill="url(#g)"/><circle cx="160" cy="92" r="42" fill="#F1EFFF"/><path d="M160 64l28 28-28 28-28-28z" fill="#6D5DFB" opacity=".86"/><text x="160" y="168" text-anchor="middle" font-family="Arial, sans-serif" font-size="20" font-weight="700" fill="#667085">{name}</text></svg>"""
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("utf-8")


def render_category_selector(df: pd.DataFrame) -> None:
    st.markdown('<div class="page-title">选择产品系列</div><div class="page-sub">选择阀芯类型，进入产品图片矩阵与实时报价工作台。</div>', unsafe_allow_html=True)
    categories = list(df["系列"].dropna().astype(str).unique())
    cols = st.columns(max(1, min(2, len(categories))), gap="large")
    for idx, category in enumerate(categories):
        count = int((df["系列"].astype(str) == str(category)).sum())
        with cols[idx % len(cols)]:
            icon = "快" if "快" in category else "芯"
            st.markdown(f"""
            <div class="series-card">
              <div class="series-icon">{icon}</div>
              <div class="series-title">{html.escape(category)}系列</div>
              <div class="series-desc">进入{html.escape(category)}阀芯产品矩阵，实时选择产品并生成报价。</div>
              <div class="series-count">{count} 款产品</div>
            </div><div class="series-hit-marker"></div>
            """, unsafe_allow_html=True)
            if st.button("打开", key=f"series_hit_{idx}_{category}", use_container_width=True):
                open_collection(category, df, select_first=False)


def get_selected_product(df: pd.DataFrame) -> pd.Series | None:
    product_name = st.session_state.selected_prod
    if not product_name:
        return None
    matched = df[df["产品名称"].astype(str) == str(product_name)]
    if matched.empty:
        return None
    return matched.iloc[0]


def render_product_grid(df: pd.DataFrame) -> None:
    selected_cat = st.session_state.selected_cat
    cat_df = df[df["系列"].astype(str) == str(selected_cat)].reset_index(drop=True) if selected_cat else df.reset_index(drop=True)
    st.markdown(f'<div class="products-note">当前系列：<b>{html.escape(str(selected_cat or "全部"))}</b>。产品卡片仅保留图片与名称，选择后右侧实时生成报价。</div>', unsafe_allow_html=True)
    if cat_df.empty:
        st.markdown('<div class="products-note">暂无产品数据。</div>', unsafe_allow_html=True)
        return
    grid_cols = st.columns(4 if len(cat_df) >= 4 else max(1, len(cat_df)), gap="large")
    for idx, (_, product) in enumerate(cat_df.iterrows()):
        selected = str(st.session_state.selected_prod) == str(product["产品名称"])
        img_src = product_image_src(product)
        with grid_cols[idx % len(grid_cols)]:
            check = '<div class="product-check">✓</div>' if selected else ''
            st.markdown(f"""
            <div class="product-card {'selected' if selected else ''}" style="position:relative;">
              {check}
              <div class="product-img-wrap"><img class="product-img" src="{img_src}" alt="{html.escape(str(product['产品名称']))}" /></div>
              <div class="product-name">{html.escape(str(product['产品名称']))}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("选择", key=f"prod_select_{selected_cat}_{idx}_{product['产品名称']}", use_container_width=True):
                open_product(str(product["系列"]), str(product["产品名称"]))


def render_product_specs(product: pd.Series) -> None:
    total_g = float(product.get("产品总重_g", 0) or 0)
    accessory_g = float(product.get("配件重量_g", 0) or 0)
    net_g = float(product.get("净铜重_g", 0) or 0)
    st.markdown(f"""
    <div class="spec-strip">
      <div class="spec-cell"><div class="sc-label">产品总重</div><div class="sc-val">{total_g:.1f}g</div><div class="sc-sub">称量口径</div></div>
      <div class="spec-cell"><div class="sc-label">配件重量</div><div class="sc-val">{accessory_g:.1f}g</div><div class="sc-sub">扣除非铜件</div></div>
      <div class="spec-cell"><div class="sc-label">净铜重</div><div class="sc-val">{net_g:.1f}g</div><div class="sc-sub">报价核心参数</div></div>
    </div>
    """, unsafe_allow_html=True)


def render_quote_controls() -> None:
    c1, c2, c3 = st.columns([1.15, 1.25, 1.0], gap="medium")
    with c1:
        plating_options = list(PLATING_RATES.keys())
        st.session_state.plating = st.selectbox("电镀", plating_options, index=plating_options.index(st.session_state.plating) if st.session_state.plating in plating_options else 0)
    with c2:
        pack_options = list(PACKAGING_FEES.keys())
        st.session_state.packaging = st.multiselect("包装", pack_options, default=st.session_state.packaging)
    with c3:
        st.session_state.quantity = st.number_input("订单数量", min_value=1, value=int(st.session_state.quantity), step=100)
    destinations = list(FREIGHT_RATES.keys())
    st.session_state.destination = st.selectbox("目的地", destinations, index=destinations.index(st.session_state.destination) if st.session_state.destination in destinations else 0)


def render_quote_panel(product: pd.Series | None, params: dict[str, Any]) -> None:
    st.markdown('<div class="quote-pane">', unsafe_allow_html=True)
    if product is None:
        st.markdown("""<div class="quote-card empty-quote"><div><div class="empty-icon">◆</div><div class="panel-product">开始报价</div><div style="color:#667085;font-size:.78rem;">先选择产品系列，然后选择具体产品。</div></div></div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        return

    quote = calculate_quote(product, params["copper_price"], st.session_state.plating, st.session_state.packaging, st.session_state.quantity, st.session_state.destination, params["currency"], params["exchange_rate"], params["box_l"], params["box_w"], params["box_h"], params["units_per_box"])
    symbol = CURRENCY_SYMBOLS.get(params["currency"], params["currency"])
    margin_cls = "mp-good" if quote["margin"] >= 8 else "mp-warn" if quote["margin"] >= 5 else "mp-danger"
    cost_total = max(quote["rmb"], 0.0001)
    cost_rows = []
    cost_colors = {"原材料":"#F79009","加工配件":"#2E90FA","电镀":"#7A5AF8","包装":"#12B76A","运费":"#6172F3","利润":"#F04438"}
    for name in ["原材料", "加工配件", "电镀", "包装", "运费", "利润"]:
        val = float(quote.get(name, 0))
        pct = val / cost_total * 100
        cost_rows.append(f'<div class="cost-row"><div class="cost-dot" style="background:{cost_colors[name]};"></div><div class="cost-name">{name}</div><div class="cost-val">¥{val:.4f}</div><div class="cost-pct">{pct:.0f}%</div></div>')
    packaging_label = " + ".join(map(str, st.session_state.packaging)) if st.session_state.packaging else "无包装附加费"
    plating_rate = float(PLATING_RATES.get(st.session_state.plating, 0.0))
    freight_rate = float(FREIGHT_RATES.get(st.session_state.destination, 0.0))
    formula_html = f"""
    <div class="formula">
      <div class="formula-title">最终报价推导</div>
      <div class="formula-line"><span class="formula-label">原材料</span><span class="formula-value">{quote['net_g']:.1f}g × ¥{params['copper_price']:,.0f}/吨 ÷ 1,000,000 = ¥{quote['原材料']:.4f}</span></div>
      <div class="formula-line"><span class="formula-label">加工配件</span><span class="formula-value">¥{quote['加工配件']:.4f}</span></div>
      <div class="formula-line"><span class="formula-label">电镀</span><span class="formula-value">{html.escape(str(st.session_state.plating))}，费率 ¥{plating_rate:,.0f}/吨 = ¥{quote['电镀']:.4f}</span></div>
      <div class="formula-line"><span class="formula-label">包装</span><span class="formula-value">{html.escape(packaging_label)} = ¥{quote['包装']:.4f}</span></div>
      <div class="formula-line"><span class="formula-label">运费</span><span class="formula-value">{html.escape(str(st.session_state.destination))}，¥{freight_rate:.2f}/CBM = ¥{quote['运费']:.4f}</span></div>
      <div class="formula-line"><span class="formula-label">利润</span><span class="formula-value">¥{quote['利润']:.4f}</span></div>
      <div class="formula-eq">人民币单价 = 原材料 + 加工配件 + 电镀 + 包装 + 运费 + 利润 = ¥{quote['rmb']:.4f}<br>有效汇率 = {params['exchange_rate']} × {EXCHANGE_RATE_MARGIN} = {quote['eff_rate']:.4f}<br>{params['currency']} 单价 = ¥{quote['rmb']:.4f} ÷ {quote['eff_rate']:.4f} = {symbol}{quote['fgn']:.4f}<br>订单总价 = {symbol}{quote['fgn']:.4f} × {int(st.session_state.quantity)} 只 = {symbol}{quote['total']:,.2f}</div>
    </div>
    """
    st.markdown(f"""
    <div class="quote-card">
      <div class="panel-kicker"><span>QUOTE SUMMARY</span><span>{params['currency']} / 只</span></div>
      <div class="panel-product">{html.escape(str(product['产品名称']))}</div>
      <div class="price-hero"><div class="ph-row"><div class="ph-label">单件报价</div><div class="ph-currency">{params['currency']} / 只</div></div><div class="ph-amount">{symbol}{quote['fgn']:.4f}</div><div class="ph-rmb">¥{quote['rmb']:.4f} RMB</div><div class="ph-sub">汇率 {params['exchange_rate']} × {EXCHANGE_RATE_MARGIN} = {quote['eff_rate']}，含安全边际。</div></div>
      <div class="metric-grid"><div class="metric-tile"><div class="mt-label">人民币单价</div><div class="mt-val">¥{quote['rmb']:.4f}</div><div class="mt-sub">元 / 只</div></div><div class="metric-tile"><div class="mt-label">净铜重</div><div class="mt-val">{quote['net_g']:.1f}g</div><div class="mt-sub">铜价 ¥{params['copper_price']:,.0f}</div></div></div>
      <div class="order-total"><div class="ot-label">订单总价 <span style="float:right;color:#98A2B3;">{int(st.session_state.quantity)} 只</span></div><div class="ot-val">{symbol}{quote['total']:,.2f}</div><div class="ot-sub">{symbol}{quote['fgn']:.4f} × {int(st.session_state.quantity)} {params['currency']}</div></div>
      <div class="margin-row"><div class="margin-label">利润率</div><div class="margin-pill {margin_cls}">+ {quote['margin']:.1f}%</div></div>
      {''.join(cost_rows)}
    </div>
    """, unsafe_allow_html=True)
    with st.expander("计算公式", expanded=False):
        st.markdown(formula_html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_workbench(df: pd.DataFrame, params: dict[str, Any]) -> dict[str, Any]:
    left_col, mid_col, right_col = st.columns([1.1, 3.0, 1.4], gap="large")
    with left_col:
        params = render_sidebar_controls()
    product = get_selected_product(df)
    with mid_col:
        if st.session_state.page == "home":
            render_category_selector(df)
        else:
            render_breadcrumb(product)
            render_product_grid(df)
            if product is not None:
                render_product_specs(product)
                render_quote_controls()
    with right_col:
        render_quote_panel(product, params)
    return params


def render_bottom_tools(df: pd.DataFrame, params: dict[str, Any]) -> None:
    tab_batch, tab_db, tab_template = st.tabs(["批量报价", "产品数据库", "Excel 模板"])
    with tab_batch:
        st.markdown('<p class="page-sub">以当前全局参数对所有产品生成报价汇总表。</p>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1.0, 1.2, 1.0], gap="medium")
        with c1:
            plating = st.selectbox("电镀", list(PLATING_RATES.keys()), key="batch_plating")
        with c2:
            destination = st.selectbox("目的地", list(FREIGHT_RATES.keys()), key="batch_destination")
        with c3:
            qty = st.number_input("数量", min_value=1, value=int(st.session_state.quantity), step=100, key="batch_qty")
        if st.button("生成全产品报价表", use_container_width=True):
            rows = []
            for _, row in df.iterrows():
                q = calculate_quote(row, params["copper_price"], plating, [], int(qty), destination, params["currency"], params["exchange_rate"], params["box_l"], params["box_w"], params["box_h"], params["units_per_box"])
                rows.append({"产品名称": row["产品名称"], "系列": row["系列"], "净铜重(g)": q["net_g"], "原材料(元)": q["原材料"], "加工+配件(元)": q["加工配件"], "电镀(元)": q["电镀"], "运费(元)": q["运费"], "利润(元)": q["利润"], "RMB单价": q["rmb"], f"{params['currency']}单价": q["fgn"], "利润率(%)": q["margin"]})
            result_df = pd.DataFrame(rows)
            st.dataframe(result_df, use_container_width=True, hide_index=True)
            out = io.BytesIO()
            result_df.to_excel(out, index=False)
            st.download_button("下载报价表 Excel", data=out.getvalue(), file_name=f"成宁阀芯报价_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with tab_db:
        st.dataframe(df, use_container_width=True, hide_index=True)
    with tab_template:
        template = pd.DataFrame({"产品名称":["示例产品A","示例产品B"],"系列":["快开","慢开"],"产品总重_g":[65,50],"配件重量_g":[7,2],"净铜重_g":[58,48],"加工费_元":[0.75,0.60],"利润_元":[0.50,0.40],"图片路径":["data/images/示例产品A.png", ""],"总重是否已称量":["已称量","估算值"]})
        buffer = io.BytesIO(); template.to_excel(buffer, index=False)
        st.download_button("下载 Excel 模板", data=buffer.getvalue(), file_name="产品明细表_模板.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.dataframe(template, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_footer() -> None:
    st.markdown(f"<div style='text-align:center;color:#98A2B3;font-size:.66rem;padding:1.2rem 0;'>ValveCore Pricing {APP_VERSION} · 产品参数来自 ./data/products.xlsx · 汇率含 {int((1-EXCHANGE_RATE_MARGIN)*100)}% 安全边际</div>", unsafe_allow_html=True)


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
    header_params = {"copper_price": st.session_state.copper_price, "currency": st.session_state.currency, "exchange_rate": st.session_state.exchange_rate}
    render_header(products_df, header_params)
    params = {"copper_price": st.session_state.copper_price, "currency": st.session_state.currency, "exchange_rate": st.session_state.exchange_rate, "box_l": st.session_state.box_l, "box_w": st.session_state.box_w, "box_h": st.session_state.box_h, "units_per_box": st.session_state.units_per_box}
    params = render_workbench(products_df, params)
    render_bottom_tools(products_df, params)
    render_footer()


if __name__ == "__main__":
    main()
