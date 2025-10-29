# app.py — Sistema de Rupturas de Argamassa (Habisolute) — versão compacta e estável
from __future__ import annotations

import math
from datetime import date, datetime
from typing import List, Dict, Any

import streamlit as st
import pandas as pd
import altair as alt

# ============================
# Utilidades e constantes
# ============================

APP_TITLE = "Sistema de Ruptura de Argamassa Habisolute"
ACCENT_DEFAULT = "#f97316"  # laranja Habisolute
KGF_CM2_TO_MPA = 0.0980665  # 1 kgf/cm² = 0.0980665 MPa

def init_state() -> None:
    s = st.session_state
    if "theme" not in s:
        s.theme = "Escuro"   # "Escuro" | "Claro"
    if "accent_color" not in s:
        s.accent_color = ACCENT_DEFAULT
    if "obra" not in s:
        s.obra = {
            "nome_obra": "TRIADE",
            "data_moldagem": date.today(),
            "data": date.today(),
            "data_ruptura": date.today(),
            "idade_dias": 28,
            "area_cm2": 16.00,
        }
    if "lote" not in s:
        s.lote: List[Dict[str, Any]] = []
    if "wide_layout" not in s:
        s.wide_layout = True

def style_css() -> None:
    accent = st.session_state.get("accent_color", ACCENT_DEFAULT)
    theme_name = st.session_state.get("theme", "Escuro")
    # fundos
    page_bg = "#0b0e14" if theme_name == "Escuro" else "#ffffff"
    text_color = "#eef2f7" if theme_name == "Escuro" else "#111111"
    card_bg = "#121723" if theme_name == "Escuro" else "#f8fafc"
    border = "#1f2937" if theme_name == "Escuro" else "#e5e7eb"
    st.markdown(
        f"""
        <style>
        .block-container{{max-width:1800px; padding-top:1.2rem; padding-bottom:2rem;}}
        html, body, [class^="stApp"]{{
            background:{page_bg};
            color:{text_color};
        }}
        .hab-card{{
            background:{card_bg};
            border:1px solid {border};
            border-radius:16px;
            padding:16px 18px;
            margin:8px 0 14px 0;
        }}
        .hab-title{{
            font-size:26px; font-weight:700; margin:0 0 8px 0; color:{text_color};
        }}
        .hab-sub{{
            font-size:14px; opacity:.85; margin-bottom:10px;
        }}
        .hab-btn .stButton>button{{
            background:{accent} !important;
            color:#111111 !important;
            border:1px solid #11111122;
            border-radius:10px; padding:8px 14px; font-weight:700;
        }}
        .hab-btn .stButton>button:hover{{ filter:brightness(0.95); }}
        </style>
        """,
        unsafe_allow_html=True,
    )

def calc_from_kgf(carga_kgf: float, area_cm2: float) -> Dict[str, float]:
    """Retorna kgf/cm² e MPa a partir de carga (kgf) e área (cm²)."""
    if area_cm2 <= 0:
        return {"kgf_cm2": float("nan"), "mpa": float("nan")}
    kgf_cm2 = float(carga_kgf) / float(area_cm2)
    mpa = kgf_cm2 * KGF_CM2_TO_MPA
    return {"kgf_cm2": kgf_cm2, "mpa": mpa}

def df_lote() -> pd.DataFrame:
    s = st.session_state
    if not s.lote:
        return pd.DataFrame(columns=["codigo_cp", "carga_kgf", "kgf_cm2", "mpa"])
    df = pd.DataFrame(s.lote)
    # garante tipos
    df["codigo_cp"] = df["codigo_cp"].astype(str)
    df["carga_kgf"] = pd.to_numeric(df["carga_kgf"], errors="coerce")
    df["kgf_cm2"] = pd.to_numeric(df["kgf_cm2"], errors="coerce")
    df["mpa"] = pd.to_numeric(df["mpa"], errors="coerce")
    return df

