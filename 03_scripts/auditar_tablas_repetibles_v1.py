from pathlib import Path
import argparse
import json
from datetime import datetime

import pandas as pd


VERSION = "1.0.0"

TABLAS_REPETIBLES = [
    "producto_parametro",
    "producto_documento",
    "producto_media",
    "producto_equivalente",
    "producto_keyword",
    "producto_certificado",
]

VALORES_NO_MATERIALES = {
    "",
    " ",
    "nan",
    "none",
    "null",
    "n/a",
    "na",
    "no",
    "false",
    "0",
    "0.0",
    "0.00",
    "0,0",
    "0,00",
}

COLUMNAS_TRAZABILIDAD = {
    "_origen_row",
    "_producto_key_origen",
    "_codigo_origen",
}


def valor_es_material(valor) -> bool:
    if valor is None:
        return False
    if pd.isna(valor):
        return False
    texto = str(valor).strip()
    if not texto:
        return False
    return texto.lower() not in VALORES_NO_MATERIALES


def leer_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep=";", dtype=str, encoding="utf-8-sig").fillna("")


def auditar_tabla(path_csv: Path, tabla: str) -> tuple[dict, list[dict]]:
    if not path_csv.exists():
        return {
            "tabla": tabla,
            "archivo_existe": False,
            "filas": 0,
            "columnas": 0,
            "productos_unicos": 0,
            "filas_por_producto_promedio": 0,
            "filas_por_producto_max": 0,
            "campos_negocio": 0,
            "campos_negocio_con_materialidad": 0,
            "estado_auditoria": "ARCHIVO_NO_ENCONTRADO",
        }, []

    df = leer_csv(path_csv)
    filas = len(df)
    columnas = len(df.columns)

    if "_producto_key_origen" in df.columns:
        serie_key = df["_producto_key_origen"].astype(str).str.strip()
        productos_unicos = int(serie_key[serie_key.map(valor_es_material)].nunique())
        conteo_por_producto = serie_key[serie_key.map(valor_es_material)].value_counts()
        filas_por_producto_promedio = round(float(conteo_por_producto.mean()), 2) if not conteo_por_producto.empty else 0
        filas_por_producto_max = int(conteo_por_producto.max()) if not conteo_por_producto.empty else 0
    else:
        productos_unicos = 0
        filas_por_producto_promedio = 0
        filas_por_producto_max = 0

    campos_negocio = [c for c in df.columns if c not in COLUMNAS_TRAZABILIDAD]
    detalle_campos = []
    campos_con_materialidad = 0

    for campo in campos_negocio:
        serie = df[campo].astype(str).str.strip()
        mask = serie.map(valor_es_material)
        materiales = int(mask.sum())
        if materiales > 0:
            campos_con_materialidad += 1
        ejemplos = serie[mask].drop_duplicates().head(8).tolist()
        detalle_campos.append({
            "tabla": tabla,
            "campo": campo,
            "filas_total": filas,
            "filas_materiales": materiales,
            "porcentaje_materialidad": round((materiales / filas) * 100, 2) if filas else 0,
            "valores_unicos_materiales": int(serie[mask].nunique()) if filas else 0,
            "ejemplos": " | ".join(ejemplos),
        })

    estado = "REVISION_HUMANA"
    if filas == 0:
        estado = "SIN_FILAS_GENERADAS"
    elif campos_con_materialidad == 0:
        estado = "SIN_CAMPOS_NEGOCIO_MATERIALES"
    elif filas_por_producto_max > 1:
        estado = "REPETIBLE_CONFIRMADA_POR_MULTIPLES_FILAS"
    else:
        estado = "HORIZONTAL_CON_UNA_FILA_POR_PRODUCTO"

    resumen = {
        "tabla": tabla,
        "archivo_existe": True,
        "filas": int(filas),
        "columnas": int(columnas),
        "productos_unicos": int(productos_unicos),
        "filas_por_producto_promedio": filas_por_producto_promedio,
        "filas_por_producto_max": filas_por_producto_max,
        "campos_negocio": int(len(campos_negocio)),
        "campos_negocio_con_materialidad": int(campos_con_materialidad),
        "estado_auditoria": estado,
    }

    return resumen, detalle_campos


