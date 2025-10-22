# app.py — Rupturas de Argamassa (kgf → kN/cm² / MPa)
# Tema preto/laranja (#d75413) e claro/laranja, gráfico de pontos, PDF com gráfico, logo e rodapé.
from __future__ import annotations
import io, os, subprocess, sys
from datetime import date
from statistics import mean, pstdev

import streamlit as st
import pandas as pd
import altair as alt
import importlib.util
def _diag():
    ok_fpdf  = importlib.util.find_spec("fpdf") is not None
    ok_plotly= importlib.util.find_spec("plotly") is not None
    ok_kale  = importlib.util.find_spec("kaleido") is not None
    st.caption(
        f"Diag: fpdf2={'✅' if ok_fpdf else '❌'} • plotly={'✅' if ok_plotly else '❌'} • kaleido={'✅' if ok_kale else '❌'}"
    )
# chame assim em qualquer lugar:
# _diag()

# =================== PDF backends (ReportLab → FPDF2; tenta auto-instalar fpdf2) ===================
PDF_BACKEND = "none"  # "reportlab" | "fpdf2" | "none"

def _try_import_pdfs():
    global PDF_BACKEND
    try:
        from reportlab.lib.pagesizes import A4  # noqa: F401
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image  # noqa: F401
        from reportlab.lib import colors  # noqa: F401
        from reportlab.lib.styles import getSampleStyleSheet  # noqa: F401
        PDF_BACKEND = "reportlab"; return
    except Exception:
        pass
    try:
        from fpdf import FPDF  # noqa: F401
        PDF_BACKEND = "fpdf2"; return
    except Exception:
        PDF_BACKEND = "none"

_try_import_pdfs()
if PDF_BACKEND == "none":
    # tenta instalar fpdf2 dinamicamente (no Cloud prefira requirements.txt)
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "fpdf2>=2.7"])
        from fpdf import FPDF  # noqa: F401
        PDF_BACKEND = "fpdf2"
    except Exception:
        PDF_BACKEND = "none"

# =================== Estado ===================
if "obra" not in st.session_state: st.session_state.obra = ""
if "data_obra" not in st.session_state: st.session_state.data_obra = date.today()
if "area_padrao" not in st.session_state: st.session_state.area_padrao = 16.00
if "registros" not in st.session_state: st.session_state.registros = []
if "pdf_bytes" not in st.session_state: st.session_state.pdf_bytes = None
if "plot_png" not in st.session_state: st.session_state.plot_png = None
if "logo_bytes" not in st.session_state: st.session_state.logo_bytes = None
if "footer_text" not in st.session_state: st.session_state.footer_text = ""
if "theme" not in st.session_state: st.session_state.theme = "Escuro"

# =================== Barra lateral: Tema + Logo + Rodapé ===================
with st.sidebar:
    st.header("Preferências")
    st.session_state.theme = st.radio("Tema", ["Escuro", "Claro"],
                                      horizontal=True,
                                      index=0 if st.session_state.theme == "Escuro" else 1)
    st.markdown("---")
    st.subheader("Logo da empresa (opcional)")
    up = st.file_uploader("PNG, JPG ou SVG", type=["png", "jpg", "jpeg", "svg"], accept_multiple_files=False)
    if up is not None:
        st.session_state.logo_bytes = up.read()
        st.image(st.session_state.logo_bytes, caption="Pré-visualização", use_container_width=True)
    st.markdown("---")
    st.subheader("Rodapé do relatório (opcional)")
    st.session_state.footer_text = st.text_area(
        "Observações (norma, técnico responsável, etc.)",
        st.session_state.footer_text, height=100,
        placeholder="Ex.: Resultados conforme ABNT NBR xxxx. Técnico resp.: Fulano CREA 000000/D."
    )

