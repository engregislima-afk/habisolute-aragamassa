# app.py — Sistema de Rupturas de Argamassa (Habisolute) — com CSS discreto
from __future__ import annotations

import math
from datetime import date
from typing import List, Dict, Any

import streamlit as st
import pandas as pd
import altair as alt

APP_TITLE = "🧪Sistema de Rupturas de Argamassa Habisolute"
ACCENT_DEFAULT = "#d75413"  # laranja Habisolute
KGF_CM2_TO_MPA = 0.0980665  # 1 kgf/cm² = 0.0980665 MPa

# -------- Estado --------
st.set_page_config(page_title="Rupturas de Argamassa", page_icon="🧪", layout="wide")

def init_state() -> None:
    s = st.session_state
    s.setdefault("theme", "Claro")
    s.setdefault("obra", "")
    s.setdefault("data_obra", date.today())
    s.setdefault("area_padrao", 16.00)
    s.setdefault("registros", [])
    s.setdefault("data_moldagem", date.today())
    s.setdefault("data_ruptura", date.today())

def style_css() -> None:
    theme = st.session_state.get("theme", "Claro")
    IS_DARK = (theme == "Escuro")

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

    st.markdown(f"""
    <style>
    @media (min-width: 1400px) {{
      .block-container {{ max-width: 1600px !important; }}
    }}
    html, body, [class*="block-container"] {{
      background: {SURFACE} !important;
      color: {TEXT} !important;
      font-family: "Segoe UI Variable Text","Segoe UI",system-ui,-apple-system,Roboto,Arial,"Noto Sans",sans-serif !important;
      letter-spacing: .2px;
    }}
    [class*="block-container"] {{ padding-top: 1.4rem; }}
    div[data-testid="stSidebar"] {{
      background: {SIDEBAR_BG} !important;
      border-right: 1px solid rgba(0,0,0,.10) !important;
    }}
    div[data-testid="stSidebar"] * {{ color: {SIDEBAR_TEXT} !important; }}
    div[data-testid="stSidebar"] [data-baseweb="radio"] label,
    div[data-testid="stSidebar"] [data-baseweb="radio"] span {{ font-weight: 600; }}
    .hab-card{{
      background:{CARD};
      border:1px solid {BORDER};
      border-radius:16px;
      box-shadow: 0 12px 28px rgba(16,24,40,.10);
      padding:.9rem;
      margin:.6rem 0 1rem 0;
    }}
    /* Inputs base */
    input, textarea, select {{
      color: {INPUT_TEXT} !important;
      background: {INPUT_BG} !important;
      border: 1px solid {INPUT_BDR} !important;
      border-radius: 12px !important;
    }}
    /* Botões laranja com texto preto */
    .stButton>button, .stDownloadButton>button,
    div[data-testid="stForm"] .stButton>button {{
      background: {ACCENT_DEFAULT} !important;
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
    </style>
    """, unsafe_allow_html=True)
    st.markdown("""
<style>
/* TÍTULO 100% PRETO */
h1#app-title, h1#app-title *{
  color:#111111 !important; opacity:1 !important; text-shadow:none !important;
  -webkit-text-fill-color:#111111 !important;
}
/* Topo/toolbar do Streamlit mais discreto (no CLARO) */
html:root:not(.dark) div[data-testid="stHeader"]{ background:transparent !important; box-shadow:none !important; }
div[data-testid="stToolbar"]{ opacity:.28 !important; filter:saturate(.6) !important; transition:opacity .18s, filter .18s; }
div[data-testid="stToolbar"]:hover{ opacity:.92 !important; filter:none !important; }
header, .stApp header, div[data-testid="stHeader"]>*{ background:transparent !important; box-shadow:none !important; }

/* Inputs mais discretos no CLARO */
html:root:not(.dark) label, html:root:not(.dark) legend{ color:#111111 !important; opacity:.9 !important; }
html:root:not(.dark) .stTextInput input,
html:root:not(.dark) .stNumberInput input,
html:root:not(.dark) .stDateInput input,
html:root:not(.dark) textarea, html:root:not(.dark) select{
  background:#ffffff !important; color:#111111 !important; border:1px solid #d1d5db !important; border-radius:12px !important; box-shadow:none !important;
}
html:root:not(.dark) ::placeholder{ color:rgba(17,19,24,.45) !important; }
html:root:not(.dark) .stTextInput input:focus,
html:root:not(.dark) .stNumberInput input:focus,
html:root:not(.dark) .stDateInput input:focus,
html:root:not(.dark) textarea:focus, html:root:not(.dark) select:focus{
  border-color:#d75413 !important; outline:none !important; box-shadow:0 0 0 2px rgba(215,84,19,.12) !important;
}
</style>
""", unsafe_allow_html=True)

    # ---- PATCHES pedidos: título preto, toolbar discreta, inputs “clean” no claro ----
    st.markdown("""
    <style>
    /* 1) TÍTULO 100% PRETO, SEM DESBOTAR */
    h1#app-title, h1#app-title * {
      color:#111111 !important;
      opacity:1 !important;
      text-shadow:none !important;
      -webkit-text-fill-color:#111111 !important;
    }
    /* 2) TOPO DO STREAMLIT DISCRETO */
    html:root:not(.dark) div[data-testid="stHeader"] { background: transparent !important; box-shadow: none !important; }
    div[data-testid="stToolbar"] { opacity:.28 !important; filter:saturate(.6) !important; transition: opacity .18s ease, filter .18s ease; }
    div[data-testid="stToolbar"]:hover { opacity:.92 !important; filter:none !important; }
    header, .stApp header, div[data-testid="stHeader"] > * {
      background: transparent !important; box-shadow: none !important;
    }
    /* 3) INPUTS MAIS DISCRETOS (MODO CLARO) */
    html:root:not(.dark) label, html:root:not(.dark) legend { color:#111111 !important; opacity:.9 !important; }
    html:root:not(.dark) .stTextInput input,
    html:root:not(.dark) .stNumberInput input,
    html:root:not(.dark) .stDateInput input,
    html:root:not(.dark) textarea,
    html:root:not(.dark) select {
      background:#ffffff !important;
      color:#111111 !important;
      border:1px solid #d1d5db !important;
      border-radius:12px !important;
      box-shadow:none !important;
    }
    html:root:not(.dark) ::placeholder { color: rgba(17,19,24,.45) !important; }
    html:root:not(.dark) .stTextInput input:focus,
    html:root:not(.dark) .stNumberInput input:focus,
    html:root:not(.dark) .stDateInput input:focus,
    html:root:not(.dark) textarea:focus,
    html:root:not(.dark) select:focus {
      border-color:#d75413 !important;
      outline: none !important;
      box-shadow: 0 0 0 2px rgba(215,84,19,.12) !important;
    }
    html:root:not(.dark) div[data-testid="stForm"],
    html:root:not(.dark) .stDataFrame { border:1px solid rgba(0,0,0,.10) !important; }
    /* Ajustes de respiro no topo e título */
    [class*="block-container"]{ padding-top: 2.2rem !important; }
    h1#app-title{ margin-top: .6rem !important; margin-bottom: .35rem !important; }
    </style>
    """, unsafe_allow_html=True)

