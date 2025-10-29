# app.py — 🏗️Sistema de Rupturas de Argamassa Habisolute
from __future__ import annotations
from datetime import date
from statistics import mean, pstdev
import unicodedata, re, base64, secrets
from io import BytesIO

import streamlit as st
import pandas as pd
import altair as alt
import streamlit.components.v1 as components

# ===================== Dependência obrigatória (PDF) =====================
MISSING = []
try:
    from fpdf import FPDF
    _HAS_ROTATE = hasattr(FPDF, "rotate")
except Exception:
    FPDF = None
    _HAS_ROTATE = False
    MISSING.append("fpdf2>=2.7")

# ===================== Estado & Tema =====================
ACCENT = "#d75413"  # laranja Habisolute

# WIDESCREEN
st.set_page_config(page_title="Rupturas de Argamassa", page_icon="🏗️", layout="wide")

if "theme" not in st.session_state: st.session_state.theme = "Claro"  # começa no claro
if "obra" not in st.session_state: st.session_state.obra = ""
if "data_obra" not in st.session_state: st.session_state.data_obra = date.today()
if "area_padrao" not in st.session_state: st.session_state.area_padrao = 16.00
if "registros" not in st.session_state: st.session_state.registros = []
# NOVOS CAMPOS (lote)
if "data_moldagem" not in st.session_state: st.session_state.data_moldagem = date.today()
if "data_ruptura"  not in st.session_state: st.session_state.data_ruptura  = date.today()

# ===== Sidebar: seletor de tema
with st.sidebar:
    st.markdown(f"<h2 style='margin-top:0;color:{ACCENT}'>Preferências</h2>", unsafe_allow_html=True)
    st.session_state.theme = st.radio(
        "Tema", ["Escuro", "Claro"],
        horizontal=True,
        index=1 if st.session_state.theme == "Claro" else 0
    )

# ===================== CSS base — Windows 11 look =====================
IS_DARK = (st.session_state.theme == "Escuro")

SURFACE, CARD, BORDER, TEXT = (
    ("#0b0b0c", "rgba(26,27,30,0.72)", "rgba(255,255,255,0.12)", "#f5f6f8")
    if IS_DARK else
    ("#ffffff", "#ffffff", "rgba(17,17,17,0.12)", "#111318")
)
SIDEBAR_BG   = ("#1b1d22" if IS_DARK else "#f2f4f7")
SIDEBAR_TEXT = ("#e9ebef" if IS_DARK else "#2b2f36")
INPUT_BG     = ("#212327" if IS_DARK else "#ffffff")
INPUT_TEXT   = ("#eef0f3" if IS_DARK else "#111318")
INPUT_BDR    = ("rgba(255,255,255,0.22)" if IS_DARK else "rgba(0,0,0,0.20)")
PLACEHOLDER  = ("rgba(240,242,245,0.55)" if IS_DARK else "rgba(17,19,24,0.55)")

