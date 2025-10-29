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
ACCENT = "#d75413"
st.set_page_config(page_title="Rupturas de Argamassa", page_icon="🏗️", layout="centered")

if "theme" not in st.session_state: st.session_state.theme = "Escuro"
if "obra" not in st.session_state: st.session_state.obra = ""
if "data_obra" not in st.session_state: st.session_state.data_obra = date.today()
if "area_padrao" not in st.session_state: st.session_state.area_padrao = 16.00
if "registros" not in st.session_state: st.session_state.registros = []
# NOVOS CAMPOS (lote)
if "data_moldagem" not in st.session_state: st.session_state.data_moldagem = date.today()
if "data_ruptura"  not in st.session_state: st.session_state.data_ruptura  = date.today()

# ===== Sidebar
with st.sidebar:
    st.markdown(f"<h2 style='margin-top:0;color:{ACCENT}'>Preferências</h2>", unsafe_allow_html=True)
    st.session_state.theme = st.radio(
        "Tema", ["Escuro", "Claro"],
        horizontal=True,
        index=0 if st.session_state.theme == "Escuro" else 1
    )

# ===================== CSS global (um único bloco) =====================
IS_DARK = (st.session_state.theme == "Escuro")

SURFACE, CARD, BORDER, TEXT = (
    ("#0a0a0a", "#111213", "rgba(255,255,255,0.12)", "#f5f5f5")
    if IS_DARK else
    ("#ffffff", "#fafafa", "rgba(0,0,0,0.16)", "#111111")
)
SIDEBAR_TEXT = "#FFC08E" if IS_DARK else ACCENT
INPUT_BG   = "#18191b" if IS_DARK else "#ffffff"
INPUT_TEXT = "#f5f5f5" if IS_DARK else "#111111"
INPUT_BDR  = "rgba(255,255,255,0.35)" if IS_DARK else "#CDD3DA"
PLACEHOLDER = "rgba(255,255,255,0.6)" if IS_DARK else "rgba(17,17,17,0.55)"

st.markdown(f"""
<style>
:root {{
  --accent:{ACCENT};
  --surface:{SURFACE};
  --card:{CARD};
  --border:{BORDER};
  --text:{TEXT};
  --sidebar-text:{SIDEBAR_TEXT};
  --input-bg:{INPUT_BG};
  --input-text:{INPUT_TEXT};
  --input-border:{INPUT_BDR};
  --placeholder:{PLACEHOLDER};
}}

html, body, [class*="block-container"] {{
  background: var(--surface) !important;
  color: var(--text) !important;
}}
/* NÃO estilize h1 aqui para não sumir o título */
h2,h3,h4, label, legend, .stMarkdown p {{ color: var(--text) !important; }}

/* Sidebar legível */
div[data-testid="stSidebar"] {{
  background: var(--surface) !important;
  border-right: 1px solid var(--border);
}}
div[data-testid="stSidebar"] h1,
div[data-testid="stSidebar"] h2,
div[data-testid="stSidebar"] h3,
div[data-testid="stSidebar"] h4,
div[data-testid="stSidebar"] p,
div[data-testid="stSidebar"] label,
div[data-testid="stSidebar"] .stMarkdown,
div[data-testid="stSidebar"] [data-baseweb="radio"] label,
div[data-testid="stSidebar"] [data-baseweb="radio"] span {{
  color: var(--sidebar-text) !important;
  opacity: 1 !important;
  filter: none !important;
}}
div[data-testid="stSidebar"] [data-baseweb="radio"] svg {{ opacity: 1 !important; filter: none !important; }}

/* Cards */
div[data-testid="stForm"] {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 1rem;
}}

/* Inputs */
input, textarea, select {{
  color: var(--input-text) !important;
  background: var(--input-bg) !important;
  border-color: var(--input-border) !important;
}}
div[role="textbox"] *, .stTextInput input, .stDateInput input, .stNumberInput input {{
  color: var(--input-text) !important;
  background: var(--input-bg) !important;
}}
::placeholder {{ color: var(--placeholder) !important; }}

/* Dataframe */
[data-testid="stDataFrame"] thead th, 
[data-testid="stDataFrame"] tbody td {{ color: var(--text) !important; }}
[data-testid="stDataFrame"] tbody tr {{ background: var(--card) !important; }}

/* Botões (inclui dentro de forms) */
.stButton>button, .stDownloadButton>button,
div[data-testid="stForm"] .stButton>button {{
  background: var(--accent) !important;
  color:#111 !important;
  border:none !important; border-radius:14px !important;
  padding:.65rem 1rem !important; font-weight:800 !important;
  box-shadow:0 6px 16px rgba(215,84,19,.35) !important;
}}
div[data-testid="stForm"] .stButton>button:disabled {{
  background:#cfcfcf !important; color:#222 !important; box-shadow:none !important; opacity:.85 !important;
}}

/* Alerts legíveis */
div[data-testid="stAlert"] {{ color: var(--text) !important; }}
div[data-testid="stAlert"] p, 
div[data-testid="stAlert"] span, 
div[data-testid="stAlert"] strong {{ color: var(--text) !important; font-weight:600; }}
html:root:not(.dark) div[data-testid="stAlert"] {{ border:1px solid rgba(0,0,0,.08); border-radius:10px; }}

/* KPIs */
.kpi {{ display:flex; gap:12px; flex-wrap:wrap; }}
.kpi>div {{ background: var(--card); border:1px solid var(--border); border-radius:14px; padding:.65rem 1rem; }}
.small-note {{ opacity:.85; font-size:.86rem }}
</style>
""", unsafe_allow_html=True)

