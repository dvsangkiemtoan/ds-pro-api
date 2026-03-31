"""
DS Pro V9.9 - Stock Data API for Render
Vietnam Stock Market - Real-time data with vnstock
500 cổ phiếu thanh khoản cao nhất
Deploy on Render.com
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import List, Dict, Any
import time
import os

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

# ==========================================
# DANH SÁCH 500 CỔ PHIẾU THANH KHOẢN CAO NHẤT
# ==========================================

ALL_STOCKS = [
    # === VN30 (30 mã) ===
    "VCB", "BID", "CTG", "TCB", "MBB", "ACB", "VPB", "TPB", "STB", "HDB",
    "VIC", "VHM", "VRE", "NVL", "KDH", "PDR", "DXS", "NLG", "HPG", "FPT",
    "MWG", "PNJ", "VNM", "MSN", "GAS", "PLX", "SAB", "VJC", "SHB", "SSI",
    
    # === Ngân hàng & Tài chính (40 mã) ===
    "VIB", "LPB", "MSB", "OCB", "NAB", "ABB", "EIB", "SGB", "PGB", "BVB",
    "KLB", "NVB", "BAB", "TGB", "VBB", "BDB", "APG", "APS", "AAS", "ABW",
    "ACE", "ACL", "ADP", "AAM", "ABC", "ABT", "ACC", "ACG", "ACL", "ADA",
    
    # === Bất động sản (50 mã) ===
    "KBC", "IDC", "SIP", "BCM", "VGC", "HDG", "LDG", "HQC", "QCG", "ITA",
    "NTL", "SJS", "SZC", "TDC", "LHG", "DIG", "TCH", "TDH", "HAR", "HUT",
    "HVH", "LGL", "NBB", "PXL", "RCL", "SJD", "TIX", "VCR", "VPH", "CRE",
    "DPR", "DRH", "DTI", "D2D", "DQC", "EVG", "FDC", "FIR", "FLC", "HBC",
    "HDC", "HHS", "HID", "HMC", "HPH", "HPP", "HRC", "HTN", "HU1", "HU3",
    
    # === Công nghệ & Viễn thông (40 mã) ===
    "CMG", "ELC", "VGI", "GEX", "CTR", "MFS", "SGT", "ICT", "PTI", "TLD",
    "VIP", "VMA", "VPS", "VSD", "VSI", "VTP", "VTV", "ALT", "AMV", "ANT",
    "APP", "ATE", "BAF", "BIC", "BMC", "BMI", "BMP", "BSI", "BVS", "C4G",
    "CAG", "CAV", "CBS", "CCI", "CDC", "CEG", "CEN", "CET", "CKG", "CLL",
    
    # === Bán lẻ & Dịch vụ (50 mã) ===
    "FRT", "PET", "DGW", "HVN", "ACV", "SGN", "AST", "CJP", "CLC", "CMV",
    "CTD", "CTI", "CYC", "DAD", "DAG", "DAS", "DBD", "DCL", "DGC", "DHC",
    "DHT", "DIC", "DMC", "DPC", "DPR", "DQC", "DRC", "DSN", "DST", "DTA",
    "DTD", "DTK", "DTT", "DXV", "EVE", "FCM", "FDC", "FIT", "FMC", "FTS",
    
    # === Dầu khí & Năng lượng (50 mã) ===
    "POW", "NT2", "PVT", "PVS", "PVD", "BSR", "OIL", "PVC", "ASP", "BTP",
    "BWE", "DNC", "DNL", "DPG", "DRL", "DWC", "EVE", "GDT", "GEG", "HAH",
    "HBC", "HES", "HGM", "HHC", "HJS", "HMC", "HND", "HNF", "HPD", "HPW",
    "HRT", "HT1", "KHP", "L18", "L61", "L62", "LAF", "LBM", "LCG", "LCS",
    
    # === Vật liệu xây dựng (50 mã) ===
    "HSG", "NKG", "POM", "TLG", "TNG", "VGT", "VOS", "VSC", "AAA", "AMD",
    "BFC", "BMC", "BRC", "BTT", "CAN", "CLX", "COM", "CSV", "DCM", "DGC",
    "DHC", "DHP", "DPM", "DRC", "DTD", "DXP", "GIL", "GMC", "HAX", "HCM",
    "HHS", "HOT", "HPH", "HPP", "HRC", "HTP", "HTV", "IDC", "IMP", "ITC",
    
    # === Thủy sản & Nông nghiệp (40 mã) ===
    "VHC", "ANV", "ACL", "AGF", "FMC", "IDI", "MPC", "CMX", "ABT", "AAM",
    "ASM", "BT6", "BTD", "BTH", "BTS", "CAN", "CII", "CLC", "CLX", "CMV",
    "CNC", "CPC", "CSC", "CSM", "CTB", "CTC", "CTD", "CTI", "CTR", "CTS",
    
    # === Logistics (30 mã) ===
    "GMD", "SCS", "TCL", "VTO", "VNA", "VNS", "VNT", "VNE", "VRC", "VSG",
    "VSH", "VSM", "VSN", "VTB", "VTC", "VTR", "WCS", "WSS", "WTC", "SGP",
    "SGR", "SGT", "SHA", "SHE", "SHS", "SIC", "SJD", "SJE", "SJF", "SJG",
    
    # === Hóa chất & Cao su (40 mã) ===
    "DCM", "DGC", "DHC", "DHP", "DPM", "DRC", "DTD", "DXP", "GIL", "GMC",
    "HAX", "HCM", "HHS", "HOT", "HPH", "HPP", "HRC", "HTP", "HTV", "IDC",
    "IMP", "ITC", "KDC", "KHP", "KMR", "KOS", "KPF", "KSD", "KSF", "KSH",
    
    # === Khác (80 mã) ===
    "BHN", "DBC", "HAG", "HNG", "SBT", "KDC", "IMP", "ITA", "ITC", "LHG",
    "MCH", "MCM", "MCO", "MCP", "MDG", "MEL", "MHC", "MHL", "MIC", "MIG",
    "MKV", "MLS", "MPC", "MSH", "MST", "NAC", "NAF", "NAG", "NAV", "NBB",
    "NBC", "NCB", "NCT", "NDC", "NDN", "NDP", "NHA", "NHC", "NHT", "NNC",
    "NNG", "NSC", "NSH", "NTP", "NVT", "OCH", "OGC", "OPC", "PAC", "PBP",
    "PCC", "PCE", "PCG", "PCT", "PDB", "PDC", "PDV", "PEC", "PEP", "PGC",
    "PGD", "PGI", "PGS", "PGT", "PHC", "PHD", "PHR", "PIT", "PJT", "PLC"
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
    
    # Tầng 1: Phát hiện sớm (volume spike)
    if volume_ratio > 1.5:
        score += 20
    elif volume_ratio > 1.2:
        score += 10
    
    if price > ma20 and (price - ma20) / ma20 < 0.02:
        score += 10
    
    # Tầng 2: Xác nhận trend
    if price > ma20:
        score += 15
    if ma20 > ma50:
        score += 20
    if price > ma50:
        score += 10
    if 40 < rsi < 70:
        score += 10
    
    # Tầng 3: Xác nhận volume và ADX
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
    
    # RR Ratio
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

def get_volume_threshold(symbol: str, volume_ratio: float) -> tuple:
    group = get_stock_group(symbol)
    
    thresholds = {
        "BLUE_CHIP": {"strong": 1.8, "moderate": 1.4, "weak": 1.2},
        "MID_CAP": {"strong": 2.2, "moderate": 1.7, "weak": 1.3},
        "SMALL_CAP": {"strong": 2.8, "moderate": 2.0, "weak": 1.5},
        "PENNY": {"strong": 3.5, "moderate": 2.5, "weak": 1.8}
    }
    
    t = thresholds[group]
    volume_score = 0
    
    if volume_ratio >= t["strong"]:
        volume_score = 20
    elif volume_ratio >= t["moderate"]:
        volume_score = 12
    elif volume_ratio >= t["weak"]:
        volume_score = 6
    
    return volume_score, group

# ==========================================
# LẤY DỮ LIỆU REALTIME TỪ VNSTOCK
# ==========================================

def get_stock_data_from_vnstock(symbol: str) -> Dict[str, Any]:
    """
    Lấy dữ liệu realtime từ vnstock
    """
    try:
        from vnstock import Vnstock
        
        stock = Vnstock().stock(symbol=symbol, source="VCI")
        current = stock.quote.current_price()
        
        if not current or current.get('price', 0) == 0:
            return None
        
        # Lấy lịch sử 60 ngày
        end = datetime.now()
        start = end - timedelta(days=60)
        history = stock.quote.history(
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d")
        )
        
        closes = history['close'].tolist() if not history.empty else []
        volumes = history['volume'].tolist() if not history.empty else []
        highs = history['high'].tolist() if not history.empty else []
        lows = history['low'].tolist() if not history.empty else []
        
        # Tính chỉ báo
        ma20 = calculate_ma(closes, 20)
        ma50 = calculate_ma(closes, 50)
        rsi = calculate_rsi(closes, 14)
        adx = calculate_adx(highs, lows, closes, 14)
        atr = calculate_atr(highs, lows, closes, 14)
        avg_volume = calculate_ma(volumes, 20) if volumes else current.get('volume', 0)
        
        price = current.get('price', 0)
        volume_ratio = current.get('volume', 0) / avg_volume if avg_volume > 0 else 1
        rr_ratio = calculate_risk_reward_vn(price, atr, adx)
        
        # Tính điểm
        score = calculate_score(price, ma20, ma50, rsi, volume_ratio, adx, rr_ratio)
        
        return {
            'price': price,
            'change': current.get('change', 0),
            'changePercent': current.get('percentChange', 0),
            'volume': current.get('volume', 0),
            'high': current.get('high', price),
            'low': current.get('low', price),
            'open': current.get('open', price),
            'ma20': round(ma20, 2),
            'ma50': round(ma50, 2),
            'rsi': round(rsi, 2),
            'adx': round(adx, 2),
            'atr': round(atr, 2),
            'rr_ratio': round(rr_ratio, 2),
            'avgVolume20': round(avg_volume, 0),
            'volume_ratio': round(volume_ratio, 2),
            'score': score,
            'source': 'vnstock',
            'time': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Error with {symbol}: {e}")
        return None

def get_stock_data_batch(symbols: List[str]) -> Dict[str, Any]:
    """Lấy dữ liệu batch cho nhiều mã"""
    result = {}
    start_time = time.time()
    max_time = 25
    
    for symbol in symbols:
        if time.time() - start_time > max_time:
            print(f"⏰ Timeout at {symbol}")
            break
        try:
            data = get_stock_data_from_vnstock(symbol)
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
        "endpoints": {
            "health": "/health",
            "price": "/api/price?symbols=VCB,FPT",
            "all": "/api/all/combined",
            "ranking": "/api/ranking"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "total_stocks": len(get_all_stocks()),
        "cache_size": len(cache)
    }

@app.get("/api/price")
async def get_price(symbols: str = Query(..., description="Mã cổ phiếu")):
    """Lấy giá realtime cho các mã cổ phiếu"""
    symbol_list = [s.strip().upper() for s in symbols.split(',')][:30]
    data = {}
    
    for symbol in symbol_list:
        stock_data = get_stock_data_from_vnstock(symbol)
        if stock_data:
            data[symbol] = stock_data
    
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "count": len(data),
        "data": data
    }

@app.get("/api/all/combined")
async def get_all_combined():
    """Lấy tất cả dữ liệu 500 mã"""
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
    
    all_stocks = get_all_stocks()[:200]  # Lấy 200 mã để ranking
    data = get_stock_data_batch(all_stocks)
    
    rankings = sorted(
        [{"symbol": s, **d} for s, d in data.items()],
        key=lambda x: x['score'],
        reverse=True
    )[:limit]
    
    response = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
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