def calc_from_kgf(carga_kgf: float, area_cm2: float) -> Dict[str, float]:
    if area_cm2 <= 0:
        return {"kgf_cm2": float("nan"), "mpa": float("nan")}
    kgf_cm2 = float(carga_kgf) / float(area_cm2)
    mpa = kgf_cm2 * KGF_CM2_TO_MPA
    return {"kgf_cm2": kgf_cm2, "mpa": mpa}

def df_lote() -> pd.DataFrame:
    s = st.session_state
    if not s.registros:
        return pd.DataFrame(columns=["codigo_cp", "carga_kgf", "area_cm2", "kgf_cm2", "mpa"])
    df = pd.DataFrame(s.registros)
    df["codigo_cp"] = df["codigo_cp"].astype(str)
    df["carga_kgf"] = pd.to_numeric(df["carga_kgf"], errors="coerce")
    df["area_cm2"]  = pd.to_numeric(df["area_cm2"], errors="coerce")
    df["kgf_cm2"]   = pd.to_numeric(df["kgf_cm2"], errors="coerce")
    df["mpa"]       = pd.to_numeric(df["mpa"], errors="coerce")
    return df

def header() -> None:
    st.markdown(f"<h1 id='app-title' style='margin:0'>{APP_TITLE}</h1>", unsafe_allow_html=True)
    st.caption("Entrada: carga (kgf) • Saídas: kN/cm² e MPa • Exportação CSV/Excel")

    with st.sidebar:
        st.markdown(f"<h2 style='margin-top:0;color:{ACCENT_DEFAULT}'>Preferências</h2>", unsafe_allow_html=True)
        st.session_state.theme = st.radio(
            "Tema", ["Escuro", "Claro"],
            horizontal=True,
            index=1 if st.session_state.theme == "Claro" else 0,
            key="pref_tema"
        )