# =================== Tema (Preto/Laranja e Claro/Laranja) ===================
ACCENT = "#d75413"
if st.session_state.theme == "Escuro":
    SURFACE = "#0a0a0a"            # preto
    CARD_BG = "#111213"
    BORDER  = "rgba(255,255,255,0.10)"
    TEXT    = "#f5f5f5"
else:
    SURFACE = "#fafafa"            # claro
    CARD_BG = "#ffffff"
    BORDER  = "rgba(0,0,0,0.10)"
    TEXT    = "#111111"

st.set_page_config(page_title="Rupturas de Argamassa", page_icon="🧱", layout="centered")
st.markdown(f"""
<style>
:root {{
  --accent:{ACCENT}; --surface:{SURFACE}; --card:{CARD_BG};
  --border:{BORDER}; --text:{TEXT};
}}
html, body, [class*="block-container"] {{ background: var(--surface); color: var(--text); }}
h1, h2, h3, h4 {{ color: var(--text); letter-spacing:.2px }}
hr {{ border-color: rgba(127,127,127,.18); }}

.stButton>button {{
  background: var(--accent); color: #111; border: none; border-radius: 14px;
  padding: .65rem 1rem; font-weight: 800; box-shadow: 0 6px 16px rgba(215,84,19,.35);
}}
.stButton>button:disabled {{ opacity:.55; cursor:not-allowed; box-shadow:none; }}

.stDownloadButton>button {{
  background: transparent; color: var(--text); border: 1px solid var(--border);
  border-radius: 14px; padding: .6rem 1rem;
}}

div[data-testid="stForm"] {{
  background: var(--card); border: 1px solid var(--border); border-radius: 18px;
  padding: 1rem 1rem .5rem; box-shadow: 0 12px 30px rgba(0,0,0,.20);
}}

table td, table th {{ color: var(--text); }}
.kpi {{ display:flex; gap:12px; flex-wrap:wrap; margin: .25rem 0 .5rem 0; }}
.kpi > div {{
  background: var(--card); border: 1px solid var(--border); border-radius: 16px;
  padding: .75rem 1rem; box-shadow: 0 6px 18px rgba(0,0,0,.12);
}}
.small-note {{ opacity:.8; font-size:.9rem; }}
</style>
""", unsafe_allow_html=True)

# =================== Cabeçalho ===================
st.markdown("<h1 style='margin:0'>Rupturas de Argamassa</h1>", unsafe_allow_html=True)
st.caption("Entrada por CP: **carga de ruptura (kgf)**. Área por obra. Saídas: **kN/cm²** e **MPa**. Gráfico só com pontos e PDF com o mesmo gráfico.")

# =================== Conversões ===================
KGF_CM2_TO_MPA    = 0.0980665
KGF_CM2_TO_KN_CM2 = 0.00980665

# =================== Helpers ===================
def tensoes_from_kgf(carga_kgf: float, area_cm2: float):
    if area_cm2 <= 0: return None, None, None
    stress_kgf_cm2 = carga_kgf / area_cm2
    return stress_kgf_cm2, stress_kgf_cm2 * KGF_CM2_TO_KN_CM2, stress_kgf_cm2 * KGF_CM2_TO_MPA

def _media(lst): return None if not lst else mean(lst)
def _dp(lst):
    if not lst: return None
    if len(lst) == 1: return 0.0
    return pstdev(lst)

# =================== PNG do gráfico (Plotly + Kaleido) ===================
def chart_png_from_df(df: pd.DataFrame) -> bytes | None:
    if df.empty: return None
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except Exception:
        return None
    codes = df["codigo_cp"].astype(str).tolist()
    mpa_vals = df["mpa"].tolist()
    fig = make_subplots(rows=1, cols=1)
    fig.add_trace(go.Scatter(x=codes, y=mpa_vals, mode="markers", marker=dict(size=9, color=ACCENT), name="MPa"), row=1, col=1)
    ymax = max(mpa_vals) * 1.15 if mpa_vals else 1
    fig.update_yaxes(range=[0, ymax], title_text="MPa", row=1, col=1)
    fig.update_xaxes(title_text="Código do CP", row=1, col=1)
    fig.update_layout(title_text="Gráfico de ruptura (MPa por CP)",
                      margin=dict(l=20,r=20,t=40,b=40), height=360,
                      paper_bgcolor="white", plot_bgcolor="white")
    try:
        return fig.to_image(format="png", scale=2)  # requer kaleido
    except Exception:
        return None

