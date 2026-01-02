# app.py
# --------------------------------------------------
# Mapa de Distribución - LAFARMED
# --------------------------------------------------

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
import tempfile

# --------------------------------------------------
# Configuración general
# --------------------------------------------------
st.set_page_config(
    page_title="Mapa de Distribución - LAFARMED",
    layout="wide"
)

st.title("🗺️ Mapa de Distribución de Clientes - LAFARMED")

# --------------------------------------------------
# Cargar datos
# --------------------------------------------------
@st.cache_data
def cargar_datos():
    df = pd.read_csv("data/clientes.csv")
    df = df.dropna(subset=["Lat", "Lng"])
    df = df.reset_index(drop=True)
    df["_uid"] = df.index.astype(str)  # ID único estable
    return df

df = cargar_datos()

# --------------------------------------------------
# Sidebar - selección de zonas
# --------------------------------------------------
st.sidebar.header("🔍 Filtros")

zonas = sorted(df["CodigoZona"].unique())

zonas_sel = st.sidebar.multiselect(
    "Selecciona códigos de zona:",
    zonas
)

df_zonas = df[df["CodigoZona"].isin(zonas_sel)] if zonas_sel else pd.DataFrame()

# 🔹 ORDEN FIJO
if not df_zonas.empty:
    df_zonas = df_zonas.sort_values(
        by=["CodigoZona", "Botica"],
        ascending=[True, True]
    ).reset_index(drop=True)

# --------------------------------------------------
# Session State
# --------------------------------------------------
if "checks" not in st.session_state:
    st.session_state.checks = {}

if "aplicar_filtro" not in st.session_state:
    st.session_state.aplicar_filtro = False

for _, r in df_zonas.iterrows():
    if r["_uid"] not in st.session_state.checks:
        st.session_state.checks[r["_uid"]] = False

# --------------------------------------------------
# TABLA + CHECKLIST
# --------------------------------------------------
if not df_zonas.empty:

    st.subheader("📋 Selección de boticas")

    encabezados = st.columns([0.5, 1, 2, 2, 3])

    encabezados[0].markdown("**✔**")
    encabezados[1].markdown("**Cod Zona**")
    encabezados[2].markdown("**Zona**")
    encabezados[3].markdown("**Botica**")
    encabezados[4].markdown("**Cliente**")

    # Línea separadora del encabezado (ultra fina)
    st.markdown(
        "<hr style='margin:4px 0; border:0; border-top:1px solid #cfcfcf;'>",
        unsafe_allow_html=True
    )

    for _, r in df_zonas.iterrows():

        cols = st.columns([0.5, 1, 2, 2, 3])

        st.session_state.checks[r["_uid"]] = cols[0].checkbox(
            "",
            value=st.session_state.checks[r["_uid"]],
            key=f"chk_{r['_uid']}"
        )

        cols[1].write(r["CodigoZona"])
        cols[2].write(r["ZonaNombre"])
        cols[3].write(r["Botica"])
        cols[4].write(r["NombreCliente"])

        # 🔹 LÍNEA DIVISORIA ULTRA DELGADA (NO aumenta altura)
        st.markdown(
            "<hr style='margin:2px 0; border:0; border-top:1px solid #e6e6e6;'>",
            unsafe_allow_html=True
        )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔍 Aplicar filtro al mapa"):
            st.session_state.aplicar_filtro = True

    with col2:
        generar_pdf = st.button("📄 Generar PDF")

else:
    st.info("Selecciona al menos una zona.")

# --------------------------------------------------
# Aplicar selección
# --------------------------------------------------
if st.session_state.aplicar_filtro:
    seleccionados = [
        k for k, v in st.session_state.checks.items() if v
    ]
    df_filtrado = df_zonas[df_zonas["_uid"].isin(seleccionados)]
else:
    df_filtrado = df_zonas

# --------------------------------------------------
# MAPA
# --------------------------------------------------
if not df_filtrado.empty:

    st.subheader("🗺️ Mapa")

    m = folium.Map(
        location=[
            df_filtrado["Lat"].mean(),
            df_filtrado["Lng"].mean()
        ],
        zoom_start=12
    )

    for _, r in df_filtrado.iterrows():
        link = f"https://www.google.com/maps?q={r['Lat']},{r['Lng']}"

        folium.Marker(
            [r["Lat"], r["Lng"]],
            popup=f"""
            <b>Zona:</b> {r['CodigoZona']} - {r['ZonaNombre']}<br>
            <b>Botica:</b> {r['Botica']}<br>
            <b>Cliente:</b> {r['NombreCliente']}<br><br>
            <a href="{link}" target="_blank">Abrir en Google Maps</a>
            """
        ).add_to(m)

    st_folium(m, height=500)

# --------------------------------------------------
# PDF
# --------------------------------------------------
if "generar_pdf" in locals() and generar_pdf and not df_filtrado.empty:

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")

    doc = SimpleDocTemplate(
        tmp.name,
        pagesize=landscape(A4)
    )

    data = [[
        "Cod Zona",
        "Nombre Zona",
        "Nombre Cliente",
        "Nombre Botica",
        "Google Maps"
    ]]

    for _, r in df_filtrado.iterrows():
        link = f"https://www.google.com/maps?q={r['Lat']},{r['Lng']}"
        data.append([
            r["CodigoZona"],
            r["ZonaNombre"],
            r["NombreCliente"],
            r["Botica"],
            link
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "LEFT")
    ]))

    doc.build([table])

    with open(tmp.name, "rb") as f:
        st.download_button(
            "⬇️ Descargar PDF",
            f,
            file_name="distribucion_boticas.pdf",
            mime="application/pdf"
        )
