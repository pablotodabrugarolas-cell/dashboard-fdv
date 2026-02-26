[datos.csv.xlsx](https://github.com/user-attachments/files/25572364/datos.csv.xlsx)
<img width="354" height="142" alt="logo" src="https://github.com/user-attachments/assets/64170f25-bd3e-4380-aac9-45a24f6fd60d" />
[requirements.txt](https://github.com/user-attachments/files/25572368/requirements.txt)
streamlit
pandas
openpyxl
plotly
numpy
[import streamlit as st.txt](https://github.com/user-attachments/files/25572370/import.streamlit.as.st.txt)
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os

# -----------------------------------------------------------------------------
# Configuration and Styling (Fundación del Valle Theme)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="App Histórico Fundación del Valle",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Colores FdV: Azul (#003366) y detalles en Naranja/Dorado (#E67E22)
st.markdown("""
<style>
    .stApp { background-color: #FDFDFD; }
    h1, h2, h3 { color: #003366 !important; font-family: 'Arial'; }
    [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 2px solid #003366; }
    div[data-testid="metric-container"] {
        background-color: #FFFFFF;
        border: 1px solid #003366;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
    }
    [data-testid="stMetricValue"] { color: #E67E22 !important; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Data Loading & Processing
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    file_path = "Relación proyectos FdV 2000-2026.7.xlsx" # Asegúrate de que el nombre coincida
    if not os.path.exists(file_path):
        # Intento leer el CSV si el Excel no está
        file_path = "Relación proyectos FdV 2000-2026.7.xlsx - 2000-2025.csv"
        if not os.path.exists(file_path):
            return pd.DataFrame()
        df = pd.read_csv(file_path, header=1)
    else:
        df = pd.read_excel(file_path, header=1)

    df.columns = df.columns.astype(str).str.strip()
    
    # Limpieza de nombres de columnas críticos
    df = df.rename(columns={
        "SOCIO LOCAL/CONTRAPARTE 1": "Socio",
        "Financiador. Tipo (Público/Privado)": "Tipo_Finan",
        "Año": "Año_Col", # Tu nueva columna
    })

    # Asegurar que las columnas numéricas sean tratadas correctamente
    numeric_cols = ["SUBVENCIÓN", "COSTE TOTAL", "B. Directos (Nº)", "B. Indirectos (Nº)"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Rellenar vacíos
    df = df.fillna("N/A")
    return df

df_raw = load_data()

# -----------------------------------------------------------------------------
# Sidebar Filters
# -----------------------------------------------------------------------------
st.sidebar.image("https://fundaciondelvalle.org/wp-content/uploads/2018/10/logo-fdv.png", width=200) # Opcional: logo
st.sidebar.title("🔍 Filtros de Proyectos")

if not df_raw.empty:
    # Filtro Sector (Sector 1)
    sector_list = sorted(df_raw["Sector 1"].unique())
    selected_sector = st.sidebar.multiselect("📚 Sector (Principal)", sector_list)

    # Filtro Socio (Socio Local/Contraparte 1)
    socio_list = sorted(df_raw["Socio"].unique())
    selected_socio = st.sidebar.multiselect("🤝 Socio Local", socio_list)

    # Filtro Financiador
    finan_list = sorted(df_raw["Financiador"].unique())
    selected_finan = st.sidebar.multiselect("💰 Financiador", finan_list)

    # Filtro Tipo Financiador
    tipo_finan_list = sorted(df_raw["Tipo_Finan"].unique())
    selected_tipo_finan = st.sidebar.multiselect("🏛️ Tipo de Financiador", tipo_finan_list)

    # Filtro Año (Tu nueva columna)
    if "Año_Col" in df_raw.columns:
        year_list = sorted(df_raw["Año_Col"].unique(), reverse=True)
        selected_year = st.sidebar.multiselect("📅 Año de Proyecto", year_list)
    else:
        selected_year = []

    # Aplicar Filtros
    df_filtered = df_raw.copy()
    if selected_sector: df_filtered = df_filtered[df_filtered["Sector 1"].isin(selected_sector)]
    if selected_socio: df_filtered = df_filtered[df_filtered["Socio"].isin(selected_socio)]
    if selected_finan: df_filtered = df_filtered[df_filtered["Financiador"].isin(selected_finan)]
    if selected_tipo_finan: df_filtered = df_filtered[df_filtered["Tipo_Finan"].isin(selected_tipo_finan)]
    if selected_year: df_filtered = df_filtered[df_filtered["Año_Col"].isin(selected_year)]

    # -----------------------------------------------------------------------------
    # Main Dashboard
    # -----------------------------------------------------------------------------
    st.title("Gestión de Proyectos - Fundación del Valle")
    
    # KPIs
    k1, k2, k3 = st.columns(3)
    k1.metric("Total Proyectos", len(df_filtered))
    k2.metric("Inversión Total", f"€{df_filtered['COSTE TOTAL'].sum():,.0f}".replace(",", "."))
    
    dir_ben = df_filtered["B. Directos (Nº)"].sum()
    ind_ben = df_filtered["B. Indirectos (Nº)"].sum()
    k3.metric("Impacto Social", f"{int(dir_ben + ind_ben):,}".replace(",", "."), f"({int(dir_ben):,} Dir / {int(ind_ben):,} Ind)")

    st.markdown("---")

    # Mapa del Mundo y Regiones
    st.subheader("🗺️ Cobertura Geográfica y Presupuesto")
    # Para el mapa necesitamos coordenadas o nombres de países. Plotly usa ISO o nombres.
    fig_map = px.scatter_geo(df_filtered,
                             locations="PAIS",
                             locationmode='country names',
                             color="Sector 1",
                             size="COSTE TOTAL",
                             hover_name="Título",
                             hover_data=["Región", "Comunidad", "COSTE TOTAL"],
                             projection="natural earth",
                             title="Distribución por País, Región y Comunidad",
                             color_discrete_sequence=px.colors.qualitative.Bold)
    fig_map.update_geos(showcountries=True, countrycolor="LightGrey")
    st.plotly_chart(fig_map, use_container_width=True)

    # Gráficas
    c1, c2 = st.columns(2)
    
    with c1:
        # Volumen de subvenciones por año
        if "Año_Col" in df_filtered.columns:
            st.write("### 📈 Subvenciones por Año")
            df_year = df_filtered.groupby("Año_Col")["SUBVENCIÓN"].sum().reset_index()
            fig_sub = px.line(df_year, x="Año_Col", y="SUBVENCIÓN", markers=True, 
                              color_discrete_sequence=["#003366"])
            st.plotly_chart(fig_sub, use_container_width=True)

    with c2:
        # Beneficiarios directos por sector
        st.write("### 👥 Beneficiarios Directos por Sector")
        df_ben_sec = df_filtered.groupby("Sector 1")["B. Directos (Nº)"].sum().reset_index()
        fig_ben = px.bar(df_ben_sec, x="Sector 1", y="B. Directos (Nº)", 
                         color_discrete_sequence=["#E67E22"])
        st.plotly_chart(fig_ben, use_container_width=True)

    st.markdown("---")

    # Ficha Técnica Completa (Filtrable)
    st.subheader("📋 Ficha Técnica Detallada")
    
    proyectos_disponibles = df_filtered["Título"].unique()
    proyecto_sel = st.selectbox("Seleccione un proyecto para ver toda su información:", proyectos_disponibles)

    if proyecto_sel:
        p = df_filtered[df_filtered["Título"] == proyecto_sel].iloc[0]
        
        with st.container():
            col_a, col_b = st.columns([2, 1])
            with col_a:
                st.info(f"**Título:** {p['Título']}")
                st.write(f"**Objetivo General:** {p['OBJETIVO GENERAL (OG)']}")
                st.write(f"**Objetivo Específico:** {p['OBJETIVO ESPECÍFICO (OE)']}")
                st.write(f"**Región / Comunidad:** {p['Región']} / {p['Comunidad']}")
            
            with col_b:
                st.write(f"**Financiador:** {p['Financiador']}")
                st.write(f"**Socio(s):** {p['Socio']}, {p.get('SOCIO LOCAL/CONTRAPARTE 2', '')}")
                st.write(f"**Periodo:** {p['INICIO']} al {p['FIN']}")
                st.write(f"**Código CAD:** {p.get('CÓDIGO CAD', 'N/A')}")

            st.write("---")
            st.write("**Desglose de Sectores:**")
            st.caption(f"1: {p['Sector 1']} | 2: {p.get('Sector 2', '-')} | 3: {p.get('Sector 3', '-')} | 4: {p.get('Sector 4', '-')} | 5: {p.get('Sector 5', '-')}")
            
            st.write("**Detalle de Beneficiarios:**")
            st.write(f"- **Directos ({p.get('Categoría Directos', 'General')}):** {int(p['B. Directos (Nº)'])}")
            st.write(f"- **Indirectos ({p.get('Categoría Indirectos', 'General')}):** {int(p['B. Indirectos (Nº)'])}")

else:
    st.error("Por favor, asegúrate de que el archivo Excel 'Relación proyectos FdV 2000-2026.7.xlsx' esté en la misma carpeta que este código.")
