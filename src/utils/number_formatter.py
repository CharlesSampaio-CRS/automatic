"""
Utilitário de Formatação de Números

Converte notação científica e formata valores numéricos adequadamente
"""
from decimal import Decimal, ROUND_HALF_UP


def format_number(value, decimal_places=8):
    """
    Formata número removendo notação científica
    
    Args:
        value: Valor numérico (float, int, str)
        decimal_places: Casas decimais (padrão 8)
    
    Returns:
        string formatado ou "0.0" se inválido
    
    Examples:
        2.7556e-07 → "0.00000028"
        1.234e+05 → "123400.00000000"
        0.00000001 → "0.00000001"
    """
    try:
        if value is None or value == 0:
            return "0." + "0" * decimal_places
        
        # Converte para Decimal para evitar notação científica
        if isinstance(value, str):
            decimal_value = Decimal(value)
        else:
            decimal_value = Decimal(str(value))
        
        # Define o formato de quantização
        quantize_format = Decimal(10) ** -decimal_places
        
        # Arredonda
        rounded = decimal_value.quantize(quantize_format, rounding=ROUND_HALF_UP)
        
        # Converte para string sem notação científica
        # Remove zeros desnecessários à direita, mas mantém pelo menos 1 casa decimal
        result_str = f"{rounded:.{decimal_places}f}"
        
        return result_str
    
    except Exception:
        return "0." + "0" * decimal_places

def format_price(value):
    """
    Formata preços (8 casas decimais) - retorna string
    
    Args:
        value: Preço a formatar
    
    Returns:
        string com 8 casas decimais
    """
    return format_number(value, decimal_places=8)


def format_amount(value):
    """
    Formata quantidades (8 casas decimais) - retorna string
    
    Args:
        value: Quantidade a formatar
    
    Returns:
        string com 8 casas decimais
    """
    return format_number(value, decimal_places=8)


def format_usdt(value):
    """
    Formata valores em USDT (2 casas decimais) - retorna string
    
    Args:
        value: Valor em USDT a formatar
    
    Returns:
        string com 2 casas decimais
    """
    return format_number(value, decimal_places=2)


def format_percent(value):
    """
    Formata percentuais (2 casas decimais) - retorna string
    
    Args:
        value: Percentual a formatar
    
    Returns:
        string com 2 casas decimais
    """
    return format_number(value, decimal_places=2)


def safe_float(value, default=0.0):
    """
    Converte valor para float com segurança
    
    Args:
        value: Valor a converter
        default: Valor padrão se conversão falhar
    
    Returns:
        float ou default
    """
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default
