
# app.py — Rupturas de Argamassa (entrada só kgf; saídas kN/cm² e MPa)
from __future__ import annotations
import io
from datetime import date
from statistics import mean, pstdev
import subprocess, sys

import streamlit as st
import pandas as pd
import altair as alt

# ====================== PDF backends (ReportLab -> FPDF2; tenta auto-instalar fpdf2) ======================
PDF_BACKEND = "none"  # "reportlab" | "fpdf2" | "none"

def _try_import_pdfs():
    global PDF_BACKEND, A4, SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, colors, getSampleStyleSheet, FPDF
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        PDF_BACKEND = "reportlab"
        return
    except Exception:
        pass
    try:
        from fpdf import FPDF
        PDF_BACKEND = "fpdf2"
        return
    except Exception:
        PDF_BACKEND = "none"

_try_import_pdfs()
if PDF_BACKEND == "none":
    try:
        st.info("Instalando backend de PDF (fpdf2)...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "fpdf2>=2.7"])
        from fpdf import FPDF
        PDF_BACKEND = "fpdf2"
        st.success("PDF habilitado com fpdf2.")
    except Exception:
        PDF_BACKEND = "none"

# ====================== Config & Estilo ======================
HB_ORANGE = "#f97316"
st.set_page_config(page_title="Rupturas de Argamassa", page_icon="🧱", layout="centered")
st.markdown(f"""
<style>
:root {{ --brand:{HB_ORANGE}; }}
html, body, [class*="block-container"] {{ background:#0f1116; color:#f5f5f5; }}
h1, h2, h3, h4 {{ color:#fff; }}
.stButton>button {{ background:var(--brand); color:#111; border:none; border-radius:12px;
  padding:.6rem 1rem; font-weight:700; cursor:pointer; }}
.stButton>button:disabled {{ opacity:.5; cursor:not-allowed; }}
.stDownloadButton>button {{ background:#1f2533; color:#fff; border:1px solid #2a3142; border-radius:12px; }}
div[data-testid="stForm"] {{ border:1px solid #2a3142; border-radius:14px; padding:1rem; background:#141821; }}
table td, table th {{ color:#eee; }}
hr {{ border-color:#2a3142; }}
.kpi {{ display:flex; gap:12px; flex-wrap:wrap }}
.kpi > div {{ background:#141821; border:1px solid #2a3142; border-radius:12px; padding:.75rem 1rem; }}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1>Rupturas de Argamassa</h1>", unsafe_allow_html=True)
st.caption("Entrada por CP: **carga de ruptura (kgf)**. Área do CP por obra. Saídas: **kN/cm²** e **MPa**.")

# ====================== Conversões ======================
KGF_CM2_TO_MPA    = 0.0980665
KGF_CM2_TO_KN_CM2 = 0.00980665

# ====================== Estado (INICIALIZE ANTES DE USAR) ======================
if "obra" not in st.session_state: st.session_state.obra = ""
if "data_obra" not in st.session_state: st.session_state.data_obra = date.today()
if "area_padrao" not in st.session_state: st.session_state.area_padrao = 16.00  # cm²
if "registros" not in st.session_state: st.session_state.registros = []
if "lote_fechado" not in st.session_state: st.session_state.lote_fechado = False
if "pdf_bytes" not in st.session_state: st.session_state.pdf_bytes = None

# ====================== Helpers ======================
def tensoes_from_kgf(carga_kgf: float, area_cm2: float):
    if area_cm2 <= 0:
        return None, None, None
    stress_kgf_cm2 = carga_kgf / area_cm2
    kn_cm2 = stress_kgf_cm2 * KGF_CM2_TO_KN_CM2
    mpa    = stress_kgf_cm2 * KGF_CM2_TO_MPA
    return stress_kgf_cm2, kn_cm2, mpa

def _media(lst):
    return None if not lst else mean(lst)

def _dp(lst):
    if not lst: return None
    if len(lst) == 1: return 0.0
    return pstdev(lst)

# ====================== PDF / HTML Builders ======================
def build_pdf(obra: str, data_obra: date, area_cm2: float, df: pd.DataFrame) -> bytes:
    if PDF_BACKEND == "reportlab":
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=24, leftMargin=24, topMargin=28, bottomMargin=28)
        styles = getSampleStyleSheet()
        title = Paragraph("<para align='center'><b>Rupturas de Argamassa — Lote</b></para>", styles["Title"])
        info  = Paragraph(
            f"<para align='center'>Obra: <b>{obra}</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Data: <b>{data_obra.strftime('%d/%m/%Y')}</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Área do CP: <b>{area_cm2:.2f} cm²</b></para>",
            styles["Normal"]
        )
        data_table = [["#", "Código CP", "Carga (kgf)", "Área (cm²)", "kN/cm²", "MPa"]]
        for i, row in enumerate(df.itertuples(index=False), start=1):
            data_table.append([i, row.codigo_cp, f"{row.carga_kgf:.3f}", f"{row.area_cm2:.2f}",
                               f"{row.kn_cm2:.4f}", f"{row.mpa:.3f}"])
        tbl = Table(data_table, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor(HB_ORANGE)),
            ("TEXTCOLOR", (0,0), (-1,0), colors.black),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("ALIGN", (0,0), (-1,0), "CENTER"),
            ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
            ("ALIGN", (0,1), (-1,-1), "CENTER"),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.whitesmoke, colors.HexColor("#f2f2f2")]),
        ]))
        kn_list  = df["kn_cm2"].tolist()
        mpa_list = df["mpa"].tolist()
        stats = [
            ["Estatística", "kN/cm²", "MPa"],
            ["Média", f"{_media(kn_list):.4f}", f"{_media(mpa_list):.3f}"],
            ["DP (pop.)", f"{_dp(kn_list):.4f}", f"{_dp(mpa_list):.3f}"],
        ]
        from reportlab.platypus import Table as T2, TableStyle as TS2, Paragraph
        tbl_stats = T2(stats)
        tbl_stats.setStyle(TS2([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#e5e7eb")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.black),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
        ]))
        elems = [title, Spacer(1,8), info, Spacer(1,12), tbl, Spacer(1,16),
                 Paragraph("<b>Resumo estatístico</b>", styles["Heading3"]),
                 Spacer(1,6), tbl_stats]
        doc.build(elems)
        buffer.seek(0)
        return buffer.read()

    if PDF_BACKEND == "fpdf2":
        from fpdf import FPDF
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.add_page()
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
            cells = [str(i), row.codigo_cp, f"{row.carga_kgf:.3f}", f"{row.area_cm2:.2f}",
                     f"{row.kn_cm2:.4f}", f"{row.mpa:.3f}"]
            for c, w in zip(cells, widths): pdf.cell(w, 6, c, border=1, align="C")
            pdf.ln()
        kn_list  = df["kn_cm2"].tolist(); mpa_list = df["mpa"].tolist()
        pdf.ln(4); pdf.set_font("Arial", "B", 11); pdf.cell(0, 6, "Resumo estatístico", ln=1)
        pdf.set_font("Arial", size=10)
        def _fmt(x, nd): return "-" if x is None else f"{x:.{nd}f}"
        pdf.cell(40, 6, "Média (kN/cm²):"); pdf.cell(0, 6, _fmt(_media(kn_list), 4), ln=1)
        pdf.cell(40, 6, "Média (MPa):");    pdf.cell(0, 6, _fmt(_media(mpa_list), 3), ln=1)
        pdf.cell(40, 6, "DP pop. (kN/cm²):"); pdf.cell(0, 6, _fmt(_dp(kn_list), 4), ln=1)
        pdf.cell(40, 6, "DP pop. (MPa):");    pdf.cell(0, 6, _fmt(_dp(mpa_list), 3), ln=1)
        out = pdf.output(dest="S").encode("latin1")
        return out

    raise RuntimeError("Sem backend de PDF disponível.")

def build_html(obra, data_obra, area_cm2, df):
    rows = "".join(
        f"<tr><td>{i+1}</td><td>{r['codigo_cp']}</td><td>{r['carga_kgf']:.3f}</td>"
        f"<td>{r['area_cm2']:.2f}</td><td>{r['kn_cm2']:.4f}</td><td>{r['mpa']:.3f}</td></tr>"
        for i, r in df.iterrows()
    )
    html = f"""<!doctype html><html><head>
<meta charset="utf-8">
<title>Rupturas — {obra}</title>
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
</body></html>"""
    return html.encode("utf-8")

# ====================== Conversor rápido ======================
with st.expander("🔁 Conversor rápido (kgf → kN/cm² / MPa)", expanded=False):
    colc, cola = st.columns([1,1])
    with colc:
        v_kgf = st.number_input("Carga (kgf)", min_value=0.0, value=0.0, step=0.1, format="%.3f")
    with cola:
        area_demo = st.number_input("Área (cm²) p/ conversão", min_value=0.0001, value=st.session_state.area_padrao, step=0.01, format="%.2f")
    if v_kgf and area_demo:
        _, kn_demo, mpa_demo = tensoes_from_kgf(v_kgf, area_demo)
        st.markdown(
            f"""
            <div class="kpi">
              <div><b>Entrada</b><br>{v_kgf:.3f} kgf</div>
              <div><b>Área</b><br>{area_demo:.2f} cm²</div>
              <div><b>kN/cm²</b><br>{kn_demo:.5f}</div>
              <div><b>MPa</b><br>{mpa_demo:.4f}</div>
            </div>
            """, unsafe_allow_html=True
        )

# ====================== Form Obra ======================
with st.form("obra_form"):
    st.subheader("Dados da obra")
    col1, col2, col3 = st.columns([2,1,1])
    with col1:
        obra = st.text_input("Nome da obra", value=st.session_state.obra, placeholder="Ex.: Residencial Jardim Tropical")
    with col2:
        data_obra = st.date_input("Data", value=st.session_state.data_obra, format="DD/MM/YYYY")
    with col3:
        area_padrao = st.number_input("Área do CP (cm²)", min_value=0.0001, value=float(st.session_state.area_padrao), step=0.01, format="%.2f")
    if st.form_submit_button("Aplicar dados da obra"):
        st.session_state.obra = obra.strip()
        st.session_state.data_obra = data_obra
        st.session_state.area_padrao = float(area_padrao)
        st.success("Dados da obra aplicados.")

# Limite por lote
qtd = len(st.session_state.registros)
st.info(f"CPs no lote atual: **{qtd}/12**")

# ====================== Lançamento CP ======================
disabled_add = (qtd >= 12) or (not st.session_state.obra)

with st.form("cp_form", clear_on_submit=True):
    st.subheader("Lançar ruptura (apenas carga em kgf)")
    codigo_cp = st.text_input("Código do CP", placeholder="Ex.: A039.258 / H682 / 037.421", max_chars=32)
    carga_kgf  = st.number_input("Carga de ruptura (kgf)", min_value=0.0, step=0.1, format="%.3f")
    if carga_kgf and st.session_state.area_padrao:
        _, _kn_prev, _mp_prev = tensoes_from_kgf(carga_kgf, st.session_state.area_padrao)
        st.caption(f"→ Conversões com área {st.session_state.area_padrao:.2f} cm²: "
                   f"**{_kn_prev:.5f} kN/cm²** • **{_mp_prev:.4f} MPa**")
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
                "kgf_cm2": float(s_kgfcm2),  # guardado, não exibido
                "kn_cm2":  float(s_kncm2),
                "mpa":     float(s_mpa),
            })
            st.success("CP adicionado ao lote.")

# ====================== Tabela + Gráfico ======================
if st.session_state.registros:
    df = pd.DataFrame(st.session_state.registros)
    df_display = df[["codigo_cp","carga_kgf","area_cm2","kn_cm2","mpa"]].copy()
    df_display.columns = ["Código CP","Carga (kgf)","Área (cm²)","kN/cm²","MPa"]
    st.subheader("Lote atual — Tabela de CPs")
    st.dataframe(df_display, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a: st.metric("Média (kN/cm²)", f"{mean(df['kn_cm2']):.4f}")
    with col_b: st.metric("Média (MPa)",    f"{mean(df['mpa']):.3f}")

    st.subheader("Gráfico de ruptura (MPa por CP)")
    chart_df = pd.DataFrame({"Código CP": df["codigo_cp"].values, "MPa": df["mpa"].values})
    y_max = max(chart_df["MPa"]) * 1.15 if len(chart_df) else 1
    line = (
        alt.Chart(chart_df)
        .mark_line(point=True)
        .encode(
            x=alt.X("Código CP:N", sort=None, title="Código do CP"),
            y=alt.Y("MPa:Q", scale=alt.Scale(domain=[0, y_max]), title="MPa"),
            tooltip=["Código CP", alt.Tooltip("MPa:Q", format=".3f")]
        )
        .properties(height=320)
    )
    st.altair_chart(line, use_container_width=True)
    st.divider()

# ====================== Ações de Lote ======================
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Limpar lote", disabled=(not st.session_state.registros)):
        st.session_state.registros = []
        st.session_state.lote_fechado = False
        st.session_state.pdf_bytes = None
        st.success("Lote limpo.")
with col2:
    if st.session_state.registros:
        df_csv = pd.DataFrame(st.session_state.registros)
        st.download_button("Baixar CSV", data=df_csv.to_csv(index=False).encode("utf-8"),
                           file_name="rupturas_lote.csv", mime="text/csv")
with col3:
    disable_pdf = (not st.session_state.registros) or (PDF_BACKEND == "none")
    if st.button("📄 Exportar para PDF", disabled=disable_pdf, type="primary"):
        try:
            df_pdf = pd.DataFrame(st.session_state.registros)
            st.session_state.pdf_bytes = build_pdf(
                st.session_state.obra, st.session_state.data_obra, st.session_state.area_padrao, df_pdf
            )
            st.success("PDF gerado! Baixe abaixo.")
        except Exception as e:
            st.error(f"Falha ao gerar PDF: {e}")

# Download do PDF / Fallback HTML
if st.session_state.get("pdf_bytes"):
    data_str = st.session_state.data_obra.strftime("%Y%m%d")
    safe_obra = "".join(c for c in st.session_state.obra if c.isalnum() or c in (" ","-","_")).strip().replace(" ","_")
    fname = f"Lote_Rupturas_{safe_obra}_{data_str}.pdf"
    st.download_button("⬇️ Baixar PDF do Lote", data=st.session_state.pdf_bytes,
                       file_name=fname, mime="application/pdf")
elif st.session_state.registros and PDF_BACKEND == "none":
    # Fallback: exportar HTML imprimível
    df_html = pd.DataFrame(st.session_state.registros)
    html_bytes = build_html(st.session_state.obra, st.session_state.data_obra,
                            st.session_state.area_padrao, df_html)
    st.download_button("🖨️ Exportar HTML (imprimir em PDF)", data=html_bytes,
                       file_name="rupturas_lote.html", mime="text/html")

# Rodapé / diagnóstico
st.caption(
    "Conversões: tensão [kgf/cm²] → kN/cm² (×0,00980665) e MPa (×0,0980665). "
    + (f"PDF via {PDF_BACKEND}" if PDF_BACKEND != "none" else "PDF desativado (instale fpdf2).")
)
st.caption(f"Status do backend PDF: **{PDF_BACKEND}**")