st.markdown(f"""
<style>
/* -------- Largura máxima do container (widescreen) -------- */
@media (min-width: 1400px) {{
  .block-container {{ max-width: 1600px !important; }}
}}

/* -------- Cores base -------- */
html, body, [class*="block-container"] {{
  background: {SURFACE} !important;
  color: {TEXT} !important;
  font-family: "Segoe UI Variable Text","Segoe UI",system-ui,-apple-system,Roboto,Arial,"Noto Sans",sans-serif !important;
  letter-spacing: .2px;
}}
[class*="block-container"] {{ padding-top: 1.4rem; }}

/* Sidebar */
div[data-testid="stSidebar"] {{
  background: {SIDEBAR_BG} !important;
  border-right: 1px solid rgba(0,0,0,.10) !important;
}}
div[data-testid="stSidebar"] * {{ color: {SIDEBAR_TEXT} !important; }}
div[data-testid="stSidebar"] [data-baseweb="radio"] label,
div[data-testid="stSidebar"] [data-baseweb="radio"] span {{ font-weight: 600; }}

/* Cards/Forms */
div[data-testid="stForm"],
.stDataFrame, .element-container:has(> div[data-testid="stDataFrame"]) {{
  background: {CARD};
  border: 1px solid {BORDER};
  border-radius: 16px;
  box-shadow: 0 12px 28px rgba(16,24,40,.10);
  padding: .9rem;
}}

/* Inputs */
input, textarea, select {{
  color: {INPUT_TEXT} !important;
  background: {INPUT_BG} !important;
  border: 1px solid {INPUT_BDR} !important;
  border-radius: 12px !important;
}}
::placeholder {{ color: {PLACEHOLDER} !important; }}

/* Título SEMPRE preto */
h1#app-title {{ color:#111111 !important; text-shadow:none !important; }}

/* Botões laranja com texto preto */
.stButton>button, .stDownloadButton>button,
div[data-testid="stForm"] .stButton>button {{
  background: {ACCENT} !important;
  color: #111 !important;
  border: none !important;
  border-radius: 12px !important;
  padding: .62rem 1.05rem !important;
  font-weight: 800 !important;
  letter-spacing: .2px;
  box-shadow: 0 8px 22px rgba(215,84,19,.25) !important;
  transition: transform .06s ease, filter .18s ease, box-shadow .18s ease;
}}
.stButton>button:hover, .stDownloadButton>button:hover {{ filter:brightness(1.03); transform:translateY(-1px); }}
.stButton>button:active, .stDownloadButton>button:active {{ transform:translateY(0); }}

/* Métricas: preto no claro e claro no escuro */
html:root:not(.dark) .stMetric label,
html:root:not(.dark) .stMetric div[data-testid="stMetricValue"]{{ color:#111111 !important; }}
html.dark .stMetric label,
html.dark .stMetric div[data-testid="stMetricValue"]{{ color:#f5f6f8 !important; }}

/* DataFrame contraste no claro */
html:root:not(.dark) [data-testid="stDataFrame"] thead th{{ color:#111318 !important; border-bottom:1px solid rgba(0,0,0,.12) !important; }}
html:root:not(.dark) [data-testid="stDataFrame"] tbody td{{ color:#111318 !important; background:#ffffff !important; border-bottom:1px solid rgba(0,0,0,.06) !important; }}
</style>
""", unsafe_allow_html=True)

