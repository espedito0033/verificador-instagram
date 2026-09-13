"""
Verificador de Contas Instagram - App Web Local (com navegador real)
----------------------------------------------------------------------
Um servidor local (Flask) + uma pagina HTML.
Por baixo dos panos, usa um Chrome de verdade rodando escondido
(Playwright) pra abrir cada perfil exatamente como um navegador faria
- isso evita a pagina generica de "nao disponivel" que o Instagram
mostra pra requisicoes que nao parecem vir de um navegador real.

INSTALAR (uma vez so):
    pip install flask requests playwright
    playwright install chromium

RODAR:
    python app.py

Depois é so deixar essa janela aberta e usar a pagina que abriu
no navegador. A primeira verificacao demora um pouco mais (o Chrome
escondido precisa iniciar).
"""

import base64
import os
import re
import threading
import time
import webbrowser

import requests
from flask import Flask, request, jsonify, render_template_string
from playwright.sync_api import sync_playwright

app = Flask(__name__)

BASE_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

TEXTOS_INDISPONIVEL = [
    "Esta página não está disponível",
    "Esta pagina nao esta disponivel",
    "Sorry, this page isn't available",
    "The link you followed may be broken",
]

# Navegador escondido (Chromium) iniciado uma unica vez e reaproveitado
# entre verificacoes. Um Lock garante que so uma verificacao usa o
# navegador por vez (Playwright sync nao e seguro pra varias threads
# usando a mesma pagina ao mesmo tempo).
_playwright = None
_browser = None
_context = None
_lock = threading.Lock()


def _iniciar_navegador():
    global _playwright, _browser, _context
    if _browser is not None:
        return
    _playwright = sync_playwright().start()
    _browser = _playwright.chromium.launch(headless=True)
    _context = _browser.new_context(
        user_agent=BASE_UA,
        locale="pt-BR",
        viewport={"width": 1280, "height": 800},
    )


def verificar_conta(username: str) -> dict:
    username = username.strip().lstrip("@")
    if not username:
        return None

    url = f"https://www.instagram.com/{username}/"

    with _lock:
        _iniciar_navegador()
        page = _context.new_page()
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=20000)
            # da um tempinho pra pagina assentar (meta tags, redirecionamentos)
            page.wait_for_timeout(1500)

            status_code = resp.status if resp else None
            if status_code == 404:
                return {"username": username, "status": "NAO_ENCONTRADA"}

            html = page.content()

            if any(t.lower() in html.lower() for t in TEXTOS_INDISPONIVEL):
                return {"username": username, "status": "NAO_ENCONTRADA"}

            def _meta(prop_or_name, valor):
                loc = f'meta[{prop_or_name}="{valor}"]'
                try:
                    return page.get_attribute(loc, "content", timeout=3000)
                except Exception:
                    return None

            foto_url = _meta("property", "og:image")
            titulo = _meta("property", "og:title") or ""
            descricao = _meta("property", "og:description") or _meta("name", "description") or ""

            nome = titulo.split(" (@")[0].strip() if " (@" in titulo else titulo

            m_seguidores = re.search(r"([\d.,]+)\s*(seguidores|Followers)", descricao, re.IGNORECASE)
            seguidores = m_seguidores.group(1) if m_seguidores else "?"

            if not foto_url and not titulo:
                return {"username": username, "status": "NAO_ENCONTRADA"}

            privada = ("This Account is Private" in html) or ("Esta conta é privada" in html) \
                or ("conta é privada" in html.lower())
            status = "PRIVADA" if privada else "ATIVA"

            foto_base64 = None
            if foto_url:
                try:
                    img = requests.get(foto_url, headers={"User-Agent": BASE_UA}, timeout=10)
                    if img.status_code == 200:
                        foto_base64 = "data:image/jpeg;base64," + base64.b64encode(img.content).decode()
                except requests.RequestException:
                    pass

            return {
                "username": username,
                "status": status,
                "nome": nome,
                "seguidores": seguidores,
                "foto": foto_base64,
            }
        except Exception as e:
            return {"username": username, "status": "ERRO", "detalhe": str(e)[:200]}
        finally:
            page.close()


@app.route("/")
def index():
    return render_template_string(PAGINA_HTML)


@app.route("/api/verificar", methods=["POST"])
def api_verificar():
    dados = request.get_json(force=True)
    usernames = [u for u in dados.get("usernames", []) if u.strip()]

    resultados = []
    for username in usernames:
        r = verificar_conta(username)
        if r:
            resultados.append(r)
        time.sleep(1.0)

    return jsonify(resultados)


