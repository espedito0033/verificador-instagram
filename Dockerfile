# Imagem oficial do Playwright ja vem com o Chromium e as dependencias
# do sistema necessarias - evita ter que instalar tudo na mao no deploy.
FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# O Render (e servicos parecidos) definem a porta pela variavel PORT
EXPOSE 5000

CMD ["python", "app.py"]
