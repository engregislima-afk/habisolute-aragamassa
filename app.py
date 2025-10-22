# app.py — Rupturas de Argamassa (kgf → kN/cm² / MPa)
# PDF direto em 1 clique usando SOMENTE fpdf2 (gráfico desenhado no próprio PDF).
from __future__ import annotations
import io
from datetime import date
from statistics import mean, pstdev

import streamlit as st
import pandas as pd
import altair as alt

# ---------------- dependência obrigatória para PDF ----------------
MISSING = []
try:
    from fpdf import FPDF
except Exception:
    MISSING.append("fpdf2>=2.7")

# ---------------- tema (preto/laranja e claro/laranja) ----------------
ACCENT = "#d75413"
st.set_page_config(page_title="Rupturas de Argamassa", page_icon="🧱", layout="centered")

if "theme" not in st.session_state: st.session_state.theme = "Escuro"
if "obra" not in st.session_state: st.session_state.obra = ""
if "data_obra" not in st.session_state: st.session_state.data_obra = date.today()
if "area_padrao" not in st.session_state: st.session_state.area_padrao = 16.00
if "registros" not in st.session_state: st.session_state.registros = []
if "logo_bytes" not in st.session_state: st.session_state.logo_bytes = None
if "footer_text" not in st.session_state: st.session_state.footer_text = ""

with st.sidebar:
    st.header("Preferências")
    st.session_state.theme = st.radio("Tema", ["Escuro", "Claro"],
                                      horizontal=True,
                                      index=0 if st.session_state.theme == "Escuro" else 1)
    st.markdown("---")
    st.subheader("Logo (opcional)")
    up = st.file_uploader("PNG/JPG/SVG", type=["png","jpg","jpeg","svg"])
    if up is not None:
        st.session_state.logo_bytes = up.read()
        st.image(st.session_state.logo_bytes, caption="Pré-visualização", use_container_width=True)
    st.markdown("---")
    st.subheader("Rodapé do relatório (opcional)")
    st.session_state.footer_text = st.text_area(
        "Observações / norma / técnico responsável", st.session_state.footer_text, height=90
    )

SURFACE, CARD, BORDER, TEXT = (
    ("#0a0a0a", "#111213", "rgba(255,255,255,0.10)", "#f5f5f5")
    if st.session_state.theme == "Escuro"
    else ("#fafafa", "#ffffff", "rgba(0,0,0,0.10)", "#111111")
)

