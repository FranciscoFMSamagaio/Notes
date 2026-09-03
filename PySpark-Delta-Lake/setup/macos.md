# Setup macOS para PySpark

PySpark precisa de Python e Java. Neste projeto o Python ja existe em `.venv`, mas o Spark local falhou porque nao encontrou Java.

## 1. Instalar Java 17

Opcao com Homebrew:

```bash
brew install openjdk@17
```

Depois adiciona o Java ao teu shell:

```bash
echo 'export JAVA_HOME="/opt/homebrew/opt/openjdk@17"' >> ~/.zshrc
echo 'export PATH="$JAVA_HOME/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Em Macs Intel, usa este caminho:

```bash
echo 'export JAVA_HOME="/usr/local/opt/openjdk@17"' >> ~/.zshrc
echo 'export PATH="$JAVA_HOME/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Este projeto tambem tem um wrapper que tenta encontrar o Java do Homebrew automaticamente:

```bash
scripts/run_spark.sh lessons/01_dataframe_basics.py
```

## 2. Verificar ambiente

Na pasta do projeto:

```bash
source .venv/bin/activate
python setup/check_environment.py
```

Deves ver:

- Python instalado.
- Java 17 encontrado.
- PySpark instalado.

## 3. Correr a primeira aula

```bash
scripts/run_spark.sh lessons/01_dataframe_basics.py
```

## Nota sobre Databricks

No Databricks nao tens de instalar Java manualmente. A plataforma ja entrega clusters com Spark configurado. Aprender localmente ajuda-te a perceber a API; trabalhar no Databricks ajuda-te a operar em ambiente real.
