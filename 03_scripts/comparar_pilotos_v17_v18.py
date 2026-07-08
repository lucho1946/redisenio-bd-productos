from pathlib import Path
import json
import pandas as pd
from datetime import datetime

V17 = Path("04_salidas_normalizadas/piloto_productos_hugo_con_nombre_top1000_v17")
V18 = Path("04_salidas_normalizadas/piloto_productos_hugo_muestra_v18_5000")
REPORTES = Path("05_reportes")
ENTREGABLES = Path("06_entregables")

REPORTES.mkdir(parents=True, exist_ok=True)
ENTREGABLES.mkdir(parents=True, exist_ok=True)

PRODUCTOS_V17 = 1000
PRODUCTOS_V18 = 5000

if not V17.exists():
    raise FileNotFoundError(f"No existe carpeta v17: {V17}")

if not V18.exists():
    raise FileNotFoundError(f"No existe carpeta v18: {V18}")

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

res_v17 = resumen_carpeta(V17)
res_v18 = resumen_carpeta(V18)

tablas = sorted(set(res_v17) | set(res_v18))

comparativo = []

for tabla in tablas:
    filas_v17 = res_v17.get(tabla, {}).get("filas", 0)
    filas_v18 = res_v18.get(tabla, {}).get("filas", 0)
    columnas_v17 = res_v17.get(tabla, {}).get("columnas", 0)
    columnas_v18 = res_v18.get(tabla, {}).get("columnas", 0)

    por_1000_v17 = round(filas_v17 / PRODUCTOS_V17 * 1000, 2)
    por_1000_v18 = round(filas_v18 / PRODUCTOS_V18 * 1000, 2)

    diferencia_por_1000 = round(por_1000_v18 - por_1000_v17, 2)

    if filas_v17 == 0 and filas_v18 > 0:
        estado = "APARECE_EN_V18"
    elif filas_v17 > 0 and filas_v18 == 0:
        estado = "DESAPARECE_EN_V18"
    elif columnas_v17 != columnas_v18:
        estado = "CAMBIO_COLUMNAS"
    else:
        estado = "COMPARABLE"

    comparativo.append({
        "tabla": tabla,
        "filas_v17": int(filas_v17),
        "columnas_v17": int(columnas_v17),
        "filas_v18": int(filas_v18),
        "columnas_v18": int(columnas_v18),
        "filas_por_1000_v17": por_1000_v17,
        "filas_por_1000_v18": por_1000_v18,
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

mercado_v17 = mercado_restante(V17)
mercado_v18 = mercado_restante(V18)

resumen = {
    "fecha_generacion": datetime.now().isoformat(timespec="seconds"),
    "piloto_v17": {
        "productos": PRODUCTOS_V17,
        "carpeta": str(V17),
        "tablas": int(len(res_v17)),
        "mercado_restante_producto_categoria": mercado_v17,
    },
    "piloto_v18": {
        "productos": PRODUCTOS_V18,
        "carpeta": str(V18),
        "tablas": int(len(res_v18)),
        "mercado_restante_producto_categoria": mercado_v18,
    },
    "total_tablas_comparadas": int(len(tablas)),
    "tablas_aparecen_en_v18": df_comp[df_comp["estado"] == "APARECE_EN_V18"]["tabla"].tolist(),
    "tablas_desaparecen_en_v18": df_comp[df_comp["estado"] == "DESAPARECE_EN_V18"]["tabla"].tolist(),
    "tablas_cambio_columnas": df_comp[df_comp["estado"] == "CAMBIO_COLUMNAS"]["tabla"].tolist(),
    "comparativo": comparativo,
}

json_path = REPORTES / "comparativo_pilotos_v17_vs_v18.json"
csv_path = REPORTES / "comparativo_pilotos_v17_vs_v18.csv"
md_path = ENTREGABLES / "comparativo_pilotos_v17_vs_v18.md"

json_path.write_text(
    json.dumps(resumen, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

df_comp.to_csv(csv_path, index=False, sep=";", encoding="utf-8-sig")

lineas = []
lineas.append("# Comparativo técnico — Piloto v17 vs Piloto v18")
lineas.append("")
lineas.append(f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
lineas.append("")
lineas.append("## 1. Objetivo")
lineas.append("")
lineas.append("Comparar el comportamiento del normalizador v1.20.0 entre el piloto v17 de 1.000 productos y el piloto ampliado v18 de 5.000 productos.")
lineas.append("")
lineas.append("## 2. Resumen")
lineas.append("")
lineas.append("| Control | v17 | v18 |")
lineas.append("|---|---:|---:|")
lineas.append(f"| Productos procesados | {PRODUCTOS_V17} | {PRODUCTOS_V18} |")
lineas.append(f"| Tablas generadas | {len(res_v17)} | {len(res_v18)} |")
lineas.append(f"| MERCADO restante en PRODUCTO_CATEGORIA | {mercado_v17} | {mercado_v18} |")
lineas.append("")
lineas.append("## 3. Hallazgos principales")
lineas.append("")

if resumen["tablas_aparecen_en_v18"]:
    lineas.append("Tablas que estaban vacías o no aparecían en v17 y aparecen en v18:")
    for t in resumen["tablas_aparecen_en_v18"]:
        lineas.append(f"- {t}")
else:
    lineas.append("No se detectaron tablas nuevas en v18 frente a v17.")

lineas.append("")

if resumen["tablas_desaparecen_en_v18"]:
    lineas.append("Tablas que tenían datos en v17 y quedaron vacías en v18:")
    for t in resumen["tablas_desaparecen_en_v18"]:
        lineas.append(f"- {t}")
else:
    lineas.append("No se detectaron tablas con datos en v17 que desaparezcan en v18.")

lineas.append("")

if resumen["tablas_cambio_columnas"]:
    lineas.append("Tablas con cambio de columnas:")
    for t in resumen["tablas_cambio_columnas"]:
        lineas.append(f"- {t}")
else:
    lineas.append("No se detectaron cambios de estructura de columnas entre v17 y v18.")

lineas.append("")
lineas.append("## 4. Comparativo por tabla")
lineas.append("")
lineas.append("| Tabla | Filas v17 | Filas v18 | Por 1000 v17 | Por 1000 v18 | Diferencia por 1000 | Estado |")
lineas.append("|---|---:|---:|---:|---:|---:|---|")

for item in comparativo:
    lineas.append(
        f"| {item['tabla']} | {item['filas_v17']} | {item['filas_v18']} | "
        f"{item['filas_por_1000_v17']} | {item['filas_por_1000_v18']} | "
        f"{item['diferencia_por_1000']} | {item['estado']} |"
    )

lineas.append("")
lineas.append("## 5. Conclusión provisional")
lineas.append("")
lineas.append("El piloto v18 permite validar el comportamiento del normalizador sobre una muestra cinco veces mayor que v17. El comparativo debe revisarse antes de escalar a una muestra mayor o a carga completa.")
lineas.append("")
lineas.append("Este comparativo no autoriza carga masiva ni modificación de SQL Server o Azure.")

md_path.write_text("\n".join(lineas), encoding="utf-8")

print(f"JSON generado: {json_path}")
print(f"CSV generado: {csv_path}")
print(f"MD generado: {md_path}")
print("Estado: OK")
print("")
print(df_comp.to_string(index=False))