def generar_markdown(resumen: list[dict], detalle: list[dict], salida_dir_piloto: str) -> str:
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    lineas = []
    lineas.append("# Auditoría de tablas repetibles")
    lineas.append("")
    lineas.append(f"Fecha de generación: {fecha}")
    lineas.append(f"Script: `auditar_tablas_repetibles_v1.py` v{VERSION}")
    lineas.append(f"Salida auditada: `{salida_dir_piloto}`")
    lineas.append("")
    lineas.append("## 1. Objetivo")
    lineas.append("")
    lineas.append(
        "Revisar tablas con posible estructura repetible antes de escalar el proceso. "
        "El objetivo es identificar si una tabla realmente representa múltiples registros por producto "
        "o si todavía está en formato horizontal y requiere una transformación similar a precios."
    )
    lineas.append("")
    lineas.append("## 2. Resumen por tabla")
    lineas.append("")
    lineas.append("| Tabla | Filas | Productos únicos | Promedio filas/producto | Máximo filas/producto | Campos negocio materiales | Estado |")
    lineas.append("|---|---:|---:|---:|---:|---:|---|")
    for row in resumen:
        lineas.append(
            f"| {row['tabla']} | {row['filas']} | {row['productos_unicos']} | "
            f"{row['filas_por_producto_promedio']} | {row['filas_por_producto_max']} | "
            f"{row['campos_negocio_con_materialidad']} | {row['estado_auditoria']} |"
        )
    lineas.append("")
    lineas.append("## 3. Campos con mayor materialidad")
    lineas.append("")
    lineas.append("| Tabla | Campo | Filas materiales | % materialidad | Únicos | Ejemplos |")
    lineas.append("|---|---|---:|---:|---:|---|")

    detalle_df = pd.DataFrame(detalle)
    if not detalle_df.empty:
        detalle_df = detalle_df.sort_values(
            by=["tabla", "filas_materiales"],
            ascending=[True, False],
        )
        for _, row in detalle_df.groupby("tabla").head(8).iterrows():
            lineas.append(
                f"| {row['tabla']} | {row['campo']} | {int(row['filas_materiales'])} | "
                f"{row['porcentaje_materialidad']} | {int(row['valores_unicos_materiales'])} | {row['ejemplos']} |"
            )

    lineas.append("")
    lineas.append("## 4. Interpretación")
    lineas.append("")
    lineas.append(
        "Las tablas marcadas como `HORIZONTAL_CON_UNA_FILA_POR_PRODUCTO` pueden contener datos útiles, "
        "pero todavía no prueban una estructura repetible real. Las tablas con múltiples filas por producto "
        "pueden requerir validación de cardinalidad, deduplicación o verticalización. Ninguna tabla debe aprobarse "
        "para carga masiva sin revisar los campos materiales y su semántica."
    )
    lineas.append("")
    return "\n".join(lineas)


def main():
    parser = argparse.ArgumentParser(description="Audita tablas repetibles generadas por el piloto de normalización.")
    parser.add_argument(
        "--salida-piloto",
        required=True,
        help="Carpeta con CSV normalizados del piloto, por ejemplo 04_salidas_normalizadas/piloto_productos_hugo_con_nombre_top1000_v2",
    )
    parser.add_argument(
        "--out-dir",
        default="05_reportes/auditoria_tablas_repetibles_v1",
        help="Carpeta de salida para reportes.",
    )

    args = parser.parse_args()
    salida_piloto = Path(args.salida_piloto)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    resumen = []
    detalle = []

    for tabla in TABLAS_REPETIBLES:
        path_csv = salida_piloto / f"{tabla}.csv"
        resumen_tabla, detalle_tabla = auditar_tabla(path_csv, tabla)
        resumen.append(resumen_tabla)
        detalle.extend(detalle_tabla)

    pd.DataFrame(resumen).to_csv(out_dir / "resumen_tablas_repetibles.csv", index=False, sep=";", encoding="utf-8-sig")
    pd.DataFrame(detalle).to_csv(out_dir / "detalle_campos_tablas_repetibles.csv", index=False, sep=";", encoding="utf-8-sig")

    payload = {
        "script": "auditar_tablas_repetibles_v1.py",
        "version": VERSION,
        "fecha_generacion": datetime.now().isoformat(),
        "salida_piloto": str(salida_piloto),
        "resumen": resumen,
        "detalle": detalle,
    }
    (out_dir / "auditoria_tablas_repetibles.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    markdown = generar_markdown(resumen, detalle, str(salida_piloto))
    (out_dir / "informe_auditoria_tablas_repetibles.md").write_text(markdown, encoding="utf-8")

    print("Auditoría de tablas repetibles generada correctamente.")
    print(f"Tablas auditadas: {len(resumen)}")
    print(f"Salida: {out_dir}")


if __name__ == "__main__":
    main()
