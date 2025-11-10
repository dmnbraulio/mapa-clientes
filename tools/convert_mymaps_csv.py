"""
convert_mymaps_csv.py
------------------------
Uso:
    python convert_mymaps_csv.py

Descripción:
    Lee un CSV exportado desde Google MyMaps con encabezados parecidos a:
        WKT, nombre, descripciÃ³n
    - Extrae lat/lng desde "POINT (lon lat)".
    - Corrige problemas de codificación (mojibake como "descripciÃ³n").
    - Extrae campos estandarizados desde la columna de descripción (separada por " - "):
        ZonaCodigo - ZonaNombre - CodigoCliente - NombreCliente - Referencias
    - Conserva el 'nombre' original del marcador como 'Botica'.
    - Genera un CSV limpio con columnas:
        CodigoZona,ZonaNombre,CodigoCliente,NombreCliente,Referencias,Botica,Lat,Lng,DireccionOpcional,...
    - Si faltan partes en la descripción, las llena con 'x'.
"""

import sys
import os
import re
import pandas as pd
import shutil              # 🔹 NUEVO: para copiar archivos
from datetime import datetime  # 🔹 NUEVO: para registrar fecha/hora del respaldo

# -----------------------------------------------------
# 🔹 CONFIGURACIÓN AUTOMÁTICA DE RUTAS (NUEVO BLOQUE)
# -----------------------------------------------------
SCRIPT_NAME = "convert_mymaps_csv.py"
BASE_DIR = r"C:\Users\Braulio\Desktop\LAFARMED\app_distribucion"
DATA_DIR = os.path.join(BASE_DIR, "data")
DATA_ORIGINALES_DIR = os.path.join(DATA_DIR, "data_originales")