# ===== Título (laranja garantido)
st.markdown(
    "<h1 id='app-title' style='margin:0'>🏗️Sistema de Rupturas de Argamassa Habisolute</h1>",
    unsafe_allow_html=True
)
st.markdown(f"""
<style>
#app-title {{
  color: {ACCENT} !important;
  letter-spacing: .2px;
}}
</style>
""", unsafe_allow_html=True)

# Força legibilidade extra da sidebar só no modo escuro
if st.session_state.theme == "Escuro":
    st.markdown("""
    <style>
    [data-testid="stSidebar"]{ background:#0a0a0a !important; }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div[role="radiogroup"] label {
      color:#FFC08E !important;
      opacity:1 !important;
      filter:none !important;
      text-shadow:none !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] svg {
      opacity:1 !important; filter:none !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.caption("Entrada: **carga (kgf)**. Saídas: **kN/cm²** e **MPa**. PDF direto em 1 clique (somente fpdf2).")

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
                # novos campos replicados (úteis no CSV)
                "data_moldagem": st.session_state.data_moldagem.isoformat(),
                "data_ruptura":  st.session_state.data_ruptura.isoformat(),
                "idade_dias":    max(0, (st.session_state.data_ruptura - st.session_state.data_moldagem).days),
            })
            st.success("CP adicionado.")
# ===================== Tabela + Gráfico (tela) =====================
if st.session_state.registros:
    # 1) DataFrame bruto
    df = pd.DataFrame(st.session_state.registros).copy()

    # 2) Normalização para retrocompatibilidade (evita KeyError)
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
    if ("kgf_cm2" not in df.columns) or ("kn_cm2" not in df.columns) or ("mpa" not in df.columns):
        df["kgf_cm2"], df["kn_cm2"], df["mpa"] = None, None, None
    if df[["kgf_cm2", "kn_cm2", "mpa"]].isnull().any().any():
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
    a, b, c = st.columns(3)
    with a: st.metric("Média (kN/cm²)", f"{mean(df['kn_cm2']):.4f}")
    with b: st.metric("Média (MPa)",    f"{mean(df['mpa']):.3f}")
    with c:
        dp = _dp(df["mpa"].tolist())
        st.metric("DP (MPa)", f"{(dp if dp is not None else 0.0):.3f}")

    # 6) Gráfico — 1 ponto por linha (sem aggregate=None)
    st.subheader("📈Gráfico de ruptura (MPa por CP)")
    chart_df = pd.DataFrame({
        "Código CP": df["codigo_cp"].astype(str).values,
        "MPa":       df["mpa"].astype(float).values
    }).reset_index(drop=False).rename(columns={"index": "rowid"})

    axis_color = TEXT
    grid_color = "rgba(255,255,255,0.20)" if IS_DARK else "rgba(0,0,0,0.12)"
    y_max = float(chart_df["MPa"].max() * 1.15) if len(chart_df) else 1.0

    points = (
        alt.Chart(chart_df)
          .mark_point(size=90, filled=True, color=ACCENT)
          .encode(
              x=alt.X("Código CP:N", sort=None, title="Código do CP"),
              y=alt.Y("MPa:Q", scale=alt.Scale(domain=[0, y_max]), title="MPa"),
              detail="rowid:N",
              tooltip=[
                  alt.Tooltip("Código CP:N", title="Código CP"),
                  alt.Tooltip("MPa:Q", format=".3f")
              ]
          )
          .properties(height=340)
          .configure_axis(labelColor=axis_color, titleColor=axis_color,
                          gridColor=grid_color, domainColor=axis_color)
          .configure_title(color=axis_color)
          .configure_legend(labelColor=axis_color, titleColor=axis_color)
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

    # Linha extra com Moldagem/Ruptura/Idade a partir do estado do lote
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

    # ID logo após o rótulo "Código do CP"
    pdf.set_y(gy + gh + 34)
    pdf.set_font("Arial", "I", 9)
    report_id = _gen_report_id(data_obra)
    pdf.cell(0, 6, _latin1_safe(f"ID do relatório: {report_id}"), ln=1, align="L")

    # Normas (bloco textual) logo após o ID
    pdf.ln(2)
    pdf.set_font("Arial", size=8)
    pdf.multi_cell(0, 4, _latin1_safe(NORMAS_TXT))

    # Rodapé na última página (sem criar nova)
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

        # (1) Download direto
        st.download_button("📄 Exportar para PDF", data=BytesIO(pdf_bytes), file_name=fname, mime="application/pdf")

        # (2) Imprimir em nova aba — Blob (sem tela em branco)
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