def header() -> None:
    theme_name = st.session_state.get("theme", "Escuro")
    accent = st.session_state.get("accent_color", ACCENT_DEFAULT)
    icon = "🧱"  # simples
    st.markdown(
        f"""
        <div class="hab-card">
            <div class="hab-title">{icon} {APP_TITLE}</div>
            <div class="hab-sub">
                Entrada: <b>carga (kgf)</b>. Saídas: <b>kgf/cm²</b> e <b>MPa</b>.
                Exportação CSV/Excel em 1 clique.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4 = st.columns([1.2,1,1,2])
    with c1:
        st.session_state.theme = st.selectbox("Tema", ["Escuro", "Claro"], index=0 if theme_name=="Escuro" else 1)
    with c2:
        st.session_state.accent_color = st.text_input("Cor de destaque (hex)", value=accent)
    with c3:
        st.session_state.wide_layout = st.toggle("Tela larga (1800px)", value=bool(st.session_state.get("wide_layout", True)))
    with c4:
        st.markdown("&nbsp;")

def bloco_converter() -> None:
    st.markdown('<div class="hab-card">', unsafe_allow_html=True)
    st.subheader("🔁 Conversor rápido (kgf ➜ kgf/cm² ➜ MPa)")
    c1, c2, c3 = st.columns(3)
    with c1:
        carga = st.number_input("Carga (kgf)", min_value=0.0, value=0.0, step=10.0)
    with c2:
        area = st.number_input("Área do CP (cm²)", min_value=0.01, value=float(st.session_state.obra["area_cm2"]), step=0.01, format="%.2f")
    with c3:
        st.write("")
        st.write("")
        if st.button("Calcular", use_container_width=True):
            pass  # botão apenas para UX
    res = calc_from_kgf(carga, area)
    c4, c5 = st.columns(2)
    with c4:
        st.metric("kgf/cm²", f"{res['kgf_cm2']:.2f}" if not math.isnan(res["kgf_cm2"]) else "—")
    with c5:
        st.metric("MPa", f"{res['mpa']:.3f}" if not math.isnan(res["mpa"]) else "—")
    st.markdown('</div>', unsafe_allow_html=True)

def bloco_dados_obra() -> None:
    st.markdown('<div class="hab-card">', unsafe_allow_html=True)
    st.subheader("✅ Dados da obra")
    s = st.session_state
    o = s.obra
    c1, c2, c3 = st.columns([2,1,1])
    with c1:
        o["nome_obra"] = st.text_input("Nome da obra", value=o.get("nome_obra", ""))
    with c2:
        o["data"] = st.date_input("Data", value=o.get("data", date.today()))
    with c3:
        o["area_cm2"] = st.number_input("Área do CP (cm²)", min_value=0.01, value=float(o.get("area_cm2", 16.00)), step=0.01, format="%.2f")

    c4, c5, c6 = st.columns([1,1,1])
    with c4:
        o["data_moldagem"] = st.date_input("Data de moldagem", value=o.get("data_moldagem", date.today()))
    with c5:
        o["data_ruptura"] = st.date_input("Data de ruptura", value=o.get("data_ruptura", date.today()))
    with c6:
        o["idade_dias"] = st.number_input("Idade de ruptura (dias)", min_value=1, value=int(o.get("idade_dias", 28)), step=1)

    st.session_state.obra = o

    c7, c8, _ = st.columns([1,2,4])
    with c7:
        st.markdown('<div class="hab-btn">', unsafe_allow_html=True)
        st.button("Aplicar", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with c8:
        st.markdown('<div class="hab-btn">', unsafe_allow_html=True)
        if st.button("Recalcular lote com nova área", use_container_width=True):
            recalc_lote_area(float(o["area_cm2"]))
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def recalc_lote_area(area_cm2: float) -> None:
    s = st.session_state
    for item in s.lote:
        c = calc_from_kgf(item["carga_kgf"], area_cm2)
        item["kgf_cm2"] = c["kgf_cm2"]
        item["mpa"] = c["mpa"]
def bloco_lancar_cp() -> None:
    st.markdown('<div class="hab-card">', unsafe_allow_html=True)
    st.subheader("🧪 Lançar ruptura (apenas kgf)")
    s = st.session_state
    o = s.obra
    c1, c2, c3 = st.columns([2,1,1])
    with c1:
        codigo = st.text_input("Código do CP", placeholder="Ex.: A039.258 / H682 / 037.421")
    with c2:
        carga_kgf = st.number_input("Carga de ruptura (kgf)", min_value=0.0, step=1.0, value=0.0)
    with c3:
        st.write("")
        st.markdown('<div class="hab-btn">', unsafe_allow_html=True)
        add = st.button("Aplicar CP", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if add and codigo.strip():
        conv = calc_from_kgf(float(carga_kgf), float(o["area_cm2"]))
        st.session_state.lote.append({
            "codigo_cp": codigo.strip(),
            "carga_kgf": float(carga_kgf),
            "kgf_cm2": conv["kgf_cm2"],
            "mpa": conv["mpa"],
        })
        st.success(f"CP '{codigo.strip()}' adicionado ao lote.")
    st.markdown('</div>', unsafe_allow_html=True)

def bloco_tabela() -> None:
    st.markdown('<div class="hab-card">', unsafe_allow_html=True)
    st.subheader("📋 CPs no lote")
    df = df_lote()
    st.dataframe(df, use_container_width=True, hide_index=True)
    c1, c2, c3 = st.columns([1,1,6])
    with c1:
        if not df.empty:
            st.download_button("Baixar CSV", df.to_csv(index=False).encode("utf-8"), "lote.csv", "text/csv")
    with c2:
        if not df.empty:
            # Excel
            from io import BytesIO
            buf = BytesIO()
            with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="Lote")
            st.download_button("Baixar Excel", buf.getvalue(), "lote.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.markdown('</div>', unsafe_allow_html=True)

def bloco_grafico() -> None:
    st.subheader("📈 Gráfico de ruptura (MPa por CP)")

    df = df_lote()
    if df.empty:
        st.info("Cadastre alguns CPs para visualizar o gráfico.")
        st.divider()
        return

    chart_df = (
        pd.DataFrame({
            "Código CP": df["codigo_cp"].astype(str).values,
            "MPa": pd.to_numeric(df["mpa"], errors="coerce").values
        })
        .dropna(subset=["MPa"])
        .reset_index(drop=False)
        .rename(columns={"index": "rowid"})
    )

    theme_name = st.session_state.get("theme", "Escuro")
    ACCENT = st.session_state.get("accent_color", "#f97316")

    bg         = "#0f1115" if theme_name == "Escuro" else "#ffffff"
    axis_color = "#e8eaed" if theme_name == "Escuro" else "#111318"
    grid_color = "rgba(255,255,255,0.22)" if theme_name == "Escuro" else "#e5e7eb"

    y_max = float(chart_df["MPa"].max() * 1.15) if len(chart_df) else 1.0

    points = (
        alt.Chart(chart_df, background=bg)
          .transform_window(dup_index='rank()', groupby=['Código CP'])
          .transform_joinaggregate(total='count()', groupby=['Código CP'])
          .transform_calculate(offset='(datum.dup_index - (datum.total + 1)/2) * 10')
          .mark_point(size=110, filled=True, color=ACCENT, opacity=0.95)
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

def main() -> None:
    init_state()
    st.set_page_config(page_title="Ruptura — Argamassa", page_icon="🧱",
                       layout="wide" if st.session_state.wide_layout else "centered")
    style_css()
    header()
    bloco_converter()
    bloco_dados_obra()
    bloco_lancar_cp()
    bloco_tabela()
    bloco_grafico()

if __name__ == "__main__":
    main()
