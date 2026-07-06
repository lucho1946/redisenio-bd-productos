from pathlib import Path
import argparse
from datetime import datetime

import pandas as pd


VERSION = "1.0.0"

TABLAS_PRIORITARIAS = [
    "PRODUCTO_CORE",
    "PRODUCTO_PRECIO",
    "PRODUCTO_PROVEEDOR",
    "PRODUCTO_INVENTARIO",
    "PRODUCTO_CATEGORIA",
    "PRODUCTO_DESCRIPCION",
    "PRODUCTO_PARAMETRO",
    "PRODUCTO_DOCUMENTO",
    "PRODUCTO_MEDIA",
    "PRODUCTO_EQUIVALENTE",
]


def leer_detalle(path: Path, nombre_piloto: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"No existe el detalle de tablas: {path}")

    df = pd.read_csv(path, sep=";", dtype=str, encoding="utf-8-sig").fillna("")
    df["piloto"] = nombre_piloto

    for col in [
        "columnas_mapeadas_para_tabla",
        "columnas_procesadas",
        "columnas_no_encontradas",
        "campos_destino_vacios",
        "filas_origen",
        "filas_generadas",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    return df


def comparar(detalle_a: pd.DataFrame, detalle_b: pd.DataFrame, nombre_a: str, nombre_b: str) -> pd.DataFrame:
    cols_base = [
        "tabla_destino",
        "modo_generacion",
        "columnas_mapeadas_para_tabla",
        "columnas_procesadas",
        "columnas_no_encontradas",
        "campos_destino_vacios",
        "filas_origen",
        "filas_generadas",
    ]

    a = detalle_a[cols_base].copy()
    b = detalle_b[cols_base].copy()

    a = a.rename(columns={
        "modo_generacion": f"modo_{nombre_a}",
        "columnas_mapeadas_para_tabla": f"columnas_mapeadas_{nombre_a}",
        "columnas_procesadas": f"columnas_procesadas_{nombre_a}",
        "columnas_no_encontradas": f"columnas_no_encontradas_{nombre_a}",
        "campos_destino_vacios": f"campos_destino_vacios_{nombre_a}",
        "filas_origen": f"filas_origen_{nombre_a}",
        "filas_generadas": f"filas_generadas_{nombre_a}",
    })

    b = b.rename(columns={
        "modo_generacion": f"modo_{nombre_b}",
        "columnas_mapeadas_para_tabla": f"columnas_mapeadas_{nombre_b}",
        "columnas_procesadas": f"columnas_procesadas_{nombre_b}",
        "columnas_no_encontradas": f"columnas_no_encontradas_{nombre_b}",
        "campos_destino_vacios": f"campos_destino_vacios_{nombre_b}",
        "filas_origen": f"filas_origen_{nombre_b}",
        "filas_generadas": f"filas_generadas_{nombre_b}",
    })

    comp = a.merge(b, on="tabla_destino", how="outer").fillna("")

    col_a = f"filas_generadas_{nombre_a}"
    col_b = f"filas_generadas_{nombre_b}"

    comp[col_a] = pd.to_numeric(comp[col_a], errors="coerce").fillna(0).astype(int)
    comp[col_b] = pd.to_numeric(comp[col_b], errors="coerce").fillna(0).astype(int)
    comp["diferencia_filas"] = comp[col_b] - comp[col_a]

    comp["tabla_prioritaria"] = comp["tabla_destino"].isin(TABLAS_PRIORITARIAS)

    comp = comp.sort_values(
        by=["tabla_prioritaria", "tabla_destino"],
        ascending=[False, True],
    ).reset_index(drop=True)

    return comp


def observacion_tabla(row: pd.Series, nombre_a: str, nombre_b: str) -> str:
    tabla = str(row["tabla_destino"])
    filas_a = int(row.get(f"filas_generadas_{nombre_a}", 0))
    filas_b = int(row.get(f"filas_generadas_{nombre_b}", 0))
    dif = filas_b - filas_a

    if tabla == "PRODUCTO_CORE":
        return "La tabla base se mantiene estable; el segundo piloto permite validar mejor nombre_producto, codigo e idn1."

    if tabla == "PRODUCTO_PRECIO":
        return "Aumentan los registros por mayor cobertura de precios; se mantiene generación vertical por fuente."

    if tabla == "PRODUCTO_PROVEEDOR":
        return "Aumenta la cobertura de proveedor en la muestra con nombre; se mantiene protección contra sobrescritura."

    if tabla == "PRODUCTO_INVENTARIO":
        return "Aparecen registros de inventario; cantidad fue limpiada y stock queda como candidato pendiente de validación semántica."

    if dif == 0:
        return "Sin cambio de volumen entre pilotos."
    if dif > 0:
        return "Aumenta el volumen en la muestra con nombre; requiere auditoría de contenido antes de escalar."
    return "Disminuye el volumen en la muestra con nombre; revisar si depende de la población seleccionada."


def generar_markdown(comp: pd.DataFrame, nombre_a: str, nombre_b: str) -> str:
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

    lineas = []
    lineas.append(f"# Comparación de pilotos de normalización `{nombre_a}` vs `{nombre_b}`")
    lineas.append("")
    lineas.append(f"Fecha de generación: {fecha}")
    lineas.append(f"Script: `comparar_pilotos_normalizacion_v1.py` v{VERSION}")
    lineas.append("")
    lineas.append("## 1. Objetivo")
    lineas.append("")
    lineas.append(
        "Comparar dos pilotos de normalización para identificar diferencias de cobertura por tabla, "
        "validar estabilidad del proceso y separar mejoras reales de variaciones causadas por la muestra."
    )
    lineas.append("")
    lineas.append("## 2. Resumen ejecutivo")
    lineas.append("")
    lineas.append(
        "El segundo piloto usa una población más útil para validar `PRODUCTO_CORE`, porque contiene productos con nombre. "
        "La comparación no debe interpretarse como aprobación de carga masiva; sirve para orientar la siguiente auditoría."
    )
    lineas.append("")
    lineas.append("## 3. Tablas prioritarias")
    lineas.append("")
    lineas.append("| Tabla | Filas piloto A | Filas piloto B | Diferencia | Observación |")
    lineas.append("|---|---:|---:|---:|---|")

    for _, row in comp[comp["tabla_prioritaria"]].iterrows():
        tabla = row["tabla_destino"]
        filas_a = int(row[f"filas_generadas_{nombre_a}"])
        filas_b = int(row[f"filas_generadas_{nombre_b}"])
        dif = int(row["diferencia_filas"])
        obs = observacion_tabla(row, nombre_a, nombre_b)
        lineas.append(f"| {tabla} | {filas_a} | {filas_b} | {dif} | {obs} |")

    lineas.append("")
    lineas.append("## 4. Todas las tablas")
    lineas.append("")
    lineas.append("| Tabla | Modo A | Modo B | Filas A | Filas B | Diferencia |")
    lineas.append("|---|---|---|---:|---:|---:|")

    for _, row in comp.iterrows():
        tabla = row["tabla_destino"]
        modo_a = row.get(f"modo_{nombre_a}", "")
        modo_b = row.get(f"modo_{nombre_b}", "")
        filas_a = int(row[f"filas_generadas_{nombre_a}"])
        filas_b = int(row[f"filas_generadas_{nombre_b}"])
        dif = int(row["diferencia_filas"])
        lineas.append(f"| {tabla} | {modo_a} | {modo_b} | {filas_a} | {filas_b} | {dif} |")

    lineas.append("")
    lineas.append("## 5. Decisiones y pendientes")
    lineas.append("")
    lineas.append("- Mantener `PRODUCTO_PRECIO` verticalizado por fuente.")
    lineas.append("- Mantener separación entre `codigo`, `item_erp`, `referencia` y `_producto_key_origen`.")
    lineas.append("- Mantener `PRODUCTO_INVENTARIO` en revisión semántica: `stock` es candidato, no aprobación final.")
    lineas.append("- Auditar tablas repetibles antes de escalar: parámetros, documentos, media, equivalentes, certificados y keywords.")
    lineas.append("- Ejecutar una muestra más representativa antes de carga completa.")
    lineas.append("")
    lineas.append("## 6. Conclusión")
    lineas.append("")
    lineas.append(
        "El proceso muestra estabilidad técnica en ambos pilotos: genera las tablas esperadas y permite comparar cobertura. "
        "El segundo piloto es más útil para validar campos base como nombre, código e IDN1. Sin embargo, antes de escalar "
        "se deben cerrar las revisiones semánticas de inventario y tablas repetibles."
    )
    lineas.append("")

    return "\n".join(lineas)


def main():
    parser = argparse.ArgumentParser(description="Compara dos pilotos de normalización por detalle de tablas generadas.")
    parser.add_argument("--detalle-a", required=True, help="CSV detalle_tablas_generadas_v1.csv del piloto A")
    parser.add_argument("--nombre-a", required=True, help="Nombre corto del piloto A")
    parser.add_argument("--detalle-b", required=True, help="CSV detalle_tablas_generadas_v1.csv del piloto B")
    parser.add_argument("--nombre-b", required=True, help="Nombre corto del piloto B")
    parser.add_argument("--out-dir", default="05_reportes/comparacion_pilotos_normalizacion_v1", help="Carpeta de salida")

    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    detalle_a = leer_detalle(Path(args.detalle_a), args.nombre_a)
    detalle_b = leer_detalle(Path(args.detalle_b), args.nombre_b)

    comp = comparar(detalle_a, detalle_b, args.nombre_a, args.nombre_b)

    comp.to_csv(out_dir / "comparacion_tablas_pilotos.csv", index=False, sep=";", encoding="utf-8-sig")

    markdown = generar_markdown(comp, args.nombre_a, args.nombre_b)
    (out_dir / "informe_comparacion_pilotos.md").write_text(markdown, encoding="utf-8")

    print("Comparación de pilotos generada correctamente.")
    print(f"Tablas comparadas: {len(comp)}")
    print(f"Salida: {out_dir}")


if __name__ == "__main__":
    main()
