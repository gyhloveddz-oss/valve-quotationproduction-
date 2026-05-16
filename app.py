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
import streamlit.components.v1 as components

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
    initial_sidebar_state="expanded",
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
  --bg:#F3F4F6;
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
#MainMenu, footer, .stDeployButton { display:none !important; }
	/* 保留 Streamlit 原生 header、toolbar 与 header base button：侧边栏展开/收起按钮位于该区域，不能用通配选择器 display:none 误伤。 */
[data-testid="stHeader"] { display:flex !important; background:transparent !important; box-shadow:none !important; z-index:999 !important; }
	[data-testid="stToolbar"] { display:flex !important; background:transparent !important; box-shadow:none !important; z-index:1000000 !important; }
	[data-testid="stBaseButton-header"] { display:inline-flex !important; visibility:visible !important; opacity:1 !important; pointer-events:auto !important; }

.main .block-container { max-width:none !important; padding:0 2.1rem 1.8rem 2.1rem !important; }
	section[data-testid="stSidebar"] { background:#FFFFFF !important; border-right:1px solid var(--line) !important; }
	section[data-testid="stSidebar"] > div { background:#FFFFFF !important; }
	div[data-testid="stVerticalBlockBorderWrapper"] { border-radius:12px !important; border:1px solid #E5E7EB !important; background:#FFFFFF !important; box-shadow:0 1px 3px 0 rgba(0,0,0,.05) !important; }
	div[data-testid="stVerticalBlockBorderWrapper"] > div { padding:14px !important; }
	section[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"] { margin-bottom:12px !important; }
	section[data-testid="stSidebar"] h4 { margin:0 0 10px 0 !important; padding:0 !important; font-size:.86rem !important; line-height:1.25 !important; }
	section[data-testid="stSidebar"] [data-testid="stNumberInput"] { margin-bottom:4px !important; }
	section[data-testid="stSidebar"] [data-testid="stFileUploader"] { width:100% !important; text-align:center !important; }
	section[data-testid="stSidebar"] [data-testid="stFileUploader"] section { width:100% !important; justify-content:center !important; align-items:center !important; text-align:center !important; }
	section[data-testid="stSidebar"] [data-testid="stFileUploader"] button { margin-left:auto !important; margin-right:auto !important; }
	section[data-testid="stSidebar"] .stButton > button { border-radius:10px !important; }

	/* 独立悬浮侧边栏控制器：由前端桥接脚本插入到父页面，避免只依赖 Streamlit 原生按钮是否渲染。 */
	#vc-sidebar-floating-toggle {
		position: fixed !important;
		top: 15px !important;
		left: 20px !important;
		z-index: 2147483647 !important;
		display: inline-flex !important;
		visibility: visible !important;
		opacity: 1 !important;
		align-items: center !important;
		justify-content: center !important;
		width: 34px !important;
		height: 34px !important;
		min-width: 34px !important;
		min-height: 34px !important;
		padding: 0 !important;
		background: #FFFFFF !important;
		border: 1px solid #E5E7EB !important;
		border-radius: 9px !important;
		box-shadow: 0 6px 18px rgba(15, 23, 42, 0.16) !important;
		color: #111827 !important;
		font-size: 20px !important;
		font-weight: 800 !important;
		line-height: 1 !important;
		cursor: pointer !important;
		pointer-events: auto !important;
		user-select: none !important;
	}
	#vc-sidebar-floating-toggle:hover {
		background: #F3F4F6 !important;
		border-color: #D1D5DB !important;
		transform: translateY(-1px);
	}
	#vc-sidebar-floating-toggle:active { transform: translateY(0); }
	#vc-sidebar-floating-toggle .vc-sidebar-toggle-icon {
		font-family: Arial, Helvetica, sans-serif !important;
		font-size: 22px !important;
		line-height: 1 !important;
		margin-top: -1px !important;
	}

	/* 侧边栏控制器必须保持可见可点：不要隐藏原生 header，也不要用固定顶栏覆盖左上角。 */
	[data-testid="stSidebarCollapseButton"],
	[data-testid="collapsedControl"],
	[data-testid="stExpandSidebarButton"] {
		z-index:2147483647 !important;
		opacity:1 !important;
		visibility:visible !important;
		pointer-events:auto !important;
	}
	/* Streamlit 1.57 收起后的真实展开按钮是 stExpandSidebarButton；将它固定成可见可点的左上角入口。 */
	[data-testid="stExpandSidebarButton"] {
		position:fixed !important;
		left:12px !important;
		top:12px !important;
		width:36px !important;
		height:36px !important;
		min-width:36px !important;
		min-height:36px !important;
		display:inline-flex !important;
		align-items:center !important;
		justify-content:center !important;
		background:#FFFFFF !important;
		border:1px solid #E5E7EB !important;
		border-radius:999px !important;
		box-shadow:0 6px 18px rgba(15,23,42,.14) !important;
		color:#111827 !important;
	}

    /* 1. Force the hidden sidebar toggle button back into existence */
    [data-testid="stSidebarCollapseButton"] {
        position: fixed !important;
        top: 15px !important;       /* Align perfectly with the sticky navbar height */
        left: 20px !important;      /* Force it to float on top of the left edge */
        z-index: 2147483647 !important; /* Ensure it overrides ALL elements, headers, and backgrounds */
        display: flex !important;   /* Guarantee it is not hidden by display: none */
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        
        /* Modern Floating Button UI styling to match our SaaS look */
        background-color: #FFFFFF !important;
        border: 1px solid #E5E7EB !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08) !important;
        padding: 6px !important;
        width: 32px !important;
        height: 32px !important;
        min-width: 32px !important;
        min-height: 32px !important;
        align-items: center !important;
        justify-content: center !important;
    }

    /* Streamlit collapsed-state expand button uses a separate test id in recent versions. */
    [data-testid="stExpandSidebarButton"],
    [data-testid="collapsedControl"] {
        position: fixed !important;
        top: 15px !important;
        left: 20px !important;
        z-index: 2147483647 !important;
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        background-color: #FFFFFF !important;
        border: 1px solid #E5E7EB !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08) !important;
        padding: 6px !important;
        width: 32px !important;
        height: 32px !important;
        min-width: 32px !important;
        min-height: 32px !important;
        align-items: center !important;
        justify-content: center !important;
    }

    /* 2. Fix hover state so it reacts to user interaction */
    [data-testid="stSidebarCollapseButton"]:hover,
    [data-testid="stExpandSidebarButton"]:hover,
    [data-testid="collapsedControl"]:hover {
        background-color: #F3F4F6 !important;
        border-color: #D1D5DB !important;
        cursor: pointer !important;
    }

    /* 3. Safety margin adjustment: Ensure the main container doesn't block the left corner */
    .stApp [data-testid="stHeader"] {
        padding-left: 60px !important; /* Give the toggle button breathing room */
    }
hr { border-color:var(--line) !important; margin:1rem 0 !important; }

	/* 固定顶部栏：玻璃态 SaaS 导航，同时不遮挡 Streamlit 原生与独立悬浮侧边栏入口。 */
.custom-navbar {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 70px;
    background-color: rgba(255, 255, 255, 0.90) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border-bottom: 1px solid #E5E7EB !important;
    z-index: 1000 !important;
    padding: 12px 24px !important;
    box-sizing:border-box !important;
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:12px;
    box-shadow:0 10px 30px rgba(15,23,42,.06);
    pointer-events:none !important;
}
.custom-navbar * { pointer-events:none !important; }
.main-body-container {
    margin-top: 85px !important;
}
.vc-brand { display:flex; align-items:center; gap:10px; min-width:0; margin-left:318px; }
.login-shell .vc-brand { margin-left:0 !important; }
@media (max-width: 980px) { .vc-brand { margin-left:64px; } }
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
.box-hint { display:block; width:100%; text-align:center; font-family:var(--font) !important; margin:10px 0 0 0 !important; padding:9px 12px; border-radius:10px; background:var(--soft); border:1px solid var(--line); color:#667085; white-space:normal; overflow:visible; text-overflow:clip; overflow-wrap:anywhere; line-height:1.55; font-size:.72rem; }
.upload-center { width:100%; display:flex; justify-content:center; align-items:center; margin:0 !important; padding:0 !important; }
div[data-testid="stVerticalBlock"]:has(.upload-center) [data-testid="stFileUploaderDropzone"] { display:flex !important; flex-direction:column !important; align-items:center !important; justify-content:center !important; text-align:center !important; width:100% !important; min-height:92px !important; padding:14px 12px !important; border:1px dashed var(--line-strong) !important; border-radius:14px !important; background:#FBFCFE !important; }
div[data-testid="stVerticalBlock"]:has(.upload-center) [data-testid="stFileUploaderDropzone"] * { text-align:center !important; justify-content:center !important; align-items:center !important; margin-left:auto !important; margin-right:auto !important; }
div[data-testid="stVerticalBlock"]:has(.upload-center) [data-testid="stFileUploaderDropzone"] [data-testid="stFileUploaderDropzoneInstructions"] { width:100% !important; display:flex !important; flex-direction:column !important; align-items:center !important; justify-content:center !important; }
div[data-testid="stVerticalBlock"]:has(.upload-center) [data-testid="stFileUploaderDropzone"] button { margin:0 auto 4px auto !important; display:flex !important; align-items:center !important; justify-content:center !important; min-width:86px !important; }
div[data-testid="stVerticalBlock"]:has(.upload-center) [data-testid="stFileUploaderDropzone"] svg, div[data-testid="stVerticalBlock"]:has(.upload-center) [data-testid="stFileUploaderDropzone"] [data-testid="stIconMaterial"] { display:none !important; }
.version-box { margin-top:16px; padding:12px; border:1px solid var(--line); border-radius:14px; background:var(--soft); text-align:center; }
.version-text { color:#344054; font-family:var(--mono) !important; font-size:.72rem; font-weight:800; }

/* 中间工作区 */
.page-title { font-size:1.15rem; font-weight:850; color:var(--text); letter-spacing:-.025em; margin:.15rem 0 .35rem; }
.page-sub { color:var(--muted); font-size:.8rem; line-height:1.65; margin-bottom:1rem; }
.section-card { background:#fff; border:1px solid var(--line); border-radius:22px; padding:18px; box-shadow:var(--shadow); }
.breadcrumb-wrap { display:flex; align-items:center; flex-wrap:wrap; gap:6px; margin:0 0 8px 0; padding:2px 0 4px; }
.crumb-sep { display:inline-flex; align-items:center; min-height:32px; color:var(--subtle); padding:0 1px; font-size:15px !important; line-height:1; }
.crumb-current { display:inline-flex; align-items:center; min-height:32px; color:var(--purple); font-weight:850; padding:6px 10px; border-radius:10px; background:var(--purple-soft); font-size:15px !important; line-height:1.15; white-space:normal; }
div[data-testid="stHorizontalBlock"]:has(.breadcrumb-wrap) { margin-bottom:8px !important; }
div[data-testid="stHorizontalBlock"]:has(.breadcrumb-wrap) .stButton > button { min-height:32px !important; padding:6px 10px !important; font-size:15px !important; border-radius:10px !important; box-shadow:none !important; font-weight:750 !important; background:#fff !important; }

/* 首页系列卡 */
.series-card { min-height:210px; display:flex; flex-direction:column; justify-content:center; align-items:center; gap:10px; text-align:center; background:#fff; border:1px solid var(--line); border-radius:22px; padding:26px; box-shadow:var(--shadow); transition:all .16s ease; }
.series-card:hover { border-color:#B8BDFD; box-shadow:var(--shadow-hover); transform:translateY(-2px); }
.series-icon { width:44px; height:44px; border-radius:15px; display:flex; align-items:center; justify-content:center; background:var(--purple-soft); color:var(--purple); font-size:1.2rem; font-weight:900; }
.series-title { font-size:1.15rem; font-weight:850; color:var(--text); }
.series-desc { color:#475467; font-size:.84rem; line-height:1.6; max-width:300px; }
.series-count { color:var(--text); font-size:.82rem; font-weight:800; }
div[data-testid="stMarkdownContainer"]:has(.series-hit-marker) + div.stButton, div[data-testid="stMarkdownContainer"]:has(.series-hit-marker) + div[data-testid="stButton"] { height:0 !important; margin:0 !important; padding:0 !important; }
div[data-testid="stMarkdownContainer"]:has(.series-hit-marker) + div.stButton > button, div[data-testid="stMarkdownContainer"]:has(.series-hit-marker) + div[data-testid="stButton"] > button { height:210px !important; min-height:210px !important; width:100% !important; margin-top:-210px !important; opacity:.001 !important; cursor:pointer !important; position:relative !important; z-index:20 !important; }

/* 产品卡网格 */
.products-note { color:var(--muted); font-size:.78rem; margin-bottom:14px; }
.product-card, .product-card-native { min-height:212px; width:100%; background:#fff; border:1px solid var(--line); border-radius:20px; padding:14px; box-shadow:var(--shadow); transition:all .16s ease; overflow:hidden; box-sizing:border-box; }
.product-card:hover, .product-card-native:hover { border-color:#B8BDFD; box-shadow:var(--shadow-hover); transform:translateY(-2px); }
.product-card.selected, .product-card-native.selected { border:2px solid var(--purple); box-shadow:0 0 0 4px rgba(109,93,251,.10), var(--shadow-hover); }
.product-img-wrap { width:100%; height:148px; border-radius:16px; background:linear-gradient(135deg,#F7F8FB,#FFFFFF); border:1px solid var(--line); display:flex; align-items:center; justify-content:center; overflow:hidden; box-sizing:border-box; }
.product-img { width:100%; height:100%; object-fit:contain; display:block; }
.product-name { margin-top:12px; color:var(--text); font-size:.94rem; font-weight:850; line-height:1.35; white-space:normal; overflow:visible; text-overflow:clip; text-align:center; min-height:2.5em; display:flex; align-items:center; justify-content:center; }
.product-check { position:absolute; top:10px; right:10px; width:22px; height:22px; border-radius:999px; display:flex; align-items:center; justify-content:center; background:var(--purple); color:#fff; font-size:.72rem; font-weight:900; }
div[data-testid="stVerticalBlock"]:has(.product-card) .stButton > button, div[data-testid="stVerticalBlock"]:has(.product-card-native) .stButton > button { margin-top:8px !important; height:38px !important; min-height:38px !important; font-size:.86rem !important; justify-content:center !important; }

/* 规格、控制、报价 */
.spec-strip { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin:16px 0; }
.spec-cell, .metric-tile { background:#FBFCFE; border:1px solid var(--line); border-radius:16px; padding:14px; box-shadow:0 1px 2px rgba(15,23,42,.03); }
.sc-label, .mt-label, .ot-label, .ph-label { color:var(--muted); font-size:.66rem; font-weight:800; letter-spacing:.04em; }
.sc-val, .mt-val { margin-top:5px; color:#101828; font-family:var(--mono) !important; font-size:1.02rem; font-weight:850; white-space:nowrap; }
.sc-sub, .mt-sub { color:var(--subtle); font-size:.66rem; margin-top:3px; }
.controls-card { background:#fff; border:1px solid var(--line); border-radius:18px; padding:16px; box-shadow:var(--shadow); margin-top:14px; }
.quote-card { background:#fff; border:1px solid var(--line); border-radius:22px; padding:18px; box-shadow:0 16px 34px rgba(15,23,42,.07); min-width:330px; overflow:hidden; }
.empty-quote { display:none; }
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
.formula { padding:10px 12px; border:1px solid var(--line); border-radius:12px; background:#fff; font-family:var(--font) !important; color:#475467; font-size:.72rem; font-weight:500; line-height:1.7; white-space:pre-wrap; overflow:visible; text-overflow:clip; overflow-wrap:anywhere; }
.tool-card { background:#fff; border:1px solid var(--line); border-radius:22px; padding:18px; box-shadow:var(--shadow); margin-top:18px; }
.login-shell { max-width:420px; margin:12vh auto 1.5rem; padding:30px; border:1px solid var(--line); border-radius:22px; background:#fff; box-shadow:var(--shadow); }
.login-title { font-size:1.2rem; font-weight:850; color:var(--text); margin-bottom:4px; }
.login-sub { color:var(--muted); font-size:.82rem; line-height:1.65; }
[data-testid="stDataFrame"] * { font-family:var(--mono) !important; }
div[data-testid="stButtonGroup"] { margin-bottom:12px !important; }
	div[data-testid="stButtonGroup"] label { font-weight:700 !important; color:#344054 !important; }
	div[data-testid="stButtonGroup"] [role="radiogroup"] { display:inline-flex !important; gap:4px !important; padding:4px !important; border:1px solid var(--line) !important; border-radius:14px !important; background:rgba(255,255,255,.82) !important; box-shadow:0 1px 2px rgba(15,23,42,.04) !important; }
	div[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_control"], div[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"] { min-height:32px !important; border-radius:10px !important; border:1px solid transparent !important; background:#FFFFFF !important; color:#475467 !important; box-shadow:none !important; font-weight:750 !important; }
	div[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_control"] * { color:#475467 !important; }
	div[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"] { border-color:#DAD7FE !important; background:var(--purple-soft) !important; color:var(--purple) !important; box-shadow:0 1px 6px rgba(101,79,240,.14) !important; }
	div[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"] * { color:var(--purple) !important; }
	.filter-bar-spacer { height:28px; }
	[data-testid="stTabs"] { margin-top:22px !important; }
	[data-testid="stTabs"] [role="tablist"] { gap:8px !important; }
	[data-testid="stTabs"] [role="tab"] { padding:8px 12px !important; }
	@media (max-width: 1180px) { .main .block-container { padding-left:1rem !important; padding-right:1rem !important; } .quote-pane, .quote-card { min-width:300px; } .product-img-wrap { height:120px; } }
@media (max-width: 980px) { .quote-pane { position:relative; top:auto; min-width:100%; } .spec-strip, .metric-grid { grid-template-columns:1fr; } .custom-navbar { padding:10px 12px !important; flex-wrap:wrap; height:auto; min-height:70px; } }
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
    """B 方案：使用原生 Streamlit Sidebar 承载全部全局参数与数据管理。"""
    with st.sidebar:
        st.markdown("### 报价参数")
        st.caption("铜价、汇率、箱规与产品表在此统一管理。")

        with st.container(border=True):
            copper_price = st.number_input(
                "铜价（元/吨）",
                min_value=40000,
                max_value=150000,
                value=int(st.session_state.copper_price),
                step=100,
            )
            st.session_state.copper_price = copper_price

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
            )
            st.session_state.exchange_rate = exchange_rate
            if currency != "RMB":
                effective_rate = round(exchange_rate * EXCHANGE_RATE_MARGIN, 4)
                st.caption(f"报价汇率 = {exchange_rate} × {EXCHANGE_RATE_MARGIN} = {effective_rate}")

        with st.container(border=True):
            st.markdown("#### 标准箱规格")
            row_1 = st.columns(3, gap="small")
            with row_1[0]:
                box_l = st.number_input("长（cm）", value=int(st.session_state.box_l), step=1, format="%d")
            with row_1[1]:
                box_w = st.number_input("宽（cm）", value=int(st.session_state.box_w), step=1, format="%d")
            with row_1[2]:
                box_h = st.number_input("高（cm）", value=int(st.session_state.box_h), step=1, format="%d")
            units_per_box = st.number_input("装箱数（PCS）", min_value=1, value=int(st.session_state.units_per_box), step=10)
            cbm_val = round(box_l * box_w * box_h / 1_000_000, 4)
            st.markdown(f'<p class="sb-hint box-hint">{box_l:.0f}×{box_w:.0f}×{box_h:.0f} cm · {cbm_val:.2f} CBM · {int(units_per_box)} PCS</p>', unsafe_allow_html=True)
            st.session_state.box_l, st.session_state.box_w, st.session_state.box_h = box_l, box_w, box_h
            st.session_state.units_per_box = units_per_box

        with st.container(border=True):
            st.markdown("#### 数据管理")
            st.markdown('<div class="upload-center"></div>', unsafe_allow_html=True)
            uploaded = st.file_uploader("上传 XLSX 产品表", type=["xlsx"], label_visibility="collapsed")
            if uploaded:
                saved_path = UPLOAD_DIR / uploaded.name
                saved_path.write_bytes(uploaded.getbuffer())
                st.session_state.custom_excel_path = str(saved_path)
                st.cache_data.clear()
                st.rerun()
            if st.session_state.custom_excel_path:
                st.caption(f"当前数据：{Path(st.session_state.custom_excel_path).name}")
                if st.button("恢复默认数据", key="reset_data", use_container_width=True):
                    st.session_state.custom_excel_path = None
                    st.cache_data.clear()
                    st.rerun()

        if st.button("刷新全局参数", type="secondary", use_container_width=True):
            with st.spinner("正在刷新铜价与汇率..."):
                copper_result = cached_copper_price()
                st.session_state.copper_price = float(copper_result.get("price", DEFAULT_COPPER_PRICE))
                st.session_state.copper_source = copper_result.get("source", "实时源")
                st.session_state.rates = cached_exchange_rates()
            st.rerun()

    return {
        "copper_price": st.session_state.copper_price,
        "currency": st.session_state.currency,
        "exchange_rate": st.session_state.exchange_rate,
        "box_l": st.session_state.box_l,
        "box_w": st.session_state.box_w,
        "box_h": st.session_state.box_h,
        "units_per_box": st.session_state.units_per_box,
    }

def inject_sidebar_toggle_bridge() -> None:
    """插入独立悬浮侧边栏开关，桥接点击 Streamlit 原生展开/收起按钮。

    说明：部分 Streamlit Cloud/浏览器组合在侧边栏收起后不会稳定显示
    `stExpandSidebarButton`。因此这里使用一个独立插入到父页面的浮层按钮，
    它始终固定在左上角，并在点击时主动寻找当前可用的 Streamlit 原生按钮
    进行代理点击。这样即使原生按钮不可见，用户也能看到稳定的回归入口。
    """
    components.html(
        """
<script>
(function () {
  const BUTTON_ID = "vc-sidebar-floating-toggle";
  const STYLE_ID = "vc-sidebar-floating-toggle-style";
  const parentWindow = window.parent || window;
  const doc = parentWindow.document || document;

  function ensureStyle() {
    if (doc.getElementById(STYLE_ID)) return;
    const style = doc.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      #${BUTTON_ID} {
        position: fixed !important;
        top: 15px !important;
        left: 20px !important;
        z-index: 2147483647 !important;
        display: inline-flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        align-items: center !important;
        justify-content: center !important;
        width: 34px !important;
        height: 34px !important;
        min-width: 34px !important;
        min-height: 34px !important;
        padding: 0 !important;
        background: #FFFFFF !important;
        border: 1px solid #E5E7EB !important;
        border-radius: 9px !important;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.16) !important;
        color: #111827 !important;
        font-size: 22px !important;
        font-weight: 800 !important;
        line-height: 1 !important;
        cursor: pointer !important;
        pointer-events: auto !important;
        user-select: none !important;
      }
      #${BUTTON_ID}:hover {
        background: #F3F4F6 !important;
        border-color: #D1D5DB !important;
      }
      #${BUTTON_ID} .vc-sidebar-toggle-icon {
        font-family: Arial, Helvetica, sans-serif !important;
        font-size: 22px !important;
        line-height: 1 !important;
        margin-top: -1px !important;
      }
    `;
    doc.head.appendChild(style);
  }

  function isVisible(el) {
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    const style = parentWindow.getComputedStyle(el);
    return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
  }

  function sidebarExpanded() {
    const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
    if (!sidebar) return false;
    const rect = sidebar.getBoundingClientRect();
    const style = parentWindow.getComputedStyle(sidebar);
    return style.display !== "none" && style.visibility !== "hidden" && rect.width > 120;
  }

  function nativeCandidates(expanded) {
    const preferred = expanded
      ? ['[data-testid="stSidebarCollapseButton"]']
      : ['[data-testid="stExpandSidebarButton"]', '[data-testid="collapsedControl"]'];
    const fallback = [
      'button[aria-label*="sidebar" i]',
      'button[title*="sidebar" i]',
      '[role="button"][aria-label*="sidebar" i]',
      '[role="button"][title*="sidebar" i]'
    ];
    return preferred.concat(fallback);
  }

  function findNativeToggle(expanded) {
    for (const selector of nativeCandidates(expanded)) {
      const nodes = Array.from(doc.querySelectorAll(selector));
      const visible = nodes.find(isVisible);
      if (visible) return visible;
      if (nodes.length) return nodes[0];
    }

    const buttons = Array.from(doc.querySelectorAll('button, [role="button"]'));
    return buttons.find((node) => {
      if (node.id === BUTTON_ID) return false;
      const text = (node.innerText || node.textContent || "").trim();
      const label = `${node.getAttribute("aria-label") || ""} ${node.getAttribute("title") || ""}`.toLowerCase();
      return /keyboard_double_arrow|chevron|sidebar|侧边栏|展开|收起|menu/.test(text + " " + label);
    }) || null;
  }

  function ensureButton() {
    ensureStyle();
    let btn = doc.getElementById(BUTTON_ID);
    if (!btn) {
      btn = doc.createElement("button");
      btn.id = BUTTON_ID;
      btn.type = "button";
      btn.setAttribute("aria-label", "展开或收起侧边栏");
      btn.title = "展开或收起侧边栏";
      btn.innerHTML = '<span class="vc-sidebar-toggle-icon">›</span>';
      doc.body.appendChild(btn);
      btn.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        const expanded = sidebarExpanded();
        const nativeBtn = findNativeToggle(expanded);
        if (nativeBtn) {
          nativeBtn.click();
          parentWindow.setTimeout(updateIcon, 220);
        }
      }, true);
    }
    btn.style.setProperty("display", "inline-flex", "important");
    btn.style.setProperty("visibility", "visible", "important");
    btn.style.setProperty("opacity", "1", "important");
    btn.style.setProperty("z-index", "2147483647", "important");
    updateIcon();
  }

  function updateIcon() {
    const btn = doc.getElementById(BUTTON_ID);
    if (!btn) return;
    const expanded = sidebarExpanded();
    const icon = btn.querySelector(".vc-sidebar-toggle-icon");
    if (icon) icon.textContent = expanded ? "‹" : "›";
    btn.setAttribute("aria-label", expanded ? "收起侧边栏" : "展开侧边栏");
    btn.title = expanded ? "收起侧边栏" : "展开侧边栏";
  }

  ensureButton();
  const observer = new MutationObserver(ensureButton);
  observer.observe(doc.body, { childList: true, subtree: true, attributes: true });
  parentWindow.setInterval(ensureButton, 700);
})();
</script>
        """,
        height=1,
        width=1,
    )


def render_header(df: pd.DataFrame, params: dict[str, Any]) -> None:
    now = datetime.now().strftime("%H:%M")
    copper_dot = "dot-green" if st.session_state.copper_source != "默认值" else "dot-yellow"
    rate_dot = "dot-green" if st.session_state.rates.get("_success") else "dot-yellow"
    st.markdown(f"""
    <div class="custom-navbar">
      <div class="vc-brand"><div class="vc-logo">成</div><div><div class="vc-title">{APP_NAME}</div><div class="vc-subtitle">{APP_SUBTITLE}</div></div></div>
      <div class="status-row">
        <span class="status-chip"><span class="dot {copper_dot}"></span>铜价 ¥{params['copper_price']:,.0f}</span>
        <span class="status-chip"><span class="dot {rate_dot}"></span>{params['currency']} {params['exchange_rate']}</span>
        <span class="status-chip"><span class="dot dot-green"></span>{len(df)} 产品 · {now}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_breadcrumb(product: pd.Series | None = None) -> None:
    """响应式可点击面包屑：使用可见 st.button 模拟链接，所有跳转均在单页 session_state 内完成。"""
    selected_cat = st.session_state.selected_cat
    st.markdown('<div class="breadcrumb-wrap"></div>', unsafe_allow_html=True)
    cols = st.columns([1.0, 0.10, 1.15, 0.10, 2.3, 4.0], gap="small")
    with cols[0]:
        if st.button("所有系列", key="crumb_all", use_container_width=True):
            reset_to_home()
    with cols[1]:
        st.markdown('<span class="crumb-sep">/</span>', unsafe_allow_html=True)
    with cols[2]:
        if selected_cat:
            if st.button(f"{selected_cat}系列", key="crumb_cat", use_container_width=True):
                st.session_state.page = "collection"
                st.session_state.selected_prod = None
                st.rerun()
        else:
            st.markdown('<span class="crumb-current">选择系列</span>', unsafe_allow_html=True)
    with cols[3]:
        st.markdown('<span class="crumb-sep">/</span>', unsafe_allow_html=True)
    with cols[4]:
        product_label = html.escape(str(product["产品名称"])) if product is not None else "产品列表"
        st.markdown(f'<span class="crumb-current">{product_label}</span>', unsafe_allow_html=True)

def render_segmented_navigation(df: pd.DataFrame) -> pd.DataFrame:
    """用清晰的产品线维度筛选产品矩阵，避免「全量列表」语义重复。"""
    series_options = ["全系列", "快开系列", "慢开系列"]
    current = "全系列"
    if st.session_state.selected_cat:
        normalized_cat = str(st.session_state.selected_cat).replace("系列", "")
        candidate = f"{normalized_cat}系列"
        if candidate in series_options:
            current = candidate

    selected_series = st.segmented_control(
        "选择阀芯系列", 
        options=["全系列", "快开系列", "慢开系列"], 
        default=current,
        key="series_segmented_control",
    )
    selected_series = selected_series or current

    st.session_state.page = "collection"
    if selected_series == "全系列":
        st.session_state.selected_cat = None
        filtered = df.reset_index(drop=True)
    else:
        category = selected_series.replace("系列", "")
        st.session_state.selected_cat = category
        filtered = df[df["系列"].astype(str).str.replace("系列", "", regex=False) == category].reset_index(drop=True)

    if st.session_state.selected_prod and st.session_state.selected_prod not in set(filtered["产品名称"].astype(str)):
        st.session_state.selected_prod = None
    return filtered

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
    """B 方案：每张产品卡片使用同一个原生 border container 包裹图片、名称和按钮。"""
    cat_df = df.reset_index(drop=True)
    if cat_df.empty:
        st.info("暂无产品数据。")
        return

    grid_cols = st.columns(4, gap="small")
    for idx, (_, product) in enumerate(cat_df.iterrows()):
        selected = str(st.session_state.selected_prod) == str(product["产品名称"])
        img_src = product_image_src(product)
        with grid_cols[idx % 4]:
            with st.container(border=True):
                st.markdown(
                    f"""
                    <div class="product-card-native {'selected' if selected else ''}">
                      <div class="product-img-wrap"><img class="product-img" src="{img_src}" alt="{html.escape(str(product['产品名称']))}" /></div>
                      <div class="product-name">{html.escape(str(product['产品名称']))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                button_type = "primary" if selected else "secondary"
                if st.button("选择", key=f"prod_select_b_{idx}_{product['产品名称']}", type=button_type, use_container_width=True):
                    st.session_state.page = "product"
                    st.session_state.selected_cat = str(product["系列"])
                    st.session_state.selected_prod = str(product["产品名称"])
                    st.rerun()

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
    """B 方案：未选择产品时不渲染静态占位卡；选择后才显示右侧报价指标。"""
    if product is None:
        return

    quote = calculate_quote(product, params["copper_price"], st.session_state.plating, st.session_state.packaging, st.session_state.quantity, st.session_state.destination, params["currency"], params["exchange_rate"], params["box_l"], params["box_w"], params["box_h"], params["units_per_box"])
    symbol = CURRENCY_SYMBOLS.get(params["currency"], params["currency"])
    cost_total = max(quote["rmb"], 0.0001)
    cost_colors = {"原材料":"#F79009","加工配件":"#2E90FA","电镀":"#7A5AF8","包装":"#12B76A","运费":"#6172F3","利润":"#F04438"}
    cost_rows = []
    for name in ["原材料", "加工配件", "电镀", "包装", "运费", "利润"]:
        val = float(quote.get(name, 0))
        pct = val / cost_total * 100
        cost_rows.append(f'<div class="cost-row"><div class="cost-dot" style="background:{cost_colors[name]};"></div><div class="cost-name">{name}</div><div class="cost-val">¥{val:.4f}</div><div class="cost-pct">{pct:.0f}%</div></div>')

    packaging_total = sum(PACKAGING_FEES.get(option, 0.0) for option in st.session_state.packaging)
    plating_rate = PLATING_RATES.get(st.session_state.plating, 0.0)
    freight_rate = FREIGHT_RATES.get(st.session_state.destination, 0.0)
    formula = (
        f"产品：{product['产品名称']}\n"
        f"净铜重：{quote['net_g']:.1f} g\n"
        f"标准箱规格：{params['box_l']:.0f}×{params['box_w']:.0f}×{params['box_h']:.0f} cm · {quote['cbm']:.2f} CBM · {int(params['units_per_box'])} PCS\n"
        f"原材料 = {quote['net_g']:.1f} g × ¥{params['copper_price']:,.0f}/吨 ÷ 1,000,000 = ¥{quote['原材料']:.4f}\n"
        f"加工配件 = ¥{quote['加工配件']:.4f}\n"
        f"电镀 = {quote['net_g']:.1f} g × {plating_rate} ÷ 1,000,000 = ¥{quote['电镀']:.4f}（{st.session_state.plating}）\n"
        f"包装 = ¥{packaging_total:.4f}（{', '.join(st.session_state.packaging) if st.session_state.packaging else '无'}）\n"
        f"运费 = {freight_rate} × {quote['cbm']:.2f} CBM ÷ {int(params['units_per_box'])} PCS × {params['exchange_rate']} = ¥{quote['运费']:.4f}（{st.session_state.destination}）\n"
        f"利润 = ¥{quote['利润']:.4f}\n"
        f"人民币单价 = 原材料 + 加工配件 + 电镀 + 包装 + 运费 + 利润 = ¥{quote['rmb']:.4f}\n"
        f"有效汇率 = {params['exchange_rate']} × {EXCHANGE_RATE_MARGIN} = {quote['eff_rate']}\n"
        f"外币单价 = 人民币单价 ÷ 有效汇率 = {symbol}{quote['fgn']:.4f}\n"
        f"订单总价 = {symbol}{quote['fgn']:.4f} × {int(st.session_state.quantity)} PCS = {symbol}{quote['total']:,.2f}"
    )

    st.markdown('<div class="quote-pane">', unsafe_allow_html=True)
    with st.container(border=True):
        st.caption("QUOTE SUMMARY")
        st.markdown(f"### {html.escape(str(product['产品名称']))}")
        st.metric("单件报价", f"{symbol}{quote['fgn']:.4f}", delta=f"利润率 {quote['margin']:.1f}%")
        st.metric("订单总价", f"{symbol}{quote['total']:,.2f}", delta=f"{int(st.session_state.quantity)} PCS")
        st.markdown(f"<div class='ph-rmb'>¥{quote['rmb']:.4f} RMB / 只</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='ph-sub'>有效汇率 {params['exchange_rate']} × {EXCHANGE_RATE_MARGIN} = {quote['eff_rate']}</div>", unsafe_allow_html=True)
        with st.expander("查看详细计算公式", expanded=False):
            st.markdown(f'<div class="formula">{html.escape(formula)}</div>', unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("#### 成本拆分")
        st.markdown(''.join(cost_rows), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_workbench(df: pd.DataFrame, params: dict[str, Any]) -> dict[str, Any]:
    """B 方案主工作台：侧边栏控制参数，主区域为分段导航、产品矩阵与条件报价面板。"""
    params = render_sidebar_controls()
    product = get_selected_product(df)

    main_col, right_col = st.columns([3.2, 1.35], gap="large")
    with main_col:
        filtered_df = render_segmented_navigation(df)
        render_product_grid(filtered_df)
        product = get_selected_product(df)
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
        c1, c2, c3, c4 = st.columns([1, 1, 1, 1], gap="medium")
        with c1:
            plating = st.selectbox("电镀", list(PLATING_RATES.keys()), key="batch_plating")
        with c2:
            destination = st.selectbox("目的地", list(FREIGHT_RATES.keys()), key="batch_destination")
        with c3:
            qty = st.number_input("数量", min_value=1, value=int(st.session_state.quantity), step=100, key="batch_qty")
        with c4:
            st.markdown('<div class="filter-bar-spacer"></div>', unsafe_allow_html=True)
            generate = st.button("生成全产品报价表", type="primary", use_container_width=True)
        if generate:
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
        buffer = io.BytesIO()
        template.to_excel(buffer, index=False)
        st.download_button("下载 Excel 模板", data=buffer.getvalue(), file_name="产品明细表_模板.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.dataframe(template, use_container_width=True, hide_index=True)

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
    inject_sidebar_toggle_bridge()
    st.markdown('<div class="main-body-container"></div>', unsafe_allow_html=True)
    params = {"copper_price": st.session_state.copper_price, "currency": st.session_state.currency, "exchange_rate": st.session_state.exchange_rate, "box_l": st.session_state.box_l, "box_w": st.session_state.box_w, "box_h": st.session_state.box_h, "units_per_box": st.session_state.units_per_box}
    params = render_workbench(products_df, params)
    render_bottom_tools(products_df, params)
    render_footer()


if __name__ == "__main__":
    main()
