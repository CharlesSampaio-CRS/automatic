"""
Strategy Rules Validator
Valida todas as regras avançadas de estratégias de trading
"""
from typing import Dict, List, Any, Tuple
from datetime import datetime
import pytz


class StrategyRulesValidator:
    """Valida regras avançadas de estratégias"""
    
    @staticmethod
    def validate_rules(rules: Dict) -> Tuple[bool, str]:
        """
        Valida todas as regras fornecidas
        
        Args:
            rules: Dicionário com todas as regras da estratégia
            
        Returns:
            Tuple (is_valid, error_message)
        """
        if not isinstance(rules, dict):
            return False, "Rules deve ser um dicionário"
        
        # Valida cada seção
        validators = [
            StrategyRulesValidator._validate_take_profit_levels,
            StrategyRulesValidator._validate_stop_loss,
            StrategyRulesValidator._validate_buy_dip,
            StrategyRulesValidator._validate_risk_management,
            StrategyRulesValidator._validate_cooldown,
            StrategyRulesValidator._validate_trading_hours,
            StrategyRulesValidator._validate_blackout_periods,
            StrategyRulesValidator._validate_volume_check,
            StrategyRulesValidator._validate_indicators,
            StrategyRulesValidator._validate_execution,
        ]
        
        for validator in validators:
            is_valid, error_msg = validator(rules)
            if not is_valid:
                return False, error_msg
        
        return True, ""
    
    @staticmethod
    def _validate_take_profit_levels(rules: Dict) -> Tuple[bool, str]:
        """Valida níveis de take profit"""
        levels = rules.get("take_profit_levels", [])
        
        if not isinstance(levels, list):
            return False, "take_profit_levels deve ser uma lista"
        
        if len(levels) == 0:
            return False, "Pelo menos um nível de take profit é obrigatório"
        
        total_quantity = 0
        for idx, level in enumerate(levels):
            if not isinstance(level, dict):
                return False, f"Nível {idx+1} deve ser um objeto"
            
            percent = level.get("percent")
            quantity_percent = level.get("quantity_percent")
            
            if percent is None or not isinstance(percent, (int, float)):
                return False, f"Nível {idx+1}: percent deve ser numérico"
            
            if percent <= 0:
                return False, f"Nível {idx+1}: percent deve ser positivo"
            
            if quantity_percent is None or not isinstance(quantity_percent, (int, float)):
                return False, f"Nível {idx+1}: quantity_percent deve ser numérico"
            
            if quantity_percent <= 0 or quantity_percent > 100:
                return False, f"Nível {idx+1}: quantity_percent deve estar entre 0 e 100"
            
            total_quantity += quantity_percent
        
        if total_quantity != 100:
            return False, f"Soma dos quantity_percent deve ser 100%, atual: {total_quantity}%"
        
        return True, ""
    
    @staticmethod
    def _validate_stop_loss(rules: Dict) -> Tuple[bool, str]:
        """Valida stop loss e trailing stop"""
        stop_loss = rules.get("stop_loss")
        
        if stop_loss is None:
            return False, "stop_loss é obrigatório"
        
        if not isinstance(stop_loss, dict):
            return False, "stop_loss deve ser um objeto"
        
        percent = stop_loss.get("percent")
        if percent is None or not isinstance(percent, (int, float)):
            return False, "stop_loss.percent deve ser numérico"
        
        if percent <= 0:
            return False, "stop_loss.percent deve ser positivo"
        
        # Valida trailing stop se habilitado
        if stop_loss.get("trailing_enabled", False):
            trailing_percent = stop_loss.get("trailing_percent")
            if trailing_percent is None or not isinstance(trailing_percent, (int, float)):
                return False, "stop_loss.trailing_percent deve ser numérico quando trailing ativado"
            
            if trailing_percent <= 0:
                return False, "stop_loss.trailing_percent deve ser positivo"
            
            activation = stop_loss.get("trailing_activation_percent")
            if activation is not None and not isinstance(activation, (int, float)):
                return False, "stop_loss.trailing_activation_percent deve ser numérico"
        
        return True, ""
    
    @staticmethod
    def _validate_buy_dip(rules: Dict) -> Tuple[bool, str]:
        """Valida buy dip e DCA"""
        buy_dip = rules.get("buy_dip")
        
        if buy_dip is None:
            return False, "buy_dip é obrigatório"
        
        if not isinstance(buy_dip, dict):
            return False, "buy_dip deve ser um objeto"
        
        percent = buy_dip.get("percent")
        if percent is None or not isinstance(percent, (int, float)):
            return False, "buy_dip.percent deve ser numérico"
        
        if percent <= 0:
            return False, "buy_dip.percent deve ser positivo"
        
        # Valida DCA se habilitado
        if buy_dip.get("dca_enabled", False):
            dca_levels = buy_dip.get("dca_levels", [])
            
            if not isinstance(dca_levels, list):
                return False, "buy_dip.dca_levels deve ser uma lista"
            
            if len(dca_levels) == 0:
                return False, "buy_dip.dca_levels deve ter pelo menos um nível quando DCA ativado"
            
            total_quantity = 0
            for idx, level in enumerate(dca_levels):
                if not isinstance(level, dict):
                    return False, f"DCA nível {idx+1} deve ser um objeto"
                
                level_percent = level.get("percent")
                quantity_percent = level.get("quantity_percent")
                
                if level_percent is None or not isinstance(level_percent, (int, float)):
                    return False, f"DCA nível {idx+1}: percent deve ser numérico"
                
                if level_percent <= 0:
                    return False, f"DCA nível {idx+1}: percent deve ser positivo"
                
                if quantity_percent is None or not isinstance(quantity_percent, (int, float)):
                    return False, f"DCA nível {idx+1}: quantity_percent deve ser numérico"
                
                if quantity_percent <= 0 or quantity_percent > 100:
                    return False, f"DCA nível {idx+1}: quantity_percent deve estar entre 0 e 100"
                
                total_quantity += quantity_percent
            
            if total_quantity != 100:
                return False, f"Soma dos DCA quantity_percent deve ser 100%, atual: {total_quantity}%"
        
        return True, ""
    
    @staticmethod
    def _validate_risk_management(rules: Dict) -> Tuple[bool, str]:
        """Valida circuit breakers"""
        risk = rules.get("risk_management", {})
        
        if not isinstance(risk, dict):
            return False, "risk_management deve ser um objeto"
        
        # Campos opcionais, mas se presentes devem ser válidos
        for field in ["max_daily_loss_usd", "max_weekly_loss_usd", "max_monthly_loss_usd"]:
            value = risk.get(field)
            if value is not None:
                if not isinstance(value, (int, float)):
                    return False, f"risk_management.{field} deve ser numérico"
                if value <= 0:
                    return False, f"risk_management.{field} deve ser positivo"
        
        return True, ""
    
    @staticmethod
    def _validate_cooldown(rules: Dict) -> Tuple[bool, str]:
        """Valida cooldown"""
        cooldown = rules.get("cooldown", {})
        
        if not isinstance(cooldown, dict):
            return False, "cooldown deve ser um objeto"
        
        if cooldown.get("enabled", False):
            for field in ["minutes_after_sell", "minutes_after_buy"]:
                value = cooldown.get(field)
                if value is not None:
                    if not isinstance(value, (int, float)):
                        return False, f"cooldown.{field} deve ser numérico"
                    if value < 0:
                        return False, f"cooldown.{field} não pode ser negativo"
        
        return True, ""
    
    @staticmethod
    def _validate_trading_hours(rules: Dict) -> Tuple[bool, str]:
        """Valida horários de trading"""
        trading_hours = rules.get("trading_hours", {})
        
        if not isinstance(trading_hours, dict):
            return False, "trading_hours deve ser um objeto"
        
        if trading_hours.get("enabled", False):
            timezone = trading_hours.get("timezone")
            if timezone:
                try:
                    pytz.timezone(timezone)
                except:
                    return False, f"trading_hours.timezone inválido: {timezone}"
            
            allowed_hours = trading_hours.get("allowed_hours", [])
            if not isinstance(allowed_hours, list):
                return False, "trading_hours.allowed_hours deve ser uma lista"
            
            for hour in allowed_hours:
                if not isinstance(hour, int) or hour < 0 or hour > 23:
                    return False, "trading_hours.allowed_hours deve conter horas entre 0 e 23"
            
            allowed_days = trading_hours.get("allowed_days", [])
            if not isinstance(allowed_days, list):
                return False, "trading_hours.allowed_days deve ser uma lista"
            
            for day in allowed_days:
                if not isinstance(day, int) or day < 0 or day > 6:
                    return False, "trading_hours.allowed_days deve conter dias entre 0 (domingo) e 6 (sábado)"
        
        return True, ""
    
    @staticmethod
    def _validate_blackout_periods(rules: Dict) -> Tuple[bool, str]:
        """Valida períodos de blackout"""
        blackout_periods = rules.get("blackout_periods", [])
        
        if not isinstance(blackout_periods, list):
            return False, "blackout_periods deve ser uma lista"
        
        for idx, period in enumerate(blackout_periods):
            if not isinstance(period, dict):
                return False, f"Blackout período {idx+1} deve ser um objeto"
            
            start = period.get("start")
            end = period.get("end")
            
            if not start or not isinstance(start, str):
                return False, f"Blackout período {idx+1}: start deve ser uma string ISO 8601"
            
            if not end or not isinstance(end, str):
                return False, f"Blackout período {idx+1}: end deve ser uma string ISO 8601"
            
            try:
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                
                if end_dt <= start_dt:
                    return False, f"Blackout período {idx+1}: end deve ser posterior a start"
            except:
                return False, f"Blackout período {idx+1}: formato de data inválido (use ISO 8601)"
        
        return True, ""
    
    @staticmethod
    def _validate_volume_check(rules: Dict) -> Tuple[bool, str]:
        """Valida verificação de volume"""
        volume_check = rules.get("volume_check", {})
        
        if not isinstance(volume_check, dict):
            return False, "volume_check deve ser um objeto"
        
        for field in ["min_24h_volume_usd", "min_1h_volume_usd"]:
            value = volume_check.get(field)
            if value is not None:
                if not isinstance(value, (int, float)):
                    return False, f"volume_check.{field} deve ser numérico"
                if value < 0:
                    return False, f"volume_check.{field} não pode ser negativo"
        
        return True, ""
    
    @staticmethod
    def _validate_indicators(rules: Dict) -> Tuple[bool, str]:
        """Valida indicadores técnicos"""
        indicators = rules.get("indicators", {})
        
        if not isinstance(indicators, dict):
            return False, "indicators deve ser um objeto"
        
        # Valida RSI
        rsi = indicators.get("rsi", {})
        if not isinstance(rsi, dict):
            return False, "indicators.rsi deve ser um objeto"
        
        if rsi.get("enabled", False):
            period = rsi.get("period", 14)
            if not isinstance(period, int) or period < 1:
                return False, "indicators.rsi.period deve ser um inteiro positivo"
            
            oversold = rsi.get("oversold", 30)
            overbought = rsi.get("overbought", 70)
            
            if not isinstance(oversold, (int, float)) or oversold < 0 or oversold > 100:
                return False, "indicators.rsi.oversold deve estar entre 0 e 100"
            
            if not isinstance(overbought, (int, float)) or overbought < 0 or overbought > 100:
                return False, "indicators.rsi.overbought deve estar entre 0 e 100"
            
            if oversold >= overbought:
                return False, "indicators.rsi.oversold deve ser menor que overbought"
        
        return True, ""
    
    @staticmethod
    def _validate_execution(rules: Dict) -> Tuple[bool, str]:
        """Valida configurações de execução"""
        execution = rules.get("execution", {})
        
        if not isinstance(execution, dict):
            return False, "execution deve ser um objeto"
        
        min_order = execution.get("min_order_size_usd")
        if min_order is not None:
            if not isinstance(min_order, (int, float)):
                return False, "execution.min_order_size_usd deve ser numérico"
            if min_order <= 0:
                return False, "execution.min_order_size_usd deve ser positivo"
        
        max_percent = execution.get("max_order_size_percent")
        if max_percent is not None:
            if not isinstance(max_percent, (int, float)):
                return False, "execution.max_order_size_percent deve ser numérico"
            if max_percent <= 0 or max_percent > 100:
                return False, "execution.max_order_size_percent deve estar entre 0 e 100"
        
        return True, ""
    
    @staticmethod
    def normalize_rules(rules: Dict) -> Dict:
        """
        Normaliza rules antigas (formato simples) para o novo formato
        
        Args:
            rules: Pode ser formato antigo ou novo
            
        Returns:
            Rules no formato novo (expandido)
        """
        # Se já está no formato novo (tem take_profit_levels), retorna como está
        if "take_profit_levels" in rules:
            return rules
        
        # Formato antigo: converte para novo
        normalized = {
            "take_profit_levels": [],
            "stop_loss": {
                "percent": 2.0,
                "enabled": True,
                "trailing_enabled": False
            },
            "buy_dip": {
                "percent": 3.0,
                "enabled": True,
                "dca_enabled": False
            },
            "risk_management": {},
            "cooldown": {"enabled": False},
            "trading_hours": {"enabled": False},
            "blackout_periods": [],
            "volume_check": {"enabled": False},
            "indicators": {"rsi": {"enabled": False}},
            "execution": {}
        }
        
        # Converte take_profit_percent
        if "take_profit_percent" in rules:
            normalized["take_profit_levels"] = [{
                "percent": float(rules["take_profit_percent"]),
                "quantity_percent": 100,
                "enabled": True
            }]
        
        # Converte stop_loss_percent
        if "stop_loss_percent" in rules:
            normalized["stop_loss"]["percent"] = float(rules["stop_loss_percent"])
        
        # Converte buy_dip_percent
        if "buy_dip_percent" in rules:
            normalized["buy_dip"]["percent"] = float(rules["buy_dip_percent"])
        
        return normalized
    
    @staticmethod
    def get_default_rules() -> Dict:
        """Retorna rules padrão para estratégias simples"""
        return {
            "take_profit_levels": [
                {"percent": 5.0, "quantity_percent": 100, "enabled": True}
            ],
            "stop_loss": {
                "percent": 2.0,
                "enabled": True,
                "trailing_enabled": False
            },
            "buy_dip": {
                "percent": 3.0,
                "enabled": True,
                "dca_enabled": False
            },
            "risk_management": {},
            "cooldown": {"enabled": False},
            "trading_hours": {"enabled": False},
            "blackout_periods": [],
            "volume_check": {"enabled": False},
            "indicators": {"rsi": {"enabled": False}},
            "execution": {
                "min_order_size_usd": 10,
                "max_order_size_percent": 100,
                "allow_partial_fills": True
            }
        }
    
    @staticmethod
    def get_template_rules(template: str) -> Dict:
        """
        Retorna rules pré-configuradas baseadas em template
        
        Templates disponíveis:
        - simple: Estratégia básica (1 TP, sem trailing, sem DCA)
        - conservative: Proteção máxima (2 TPs, trailing, max loss baixo)
        - aggressive: Máximo lucro (3 TPs, DCA, max loss alto)
        
        Args:
            template: Nome do template ('simple', 'conservative', 'aggressive')
            
        Returns:
            Dict com rules configuradas
        """
        templates = {
            "simple": {
                "take_profit_levels": [
                    {"percent": 5.0, "quantity_percent": 100, "enabled": True}
                ],
                "stop_loss": {
                    "percent": 2.0,
                    "enabled": True,
                    "trailing_enabled": False
                },
                "buy_dip": {
                    "percent": 3.0,
                    "enabled": True,
                    "dca_enabled": False
                },
                "risk_management": {},
                "cooldown": {"enabled": False},
                "trading_hours": {"enabled": False},
                "blackout_periods": [],
                "volume_check": {"enabled": False},
                "indicators": {"rsi": {"enabled": False}},
                "execution": {
                    "min_order_size_usd": 10,
                    "max_order_size_percent": 100,
                    "allow_partial_fills": True
                }
            },
            
            "conservative": {
                "take_profit_levels": [
                    {"percent": 2.0, "quantity_percent": 50, "enabled": True},
                    {"percent": 4.0, "quantity_percent": 50, "enabled": True}
                ],
                "stop_loss": {
                    "percent": 1.0,
                    "enabled": True,
                    "trailing_enabled": True,
                    "trailing_percent": 0.5,
                    "trailing_activation_percent": 1.0
                },
                "buy_dip": {
                    "percent": 2.0,
                    "enabled": True,
                    "dca_enabled": False
                },
                "risk_management": {
                    "max_daily_loss_usd": 200,
                    "max_weekly_loss_usd": 500,
                    "pause_on_limit": True
                },
                "cooldown": {
                    "enabled": True,
                    "minutes_after_sell": 60,
                    "minutes_after_buy": 30
                },
                "trading_hours": {"enabled": False},
                "blackout_periods": [],
                "volume_check": {
                    "enabled": False,
                    "min_24h_volume_usd": 5000000
                },
                "indicators": {"rsi": {"enabled": False}},
                "execution": {
                    "min_order_size_usd": 10,
                    "max_order_size_percent": 100,
                    "allow_partial_fills": True
                }
            },
            
            "aggressive": {
                "take_profit_levels": [
                    {"percent": 5.0, "quantity_percent": 30, "enabled": True},
                    {"percent": 10.0, "quantity_percent": 40, "enabled": True},
                    {"percent": 20.0, "quantity_percent": 30, "enabled": True}
                ],
                "stop_loss": {
                    "percent": 3.0,
                    "enabled": True,
                    "trailing_enabled": True,
                    "trailing_percent": 2.0,
                    "trailing_activation_percent": 3.0
                },
                "buy_dip": {
                    "percent": 5.0,
                    "enabled": True,
                    "dca_enabled": True,
                    "dca_levels": [
                        {"percent": 5.0, "quantity_percent": 50},
                        {"percent": 8.0, "quantity_percent": 50}
                    ]
                },
                "risk_management": {
                    "max_daily_loss_usd": 1000,
                    "max_weekly_loss_usd": 3000,
                    "pause_on_limit": True
                },
                "cooldown": {
                    "enabled": True,
                    "minutes_after_sell": 15,
                    "minutes_after_buy": 10
                },
                "trading_hours": {"enabled": False},
                "blackout_periods": [],
                "volume_check": {
                    "enabled": False,
                    "min_24h_volume_usd": 10000000
                },
                "indicators": {"rsi": {"enabled": False}},
                "execution": {
                    "min_order_size_usd": 10,
                    "max_order_size_percent": 100,
                    "allow_partial_fills": True
                }
            }
        }
        
        template_lower = template.lower()
        if template_lower not in templates:
            raise ValueError(f"Template inválido: {template}. Use: simple, conservative ou aggressive")
        
        return templates[template_lower]