# Archivo exportado por MyMaps y archivo limpio final
INPUT_FILE = os.path.join(DATA_DIR, "MAPA LAFARMED- LAFARMED CLIENTES.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "clientes.csv")

# Crear carpeta de respaldos si no existe
os.makedirs(DATA_ORIGINALES_DIR, exist_ok=True)

# -----------------------------------------------------
# 🔹 RESPALDAR CSV ORIGINAL (NUEVO BLOQUE)
# -----------------------------------------------------
if os.path.exists(INPUT_FILE):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"clientes_original_{timestamp}.csv"
    backup_path = os.path.join(DATA_ORIGINALES_DIR, backup_name)
    shutil.copy(INPUT_FILE, backup_path)
    print(f"✅ Copia de respaldo creada en: {backup_path}")
else:
    print(f"❌ ERROR: No se encontró el archivo de entrada en:\n{INPUT_FILE}")
    sys.exit(1)

# ---------------------------
# Funciones utilitarias
# ---------------------------

def extract_lon_lat_from_wkt(wkt_str):
    """
    Extrae lat y lon desde un string tipo 'POINT (lon lat)'.
    Devuelve (lat, lon) como floats; si no encuentra, devuelve (None, None).
    Nota: en WKT el orden suele ser (lon lat).
    """
    if not isinstance(wkt_str, str):
        return (None, None)
    wkt_str = wkt_str.strip().strip('"').strip("'")
    m = re.search(r'POINT\s*\(\s*([\-0-9]+(?:\.[0-9]+)?)\s+([\-0-9]+(?:\.[0-9]+)?)\s*\)', wkt_str)
    if not m:
        return (None, None)
    try:
        lon = float(m.group(1))
        lat = float(m.group(2))
        return (lat, lon)
    except Exception:
        return (None, None)

def fix_mojibake_text(s):
    """
    Arregla mojibake básico (ej.: 'descripciÃ³n' -> 'descripción').
    """
    if not isinstance(s, str):
        return s
    if 'Ã' in s or 'Â' in s:
        try:
            return s.encode('latin-1').decode('utf-8')
        except Exception:
            return s
    return s

def split_standard_description(desc):
    """
    Parte la string estandarizada por " - " en 5 campos:
      [CodigoZona, ZonaNombre, CodigoCliente, NombreCliente, Referencias]
    """
    if not isinstance(desc, str) or desc.strip() == "":
        return ["x","x","x","x","x"]
    desc = fix_mojibake_text(desc)
    desc_norm = re.sub(r'\s*[-–—]\s*', ' - ', desc.strip())
    parts = [p.strip() for p in desc_norm.split(' - ')]
    if len(parts) > 5:
        parts = parts[:4] + [' - '.join(parts[4:])]
    while len(parts) < 5:
        parts.append('x')
    return parts

# ---------------------------
# Lógica de conversión
# ---------------------------

def convert_mymaps_csv(input_path, output_path):
    """Lee input_path (CSV exportado desde MyMaps), procesa y guarda output_path."""
    try:
        df = pd.read_csv(input_path, dtype=str, encoding='utf-8')
    except Exception:
        df = pd.read_csv(input_path, dtype=str, encoding='latin-1')

    cols_lower = {c.lower(): c for c in df.columns}

    # Buscar columna WKT
    wkt_col = None
    for name in cols_lower:
        if 'wkt' in name or 'point' in name or 'geometry' in name:
            wkt_col = cols_lower[name]
            break
    if wkt_col is None:
        for c in df.columns:
            sample_vals = df[c].dropna().astype(str).head(5).tolist()
            if any(s.strip().upper().startswith('POINT') for s in sample_vals):
                wkt_col = c
                break
    if wkt_col is None:
        print("ERROR: No se encontró columna con WKT/POINT. Columnas disponibles:", df.columns.tolist())
        sys.exit(1)

    # Buscar columna 'nombre'
    nombre_col = None
    for key in cols_lower:
        if key in ['nombre','name','title','placename']:
            nombre_col = cols_lower[key]
            break
    if nombre_col is None:
        candidates = [c for c in df.columns if c != wkt_col]
        nombre_col = candidates[0] if candidates else None

    # Buscar columna 'descripción'
    descr_col = None
    for key in cols_lower:
        if 'descrip' in key or 'description' in key or 'descripción' in key or 'desc' in key:
            descr_col = cols_lower[key]
            break
    if descr_col is None:
        print("Aviso: No se encontró columna de descripción. Procederemos sin parsear descripción.")
        df['__descr_missing__'] = ''
        descr_col = '__descr_missing__'

    # Extraer lat/lng
    latitudes, longitudes = [], []
    for val in df[wkt_col].fillna('').astype(str):
        lat, lon = extract_lon_lat_from_wkt(val)
        latitudes.append(lat)
        longitudes.append(lon)
    df['Lat'], df['Lng'] = latitudes, longitudes

    # Corregir mojibake
    df[nombre_col] = df[nombre_col].astype(str).apply(fix_mojibake_text)
    df[descr_col] = df[descr_col].astype(str).apply(fix_mojibake_text)

    # Parsear descripción
    parsed = df[descr_col].apply(split_standard_description)
    parsed_df = pd.DataFrame(parsed.tolist(), columns=[
        'ZonaCodigo','ZonaNombre','CodigoCliente','NombreCliente','Referencias'
    ])

    # Construir DataFrame final
    final = pd.DataFrame()
    final['CodigoZona'] = parsed_df['ZonaCodigo'].fillna('x')
    final['ZonaNombre'] = parsed_df['ZonaNombre'].fillna('x')
    final['CodigoCliente'] = parsed_df['CodigoCliente'].fillna('x')
    final['NombreCliente'] = parsed_df['NombreCliente'].fillna('x')
    final['Referencias'] = parsed_df['Referencias'].fillna('x')
    final['Botica'] = df[nombre_col].astype(str).fillna('').str.strip()
    final['Lat'] = df['Lat']
    final['Lng'] = df['Lng']
    final['DescripcionOriginal'] = df[descr_col].astype(str)

    direccion_col = None
    for key in cols_lower:
        if key in ['direccion','address','addr','street']:
            direccion_col = cols_lower[key]
            break
    final['Direccion'] = df[direccion_col].astype(str).fillna('') if direccion_col else ''

    # Guardar CSV de salida
    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    final_cols_order = [
        'CodigoZona','ZonaNombre','CodigoCliente','NombreCliente',
        'Botica','Referencias','Direccion','Lat','Lng','DescripcionOriginal'
    ]
    final = final[final_cols_order]
    final.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"✅ Archivo limpio guardado en: {output_path}")
    print(f"Filas procesadas: {len(final)} | Filas sin coordenadas: {final['Lat'].isna().sum()}")

# ---------------------------
# Entrypoint
# ---------------------------

if __name__ == "__main__":
    # 🔹 MODIFICADO: ahora no requiere argumentos, usa rutas automáticas
    convert_mymaps_csv(INPUT_FILE, OUTPUT_FILE)

    print(f"""
🏁 Script ejecutado correctamente:
   - Script: {SCRIPT_NAME}
   - Archivo original: {INPUT_FILE}
   - Archivo limpio: {OUTPUT_FILE}
   - Copias de respaldo en: {DATA_ORIGINALES_DIR}
""")