PAGINA_HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<title>Verificador de Contas Instagram</title>
<style>
  * { box-sizing: border-box; }
  body {
    font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
    background: #fafafa;
    margin: 0;
    padding: 24px;
    color: #262626;
  }
  h1 { font-size: 22px; margin-bottom: 4px; }
  p.sub { color: #737373; margin-top: 0; margin-bottom: 20px; }
  .painel {
    background: #fff;
    border: 1px solid #dbdbdb;
    border-radius: 12px;
    padding: 20px;
    max-width: 900px;
  }
  textarea {
    width: 100%;
    min-height: 100px;
    border: 1px solid #dbdbdb;
    border-radius: 8px;
    padding: 10px;
    font-size: 14px;
    resize: vertical;
  }
  button {
    margin-top: 12px;
    background: #0095f6;
    color: #fff;
    border: none;
    padding: 10px 22px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
  }
  button:disabled { background: #7fc4f6; cursor: default; }
  #status-carregando { margin-top: 10px; color: #737373; font-size: 13px; }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 14px;
    margin-top: 22px;
    max-width: 900px;
  }
  .card {
    background: #fff;
    border: 1px solid #dbdbdb;
    border-radius: 12px;
    padding: 14px;
    text-align: center;
  }
  .card img {
    width: 72px; height: 72px;
    border-radius: 50%;
    object-fit: cover;
    margin-bottom: 8px;
    background: #efefef;
  }
  .card .semfoto {
    width: 72px; height: 72px;
    border-radius: 50%;
    background: #efefef;
    margin: 0 auto 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 11px; color: #a8a8a8;
  }
  .card .user { font-weight: 600; font-size: 14px; }
  .card .nome { color: #737373; font-size: 12px; margin: 2px 0 8px; }
  .badge {
    display: inline-block;
    font-size: 11px;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 999px;
  }
  .ATIVA { background: #dcf7e3; color: #1f8b3f; }
  .PRIVADA { background: #fff3cd; color: #8a6d00; }
  .NAO_ENCONTRADA { background: #fde2e1; color: #c62828; }
  .RATE_LIMIT, .ERRO { background: #eee; color: #555; }
  .seguidores { font-size: 12px; color: #737373; margin-top: 6px; }
</style>
</head>
<body>

<h1>Verificador de Contas Instagram</h1>
<p class="sub">Sem login. Cola os usernames abaixo (um por linha) e clica em verificar.</p>

<div class="painel">
  <textarea id="usernames" placeholder="luciana509454&#10;outroperfil&#10;maisumperfil"></textarea>
  <br>
  <button id="btnVerificar" onclick="verificar()">Verificar contas</button>
  <div id="status-carregando"></div>
</div>

<div class="grid" id="resultados"></div>

<script>
async function verificar() {
  const texto = document.getElementById('usernames').value;
  const usernames = texto.split('\\n').map(u => u.trim()).filter(u => u.length > 0);
  if (usernames.length === 0) return;

  const btn = document.getElementById('btnVerificar');
  const statusDiv = document.getElementById('status-carregando');
  const grid = document.getElementById('resultados');
  grid.innerHTML = '';
  btn.disabled = true;
  statusDiv.textContent = 'Verificando ' + usernames.length + ' conta(s)... a primeira demora um pouco mais (abrindo o navegador escondido).';

  try {
    const resp = await fetch('/api/verificar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ usernames })
    });
    const resultados = await resp.json();

    resultados.forEach(r => {
      const card = document.createElement('div');
      card.className = 'card';

      const fotoHtml = r.foto
        ? `<img src="${r.foto}">`
        : `<div class="semfoto">sem foto</div>`;

      const statusTexto = {
        ATIVA: 'Ativa',
        PRIVADA: 'Privada',
        NAO_ENCONTRADA: 'Não encontrada',
        RATE_LIMIT: 'Bloqueado (espera)',
        ERRO: 'Erro'
      }[r.status] || r.status;

      card.innerHTML = `
        ${fotoHtml}
        <div class="user">@${r.username}</div>
        <div class="nome">${r.nome || ''}</div>
        <span class="badge ${r.status}">${statusTexto}</span>
        ${r.seguidores !== undefined ? `<div class="seguidores">${r.seguidores} seguidores</div>` : ''}
        ${r.detalhe ? `<div class="seguidores" style="color:#c62828;word-break:break-all;">${r.detalhe}</div>` : ''}
      `;
      grid.appendChild(card);
    });

    statusDiv.textContent = 'Concluído: ' + resultados.length + ' conta(s) verificada(s).';
  } catch (e) {
    statusDiv.textContent = 'Erro ao verificar: ' + e;
  } finally {
    btn.disabled = false;
  }
}
</script>

</body>
</html>
"""


def abrir_navegador(porta):
    time.sleep(1.2)
    webbrowser.open(f"http://127.0.0.1:{porta}")


if __name__ == "__main__":
    # Quando hospedado (Render, Railway, etc.) a plataforma define a porta
    # pela variavel de ambiente PORT. Localmente, roda na 5000 e abre o
    # navegador sozinho.
    porta = int(os.environ.get("PORT", 5000))
    rodando_local = "PORT" not in os.environ

    if rodando_local:
        threading.Thread(target=abrir_navegador, args=(porta,)).start()

    app.run(host="0.0.0.0", port=porta, debug=False)