st.markdown(f"""
<style>
:root {{ --accent:{ACCENT}; --surface:{SURFACE}; --card:{CARD}; --border:{BORDER}; --text:{TEXT}; }}
html, body, [class*="block-container"] {{ background: var(--surface); color: var(--text); }}
h1,h2,h3,h4{{color:var(--text)}}
.stButton>button, .stDownloadButton>button {{
  background:var(--accent); color:#111; border:none; border-radius:14px;
  padding:.65rem 1rem; font-weight:800; box-shadow:0 6px 16px rgba(215,84,19,.35);
}}
.stButton>button:disabled, .stDownloadButton>button:disabled {{ opacity:.55; cursor:not-allowed; box-shadow:none; }}
div[data-testid="stForm"] {{ background:var(--card); border:1px solid var(--border); border-radius:18px; padding:1rem; }}
.kpi {{ display:flex; gap:12px; flex-wrap:wrap; }}
.kpi>div {{ background:var(--card); border:1px solid var(--border); border-radius:14px; padding:.65rem 1rem; }}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='margin:0'>Rupturas de Argamassa</h1>", unsafe_allow_html=True)
st.caption("Entrada: **carga (kgf)**. Saídas: **kN/cm²** e **MPa**. PDF direto em 1 clique (somente fpdf2).")

# ---------------- conversões ----------------
KGF_CM2_TO_MPA    = 0.0980665
KGF_CM2_TO_KN_CM2 = 0.00980665
def tensoes_from_kgf(carga_kgf: float, area_cm2: float):
    if area_cm2 <= 0: return None, None, None
    s = carga_kgf / area_cm2
    return s, s*KGF_CM2_TO_KN_CM2, s*KGF_CM2_TO_MPA
def _media(v): return None if not v else mean(v)
def _dp(v):
    if not v: return None
    if len(v)==1: return 0.0
    return pstdev(v)

# ---------------- conversor rápido ----------------
with st.expander("🔁 Conversor rápido (kgf → kN/cm² / MPa)", expanded=False):
    c1,c2 = st.columns(2)
    kgf = c1.number_input("Carga (kgf)", min_value=0.0, value=0.0, step=0.1, format="%.3f")
    area_demo = c2.number_input("Área (cm²)", min_value=0.0001, value=st.session_state.area_padrao, step=0.01, format="%.2f")
    if kgf and area_demo:
        _, kn, mp = tensoes_from_kgf(kgf, area_demo)
        st.markdown(
            f"<div class='kpi'><div><b>kN/cm²</b><br>{kn:.5f}</div><div><b>MPa</b><br>{mp:.4f}</div></div>",
            unsafe_allow_html=True
        )

# ---------------- dados da obra ----------------
with st.form("obra_form"):
    st.subheader("Dados da obra")
    a,b,c = st.columns([2,1,1])
    obra = a.text_input("Nome da obra", st.session_state.obra, placeholder="Ex.: Residencial Jardim Tropical")
    data_obra = b.date_input("Data", st.session_state.data_obra, format="DD/MM/YYYY")
    area_padrao = c.number_input("Área do CP (cm²)", min_value=0.0001, value=float(st.session_state.area_padrao), step=0.01, format="%.2f")
    if st.form_submit_button("Aplicar"):
        st.session_state.obra = obra.strip()
        st.session_state.data_obra = data_obra
        st.session_state.area_padrao = float(area_padrao)
        st.success("Dados aplicados.")

# ---------------- lançar CP ----------------
st.info(f"CPs no lote: **{len(st.session_state.registros)}/12**")
with st.form("cp_form", clear_on_submit=True):
    st.subheader("Lançar ruptura (apenas kgf)")
    codigo = st.text_input("Código do CP", max_chars=32, placeholder="Ex.: A039.258 / H682 / 037.421")
    carga  = st.number_input("Carga de ruptura (kgf)", min_value=0.0, step=0.1, format="%.3f")
    if carga and st.session_state.area_padrao:
        _, knp, mpp = tensoes_from_kgf(carga, st.session_state.area_padrao)
        st.caption(f"→ Conversões (área {st.session_state.area_padrao:.2f} cm²): **{knp:.5f} kN/cm²** • **{mpp:.4f} MPa**")
    ok = st.form_submit_button("Adicionar CP", disabled=(len(st.session_state.registros)>=12 or not st.session_state.obra))
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

# ---------------- tabela + gráfico (Altair só para tela) ----------------
if st.session_state.registros:
    df = pd.DataFrame(st.session_state.registros)
    view = df[["codigo_cp","carga_kgf","area_cm2","kn_cm2","mpa"]].copy()
    view.columns = ["Código CP","Carga (kgf)","Área (cm²)","kN/cm²","MPa"]
    st.subheader("Lote atual")
    st.dataframe(view, use_container_width=True)

    a,b = st.columns(2)
    with a: st.metric("Média (kN/cm²)", f"{mean(df['kn_cm2']):.4f}")
    with b: st.metric("Média (MPa)",    f"{mean(df['mpa']):.3f}")

    st.subheader("Gráfico de ruptura (MPa por CP)")
    chart_df = pd.DataFrame({"Código CP": df["codigo_cp"].values, "MPa": df["mpa"].values})
    y_max = max(chart_df["MPa"]) * 1.15 if len(chart_df) else 1
    points = (
        alt.Chart(chart_df).mark_point(size=90, filled=True, color=ACCENT)
        .encode(
            x=alt.X("Código CP:N", sort=None, title="Código do CP"),
            y=alt.Y("MPa:Q", scale=alt.Scale(domain=[0, y_max]), title="MPa"),
            tooltip=["Código CP", alt.Tooltip("MPa:Q", format=".3f")]
        )
        .properties(height=340)
    )
    st.altair_chart(points, use_container_width=True)
    st.divider()

# ---------------- funções do PDF (apenas fpdf2) ----------------
def draw_scatter_on_pdf(pdf: "FPDF", df: pd.DataFrame, x: float, y: float, w: float, h: float, accent="#d75413"):
    """Desenha o gráfico de pontos (MPa por CP) diretamente no PDF."""
    # moldura
    pdf.set_draw_color(220,220,220)
    pdf.rect(x, y, w, h)

    # dados
    codes = df["codigo_cp"].astype(str).tolist()
    ys    = df["mpa"].astype(float).tolist()
    if not ys: return
    y_max = max(ys) * 1.15
    y_min = 0.0

    # grade/ticks Y
    pdf.set_font("Arial", size=8)
    ticks = 5
    for k in range(ticks+1):
        yy = y + h - (h * k / ticks)
        val = y_min + (y_max - y_min) * k / ticks
        pdf.line(x, yy, x+w, yy)
        pdf.text(x-6, yy+2.2, f"{val:.1f}")

    # pontos
    r = int(accent[1:3],16); g = int(accent[3:5],16); b = int(accent[5:7],16)
    pdf.set_fill_color(r,g,b)
    n = len(ys)
    for i, val in enumerate(ys):
        px = x + (w * (i / max(1, n-1)))
        py = y + h - (h * (val - y_min) / max(1e-9, (y_max - y_min)))
        pdf.ellipse(px-1.8, py-1.8, 3.6, 3.6, style="F")
        # rótulo X rotacionado
        pdf.rotate(90, px, y+h+8)
        pdf.text(px, y+h+8, codes[i][:10])
        pdf.rotate(0)

    # títulos
    pdf.set_font("Arial", "B", 11)
    pdf.text(x, y-4, "Gráfico de ruptura (MPa por CP)")
    pdf.set_font("Arial", size=9)
    pdf.text(x + w/2 - 12, y + h + 12, "Código do CP")

def build_pdf(obra: str, data_obra: date, area_cm2: float,
              df: pd.DataFrame, logo_bytes: bytes | None, footer_text: str) -> bytes:
    pdf = FPDF("P","mm","A4")
    pdf.add_page()
    # logo
    if logo_bytes:
        try:
            p = "/tmp/_logo.png"; open(p,"wb").write(logo_bytes); pdf.image(p, x=10, y=10, w=35)
        except Exception:
            pass
    # título e info
    pdf.set_font("Arial","B",14); pdf.cell(0,7,"Rupturas de Argamassa — Lote",ln=1,align="C")
    pdf.set_font("Arial", size=11)
    pdf.cell(0,6,f"Obra: {obra}   |   Data: {data_obra.strftime('%d/%m/%Y')}   |   Área do CP: {area_cm2:.2f} cm²",ln=1,align="C")
    pdf.ln(3)
    # tabela
    hdr, wid = ["#","Código CP","Carga (kgf)","Área (cm²)","kN/cm²","MPa"], [8,52,28,22,28,24]
    pdf.set_font("Arial","B",10)
    for h,w in zip(hdr,wid): pdf.cell(w,7,h,1,0,"C")
    pdf.ln(); pdf.set_font("Arial", size=10)
    for i,row in enumerate(df.itertuples(index=False),1):
        cells=[str(i), row.codigo_cp, f"{row.carga_kgf:.3f}", f"{row.area_cm2:.2f}", f"{row.kn_cm2:.4f}", f"{row.mpa:.3f}"]
        for c,w in zip(cells,wid): pdf.cell(w,6,c,1,0,"C")
        pdf.ln()
    # gráfico desenhado
    pdf.ln(3)
    gy = pdf.get_y() + 2
    draw_scatter_on_pdf(pdf, df, x=15, y=gy, w=180, h=70, accent=ACCENT)
    pdf.set_y(gy + 70)
    # rodapé
    if footer_text.strip():
        pdf.ln(3); pdf.set_font("Arial", size=9); pdf.multi_cell(0,5,footer_text.strip())
    return pdf.output(dest="S").encode("latin1")

# ---------------- ações (1 clique = baixar) ----------------
c1,c2,c3 = st.columns(3)
with c1:
    st.button("Limpar lote", disabled=(not st.session_state.registros),
              on_click=lambda: st.session_state.update(registros=[]))

with c2:
    if st.session_state.registros:
        st.download_button(
            "Baixar CSV",
            data=pd.DataFrame(st.session_state.registros).to_csv(index=False).encode("utf-8"),
            file_name="rupturas_lote.csv", mime="text/csv"
        )

with c3:
    if not st.session_state.registros:
        st.download_button("📄 Exportar para PDF", data=b"", file_name="vazio.pdf", disabled=True)
    else:
        if MISSING:
            st.download_button("📄 Exportar para PDF", data=b"", file_name="rupturas.pdf", disabled=True)
            st.error("Para PDF direto, instale: " + ", ".join(MISSING))
        else:
            df_pdf = pd.DataFrame(st.session_state.registros)
            pdf_bytes = build_pdf(
                st.session_state.obra, st.session_state.data_obra, st.session_state.area_padrao,
                df_pdf, st.session_state.logo_bytes, st.session_state.footer_text
            )
            data_str = st.session_state.data_obra.strftime("%Y%m%d")
            safe_obra = "".join(c for c in st.session_state.obra if c.isalnum() or c in (" ","-","_")).strip().replace(" ","_")
            fname = f"Lote_Rupturas_{safe_obra}_{data_str}.pdf"
            st.download_button("📄 Exportar para PDF", data=pdf_bytes, file_name=fname, mime="application/pdf")

# ---------------- rodapé diagnóstico ----------------
st.caption(
    ("PDF direto ativo ✅" if not MISSING else "PDF direto inativo ❌") +
    (" • Dependência faltando: " + ", ".join(MISSING) if MISSING else "") +
    " • Conversões: [kgf/cm²] → kN/cm² (×0,00980665) e MPa (×0,0980665)."
)