# =================== PDF ===================
def build_pdf(obra: str, data_obra: date, area_cm2: float, df: pd.DataFrame,
              chart_png: bytes | None, logo_bytes: bytes | None, footer_text: str) -> bytes:
    if PDF_BACKEND == "reportlab":
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=24, leftMargin=24, topMargin=28, bottomMargin=28)
        styles = getSampleStyleSheet()
        elems = []
        if logo_bytes:
            try:
                img_logo = Image(io.BytesIO(logo_bytes)); img_logo._restrictSize(120,60)
                elems += [img_logo, Spacer(1,6)]
            except Exception: pass
        elems.append(Paragraph("<para align='center'><b>Rupturas de Argamassa — Lote</b></para>", styles["Title"]))
        info = Paragraph(
            f"<para align='center'>Obra: <b>{obra}</b> &nbsp;|&nbsp; Data: <b>{data_obra.strftime('%d/%m/%Y')}</b> &nbsp;|&nbsp; Área do CP: <b>{area_cm2:.2f} cm²</b></para>",
            styles["Normal"]
        )
        elems += [Spacer(1,6), info, Spacer(1,12)]
        data_table = [["#", "Código CP", "Carga (kgf)", "Área (cm²)", "kN/cm²", "MPa"]]
        for i, row in enumerate(df.itertuples(index=False), start=1):
            data_table.append([i, row.codigo_cp, f"{row.carga_kgf:.3f}", f"{row.area_cm2:.2f}", f"{row.kn_cm2:.4f}", f"{row.mpa:.3f}"])
        tbl = Table(data_table, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#ffd7c5")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.black),
            ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ]))
        elems.append(tbl)
        if chart_png:
            elems += [Spacer(1,14), Paragraph("<b>Gráfico de ruptura</b>", styles["Heading3"]), Spacer(1,6)]
            elems.append(Image(io.BytesIO(chart_png), width=500, height=280))
        if footer_text.strip():
            elems += [Spacer(1,10), Paragraph(footer_text.strip(), styles["Normal"])]
        doc.build(elems); buffer.seek(0); return buffer.read()

    if PDF_BACKEND == "fpdf2":
        from fpdf import FPDF
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.add_page()
        if logo_bytes:
            try:
                path_logo = "/tmp/_logo.png"
                with open(path_logo, "wb") as f: f.write(logo_bytes)
                pdf.image(path_logo, x=10, y=10, w=35)
            except Exception: pass
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 7, "Rupturas de Argamassa — Lote", ln=1, align="C")
        pdf.set_font("Arial", size=11)
        pdf.cell(0, 6, f"Obra: {obra}   |   Data: {data_obra.strftime('%d/%m/%Y')}   |   Área do CP: {area_cm2:.2f} cm²", ln=1, align="C")
        pdf.ln(3)
        headers = ["#", "Código CP", "Carga (kgf)", "Área (cm²)", "kN/cm²", "MPa"]
        widths  = [8, 52, 28, 22, 28, 24]
        pdf.set_font("Arial", "B", 10)
        for h, w in zip(headers, widths): pdf.cell(w, 7, h, border=1, align="C")
        pdf.ln(); pdf.set_font("Arial", size=10)
        for i, row in enumerate(df.itertuples(index=False), start=1):
            cells = [str(i), row.codigo_cp, f"{row.carga_kgf:.3f}", f"{row.area_cm2:.2f}", f"{row.kn_cm2:.4f}", f"{row.mpa:.3f}"]
            for c, w in zip(cells, widths): pdf.cell(w, 6, c, border=1, align="C")
            pdf.ln()
        if chart_png:
            path = "/tmp/chart_mpa.png"
            with open(path, "wb") as f: f.write(chart_png)
            pdf.ln(3); pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 6, "Gráfico de ruptura (MPa por CP)", ln=1, align="L")
            pdf.image(path, x=None, y=None, w=180)
        if footer_text.strip():
            pdf.ln(3); pdf.set_font("Arial", size=9); pdf.multi_cell(0, 5, footer_text.strip(), align="L")
        return pdf.output(dest="S").encode("latin1")

    raise RuntimeError("Sem backend de PDF disponível.")

