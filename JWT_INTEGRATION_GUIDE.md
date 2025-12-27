# 🔐 JWT Authentication Integration Guide

## Status da Implementação Backend

### ✅ Endpoints Protegidos (Concluído)

#### **Autenticação (3 endpoints)**
- `POST /api/v1/auth/login` - Login OAuth (Google/Apple) - **Público**
- `POST /api/v1/auth/refresh` - Renovar access token - **Público**
- `GET /api/v1/auth/verify` - Verificar token JWT - **@require_auth**

#### **Balances (4 endpoints)**
- `GET /api/v1/balances` - **@require_auth + @require_params('user_id')**
- `GET /api/v1/balances/summary` - **@require_auth + @require_params('user_id')**
- `GET /api/v1/balances/exchange/<exchange_id>` - **@require_auth + @require_params('user_id')**
- `POST /api/v1/balances/clear-cache` - **@require_auth**

#### **Exchanges (2 endpoints)**
- `GET /api/v1/exchanges/linked` - **@require_auth + @require_params('user_id')**
- `POST /api/v1/exchanges/link` - **@require_auth + @require_params('user_id', 'exchange_id', 'api_key', 'api_secret')**

#### **Orders/Trading (2 endpoints)**
- `GET /api/v1/orders/open` - **@require_auth + @require_params('user_id', 'exchange_id')**
- `POST /api/v1/orders/create` - **@require_auth + @require_params('user_id', 'exchange_id', 'symbol', 'side', 'type', 'amount')**

#### **Strategies (3 endpoints)**
- `POST /api/v1/strategies` - **@require_auth + @require_params('user_id', 'exchange_id', 'token')**
- `GET /api/v1/strategies` - **@require_auth + @require_params('user_id')**
- `DELETE /api/v1/strategies/<strategy_id>` - **@require_auth + ownership verification**

---

## 🚀 Frontend Integration Guide

### 1. Fluxo de Login OAuth

#### **Login com Google/Apple**
```typescript
// services/authService.ts
import AsyncStorage from '@react-native-async-storage/async-storage';

export async function loginWithOAuth(provider: 'google' | 'apple', email: string, name: string) {
  const response = await fetch('http://localhost:5000/api/v1/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      provider,
      email,
      name,
    }),
  });

  const data = await response.json();

  if (data.success) {
    // Armazenar tokens no AsyncStorage
    await AsyncStorage.setItem('access_token', data.access_token);
    await AsyncStorage.setItem('refresh_token', data.refresh_token);
    await AsyncStorage.setItem('user_id', data.user.user_id);
    await AsyncStorage.setItem('user_email', data.user.email);
    
    return data.user;
  } else {
    throw new Error(data.error || 'Login failed');
  }
}
```

### 2. Adicionar Authorization Header em Todas as Requisições

#### **Atualizar api.ts**
```typescript
// services/api.ts
import AsyncStorage from '@react-native-async-storage/async-storage';

export async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeout: number = 30000
): Promise<Response> {
  // Adicionar token JWT automaticamente
  const accessToken = await AsyncStorage.getItem('access_token');
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  // Adicionar Authorization header se token existir
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    // Se 401 (token expirado), tentar refresh
    if (response.status === 401) {
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        // Retry com novo token
        const newToken = await AsyncStorage.getItem('access_token');
        headers['Authorization'] = `Bearer ${newToken}`;
        
        return await fetch(url, {
          ...options,
          headers,
        });
      } else {
        // Logout se refresh falhar
        await logout();
        throw new Error('Session expired');
      }
    }

    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    throw error;
  }
}
```

### 3. Implementar Refresh Token

```typescript
// services/authService.ts
export async function refreshAccessToken(): Promise<boolean> {
  try {
    const refreshToken = await AsyncStorage.getItem('refresh_token');
    
    if (!refreshToken) {
      return false;
    }

    const response = await fetch('http://localhost:5000/api/v1/auth/refresh', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        refresh_token: refreshToken,
      }),
    });

    const data = await response.json();

    if (data.success) {
      // Atualizar access token
      await AsyncStorage.setItem('access_token', data.access_token);
      return true;
    }

    return false;
  } catch (error) {
    console.error('Refresh token failed:', error);
    return false;
  }
}
```