# ===== Título
st.markdown(
    "<h1 id='app-title' style='margin:0'>🏗️Sistema de Rupturas de Argamassa Habisolute</h1>",
    unsafe_allow_html=True
)
st.caption("Entrada: **carga (kgf)**. Saídas: **kN/cm²** e **MPa**. PDF direto em 1 clique (somente fpdf2).")
# === HOTFIX FINAL (coloque no FIM do arquivo) ===
st.markdown("""
<style>
/* 0) Força precedência deste bloco */
:root { --_fix_20251029: 1; }

/* 1) MODO CLARO totalmente branco */
html:root:not(.dark) html,
html:root:not(.dark) body,
html:root:not(.dark) .stApp,
html:root:not(.dark) .stAppViewContainer,
html:root:not(.dark) .main,
html:root:not(.dark) section.main,
html:root:not(.dark) [class*="block-container"]{
  background: #ffffff !important;
  color: #111111 !important;
}

/* 2) Título e subtítulos sempre em preto no CLARO */
html:root:not(.dark) h1#app-title { color:#111111 !important; text-shadow:none !important; }
html:root:not(.dark) h2, 
html:root:not(.dark) h3,
html:root:not(.dark) .stMarkdown h2,
html:root:not(.dark) .stMarkdown h3,
html:root:not(.dark) label,
html:root:not(.dark) legend,
html:root:not(.dark) p {
  color:#111111 !important;
}

/* 3) Inputs no CLARO: branco + texto preto + borda visível */
html:root:not(.dark) input,
html:root:not(.dark) textarea,
html:root:not(.dark) select,
html:root:not(.dark) .stTextInput input,
html:root:not(.dark) .stDateInput input,
html:root:not(.dark) .stNumberInput input{
  background:#ffffff !important;
  color:#111111 !important;
  border:1px solid rgba(0,0,0,.22) !important;
}
html:root:not(.dark) ::placeholder { color: rgba(17,19,24,.55) !important; }

/* 4) Botões SEMPRE laranja com texto preto (inclui forms e desabilitados) */
html .stButton > button,
html .stDownloadButton > button,
html div[data-testid="stForm"] .stButton > button,
html .stButton > button[kind],
html button[kind="secondary"] {
  background: #d75413 !important;
  color:#111111 !important;
  border:none !important;
  border-radius:12px !important;
  padding:.62rem 1.05rem !important;
  font-weight:800 !important;
  box-shadow:0 8px 22px rgba(215,84,19,.25) !important;
}
html .stButton > button:disabled,
html div[data-testid="stForm"] .stButton > button:disabled {
  background: #ebb08f !important;   /* laranja claro pra parecer desabilitado */
  color:#222 !important;
  box-shadow:none !important;
  opacity:.85 !important;
}

/* 5) Cartões/Forms no CLARO com fundo branco */
html:root:not(.dark) div[data-testid="stForm"],
html:root:not(.dark) .stDataFrame,
html:root:not(.dark) .element-container:has(> div[data-testid="stDataFrame"]) {
  background:#ffffff !important;
  border:1px solid rgba(0,0,0,.12) !important;
  border-radius:16px !important;
  box-shadow:0 10px 28px rgba(16,24,40,.10) !important;
}

/* 6) Métricas em preto no CLARO */
html:root:not(.dark) .stMetric label,
html:root:not(.dark) .stMetric div[data-testid="stMetricValue"]{
  color:#111111 !important;
}

/* 7) Gráfico Altair legível no CLARO (eixos/labels/grade) */
html:root:not(.dark) .vega-embed * { color:#111318 !important; }
</style>
""", unsafe_allow_html=True)
st.markdown("""
<style>
/* Desce o título e dá respiro no topo do conteúdo */
[class*="block-container"]{ padding-top: 2.2rem !important; }
h1#app-title{ margin-top: .6rem !important; margin-bottom: .35rem !important; }
</style>
""", unsafe_allow_html=True)
st.markdown("""
<style>
/* Força laranja Habisolute nos botões do app inteiro */
:root{ --hab-accent:#d75413; --hab-text:#111; }

/* Botões padrão e de form */
.stButton > button,
.stDownloadButton > button,
div[data-testid="stForm"] .stButton > button,
button[kind],
button[kind="secondary"],
button[kind="primary"]{
  background: var(--hab-accent) !important;
  color: var(--hab-text) !important;
  border: none !important;
  border-radius: 12px !important;
  padding: .62rem 1.05rem !important;
  font-weight: 800 !important;
  letter-spacing: .2px;
  box-shadow: 0 8px 22px rgba(215,84,19,.25) !important;
  transition: transform .06s ease, filter .18s ease, box-shadow .18s ease;
}

/* Hover/Active */
.stButton > button:hover,
.stDownloadButton > button:hover,
div[data-testid="stForm"] .stButton > button:hover{ filter:brightness(1.03); transform:translateY(-1px); }
.stButton > button:active,
.stDownloadButton > button:active,
div[data-testid="stForm"] .stButton > button:active{ transform:translateY(0); }

/* Mesmo quando desabilitados, segue laranja (com leve “desativado”) */
.stButton > button:disabled,
div[data-testid="stForm"] .stButton > button:disabled{
  background: #f0a77f !important;  /* laranja mais claro */
  color: #222 !important;
  box-shadow: none !important;
  opacity: .85 !important;
}

/* Remove estilos escuros “por cima” que escureciam os botões */
html:root:not(.dark) .stButton > button,
html:root:not(.dark) .stDownloadButton > button,
html:root:not(.dark) div[data-testid="stForm"] .stButton > button{
  filter:none !important;
}
</style>
""", unsafe_allow_html=True)
st.markdown("""
<style>
/* FIX: texto preto em inputs desabilitados (ex.: "Idade de ruptura (dias)") */
html:root:not(.dark) input:disabled,
html:root:not(.dark) .stNumberInput input:disabled,
html:root:not(.dark) .stTextInput input:disabled{
  color:#111111 !important;
  -webkit-text-fill-color:#111111 !important; /* Safari/Chrome */
  opacity:1 !important; /* evita "esbranquiçado" de disabled */
  background:#ffffff !important;
  border-color: rgba(0,0,0,.22) !important;
}

/* No modo escuro, mantém legível */
html.dark input:disabled,
html.dark .stNumberInput input:disabled,
html.dark .stTextInput input:disabled{
  color:#f5f6f8 !important;
  -webkit-text-fill-color:#f5f6f8 !important;
  opacity:1 !important;
  background:#212327 !important;
  border-color: rgba(255,255,255,.22) !important;
}
</style>
""", unsafe_allow_html=True)

# ===================== Conversões & helpers =====================
KGF_CM2_TO_MPA    = 0.0980665
KGF_CM2_TO_KN_CM2 = 0.00980665

def tensoes_from_kgf(carga_kgf: float, area_cm2: float):
    if area_cm2 <= 0: return None, None, None
    s = carga_kgf / area_cm2
    return s, s*KGF_CM2_TO_KN_CM2, s*KGF_CM2_TO_MPA

def _dp(v):
    if not v: return None
    if len(v)==1: return 0.0
    return pstdev(v)

