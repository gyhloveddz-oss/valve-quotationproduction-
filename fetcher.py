"""
fetcher.py
实时数据抓取模块
- 铜价：长江有色金属网 (lme.com.cn / ccmn.cn)
- 汇率：exchangerate-api.com (免费) + 备用 fixer.io
"""
import requests
from bs4 import BeautifulSoup
import re
import time

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ── 铜价抓取 ──────────────────────────────────────────────

def fetch_copper_price_ccmn() -> float | None:
    """
    从长江有色金属网 (ccmn.cn) 抓取当日铜价（元/吨）
    目标：1# 铜 现货均价
    """
    try:
        url = "https://ccmn.cn/nonferrous/Cu.shtml"
        resp = requests.get(url, headers=HEADERS, timeout=8)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

        # 查找含"铜"价格的表格行
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
                text = " ".join(cells)
                if "1#铜" in text or "1# 铜" in text or "电解铜" in text:
                    for cell in cells:
                        # 匹配 5~6 位数字（铜价范围 40000~120000）
                        m = re.search(r"\b([4-9]\d{4}|1[0-2]\d{4})\b", cell.replace(",", ""))
                        if m:
                            return float(m.group(1))
    except Exception:
        pass
    return None


def fetch_copper_price_smm() -> float | None:
    """
    备用：从上海有色网 (smm.cn) 抓取铜价
    """
    try:
        url = "https://www.smm.cn/copper"
        resp = requests.get(url, headers=HEADERS, timeout=8)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

        # 查找价格数字
        for tag in soup.find_all(string=re.compile(r"[4-9]\d{4}")):
            m = re.search(r"\b([4-9]\d{4}|1[0-2]\d{4})\b", tag.replace(",", ""))
            if m:
                val = float(m.group(1))
                if 40000 <= val <= 120000:
                    return val
    except Exception:
        pass
    return None


def fetch_copper_price_lme() -> float | None:
    """
    备用2：从 LME 官网抓取铜价（USD/吨），转换为人民币
    """
    try:
        url = "https://www.lme.com/en/metals/non-ferrous/lme-copper"
        resp = requests.get(url, headers=HEADERS, timeout=8)
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup.find_all(string=re.compile(r"\d{4,5}\.\d{2}")):
            m = re.search(r"(\d{4,5}\.\d{2})", tag)
            if m:
                usd_price = float(m.group(1))
                if 4000 <= usd_price <= 15000:
                    # 转换为人民币（粗略用 7.25）
                    rate = fetch_exchange_rate("USD") or 7.25
                    return round(usd_price * rate, 0)
    except Exception:
        pass
    return None


def get_copper_price() -> dict:
    """
    主函数：依次尝试多个数据源，返回铜价和来源信息
    返回: {"price": float, "source": str, "success": bool}
    """
    # 尝试长江有色
    price = fetch_copper_price_ccmn()
    if price:
        return {"price": price, "source": "长江有色金属网", "success": True}

    # 尝试上海有色
    price = fetch_copper_price_smm()
    if price:
        return {"price": price, "source": "上海有色网(SMM)", "success": True}

    # 尝试 LME
    price = fetch_copper_price_lme()
    if price:
        return {"price": price, "source": "LME(换算)", "success": True}

    # 全部失败，返回默认值
    return {"price": 78500.0, "source": "默认值（网络获取失败）", "success": False}


# ── 汇率抓取 ──────────────────────────────────────────────

def fetch_exchange_rate(currency: str) -> float | None:
    """
    从 exchangerate-api.com 获取实时汇率
    返回：1 {currency} = ? RMB
    """
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/CNY"
        resp = requests.get(url, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            rates = data.get("rates", {})
            rate_cny_to_currency = rates.get(currency)
            if rate_cny_to_currency and rate_cny_to_currency > 0:
                return round(1.0 / rate_cny_to_currency, 4)
    except Exception:
        pass
    return None


def fetch_exchange_rate_backup(currency: str) -> float | None:
    """
    备用汇率源：frankfurter.app（欧洲央行数据）
    """
    try:
        url = f"https://api.frankfurter.app/latest?from=CNY&to={currency}"
        resp = requests.get(url, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            rate_cny_to_currency = data.get("rates", {}).get(currency)
            if rate_cny_to_currency and rate_cny_to_currency > 0:
                return round(1.0 / rate_cny_to_currency, 4)
    except Exception:
        pass
    return None


# 货币默认值（网络失败时使用）
DEFAULT_RATES = {
    "USD": 7.25,
    "EUR": 7.85,
    "AED": 1.97,
    "SAR": 1.93,
    "MYR": 1.60,
    "IDR": 0.00046,
    "BRL": 1.35,
    "NGN": 0.0046,
}


def get_all_rates() -> dict:
    """
    批量获取所有支持货币的汇率
    返回: {"USD": 7.25, "EUR": 7.85, ..., "_source": "...", "_success": True}
    """
    results = {}
    source = "默认值（网络获取失败）"
    success = False

    # 尝试主源
    try:
        url = "https://api.exchangerate-api.com/v4/latest/CNY"
        resp = requests.get(url, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            rates = data.get("rates", {})
            for currency in DEFAULT_RATES:
                r = rates.get(currency)
                if r and r > 0:
                    results[currency] = round(1.0 / r, 4)
                else:
                    results[currency] = DEFAULT_RATES[currency]
            source = "ExchangeRate-API（实时）"
            success = True
    except Exception:
        pass

    # 主源失败，尝试备用源
    if not success:
        try:
            currencies_str = ",".join(DEFAULT_RATES.keys())
            url = f"https://api.frankfurter.app/latest?from=CNY&to={currencies_str}"
            resp = requests.get(url, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                rates = data.get("rates", {})
                for currency in DEFAULT_RATES:
                    r = rates.get(currency)
                    if r and r > 0:
                        results[currency] = round(1.0 / r, 4)
                    else:
                        results[currency] = DEFAULT_RATES[currency]
                source = "Frankfurter（欧洲央行）"
                success = True
        except Exception:
            pass

    # 全部失败，使用默认值
    if not success:
        results = dict(DEFAULT_RATES)

    results["_source"] = source
    results["_success"] = success
    return results


# ── 测试入口 ──────────────────────────────────────────────
if __name__ == "__main__":
    print("=== 铜价测试 ===")
    copper = get_copper_price()
    print(f"铜价: {copper['price']:,.0f} 元/吨  来源: {copper['source']}  成功: {copper['success']}")

    print("\n=== 汇率测试 ===")
    rates = get_all_rates()
    for k, v in rates.items():
        if not k.startswith("_"):
            print(f"  1 {k} = {v} RMB")
    print(f"  来源: {rates['_source']}  成功: {rates['_success']}")