### 4. Implementar Logout

```typescript
// services/authService.ts
export async function logout() {
  await AsyncStorage.multiRemove([
    'access_token',
    'refresh_token',
    'user_id',
    'user_email',
  ]);
  
  // Redirecionar para login
  // navigation.navigate('Login');
}
```

### 5. Atualizar Chamadas API

#### **Exemplo: Buscar Balances**
```typescript
// Antes (sem JWT)
const response = await fetchWithTimeout(
  `${API_BASE_URL}/balances?user_id=${userId}`,
);

// Depois (com JWT) - NÃO MUDA NADA!
// O token é adicionado automaticamente pelo fetchWithTimeout
const response = await fetchWithTimeout(
  `${API_BASE_URL}/balances?user_id=${userId}`,
);
```

### 6. Tratamento de Erros

```typescript
// contexts/AuthContext.tsx
try {
  const response = await fetchWithTimeout(`${API_BASE_URL}/balances?user_id=${userId}`);
  const data = await response.json();
  
  if (!response.ok) {
    if (response.status === 401) {
      // Token inválido ou expirado
      Alert.alert('Sessão Expirada', 'Faça login novamente');
      await logout();
    } else if (response.status === 403) {
      // user_id mismatch
      Alert.alert('Erro', 'Você não tem permissão para acessar estes dados');
    } else if (response.status === 400) {
      // Parâmetros ausentes
      Alert.alert('Erro', data.error || 'Parâmetros inválidos');
    }
  }
  
  return data;
} catch (error) {
  console.error('API Error:', error);
  throw error;
}
```

---

## 🔒 Códigos HTTP Retornados

| Código | Descrição | Ação Recomendada |
|--------|-----------|------------------|
| **200/201** | Sucesso | Processar resposta normalmente |
| **400** | Parâmetros ausentes/inválidos | Mostrar erro ao usuário |
| **401** | Token ausente, inválido ou expirado | Tentar refresh, depois logout |
| **403** | user_id do token ≠ user_id do parâmetro | Mostrar erro e fazer logout |
| **404** | Recurso não encontrado | Mostrar mensagem apropriada |
| **429** | Rate limit excedido | Aguardar retry_after segundos |
| **500** | Erro interno do servidor | Mostrar erro genérico |

---

## 📝 Exemplo Completo: AuthContext

```typescript
// contexts/AuthContext.tsx
import React, { createContext, useState, useEffect, useContext } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { loginWithOAuth, refreshAccessToken, logout } from '../services/authService';

interface User {
  user_id: string;
  email: string;
  name: string;
  provider: 'google' | 'apple';
}

interface AuthContextData {
  user: User | null;
  loading: boolean;
  signIn: (provider: 'google' | 'apple', email: string, name: string) => Promise<void>;
  signOut: () => Promise<void>;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextData>({} as AuthContextData);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStoredUser();
  }, []);

  async function loadStoredUser() {
    try {
      const userId = await AsyncStorage.getItem('user_id');
      const email = await AsyncStorage.getItem('user_email');
      const name = await AsyncStorage.getItem('user_name');
      const provider = await AsyncStorage.getItem('user_provider');

      if (userId && email) {
        setUser({
          user_id: userId,
          email,
          name: name || '',
          provider: (provider as 'google' | 'apple') || 'google',
        });
      }
    } catch (error) {
      console.error('Error loading user:', error);
    } finally {
      setLoading(false);
    }
  }

  async function signIn(provider: 'google' | 'apple', email: string, name: string) {
    try {
      const userData = await loginWithOAuth(provider, email, name);
      setUser(userData);
      await AsyncStorage.setItem('user_name', name);
      await AsyncStorage.setItem('user_provider', provider);
    } catch (error) {
      console.error('Sign in error:', error);
      throw error;
    }
  }

  async function signOut() {
    await logout();
    setUser(null);
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        signIn,
        signOut,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
```