# =================== Conversor rápido ===================
with st.expander("🔁 Conversor rápido (kgf → kN/cm² / MPa)", expanded=False):
    colc, cola = st.columns([1,1])
    with colc:
        v_kgf = st.number_input("Carga (kgf)", min_value=0.0, value=0.0, step=0.1, format="%.3f")
    with cola:
        area_demo = st.number_input("Área (cm²) p/ conversão", min_value=0.0001,
                                    value=st.session_state.area_padrao, step=0.01, format="%.2f")
    if v_kgf and area_demo:
        _, kn_demo, mpa_demo = tensoes_from_kgf(v_kgf, area_demo)
        st.markdown(
            f"<div class='kpi'>"
            f"<div><b>Entrada</b><br>{v_kgf:.3f} kgf</div>"
            f"<div><b>Área</b><br>{area_demo:.2f} cm²</div>"
            f"<div><b>kN/cm²</b><br>{kn_demo:.5f}</div>"
            f"<div><b>MPa</b><br>{mpa_demo:.4f}</div>"
            f"</div>", unsafe_allow_html=True
        )

# =================== Dados da obra ===================
with st.form("obra_form"):
    st.subheader("Dados da obra")
    col1, col2, col3 = st.columns([2,1,1])
    with col1:
        obra = st.text_input("Nome da obra", value=st.session_state.obra,
                             placeholder="Ex.: Residencial Jardim Tropical")
    with col2:
        data_obra = st.date_input("Data", value=st.session_state.data_obra, format="DD/MM/YYYY")
    with col3:
        area_padrao = st.number_input("Área do CP (cm²)", min_value=0.0001,
                                      value=float(st.session_state.area_padrao), step=0.01, format="%.2f")
    if st.form_submit_button("Aplicar dados da obra"):
        st.session_state.obra = obra.strip()
        st.session_state.data_obra = data_obra
        st.session_state.area_padrao = float(area_padrao)
        st.session_state.plot_png = None
        st.success("Dados da obra aplicados.")

# =================== Lançamento CP ===================
qtd = len(st.session_state.registros)
st.info(f"CPs no lote atual: **{qtd}/12**")
disabled_add = (qtd >= 12) or (not st.session_state.obra)
with st.form("cp_form", clear_on_submit=True):
    st.subheader("Lançar ruptura (apenas carga em kgf)")
    codigo_cp = st.text_input("Código do CP", placeholder="Ex.: A039.258 / H682 / 037.421", max_chars=32)
    carga_kgf  = st.number_input("Carga de ruptura (kgf)", min_value=0.0, step=0.1, format="%.3f")
    if carga_kgf and st.session_state.area_padrao:
        _, _kn_prev, _mp_prev = tensoes_from_kgf(carga_kgf, st.session_state.area_padrao)
        st.caption(f"→ Conversões com área {st.session_state.area_padrao:.2f} cm²: **{_kn_prev:.5f} kN/cm²** • **{_mp_prev:.4f} MPa**")
    if st.form_submit_button("Adicionar CP ao lote", disabled=disabled_add):
        if not st.session_state.obra:
            st.error("Defina os dados da obra antes de lançar CPs.")
        elif not codigo_cp.strip():
            st.error("Informe o código do CP.")
        elif carga_kgf <= 0:
            st.error("Informe uma carga em kgf maior que zero.")
        else:
            s_kgfcm2, s_kncm2, s_mpa = tensoes_from_kgf(carga_kgf, st.session_state.area_padrao)
            st.session_state.registros.append({
                "codigo_cp": codigo_cp.strip(),
                "carga_kgf": float(carga_kgf),
                "area_cm2": float(st.session_state.area_padrao),
                "kgf_cm2": float(s_kgfcm2),
                "kn_cm2":  float(s_kncm2),
                "mpa":     float(s_mpa),
            })
            st.session_state.plot_png = None

