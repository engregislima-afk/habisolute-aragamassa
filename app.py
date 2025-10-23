# app.py — Rupturas de Argamassa (kgf → kN/cm² / MPa)
# PDF direto em 1 clique usando SOMENTE fpdf2 (gráfico desenhado no PDF).
from __future__ import annotations
from datetime import date
from statistics import mean, pstdev
import unicodedata
import re
import base64

import streamlit as st
import pandas as pd
import altair as alt

from io import BytesIO

# ===================== Dependência obrigatória (PDF) =====================
MISSING = []
try:
    from fpdf import FPDF
    _HAS_ROTATE = hasattr(FPDF, "rotate")  # algumas builds antigas não têm rotate()
except Exception:
    FPDF = None
    _HAS_ROTATE = False
    MISSING.append("fpdf2>=2.7")

# ===================== Tema & Estado =====================
ACCENT = "#d75413"
st.set_page_config(page_title="Rupturas de Argamassa", page_icon="🧱", layout="centered")

if "theme" not in st.session_state: st.session_state.theme = "Escuro"
if "obra" not in st.session_state: st.session_state.obra = ""
if "data_obra" not in st.session_state: st.session_state.data_obra = date.today()
if "area_padrao" not in st.session_state: st.session_state.area_padrao = 16.00
if "registros" not in st.session_state: st.session_state.registros = []

with st.sidebar:
    st.header("Preferências")
    st.session_state.theme = st.radio(
        "Tema", ["Escuro", "Claro"],
        horizontal=True,
        index=0 if st.session_state.theme == "Escuro" else 1
    )

# Paleta por tema (alto contraste)
SURFACE, CARD, BORDER, TEXT = (
    ("#0a0a0a", "#111213", "rgba(255,255,255,0.10)", "#f5f5f5")  # Escuro
    if st.session_state.theme == "Escuro"
    else ("#ffffff", "#fafafa", "rgba(0,0,0,0.12)", "#111111")    # Claro
)

