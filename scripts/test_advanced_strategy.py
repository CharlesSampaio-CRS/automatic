"""
Test Advanced Strategy Features
Testa todas as novas features de estratégias avançadas
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.validators.strategy_rules_validator import StrategyRulesValidator


def test_validation():
    """Testa validações de rules"""
    print("=" * 60)
    print("🔍 TESTANDO VALIDAÇÕES DE RULES")
    print("=" * 60)
    
    # Test 1: Rules válidas completas
    print("\n✅ Test 1: Rules válidas completas")
    valid_rules = {
        "take_profit_levels": [
            {"percent": 3.0, "quantity_percent": 30, "enabled": True},
            {"percent": 5.0, "quantity_percent": 40, "enabled": True},
            {"percent": 10.0, "quantity_percent": 30, "enabled": True}
        ],
        "stop_loss": {
            "percent": 2.0,
            "enabled": True,
            "trailing_enabled": True,
            "trailing_percent": 1.5,
            "trailing_activation_percent": 2.0
        },
        "buy_dip": {
            "percent": 3.0,
            "enabled": True,
            "dca_enabled": True,
            "dca_levels": [
                {"percent": 3.0, "quantity_percent": 33},
                {"percent": 4.0, "quantity_percent": 33},
                {"percent": 5.0, "quantity_percent": 34}
            ]
        },
        "risk_management": {
            "max_daily_loss_usd": 500,
            "max_weekly_loss_usd": 1500,
            "max_monthly_loss_usd": 5000
        },
        "cooldown": {
            "enabled": True,
            "minutes_after_sell": 30,
            "minutes_after_buy": 15
        },
        "trading_hours": {
            "enabled": True,
            "timezone": "UTC",
            "allowed_hours": [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
            "allowed_days": [1, 2, 3, 4, 5]
        },
        "blackout_periods": [
            {
                "description": "FOMC Meeting",
                "start": "2024-12-15T14:00:00Z",
                "end": "2024-12-15T16:00:00Z",
                "enabled": True
            }
        ],
        "volume_check": {
            "enabled": True,
            "min_24h_volume_usd": 100000000,
            "min_1h_volume_usd": 5000000
        },
        "indicators": {
            "rsi": {
                "enabled": True,
                "period": 14,
                "oversold": 30,
                "overbought": 70,
                "require_on_buy": True,
                "require_on_sell": True
            }
        },
        "execution": {
            "min_order_size_usd": 10,
            "max_order_size_percent": 100,
            "allow_partial_fills": True
        }
    }
    
    is_valid, error = StrategyRulesValidator.validate_rules(valid_rules)
    if is_valid:
        print("   ✅ PASSOU - Rules válidas aceitas")
    else:
        print(f"   ❌ FALHOU - {error}")
    
    # Test 2: Take profit levels com soma incorreta
    print("\n❌ Test 2: Take profit levels com soma != 100%")
    invalid_tp = {
        "take_profit_levels": [
            {"percent": 3.0, "quantity_percent": 30, "enabled": True},
            {"percent": 5.0, "quantity_percent": 40, "enabled": True}
        ],
        "stop_loss": {"percent": 2.0, "enabled": True},
        "buy_dip": {"percent": 3.0, "enabled": True}
    }
    
    is_valid, error = StrategyRulesValidator.validate_rules(invalid_tp)
    if not is_valid and "100%" in error:
        print(f"   ✅ PASSOU - Erro detectado: {error}")
    else:
        print(f"   ❌ FALHOU - Deveria rejeitar soma != 100%")
    
    # Test 3: RSI com valores inválidos
    print("\n❌ Test 3: RSI oversold >= overbought")
    invalid_rsi = {
        "take_profit_levels": [{"percent": 5.0, "quantity_percent": 100, "enabled": True}],
        "stop_loss": {"percent": 2.0, "enabled": True},
        "buy_dip": {"percent": 3.0, "enabled": True},
        "indicators": {
            "rsi": {
                "enabled": True,
                "period": 14,
                "oversold": 70,  # Errado: oversold > overbought
                "overbought": 30
            }
        }
    }
    
    is_valid, error = StrategyRulesValidator.validate_rules(invalid_rsi)
    if not is_valid and "oversold" in error:
        print(f"   ✅ PASSOU - Erro detectado: {error}")
    else:
        print(f"   ❌ FALHOU - Deveria rejeitar oversold >= overbought")
    
    # Test 4: DCA levels com soma incorreta
    print("\n❌ Test 4: DCA levels com soma != 100%")
    invalid_dca = {
        "take_profit_levels": [{"percent": 5.0, "quantity_percent": 100, "enabled": True}],
        "stop_loss": {"percent": 2.0, "enabled": True},
        "buy_dip": {
            "percent": 3.0,
            "enabled": True,
            "dca_enabled": True,
            "dca_levels": [
                {"percent": 3.0, "quantity_percent": 50},
                {"percent": 4.0, "quantity_percent": 30}
            ]
        }
    }
    
    is_valid, error = StrategyRulesValidator.validate_rules(invalid_dca)
    if not is_valid and "100%" in error:
        print(f"   ✅ PASSOU - Erro detectado: {error}")
    else:
        print(f"   ❌ FALHOU - Deveria rejeitar soma DCA != 100%")


def test_normalization():
    """Testa conversão de formato antigo para novo"""
    print("\n" + "=" * 60)
    print("🔄 TESTANDO NORMALIZAÇÃO (Formato Antigo → Novo)")
    print("=" * 60)
    
    # Test 1: Formato antigo
    print("\n✅ Test 1: Converter formato antigo")
    old_format = {
        "take_profit_percent": 5.0,
        "stop_loss_percent": 2.0,
        "buy_dip_percent": 3.0
    }
    
    normalized = StrategyRulesValidator.normalize_rules(old_format)
    
    if "take_profit_levels" in normalized:
        tp = normalized["take_profit_levels"][0]
        if tp["percent"] == 5.0 and tp["quantity_percent"] == 100:
            print("   ✅ PASSOU - Take profit convertido corretamente")
        else:
            print(f"   ❌ FALHOU - Take profit incorreto: {tp}")
    else:
        print("   ❌ FALHOU - take_profit_levels não criado")
    
    if normalized["stop_loss"]["percent"] == 2.0:
        print("   ✅ PASSOU - Stop loss convertido corretamente")
    else:
        print(f"   ❌ FALHOU - Stop loss incorreto")
    
    if normalized["buy_dip"]["percent"] == 3.0:
        print("   ✅ PASSOU - Buy dip convertido corretamente")
    else:
        print(f"   ❌ FALHOU - Buy dip incorreto")
    
    # Test 2: Formato novo permanece inalterado
    print("\n✅ Test 2: Formato novo permanece inalterado")
    new_format = {
        "take_profit_levels": [{"percent": 5.0, "quantity_percent": 100, "enabled": True}],
        "stop_loss": {"percent": 2.0, "enabled": True},
        "buy_dip": {"percent": 3.0, "enabled": True}
    }
    
    normalized = StrategyRulesValidator.normalize_rules(new_format)
    
    if normalized == new_format:
        print("   ✅ PASSOU - Formato novo não foi alterado")
    else:
        print("   ❌ FALHOU - Formato novo foi modificado")


def test_defaults():
    """Testa regras padrão"""
    print("\n" + "=" * 60)
    print("🎯 TESTANDO REGRAS PADRÃO")
    print("=" * 60)
    
    defaults = StrategyRulesValidator.get_default_rules()
    
    print("\n✅ Rules padrão geradas:")
    print(f"   Take Profit: {defaults['take_profit_levels'][0]['percent']}% (100% da posição)")
    print(f"   Stop Loss: {defaults['stop_loss']['percent']}%")
    print(f"   Buy Dip: {defaults['buy_dip']['percent']}%")
    print(f"   Trailing Stop: {defaults['stop_loss']['trailing_enabled']}")
    print(f"   DCA: {defaults['buy_dip']['dca_enabled']}")
    print(f"   Trading Hours: {defaults['trading_hours']['enabled']}")
    print(f"   RSI: {defaults['indicators']['rsi']['enabled']}")
    
    is_valid, error = StrategyRulesValidator.validate_rules(defaults)
    if is_valid:
        print("\n   ✅ PASSOU - Defaults válidos")
    else:
        print(f"\n   ❌ FALHOU - Defaults inválidos: {error}")


def show_example_rules():
    """Mostra exemplos de configurações"""
    print("\n" + "=" * 60)
    print("📋 EXEMPLOS DE CONFIGURAÇÃO")
    print("=" * 60)
    
    print("\n1️⃣ ESTRATÉGIA CONSERVADORA (Proteção máxima):")
    print("""
{
  "take_profit_levels": [
    {"percent": 2.0, "quantity_percent": 50, "enabled": true},
    {"percent": 4.0, "quantity_percent": 50, "enabled": true}
  ],
  "stop_loss": {
    "percent": 1.0,
    "enabled": true,
    "trailing_enabled": true,
    "trailing_percent": 0.5,
    "trailing_activation_percent": 1.0
  },
  "risk_management": {
    "max_daily_loss_usd": 200
  },
  "cooldown": {
    "enabled": true,
    "minutes_after_sell": 60
  }
}
""")
    
    print("\n2️⃣ ESTRATÉGIA AGRESSIVA (Máximo lucro):")
    print("""
{
  "take_profit_levels": [
    {"percent": 5.0, "quantity_percent": 30, "enabled": true},
    {"percent": 10.0, "quantity_percent": 40, "enabled": true},
    {"percent": 20.0, "quantity_percent": 30, "enabled": true}
  ],
  "stop_loss": {
    "percent": 3.0,
    "enabled": true,
    "trailing_enabled": true,
    "trailing_percent": 2.0,
    "trailing_activation_percent": 3.0
  },
  "buy_dip": {
    "percent": 5.0,
    "enabled": true,
    "dca_enabled": true,
    "dca_levels": [
      {"percent": 5.0, "quantity_percent": 50},
      {"percent": 8.0, "quantity_percent": 50}
    ]
  },
  "risk_management": {
    "max_daily_loss_usd": 1000
  }
}
""")
    
    print("\n3️⃣ ESTRATÉGIA HORÁRIO COMERCIAL (9h-17h):")
    print("""
{
  "take_profit_levels": [
    {"percent": 3.0, "quantity_percent": 100, "enabled": true}
  ],
  "stop_loss": {
    "percent": 2.0,
    "enabled": true
  },
  "trading_hours": {
    "enabled": true,
    "timezone": "America/Sao_Paulo",
    "allowed_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17],
    "allowed_days": [1, 2, 3, 4, 5]
  },
  "volume_check": {
    "enabled": true,
    "min_24h_volume_usd": 50000000
  }
}
""")


if __name__ == "__main__":
    print("\n🚀 TESTE DE FEATURES AVANÇADAS DE ESTRATÉGIA\n")
    
    test_validation()
    test_normalization()
    test_defaults()
    show_example_rules()
    
    print("\n" + "=" * 60)
    print("✅ TESTES COMPLETOS!")
    print("=" * 60)
