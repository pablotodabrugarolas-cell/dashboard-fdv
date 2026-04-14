import streamlit as st
import pandas as pd
import plotly.express as px
import os
import warnings
from docx import Document
from io import BytesIO
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
warnings.filterwarnings("ignore")
st.set_page_config(page_title="Fundación del Valle", layout="wide")

AZUL_FDV = "#003366"
NARANJA_FDV = "#E67E22"
VERDE_ACTIVO = "#28a745"
AMARILLO_MAPA = "#FFB300"

# CSS Limpio
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
    if not os.path.exists(target): 
        return pd.DataFrame()
    try:
        # Intento leer CSV
        df = pd.read_csv(target, sep=",", skiprows=1, encoding='utf-8')
    except:
        # Intento leer Excel
        df = pd.read_excel(target, skiprows=1)
    
    df.columns = [str(c).strip() for c in df.columns]
    
    cols_txt = ["Sector 1", "PAIS", "SOCIO LOCAL/CONTRAPARTE 1", "Título"]
    for c in cols_txt:
        if c in df.columns:
            df[c] = df[c].fillna('').astype(str).replace(['nan', 'None', 'N/A'], '').str.strip()

    num_cols = ["SUBVENCIÓN", "COSTE TOTAL", "B. Directos (Nº)", "B. Indirectos (Nº)"]
    for n in num_cols:
        if n in df.columns:
            df[n] = df[n].astype(str).str.replace(r'[^\d,.-]', '', regex=True).str.replace(',', '.')
            df[n] = pd.to_numeric(df[n], errors='coerce').fillna(0)

    df["Año_Num"] = pd.to_numeric(df["AÑO"], errors='coerce').fillna(0).astype(int)
    
    if 'FIN' in df.columns:
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
    # --- 3. BARRA LATERAL ---
    with st.sidebar:
        st.header("🔍 Filtros")
        st.markdown("---")
        # Protección de tipos para evitar TypeError
        f_pais = st.multiselect("📍 País", sorted([str(x) for x in df["PAIS"].unique() if str(x) != '']))
        f_año = st.multiselect("📅 Año", sorted([int(x) for x in df["Año_Num"].unique() if x > 0], reverse=True))
        f_sector = st.multiselect("🎯 Sector", sorted([str(x) for x in df["Sector 1"].unique() if str(x) != '']))
        f_socio = st.multiselect("🤝 Socio Local", sorted([str(x) for x in df["SOCIO LOCAL/CONTRAPARTE 1"].unique() if str(x) != '']))

    df_f = df.copy()
    if f_pais: df_f = df_f[df_f["PAIS"].isin(f_pais)]
    if f_año: df_f = df_f[df_f["Año_Num"].isin(f_año)]
    if f_sector: df_f = df_f[df_f["Sector 1"].isin(f_sector)]
    if f_socio: df_f = df_f[df_f["SOCIO LOCAL/CONTRAPARTE 1"].isin(f_socio)]

    # --- 4. DASHBOARD ---
    st.title("🌍 Impacto Global - Fundación del Valle")
    
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Proyectos", f"{len(df_f)}")
    m2.metric("Subvención", fmt_euro(df_f['SUBVENCIÓN'].sum()))
    m3.metric("Coste Total", fmt_euro(df_f['COSTE TOTAL'].sum()))
    m4.metric("Ben. Directos", f"{int(df_f['B. Directos (Nº)'].sum()):,.0f}".replace(",", "."))
    m5.metric("Ben. Indirectos", f"{int(df_f['B. Indirectos (Nº)'].sum()):,.0f}".replace(",", "."))

    st.divider()
    st.subheader("📍 Presencia Institucional Global")
    
    df_mapa = df_f.groupby("PAIS").agg({"SUBVENCIÓN":"sum", "B. Directos (Nº)":"sum", "Estado":"first"}).reset_index()
    df_mapa["Subv_T"] = df_mapa["SUBVENCIÓN"].apply(fmt_euro)
    df_mapa["Ben_T"] = df_mapa["B. Directos (Nº)"].apply(lambda x: f"{int(x):,.0f}".replace(",", "."))

    fig_map = px.choropleth(df_mapa, locations="PAIS", locationmode='country names', color="Estado",
                           color_discrete_map={"Activo": VERDE_ACTIVO, "Histórico": AMARILLO_MAPA}, projection="natural earth")
    
    fig_dots = px.scatter_geo(df_mapa, locations="PAIS", locationmode='country names', size="SUBVENCIÓN",
                             hover_name="PAIS", custom_data=["Ben_T", "Subv_T"], size_max=30)
    
    fig_dots.update_traces(hovertemplate="<b>%{hovertext}</b><br>Beneficiarios: %{customdata[0]}<br>Subvención: %{customdata[1]}<extra></extra>",
                           marker=dict(color=AZUL_FDV, opacity=0.5))
    
    fig_map.add_trace(fig_dots.data[0])
    fig_map.update_geos(showcountries=True, countrycolor="white", showocean=True, oceancolor="#D6EAF8")
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=600, showlegend=False)
    st.plotly_chart(fig_map, use_container_width=True)

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("👥 Beneficiarios por Sector")
        df_b = df_f.groupby("Sector 1")["B. Directos (Nº)"].sum().reset_index().sort_values("B. Directos (Nº)", ascending=True)
        st.plotly_chart(px.bar(df_b, x="B. Directos (Nº)", y="Sector 1", orientation='h', color="Sector 1").update_layout(showlegend=False), use_container_width=True)
    with c2:
        st.subheader("🍩 Inversión por Sector")
        df_p = df_f.groupby("Sector 1")["COSTE TOTAL"].sum().reset_index()
        st.plotly_chart(px.pie(df_p, values="COSTE TOTAL", names="Sector 1", hole=0.5), use_container_width=True)

    st.divider()
    
    # --- FICHA DE PROYECTO ---
    proy_l = sorted([str(x) for x in df_f["Título"].unique() if str(x) != ''])
    if proy_l:
        p_sel = st.selectbox("📋 Ficha del Proyecto:", proy_l)
        p = df_f[df_f["Título"] == p_sel].iloc[0]

        def get_word(d):
            doc = Document()
            doc.add_heading(str(d['Título']), 0)
            doc.add_paragraph(f"País: {d['PAIS']} | Año: {int(d['Año_Num'])}")
            doc.add_paragraph(f"Subvención: {fmt_euro(d['SUBVENCIÓN'])}")
            buf = BytesIO()
            doc.save(buf)
            buf.seek(0)
            return buf

        st.download_button("📄 Descargar Word", data=get_word(p), file_name=f"{p_sel}.docx")
        st.markdown(f"### {p['Título']}")
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.write(f"**📍 País:** {p['PAIS']} | **📅 Año:** {int(p['Año_Num'])}")
            st.write(f"**🤝 Socio:** {p['SOCIO LOCAL/CONTRAPARTE 1']}")
        with col_b:
            st.write(f"**💰 Financiación:** {fmt_euro(p['SUBVENCIÓN'])}")
            st.write(f"**👥 Impacto:** {int(p['B. Directos (Nº)'])} Directos")
        
        st.info(f"**Objetivo General (OG):**\n\n{p.get('OBJETIVO GENERAL (OG)', 'N/A')}")
        st.warning(f"**Objetivo Específico (OE):**\n\n{p.get('OBJETIVO ESPECÍFICO (OE)', 'N/A')}")
else:
    st.error("No se han encontrado datos. Verifica el archivo 'datos.csv.xlsx'.")
