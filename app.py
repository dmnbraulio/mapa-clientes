# app.py
# ---------------------------------
# Mapa de distribución con:
# - filtros
# - selección por tabla
# - exportación a PDF con mapa
# ---------------------------------

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Image, PageBreak
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

# ---------------------------------
# Configuración inicial
# ---------------------------------
st.set_page_config(page_title="Mapa de Distribución - LAFARMED", layout="wide")
st.title("🗺️ Mapa de Distribución de Clientes - LAFARMED")

# ---------------------------------
# Cargar datos
# ---------------------------------
@st.cache_data
def cargar_datos():
    df = pd.read_csv("data/clientes.csv")
    return df.dropna(subset=["Lat", "Lng"])

df = cargar_datos()

# ---------------------------------
# Filtros
# ---------------------------------
st.sidebar.header("🔍 Filtros")

zonas_sel = st.sidebar.multiselect(
    "Selecciona zonas:",
    sorted(df["CodigoZona"].unique())
)

df_zonas = df[df["CodigoZona"].isin(zonas_sel)] if zonas_sel else pd.DataFrame()

# ---------------------------------
# Tabla con selección
# ---------------------------------
if not df_zonas.empty:
    df_tabla = df_zonas.copy().reset_index(drop=True)
    df_tabla.insert(0, "Seleccionar", False)
    df_tabla.insert(1, "Indice", df_tabla.index + 1)

    df_editado = st.data_editor(
        df_tabla,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Seleccionar": st.column_config.CheckboxColumn("Seleccionar")
        }
    )

    df_sel = df_editado[df_editado["Seleccionar"]]

    if df_sel.empty:
        st.info("Selecciona al menos una fila para exportar.")
    else:
        st.success(f"{len(df_sel)} registros seleccionados")

    # ---------------------------------
    # Crear mapa
    # ---------------------------------
    df_mapa = df_sel if not df_sel.empty else df_zonas

    center = [df_mapa["Lat"].mean(), df_mapa["Lng"].mean()]
    m = folium.Map(location=center, zoom_start=12)

    for _, r in df_mapa.iterrows():
        folium.Marker(
            [r["Lat"], r["Lng"]],
            tooltip=f'{r["Indice"]} - {r["Botica"]}',
            icon=folium.DivIcon(
                html=f"""
                <div style="font-size:12px;
                            color:white;
                            background:#1f77b4;
                            border-radius:50%;
                            width:24px;
                            height:24px;
                            text-align:center;
                            line-height:24px;">
                    {r["Indice"]}
                </div>
                """
            )
        ).add_to(m)

    st_folium(m, width=1400, height=600)

    # ---------------------------------
    # Exportar PDF
    # ---------------------------------
    if st.button("📄 Exportar PDF"):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        elementos = []

        elementos.append(Paragraph("Listado de clientes seleccionados", styles["Title"]))

        tabla_data = [[
            "Indice", "Zona", "Nombre Cliente", "Botica", "Referencias", "Google Maps"
        ]]

        for _, r in df_sel.iterrows():
            link = f"https://www.google.com/maps?q={r['Lat']},{r['Lng']}"
            tabla_data.append([
                r["Indice"],
                f"{r['ZonaNombre']} ({r['CodigoZona']})",
                r["NombreCliente"],
                r["Botica"],
                r["Referencias"],
                Paragraph(f'<link href="{link}">Abrir</link>', styles["Normal"])
            ])

        tabla = Table(tabla_data, repeatRows=1)
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
        ]))

        elementos.append(tabla)
        elementos.append(PageBreak())

        # Convertir mapa a imagen
        img_data = m._to_png(5)
        img = Image(BytesIO(img_data), width=500, height=350)

        elementos.append(Paragraph("Mapa de clientes", styles["Title"]))
        elementos.append(img)

        doc.build(elementos)
        buffer.seek(0)

        st.download_button(
            "⬇️ Descargar PDF",
            buffer,
            file_name="clientes_seleccionados.pdf",
            mime="application/pdf"
        )

else:
    st.warning("Selecciona al menos una zona.")
