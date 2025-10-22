# app.py — Rupturas de Argamassa (Habisolute) — conversões + gráfico + PDF
from __future__ import annotations
import io
from datetime import date
from statistics import mean, pstdev
import subprocess, sys

import streamlit as st
import pandas as pd

# ====== Backends de PDF ======
PDF_BACKEND = "none"  # "reportlab" | "fpdf2" | "none"

def _try_import_pdfs():
    global PDF_BACKEND, A4, SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, colors, getSampleStyleSheet, FPDF
    # 1) tenta ReportLab
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        PDF_BACKEND = "reportlab"
        return
    except Exception:
        pass
    # 2) tenta FPDF2
    try:
        from fpdf import FPDF
        PDF_BACKEND = "fpdf2"
        return
    except Exception:
        PDF_BACKEND = "none"

_try_import_pdfs()

# 3) Se nenhum disponível, instala fpdf2 on-the-fly e tenta de novo
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
st.set_page_config(page_title="Rupturas de Argamassa — Habisolute", page_icon="🧱", layout="centered")

st.markdown(f"""
<style>
:root {{ --brand:{HB_ORANGE}; }}
html, body, [class*="block-container"] {{ background:#0f1116; color:#f5f5f5; }}
h1, h2, h3, h4 {{ color:#fff; }}
.stButton>button {{
  background:var(--brand); color:#111; border:none; border-radius:12px;
  padding:.6rem 1rem; font-weight:700; cursor:pointer;
}}
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
st.caption("Conversões automáticas: **kgf/cm² → kN/cm²** e **kgf/cm² → MPa**. Também aceita **kgf + área (cm²)**.")

# ====================== Helpers / Conversões ======================
KGF_CM2_TO_MPA = 0.0980665       # 1 kgf/cm² = 0,0980665 MPa
KGF_CM2_TO_KN_CM2 = 0.00980665   # 1 kgf/cm² = 0,00980665 kN/cm²

def stress_from_inputs(mode:str, val_kgf_cm2:float|None, carga_kgf:float|None, area_cm2:float|None):
    if mode == "kgf/cm²":
        if val_kgf_cm2 is None:
            return None, None, None
        s_kgf_cm2 = float(val_kgf_cm2)
    else:
        if not carga_kgf or not area_cm2 or area_cm2 <= 0:
            return None, None, None
        s_kgf_cm2 = float(carga_kgf) / float(area_cm2)
    s_kn_cm2 = s_kgf_cm2 * KGF_CM2_TO_KN_CM2
    s_mpa    = s_kgf_cm2 * KGF_CM2_TO_MPA
    return s_kgf_cm2, s_kn_cm2, s_mpa

def _media(lst):
    return None if not lst else mean(lst)

def _dp(lst):
    if not lst: return None
    if len(lst) == 1: return 0.0
    return pstdev(lst)

# ====================== PDF Builder ======================
def build_pdf(obra: str, data_obra: date, df: pd.DataFrame) -> bytes:
    if PDF_BACKEND == "reportlab":
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=24, leftMargin=24, topMargin=28, bottomMargin=28)
        styles = getSampleStyleSheet()
        title = Paragraph("<para align='center'><b>Rupturas de Argamassa — Lote</b></para>", styles["Title"])
        info  = Paragraph(
            f"<para align='center'>Obra: <b>{obra}</b> &nbsp;&nbsp;|&nbsp;&nbsp; Data: <b>{data_obra.strftime('%d/%m/%Y')}</b></para>",
            styles["Normal"]
        )
        data_table = [["#", "Código CP", "Modo entrada", "Entrada", "Área (cm²)", "kgf/cm²", "kN/cm²", "MPa"]]
        for i, row in enumerate(df.itertuples(index=False), start=1):
            entrada_txt = f"{row.carga_kgf_cm2:.3f} kgf/cm²" if row.modo == "kgf/cm²" else f"{row.carga_kgf:.3f} kgf"
            area_txt = "" if row.modo == "kgf/cm²" else f"{row.area_cm2:.2f}"
            data_table.append([i, row.codigo_cp, row.modo, entrada_txt, area_txt,
                               f"{row.kgf_cm2:.3f}", f"{row.kn_cm2:.4f}", f"{row.mpa:.3f}"])
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
        kgf_cm2_list = df["kgf_cm2"].tolist()
        kn_cm2_list  = df["kn_cm2"].tolist()
        mpa_list     = df["mpa"].tolist()
        stats = [
            ["Estatística", "kgf/cm²", "kN/cm²", "MPa"],
            ["Média", f"{_media(kgf_cm2_list):.3f}", f"{_media(kn_cm2_list):.4f}", f"{_media(mpa_list):.3f}"],
            ["DP (pop.)", f"{_dp(kgf_cm2_list):.3f}", f"{_dp(kn_cm2_list):.4f}", f"{_dp(mpa_list):.3f}"],
        ]
        tbl_stats = Table(stats)
        tbl_stats.setStyle(TableStyle([
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
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 7, "Rupturas de Argamassa — Lote", ln=1, align="C")
        pdf.set_font("Arial", size=11)
        pdf.cell(0, 6, f"Obra: {obra}   |   Data: {data_obra.strftime('%d/%m/%Y')}", ln=1, align="C")
        pdf.ln(3)
        headers = ["#", "Código CP", "Modo", "Entrada", "Área", "kgf/cm²", "kN/cm²", "MPa"]
        widths  = [8, 42, 20, 28, 18, 22, 22, 20]
        pdf.set_font("Arial", "B", 10)
        for h, w in zip(headers, widths): pdf.cell(w, 7, h, border=1, align="C")
        pdf.ln(); pdf.set_font("Arial", size=10)
        for i, row in enumerate(df.itertuples(index=False), start=1):
            entrada_txt = f"{row.carga_kgf_cm2:.3f}" if row.modo == "kgf/cm²" else f"{row.carga_kgf:.3f}"
            area_txt    = "" if row.modo == "kgf/cm²" else f"{row.area_cm2:.2f}"
            cells = [str(i), row.codigo_cp, row.modo, entrada_txt, area_txt,
                     f"{row.kgf_cm2:.3f}", f"{row.kn_cm2:.4f}", f"{row.mpa:.3f}"]
            for c, w in zip(cells, widths): pdf.cell(w, 6, c, border=1, align="C")
            pdf.ln()
        kgf_cm2_list = df["kgf_cm2"].tolist()
        kn_cm2_list  = df["kn_cm2"].tolist()
        mpa_list     = df["mpa"].tolist()
        pdf.ln(4); pdf.set_font("Arial", "B", 11); pdf.cell(0, 6, "Resumo estatístico", ln=1)
        pdf.set_font("Arial", size=10)
        def _fmt(x, nd): 
            if x is None: return "-"
            return f"{x:.{nd}f}"
        pdf.cell(40, 6, "Média (kgf/cm²):"); pdf.cell(0, 6, _fmt(_media(kgf_cm2_list), 3), ln=1)
        pdf.cell(40, 6, "Média (kN/cm²):");  pdf.cell(0, 6, _fmt(_media(kn_cm2_list), 4), ln=1)
        pdf.cell(40, 6, "Média (MPa):");     pdf.cell(0, 6, _fmt(_media(mpa_list), 3), ln=1)
        pdf.cell(40, 6, "DP pop. (kgf/cm²):"); pdf.cell(0, 6, _fmt(_dp(kgf_cm2_list), 3), ln=1)
        pdf.cell(40, 6, "DP pop. (kN/cm²):");  pdf.cell(0, 6, _fmt(_dp(kn_cm2_list), 4), ln=1)
        pdf.cell(40, 6, "DP pop. (MPa):");     pdf.cell(0, 6, _fmt(_dp(mpa_list), 3), ln=1)
        buf = io.BytesIO()
        pdf_bytes = pdf.output(dest="S").encode("latin1")
        buf.write(pdf_bytes); buf.seek(0)
        return buf.read()

    # Sem backend de PDF disponível
    raise RuntimeError("Sem backend de PDF disponível (instale reportlab ou fpdf2).")

# ====================== Estado ======================
if "obra" not in st.session_state: st.session_state.obra = ""
if "data_obra" not in st.session_state: st.session_state.data_obra = date.today()
if "registros" not in st.session_state: st.session_state.registros = []
if "lote_fechado" not in st.session_state: st.session_state.lote_fechado = False
if "pdf_bytes" not in st.session_state: st.session_state.pdf_bytes = None

# ====================== Conversor rápido ======================
with st.expander("🔁 Conversor rápido (kgf/cm² → kN/cm² / MPa)", expanded=False):
    v = st.number_input("Valor em kgf/cm²", min_value=0.0, value=0.0, step=0.01, format="%.3f")
    kn_cm2 = v * KGF_CM2_TO_KN_CM2
    mpa    = v * KGF_CM2_TO_MPA
    st.markdown(
        f"""
        <div class="kpi">
          <div><b>Entrada</b><br>{v:.3f} kgf/cm²</div>
          <div><b>kN/cm²</b><br>{kn_cm2:.5f}</div>
          <div><b>MPa</b><br>{mpa:.4f}</div>
        </div>
        <br>
        <small>Fórmulas: kN/cm² = kgf/cm² × 0,00980665 • MPa = kgf/cm² × 0,0980665</small>
        """,
        unsafe_allow_html=True
    )

# Aviso se estiver sem backend de PDF
if PDF_BACKEND == "none":
    st.warning(
        "⚠️ O PDF está desativado neste deploy (bibliotecas ausentes). "
        "Baixe o CSV normalmente. Para ativar o PDF, garanta que **requirements.txt** contenha "
        "`reportlab` **ou** `fpdf2` e reinicie o app."
    )

# ====================== Form Obra ======================
with st.form("obra_form"):
    st.subheader("Dados da obra")
    col1, col2 = st.columns([2,1])
    with col1:
        obra = st.text_input("Nome da obra", value=st.session_state.obra, placeholder="Ex.: Residencial Jardim Tropical")
    with col2:
        data_obra = st.date_input("Data", value=st.session_state.data_obra, format="DD/MM/YYYY")
    submitted_obra = st.form_submit_button("Aplicar dados da obra")
    if submitted_obra:
        st.session_state.obra = obra.strip()
        st.session_state.data_obra = data_obra
        st.success("Dados da obra aplicados.")

# Limite por lote
qtd = len(st.session_state.registros)
st.info(f"CPs no lote atual: **{qtd}/12**")

# ====================== Form Lançamento CP ======================
disabled_add = (qtd >= 12) or st.session_state.lote_fechado or (not st.session_state.obra)

with st.form("cp_form", clear_on_submit=True):
    st.subheader("Lançar ruptura")
    codigo_cp = st.text_input("Código do CP", placeholder="Ex.: A039.258 / H682 / 037.421", max_chars=32)
    modo = st.radio("Modo de entrada da carga", ["kgf/cm²", "kgf + área"], horizontal=True)

    val_kgf_cm2 = None
    carga_kgf, area_cm2 = None, None
    if modo == "kgf/cm²":
        val_kgf_cm2 = st.number_input("Carga em kgf/cm²", min_value=0.0, step=0.01, format="%.3f")
        if val_kgf_cm2 and val_kgf_cm2 > 0:
            _kn = val_kgf_cm2 * KGF_CM2_TO_KN_CM2
            _mp = val_kgf_cm2 * KGF_CM2_TO_MPA
            st.caption(f"→ Conversões: **{val_kgf_cm2:.3f} kgf/cm²** = **{_kn:.5f} kN/cm²** = **{_mp:.4f} MPa**")
    else:
        cols = st.columns(2)
        with cols[0]:
            carga_kgf = st.number_input("Carga em kgf", min_value=0.0, step=0.1, format="%.3f")
        with cols[1]:
            area_cm2 = st.number_input("Área do CP (cm²)", min_value=0.0001, step=0.01, format="%.2f", value=16.00)
        if carga_kgf and area_cm2 and area_cm2 > 0:
            _kgfcm2 = carga_kgf/area_cm2
            _kn = _kgfcm2 * KGF_CM2_TO_KN_CM2
            _mp = _kgfcm2 * KGF_CM2_TO_MPA
            st.caption(f"→ Conversões: **{_kgfcm2:.3f} kgf/cm²** = **{_kn:.5f} kN/cm²** = **{_mp:.4f} MPa**")

    add = st.form_submit_button("Adicionar CP ao lote", disabled=disabled_add)
    if add:
        if not st.session_state.obra:
            st.error("Defina os dados da obra antes de lançar CPs.")
        elif not codigo_cp.strip():
            st.error("Informe o código do CP.")
        else:
            s_kgf_cm2, s_kn_cm2, s_mpa = stress_from_inputs(modo, val_kgf_cm2, carga_kgf, area_cm2)
            if s_kgf_cm2 is None:
                st.error("Verifique os valores informados (carga/área).")
            else:
                st.session_state.registros.append({
                    "codigo_cp": codigo_cp.strip(),
                    "modo": modo,
                    "carga_kgf_cm2": float(val_kgf_cm2) if modo == "kgf/cm²" else None,
                    "carga_kgf": float(carga_kgf) if modo == "kgf + área" else None,
                    "area_cm2": float(area_cm2) if modo == "kgf + área" else None,
                    "kgf_cm2": float(s_kgf_cm2),
                    "kn_cm2": float(s_kn_cm2),
                    "mpa": float(s_kgf_cm2 * KGF_CM2_TO_MPA),
                })
                st.success("CP adicionado ao lote.")

# ====================== Tabela + Gráfico ======================
if st.session_state.registros:
    df = pd.DataFrame(st.session_state.registros)
    df_display = df[["codigo_cp","modo","carga_kgf_cm2","carga_kgf","area_cm2","kgf_cm2","kn_cm2","mpa"]].copy()
    df_display.columns = ["Código CP","Modo","Carga (kgf/cm²)","Carga (kgf)","Área (cm²)","kgf/cm²","kN/cm²","MPa"]

    st.subheader("Lote atual — Tabela de CPs")
    st.dataframe(df_display, use_container_width=True)

    col_a, col_b, col_c = st.columns(3)
    with col_a: st.metric("Média (MPa)", f"{mean(df['mpa']):.3f}")
    with col_b: st.metric("Média (kgf/cm²)", f"{mean(df['kgf_cm2']):.3f}")
    with col_c: st.metric("Média (kN/cm²)", f"{mean(df['kn_cm2']):.4f}")

    # Gráfico nativo (MPa por CP) — começa em 0
    st.subheader("Gráfico de ruptura (MPa por CP)")
    chart_df = pd.DataFrame({"MPa": df["mpa"].values}, index=df["codigo_cp"].values)
    st.bar_chart(chart_df, height=320, use_container_width=True)

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
        csv_bytes = df_csv.to_csv(index=False).encode("utf-8")
        st.download_button("Baixar CSV", data=csv_bytes, file_name="rupturas_lote.csv", mime="text/csv")

with col3:
    can_finish = bool(st.session_state.registros) and (not st.session_state.lote_fechado) and (PDF_BACKEND != "none")
    if st.button("📄 Exportar / Finalizar lote (PDF)", disabled=not can_finish, type="primary"):
        try:
            df_pdf = pd.DataFrame(st.session_state.registros)
            pdf_bytes = build_pdf(st.session_state.obra, st.session_state.data_obra, df_pdf)
            st.session_state.lote_fechado = True
            st.session_state.pdf_bytes = pdf_bytes
            st.success("Lote finalizado. Baixe o PDF abaixo.")
        except Exception as e:
            st.error(f"Falha ao gerar PDF: {e}")

# Download do PDF
if st.session_state.get("pdf_bytes"):
    data_str = st.session_state.data_obra.strftime("%Y%m%d")
    safe_obra = "".join(c for c in st.session_state.obra if c.isalnum() or c in (" ","-","_")).strip().replace(" ","_")
    fname = f"Lote_Rupturas_{safe_obra}_{data_str}.pdf"
    st.download_button("⬇️ Baixar PDF do Lote", data=st.session_state.pdf_bytes, file_name=fname, mime="application/pdf")

# Rodapé
st.caption(
    "Conversões: 1 kgf/cm² = 0,00980665 kN/cm² = 0,0980665 MPa. • "
    + (f"PDF via {PDF_BACKEND}" if PDF_BACKEND != "none" else "PDF desativado (instale reportlab ou fpdf2)")
)
