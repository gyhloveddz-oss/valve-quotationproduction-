"""
成宁阀芯报价工作台 · Streamlit Cloud 生产版

设计原则：
1. 产品参数只从 data/products.xlsx 读取，Python 代码不硬编码任何具体产品参数。
2. 汇率默认值、铜价默认值、公式系数、费率字典集中存放在 config.py。
3. 账号密码通过 st.secrets 读取，保护工厂底价与成本数据。
4. 所有文件路径基于当前文件的相对目录构建，适合上传 GitHub 后部署到 Streamlit Cloud。
5. UI 渲染、数据处理、核心计算拆分为独立函数，便于后续升级阶梯报价模型。
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
from urllib.parse import unquote

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


# ═══════════════════════════════════════════════════════════
# 路径配置：全部基于项目根目录的相对路径
# ═══════════════════════════════════════════════════════════
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
IMG_DIR = DATA_DIR / "images"
UPLOAD_DIR = DATA_DIR / "uploads"
DEFAULT_PRODUCTS_FILE = DATA_DIR / "products.xlsx"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


st.set_page_config(
    page_title=f"{APP_NAME} · Production",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ═══════════════════════════════════════════════════════════
# 视觉系统
# ═══════════════════════════════════════════════════════════
def inject_css() -> None:
    """注入深色工业 HUD 风格 CSS，并稳定三段式生产布局。"""
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600;14..32,700;14..32,800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,400,0,0&display=block');
:root {
  --bg-base:#0D0E12; --bg-surface:#111318; --bg-elevated:#16181D; --bg-panel:#1A1B22;
  --border:#2D2E33; --border-soft:rgba(255,255,255,.10);
  --text:#FAFAFA; --muted:#B8BBC2; --subtle:#9CA3AF; --disabled:#6B7280;
  --radius-card:16px; --radius-control:10px;
  --cyan:#A5F3FC; --cyan-strong:#67E8F9; --purple:#C4B5FD;
  --green:#22C55E; --yellow:#EAB308; --red:#EF4444;
  --mono:'JetBrains Mono','SF Mono','Consolas',monospace;
  --font:'Inter',-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB',sans-serif;
}
*, *::before, *::after { font-family:var(--font) !important; box-sizing:border-box; }
span[data-testid="stIconMaterial"], span[translate="no"], span[class*="material"], i[class*="material"], .material-icons, .material-symbols-rounded, .material-symbols-outlined {
  font-family:'Material Symbols Rounded','Material Symbols Outlined','Material Icons' !important;
  font-weight:normal !important; font-style:normal !important; font-size:1.1em !important; line-height:1 !important;
  letter-spacing:normal !important; text-transform:none !important; white-space:nowrap !important; word-wrap:normal !important; direction:ltr !important;
  -webkit-font-feature-settings:'liga' !important; -webkit-font-smoothing:antialiased !important; font-feature-settings:'liga' !important;
}
.stApp { background:var(--bg-base) !important; color:var(--text) !important; overflow-x:hidden !important; }
#MainMenu, footer, header[data-testid="stHeader"], .stDeployButton, [data-testid="stToolbar"] { display:none !important; }
.main .block-container { max-width:none !important; padding:1.05rem 1.35rem 2rem 1.55rem !important; overflow-x:hidden !important; }
section[data-testid="stSidebar"] { background:var(--bg-surface) !important; border-right:1px solid var(--border) !important; width:244px !important; min-width:244px !important; }
section[data-testid="stSidebar"] > div:first-child { padding:1.35rem 1.1rem !important; overflow-x:hidden !important; }
hr { border-color:var(--border-soft) !important; }
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div:first-child {
  background:var(--bg-elevated) !important; border:1px solid var(--border) !important; border-radius:var(--radius-control) !important;
}
div[data-baseweb="input"] input, .stNumberInput input { color:#fff !important; font-family:var(--mono) !important; pointer-events:auto !important; }
.stButton > button, .stDownloadButton > button {
  background:transparent !important; border:1px solid var(--border) !important; color:var(--muted) !important;
  border-radius:var(--radius-control) !important; font-weight:400 !important; letter-spacing:.5px !important; transition:all .16s ease !important;
}
.stButton > button:hover, .stDownloadButton > button:hover { background:rgba(255,255,255,.04) !important; border-color:#3D3E44 !important; color:#E5E7EB !important; }
.sb-label { display:block; color:var(--muted); font-size:.72rem; font-weight:600; letter-spacing:.06em; text-transform:uppercase; margin:.6rem 0 .35rem; }
.sb-hint { color:var(--subtle); font-size:.72rem; line-height:1.55; margin:.35rem 0 .2rem; }
.sidebar-upload-wrap { width:100%; display:flex; justify-content:center; align-items:center; margin:.35rem 0 .55rem; }
section[data-testid="stSidebar"] [data-testid="stFileUploader"] { width:100% !important; max-width:178px !important; margin:0 auto !important; }
section[data-testid="stSidebar"] [data-testid="stFileUploader"] > div { display:flex !important; justify-content:center !important; text-align:center !important; }
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] { min-height:84px !important; padding:12px !important; justify-content:center !important; align-items:center !important; text-align:center !important; border-radius:12px !important; }
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] div { text-align:center !important; margin-left:auto !important; margin-right:auto !important; }
.version-box { width:100%; max-width:178px; margin:18px auto 0; padding:13px; border:1px solid var(--border); border-radius:12px; background:rgba(22,24,29,.6); text-align:center; }
.version-text { color:var(--subtle); font-family:var(--mono) !important; font-size:.72rem; text-align:center; }
section[data-testid="stSidebar"] [data-testid="stExpander"] { width:100% !important; max-width:178px !important; margin-left:auto !important; margin-right:auto !important; text-align:center !important; }
section[data-testid="stSidebar"] [data-testid="stExpander"] summary { justify-content:center !important; }
.vc-header { display:flex; align-items:center; justify-content:space-between; gap:1rem; padding:10px 18px; margin:-1px -2px 64px; background:rgba(17,19,24,.86); border-bottom:1px solid var(--border); border-radius:0; box-shadow:inset 0 1px 0 rgba(255,255,255,.05); backdrop-filter:blur(10px); }
.vc-brand { display:flex; align-items:center; gap:12px; }
.vc-logo { width:32px; height:32px; display:flex; align-items:center; justify-content:center; border-radius:8px; color:#fff; font-weight:800; background:linear-gradient(135deg,#7C3AED,#4F46E5); box-shadow:0 0 18px rgba(124,58,237,.35); }
.vc-title { font-weight:700; letter-spacing:-.02em; }
.vc-subtitle { color:var(--subtle); font-size:.74rem; margin-top:2px; }
.status-row { display:flex; gap:8px; align-items:center; flex-wrap:wrap; justify-content:flex-end; }
.status-chip { display:inline-flex; align-items:center; gap:6px; padding:5px 10px; border:1px solid var(--border); border-radius:999px; color:#D1D5DB; background:rgba(22,24,29,.78); font-size:.70rem; }
.dot { width:6px; height:6px; border-radius:50%; display:inline-block; }
.dot-green { background:var(--green); box-shadow:0 0 8px rgba(34,197,94,.55); } .dot-yellow { background:var(--yellow); box-shadow:0 0 8px rgba(234,179,8,.35); }
.page-title { font-size:1.05rem; font-weight:800; letter-spacing:-.025em; margin:.15rem 0 .55rem; }
.page-sub { color:var(--subtle); font-size:.78rem; margin-bottom:.8rem; }
.cat-card, .prod-card, .quote-card, .spec-strip, .tool-card {
  background:rgba(22,24,29,.84); border:1px solid var(--border); border-radius:var(--radius-card); box-shadow:inset 0 1px 0 rgba(255,255,255,.05),0 8px 28px rgba(0,0,0,.28); backdrop-filter:blur(10px);
}
.cat-card { min-height:150px; padding:22px; cursor:pointer; position:relative; transition:all .18s ease; }
.cat-card:hover, .prod-card:hover { border-color:#3D3E44; transform:translateY(-1px); }
.cat-icon { font-size:1.45rem; margin-bottom:.8rem; }
.cat-title { font-size:1.08rem; font-weight:700; margin-bottom:.4rem; }
.cat-desc { color:var(--subtle); font-size:.82rem; line-height:1.65; }
.cat-badge { display:inline-flex; margin-top:1rem; padding:3px 10px; border:1px solid rgba(165,243,252,.25); border-radius:999px; color:var(--cyan); font-size:.72rem; background:rgba(165,243,252,.08); }
.cat-click-marker, .prod-click-marker { display:none; }
div[data-testid="stVerticalBlock"]:has(.cat-click-marker), div[data-testid="stVerticalBlock"]:has(.prod-click-marker) { position:relative; }
div[data-testid="stVerticalBlock"]:has(.cat-click-marker) .stButton,
div[data-testid="stVerticalBlock"]:has(.prod-click-marker) .stButton,
div[data-testid="stVerticalBlock"]:has(.cat-click-marker) div[data-testid="stButton"],
div[data-testid="stVerticalBlock"]:has(.prod-click-marker) div[data-testid="stButton"] { position:absolute; inset:0; z-index:20; margin:0 !important; }
div[data-testid="stVerticalBlock"]:has(.cat-click-marker) .stButton > button,
div[data-testid="stVerticalBlock"]:has(.prod-click-marker) .stButton > button,
div[data-testid="stVerticalBlock"]:has(.cat-click-marker) div[data-testid="stButton"] > button,
div[data-testid="stVerticalBlock"]:has(.prod-click-marker) div[data-testid="stButton"] > button { width:100% !important; height:100% !important; min-height:100% !important; opacity:0 !important; cursor:pointer !important; border:0 !important; padding:0 !important; }
.prod-card { height:156px; padding:12px; cursor:pointer; text-align:center; transition:all .18s ease; overflow:hidden; position:relative; display:flex; flex-direction:column; align-items:center; justify-content:center; }
.prod-card.selected { border:2px solid #7C3AED; box-shadow:0 0 0 1px rgba(124,58,237,.35),0 0 26px rgba(124,58,237,.20); }
.prod-img { width:100%; height:112px; object-fit:contain; margin-bottom:8px; filter:drop-shadow(0 12px 18px rgba(0,0,0,.25)); }
.prod-placeholder { height:112px; display:flex; align-items:center; justify-content:center; color:#3F3F46; font-size:1.45rem; }
.prod-name { color:#E5E7EB; font-size:.72rem; font-weight:700; line-height:1.25; position:absolute; left:0; right:0; bottom:0; padding:6px 8px; background:linear-gradient(180deg,rgba(17,19,24,0),rgba(17,19,24,.92)); }
.three-col-left, .three-col-mid, .three-col-right { width:100%; max-width:100%; overflow-x:hidden; }
.three-col-mid { min-width:0; }
.three-col-right { min-width:350px; }
div[data-testid="stVerticalBlock"]:has(.quote-column-marker) { position:sticky; top:18px; align-self:flex-start; min-width:350px !important; overflow-x:visible !important; }
.quote-column-marker { height:0; width:100%; }
.spec-strip { display:grid; grid-template-columns:repeat(3,1fr); gap:0; overflow:hidden; margin:12px 0 18px; }
.spec-cell { padding:15px 18px; border-right:1px solid var(--border-soft); }
.spec-cell:last-child { border-right:0; }
.sc-label { color:var(--subtle); font-size:.68rem; letter-spacing:.08em; text-transform:uppercase; margin-bottom:4px; }
.sc-val { color:#fff; font-family:var(--mono) !important; font-weight:700; font-size:1.08rem; }
.sc-sub { color:var(--disabled); font-size:.72rem; margin-top:3px; }
.warn-bar { color:#FDE68A; background:rgba(234,179,8,.10); border:1px solid rgba(234,179,8,.22); border-radius:10px; padding:10px 12px; font-size:.78rem; margin-bottom:16px; }
.quote-card { padding:16px 16px 18px; text-align:left; min-width:350px; background:linear-gradient(180deg,rgba(26,27,34,.96),rgba(26,27,34,.90)); border:1px solid var(--border); box-shadow:inset 0 1px 0 rgba(255,255,255,.05),0 8px 28px rgba(0,0,0,.28); }
.quote-card * { text-align:left; }
.quote-empty { min-height:420px; display:flex; align-items:center; justify-content:center; text-align:center; }
.quote-empty * { text-align:center; }
.panel-kicker { display:flex; align-items:center; justify-content:space-between; gap:8px; color:var(--subtle); font-size:.62rem; text-transform:uppercase; letter-spacing:.1em; margin-bottom:8px; }
.panel-product { font-weight:800; font-size:1.05rem; padding-bottom:10px; margin-bottom:0; color:#F4F4F5; }
.price-hero { background:linear-gradient(100deg,rgba(22,24,29,.95),rgba(31,32,46,.96)); border:1px solid rgba(255,255,255,.08); border-radius:var(--radius-card); padding:18px 18px 18px 15px; text-align:left; box-shadow:inset 0 1px 0 rgba(255,255,255,.08),0 4px 20px rgba(0,0,0,.35); }
.ph-row { display:flex; justify-content:space-between; align-items:baseline; gap:12px; }
.ph-label { font-size:.62rem; color:var(--muted); text-transform:uppercase; letter-spacing:.09em; font-weight:700; }
.ph-currency { color:#A1A1AA; font-size:.74rem; white-space:nowrap; }
.ph-amount { padding-left:15px; color:#FAFAFA; font-family:var(--mono) !important; font-size:2.05rem; font-weight:800; letter-spacing:-.05em; line-height:1.05; text-shadow:0 0 20px rgba(165,243,252,.18); white-space:nowrap; }
.ph-rmb { padding-left:15px; color:var(--subtle); font-family:var(--mono) !important; font-size:.84rem; margin-top:4px; white-space:nowrap; }
.ph-sub { padding-left:15px; color:#9CA3AF; font-size:.62rem; line-height:1.5; border-top:1px solid rgba(255,255,255,.05); margin-top:10px; padding-top:8px; }
.metric-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin:8px 0; }
.metric-tile { background:rgba(22,24,29,.85); border:1px solid var(--border-soft); border-radius:12px; padding:15px 14px; min-width:0; }
.mt-label { color:var(--muted); font-size:.58rem; font-weight:700; text-transform:uppercase; letter-spacing:.08em; }
.mt-val { font-family:var(--mono) !important; color:#fff; font-size:1.04rem; font-weight:800; text-align:left; white-space:nowrap; }
.mt-sub { color:#7A7A8A; font-size:.6rem; }
.order-total { background:rgba(31,30,48,.9); border:1px solid rgba(124,58,237,.35); border-radius:var(--radius-card); padding:18px 20px; box-shadow:0 0 28px rgba(124,58,237,.15),inset 0 1px 0 rgba(255,255,255,.06); }
.ot-label { color:#7A7A8A; font-size:.62rem; text-transform:uppercase; letter-spacing:.09em; font-weight:700; }
.ot-val { color:var(--purple); font-family:var(--mono) !important; font-size:1.42rem; font-weight:800; text-align:left; text-shadow:0 0 16px rgba(196,181,253,.3); white-space:nowrap; }
.ot-sub { color:#A1A1AA; font-family:var(--mono) !important; font-size:.65rem; text-align:left; }
.margin-row { display:flex; align-items:center; justify-content:space-between; padding:14px 0; border-bottom:1px solid var(--border-soft); margin-bottom:12px; }
.margin-label { color:#7A7A8A; font-size:.75rem; }
.margin-pill { display:inline-flex; padding:4px 11px; border-radius:999px; font-size:.72rem; font-weight:800; font-family:var(--mono) !important; }
.mp-good { color:var(--green); background:rgba(34,197,94,.14); border:1px solid rgba(34,197,94,.28); }
.mp-warn { color:var(--yellow); background:rgba(234,179,8,.14); border:1px solid rgba(234,179,8,.28); }
.mp-danger { color:var(--red); background:rgba(239,68,68,.14); border:1px solid rgba(239,68,68,.28); }
.cost-row { display:grid; grid-template-columns:7px 1fr 70px 42px; gap:8px; align-items:center; padding:7px 0; border-bottom:1px solid rgba(255,255,255,.05); }
.cost-dot { width:7px; height:7px; border-radius:50%; } .cost-name { color:#A1A1AA; font-size:.72rem; } .cost-val { color:#E5E7EB; font-family:var(--mono) !important; font-size:.7rem; text-align:right; } .cost-pct { color:#666; font-size:.62rem; text-align:right; }
.formula { font-family:var(--mono) !important; color:#8B8B98; font-size:.68rem; white-space:pre-wrap; line-height:1.7; }
.tool-card { padding:18px; margin-top:20px; overflow-x:hidden; }
.login-shell { max-width:420px; margin:12vh auto; padding:28px; border:1px solid var(--border); border-radius:20px; background:rgba(17,19,24,.92); box-shadow:0 20px 80px rgba(0,0,0,.42), inset 0 1px 0 rgba(255,255,255,.06); }
.login-title { font-size:1.25rem; font-weight:800; margin-bottom:6px; } .login-sub { color:var(--subtle); font-size:.82rem; margin-bottom:18px; line-height:1.6; }
[data-testid="stDataFrame"] * { font-family:var(--mono) !important; }
.breadcrumb { display:flex; align-items:center; gap:7px; flex-wrap:wrap; margin-bottom:24px; }
.breadcrumb .crumb-static { display:inline-flex; align-items:center; min-height:32px; padding:7px 10px; background:rgba(26,27,34,.84); border:1px solid var(--border); border-radius:8px; color:#8A8D96; font-size:.72rem; }
.breadcrumb .crumb-current { color:#FAFAFA; font-weight:800; }
.breadcrumb .stButton > button { min-height:32px !important; padding:6px 10px !important; font-size:.72rem !important; color:#B8BBC2 !important; }
.products-stage { width:100%; max-width:100%; margin:0; overflow-x:hidden; }
@media (max-width: 1280px) { .three-col-right, div[data-testid="stVerticalBlock"]:has(.quote-column-marker), .quote-card { min-width:350px !important; } }
@media (max-width: 1100px) { .metric-grid, .spec-strip { grid-template-columns:1fr; } .vc-header { align-items:flex-start; flex-direction:column; } }
</style>
        """,
        unsafe_allow_html=True,
    )

