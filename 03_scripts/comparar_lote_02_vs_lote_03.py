from pathlib import Path
import json
import pandas as pd
from datetime import datetime

L02 = Path("04_salidas_normalizadas/lote_02_productos_hugo_10000_v120")
L03 = Path("04_salidas_normalizadas/lote_03_productos_hugo_10000_v120")
REPORTES = Path("05_reportes")

PRODUCTOS = 10000

def leer_tabla(path):
    return pd.read_csv(
        path,
        sep=";",
        dtype=str,
        encoding="utf-8-sig",
        low_memory=False,
    ).fillna("")

def resumen_carpeta(base):
    salida = {}
    for p in sorted(base.glob("*.csv")):
        df = leer_tabla(p)
        salida[p.name] = {
            "filas": int(len(df)),
            "columnas": int(len(df.columns)),
        }
    return salida

def mercado_restante(base):
    p = base / "producto_categoria.csv"
    if not p.exists():
        return None
    df = leer_tabla(p)
    return int((df["tipo_categoria"] == "MERCADO").sum())

res_l02 = resumen_carpeta(L02)
res_l03 = resumen_carpeta(L03)

tablas = sorted(set(res_l02) | set(res_l03))
comparativo = []

for tabla in tablas:
    filas_l02 = res_l02.get(tabla, {}).get("filas", 0)
    filas_l03 = res_l03.get(tabla, {}).get("filas", 0)
    columnas_l02 = res_l02.get(tabla, {}).get("columnas", 0)
    columnas_l03 = res_l03.get(tabla, {}).get("columnas", 0)

    diferencia = filas_l03 - filas_l02

    if filas_l02 == 0 and filas_l03 > 0:
        estado = "APARECE_EN_LOTE_03"
    elif filas_l02 > 0 and filas_l03 == 0:
        estado = "DESAPARECE_EN_LOTE_03"
    elif columnas_l02 != columnas_l03:
        estado = "CAMBIO_COLUMNAS"
    else:
        estado = "COMPARABLE"

    comparativo.append({
        "tabla": tabla,
        "filas_lote_02": int(filas_l02),
        "columnas_lote_02": int(columnas_l02),
        "filas_lote_03": int(filas_l03),
        "columnas_lote_03": int(columnas_l03),
        "diferencia_filas": int(diferencia),
        "estado": estado,
    })

df = pd.DataFrame(comparativo)

out = {
    "fecha_generacion": datetime.now().isoformat(timespec="seconds"),
    "comparacion": "lote_02_vs_lote_03",
    "normalizador": "v1.20.0",
    "productos_por_lote": PRODUCTOS,
    "lote_02": {
        "carpeta": str(L02),
        "tablas": int(len(res_l02)),
        "mercado_restante_producto_categoria": mercado_restante(L02),
    },
    "lote_03": {
        "carpeta": str(L03),
        "tablas": int(len(res_l03)),
        "mercado_restante_producto_categoria": mercado_restante(L03),
    },
    "tablas_aparecen_en_lote_03": df[df["estado"] == "APARECE_EN_LOTE_03"]["tabla"].tolist(),
    "tablas_desaparecen_en_lote_03": df[df["estado"] == "DESAPARECE_EN_LOTE_03"]["tabla"].tolist(),
    "tablas_cambio_columnas": df[df["estado"] == "CAMBIO_COLUMNAS"]["tabla"].tolist(),
    "comparativo": comparativo,
}

json_path = REPORTES / "comparativo_lote_02_vs_lote_03_10000_v120.json"
csv_path = REPORTES / "comparativo_lote_02_vs_lote_03_10000_v120.csv"

json_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
df.to_csv(csv_path, sep=";", index=False, encoding="utf-8-sig")

print(f"JSON generado: {json_path}")
print(f"CSV generado: {csv_path}")
print("Estado: OK")
print("")
print(df.to_string(index=False))
