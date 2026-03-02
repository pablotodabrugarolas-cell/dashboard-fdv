import streamlit as st
import pandas as pd
import plotly.express as px
import os
import warnings
from docx import Document
from io import BytesIO
from datetime import datetime

# --- 1. CONFIGURACIÓN Y ESTILOS ---
warnings.filterwarnings("ignore")
st.set_page_config(page_title="Fundación del Valle", layout="wide")

AZUL_FDV = "#003366"
NARANJA_FDV = "#E67E22"
VERDE_ACTIVO = "#28a745"
AMARILLO_MAPA = "#FFB300"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FFFFFF; }}
    h1, h2, h3 {{ color: {AZUL_FDV} !important; font-family: 'Arial'; }}
    .stMetric {{ background-color: #F8F9FA; padding: 15px; border-radius: 10px; border-left: 5px solid {NARANJA_FDV}; }}
    </style>
    """, unsafe_allow_html=True)

def fmt_euro(valor):
    try:
        return f"{int(round(float(valor))):,.0f}".replace(",", ".") + " €"
    except:
        return "0 €"

# --- 2. CARGA DE DATOS ---
@st.cache_data
def load_data():
    folder = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(folder, "datos.csv.xlsx")
    if not os.path.exists(target): return pd.DataFrame()

    try:
        df = pd.read_csv(target, sep=",", skiprows=1, encoding='utf-8')
    except:
        df = pd.read_excel(target, skiprows=1)

    df.columns = [str(c).strip() for c in df.columns]
    
    # Limpieza de textos para evitar errores de tipo
    columnas_texto = ["Sector 1", "PAIS", "SOCIO LOCAL/CONTRAPARTE 1", "Título"]
    for col in columnas_texto:
        if col in df.columns:
            df[col] = df[col].astype(str).replace(['nan', 'None', 'N/A'], '').str.strip()

    # Limpieza de números
    for n in ["SUBVENCIÓN", "COSTE TOTAL", "B. Directos (Nº)", "B. Indirectos (Nº)"]:
        if n in df.columns:
            df[n] = df[n].astype(str).str.replace(r'[^\d,.-]', '', regex=True).str.replace(',', '.')
            df[n] = pd.to_numeric(df[n], errors='coerce').fillna(0)

    df["Año_Num"] = pd.to_numeric(df["AÑO"], errors='coerce').fillna(0).astype(int)
    
    # Estado de los países para el mapa
    df['FECHA_FIN_DT'] = pd.to_datetime(df['FIN'], errors='coerce')
    hoy = pd.to_datetime(datetime.now().date())
    status_paises = df.groupby("PAIS")["FECHA_FIN_DT"].max().reset_index()
    status_paises["Estado"] = status_paises["FECHA_FIN_DT"].apply(
        lambda x: "Activo" if pd.notnull(x) and x >= hoy else "Histórico"
    )
    df = df.merge(status_paises[["PAIS", "Estado"]], on="PAIS", how="left")
    return df

df = load_data()

if not df.empty:
    # --- 3. BARRA LATERAL (FILTROS SOLAMENTE) ---
    with st.sidebar:
        st.header("🔍 Filtros de Búsqueda")
        st.markdown("---")
        f_pais = st.multiselect("📍 País", sorted([x for x in df["PAIS"].unique() if x and x != '']))
        f_año = st.multiselect("📅 Año", sorted([int(x) for x in df["Año_Num"].unique() if x > 0], reverse=True))
        f_sector = st.multiselect("🎯 Sector", sorted([x for x in df["Sector 1"].unique() if x and x != '']))
        f_socio = st.multiselect("🤝 Socio Local", sorted([x for x in df["SOCIO LOCAL/CONTRAPARTE 1"].unique() if x and x != '']))

    df_f = df.copy()
    if f_pais: df_f = df_f[df_f["PAIS"].isin(f_pais)]
    if f_año: df_f = df_f[df_f["Año_Num"].isin(f_año)]
    if f_sector: df_f = df_f[df_f["Sector 1"].isin(f_sector)]
    if f_socio: df_f = df_f[df_f["SOCIO LOCAL/CONTRAPARTE 1"].isin(f_socio)]

    # --- 4. PANEL DE IMPACTO ---
    st.title("🌍 Impacto Global - Fundación del Valle")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Proyectos", f"{len(df)}")
    m2.metric("Subvención", fmt_euro(df['SUBVENCIÓN'].sum()))
    m3.metric("Coste Total", fmt_euro(df['COSTE TOTAL'].sum()))
    m4.metric("Ben. Directos", f"{int(df['B. Directos (Nº)'].sum()):,.0f}".replace(",", "."))
    m5.metric("Ben. Indirectos", f"{int(df['B. Indirectos (Nº)'].sum()):,.0f}".replace(",", "."))

    st.divider()

    # --- 5. MAPA ---
    st.subheader("📍 Presencia Institucional Global")
    df_mapa = df.groupby("PAIS").agg({"SUBVENCIÓN": "sum", "B. Directos (Nº)": "sum", "Estado": "first"}).reset_index()
    df_mapa["Subv_Texto"] = df_mapa["SUBVENCIÓN"].apply(fmt_euro)
    df_mapa["Ben_Texto"] = df_mapa["B. Directos (Nº)"].apply(lambda x: f"{int(x):,.0f}".replace(",", "."))

    fig_map = px.choropleth(df_mapa, locations="PAIS", locationmode='country names', color="Estado",
                           color_discrete_map={"Activo": VERDE_ACTIVO, "Histórico": AMARILLO_MAPA}, projection="natural earth")
    fig_dots = px.scatter_geo(df_mapa, locations="PAIS", locationmode='country names', size="SUBVENCIÓN",
                             hover_name="PAIS", custom_data=["Ben_Texto", "Subv_Texto"], size_max=30)
    fig_dots.update_traces(hovertemplate="<b>%{hovertext}</b><br>Beneficiarios Directos: %{customdata[0]}<br>Subvención: %{customdata[1]}<extra></extra>",
                           marker=dict(color=AZUL_FDV, opacity=0.5))
    fig_map.add_trace(fig_dots.data[0])
    fig_map.update_geos(showcountries=True, countrycolor="white", showocean=True, oceancolor="#D6EAF8")
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=600, showlegend=False)
    st.plotly_chart(fig_map, width='stretch')

    # --- 6. GRÁFICAS ---
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("👥 Beneficiarios Directos por Sector")
        df_ben = df_f.groupby("Sector 1")["B. Directos (Nº)"].sum().reset_index().sort_values("B. Directos (Nº)", ascending=True)
        fig_bar = px.bar(df_ben, x="B. Directos (Nº)", y="Sector 1", orientation='h', color="Sector 1")
        fig_bar.update_layout(showlegend=False, height=450)
        st.plotly_chart(fig_bar, width='stretch')
    with c2:
        st.subheader("🍩 Inversión por Sector")
        df_pie = df_f.groupby("Sector 1")["COSTE TOTAL"].sum().reset_index()
        total_inv = df_pie["COSTE TOTAL"].sum()
        if total_inv > 0:
            df_pie['Agrup'] = df_pie.apply(lambda x: x['Sector 1'] if (x['COSTE TOTAL']/total_inv) > 0.02 else 'Otros', axis=1)
            df_pie_f = df_pie.groupby('Agrup')["COSTE TOTAL"].sum().reset_index()
        else: df_pie_f = df_pie
        fig_pie = px.pie(df_pie_f, values="COSTE TOTAL", names="Agrup", hole=0.5)
        st.plotly_chart(fig_pie, width='stretch')

    # --- 7. FICHA TÉCNICA ---
    st.divider()
    proy_lista = sorted([x for x in df_f["Título"].unique() if x and x != ''])
    if proy_lista:
        proy_sel = st.selectbox("📋 Ficha del Proyecto Seleccionado:", proy_lista)
        p = df_f[df_f["Título"] == proy_sel].iloc[0]

        def get_word(data):
            doc = Document()
            doc.add_heading(data['Título'], 0)
            doc.add_paragraph(f"País: {data['PAIS']} | Año: {int(data['Año_Num'])}")
            doc.add_paragraph(f"Socio Local: {data['SOCIO LOCAL/CONTRAPARTE 1']}")
            doc.add_paragraph(f"Financiador: {data.get('Financiador', 'N/A')}")
            doc.add_paragraph(f"Subvención: {fmt_euro(data['SUBVENCIÓN'])} | Coste Total: {fmt_euro(data['COSTE TOTAL'])}")
            doc.add_paragraph(f"Impacto: {int(data['B. Directos (Nº)'])} Directos / {int(data['B. Indirectos (Nº)'])} Indirectos")
            doc.add_heading("Objetivo General (OG)", 1); doc.add_paragraph(str(data.get('OBJETIVO GENERAL (OG)', 'N/A')))
            doc.add_heading("Objetivo Específico (OE)", 1); doc.add_paragraph(str(data.get('OBJETIVO ESPECÍFICO (OE)', 'N/A')))
            buf = BytesIO(); doc.save(buf); buf.seek(0); return buf

        st.download_button("📄 Descargar Ficha Completa", data=get_word(p), file_name=f"{proy_sel}.docx")

        with st.container():
            st.markdown(f"### {p['Título']}")
            col_a, col_b = st.columns(2)
            with col_a:
                st.write(f"**📍 País:** {p['PAIS']} | **📅 Año:** {int(p['Año_Num'])}")
                st.write(f"**🤝 Socio:** {p['SOCIO LOCAL/CONTRAPARTE 1']}")
                st.write(f"**🏛️ Financiador:** {p.get('Financiador', 'N/A')}")
            with col_b:
                st.write(f"**💰 Financiación:** Subvención {fmt_euro(p['SUBVENCIÓN'])} / Total {fmt_euro(p['COSTE TOTAL'])}")
                st.write(f"**👥 Impacto:** {int(p['B. Directos (Nº)'])} Directos / {int(p['B. Indirectos (Nº)'])} Indirectos")
            st.info(f"**Objetivo General (OG):**\n\n{p.get('OBJETIVO GENERAL (OG)', 'No disponible')}")
            st.warning(f"**Objetivo Específico (OE):**\n\n{p.get('OBJETIVO ESPECÍFICO (OE)', 'No disponible')}")