# ===================== CSS global =====================
st.markdown(f"""
<style>
:root {{
  --accent:{ACCENT};
  --surface:{SURFACE};
  --card:{CARD};
  --border:{BORDER};
  --text:{TEXT};
}}

html, body, [class*="block-container"] {{
  background: var(--surface) !important;
  color: var(--text) !important;
}}

h1,h2,h3,h4, label, legend, .stMarkdown p {{
  color: var(--text) !important;
}}

div[data-testid="stSidebar"] {{
  background: var(--surface) !important;
  color: var(--text) !important;
  border-right: 1px solid var(--border);
}}

div[data-testid="stForm"] {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 1rem;
}}

.stButton>button, .stDownloadButton>button {{
  background: var(--accent);
  color: #111 !important;
  border: none; border-radius: 14px;
  padding: .65rem 1rem; font-weight: 800;
  box-shadow: 0 6px 16px rgba(215,84,19,.35);
}}
.stButton>button:disabled, .stDownloadButton>button:disabled {{
  opacity:.55; cursor:not-allowed; box-shadow:none;
}}

/* Inputs coerentes com o tema */
input, textarea, select {{
  color: var(--text) !important;
  background: var(--card) !important;
  border-color: var(--border) !important;
}}
::placeholder {{ color: color-mix(in oklab, var(--text), transparent 50%); }}
input[disabled], textarea[disabled] {{
  opacity: .85;
  color: color-mix(in oklab, var(--text), white 25%) !important;
}}

/* Dataframe */
[data-testid="stDataFrame"] thead th, 
[data-testid="stDataFrame"] tbody td {{
  color: var(--text) !important;
}}
[data-testid="stDataFrame"] tbody tr {{
  background: var(--card) !important;
}}

.kpi {{ display:flex; gap:12px; flex-wrap:wrap; }}
.kpi>div {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px; padding:.65rem 1rem;
}}
.small-note {{ opacity:.85; font-size:.86rem }}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='margin:0'>Rupturas de Argamassa</h1>", unsafe_allow_html=True)
st.caption("Entrada: **carga (kgf)**. Saídas: **kN/cm²** e **MPa**. PDF direto em 1 clique (somente fpdf2).")

# ===================== Conversões =====================
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
    """Mantém PDF robusto caso haja caracteres fora de Latin-1 (Arial core)."""
    try:
        text.encode("latin1")
        return text
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
    """Garante bytes para qualquer versão do fpdf2 (str/bytes/bytearray)."""
    out = pdf_obj.output(dest="S")
    if isinstance(out, bytes):
        return out
    if isinstance(out, bytearray):
        return bytes(out)
    # fpdf2 antigo pode devolver str latin1
    return out.encode("latin1", errors="ignore")

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

# ===================== Dados da obra =====================
with st.form("obra_form"):
    st.subheader("Dados da obra")
    a,b,c = st.columns([2,1,1])
    obra = a.text_input("Nome da obra", st.session_state.obra, placeholder="Ex.: Residencial Jardim Tropical")
    data_obra = b.date_input("Data", st.session_state.data_obra, format="DD/MM/YYYY")
    area_padrao = c.number_input("Área do CP (cm²)", min_value=0.0001,
                                 value=float(st.session_state.area_padrao), step=0.01, format="%.2f")
    col = st.columns([1,1,2])
    apply_clicked = col[0].form_submit_button("Aplicar")
    recalc_clicked = col[1].form_submit_button("Recalcular lote com nova área", disabled=(not st.session_state.registros))
    if apply_clicked:
        st.session_state.obra = obra.strip()
        st.session_state.data_obra = data_obra
        st.session_state.area_padrao = float(area_padrao)
        st.success("Dados aplicados.")
    if recalc_clicked and st.session_state.registros:
        nova_area = float(area_padrao)
        for r in st.session_state.registros:
            r["area_cm2"] = nova_area
            s_kgfcm2, s_kncm2, s_mpa = tensoes_from_kgf(r["carga_kgf"], nova_area)
            r["kgf_cm2"] = float(s_kgfcm2)
            r["kn_cm2"]  = float(s_kncm2)
            r["mpa"]     = float(s_mpa)
        st.session_state.area_padrao = nova_area
        st.success("Todos os CPs recalculados com a nova área.")

# ===================== Lançar CP =====================
st.info(f"CPs no lote: **{len(st.session_state.registros)}/12**")
with st.form("cp_form", clear_on_submit=True):
    st.subheader("Lançar ruptura (apenas kgf)")
    codigo = st.text_input("Código do CP", max_chars=32, placeholder="Ex.: A039.258 / H682 / 037.421")
    carga  = st.number_input("Carga de ruptura (kgf)", min_value=0.0, step=0.1, format="%.3f")
    if carga and st.session_state.area_padrao:
        _, knp, mpp = tensoes_from_kgf(carga, st.session_state.area_padrao)
        st.caption(f"→ Conversões (área {st.session_state.area_padrao:.2f} cm²): "
                   f"**{knp:.5f} kN/cm²** • **{mpp:.4f} MPa**")
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
            })
            st.success("CP adicionado.")

# ===================== Tabela + Gráfico (tela) =====================
if st.session_state.registros:
    df = pd.DataFrame(st.session_state.registros).copy()

    st.subheader("Lote atual (editável)")
    edited = st.data_editor(
        df[["codigo_cp","carga_kgf","area_cm2","kn_cm2","mpa"]],
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "codigo_cp": st.column_config.TextColumn("Código CP"),
            "carga_kgf": st.column_config.NumberColumn("Carga (kgf)", step=0.1, format="%.3f"),
            "area_cm2": st.column_config.NumberColumn("Área (cm²)", disabled=True, format="%.2f"),
            "kn_cm2": st.column_config.NumberColumn("kN/cm²", disabled=True, format="%.5f"),
            "mpa": st.column_config.NumberColumn("MPa", disabled=True, format="%.4f"),
        }
    )
    # aplica edições
    if not edited.equals(df[edited.columns]):
        new_regs = []
        for row in edited.itertuples(index=False):
            s_kgfcm2, s_kncm2, s_mpa = tensoes_from_kgf(float(row.carga_kgf), float(row.area_cm2))
            new_regs.append({
                "codigo_cp": str(row.codigo_cp),
                "carga_kgf": float(row.carga_kgf),
                "area_cm2": float(row.area_cm2),
                "kgf_cm2": float(s_kgfcm2),
                "kn_cm2":  float(s_kncm2),
                "mpa":     float(s_mpa),
            })
        st.session_state.registros = new_regs
        df = pd.DataFrame(st.session_state.registros)

    # exclusão por códigos
    with st.expander("🗑️ Excluir CPs", expanded=False):
        codigos = [r["codigo_cp"] for r in st.session_state.registros]
        opt = st.multiselect("Selecione os códigos a excluir", codigos)
        if st.button("Confirmar exclusão"):
            st.session_state.registros = [r for r in st.session_state.registros if r["codigo_cp"] not in set(opt)]
            st.rerun()

    # KPIs
    a,b,c = st.columns(3)
    with a: st.metric("Média (kN/cm²)", f"{mean(df['kn_cm2']):.4f}")
    with b: st.metric("Média (MPa)",    f"{mean(df['mpa']):.3f}")
    with c:
        dp = _dp(df["mpa"].tolist())
        st.metric("DP (MPa)", f"{(dp if dp is not None else 0.0):.3f}")

    st.subheader("Gráfico de ruptura (MPa por CP)")
    chart_df = pd.DataFrame({"Código CP": df["codigo_cp"].values, "MPa": df["mpa"].values})

    # Cores de eixos/grades conforme o tema
    axis_color = TEXT
    grid_color = "rgba(255,255,255,0.20)" if st.session_state.theme == "Escuro" else "rgba(0,0,0,0.12)"

    y_max = max(chart_df["MPa"]) * 1.15 if len(chart_df) else 1
    points = (
        alt.Chart(chart_df)
          .mark_point(size=90, filled=True, color=ACCENT)
          .encode(
              x=alt.X("Código CP:N", sort=None, title="Código do CP"),
              y=alt.Y("MPa:Q", scale=alt.Scale(domain=[0, y_max]), title="MPa"),
              tooltip=["Código CP", alt.Tooltip("MPa:Q", format=".3f")]
          )
          .properties(height=340)
          .configure_axis(
              labelColor=axis_color,
              titleColor=axis_color,
              gridColor=grid_color,
              domainColor=axis_color
          )
          .configure_title(color=axis_color)
          .configure_legend(labelColor=axis_color, titleColor=axis_color)
    )
    st.altair_chart(points, use_container_width=True)
    st.divider()

# ===================== PDF (fpdf2 desenhando o gráfico) =====================
def draw_scatter_on_pdf(
    pdf: "FPDF",
    df: pd.DataFrame,
    x: float,
    y: float,
    w: float,
    h: float,
    accent: str = "#d75413",
) -> None:
    """Desenha o gráfico (MPa por CP) no PDF com espaçamentos ajustados."""
    # Moldura + grade
    pdf.set_draw_color(220, 220, 220)
    pdf.rect(x, y, w, h)

    codes = df["codigo_cp"].astype(str).tolist()
    ys = df["mpa"].astype(float).tolist()
    if not ys:
        return

    y_max = max(ys) * 1.15
    y_min = 0.0

    # Eixo Y (linhas de grade + ticks)
    pdf.set_font("Arial", size=8)
    ticks = 5
    for k in range(ticks + 1):
        yy = y + h - (h * k / ticks)
        val = y_min + (y_max - y_min) * k / ticks
        pdf.line(x, yy, x + w, yy)
        pdf.text(x - 7.5, yy + 2.2, f"{val:.1f}")

    # Pontos + rótulos de CP (afastados do eixo)
    r = int(accent[1:3], 16)
    g = int(accent[3:5], 16)
    b = int(accent[5:7], 16)
    pdf.set_fill_color(r, g, b)

    n = len(ys)
    dx = 8.0  # afastamento lateral dos rótulos (aumente se quiser mais)
    for i, val in enumerate(ys):
        px = x + (w * (i / max(1, n - 1)))
        py = y + h - (h * (val - y_min) / max(1e-9, (y_max - y_min)))
        pdf.ellipse(px - 1.8, py - 1.8, 3.6, 3.6, style="F")

        label = _latin1_safe(codes[i][:14])
        if _HAS_ROTATE:
            try:
                pivot_x = px + dx
                pivot_y = y + h + 16  # desce bem os rótulos verticais
                pdf.rotate(90, pivot_x, pivot_y)
                pdf.text(pivot_x, pivot_y, label)
                pdf.rotate(0)
            except Exception:
                pdf.text(px - (len(label) * 1.2) + dx, y + h + 12, label)
        else:
            pdf.text(px - (len(label) * 1.2) + dx, y + h + 12, label)

    # Títulos do gráfico
    pdf.set_font("Arial", "B", 11)
    pdf.text(x, y - 1, "Gráfico de ruptura (MPa por CP)")  # mais longe da tabela
    pdf.set_font("Arial", size=9)
    pdf.text(x + w / 2 - 12, y + h + 26, "Código do CP")   # mais abaixo dos rótulos


def build_pdf(obra: str, data_obra: date, area_cm2: float, df: pd.DataFrame) -> bytes:
    pdf = FPDF("P", "mm", "A4")

    # Margens & quebra automática
    left, top, right = 20, 22, 20
    pdf.set_margins(left, top, right)
    pdf.set_auto_page_break(auto=True, margin=18)

    pdf.add_page()

    # Cabeçalho
    pdf.set_font("Arial", "B", 15)
    pdf.cell(0, 8, _latin1_safe("Rupturas de Argamassa  Lote"), ln=1, align="C")

    pdf.set_font("Arial", size=11)
    info = f"Obra: {obra}   |   Data: {data_obra.strftime('%d/%m/%Y')}   |   Área do CP: {area_cm2:.2f} cm²"
    pdf.cell(0, 6, _latin1_safe(info), ln=1, align="C")
    pdf.ln(6)

    # Tabela
    hdr = ["#", "Código CP", "Carga (kgf)", "Área (cm²)", "kN/cm²", "MPa"]
    wid = [10, 60, 30, 24, 28, 24]
    pdf.set_font("Arial", "B", 10)
    for h, w in zip(hdr, wid):
        pdf.cell(w, 7, _latin1_safe(h), 1, 0, "C")
    pdf.ln()
    pdf.set_font("Arial", size=10)
    for i, row in enumerate(df.itertuples(index=False), 1):
        cells = [
            str(i),
            _latin1_safe(row.codigo_cp),
            f"{row.carga_kgf:.3f}",
            f"{row.area_cm2:.2f}",
            f"{row.kn_cm2:.4f}",
            f"{row.mpa:.3f}",
        ]
        for c, w in zip(cells, wid):
            pdf.cell(w, 6, c, 1, 0, "C")
        pdf.ln()

    # Gráfico (com mais “respiro” após a tabela)
    pdf.ln(12)
    gy = pdf.get_y() + 6
    gx = left + 2
    gw = 180 - (left - 15)
    gh = 78
    draw_scatter_on_pdf(pdf, df, x=gx, y=gy, w=gw, h=gh, accent=ACCENT)
    pdf.set_y(gy + gh + 30)

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
        # Gera o PDF
        df_pdf = pd.DataFrame(st.session_state.registros)
        pdf_bytes = build_pdf(
            st.session_state.obra, st.session_state.data_obra, st.session_state.area_padrao, df_pdf
        )
        # Nome do arquivo
        data_str = st.session_state.data_obra.strftime("%Y%m%d")
        safe_obra = _safe_filename(st.session_state.obra)
        fname = f"Lote_Rupturas_{safe_obra}_{data_str}.pdf" if safe_obra else f"Lote_Rupturas_{data_str}.pdf"

        # 1) Download direto do PDF (como arquivo em memória)
        pdf_file = BytesIO(pdf_bytes)
        st.download_button("📄 Exportar para PDF", data=pdf_file, file_name=fname, mime="application/pdf")

        # 2) Abrir para imprimir em nova aba (data URI)
        b64 = base64.b64encode(pdf_bytes).decode("utf-8")
        pdf_data_uri = f"data:application/pdf;base64,{b64}"
        st.markdown(
            f"""<a href="{pdf_data_uri}" target="_blank" 
                   style="display:inline-block;margin-top:8px;padding:.55rem .9rem;border-radius:12px;
                          background:{ACCENT};color:#111;font-weight:800;text-decoration:none;">
                   🖨️ Imprimir (abrir PDF)
                </a>""",
            unsafe_allow_html=True
        )

# ===================== Rodapé diagnóstico =====================
st.caption(
    ("PDF direto ativo ✅" if not MISSING else "PDF direto inativo ❌") +
    (" • Dependência faltando: " + ", ".join(MISSING) if MISSING else "") +
    " • Conversões: [kgf/cm²] → kN/cm² (×0,00980665) e MPa (×0,0980665)."
)
