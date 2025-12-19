# 🚀 Deploy no Render

## Opções de Start Command

O Render suporta múltiplas formas de iniciar a aplicação:

### ✅ Opção 1: wsgi.py (Recomendado)
```bash
gunicorn wsgi:app --workers=1 --threads=4 --timeout=120 --bind 0.0.0.0:$PORT
```

### ✅ Opção 2: run.py
```bash
gunicorn run:app --workers=1 --threads=4 --timeout=120 --bind 0.0.0.0:$PORT
```

### ✅ Opção 3: app.py (Fallback)
```bash
gunicorn app:app --workers=1 --threads=4 --timeout=120 --bind 0.0.0.0:$PORT
```

### ⚠️ Opção 4: Flask Development (Não recomendado para produção)
```bash
python run.py
```

## 🔧 Configuração no Render Dashboard

Se o `render.yaml` não estiver sendo usado:

1. Acesse o dashboard do Render
2. Vá em **Settings** do seu serviço
3. Em **Build & Deploy** > **Start Command**, use:
   ```
   gunicorn wsgi:app --workers=1 --threads=4 --timeout=120 --bind 0.0.0.0:$PORT
   ```

## 📦 Build Command

```bash
pip install -r requirements.txt
```

## 🌍 Variáveis de Ambiente Obrigatórias

```bash
MONGODB_URI=mongodb+srv://...
MONGODB_DATABASE=MultExchange
ENCRYPTION_KEY=your-32-char-encryption-key
FLASK_ENV=production
FLASK_DEBUG=False
PORT=10000  # Render define automaticamente
```

## 🐛 Troubleshooting

### Erro: "No module named 'app'"

**Solução:** Altere o start command para usar `wsgi:app` em vez de `app:app`:
```bash
gunicorn wsgi:app --bind 0.0.0.0:$PORT
```

### Erro: "Address already in use"

**Solução:** Use a variável `$PORT` do Render:
```bash
--bind 0.0.0.0:$PORT
```

### Erro: "Worker timeout"

**Solução:** Aumente o timeout:
```bash
--timeout=120
```

## 📝 Estrutura de Entry Points

```
automatic/
├── wsgi.py          # ✅ WSGI entry point (recomendado)
├── run.py           # ✅ Development + Gunicorn
├── app.py           # ✅ Fallback compatibility
└── src/
    └── api/
        └── main.py  # Flask app principal
```

Todos os arquivos acima importam o mesmo `app` de `src/api/main.py`.
