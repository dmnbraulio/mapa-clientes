# app.py
# ---------------------------------
# Mapa con actualización por zonas y filtro estable de boticas
# ---------------------------------

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# ---------------------------------
# 1) Configuración inicial
# ---------------------------------
st.set_page_config(page_title="Mapa de Distribución - LAFARMED", layout="wide")
st.title("🗺️ Mapa de Distribución de Clientes - LAFARMED")

# ---------------------------------
# 2) Cargar datos
# ---------------------------------
@st.cache_data
def cargar_datos():
    path_csv = "data/clientes.csv"
    df = pd.read_csv(path_csv)
    df = df.dropna(subset=["Lat", "Lng"])
    return df

df = cargar_datos()

# ---------------------------------
# 3) Panel lateral (filtros)
# ---------------------------------
st.sidebar.header("🔍 Filtros")

# 🔸 Selección de zonas (múltiple)
zonas_disponibles = sorted(df["CodigoZona"].dropna().unique())
zonas_sel = st.sidebar.multiselect(
    "Selecciona uno o varios Códigos de Zona:",
    options=zonas_disponibles,
    default=[]
)

# 🔹 Filtrado inicial por zonas seleccionadas
if len(zonas_sel) > 0:
    df_zonas = df[df["CodigoZona"].isin(zonas_sel)]
else:
    df_zonas = pd.DataFrame()

# 🔹 Boticas dentro de las zonas seleccionadas
if not df_zonas.empty:
    boticas_disponibles = sorted(df_zonas["Botica"].dropna().unique())
else:
    boticas_disponibles = []

boticas_sel = st.sidebar.multiselect(
    "Selecciona una o varias Boticas (opcional):",
    options=boticas_disponibles,
    default=[]
)

# ---------------------------------
# 4) Control del estado del botón
# ---------------------------------
# Creamos una variable persistente para saber si el filtro está activo
if "filtrar_boticas" not in st.session_state:
    st.session_state.filtrar_boticas = False
if "boticas_filtradas" not in st.session_state:
    st.session_state.boticas_filtradas = []

# Cuando se presiona el botón, guardamos las boticas seleccionadas
if st.sidebar.button("🔍 Aplicar filtro de Boticas"):
    st.session_state.filtrar_boticas = True
    st.session_state.boticas_filtradas = boticas_sel

# Si el usuario limpia la selección de boticas, desactivamos el filtro
if len(boticas_sel) == 0 and st.session_state.filtrar_boticas:
    st.session_state.filtrar_boticas = False
    st.session_state.boticas_filtradas = []

# ---------------------------------
# 5) Aplicar filtro según estado
# ---------------------------------
if not df_zonas.empty:
    if st.session_state.filtrar_boticas and len(st.session_state.boticas_filtradas) > 0:
        df_filtrado = df_zonas[df_zonas["Botica"].isin(st.session_state.boticas_filtradas)]
        st.sidebar.success(f"{len(df_filtrado)} boticas filtradas dentro de las zonas seleccionadas.")
    else:
        df_filtrado = df_zonas
else:
    df_filtrado = pd.DataFrame()
    st.info("Selecciona al menos una zona para mostrar el mapa.")

# ---------------------------------
# 6) Mostrar tabla y mapa
# ---------------------------------
if not df_filtrado.empty:
    st.subheader("📋 Datos filtrados")
    st.dataframe(df_filtrado, use_container_width=True)

    st.subheader("🗺️ Mapa de clientes")

    # Calcular centro del mapa
    center_lat = df_filtrado["Lat"].mean()
    center_lng = df_filtrado["Lng"].mean()
    m = folium.Map(location=[center_lat, center_lng], zoom_start=12)

    color_map = {
        "SU01": "red",
        "SU02": "green",
        "SU03": "blue",
        "SU04": "purple",
        "SU05": "orange"
    }

    for _, row in df_filtrado.iterrows():
        color = color_map.get(row["CodigoZona"], "gray")
        popup_html = f"""
        <b>Botica:</b> {row['Botica']}<br>
        <b>Zona:</b> {row['ZonaNombre']} ({row['CodigoZona']})<br>
        <b>Cliente:</b> {row['CodigoCliente']} - {row['NombreCliente']}<br>
        <b>Referencias:</b> {row['Referencias']}<br>
        <b>Dirección:</b> {row['Direccion']}
        """
        folium.Marker(
            location=[row["Lat"], row["Lng"]],
            popup=popup_html,
            tooltip=row["Botica"],
            icon=folium.Icon(color=color, icon="info-sign")
        ).add_to(m)

    st_folium(m, width=1400, height=600)
else:
    st.warning("No hay datos para mostrar. Selecciona al menos una zona.")