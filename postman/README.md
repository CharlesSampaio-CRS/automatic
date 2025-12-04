# 📮 Postman Collection - MEXC Trading Bot v2.1

## How to Import

1. Open Postman
2. Click on **Import**
3. Select the file `Bot_Trading_v2.1.postman_collection.json`
4. The collection will be imported with all organized endpoints

---

## 📋 Collection Structure

### 🏥 **Health Check**
- `GET /` - Check if API is running
- `GET /health` - System health status

### 💰 **Balance**
- `GET /balance` - Check total balance in USDT

### 📦 **Order**
- `POST /order` - Execute manual order

### ⚙️ **Configs (MongoDB)**
- `GET /configs` - List all configs
- `GET /configs?enabled_only=true` - List only enabled configs
- `GET /configs/{pair}` - Get config by pair (ex: REKT/USDT)
- `POST /configs` - Create new config
- `PUT /configs/{pair}` - Update config (partial)
- `DELETE /configs/{pair}` - Delete config

### 🤖 **Jobs (Scheduler)**
- `GET /jobs` - List all active jobs
- `POST /jobs` with `action: reload` - Reload from MongoDB
- `POST /jobs` with `action: start` - Start specific jobs
- `POST /jobs` with `action: stop` - Stop specific or all jobs

---

## 🔧 Configuration

### Environment Variable

The collection comes pre-configured with the variable:

```
base_url = http://localhost:5000
```

To change:
1. Click on the collection name
2. Go to **Variables**
3. Edit the `base_url` value
---

##  Recommended Usage Flow

### 1️⃣ **Check Status**
```
GET /
GET /health
GET /balance
```

### 2️⃣ **Create Configuration**
```
POST /configs
Body: {Complete JSON}
```

### 3️⃣ **Reload Jobs**
```
POST /jobs
Body: {"action": "reload"}
```

### 4️⃣ **Check Active Jobs**
```
GET /jobs
```

### 5️⃣ **Test Manual Order**
```
POST /order
Body: {"pair": "ETH/USDT"}
```

### 6️⃣ **Update Config**
```
PUT /configs/ETH%2FUSDT
Body: {"schedule": {"interval_hours": 4}}
```

### 7️⃣ **Reload Again**
```
POST /jobs
Body: {"action": "reload"}
```

---

##  Body Examples

### Create Complete Config
```json
{
  "pair": "BTC/USDT",
  "enabled": true,
  "schedule": {
    "interval_hours": 4,
    "business_hours_start": 9,
    "business_hours_end": 23,
    "enabled": true
  },
  "limits": {
    "min_value_per_order": 20,
    "allocation_percentage": 30
  },
  "trading_strategy": {
    "type": "buy_levels",
    "min_price_variation": 1.0,
    "levels": [
      {"price_drop_percent": 1.0, "allocation_percent": 20},
      {"price_drop_percent": 3.0, "allocation_percent": 30},
      {"price_drop_percent": 5.0, "allocation_percent": 50}
    ]
  },
  "sell_strategy": {
    "type": "profit_levels",
    "levels": [
      {"profit_percent": 2.0, "sell_percent": 30},
      {"profit_percent": 5.0, "sell_percent": 50},
      {"profit_percent": 10.0, "sell_percent": 100}
    ]
  }
}
```

### Update Only Interval
```json
{
  "schedule": {
    "interval_hours": 3
  }
}
```

### Disable Symbol
```json
{
  "enabled": false
}
```

---

##  Important Notes

### URL Encoding
When using pairs with `/` in URL, use `%2F`:
-  Correct: `/configs/REKT%2FUSDT`
-  Wrong: `/configs/REKT/USDT`

### Jobs Actions
The `POST /jobs` endpoint accepts 3 actions:

1. **reload** - Reload all from MongoDB
   ```json
   {"action": "reload"}
   ```

2. **start** - Start specific (requires pairs)
   ```json
   {"action": "start", "pairs": ["REKT/USDT", "BTC/USDT"]}
   ```

3. **stop** - Stop specific or all
   ```json
   {"action": "stop", "pairs": ["REKT/USDT"]}
   ```
   or
   ```json
   {"action": "stop"}
   ```

### After MongoDB Changes
**ALWAYS** use `POST /jobs {"action": "reload"}` to apply changes!

---

## 📚 Complete Documentation

For more details, check:
- `API_DOCS.md` - Complete API documentation
- `API_CHANGELOG.txt` - Changes summary
- `LOGS_MONGODB_AJUSTADOS.md` - MongoDB logs improvements

---

## ✨ Collection v2.1 Features

-  Organized by domains (Health, Balance, Order, Configs, Jobs)
-  Pre-configured body examples
-  Descriptions in each request
-  Configurable `base_url` variable
-  Complete API v2.1 coverage
-  MongoDB and Dynamic Jobs support
-  Professional English messages
-  Formatted values (no scientific notation)
-  Correct timezone (America/Sao_Paulo)
