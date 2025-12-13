"""
Utilitários de formatação de valores numéricos
"""

def format_decimal(value, decimals=10):
    """
    Formata um valor numérico como string com casas decimais fixas.
    Evita notação científica em valores muito pequenos.
    
    Args:
        value: Valor numérico a ser formatado
        decimals: Número de casas decimais (padrão: 10)
    
    Returns:
        String formatada com casas decimais fixas
    
    Examples:
        >>> format_decimal(0.00000030, 10)
        '0.0000003000'
        >>> format_decimal(135.02, 2)
        '135.02'
        >>> format_decimal(0, 10)
        '0.0000000000'
    """
    if value is None or value == 0:
        return "0." + "0" * decimals
    return f"{float(value):.{decimals}f}"


def format_price(value):
    """
    Formata preço com decimais variáveis:
    - 10 decimais para valores absolutos < 1
    - 2 decimais para valores absolutos >= 1
    
    Args:
        value: Preço a ser formatado
    
    Returns:
        String com decimais apropriados
    
    Examples:
        >>> format_price(0.00000030)
        '0.0000003000'
        >>> format_price(89448.62)
        '89448.62'
        >>> format_price(-31.94)
        '-31.94'
    """
    if value is None or value == 0:
        return "0.0000000000"
    
    float_value = float(value)
    if abs(float_value) < 1:
        return f"{float_value:.10f}"
    else:
        return f"{float_value:.2f}"


def format_amount(value):
    """
    Formata quantidade/amount com decimais variáveis:
    - 10 decimais para valores absolutos < 1
    - 2 decimais para valores absolutos >= 1
    
    Args:
        value: Quantidade a ser formatada
    
    Returns:
        String com decimais apropriados
    """
    if value is None or value == 0:
        return "0.0000000000"
    
    float_value = float(value)
    if abs(float_value) < 1:
        return f"{float_value:.10f}"
    else:
        return f"{float_value:.2f}"


def format_usd(value):
    """
    Formata valor em USD com 2 casas decimais.
    
    Args:
        value: Valor em USD a ser formatado
    
    Returns:
        String com 2 casas decimais
    """
    return format_decimal(value, 2)


def format_brl(value):
    """
    Formata valor em BRL com 2 casas decimais.
    
    Args:
        value: Valor em BRL a ser formatado
    
    Returns:
        String com 2 casas decimais
    """
    return format_decimal(value, 2)


def format_percent(value):
    """
    Formata percentual com 2 casas decimais.
    
    Args:
        value: Percentual a ser formatado
    
    Returns:
        String com 2 casas decimais
    """
    return format_decimal(value, 2)


def format_rate(value):
    """
    Formata taxa de câmbio com 4 casas decimais.
    
    Args:
        value: Taxa a ser formatada
    
    Returns:
        String com 4 casas decimais
    """
    return format_decimal(value, 4)