def bloco_converter() -> None:
    with st.expander("🔁 Conversor rápido (kgf → MPa)", expanded=False):
        c1,c2 = st.columns(2)
        kgf = c1.number_input("Carga (kgf)", min_value=0.0, value=0.0, step=0.1, format="%.3f", key="conv_carga_kgf")
        area_demo = c2.number_input("Área (cm²)", min_value=0.0001, value=float(st.session_state.area_padrao), step=0.01, format="%.2f", key="conv_area")
        if kgf and area_demo:
            res = calc_from_kgf(kgf, area_demo)
            c3, c4 = st.columns(2)
            with c3: st.metric("kgf/cm²", f"{res['kgf_cm2']:.5f}")
            with c4: st.metric("MPa", f"{res['mpa']:.4f}")

def bloco_obra() -> None:
    with st.form("obra_form"):
        st.subheader("✅Dados da obra")
        a,b,c = st.columns([2,1,1])
        obra = a.text_input("Nome da obra", st.session_state.obra, placeholder="Ex.: Residencial Jardim Tropical", key="obra_nome")
        data_obra = b.date_input("Data", st.session_state.data_obra, format="DD/MM/YYYY", key="obra_data")
        area_padrao = c.number_input("Área do CP (cm²)", min_value=0.0001, value=float(st.session_state.area_padrao), step=0.01, format="%.2f", key="obra_area")
        d,e,f = st.columns([1,1,1])
        data_mold = d.date_input("Data de moldagem", st.session_state.data_moldagem, format="DD/MM/YYYY", key="obra_mold")
        data_rupt = e.date_input("Data de ruptura",  st.session_state.data_ruptura,  format="DD/MM/YYYY", key="obra_rupt")
        idade = max(0, (data_rupt - data_mold).days)
        f.number_input("Idade de ruptura (dias)", value=idade, disabled=True, key="obra_idade_readonly")

        col = st.columns([1,1,2])
        apply_clicked  = col[0].form_submit_button("Aplicar")
        recalc_clicked = col[1].form_submit_button("Recalcular lote com nova área", disabled=(not st.session_state.registros))

        if apply_clicked:
            st.session_state.obra = obra.strip()
            st.session_state.data_obra = data_obra
            st.session_state.area_padrao = float(area_padrao)
            st.session_state.data_moldagem = data_mold
            st.session_state.data_ruptura  = data_rupt
            st.success("Dados aplicados.")

        if recalc_clicked and st.session_state.registros:
            nova_area = float(area_padrao)
            for r in st.session_state.registros:
                conv = calc_from_kgf(r["carga_kgf"], nova_area)
                r["area_cm2"] = nova_area
                r["kgf_cm2"] = conv["kgf_cm2"]
                r["mpa"] = conv["mpa"]
            st.session_state.area_padrao = nova_area
            st.success("Todos os CPs recalculados com a nova área.")

