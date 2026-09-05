# Publicando o BetAnalyzer de graça (Vercel + Koyeb)

Guia passo a passo para colocar o BetAnalyzer no ar: frontend na **Vercel** e
backend (API + coletor + banco SQLite) na **Koyeb**, usando os planos
gratuitos de ambas.

Antes de começar, tenha em mãos:

- Uma conta no [GitHub](https://github.com) (as duas plataformas fazem deploy
  a partir de um repositório git).
- Uma conta na [Vercel](https://vercel.com) (pode entrar direto com o GitHub).
- Uma conta na [Koyeb](https://www.koyeb.com) (também dá pra entrar com o GitHub).
- Sua chave da API-Football (a mesma que já está no seu `.env` local, em
  `API_FOOTBALL_KEY`).

---

## Passo 1 — Subir o projeto para o GitHub

Se o projeto ainda não está em um repositório git, na pasta
`C:\Projetos\ApiEstatisticas` (PowerShell ou terminal do VS Code):

```
git init
git add .
git commit -m "BetAnalyzer - versao inicial para deploy"
```

Depois crie um repositório novo (privado, se preferir) no GitHub e siga as
instruções que o próprio GitHub mostra para "push an existing repository":

```
git remote add origin https://github.com/SEU_USUARIO/betanalyzer.git
git branch -M main
git push -u origin main
```

O `.gitignore` do projeto já exclui o `.env`, o `betanalyzer.db` e as pastas
`node_modules`/`dist` — então sua chave de API e o banco local não vão parar
no GitHub. Bom, é assim mesmo que tem que ser.

---

## Passo 2 — Backend na Koyeb

1. No [dashboard da Koyeb](https://app.koyeb.com), clique em **Create Service** → **GitHub** → autorize e escolha o repositório `betanalyzer`.
2. Em **Builder**, escolha **Dockerfile** e aponte o **Work directory / Root directory** para `backend` (é a pasta que contém o `Dockerfile` que já preparei).
3. Em **Instance**, escolha o plano **Free** (Koyeb chama de "Nano" ou similar no free tier — 0.1 vCPU / 512 MB RAM).
4. Em **Environment variables**, adicione (uma por linha, tipo `CHAVE=valor`):
   - `API_FOOTBALL_KEY` = sua chave real da API-Football
   - `DATABASE_URL` = `sqlite+aiosqlite:////data/betanalyzer.db`
   - `COLLECTOR_INTERVAL_MINUTES` = `5`
   - `LIVE_SCAN_INTERVAL_MINUTES` = `2`
   - `MAX_MONITORED_FIXTURES` = `8`
   - `TEAM_FORM_SAMPLE_SIZE` = `3`
   - `FRONTEND_ORIGIN` = (deixe em branco por enquanto — você volta aqui no Passo 4 com a URL da Vercel)
5. Em **Volumes**, crie um volume novo:
   - Nome: `betanalyzer-data`
   - Tamanho: 1 GB (bem mais que suficiente pro SQLite)
   - **Mount path**: `/data`

   Isso é o que garante que o `betanalyzer.db` sobreviva a redeploys — sem
   isso, cada novo deploy apagaria o banco.
6. Confirme e clique em **Deploy**.

Depois que o deploy terminar, a Koyeb te dá uma URL pública, algo como
`https://betanalyzer-seuuser.koyeb.app`. Teste abrindo
`https://betanalyzer-seuuser.koyeb.app/health` no navegador — deve responder
`{"status":"ok"}`. **Guarde essa URL**, você vai precisar dela no próximo passo.

> Nota sobre o plano free da Koyeb: ele roda com 0.1 vCPU, que é pouco. Se
> perceber os ciclos de coleta demorando muito ou a API travando sob carga,
> pode ser necessário subir pro menor plano pago da Koyeb (bem barato) ou
> considerar a VM da Oracle Cloud Free Tier, que tem bem mais CPU disponível.

---

## Passo 3 — Frontend na Vercel

1. No [dashboard da Vercel](https://vercel.com/new), clique em **Import Project** e escolha o mesmo repositório `betanalyzer`.
2. Em **Root Directory**, clique em "Edit" e selecione a pasta `frontend`.
3. A Vercel já detecta automaticamente que é um projeto Vite (build command `npm run build`, output `dist`) — não precisa mexer em nada aqui.
4. Em **Environment Variables**, adicione:
   - `VITE_API_BASE_URL` = a URL da Koyeb do Passo 2 (ex: `https://betanalyzer-seuuser.koyeb.app`, **sem** `/api` no final e **sem** barra `/` sobrando no final)
5. Clique em **Deploy**.

Ao final você recebe uma URL tipo `https://betanalyzer.vercel.app`. Abra ela —
nesse momento o site vai carregar, mas provavelmente vai dar erro ao buscar
dados, porque o backend ainda não sabe que pode aceitar requisições vindas
dessa URL (CORS). Isso é resolvido no próximo passo.

---

## Passo 4 — Liberar o CORS: volte na Koyeb

1. Volte nas **Environment variables** do serviço na Koyeb.
2. Edite `FRONTEND_ORIGIN` e coloque a URL da Vercel do Passo 3, por exemplo:
   ```
   FRONTEND_ORIGIN=https://betanalyzer.vercel.app
   ```
   (Se quiser liberar mais de uma URL — por exemplo um domínio próprio que
   adicionar depois — separe por vírgula, sem espaço: `url1,url2`.)
3. Salve — a Koyeb faz um redeploy automático com a nova variável.

Já preparei o backend para liberar automaticamente qualquer URL de **preview**
da Vercel também (as URLs tipo `https://betanalyzer-git-branch-x-seuuser.vercel.app`
que a Vercel cria a cada branch/PR), então você só precisa manter o
`FRONTEND_ORIGIN` atualizado com a URL de produção mesmo.

---

## Passo 5 — Testar tudo junto

1. Abra a URL da Vercel de novo (talvez precise dar um refresh forçado, Ctrl+F5).
2. O dashboard deve carregar e, dentro de alguns minutos (o coletor roda a
   cada 2-5 min), começar a mostrar partidas ao vivo normalmente.
3. Se aparecer erro de conexão no site:
   - Abra o DevTools (F12) → aba **Console** e veja se tem erro de CORS
     (mensagem mencionando "blocked by CORS policy") → confira se
     `FRONTEND_ORIGIN` na Koyeb está com a URL exata da Vercel (https, sem
     barra no final).
   - Veja também a aba **Network**: se as chamadas pra
     `.../api/matches/live` estão indo pro domínio certo (a URL da Koyeb) —
     se estiverem indo para a própria URL da Vercel, é sinal que
     `VITE_API_BASE_URL` não foi configurada antes do build (variáveis de
     ambiente do Vite só entram no código durante o `build`, então mudar a
     variável exige um **redeploy** na Vercel, não só salvar).
4. Nos logs do serviço na Koyeb (aba **Logs**), você deve ver as linhas de
   log do scheduler rodando a cada 2 e 5 minutos, tipo `Fixture ... recomendacao(oes) atualizada(s)`.

---

## Depois de publicado

- Todo `git push` na branch `main` faz a Vercel e a Koyeb re-deployarem
  automaticamente — não precisa repetir os passos acima depois.
- Fique de olho no uso da sua cota da API-Football
  (https://dashboard.api-football.com/profile?access) de vez em quando,
  principalmente nos primeiros dias após publicar, pra confirmar que o
  consumo real bate com o esperado.
- O volume de 1 GB na Koyeb aguenta o SQLite por muito, muito tempo (o banco
  cresce devagar); não precisa se preocupar com isso tão cedo.