def _latin1_safe(text: str) -> str:
    try:
        text.encode("latin1"); return text
    except Exception:
        norm = unicodedata.normalize("NFKD", text)
        ascii_like = "".join(ch for ch in norm if not unicodedata.combining(ch))
        return ascii_like.encode("latin1", errors="ignore").decode("latin1", errors="ignore")

def _safe_filename(s: str) -> str:
    s = s.strip()
    s = re.sub(r"[^\w\-\s\.]", "", s, flags=re.UNICODE)
    s = re.sub(r"\s+", "_", s)
    return s[:80] if s else "relatorio"

def _as_bytes(pdf_obj) -> bytes:
    out = pdf_obj.output(dest="S")
    if isinstance(out, (bytes, bytearray)): return bytes(out)
    return out.encode("latin1", errors="ignore")

def _hex_to_rgb(hexstr: str):
    s = hexstr.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))

def _gen_report_id(dt: date) -> str:
    # Ex.: 20251023-A453DA
    return f"{dt.strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"

# ===== Normas (usadas no PDF e exibidas como rodapé do app)
NORMAS_TXT = (
    "Normas de referência (argamassa):\n"
    "• 📚ABNT NBR 13279 — Determinação da resistência à tração na flexão e à compressão.\n"
    "• 📚ABNT NBR 13276 — Determinação do índice de consistência.\n"
    "• 📚ABNT NBR 13277 — Retenção de água.\n"
    "• 📚ABNT NBR 13281 — Requisitos para argamassas de assentamento e revestimento."
)

# ===================== Conversor rápido =====================
with st.expander("🔁 Conversor rápido (kgf → kN/cm² / MPa)", expanded=False):
    c1,c2 = st.columns(2)
    kgf = c1.number_input("Carga (kgf)", min_value=0.0, value=0.0, step=0.1, format="%.3f")
    area_demo = c2.number_input("Área (cm²)", min_value=0.0001, value=st.session_state.area_padrao, step=0.01, format="%.2f")
    if kgf and area_demo:
        _, kn, mp = tensoes_from_kgf(kgf, area_demo)
        st.markdown(
            f"<div class='kpi'><div><b>kN/cm²</b><br>{kn:.5f}</div>"
            f"<div><b>MPa</b><br>{mp:.4f}</div></div>",
            unsafe_allow_html=True
        )

# ===================== Dados da obra (inclui datas novas) =====================
with st.form("obra_form"):
    st.subheader("✅Dados da obra")

    # linha 1
    a,b,c = st.columns([2,1,1])
    obra = a.text_input("Nome da obra", st.session_state.obra, placeholder="Ex.: Residencial Jardim Tropical")
    data_obra = b.date_input("Data", st.session_state.data_obra, format="DD/MM/YYYY")
    area_padrao = c.number_input("Área do CP (cm²)", min_value=0.0001, value=float(st.session_state.area_padrao), step=0.01, format="%.2f")

    # linha 2 — NOVOS CAMPOS
    d,e,f = st.columns([1,1,1])
    data_moldagem = d.date_input("Data de moldagem", st.session_state.data_moldagem, format="DD/MM/YYYY")
    data_ruptura  = e.date_input("Data de ruptura",  st.session_state.data_ruptura,  format="DD/MM/YYYY")
    idade_dias = max(0, (data_ruptura - data_moldagem).days)
    f.number_input("Idade de ruptura (dias)", value=idade_dias, disabled=True)

    col = st.columns([1,1,2])
    apply_clicked  = col[0].form_submit_button("Aplicar")
    recalc_clicked = col[1].form_submit_button("Recalcular lote com nova área", disabled=(not st.session_state.registros))

    if apply_clicked:
        st.session_state.obra = obra.strip()
        st.session_state.data_obra = data_obra
        st.session_state.area_padrao = float(area_padrao)
        st.session_state.data_moldagem = data_moldagem
        st.session_state.data_ruptura  = data_ruptura
        st.success("Dados aplicados.")

    if recalc_clicked and st.session_state.registros:
        nova_area = float(area_padrao)
        for r in st.session_state.registros:
            r["area_cm2"] = nova_area
            s_kgfcm2, s_kncm2, s_mpa = tensoes_from_kgf(r["carga_kgf"], nova_area)
            r["kgf_cm2"] = float(s_kgfcm2); r["kn_cm2"] = float(s_kncm2); r["mpa"] = float(s_mpa)
        st.session_state.area_padrao = nova_area
        st.success("Todos os CPs recalculados com a nova área.")

