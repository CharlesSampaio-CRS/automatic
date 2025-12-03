"""
Estratégia de Venda Progressiva (Scaling Out)
Vende em partes conforme o preço aumenta
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime

class SellStrategy:
    """
    Gerencia vendas progressivas em múltiplos níveis
    Recebe configurações do MongoDB
    """
    
    def __init__(self, sell_strategy: Optional[Dict] = None):
        """
        Inicializa estratégia com configuração do MongoDB
        
        Args:
            sell_strategy: Configuração de sell_strategy do MongoDB
                          Se None, usa níveis padrão
        """
        if sell_strategy and isinstance(sell_strategy, dict):
            levels_config = sell_strategy.get('levels', [])
            
            # Converte configuração para formato interno
            self.sell_levels = []
            for level in levels_config:
                self.sell_levels.append({
                    "percentage": level.get('sell_percent', level.get('sell_percentage', 33)),
                    "profit_target": level.get('profit_percent', level.get('profit_target', 5.0)),
                    "name": level.get('name', f"Nível {len(self.sell_levels) + 1}"),
                    "description": level.get('description', '')
                })
            
            if not self.sell_levels:
                self.sell_levels = self._get_default_levels()
        else:
            self.sell_levels = self._get_default_levels()
    
    def _get_default_levels(self):
        """Retorna níveis de venda padrão"""
        return [
            {"percentage": 33, "profit_target": 5.0,  "name": "Nível 1 - Lucro Seguro"},
            {"percentage": 33, "profit_target": 10.0, "name": "Nível 2 - Lucro Médio"},
            {"percentage": 34, "profit_target": 15.0, "name": "Nível 3 - Lucro Máximo"}
        ]
    
    def get_min_profit_for_symbol(self, symbol: str) -> float:
        """
        Retorna o lucro mínimo configurado para o símbolo
        Usa o primeiro nível de venda como referência (mais conservador)
        
        Args:
            symbol: Par de Tranding (ex: REKTCOIN/USDT)
        
        Returns:
            Percentual de lucro mínimo (ex: 5.0 para 5%)
        """
        if self.sell_levels and len(self.sell_levels) > 0:
            return self.sell_levels[0]["profit_target"]
        return 5.0  # Padrão: 5% de lucro mínimo
    
    def should_sell(self, current_price: float, buy_price: float, symbol: str) -> bool:
        """
        Verifica se deve vender baseado no lucro mínimo configurado
        
        Args:
            current_price: Preço atual do ativo
            buy_price: Preço de compra do ativo
            symbol: Par de Tranding (ex: REKTCOIN/USDT)
        
        Returns:
            True se deve vender, False caso contrário
        """
        if buy_price <= 0:
            return False
        
        # Calcula lucro percentual
        profit_percent = ((current_price - buy_price) / buy_price) * 100
        
        # Busca lucro mínimo configurado
        min_profit = self.get_min_profit_for_symbol(symbol)
        
        # Vende se lucro atual >= lucro mínimo
        return profit_percent >= min_profit
    
    def calculate_sell_targets(self, buy_price: float, amount_bought: float, 
                               investment_value: float) -> List[Dict]:
        """
        Calcula os alvos de venda em múltiplos níveis
        
        Args:
            buy_price: Preço de compra
            amount_bought: Quantidade comprada
            investment_value: Valor investido em USDT
        
        Returns:
            Lista de alvos de venda com preços e quantidades
        """
        targets = []
        remaining_amount = amount_bought
        
        for level in self.sell_levels:
            # Calcula quantidade a vender neste nível
            sell_amount = (amount_bought * level["percentage"]) / 100
            
            # Calcula preço alvo (buy_price + lucro%)
            target_price = buy_price * (1 + level["profit_target"] / 100)
            
            # Calcula valor que vai receber (ANTES de arredondar para evitar perda de precisão)
            usdt_received = sell_amount * target_price
            
            # Calcula lucro deste nível
            invested_in_level = (investment_value * level["percentage"]) / 100
            profit_usdt = usdt_received - invested_in_level
            profit_pct = level["profit_target"]
            
            targets.append({
                "level": len(targets) + 1,
                "name": level["name"],
                "sell_percentage": level["percentage"],
                "sell_amount": round(sell_amount, 8),
                "target_price": round(target_price, 8),
                "profit_target_pct": profit_pct,
                "usdt_received": round(usdt_received, 2),  # Arredonda DEPOIS do cálculo
                "profit_usdt": round(profit_usdt, 2),  # Arredonda DEPOIS do cálculo
                "invested_in_level": round(invested_in_level, 2),
                "executed": False,
                "execution_date": None,
                "actual_price": None,
                "actual_profit": None
            })
            
            remaining_amount -= sell_amount
        
        return targets
    
    def check_sell_opportunities(self, current_price: float, 
                                  sell_targets: List[Dict]) -> List[Dict]:
        """
        Verifica quais níveis de venda devem ser executados
        
        Args:
            current_price: Preço atual do ativo
            sell_targets: Lista de alvos de venda
        
        Returns:
            Lista de vendas a executar
        """
        to_execute = []
        
        for target in sell_targets:
            # Se já foi executado, pula
            if target["executed"]:
                continue
            
            # Se preço atual >= preço alvo, vende
            if current_price >= target["target_price"]:
                target["actual_price"] = current_price
                target["actual_profit"] = round(
                    (target["sell_amount"] * current_price) - target["invested_in_level"], 
                    2
                )
                to_execute.append(target)
        
        return to_execute
    
    def execute_sell_level(self, symbol: str, target: Dict, 
                           actual_price: float, mexc_client) -> Dict:
        """
        Executa venda de um nível específico
        
        Args:
            symbol: Par de Tranding (ex: REKT/USDT)
            target: Alvo de venda a executar
            actual_price: Preço atual
            mexc_client: Cliente MEXC para executar ordem
        
        Returns:
            Resultado da execução
        """
        try:
            # Cria ordem de venda no mercado
            order = mexc_client.client.create_market_sell_order(
                symbol, 
                float(target["sell_amount"])
            )
            
            target["executed"] = True
            target["execution_date"] = datetime.now()
            target["actual_price"] = actual_price
            
            # Calcula lucro real
            usdt_received = target["sell_amount"] * actual_price
            target["actual_profit"] = round(
                usdt_received - target["invested_in_level"], 
                2
            )
            
            return {
                "success": True,
                "level": target["level"],
                "name": target["name"],
                "amount_sold": target["sell_amount"],
                "sell_price": actual_price,
                "usdt_received": round(usdt_received, 2),
                "profit": target["actual_profit"],
                "order_id": order.get("id"),
                "message": f"✅ {target['name']} executado com sucesso!"
            }
            
        except Exception as e:
            return {
                "success": False,
                "level": target["level"],
                "name": target["name"],
                "error": str(e),
                "message": f"❌ Erro ao executar {target['name']}: {e}"
            }
    
    def get_summary(self, sell_targets: List[Dict], 
                    buy_price: float, current_price: float) -> Dict:
        """
        Retorna um resumo do progresso das vendas
        """
        executed = [t for t in sell_targets if t["executed"]]
        pending = [t for t in sell_targets if not t["executed"]]
        
        total_invested = sum(t["invested_in_level"] for t in sell_targets)
        total_profit_expected = sum(t["profit_usdt"] for t in sell_targets)
        realized_profit = sum(t.get("actual_profit", 0) for t in executed)
        pending_profit = sum(t["profit_usdt"] for t in pending)
        
        # Calcula progresso
        current_profit_pct = ((current_price - buy_price) / buy_price) * 100 if buy_price > 0 else 0
        
        return {
            "buy_price": buy_price,
            "current_price": current_price,
            "current_profit_pct": round(current_profit_pct, 2),
            "total_invested": round(total_invested, 2),
            "total_levels": len(sell_targets),
            "executed_levels": len(executed),
            "pending_levels": len(pending),
            "realized_profit": round(realized_profit, 2),
            "pending_profit": round(pending_profit, 2),
            "total_expected_profit": round(total_profit_expected, 2),
            "completion_pct": round((len(executed) / len(sell_targets)) * 100, 2) if sell_targets else 0,
            "next_target": pending[0] if pending else None
        }


def example_usage():
    """
    Exemplo de uso da estratégia de venda progressiva
    """
    print("\n" + "="*80)
    print("🎯 ESTRATÉGIA DE VENDA PROGRESSIVA - Exemplo")
    print("="*80)
    
    # Configuração da compra
    buy_price = 0.00000135
    amount_bought = 74074074.07
    investment = 100.00
    
    print(f"\n📊 POSIÇÃO COMPRADA:")
    print(f"   Preço de Compra: ${buy_price:.8f}")
    print(f"   Quantidade: {amount_bought:,.2f} REKT")
    print(f"   Investimento: ${investment:.2f} USDT")
    
    # Cria estratégia
    strategy = SellStrategy()
    
    # Calcula alvos de venda
    sell_targets = strategy.calculate_sell_targets(buy_price, amount_bought, investment)
    
    print(f"\n🎯 ALVOS DE VENDA CONFIGURADOS:")
    print(f"   {'Nível':<8} {'% Venda':<10} {'Preço Alvo':<15} {'Lucro':<10} {'Recebe':<12} {'Lucro $':<10}")
    print(f"   {'-'*75}")
    
    for target in sell_targets:
        print(f"   Nível {target['level']:<3} "
              f"{target['sell_percentage']}%{' '*6} "
              f"${target['target_price']:.8f}  "
              f"+{target['profit_target_pct']}%{' '*5} "
              f"${target['usdt_received']:.2f}{' '*5} "
              f"+${target['profit_usdt']:.2f}")
    
    # Simula diferentes cenários de preço
    scenarios = [
        (0.00000140, "Pequena alta +3.7%"),
        (0.00000142, "Alta de +5.2%"),
        (0.00000149, "Alta de +10.4%"),
        (0.00000156, "Alta de +15.6%")
    ]
    
    for current_price, description in scenarios:
        print(f"\n{'='*80}")
        print(f"📈 CENÁRIO: Preço atual ${current_price:.8f} ({description})")
        print(f"{'='*80}")
        
        # Verifica oportunidades de venda
        to_sell = strategy.check_sell_opportunities(current_price, sell_targets)
        
        if to_sell:
            print(f"\n✅ VENDAS A EXECUTAR: {len(to_sell)} nível(is)")
            for target in to_sell:
                print(f"\n   🎯 {target['name']}")
                print(f"      Vender: {target['sell_amount']:,.2f} REKT ({target['sell_percentage']}%)")
                print(f"      Preço: ${target['actual_price']:.8f}")
                print(f"      Receber: ${target['sell_amount'] * target['actual_price']:.2f} USDT")
                print(f"      Lucro: +${target['actual_profit']:.2f} USDT")
                
                # Marca como executado para próxima iteração
                target["executed"] = True
        else:
            print(f"\n⏸️  Nenhuma venda a executar neste preço")
        
        # Mostra resumo
        summary = strategy.get_summary(sell_targets, buy_price, current_price)
        print(f"\n📊 RESUMO DA POSIÇÃO:")
        print(f"   Lucro Atual: {summary['current_profit_pct']:+.2f}%")
        print(f"   Níveis Executados: {summary['executed_levels']}/{summary['total_levels']}")
        print(f"   Lucro Realizado: ${summary['realized_profit']:.2f}")
        print(f"   Lucro Pendente: ${summary['pending_profit']:.2f}")
        print(f"   Progresso: {summary['completion_pct']:.1f}%")
        
        if summary['next_target']:
            next_t = summary['next_target']
            print(f"\n   🎯 Próximo Alvo: {next_t['name']}")
            print(f"      Preço: ${next_t['target_price']:.8f} (+{next_t['profit_target_pct']}%)")
            print(f"      Lucro Esperado: +${next_t['profit_usdt']:.2f}")
    
    print("\n" + "="*80)
    print("💡 VANTAGENS DA VENDA PROGRESSIVA:")
    print("="*80)
    print("✅ Garante lucro em diferentes níveis")
    print("✅ Não precisa acertar o topo do mercado")
    print("✅ Reduz risco de perder todos os ganhos")
    print("✅ Maximiza lucro se continuar subindo")
    print("✅ Realiza lucros parciais no caminho")
    print("="*80 + "\n")


if __name__ == "__main__":
    example_usage()