# =================== Tabela + Gráfico ===================
if st.session_state.registros:
    df = pd.DataFrame(st.session_state.registros)
    df_display = df[["codigo_cp","carga_kgf","area_cm2","kn_cm2","mpa"]].copy()
    df_display.columns = ["Código CP","Carga (kgf)","Área (cm²)","kN/cm²","MPa"]

    st.subheader("Lote atual")
    st.dataframe(df_display, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a: st.metric("Média (kN/cm²)", f"{mean(df['kn_cm2']):.4f}")
    with col_b: st.metric("Média (MPa)",    f"{mean(df['mpa']):.3f}")

    st.subheader("Gráfico de ruptura (MPa por CP)")
    chart_df = pd.DataFrame({"Código CP": df["codigo_cp"].values, "MPa": df["mpa"].values})
    y_max = max(chart_df["MPa"]) * 1.15 if len(chart_df) else 1
    points = (
        alt.Chart(chart_df)
        .mark_point(size=90, filled=True, color=ACCENT)
        .encode(
            x=alt.X("Código CP:N", sort=None, title="Código do CP"),
            y=alt.Y("MPa:Q", scale=alt.Scale(domain=[0, y_max]), title="MPa"),
            tooltip=["Código CP", alt.Tooltip("MPa:Q", format=".3f")]
        ).properties(height=340)
    )
    st.altair_chart(points, use_container_width=True)

    st.divider()

# =================== Ações (regera PNG no export) ===================
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Limpar lote", disabled=(not st.session_state.registros)):
        st.session_state.registros = []; st.session_state.pdf_bytes = None; st.session_state.plot_png = None
        st.success("Lote limpo.")

with col2:
    if st.session_state.registros:
        st.download_button("Baixar CSV",
                           data=pd.DataFrame(st.session_state.registros).to_csv(index=False).encode("utf-8"),
                           file_name="rupturas_lote.csv", mime="text/csv")

with col3:
    disable_pdf = (not st.session_state.registros) or (PDF_BACKEND == "none")
    click = st.button("📄 Exportar para PDF", disabled=disable_pdf, type="primary")
    if click:
        try:
            df_pdf = pd.DataFrame(st.session_state.registros)
            png_now = chart_png_from_df(df_pdf)  # gera PNG do gráfico na hora
            st.session_state.plot_png = png_now
            st.session_state.pdf_bytes = build_pdf(
                st.session_state.obra, st.session_state.data_obra, st.session_state.area_padrao,
                df_pdf, png_now, st.session_state.logo_bytes, st.session_state.footer_text
            )
            if png_now is None:
                st.warning("PDF gerado **sem o gráfico** (plotly/kaleido ausentes). Confira o requirements.txt.")
            else:
                st.success("PDF gerado com gráfico! Baixe abaixo.")
        except Exception as e:
            st.error(f"Falha ao gerar PDF: {e}")

def svg_scatter_from_df(df, width=900, height=360, margin=50):
    """Gera um SVG simples (scatter MPa por CP) sem bibliotecas externas."""
    if df.empty:
        return "<svg width='1' height='1'></svg>"
    codes = [str(x) for x in df["codigo_cp"].tolist()]
    ys    = [float(x) for x in df["mpa"].tolist()]
    y_max = max(ys) * 1.15 if ys else 1.0
    y_min = 0.0

    plot_w = width - margin*2
    plot_h = height - margin*2

    def x_pos(i, n):

# =================== Download do PDF ou Fallback HTML (com gráfico) ===================
if st.session_state.get("pdf_bytes"):
    data_str = st.session_state.data_obra.strftime("%Y%m%d")
    safe_obra = "".join(c for c in st.session_state.obra if c.isalnum() or c in (" ","-","_")).strip().replace(" ","_")
    fname = f"Lote_Rupturas_{safe_obra}_{data_str}.pdf"
    st.download_button("⬇️ Baixar PDF do Lote", data=st.session_state.pdf_bytes,
                       file_name=fname, mime="application/pdf")

elif st.session_state.registros and PDF_BACKEND == "none":
    import base64
    df_html = pd.DataFrame(st.session_state.registros)
    png_now = chart_png_from_df(df_html)

    def build_html(obra, data_obra, area_cm2, df, footer_text, chart_png):
        rows = "".join(
            f"<tr><td>{i+1}</td><td>{r['codigo_cp']}</td><td>{r['carga_kgf']:.3f}</td>"
            f"<td>{r['area_cm2']:.2f}</td><td>{r['kn_cm2']:.4f}</td><td>{r['mpa']:.3f}</td></tr>"
            for i, r in df.iterrows()
        )
        chart_html = ""
        if chart_png:
            b64 = base64.b64encode(chart_png).decode("ascii")
            chart_html = f"""
            <h3 style="margin-top:22px">Gráfico de ruptura (MPa por CP)</h3>
            <img alt="Gráfico de ruptura" src="data:image/png;base64,{b64}"
                 style="max-width:100%;height:auto;border:1px solid #ccc;border-radius:8px"/>
            """
        html = f"""<!doctype html><html><head>
<meta charset="utf-8"><title>Rupturas — {obra}</title>
<style>
body{{font-family:Arial,Helvetica,sans-serif;margin:24px}}
table{{border-collapse:collapse;width:100%;margin-top:12px}}
th,td{{border:1px solid #999;padding:6px;text-align:center}}
thead th{{background:#f2f2f2}}
</style></head><body>
<h2>Rupturas de Argamassa — Lote</h2>
<div>Obra: <b>{obra}</b> | Data: <b>{data_obra.strftime('%d/%m/%Y')}</b> | Área do CP: <b>{area_cm2:.2f} cm²</b></div>
<table>
<thead><tr><th>#</th><th>Código CP</th><th>Carga (kgf)</th><th>Área (cm²)</th><th>kN/cm²</th><th>MPa</th></tr></thead>
<tbody>{rows}</tbody>
</table>
{chart_html}
{('<p>'+footer_text+'</p>') if footer_text.strip() else ''}
</body></html>"""
        return html.encode("utf-8")

    html_bytes = build_html(
        st.session_state.obra, st.session_state.data_obra,
        st.session_state.area_padrao, df_html, st.session_state.footer_text, png_now
    )
    st.download_button("🖨️ Exportar HTML (imprimir em PDF)", data=html_bytes,
                       file_name="rupturas_lote.html", mime="text/html")

# =================== Rodapé / diagnóstico ===================
try:
    import plotly  # noqa: F401
    _img_ok = True
except Exception:
    _img_ok = False

st.caption(
    "Conversões: [kgf/cm²] → kN/cm² (×0,00980665) e MPa (×0,0980665). "
    + (f"PDF via {PDF_BACKEND}" if PDF_BACKEND != "none" else "PDF desativado (instale fpdf2).")
    + (" • Backend de imagem: ✅ plotly/kaleido" if _img_ok else " • Backend de imagem: ❌ indisponível")
)