def bloco_lancar_cp() -> None:
    st.info(f"CPs no lote: **{len(st.session_state.registros)}/12**")
    with st.form("cp_form", clear_on_submit=True):
        st.subheader("✅Lançar ruptura (apenas kgf)")
        codigo = st.text_input("Código do CP", max_chars=32, placeholder="Ex.: A039.258 / H682 / 037.421", key="cp_codigo")
        carga  = st.number_input("Carga de ruptura (kgf)", min_value=0.0, step=0.1, format="%.3f", key="cp_carga")
        if carga and st.session_state.area_padrao:
            conv = calc_from_kgf(carga, st.session_state.area_padrao)
            st.caption(f"→ Conversões (área {st.session_state.area_padrao:.2f} cm²): **{conv['kgf_cm2']:.5f} kgf/cm²** • **{conv['mpa']:.4f} MPa**")
        ok = st.form_submit_button("Adicionar CP", disabled=(len(st.session_state.registros)>=12))
        if ok:
            if not st.session_state.obra: st.error("Preencha os dados da obra.")
            elif not codigo.strip():      st.error("Informe o código do CP.")
            elif carga <= 0:              st.error("Informe uma carga > 0.")
            else:
                conv = calc_from_kgf(carga, st.session_state.area_padrao)
                st.session_state.registros.append({
                    "codigo_cp": codigo.strip(),
                    "carga_kgf": float(carga),
                    "area_cm2": float(st.session_state.area_padrao),
                    "kgf_cm2": float(conv["kgf_cm2"]),
                    "mpa":     float(conv["mpa"]),
                    "data_moldagem": st.session_state.data_moldagem.isoformat(),
                    "data_ruptura":  st.session_state.data_ruptura.isoformat(),
                    "idade_dias":    max(0, (st.session_state.data_ruptura - st.session_state.data_moldagem).days),
                })
                st.success("CP adicionado.")
def df_lote() -> pd.DataFrame:
    s = st.session_state
    if not s.registros:
        return pd.DataFrame(columns=["codigo_cp", "carga_kgf", "area_cm2", "kgf_cm2", "mpa", "data_moldagem", "data_ruptura", "idade_dias"])
    df = pd.DataFrame(s.registros)
    df["codigo_cp"] = df["codigo_cp"].astype(str)
    df["carga_kgf"] = pd.to_numeric(df["carga_kgf"], errors="coerce")
    df["area_cm2"]  = pd.to_numeric(df["area_cm2"], errors="coerce")
    df["kgf_cm2"]   = pd.to_numeric(df["kgf_cm2"], errors="coerce")
    df["mpa"]       = pd.to_numeric(df["mpa"], errors="coerce")
    return df

