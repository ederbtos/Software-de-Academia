# Script de inicialização: cria o .env a partir do .env.example se não existir
import os
import shutil

if not os.path.exists(".env"):
    shutil.copy(".env.example", ".env")
    print("Arquivo .env criado. Configure as variáveis antes de iniciar.")
else:
    print(".env já existe.")
