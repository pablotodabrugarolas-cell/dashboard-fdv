import streamlit as st
import pandas as pd
import plotly.express as px
import os
from docx import Document
from io import BytesIO

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Fundación del Valle", layout="wide")

AZUL_FDV = "#003366"
NARANJA_FDV = "#E67E22"
VERDE_FDV = "#2E7D32" 
AMARILLO_MAPA = "#FFB300" 

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FFFFFF; }}
    h1, h2, h3 {{ color: {AZUL_FDV} !important; font-family: 'Arial'; }}
    .stMetric {{ background-color: #F8F9FA; padding: 15px; border-radius: 10px; border-left: 5px solid {NARANJA_FDV}; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CARGA Y LIMPIEZA ---
@st.cache_data
def load_data():
    folder = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(folder, "datos.csv.xlsx")
    if not os.path.exists(target): return pd.DataFrame()

    try:
        df = pd.read_excel(target, skiprows=1)
        df.columns = [str(c).strip() for c in df.columns]
        
        if "Sector 1" in df.columns:
            df["Sector 1"] = df["Sector 1"].astype(str).str.strip().str.capitalize()

        col_año = next((c for c in df.columns if 'año' in c.lower()), "Año")
        df["Año_Num"] = pd.to_numeric(df[col_año], errors='coerce').fillna(0).astype(int)
        df["Año_Str"] = df["Año_Num"].astype(str).replace('0', 'N/A')

        status_paises = df.groupby("PAIS")["Año_Num"].max().reset_index()
        status_paises["Estado"] = status_paises["Año_Num"].apply(lambda x: "Actual" if x >= 2025 else "Histórico")
        df = df.merge(status_paises[["PAIS", "Estado"]], on="PAIS", how="left")

        for n in ["SUBVENCIÓN", "COSTE TOTAL", "B. Directos (Nº)", "B. Indirectos (Nº)"]:
            if n in df.columns:
                df[n] = pd.to_numeric(df[n].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()

df = load_data()

# --- 3. BARRA LATERAL ---
if not df.empty:
    with st.sidebar:
        if os.path.exists("logo.png"):
            st.image("logo.png")
        else:
            st.markdown(f"<h2 style='color:{AZUL_FDV}'>Fundación del Valle</h2>", unsafe_allow_html=True)
        
        st.markdown("---")
        def get_opts(col):
            lista = [str(x) for x in df[col].unique() if str(x) not in ['', 'Sin especificar', 'N/A', '0']]
            return sorted(lista)

        f_pais = st.multiselect("📍 País", get_opts("PAIS"))
        f_año = st.multiselect("📅 Año", get_opts("Año_Num"))
        f_sector = st.multiselect("🎯 Sector", get_opts("Sector 1"))
        f_socio = st.multiselect("🤝 Socio Local", get_opts("SOCIO LOCAL/CONTRAPARTE 1"))

    df_f = df.copy()
    if f_pais: df_f = df_f[df_f["PAIS"].isin(f_pais)]
    if f_año: df_f = df_f[df_f["Año_Num"].astype(str).isin(f_año)]
    if f_sector: df_f = df_f[df_f["Sector 1"].isin(f_sector)]
    if f_socio: df_f = df_f[df_f["SOCIO LOCAL/CONTRAPARTE 1"].isin(f_socio)]

    # --- 4. MAPA MEJORADO (CON DATOS AGREGADOS) ---
    st.title("🌍 Presencia Institucional Global")
    
    # Creamos un resumen por país para el mapa
    df_mapa = df_f.groupby("PAIS").agg({
        "COSTE TOTAL": "sum",
        "B. Directos (Nº)": "sum",
        "Título": "count",
        "Estado": "first"
    }).reset_index()
    df_mapa.columns = ["PAIS", "Inversión Total", "Total Beneficiarios", "Nº Proyectos", "Estado"]

    fig_map = px.choropleth(
        df_mapa,
        locations="PAIS", locationmode='country names',
        color="Estado",
        color_discrete_map={"Actual": VERDE_FDV, "Histórico": AMARILLO_MAPA},
        projection="natural earth"
    )

    fig_dots = px.scatter_geo(
        df_mapa, 
        locations="PAIS", 
        locationmode='country names', 
        size="Inversión Total",
        hover_name="PAIS",
        custom_data=["Nº Proyectos", "Total Beneficiarios", "Inversión Total"],
        size_max=40 # Controla el tamaño máximo de los círculos
    )

    # Configuramos la etiqueta que aparece al pasar el cursor
    fig_dots.update_traces(
        hovertemplate="<b>%{hovertext}</b><br><br>" +
                      "Nº Proyectos: %{customdata[0]}<br>" +
                      "Total Beneficiarios: %{customdata[1]:,.0f}<br>" +
                      "Financiación Total: €%{customdata[2]:,.2f}<extra></extra>",
        marker=dict(color=AZUL_FDV, opacity=0.7, line=dict(width=1, color='white'))
    )

    fig_map.add_trace(fig_dots.data[0])
    fig_map.update_layout(showlegend=False, margin={"r":0,"t":0,"l":0,"b":0}, height=600)
    fig_map.update_geos(showocean=True, oceancolor="#D6EAF8", showcountries=True, countrycolor="#FFFFFF")
    st.plotly_chart(fig_map, width='stretch')

    # --- 5. SUBVENCIONES POR AÑO ---
    st.subheader("📈 Evolución de Subvenciones por Año")
    df_graf = df_f[df_f["Año_Num"] > 0].groupby("Año_Num")["SUBVENCIÓN"].sum().reset_index()
    fig_año = px.area(df_graf, x="Año_Num", y="SUBVENCIÓN", markers=True, color_discrete_sequence=[AZUL_FDV])
    fig_año.update_xaxes(type='category', title="Año") 
    fig_año.update_layout(height=350, yaxis_title="Euros (€)")
    st.plotly_chart(fig_año, width='stretch')

    # --- 6. GRÁFICAS COMPARATIVAS ---
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("👥 Beneficiarios Directos por Sector")
        df_ben = df_f.groupby("Sector 1")["B. Directos (Nº)"].sum().reset_index().sort_values("B. Directos (Nº)", ascending=True)
        fig_bar = px.bar(df_ben, x="B. Directos (Nº)", y="Sector 1", orientation='h', color="Sector 1")
        fig_bar.update_layout(height=450, showlegend=False)
        st.plotly_chart(fig_bar, width='stretch')

    with c2:
        st.subheader("🍩 Inversión por Sector")
        df_pie = df_f.groupby("Sector 1")["COSTE TOTAL"].sum().reset_index()
        total_inv = df_pie["COSTE TOTAL"].sum()
        df_pie['Agrup'] = df_pie.apply(lambda x: x['Sector 1'] if (total_inv > 0 and (x['COSTE TOTAL']/total_inv) > 0.02) else 'Otros', axis=1)
        fig_pie = px.pie(df_pie.groupby('Agrup')["COSTE TOTAL"].sum().reset_index(), values="COSTE TOTAL", names="Agrup", hole=0.5)
        fig_pie.update_layout(height=450, showlegend=False)
        st.plotly_chart(fig_pie, width='stretch')

    # --- 7. FICHA TÉCNICA ---
    st.markdown("---")
    proy_lista = sorted(df_f["Título"].unique())
    if proy_lista:
        proy_sel = st.selectbox("📋 Ficha del Proyecto Seleccionado:", proy_lista)
        p = df_f[df_f["Título"] == proy_sel].iloc[0]

        def get_word(data):
            doc = Document(); doc.add_heading(data['Título'], 0)
            doc.add_paragraph(f"País: {data['PAIS']} | Año: {data['Año_Num']}")
            buf = BytesIO(); doc.save(buf); buf.seek(0); return buf

        st.download_button("📄 Descargar Ficha en Word", data=get_word(p), file_name=f"{proy_sel}.docx")

        with st.container():
            st.markdown(f"### {p['Título']}")
            col_a, col_b = st.columns(2)
            with col_a:
                st.write(f"**📍 País:** {p['PAIS']} | **📅 Año:** {p['Año_Str']}")
                st.write(f"**🏛️ Financiador:** {p.get('Financiador', 'N/A')}")
            with col_b:
                st.write(f"**💰 Presupuesto:** Subvención €{p['SUBVENCIÓN']:,.2f} / Total €{p['COSTE TOTAL']:,.2f}")
                st.write(f"**👥 Impacto:** {int(p['B. Directos (Nº)'])} Directos ({p.get('Categoría Directos', 'N/A')}) / {int(p['B. Indirectos (Nº)'])} Indirectos ({p.get('Categoría Indirectos', 'N/A')})")
            
            st.info(f"**Objetivo General (OG):**\n\n{p.get('OBJETIVO GENERAL (OG)', 'No disponible')}")
            st.warning(f"**Objetivo Específico (OE):**\n\n{p.get('OBJETIVO ESPECÍFICO (OE)', 'No disponible')}")