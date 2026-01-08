# app.py
# --------------------------------------------------
# Mapa de Distribución - LAFARMED
# --------------------------------------------------

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.features import DivIcon
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
    df["_uid"] = df.index.astype(str)
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

# --------------------------------------------------
# Session State
# --------------------------------------------------
if "checks" not in st.session_state:
    st.session_state.checks = {}

if "orden_pdf" not in st.session_state:
    st.session_state.orden_pdf = {}

if "aplicar_filtro" not in st.session_state:
    st.session_state.aplicar_filtro = False

for _, r in df.iterrows():
    st.session_state.checks.setdefault(r["_uid"], False)

# --------------------------------------------------
# BUSCADOR
# --------------------------------------------------
st.subheader("🔎 Buscar botica o cliente")

busqueda = st.text_input(
    "Busca por botica o cliente:",
    placeholder="Ej: Inkafarma, Botica Sin Nombre, Juan Pérez..."
)

if busqueda:
    df_visible = df[
        df["Botica"].str.contains(busqueda, case=False, na=False) |
        df["NombreCliente"].str.contains(busqueda, case=False, na=False)
    ]
else:
    df_visible = df_zonas if not df_zonas.empty else pd.DataFrame()

# --------------------------------------------------
# CHECKLIST DE SELECCIÓN
# --------------------------------------------------
if not df_visible.empty:

    st.subheader("📋 Selección de boticas")

    headers = st.columns([0.6, 1.2, 2.2, 2.5, 2.5])
    headers[0].markdown("**✔**")
    headers[1].markdown("**Cod Zona**")
    headers[2].markdown("**Zona**")
    headers[3].markdown("**Botica**")
    headers[4].markdown("**Cliente**")

    st.divider()

    for _, r in df_visible.iterrows():

        cols = st.columns([0.6, 1.2, 2.2, 2.5, 2.5])

        st.session_state.checks[r["_uid"]] = cols[0].checkbox(
            "",
            value=st.session_state.checks[r["_uid"]],
            key=f"chk_{r['_uid']}"
        )

        cols[1].write(r["CodigoZona"])
        cols[2].write(r["ZonaNombre"])
        cols[3].write(r["Botica"])
        cols[4].write(r["NombreCliente"])

    if st.button("🔍 Aplicar filtro al mapa"):
        st.session_state.aplicar_filtro = True

# --------------------------------------------------
# FILTRADO FINAL
# --------------------------------------------------
if st.session_state.aplicar_filtro:
    seleccionados = [k for k, v in st.session_state.checks.items() if v]
    df_filtrado = df[df["_uid"].isin(seleccionados)].copy()
else:
    df_filtrado = pd.DataFrame()

# --------------------------------------------------
# CHECKLIST FINAL (ORDEN + VISUAL)
# --------------------------------------------------
if not df_filtrado.empty:

    st.subheader("✅ Checklist final")

    df_filtrado = df_filtrado.sort_values(
        by="CodigoZona",
        ascending=False
    ).reset_index(drop=True)

    headers = st.columns([0.8, 1.5, 2.5, 3.5, 1.2])
    headers[0].markdown("**#**")
    headers[1].markdown("**Cod Zona**")
    headers[2].markdown("**Zona**")
    headers[3].markdown("**Botica / Cliente**")
    headers[4].markdown("**Orden PDF**")

    st.divider()

    for idx, r in df_filtrado.iterrows():

        uid = r["_uid"]

        # 🔹 TODOS INICIAN EN 0
        st.session_state.orden_pdf.setdefault(uid, 0)

        nombre_mostrar = (
            r["NombreCliente"]
            if str(r["Botica"]).strip().lower() == "botica sin nombre"
            else r["Botica"]
        )

        cols = st.columns([0.8, 1.5, 2.5, 3.5, 1.2])

        cols[0].write(idx + 1)
        cols[1].write(r["CodigoZona"])
        cols[2].write(r["ZonaNombre"])
        cols[3].write(nombre_mostrar)

        st.session_state.orden_pdf[uid] = cols[4].number_input(
            "",
            min_value=0,
            step=1,
            value=int(st.session_state.orden_pdf[uid]),
            key=f"orden_{uid}",
            label_visibility="collapsed"
        )

# --------------------------------------------------
# MAPA CON NÚMEROS
# --------------------------------------------------
if not df_filtrado.empty:

    st.subheader("🗺️ Mapa numerado")

    m = folium.Map(
        location=[df_filtrado["Lat"].mean(), df_filtrado["Lng"].mean()],
        zoom_start=12
    )

    for idx, r in df_filtrado.iterrows():

        numero = idx + 1
        link = f"https://www.google.com/maps?q={r['Lat']},{r['Lng']}"

        folium.Marker(
            location=[r["Lat"], r["Lng"]],
            icon=DivIcon(
                icon_size=(30, 30),
                icon_anchor=(15, 30),
                html=f"""
                <div style="
                    background:#4FC3F7;
                    color:white;
                    border-radius:50%;
                    width:30px;
                    height:30px;
                    text-align:center;
                    line-height:30px;
                    font-weight:bold;
                    font-size:14px;">
                    {numero}
                </div>
                """
            ),
            popup=f"""
            <b>{numero}. {r['Botica']}</b><br>
            Cliente: {r['NombreCliente']}<br>
            <a href="{link}" target="_blank">Abrir en Google Maps</a>
            """
        ).add_to(m)

    st_folium(m, height=550)

# --------------------------------------------------
# PDF
# --------------------------------------------------
if st.button("📄 Generar PDF") and not df_filtrado.empty:

    df_pdf = df_filtrado.copy()
    df_pdf["OrdenPDF"] = df_pdf["_uid"].map(st.session_state.orden_pdf)
    df_pdf = df_pdf.sort_values("OrdenPDF")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")

    doc = SimpleDocTemplate(tmp.name, pagesize=landscape(A4))

    data = [[
        "Orden",
        "Cod Zona",
        "Zona",
        "Cliente",
        "Botica",
        "Google Maps"
    ]]

    for _, r in df_pdf.iterrows():
        data.append([
            r["OrdenPDF"],
            r["CodigoZona"],
            r["ZonaNombre"],
            r["NombreCliente"],
            r["Botica"],
            f"https://www.google.com/maps?q={r['Lat']},{r['Lng']}"
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))

    doc.build([table])

    with open(tmp.name, "rb") as f:
        st.download_button(
            "⬇️ Descargar PDF",
            f,
            file_name="distribucion_boticas.pdf",
            mime="application/pdf"
        )
