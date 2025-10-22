# Rupturas de Argamassa

App Streamlit para lançar rupturas de argamassa por obra (até 12 CPs por lote), com conversões automáticas:
- kgf/cm² → kN/cm²
- kgf/cm² → MPa
- Entrada alternativa: carga (kgf) + área (cm²)

Gera PDF do lote (tabela + estatística de média e DP) e CSV.

## Como rodar local

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