def bloco_tabela() -> None:
    df = df_lote()
    if df.empty:
        st.info("Nenhum CP lançado ainda. Adicione registros para visualizar tabela e gráfico.")
        return
    st.subheader("📋Lote atual (editável)")
    edited = st.data_editor(
        df[["codigo_cp","carga_kgf","area_cm2","kgf_cm2","mpa","data_moldagem","data_ruptura","idade_dias"]],
        use_container_width=True, num_rows="fixed",
        column_config={
            "codigo_cp": st.column_config.TextColumn("Código CP"),
            "carga_kgf": st.column_config.NumberColumn("Carga (kgf)", step=0.1, format="%.3f"),
            "area_cm2":  st.column_config.NumberColumn("Área (cm²)", disabled=True, format="%.2f"),
            "kgf_cm2":   st.column_config.NumberColumn("kgf/cm²", disabled=True, format="%.5f"),
            "mpa":       st.column_config.NumberColumn("MPa", disabled=True, format="%.4f"),
            "data_moldagem": st.column_config.TextColumn("Data moldagem", disabled=True),
            "data_ruptura":  st.column_config.TextColumn("Data ruptura", disabled=True),
            "idade_dias":    st.column_config.NumberColumn("Idade (dias)", disabled=True),
        },
        key="lote_editor"
    )
    if not edited.equals(df[edited.columns]):
        new_regs = []
        for row in edited.itertuples(index=False):
            conv = calc_from_kgf(float(row.carga_kgf), float(row.area_cm2))
            new_regs.append({
                "codigo_cp": str(row.codigo_cp),
                "carga_kgf": float(row.carga_kgf),
                "area_cm2":  float(row.area_cm2),
                "kgf_cm2":   float(conv["kgf_cm2"]),
                "mpa":       float(conv["mpa"]),
                "data_moldagem": str(row.data_moldagem),
                "data_ruptura":  str(row.data_ruptura),
                "idade_dias":    int(row.idade_dias),
            })
        st.session_state.registros = new_regs

    df = df_lote()
    if not df.empty:
        a,b = st.columns(2)
        a.metric("Média (MPa)", f"{pd.to_numeric(df['mpa']).mean():.3f}")
        b.metric("Nº de CPs", f"{len(df)}")

    c1, c2 = st.columns([1,1])
    with c1:
        st.download_button("Baixar CSV", df.to_csv(index=False).encode("utf-8"), "lote.csv", "text/csv", key="dl_csv")
    with c2:
        from io import BytesIO
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Lote")
        st.download_button("Baixar Excel", buf.getvalue(), "lote.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_xlsx")

def bloco_grafico() -> None:
    df = df_lote()
    if df.empty:
        return
    st.subheader("📈Gráfico de ruptura (MPa por CP)")
    chart_df = (
        pd.DataFrame({
            "Código CP": df["codigo_cp"].astype(str).values,
            "MPa":       pd.to_numeric(df["mpa"], errors="coerce").values
        })
        .dropna(subset=["MPa"])
        .reset_index(drop=False)
        .rename(columns={"index": "rowid"})
    )
    theme = st.session_state.get("theme", "Claro")
    bg         = "#0f1115" if theme == "Escuro" else "#ffffff"
    axis_color = "#e8eaed" if theme == "Escuro" else "#111318"
    grid_color = "rgba(255,255,255,0.22)" if theme == "Escuro" else "#e5e7eb"
    y_max = float(chart_df["MPa"].max() * 1.15) if len(chart_df) else 1.0

    points = (
        alt.Chart(chart_df, background=bg)
          .transform_window(dup_index='rank()', groupby=['Código CP'])
          .transform_joinaggregate(total='count()', groupby=['Código CP'])
          .transform_calculate(offset='(datum.dup_index - (datum.total + 1)/2) * 10')
          .mark_point(size=110, filled=True, color=ACCENT_DEFAULT, opacity=0.95)
          .encode(
              x=alt.X('Código CP:N', title='Código do CP', sort=None, axis=alt.Axis(labelAngle=0)),
              xOffset='offset:Q',
              y=alt.Y('MPa:Q', scale=alt.Scale(domain=[0, y_max]), title='MPa'),
              tooltip=[alt.Tooltip('Código CP:N', title='Código CP'),
                       alt.Tooltip('MPa:Q', format='.3f')]
          )
          .properties(height=360, padding={"left":10,"right":10,"top":10,"bottom":10},
                      title='Gráfico de ruptura (MPa por CP)')
          .configure_axis(labelColor=axis_color, titleColor=axis_color,
                          gridColor=grid_color, domainColor=axis_color)
          .configure_title(color=axis_color)
          .configure_view(stroke='transparent')
    )
    st.altair_chart(points, use_container_width=True)
    st.divider()

def main():
    init_state()
    style_css()
    header()
    bloco_converter()
    bloco_obra()
    bloco_lancar_cp()
    bloco_tabela()
    bloco_grafico()

if __name__ == "__main__":
    main()