# ===================== Lançar CP =====================
st.info(f"CPs no lote: **{len(st.session_state.registros)}/12**")
with st.form("cp_form", clear_on_submit=True):
    st.subheader("✅Lançar ruptura (apenas kgf)")
    codigo = st.text_input("Código do CP", max_chars=32, placeholder="Ex.: A039.258 / H682 / 037.421")
    carga  = st.number_input("Carga de ruptura (kgf)", min_value=0.0, step=0.1, format="%.3f")
    if carga and st.session_state.area_padrao:
        _, knp, mpp = tensoes_from_kgf(carga, st.session_state.area_padrao)
        st.caption(f"→ Conversões (área {st.session_state.area_padrao:.2f} cm²): **{knp:.5f} kN/cm²** • **{mpp:.4f} MPa**")
    ok = st.form_submit_button("Adicionar CP", disabled=(len(st.session_state.registros)>=12))
    if ok:
        if not st.session_state.obra: st.error("Preencha os dados da obra.")
        elif not codigo.strip():      st.error("Informe o código do CP.")
        elif carga <= 0:              st.error("Informe uma carga > 0.")
        else:
            s_kgfcm2, s_kncm2, s_mpa = tensoes_from_kgf(carga, st.session_state.area_padrao)
            st.session_state.registros.append({
                "codigo_cp": codigo.strip(),
                "carga_kgf": float(carga),
                "area_cm2": float(st.session_state.area_padrao),
                "kgf_cm2": float(s_kgfcm2),
                "kn_cm2":  float(s_kncm2),
                "mpa":     float(s_mpa),
                # novos campos (CSV)
                "data_moldagem": st.session_state.data_moldagem.isoformat(),
                "data_ruptura":  st.session_state.data_ruptura.isoformat(),
                "idade_dias":    max(0, (st.session_state.data_ruptura - st.session_state.data_moldagem).days),
            })
            st.success("CP adicionado.")
            # ===================== Tabela + Gráfico (tela) =====================
if st.session_state.registros:
    # 1) DataFrame bruto
    df = pd.DataFrame(st.session_state.registros).copy()

    # 2) Normalização para retrocompatibilidade
    lote_mold = st.session_state.data_moldagem
    lote_rupt = st.session_state.data_ruptura
    lote_idade = max(0, (lote_rupt - lote_mold).days)

    if "data_moldagem" not in df.columns:
        df["data_moldagem"] = lote_mold.isoformat()
    df["data_moldagem"] = df["data_moldagem"].fillna(lote_mold.isoformat())

    if "data_ruptura" not in df.columns:
        df["data_ruptura"] = lote_rupt.isoformat()
    df["data_ruptura"] = df["data_ruptura"].fillna(lote_rupt.isoformat())

    if "idade_dias" not in df.columns:
        df["idade_dias"] = lote_idade
    df["idade_dias"] = df["idade_dias"].fillna(lote_idade).astype(int)

    # 2.1) Garante tensões
    if "kgf_cm2" not in df.columns or "kn_cm2" not in df.columns or "mpa" not in df.columns:
        df["kgf_cm2"], df["kn_cm2"], df["mpa"] = None, None, None
    if df[["kgf_cm2","kn_cm2","mpa"]].isnull().any().any():
        vals = []
        for r in df.itertuples(index=False):
            s_kgfcm2, s_kncm2, s_mpa = tensoes_from_kgf(float(r.carga_kgf), float(r.area_cm2))
            vals.append((s_kgfcm2, s_kncm2, s_mpa))
        df["kgf_cm2"] = [v[0] for v in vals]
        df["kn_cm2"]  = [v[1] for v in vals]
        df["mpa"]     = [v[2] for v in vals]

    # 3) Editor
    st.subheader("📋Lote atual (editável)")
    edited = st.data_editor(
        df[[
            "codigo_cp","carga_kgf","area_cm2","kn_cm2","mpa",
            "data_moldagem","data_ruptura","idade_dias"
        ]],
        use_container_width=True, num_rows="fixed",
        column_config={
            "codigo_cp": st.column_config.TextColumn("Código CP"),
            "carga_kgf": st.column_config.NumberColumn("Carga (kgf)", step=0.1, format="%.3f"),
            "area_cm2":  st.column_config.NumberColumn("Área (cm²)", disabled=True, format="%.2f"),
            "kn_cm2":    st.column_config.NumberColumn("kN/cm²", disabled=True, format="%.5f"),
            "mpa":       st.column_config.NumberColumn("MPa", disabled=True, format="%.4f"),
            "data_moldagem": st.column_config.TextColumn("Data moldagem", disabled=True),
            "data_ruptura":  st.column_config.TextColumn("Data ruptura", disabled=True),
            "idade_dias":    st.column_config.NumberColumn("Idade (dias)", disabled=True),
        }
    )

    # 4) Persistência após edição
    if not edited.equals(df[edited.columns]):
        new_regs = []
        for row in edited.itertuples(index=False):
            s_kgfcm2, s_kn_cm2, s_mpa = tensoes_from_kgf(float(row.carga_kgf), float(row.area_cm2))
            new_regs.append({
                "codigo_cp": str(row.codigo_cp),
                "carga_kgf": float(row.carga_kgf),
                "area_cm2":  float(row.area_cm2),
                "kgf_cm2":   float(s_kgfcm2),
                "kn_cm2":    float(s_kn_cm2),
                "mpa":       float(s_mpa),
                "data_moldagem": str(row.data_moldagem),
                "data_ruptura":  str(row.data_ruptura),
                "idade_dias":    int(row.idade_dias),
            })
        st.session_state.registros = new_regs
        df = pd.DataFrame(st.session_state.registros)

    # 5) Métricas
    a,b,c = st.columns(3)
    with a: st.metric("Média (kN/cm²)", f"{mean(df['kn_cm2']):.4f}")
    with b: st.metric("Média (MPa)",    f"{mean(df['mpa']):.3f}")
    with c:
        dp = _dp(df["mpa"].tolist()); st.metric("DP (MPa)", f"{(dp if dp is not None else 0.0):.3f}")


    # 6) Gráfico — pontos espaçados mesmo quando o Código CP se repete
