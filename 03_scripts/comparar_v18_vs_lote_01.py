from pathlib import Path
import json
import pandas as pd
from datetime import datetime

V18 = Path("04_salidas_normalizadas/piloto_productos_hugo_muestra_v18_5000")
L01 = Path("04_salidas_normalizadas/lote_01_productos_hugo_10000_v120")
REPORTES = Path("05_reportes")
ENTREGABLES = Path("06_entregables")

REPORTES.mkdir(parents=True, exist_ok=True)
ENTREGABLES.mkdir(parents=True, exist_ok=True)

PRODUCTOS_V18 = 5000
PRODUCTOS_L01 = 10000

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

res_v18 = resumen_carpeta(V18)
res_l01 = resumen_carpeta(L01)

tablas = sorted(set(res_v18) | set(res_l01))
comparativo = []

for tabla in tablas:
    filas_v18 = res_v18.get(tabla, {}).get("filas", 0)
    filas_l01 = res_l01.get(tabla, {}).get("filas", 0)
    columnas_v18 = res_v18.get(tabla, {}).get("columnas", 0)
    columnas_l01 = res_l01.get(tabla, {}).get("columnas", 0)

    por_1000_v18 = round(filas_v18 / PRODUCTOS_V18 * 1000, 2)
    por_1000_l01 = round(filas_l01 / PRODUCTOS_L01 * 1000, 2)
    diferencia_por_1000 = round(por_1000_l01 - por_1000_v18, 2)

    if filas_v18 == 0 and filas_l01 > 0:
        estado = "APARECE_EN_LOTE_01"
    elif filas_v18 > 0 and filas_l01 == 0:
        estado = "DESAPARECE_EN_LOTE_01"
    elif columnas_v18 != columnas_l01:
        estado = "CAMBIO_COLUMNAS"
    else:
        estado = "COMPARABLE"

    comparativo.append({
        "tabla": tabla,
        "filas_v18": int(filas_v18),
        "columnas_v18": int(columnas_v18),
        "filas_lote_01": int(filas_l01),
        "columnas_lote_01": int(columnas_l01),
        "filas_por_1000_v18": por_1000_v18,
        "filas_por_1000_lote_01": por_1000_l01,
        "diferencia_por_1000": diferencia_por_1000,
        "estado": estado,
    })

df_comp = pd.DataFrame(comparativo)

def mercado_restante(base):
    path = base / "producto_categoria.csv"
    if not path.exists():
        return None
    df = leer_tabla(path)
    if "tipo_categoria" not in df.columns:
        return None
    return int((df["tipo_categoria"] == "MERCADO").sum())

resumen = {
    "fecha_generacion": datetime.now().isoformat(timespec="seconds"),
    "comparacion": "piloto_v18_vs_lote_01",
    "piloto_v18": {
        "productos": PRODUCTOS_V18,
        "carpeta": str(V18),
        "tablas": int(len(res_v18)),
        "mercado_restante_producto_categoria": mercado_restante(V18),
    },
    "lote_01": {
        "productos": PRODUCTOS_L01,
        "carpeta": str(L01),
        "tablas": int(len(res_l01)),
        "mercado_restante_producto_categoria": mercado_restante(L01),
    },
    "total_tablas_comparadas": int(len(tablas)),
    "tablas_aparecen_en_lote_01": df_comp[df_comp["estado"] == "APARECE_EN_LOTE_01"]["tabla"].tolist(),
    "tablas_desaparecen_en_lote_01": df_comp[df_comp["estado"] == "DESAPARECE_EN_LOTE_01"]["tabla"].tolist(),
    "tablas_cambio_columnas": df_comp[df_comp["estado"] == "CAMBIO_COLUMNAS"]["tabla"].tolist(),
    "comparativo": comparativo,
}

json_path = REPORTES / "comparativo_v18_vs_lote_01_10000_v120.json"
csv_path = REPORTES / "comparativo_v18_vs_lote_01_10000_v120.csv"

json_path.write_text(
    json.dumps(resumen, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

df_comp.to_csv(csv_path, index=False, sep=";", encoding="utf-8-sig")

print(f"JSON generado: {json_path}")
print(f"CSV generado: {csv_path}")
print("Estado: OK")
print("")
print(df_comp.to_string(index=False))