---

## ⚠️ Notas Importantes

### **Backend**
1. **JWT_SECRET**: Atualmente usa valor padrão. Em produção, defina variável de ambiente:
   ```bash
   export JWT_SECRET="sua-chave-super-secreta-aqui"
   ```

2. **Token Expiration**:
   - Access Token: 24 horas
   - Refresh Token: 30 dias

3. **Ownership Verification**: 
   - DELETE /strategies/<id> verifica se a strategy pertence ao usuário
   - Retorna 403 se tentar deletar strategy de outro usuário

### **Frontend**
1. **AsyncStorage**: Armazene tokens de forma segura
2. **Token Refresh**: Implementar interceptor para renovação automática
3. **Logout Automático**: Se refresh falhar, fazer logout
4. **Header Obrigatório**: Todas as requisições protegidas precisam do header `Authorization: Bearer <token>`

---

## 🧪 Testando com curl

### **1. Login**
```bash
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "google",
    "email": "user@example.com",
    "name": "Test User"
  }'
```

### **2. Acessar Endpoint Protegido**
```bash
# Salve o access_token da resposta anterior
TOKEN="eyJ0eXAiOiJKV1QiLCJhbGc..."

curl -X GET "http://localhost:5000/api/v1/balances?user_id=67829f79a7d5a5c744877a94" \
  -H "Authorization: Bearer $TOKEN"
```

### **3. Refresh Token**
```bash
REFRESH_TOKEN="eyJ0eXAiOiJKV1QiLCJhbGc..."

curl -X POST http://localhost:5000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$REFRESH_TOKEN\"}"
```

### **4. Verificar Token**
```bash
curl -X GET http://localhost:5000/api/v1/auth/verify \
  -H "Authorization: Bearer $TOKEN"
```

---

## 📊 Endpoints Restantes (Pendentes)

### **Exchanges**
- GET /api/v1/exchanges/available (público - não precisa JWT)
- POST /api/v1/exchanges/unlink
- POST /api/v1/exchanges/disconnect
- DELETE /api/v1/exchanges/delete
- POST /api/v1/exchanges/connect
- GET /api/v1/exchanges/<id>
- GET /api/v1/exchanges/<id>/markets
- GET /api/v1/exchanges/<id>/token/<symbol>

### **Orders**
- POST /api/v1/orders/cancel
- POST /api/v1/orders/cancel-all
- GET /api/v1/orders/list
- POST /api/v1/orders/monitor
- GET /api/v1/orders/status/<order_id>
- POST /api/v1/orders/buy
- POST /api/v1/orders/sell
- GET /api/v1/orders/history

### **Strategies**
- PUT /api/v1/strategies/<strategy_id>
- GET /api/v1/strategies/<strategy_id>
- POST /api/v1/strategies/<strategy_id>/check
- GET /api/v1/strategies/<strategy_id>/stats

---

## 🎯 Próximos Passos

### Backend
1. ✅ Aplicar @require_auth + @require_params nos demais endpoints
2. ✅ Adicionar ownership verification onde necessário
3. ⏳ Testar todos os fluxos com Postman
4. ⏳ Configurar JWT_SECRET em produção

### Frontend
1. ⏳ Implementar AuthContext completo
2. ⏳ Atualizar api.ts com interceptor JWT
3. ⏳ Implementar tela de Login OAuth
4. ⏳ Testar fluxo completo (login → API calls → refresh → logout)
5. ⏳ Tratamento de erros 401/403

---

**Última Atualização**: 27/12/2025
**Backend Commits**: 
- `b721636` - JWT authentication module (Kong-style)
- `1767c4a` - Request validators e documentação
- `717b31f` - Decorators em Balances, Exchanges, Orders
- `535436f` - Decorators em Strategies
