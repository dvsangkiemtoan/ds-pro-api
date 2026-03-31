"""
DS Pro V9.9 - Stock Data API for Render
Multi-source with FireAnt historical for closing prices
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import List, Dict, Any
import time
import os
import requests

app = FastAPI(title="DS Pro Stock API", version="9.9")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache
cache = {}
cache_time = {}

def get_cache(key: str, ttl: int = 120) -> Any:
    if key in cache and time.time() - cache_time.get(key, 0) < ttl:
        return cache[key]
    return None

def set_cache(key: str, value: Any):
    cache[key] = value
    cache_time[key] = time.time()

def is_market_hours() -> bool:
    """Kiểm tra có phải giờ giao dịch không (9:00-11:30, 13:00-15:00)"""
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    current_time = hour * 60 + minute
    
    if now.weekday() >= 5:  # Thứ 7, Chủ nhật
        return False
    
    if 9 * 60 <= current_time <= 11 * 60 + 30:
        return True
    if 13 * 60 <= current_time <= 15 * 60:
        return True
    return False

# ==========================================
# DANH SÁCH CỔ PHIẾU
# ==========================================

ALL_STOCKS = [
    "VCB", "BID", "CTG", "TCB", "MBB", "ACB", "VPB", "TPB", "STB", "HDB",
    "VIC", "VHM", "VRE", "NVL", "KDH", "PDR", "DXS", "NLG", "HPG", "FPT",
    "MWG", "PNJ", "VNM", "MSN", "GAS", "PLX", "SAB", "VJC", "SHB", "SSI",
    "VIB", "LPB", "MSB", "OCB", "NAB", "ABB", "EIB", "SGB", "PGB", "BVB",
    "CMG", "GEX", "VGI", "CTR", "FRT", "PET", "DGW", "HSG", "NKG", "VHC",
    "DCM", "DGC", "DPM", "PVC", "PVT", "PVS", "PVD", "BSR", "OIL", "POW",
    "NT2", "BWE", "GMD", "SCS", "TCL", "VSC", "VTO", "SBT", "KDC", "IMP",
    "ELC", "VGT", "TNG", "TLG", "VOS", "ITA", "LHG", "HAG", "HNG", "ASM",
]

def get_all_stocks() -> List[str]:
    return ALL_STOCKS

# ==========================================
# HÀM TÍNH TOÁN CHỈ BÁO
# ==========================================

def calculate_ma(data: List[float], period: int) -> float:
    if len(data) < period:
        return data[-1] if data else 0
    return sum(data[-period:]) / period

def calculate_rsi(data: List[float], period: int = 14) -> float:
    if len(data) < period + 1:
        return 55
    
    gains, losses = 0, 0
    for i in range(-period, 0):
        change = data[i] - data[i-1]
        if change > 0:
            gains += change
        else:
            losses += abs(change)
    
    avg_gain = gains / period
    avg_loss = losses / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_adx(highs, lows, closes, period=14):
    if len(highs) < period + 1:
        return 20
    
    plus_dm, minus_dm, tr = [], [], []
    for i in range(1, len(highs)):
        high_diff = highs[i] - highs[i-1]
        low_diff = lows[i-1] - lows[i]
        
        plus_dm.append(high_diff if high_diff > low_diff and high_diff > 0 else 0)
        minus_dm.append(low_diff if low_diff > high_diff and low_diff > 0 else 0)
        
        tr1 = highs[i] - lows[i]
        tr2 = abs(highs[i] - closes[i-1])
        tr3 = abs(lows[i] - closes[i-1])
        tr.append(max(tr1, tr2, tr3))
    
    plus_dm_smooth = calculate_ma(plus_dm[-period:], period)
    minus_dm_smooth = calculate_ma(minus_dm[-period:], period)
    tr_smooth = calculate_ma(tr[-period:], period)
    
    if tr_smooth == 0:
        return 20
    
    plus_di = (plus_dm_smooth / tr_smooth) * 100
    minus_di = (minus_dm_smooth / tr_smooth) * 100
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    
    return dx

def calculate_atr(highs, lows, closes, period=14):
    if len(highs) < period + 1:
        return 0
    
    tr_values = []
    for i in range(1, len(highs)):
        tr1 = highs[i] - lows[i]
        tr2 = abs(highs[i] - closes[i-1])
        tr3 = abs(lows[i] - closes[i-1])
        tr_values.append(max(tr1, tr2, tr3))
    
    return calculate_ma(tr_values[-period:], period)

def calculate_risk_reward_vn(price, atr, adx):
    risk = atr * 1.5
    if adx > 40:
        reward = atr * 4.5
    elif adx > 30:
        reward = atr * 3.5
    elif adx > 20:
        reward = atr * 2.5
    else:
        reward = atr * 1.8
    
    rr = reward / risk if risk > 0 else 0
    return min(4, rr)

def calculate_score(price, ma20, ma50, rsi, volume_ratio, adx, rr_ratio):
    """Tính điểm theo chiến lược 3 tầng"""
    score = 50
    
    if volume_ratio > 1.5:
        score += 20
    elif volume_ratio > 1.2:
        score += 10
    
    if price > ma20 and (price - ma20) / ma20 < 0.02:
        score += 10
    
    if price > ma20:
        score += 15
    if ma20 > ma50:
        score += 20
    if price > ma50:
        score += 10
    if 40 < rsi < 70:
        score += 10
    
    if volume_ratio > 2:
        score += 15
    elif volume_ratio > 1.5:
        score += 10
    
    if adx > 40:
        score += 15
    elif adx > 30:
        score += 10
    elif adx > 20:
        score += 5
    
    if rr_ratio >= 3:
        score += 15
    elif rr_ratio >= 2:
        score += 10
    elif rr_ratio >= 1.5:
        score += 5
    
    return min(100, max(0, round(score)))

# ==========================================
# PHÂN NHÓM VỐN HÓA
# ==========================================

MARKET_CAP = {
    "VCB": 350000, "BID": 280000, "CTG": 210000, "TCB": 180000, "MBB": 120000,
    "ACB": 110000, "VPB": 100000, "TPB": 80000, "STB": 70000, "HDB": 65000,
    "VIC": 130000, "VHM": 150000, "VRE": 60000, "HPG": 140000, "FPT": 95000,
    "MWG": 75000, "PNJ": 40000, "VNM": 160000, "MSN": 80000, "GAS": 170000,
    "PLX": 55000, "SAB": 50000, "VJC": 45000, "SHB": 35000, "SSI": 30000,
}

def get_stock_group(symbol: str) -> str:
    cap = MARKET_CAP.get(symbol, 0)
    if cap >= 50000:
        return "BLUE_CHIP"
    elif cap >= 10000:
        return "MID_CAP"
    elif cap >= 3000:
        return "SMALL_CAP"
    else:
        return "PENNY"

# ==========================================
# DỮ LIỆU MẪU (FALLBACK CUỐI CÙNG)
# ==========================================

SAMPLE_PRICES = {
    "VCB": 89500, "BID": 52500, "CTG": 34500, "TCB": 42800, "MBB": 25600,
    "ACB": 28900, "VPB": 19600, "TPB": 27800, "STB": 31900, "HDB": 25800,
    "VIC": 43500, "VHM": 48500, "VRE": 28500, "NVL": 14800, "KDH": 32800,
    "HPG": 26500, "FPT": 76000, "MWG": 81000, "PNJ": 94500, "VNM": 74500,
    "MSN": 72500, "GAS": 118500, "PLX": 36500, "SAB": 168500, "VJC": 104500,
}

def get_sample_data(symbol: str) -> Dict[str, Any]:
    """Trả về dữ liệu mẫu khi không lấy được dữ liệu từ bất kỳ nguồn nào"""
    price = SAMPLE_PRICES.get(symbol, 50000)
    ma20 = price * 0.98
    ma50 = price * 0.96
    
    return {
        'price': price,
        'change': 0,
        'changePercent': 0,
        'volume': 1000000,
        'high': price * 1.01,
        'low': price * 0.99,
        'open': price,
        'ma20': round(ma20, 2),
        'ma50': round(ma50, 2),
        'rsi': 55,
        'adx': 25,
        'atr': price * 0.02,
        'rr_ratio': 1.5,
        'avgVolume20': 1000000,
        'volume_ratio': 1,
        'score': 65,
        'source': 'sample',
        'time': datetime.now().isoformat(),
        'market_hours': is_market_hours()
    }

# ==========================================
# NGUỒN CHÍNH: FIRANT LỊCH SỬ (GIÁ ĐÓNG CỬA)
# ==========================================

def fetch_from_fireant_historical(symbol: str) -> Dict[str, Any]:
    """
    Lấy dữ liệu lịch sử từ FireAnt API (giá đóng cửa)
    HOẠT ĐỘNG MỌI LÚC
    """
    try:
        end = datetime.now()
        start = end - timedelta(days=60)
        
        url = "https://www.fireant.vn/api/Data/StockPriceHistory"
        params = {
            'symbols': symbol,
            'startDate': start.strftime("%Y-%m-%d"),
            'endDate': end.strftime("%Y-%m-%d")
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': 'https://www.fireant.vn/'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"FireAnt history error: HTTP {response.status_code}")
            return None
        
        data = response.json()
        
        if not data or 'data' not in data:
            print(f"No data in FireAnt response for {symbol}")
            return None
        
        history = data['data'].get(symbol)
        if not history or len(history) == 0:
            print(f"No history for {symbol}")
            return None
        
        # Lấy ngày gần nhất
        latest = history[-1]
        price = latest.get('close', 0)
        if price == 0:
            print(f"Price is 0 for {symbol}")
            return None
        
        # Tính chỉ báo từ lịch sử
        closes = [day.get('close', 0) for day in history if day.get('close', 0) > 0]
        volumes = [day.get('volume', 0) for day in history]
        highs = [day.get('high', 0) for day in history]
        lows = [day.get('low', 0) for day in history]
        
        if len(closes) < 20:
            print(f"Not enough history for {symbol}, only {len(closes)} days")
            return None
        
        ma20 = calculate_ma(closes, 20)
        ma50 = calculate_ma(closes, 50)
        rsi = calculate_rsi(closes, 14)
        adx = calculate_adx(highs, lows, closes, 14)
        atr = calculate_atr(highs, lows, closes, 14)
        avg_volume = calculate_ma(volumes, 20) if volumes else 0
        
        volume = latest.get('volume', 0)
        high = latest.get('high', price)
        low = latest.get('low', price)
        open_price = latest.get('open', price)
        
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1
        rr_ratio = calculate_risk_reward_vn(price, atr, adx)
        score = calculate_score(price, ma20, ma50, rsi, volume_ratio, adx, rr_ratio)
        
        print(f"✅ Got {symbol} from FireAnt historical: {price}")
        
        return {
            'price': price,
            'change': 0,
            'changePercent': 0,
            'volume': volume,
            'high': high,
            'low': low,
            'open': open_price,
            'ma20': round(ma20, 2),
            'ma50': round(ma50, 2),
            'rsi': round(rsi, 2),
            'adx': round(adx, 2),
            'atr': round(atr, 2),
            'rr_ratio': round(rr_ratio, 2),
            'avgVolume20': round(avg_volume, 0),
            'volume_ratio': round(volume_ratio, 2),
            'score': score,
            'source': 'fireant_historical',
            'time': datetime.now().isoformat(),
            'market_hours': is_market_hours()
        }
        
    except Exception as e:
        print(f"FireAnt historical error for {symbol}: {e}")
        return None

# ==========================================
# NGUỒN 2: VNSTOCK LỊCH SỬ (FALLBACK)
# ==========================================

def fetch_from_vnstock_historical(symbol: str) -> Dict[str, Any]:
    """
    Lấy dữ liệu lịch sử từ vnstock (dự phòng)
    """
    try:
        from vnstock import Vnstock
        
        stock = Vnstock().stock(symbol=symbol, source="VCI")
        
        end = datetime.now()
        start = end - timedelta(days=60)
        history = stock.quote.history(
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d")
        )
        
        if history.empty:
            return None
        
        latest = history.iloc[-1]
        price = float(latest['close'])
        
        if price == 0:
            return None
        
        closes = history['close'].tolist()
        volumes = history['volume'].tolist()
        highs = history['high'].tolist()
        lows = history['low'].tolist()
        
        ma20 = calculate_ma(closes, 20)
        ma50 = calculate_ma(closes, 50)
        rsi = calculate_rsi(closes, 14)
        adx = calculate_adx(highs, lows, closes, 14)
        atr = calculate_atr(highs, lows, closes, 14)
        avg_volume = calculate_ma(volumes, 20) if volumes else 0
        
        volume = float(latest['volume']) if latest['volume'] else 0
        high = float(latest['high']) if latest['high'] else price
        low = float(latest['low']) if latest['low'] else price
        open_price = float(latest['open']) if latest['open'] else price
        
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1
        rr_ratio = calculate_risk_reward_vn(price, atr, adx)
        score = calculate_score(price, ma20, ma50, rsi, volume_ratio, adx, rr_ratio)
        
        print(f"✅ Got {symbol} from vnstock historical: {price}")
        
        return {
            'price': price,
            'change': 0,
            'changePercent': 0,
            'volume': volume,
            'high': high,
            'low': low,
            'open': open_price,
            'ma20': round(ma20, 2),
            'ma50': round(ma50, 2),
            'rsi': round(rsi, 2),
            'adx': round(adx, 2),
            'atr': round(atr, 2),
            'rr_ratio': round(rr_ratio, 2),
            'avgVolume20': round(avg_volume, 0),
            'volume_ratio': round(volume_ratio, 2),
            'score': score,
            'source': 'vnstock_historical',
            'time': datetime.now().isoformat(),
            'market_hours': is_market_hours()
        }
        
    except Exception as e:
        print(f"Vnstock historical error for {symbol}: {e}")
        return None

# ==========================================
# NGUỒN 3: FIRANT REALTIME (TRONG GIỜ)
# ==========================================

def fetch_from_fireant(symbol: str) -> Dict[str, Any]:
    """Lấy dữ liệu realtime từ FireAnt"""
    try:
        url = f"https://www.fireant.vn/api/Data/StockPrices?symbols={symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json',
            'Referer': 'https://www.fireant.vn/'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        if not data or 'data' not in data:
            return None
        
        stock_data = data['data'].get(symbol)
        if not stock_data:
            return None
        
        price = stock_data.get('price', 0)
        if price == 0:
            return None
        
        print(f"✅ Got {symbol} from FireAnt realtime: {price}")
        
        # Lấy thêm lịch sử để tính MA
        hist_data = fetch_from_fireant_historical(symbol)
        if hist_data:
            hist_data['source'] = 'fireant'
            hist_data['price'] = price
            hist_data['change'] = stock_data.get('change', 0)
            hist_data['changePercent'] = stock_data.get('changePercent', 0)
            hist_data['volume'] = stock_data.get('volume', 0)
            hist_data['high'] = stock_data.get('high', price)
            hist_data['low'] = stock_data.get('low', price)
            hist_data['open'] = stock_data.get('open', price)
            return hist_data
        
        return {
            'price': price,
            'change': stock_data.get('change', 0),
            'changePercent': stock_data.get('changePercent', 0),
            'volume': stock_data.get('volume', 0),
            'high': stock_data.get('high', price),
            'low': stock_data.get('low', price),
            'open': stock_data.get('open', price),
            'source': 'fireant',
            'time': datetime.now().isoformat(),
            'market_hours': is_market_hours()
        }
        
    except Exception as e:
        print(f"FireAnt error for {symbol}: {e}")
        return None

# ==========================================
# NGUỒN 4: VCBS (TRONG GIỜ)
# ==========================================

def fetch_from_vcbs(symbol: str) -> Dict[str, Any]:
    """Lấy dữ liệu realtime từ VCBS"""
    try:
        url = "https://priceboard.vcbs.com.vn/PriceBoard"
        payload = {
            'symbols': symbol,
            'btn_ChBx_Realtime': '1'
        }
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        response = requests.post(url, data=payload, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        if not data or not isinstance(data, list) or len(data) == 0:
            return None
        
        item = data[0]
        price = item.get('gia', 0)
        if price == 0:
            return None
        
        print(f"✅ Got {symbol} from VCBS: {price}")
        
        hist_data = fetch_from_fireant_historical(symbol)
        if hist_data:
            hist_data['source'] = 'vcbs'
            hist_data['price'] = price
            hist_data['change'] = item.get('thaydoi', 0)
            hist_data['changePercent'] = item.get('tylechua', 0)
            hist_data['volume'] = item.get('khoiluong', 0)
            hist_data['high'] = item.get('giaCao', price)
            hist_data['low'] = item.get('giaThap', price)
            hist_data['open'] = item.get('giaMoCua', price)
            return hist_data
        
        return {
            'price': price,
            'change': item.get('thaydoi', 0),
            'changePercent': item.get('tylechua', 0),
            'volume': item.get('khoiluong', 0),
            'high': item.get('giaCao', price),
            'low': item.get('giaThap', price),
            'open': item.get('giaMoCua', price),
            'source': 'vcbs',
            'time': datetime.now().isoformat(),
            'market_hours': is_market_hours()
        }
        
    except Exception as e:
        print(f"VCBS error for {symbol}: {e}")
        return None

# ==========================================
# NGUỒN 5: CAFEF (GIÁ ĐÓNG CỬA)
# ==========================================

def fetch_from_cafef(symbol: str) -> Dict[str, Any]:
    """Lấy dữ liệu giá đóng cửa từ CafeF"""
    try:
        yesterday = datetime.now() - timedelta(days=1)
        while yesterday.weekday() >= 5:
            yesterday -= timedelta(days=1)
        
        date_str = yesterday.strftime("%d/%m/%Y")
        
        url = f"https://api.cafef.vn/pricehistory?symbol={symbol}&fromDate={date_str}&toDate={date_str}"
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        if not data or 'data' not in data or len(data['data']) == 0:
            return None
        
        day_data = data['data'][0]
        price = day_data.get('close', 0)
        if price == 0:
            return None
        
        print(f"✅ Got {symbol} from CafeF: {price}")
        
        hist_data = fetch_from_fireant_historical(symbol)
        if hist_data:
            hist_data['source'] = 'cafef'
            hist_data['price'] = price
            return hist_data
        
        return {
            'price': price,
            'change': 0,
            'changePercent': 0,
            'volume': day_data.get('volume', 0),
            'high': day_data.get('high', price),
            'low': day_data.get('low', price),
            'open': day_data.get('open', price),
            'source': 'cafef',
            'time': datetime.now().isoformat(),
            'market_hours': is_market_hours()
        }
        
    except Exception as e:
        print(f"CafeF error for {symbol}: {e}")
        return None

# ==========================================
# HÀM CHÍNH LẤY DỮ LIỆU
# ==========================================

def get_stock_data(symbol: str) -> Dict[str, Any]:
    """
    Lấy dữ liệu từ nhiều nguồn
    Thứ tự: FireAnt lịch sử -> Vnstock lịch sử -> FireAnt realtime -> VCBS -> CafeF -> Sample
    """
    # 1. FireAnt lịch sử - HOẠT ĐỘNG MỌI LÚC
    data = fetch_from_fireant_historical(symbol)
    if data:
        return data
    
    # 2. Vnstock lịch sử
    data = fetch_from_vnstock_historical(symbol)
    if data:
        return data
    
    # 3. FireAnt realtime (chỉ trong giờ)
    if is_market_hours():
        data = fetch_from_fireant(symbol)
        if data:
            return data
    
    # 4. VCBS (chỉ trong giờ)
    if is_market_hours():
        data = fetch_from_vcbs(symbol)
        if data:
            return data
    
    # 5. CafeF
    data = fetch_from_cafef(symbol)
    if data:
        return data
    
    # 6. Sample
    print(f"⚠️ Using sample data for {symbol}")
    return get_sample_data(symbol)

def get_stock_data_batch(symbols: List[str]) -> Dict[str, Any]:
    """Lấy dữ liệu batch"""
    result = {}
    start_time = time.time()
    max_time = 25
    
    for symbol in symbols:
        if time.time() - start_time > max_time:
            print(f"⏰ Timeout at {symbol}")
            break
        try:
            data = get_stock_data(symbol)
            if data:
                result[symbol] = data
        except Exception as e:
            print(f"Error {symbol}: {e}")
    
    return result

# ==========================================
# API ENDPOINTS
# ==========================================

@app.get("/")
async def root():
    return {
        "message": "DS Pro Stock API v9.9",
        "status": "running",
        "total_stocks": len(get_all_stocks()),
        "market_hours": is_market_hours(),
        "data_sources": ["FireAnt_Historical", "Vnstock_Historical", "FireAnt_Realtime", "VCBS", "CafeF"],
        "endpoints": {
            "health": "/health",
            "price": "/api/price?symbols=VCB,FPT",
            "all": "/api/all/combined",
            "ranking": "/api/ranking",
            "test": "/api/test/{symbol}"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "total_stocks": len(get_all_stocks()),
        "market_hours": is_market_hours(),
        "cache_size": len(cache)
    }

@app.get("/api/test/{symbol}")
async def test_symbol(symbol: str):
    """Test endpoint để debug"""
    data = get_stock_data(symbol.upper())
    if data:
        return {"symbol": symbol, "success": True, "data": data}
    return {"symbol": symbol, "success": False, "error": "Cannot fetch data from any source"}

@app.get("/api/price")
async def get_price(symbols: str = Query(..., description="Mã cổ phiếu")):
    """Lấy giá realtime cho các mã cổ phiếu"""
    symbol_list = [s.strip().upper() for s in symbols.split(',')][:30]
    data = {}
    
    for symbol in symbol_list:
        stock_data = get_stock_data(symbol)
        if stock_data:
            data[symbol] = stock_data
    
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "market_hours": is_market_hours(),
        "count": len(data),
        "data": data
    }

@app.get("/api/all/combined")
async def get_all_combined():
    """Lấy tất cả dữ liệu"""
    cache_key = "all_combined"
    cached = get_cache(cache_key, 120)
    if cached:
        return cached
    
    all_stocks = get_all_stocks()
    limit = 100
    total_pages = (len(all_stocks) + limit - 1) // limit
    
    all_data = {}
    for page in range(1, total_pages + 1):
        start = (page - 1) * limit
        end = start + limit
        symbols = all_stocks[start:end]
        print(f"📡 Fetching page {page}/{total_pages}: {len(symbols)} stocks")
        page_data = get_stock_data_batch(symbols)
        all_data.update(page_data)
        if page < total_pages:
            time.sleep(1)
    
    scores = [d['score'] for d in all_data.values()]
    avg_score = sum(scores) / len(scores) if scores else 0
    
    response = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "market_hours": is_market_hours(),
        "total_stocks": len(all_data),
        "summary": {
            "count": len(all_data),
            "avgScore": round(avg_score, 1),
            "strongBuy": len([s for s in scores if s >= 85]),
            "buy": len([s for s in scores if 75 <= s < 85]),
            "accumulate": len([s for s in scores if 65 <= s < 75])
        },
        "rankings": sorted(
            [{"symbol": s, **d} for s, d in all_data.items()],
            key=lambda x: x['score'],
            reverse=True
        )[:100],
        "data": all_data
    }
    
    set_cache(cache_key, response)
    return response

@app.get("/api/ranking")
async def get_ranking(limit: int = Query(50, ge=10, le=100)):
    """Lấy xếp hạng cổ phiếu theo điểm"""
    cache_key = f"ranking_{limit}"
    cached = get_cache(cache_key, 60)
    if cached:
        return cached
    
    all_stocks = get_all_stocks()[:200]
    data = get_stock_data_batch(all_stocks)
    
    rankings = sorted(
        [{"symbol": s, **d} for s, d in data.items()],
        key=lambda x: x['score'],
        reverse=True
    )[:limit]
    
    response = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "market_hours": is_market_hours(),
        "limit": limit,
        "count": len(rankings),
        "data": rankings
    }
    
    set_cache(cache_key, response)
    return response

# ==========================================
# CHẠY ỨNG DỤNG
# ==========================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
