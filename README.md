# Verificador de Contas Instagram

App web local que verifica se contas do Instagram estão **ativas**,
**privadas** ou **não encontradas** (banidas/deletadas), sem precisar
fazer login — e mostra a foto de perfil na tela.

Por baixo dos panos, usa um Chromium headless (via Playwright) pra
abrir cada perfil exatamente como um navegador real faria, evitando
a página genérica de bloqueio que o Instagram mostra pra requisições
que não parecem vir de um navegador de verdade.

## Instalação

```bash
pip install -r requirements.txt
playwright install chromium
```

## Como rodar

```bash
python app.py
```

O navegador abre sozinho em `http://127.0.0.1:5000`. Cola os
usernames (um por linha) na caixa de texto e clica em **Verificar
contas**.

## O que ele mostra

Pra cada conta:
- Foto de perfil
- Nome
- Status: **Ativa** / **Privada** / **Não encontrada**
- Número de seguidores

## Observações

- A primeira verificação demora um pouco mais (o Chromium escondido
  precisa iniciar).
- As verificações são feitas uma de cada vez (não em paralelo) pra
  reduzir a chance de bloqueio.