# ═══════════════════════════════════════════════════════════
# 访问权限控制
# ═══════════════════════════════════════════════════════════
def read_auth_secrets() -> tuple[str | None, str | None]:
    """从 st.secrets 读取账号与密码。"""
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
        else:
            st.error("账号或密码不正确。")
            st.stop()
    else:
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
        # 生产版避免依赖云电脑绝对路径；只保留文件名并尝试在 data/images 中寻找。
        return IMG_DIR / raw.name
    return (BASE_DIR / raw).resolve()


@st.cache_data(show_spinner=False)
def image_to_base64(image_path: str) -> str:
    """读取图片并转为 Base64。缓存后产品网格不会反复访问磁盘。"""
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
    """纯参数报价引擎。后续阶梯报价只需替换此函数。"""
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
# 状态初始化
# ═══════════════════════════════════════════════════════════
def init_session_state() -> None:
    defaults = {
        "authenticated": False,
        "selected_cat": None,
        "selected_prod": None,
        "current_page": "home",
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
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

def sync_selection_from_query(df: pd.DataFrame) -> None:
    """仅兼容外部直达 URL；业务点击全部通过 session_state 完成，避免重新登录。"""
    if st.session_state.get("_query_synced"):
        return
    st.session_state._query_synced = True
    params = st.query_params
    raw_cat = params.get("cat")
    raw_prod = params.get("prod")
    if isinstance(raw_cat, list):
        raw_cat = raw_cat[0] if raw_cat else None
    if isinstance(raw_prod, list):
        raw_prod = raw_prod[0] if raw_prod else None

    valid_categories = set(df["系列"].dropna().astype(str))
    valid_products = set(df["产品名称"].dropna().astype(str))
    category_aliases = {cat: cat for cat in valid_categories}
    category_aliases.update({f"{cat}系列": cat for cat in valid_categories if not cat.endswith("系列")})

    if raw_cat:
        cat = unquote(str(raw_cat)).strip()
        cat = category_aliases.get(cat, cat)
        if cat in valid_categories:
            st.session_state.selected_cat = cat
            st.session_state.current_page = "category"
    if raw_prod:
        prod = unquote(str(raw_prod))
        if prod in valid_products:
            st.session_state.selected_prod = prod
            st.session_state.current_page = "category"
    if st.session_state.selected_cat and not st.session_state.selected_prod:
        cat_df = df[df["系列"].astype(str) == str(st.session_state.selected_cat)]
        if len(cat_df):
            st.session_state.selected_prod = str(cat_df.iloc[0]["产品名称"])

# ═══════════════════════════════════════════════════════════
# UI 渲染层
# ═══════════════════════════════════════════════════════════
def render_sidebar() -> dict[str, Any]:
    """渲染左侧全局配置面板，并返回当前参数。"""
    with st.sidebar:
        st.markdown('<span class="sb-label">铜价（元/吨）</span>', unsafe_allow_html=True)
        copper_price = st.number_input(
            "copper",
            min_value=40000,
            max_value=150000,
            value=int(st.session_state.copper_price),
            step=100,
            label_visibility="collapsed",
        )
        st.session_state.copper_price = copper_price
        if st.button("🔄  同步实时铜价", key="sb_copper", use_container_width=True):
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
            "cur",
            currency_options,
            format_func=lambda item: currency_labels.get(item, item),
            index=currency_options.index(st.session_state.currency),
            label_visibility="collapsed",
        )
        st.session_state.currency = currency
        default_rate = st.session_state.rates.get(currency, DEFAULT_RATES.get(currency, 1.0)) if currency != "RMB" else 1.0
        exchange_rate = st.number_input(
            "rate",
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
            st.markdown(
                f'<p class="sb-hint">报价汇率 = {exchange_rate} × {EXCHANGE_RATE_MARGIN} = <b style="color:#FAFAFA">{effective_rate}</b></p>',
                unsafe_allow_html=True,
            )
        if st.button("🔄  同步实时汇率", key="sb_rate", use_container_width=True):
            with st.spinner("同步汇率中..."):
                st.session_state.rates = cached_exchange_rates()
            st.rerun()

        st.divider()
        st.markdown('<span class="sb-label">标准箱规格</span>', unsafe_allow_html=True)
        col_l, col_w, col_h = st.columns(3)
        with col_l:
            box_l = st.number_input("长cm", value=int(st.session_state.box_l), step=1, format="%d", label_visibility="collapsed")
        with col_w:
            box_w = st.number_input("宽cm", value=int(st.session_state.box_w), step=1, format="%d", label_visibility="collapsed")
        with col_h:
            box_h = st.number_input("高cm", value=int(st.session_state.box_h), step=1, format="%d", label_visibility="collapsed")
        units_per_box = st.number_input("每箱数量", min_value=1, value=int(st.session_state.units_per_box), step=10, label_visibility="collapsed")
        cbm_val = round(box_l * box_w * box_h / 1_000_000, 4)
        st.markdown(
            f'<p class="sb-hint" style="font-family:JetBrains Mono,monospace;font-size:.68rem;color:#6B7280;text-align:center;">{box_l:.0f}×{box_w:.0f}×{box_h:.0f} cm · {cbm_val} CBM · {units_per_box} 只/箱</p>',
            unsafe_allow_html=True,
        )
        st.session_state.box_l, st.session_state.box_w, st.session_state.box_h = box_l, box_w, box_h
        st.session_state.units_per_box = units_per_box

        st.divider()
        st.markdown('<span class="sb-label">数据管理</span>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-upload-wrap">', unsafe_allow_html=True)
        uploaded = st.file_uploader("上传产品明细表", type=["xlsx"], label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)
        if uploaded:
            saved_path = UPLOAD_DIR / uploaded.name
            saved_path.write_bytes(uploaded.getbuffer())
            st.session_state.custom_excel_path = str(saved_path)
            st.cache_data.clear()
            st.rerun()
        if st.session_state.custom_excel_path:
            st.markdown(f'<p class="sb-hint">✓ 当前数据：{Path(st.session_state.custom_excel_path).name}</p>', unsafe_allow_html=True)
            if st.button("恢复默认数据", key="reset_data", use_container_width=True):
                st.session_state.custom_excel_path = None
                st.cache_data.clear()
                st.rerun()

        render_version_block()

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
    """侧边栏底部版本标注与更新说明。"""
    st.markdown(
        f"""
        <div class="version-box">
          <div class="version-text">{APP_VERSION}</div>
          <div style="color:#4B5563;font-size:.66rem;margin-top:4px;">Streamlit Cloud Ready</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("更新说明", expanded=False):
        for item in CHANGELOG:
            st.markdown(f"<p class='sb-hint'>• {item}</p>", unsafe_allow_html=True)


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


def render_category_selector(df: pd.DataFrame) -> None:
    """按 Excel 中的系列动态渲染系列入口，整张卡片点击进入，不使用网页跳转。"""
    st.markdown('<div class="page-title">选择产品系列</div><div class="page-sub">选择阀芯类型，进入产品选择与实时报价工作台。</div>', unsafe_allow_html=True)
    categories = list(df["系列"].dropna().astype(str).unique())
    cols = st.columns(max(1, min(3, len(categories))), gap="small")
    for idx, category in enumerate(categories):
        count = int((df["系列"] == category).sum())
        with cols[idx % len(cols)]:
            icon = "⚡" if "快" in category else "🔩"
            st.markdown(
                f"""
                <div class="cat-click-marker"></div>
                <div class="cat-card">
                  <div class="cat-icon">{icon}</div>
                  <div class="cat-title">{html.escape(category)}系列</div>
                  <div class="cat-desc">来自 products.xlsx 的动态产品系列。新增系列后这里会自动出现入口。</div>
                  <span class="cat-badge">◆ {count} 款产品</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(" ", key=f"cat_card_{idx}_{category}", use_container_width=True):
                st.session_state.selected_cat = category
                cat_df = df[df["系列"] == category].reset_index(drop=True)
                st.session_state.selected_prod = str(cat_df.iloc[0]["产品名称"]) if len(cat_df) else None
                st.session_state.current_page = "category"
                st.rerun()

def render_product_grid(df: pd.DataFrame) -> None:
    """按 Excel 行数动态循环生成产品卡片，整张卡片点击只更新会话状态。"""
    selected_cat = st.session_state.selected_cat
    selected_prod = st.session_state.selected_prod
    safe_cat_title = html.escape(str(selected_cat))
    safe_prod_title = html.escape(str(selected_prod)) if selected_prod else "请选择产品"

    st.markdown('<div class="products-stage">', unsafe_allow_html=True)
    crumb_cols = st.columns([0.9, 0.2, 0.95, 0.2, 1.25, 5.0], gap="small")
    with crumb_cols[0]:
        if st.button("所有系列", key="crumb_all", use_container_width=True):
            st.session_state.selected_cat = None
            st.session_state.selected_prod = None
            st.session_state.current_page = "home"
            st.rerun()
    with crumb_cols[1]:
        st.markdown('<div class="breadcrumb"><span class="crumb-static">/</span></div>', unsafe_allow_html=True)
    with crumb_cols[2]:
        if st.button(f"{selected_cat}系列", key="crumb_cat", use_container_width=True):
            st.session_state.current_page = "category"
            st.rerun()
    with crumb_cols[3]:
        st.markdown('<div class="breadcrumb"><span class="crumb-static">/</span></div>', unsafe_allow_html=True)
    with crumb_cols[4]:
        st.markdown(f'<div class="breadcrumb"><span class="crumb-static crumb-current">{safe_prod_title}</span></div>', unsafe_allow_html=True)

    cat_df = df[df["系列"] == selected_cat].reset_index(drop=True)
    columns_per_row = 4
    for start in range(0, len(cat_df), columns_per_row):
        row_df = cat_df.iloc[start : start + columns_per_row]
        cols = st.columns(columns_per_row, gap="small")
        for offset, (_, product) in enumerate(row_df.iterrows()):
            product_name = str(product["产品名称"])
            with cols[offset]:
                image_b64 = find_product_image(product)
                selected_class = "selected" if selected_prod == product_name else ""
                safe_name = html.escape(product_name)
                image_html = f'<img class="prod-img" src="data:image/png;base64,{image_b64}" alt="{safe_name}">' if image_b64 else '<div class="prod-placeholder">◇</div>'
                st.markdown(
                    f"""
                    <div class="prod-click-marker"></div>
                    <div class="prod-card {selected_class}">
                      {image_html}
                      <div class="prod-name">{safe_name}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button(" ", key=f"prod_card_{start}_{offset}_{product_name}", use_container_width=True):
                    st.session_state.selected_prod = product_name
                    st.session_state.selected_cat = selected_cat
                    st.session_state.current_page = "category"
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def render_series_navigation(df: pd.DataFrame) -> None:
    """三段式布局左栏：系列导航，仅切换会话状态。"""
    st.markdown('<div class="three-col-left"><div class="page-title">系列导航</div><div class="page-sub">点击系列后，中间区域将显示产品卡片。</div>', unsafe_allow_html=True)
    categories = list(df["系列"].dropna().astype(str).unique())
    if st.button("所有系列", key="nav_all_categories", use_container_width=True):
        st.session_state.selected_cat = None
        st.session_state.selected_prod = None
        st.session_state.current_page = "home"
        st.rerun()
    for idx, category in enumerate(categories):
        count = int((df["系列"] == category).sum())
        label = f"{category}系列 · {count}款"
        if st.button(label, key=f"nav_cat_{idx}_{category}", use_container_width=True):
            st.session_state.selected_cat = category
            cat_df = df[df["系列"] == category].reset_index(drop=True)
            st.session_state.selected_prod = str(cat_df.iloc[0]["产品名称"]) if len(cat_df) else None
            st.session_state.current_page = "category"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def render_product_empty_state(df: pd.DataFrame) -> None:
    """三段式布局中栏：未选系列时的提示区。"""
    category_count = df["系列"].nunique()
    product_count = len(df)
    st.markdown(
        f"""
        <div class="tool-card" style="min-height:360px;display:flex;align-items:center;justify-content:center;text-align:left;">
          <div>
            <div class="page-title">请选择左侧产品系列</div>
            <div class="page-sub" style="max-width:520px;line-height:1.8;">当前数据库包含 {category_count} 个系列、{product_count} 款产品。选择系列后，中间区域会显示该系列产品卡片；点击任意卡片即可在右侧生成实时报价。</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_product_specs(product: pd.Series) -> None:
    """渲染当前产品规格条。"""
    st.markdown(
        f"""
        <div class="spec-strip">
          <div class="spec-cell"><div class="sc-label">净铜重</div><div class="sc-val">{float(product['净铜重_g']):.1f}g</div><div class="sc-sub">总重 {float(product['产品总重_g']):.1f}g</div></div>
          <div class="spec-cell"><div class="sc-label">加工+配件</div><div class="sc-val">¥{float(product['加工费_元']):.2f}</div><div class="sc-sub">配件 {float(product['配件重量_g']):.1f}g</div></div>
          <div class="spec-cell"><div class="sc-label">利润</div><div class="sc-val">¥{float(product['利润_元']):.2f}</div><div class="sc-sub">{product.get('系列', '—')} 系列</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if "⚠️" in str(product.get("总重是否已称量", "")):
        st.markdown('<div class="warn-bar">⚠ 产品总重为估算值，请向车间确认后更新 products.xlsx 以提高报价精度。</div>', unsafe_allow_html=True)


def render_quote_controls() -> None:
    """渲染单产品报价参数。"""
    st.markdown('<div class="page-sub" style="margin-bottom:.5rem;">报价参数</div>', unsafe_allow_html=True)
    col_a, col_b, col_c, col_d = st.columns(4, gap="small")
    with col_a:
        plating_options = list(PLATING_RATES.keys())
        st.session_state.plating = st.selectbox("表面处理", plating_options, index=plating_options.index(st.session_state.plating), key="cfg_plating")
    with col_b:
        st.session_state.packaging = st.multiselect("包装附加", list(PACKAGING_FEES.keys()), default=st.session_state.packaging, key="cfg_packaging")
    with col_c:
        st.session_state.quantity = st.number_input("订单数量（只）", min_value=1, value=int(st.session_state.quantity), step=100, key="cfg_quantity")
    with col_d:
        destination_options = list(FREIGHT_RATES.keys())
        st.session_state.destination = st.selectbox("目的地", destination_options, index=destination_options.index(st.session_state.destination), key="cfg_destination")


def get_selected_product(df: pd.DataFrame) -> pd.Series | None:
    product_name = st.session_state.selected_prod
    if not product_name:
        return None
    matched = df[df["产品名称"] == product_name]
    return matched.iloc[0] if len(matched) else None


def render_quote_panel(product: pd.Series | None, params: dict[str, Any]) -> None:
    """渲染右侧报价卡片。"""
    if product is None:
        title = "开始报价" if st.session_state.selected_cat is None else "选择产品"
        desc = "先选择产品系列，然后选择具体产品。" if st.session_state.selected_cat is None else "点击中间任意产品卡片后，报价结果将在这里实时显示。"
        st.markdown(
            f"""
            <div class="quote-card">
              <div style="min-height:420px;display:flex;align-items:center;justify-content:center;text-align:center;">
                <div>
                  <div style="font-size:2rem;color:#6B7280;margin-bottom:1rem;">◇</div>
                  <div style="font-size:1rem;font-weight:800;color:#D1D5DB;margin-bottom:8px;">{title}</div>
                  <div style="font-size:.78rem;color:#9CA3AF;line-height:1.6;">{desc}</div>
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
        pill_class, arrow = "mp-good", "↑"
    elif margin >= 8:
        pill_class, arrow = "mp-warn", "→"
    else:
        pill_class, arrow = "mp-danger", "↓"

    safe_product_name = html.escape(str(product['产品名称']))
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
            <div class="ph-row"><div class="ot-label">订单总价</div><div style="color:#9CA3AF;font-size:.62rem;font-family:JetBrains Mono,monospace;">{int(st.session_state.quantity):,} 只</div></div>
            <div class="ot-val">{symbol}{quote['total']:,.2f}</div>
            <div class="ot-sub">{symbol}{quote['fgn']:.4f} × {int(st.session_state.quantity):,} {currency}</div>
          </div>
          <div class="margin-row"><span class="margin-label">利润率</span><span class="margin-pill {pill_class}">{arrow} {margin}%</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("☷ 成本构成明细", expanded=False):
        cost_items = [
            ("原材料", quote["原材料"], "#635BFF"),
            ("加工+配件", quote["加工配件"], "#22C55E"),
            ("电镀", quote["电镀"], "#EAB308"),
            ("包装", quote["包装"], "#8B5CF6"),
            ("运费", quote["运费"], "#3B82F6"),
            ("利润", quote["利润"], "#EF4444"),
        ]
        for name, value, color in cost_items:
            pct = round(value / quote["rmb"] * 100, 1) if quote["rmb"] else 0
            st.markdown(
                f"<div class='cost-row'><span class='cost-dot' style='background:{color}'></span><span class='cost-name'>{name}</span><span class='cost-val'>¥{value:.3f}</span><span class='cost-pct'>{pct}%</span></div>",
                unsafe_allow_html=True,
            )

    with st.expander("≡ 查看计算公式", expanded=False):
        formula = (
            f"原材料 = {quote['net_g']}g × {params['copper_price']:,.0f} / 1,000,000 = ¥{quote['原材料']}\n"
            f"电镀   = {quote['net_g']}g × {PLATING_RATES.get(st.session_state.plating, 0):,} / 1,000,000 = ¥{quote['电镀']}\n"
            f"运费   = {FREIGHT_RATES.get(st.session_state.destination, 0)} $/CBM × {quote['cbm']} CBM / {params['units_per_box']} × {params['exchange_rate']} = ¥{quote['运费']}\n"
            f"{'─' * 30}\n"
            f"RMB    = {quote['原材料']} + {quote['加工配件']} + {quote['电镀']} + {quote['包装']} + {quote['运费']} + {quote['利润']} = ¥{quote['rmb']}\n"
            f"{currency} = ¥{quote['rmb']} / {quote['eff_rate']} = {symbol}{quote['fgn']}"
        )
        st.markdown(f"<div class='formula'>{formula}</div>", unsafe_allow_html=True)



def render_workbench(df: pd.DataFrame, params: dict[str, Any]) -> None:
    """渲染生产三段式工作台：左导航 / 中间产品 / 右报价。"""
    st.markdown('<div id="workbench"></div>', unsafe_allow_html=True)
    left_col, mid_col, right_col = st.columns([1.1, 2.0, 1.4], gap="large")

    with left_col:
        render_series_navigation(df)

    with mid_col:
        st.markdown('<div class="three-col-mid">', unsafe_allow_html=True)
        if st.session_state.selected_cat is None or st.session_state.get("current_page") == "home":
            render_category_selector(df)
        else:
            render_product_grid(df)
            selected = get_selected_product(df)
            if selected is not None:
                st.markdown('<div class="products-stage" style="margin-top:14px;">', unsafe_allow_html=True)
                render_product_specs(selected)
                render_quote_controls()
                st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with right_col:
        st.markdown('<div class="quote-column-marker"></div><div class="three-col-right">', unsafe_allow_html=True)
        render_quote_panel(get_selected_product(df), params)
        st.markdown('</div>', unsafe_allow_html=True)

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
        if st.button("生成全产品报价表", key="batch_generate"):
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
                "总重是否已称量": ["✅ 已称量", "⚠️ 估算值"],
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
        f"<div style='text-align:center;color:#4B5563;font-size:.66rem;padding:1.2rem 0;'>ValveCore Pricing {APP_VERSION} · 产品参数来自 ./data/products.xlsx · 汇率含 {int((1-EXCHANGE_RATE_MARGIN)*100)}% 安全边际</div>",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════
# 应用入口
# ═══════════════════════════════════════════════════════════
def main() -> None:
    inject_css()
    init_session_state()
    require_login()

    params = render_sidebar()
    data_file = st.session_state.custom_excel_path or str(DEFAULT_PRODUCTS_FILE)
    try:
        products_df = load_products(data_file)
    except Exception as exc:
        st.error(f"产品数据库加载失败：{exc}")
        st.stop()

    sync_selection_from_query(products_df)
    render_header(products_df, params)
    render_workbench(products_df, params)
    render_bottom_tools(products_df, params)
    render_footer()


if __name__ == "__main__":
    main()
