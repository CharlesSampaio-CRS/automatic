"""
Script para demonstrar o novo campo STATUS nos logs
"""

import sys
sys.path.append('/Users/charles.roberto/Documents/projects/crs-saturno/automatic')

from src.database.mongodb_connection import get_database
from datetime import datetime

def get_status_icon(status):
    """Retorna ícone baseado no status"""
    icons = {
        "buy": "💰 Compra Executada",
        "sell": "💸 Venda Executada",
        "buy_and_sell": "🔄 Compra e Venda",
        "no_action": "⏸️  Sem Operação",
        "error": "❌ Erro"
    }
    return icons.get(status, "❓ Desconhecido")

def get_status_color_class(status):
    """Retorna classe CSS para o status (exemplo para frontend)"""
    colors = {
        "buy": "success",
        "sell": "info",
        "buy_and_sell": "primary",
        "no_action": "secondary",
        "error": "danger"
    }
    return colors.get(status, "secondary")

def demo_status_field():
    """Demonstra o novo campo status"""
    print("\n" + "="*80)
    print("✨ NOVO CAMPO: STATUS NOS LOGS DE EXECUÇÃO")
    print("="*80 + "\n")
    
    print("📋 Possíveis valores de STATUS:\n")
    print("   1. 'buy'          → 💰 Compra executada com sucesso")
    print("   2. 'sell'         → 💸 Venda executada com sucesso")
    print("   3. 'buy_and_sell' → 🔄 Compra E venda na mesma execução (raro)")
    print("   4. 'no_action'    → ⏸️  Nenhuma operação realizada")
    print("   5. 'error'        → ❌ Erro durante a execução")
    
    print("\n" + "="*80)
    print("📱 EXEMPLO DE ESTRUTURA DO LOG:")
    print("="*80 + "\n")
    
    example_log = {
        "execution_type": "scheduled",
        "executed_by": "scheduler",
        "timestamp": "2025-12-04T15:30:00-03:00",
        "pair": "REKTCOIN/USDT",
        "status": "buy",  # ← NOVO CAMPO!
        "summary": {
            "buy_executed": True,
            "sell_executed": False,
            "total_invested": "4.50",
            "total_profit": "0.00",
            "net_result": "0.00"
        },
        "buy_details": "...",
        "sell_details": "...",
        "market_info": "..."
    }
    
    import json
    print(json.dumps(example_log, indent=2))
    
    print("\n" + "="*80)
    print("💻 EXEMPLO DE USO NO FRONTEND (React/Vue/Angular):")
    print("="*80 + "\n")
    
    print("""
// JavaScript/TypeScript
const getStatusBadge = (status) => {
  switch(status) {
    case 'buy':
      return <Badge color="success">💰 Compra</Badge>;
    case 'sell':
      return <Badge color="info">💸 Venda</Badge>;
    case 'buy_and_sell':
      return <Badge color="primary">🔄 Compra/Venda</Badge>;
    case 'no_action':
      return <Badge color="secondary">⏸️ Sem Ação</Badge>;
    case 'error':
      return <Badge color="danger">❌ Erro</Badge>;
    default:
      return <Badge>❓ Desconhecido</Badge>;
  }
};

// Exemplo de renderização
{logs.map(log => (
  <tr key={log._id}>
    <td>{log.pair}</td>
    <td>{formatDate(log.timestamp)}</td>
    <td>{getStatusBadge(log.status)}</td>
    <td>${log.summary.net_result}</td>
  </tr>
))}
""")
    
    print("\n" + "="*80)
    print("🎨 EXEMPLO DE CSS PARA OS STATUS:")
    print("="*80 + "\n")
    
    print("""
.status-buy {
  background-color: #28a745;
  color: white;
  padding: 4px 12px;
  border-radius: 12px;
}

.status-sell {
  background-color: #17a2b8;
  color: white;
  padding: 4px 12px;
  border-radius: 12px;
}

.status-no_action {
  background-color: #6c757d;
  color: white;
  padding: 4px 12px;
  border-radius: 12px;
}

.status-error {
  background-color: #dc3545;
  color: white;
  padding: 4px 12px;
  border-radius: 12px;
}
""")
    
    print("\n" + "="*80)
    print("🔍 VERIFICANDO LOGS EXISTENTES (se houver):")
    print("="*80 + "\n")
    
    try:
        db = get_database()
        logs_db = db["ExecutionLogs"]
        
        # Verifica se já existe algum log com status
        recent_logs = list(logs_db.find().sort("timestamp", -1).limit(5))
        
        if recent_logs:
            print(f"Encontrados {len(recent_logs)} logs recentes:\n")
            print(f"{'Par':<20} {'Timestamp':<25} {'Status':<20} {'Resultado'}")
            print("-" * 80)
            
            for log in recent_logs:
                pair = log.get('pair', 'N/A')
                timestamp = log.get('timestamp', 'N/A')[:19]
                status = log.get('status', 'N/A')  # Novo campo
                net_result = log.get('summary', {}).get('net_result', '0.00')
                
                status_display = get_status_icon(status) if status != 'N/A' else "❓ Campo não existe ainda"
                
                print(f"{pair:<20} {timestamp:<25} {status_display:<30} ${net_result}")
            
            # Verifica se o campo 'status' existe
            has_status = any('status' in log for log in recent_logs)
            
            if has_status:
                print("\n✅ Campo 'status' JÁ EXISTE nos logs!")
            else:
                print("\n⚠️  Campo 'status' ainda NÃO EXISTE nos logs antigos")
                print("   Os novos logs (após deploy) terão este campo automaticamente")
        else:
            print("⚠️  Nenhum log encontrado no banco")
            
    except Exception as e:
        print(f"❌ Erro ao verificar logs: {e}")
    
    print("\n" + "="*80)
    print("✅ DEMONSTRAÇÃO COMPLETA")
    print("="*80 + "\n")

if __name__ == "__main__":
    demo_status_field()