st.subheader("📈 Gráfico de ruptura (MPa por CP)")

# ------- salvaguardas de tema/cor -------
theme_name = st.session_state.get("theme", "Escuro")
ACCENT = st.session_state.get("accent_color", "#f97316")  # laranja Habisolute (fallback)

# ------- dataframe do gráfico -------
chart_df = (
    pd.DataFrame({
        "Código CP": df["codigo_cp"].astype(str).values,
        "MPa":       pd.to_numeric(df["mpa"], errors="coerce").values
    })
    .dropna(subset=["MPa"])
    .reset_index(drop=False)  # cria coluna 'index' para rowid
    .rename(columns={"index": "rowid"})
)

# Cores/estilo por tema (claro/escuro)
bg         = "#0f1115" if theme_name == "Escuro" else "#ffffff"
axis_color = "#e8eaed" if theme_name == "Escuro" else "#111318"
grid_color = "rgba(255,255,255,0.22)" if theme_name == "Escuro" else "#e5e7eb"

y_max = float(chart_df["MPa"].max() * 1.15) if len(chart_df) else 1.0

# ------- gráfico com deslocamento (xOffset) por duplicidade -------
points = (
    alt.Chart(chart_df, background=bg)
      # dup_index = 1..N para cada "Código CP"
      .transform_window(dup_index='rank()', groupby=['Código CP'])
      # total = quantidade de CPs por código
      .transform_joinaggregate(total='count()', groupby=['Código CP'])
      # offset centralizado: espaçamento de 10 px entre pontos do mesmo código
      .transform_calculate(offset='(datum.dup_index - (datum.total + 1)/2) * 10')
      .mark_point(size=110, filled=True, color=ACCENT, opacity=0.95)
      .encode(
          x=alt.X('Código CP:N', title='Código do CP', sort=None,
                  axis=alt.Axis(labelAngle=0),
          xOffset='offset:Q',
          y=alt.Y('MPa:Q', scale=alt.Scale(domain=[0, y_max]), title='MPa'),
          tooltip=[alt.Tooltip('Código CP:N', title='Código CP'),
                   alt.Tooltip('MPa:Q', format='.3f')]
      )
      .properties(
          height=360,
          padding={"left": 10, "right": 10, "top": 10, "bottom": 10},
          title='Gráfico de ruptura (MPa por CP)'
      )
      .configure_axis(
          labelColor=axis_color, titleColor=axis_color,
          gridColor=grid_color, domainColor=axis_color
      )
      .configure_title(color=axis_color)
      .configure_view(stroke='transparent')
)

st.altair_chart(points, use_container_width=True)
st.divider()
else:
    st.info("Nenhum CP lançado ainda. Adicione registros para visualizar tabela e gráfico.")

# ===================== PDF (fpdf2 desenhando o gráfico) =====================
def draw_scatter_on_pdf(pdf: "FPDF", df: pd.DataFrame, x: float, y: float, w: float, h: float, accent: str | None = None) -> None:
    accent_hex = (accent or ACCENT)
    pdf.set_draw_color(220, 220, 220); pdf.rect(x, y, w, h)

    codes = df["codigo_cp"].astype(str).tolist()
    ys = df["mpa"].astype(float).tolist()
    if not ys: return

    y_max = max(ys) * 1.15; y_min = 0.0

    pdf.set_font("Arial", size=8); ticks = 5
    for k in range(ticks + 1):
        yy = y + h - (h * k / ticks); val = y_min + (y_max - y_min) * k / ticks
        pdf.line(x, yy, x + w, yy); pdf.text(x - 7.5, yy + 2.2, f"{val:.1f}")

    r, g, b = _hex_to_rgb(accent_hex); pdf.set_fill_color(r, g, b)
    LABEL_GAP = 18
    n = len(ys)
    for i, val in enumerate(ys):
        px = x + (w * (i / max(1, n - 1)))
        py = y + h - (h * (val - y_min) / max(1e-9, (y_max - y_min)))
        pdf.ellipse(px - 1.8, py - 1.8, 3.6, 3.6, style="F")

        label = _latin1_safe(codes[i][:14]); tw = pdf.get_string_width(label)
        if _HAS_ROTATE:
            pivot_x = px; pivot_y = y + h + LABEL_GAP + (tw / 2.0)
            pdf.rotate(90, pivot_x, pivot_y); pdf.text(pivot_x, pivot_y, label); pdf.rotate(0)
        else:
            pdf.text(px - (tw / 2.0), y + h + (LABEL_GAP - 4), label)

    pdf.set_font("Arial", "B", 11); pdf.text(x, y - 1, "Gráfico de ruptura (MPa por CP)")
    pdf.set_font("Arial", size=9); pdf.text(x + w / 2 - 12, y + h + 26, "Código do CP")

def build_pdf(obra: str, data_obra: date, area_cm2: float, df: pd.DataFrame) -> bytes:
    pdf = FPDF("P", "mm", "A4")
    left, top, right = 20, 22, 20
    pdf.set_margins(left, top, right); pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    pdf.set_font("Arial", "B", 15)
    pdf.cell(0, 8, _latin1_safe("🏗️Rupturas de Argamassa  Lote"), ln=1, align="C")
    pdf.set_font("Arial", size=11)
    info = f"Obra: {obra}   |   Data: {data_obra.strftime('%d/%m/%Y')}   |   Área do CP: {area_cm2:.2f} cm²"
    pdf.cell(0, 6, _latin1_safe(info), ln=1, align="C")

    # Linha extra com Moldagem/Ruptura/Idade
    mold = st.session_state.data_moldagem.strftime('%d/%m/%Y')
    rupt = st.session_state.data_ruptura.strftime('%d/%m/%Y')
    idade = max(0, (st.session_state.data_ruptura - st.session_state.data_moldagem).days)
    pdf.cell(0, 6, _latin1_safe(f"Moldagem: {mold}   |   Ruptura: {rupt}   |   Idade: {idade} dias"), ln=1, align="C")

    pdf.ln(6)

    hdr = ["#", "Código CP", "Carga (kgf)", "Área (cm²)", "kN/cm²", "MPa"]
    wid = [10, 60, 30, 24, 28, 24]
    pdf.set_font("Arial", "B", 10)
    for h, w in zip(hdr, wid): pdf.cell(w, 7, _latin1_safe(h), 1, 0, "C")
    pdf.ln(); pdf.set_font("Arial", size=10)
    for i, row in enumerate(df.itertuples(index=False), 1):
        cells=[str(i), _latin1_safe(row.codigo_cp), f"{row.carga_kgf:.3f}", f"{row.area_cm2:.2f}", f"{row.kn_cm2:.4f}", f"{row.mpa:.3f}"]
        for c,w in zip(cells,wid): pdf.cell(w,6,c,1,0,"C")
        pdf.ln()

    pdf.ln(12); gy = pdf.get_y() + 6; gx = left + 2; gw = 180 - (left - 15); gh = 78
    draw_scatter_on_pdf(pdf, df, x=gx, y=gy, w=gw, h=gh, accent=ACCENT)

    # ID e Normas
    pdf.set_y(gy + gh + 34)
    pdf.set_font("Arial", "I", 9)
    report_id = _gen_report_id(data_obra)
    pdf.cell(0, 6, _latin1_safe(f"ID do relatório: {report_id}"), ln=1, align="L")

    pdf.ln(2)
    pdf.set_font("Arial", size=8)
    pdf.multi_cell(0, 4, _latin1_safe(NORMAS_TXT))

    prev_apb = pdf.auto_page_break
    pdf.set_auto_page_break(auto=False)
    pdf.set_y(-15)
    pdf.set_font("Arial", "I", 9)
    pdf.cell(0, 6, _latin1_safe("Sistema desenvolvido pela Habisolute Engenharia e Controle Tecnológico"), align="C")
    pdf.set_auto_page_break(auto=prev_apb, margin=18)

    return _as_bytes(pdf)

# ===================== Ações (botões + PDF/Imprimir) =====================
b1, b2, b3 = st.columns([1,1,1])

with b1:
    st.button("Limpar lote", disabled=(not st.session_state.registros),
              on_click=lambda: st.session_state.update(registros=[]))

with b2:
    if st.session_state.registros:
        st.download_button(
            "Baixar CSV",
            data=pd.DataFrame(st.session_state.registros).to_csv(index=False).encode("utf-8"),
            file_name="rupturas_lote.csv", mime="text/csv"
        )

with b3:
    if not st.session_state.registros:
        st.download_button("📄 Exportar para PDF", data=b"", file_name="vazio.pdf", disabled=True)
    elif MISSING:
        st.download_button("📄 Exportar para PDF", data=b"", file_name="rupturas.pdf", disabled=True)
        st.error("Para PDF direto, instale: " + ", ".join(MISSING))
    else:
        df_pdf = pd.DataFrame(st.session_state.registros)
        pdf_bytes = build_pdf(st.session_state.obra, st.session_state.data_obra,
                              st.session_state.area_padrao, df_pdf)
        report_id = _gen_report_id(st.session_state.data_obra)
        data_str = st.session_state.data_obra.strftime("%Y%m%d")
        safe_obra = _safe_filename(st.session_state.obra)
        fname = f"Lote_Rupturas_{safe_obra}_{data_str}_{report_id}.pdf" if safe_obra else f"Lote_Rupturas_{data_str}_{report_id}.pdf"

        # Download
        st.download_button("📄 Exportar para PDF", data=BytesIO(pdf_bytes), file_name=fname, mime="application/pdf")

        # Imprimir em nova aba
        b64 = base64.b64encode(pdf_bytes).decode("utf-8")
        components.html(f"""
        <div>
          <button id="printPdfBtn"
                  style="margin-top:8px;padding:.55rem .9rem;border-radius:12px;
                         background:{ACCENT};color:#111;font-weight:800;border:none;cursor:pointer;">
            🖨️ Imprimir (abrir PDF)
          </button>
        </div>
        <script>
        (function(){{
          const b64 = "{b64}";
          function b64ToUint8Array(b64str){{
            const byteChars = atob(b64str);
            const out = new Uint8Array(byteChars.length);
            for (let i=0;i<byteChars.length;i++) out[i] = byteChars.charCodeAt(i);
            return out;
          }}
          const bytes = b64ToUint8Array(b64);
          const blob  = new Blob([bytes], {{type: "application/pdf"}});
          document.getElementById("printPdfBtn").addEventListener("click", function(){{
            const url = URL.createObjectURL(blob);
            const win = window.open(url, "_blank");
            if (win) {{ win.focus(); }}
          }});
        }})();
        </script>
        """, height=60)

# ======= Diagnóstico (acima das normas)
st.caption(
    ("PDF direto ativo ✅" if not MISSING else "PDF direto inativo ❌") +
    (" • Dependência faltando: " + ", ".join(MISSING) if MISSING else "") +
    " • Conversões: [kgf/cm²] → kN/cm² (×0,00980665) e MPa (×0,0980665)."
)

# ===================== Rodapé do APP (normas + assinatura)
st.markdown("---")
st.markdown(
    "**Normas de referência (argamassa):**  \n"
    "• 📚ABNT NBR 13279 — Determinação da resistência à tração na flexão e à compressão.  \n"
    "• 📚ABNT NBR 13276 — Determinação do índice de consistência.  \n"
    "• 📚ABNT NBR 13277 — Retenção de água.  \n"
    "• 📚ABNT NBR 13281 — Requisitos para argamassas de assentamento e revestimento."
)
st.markdown(
    "<div style='text-align:center;opacity:.9;margin-top:.5rem'><em>"
    "Sistema desenvolvido pela Habisolute Engenharia e Controle Tecnológico"
    "</em></div>",
    unsafe_allow_html=True
)
