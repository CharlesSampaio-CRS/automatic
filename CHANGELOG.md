# 📋 CHANGELOG - MAVERICK Trading Bot

## Version 2.1.0 - December 3, 2025

### 🌍 Internationalization
- ✅ All system messages translated to English
- ✅ Professional log prefixes (WARNING, ERROR, START, END, etc.)
- ✅ MongoDB messages in English
- ✅ API responses in English
- ✅ Documentation updated to English

### 📊 MongoDB Logs Improvements
- ✅ **Fixed timezone**: Now saves correct America/Sao_Paulo time (was UTC+3)
- ✅ **Formatted values**: No more scientific notation (0.0000003373 instead of 3.373e-7)
- ✅ **8 decimal places**: Consistent crypto price formatting
- ✅ **Rounded percentages**: 2-4 decimal places for better readability

### 🔧 Technical Changes
- ✅ Added `format_price()` function to avoid scientific notation
- ✅ Timestamp now uses `datetime.now(TZ)` for correct timezone
- ✅ All prices formatted to 8 decimals
- ✅ Percentages rounded (spread: 4, change: 2, volume: 2, volatility: 2)

### 📚 Documentation
- ✅ README.md translated to English
- ✅ postman/README.md translated to English
- ✅ Added LOGS_MONGODB_AJUSTADOS.md with detailed changes
- ✅ Updated Postman collection examples

### 🎯 Example Log Before/After

**BEFORE:**
```json
{
  "timestamp": "2025-12-04T01:07:50",  // Wrong +3h
  "market_info": {
    "current_price": 3.373e-7,  // Scientific notation
    "spread": { "value": 8.999999999999617e-10 }
  },
  "sell_details": {
    "message": "Execução scheduled não realiza vendas"  // Portuguese
  }
}
```

**AFTER:**
```json
{
  "timestamp": "2025-12-03T22:07:50-03:00",  // Correct
  "market_info": {
    "current_price": 0.0000003373,  // Readable
    "bid_price": 0.00000033612,
    "ask_price": 0.00000033702,
    "spread": {
      "value": 0.0000000009,
      "percent": 0.2678
    }
  },
  "sell_details": {
    "message": "Scheduled execution does not perform sells"  // English
  }
}
```

---

## Version 2.0.0 - December 2, 2025

### 🚀 Production Ready
- ✅ Fixed Gunicorn multi-worker issue (--workers=1)
- ✅ Scheduler initialization outside __main__
- ✅ Added /health endpoint for monitoring
- ✅ Removed verbose debug logs
- ✅ Production robustness improvements

### 📝 Logging Enhancements
- ✅ Detailed execution logs with job ID
- ✅ No swallowed exceptions (all errors printed)
- ✅ Startup screen with version info
- ✅ Next execution time display

### 🎨 Professional Logs
- ✅ Removed ALL emojis from logs
- ✅ Standardized ASCII prefixes
- ✅ grep-friendly format
- ✅ Parsing-compatible structure

---

## Version 1.0.0 - November 2025

### 🎯 Initial Release
- ✅ MEXC integration via CCXT
- ✅ MongoDB configuration storage
- ✅ APScheduler dynamic jobs
- ✅ 4h scalping strategy
- ✅ Profit guarantee system (100% success rate)
- ✅ Multi-level buy strategy (-3%, -5%, -10%)
- ✅ Flask REST API
- ✅ Postman collection v1.0

---

## 🔗 Related Files
- `LOGS_MONGODB_AJUSTADOS.md` - Detailed MongoDB logs changes
- `LOGS_PROFISSIONAIS_SEM_EMOJIS.py` - Emoji removal documentation
- `README.md` - Main project documentation
- `postman/README.md` - Postman collection guide
