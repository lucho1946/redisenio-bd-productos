from pathlib import Path
import argparse
import json
from datetime import datetime

import pandas as pd


VERSION = "1.0.0"

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

CAMPOS_CORE_PRIORITARIOS = [
    "_origen_row",
    "_producto_key_origen",
    "_codigo_origen",
    "codigo",
    "referencia",
    "item_erp",
    "nombre_producto",
    "idn1",
    "idn4",
    "activo",
    "unidad_medida",
]


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
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {path}")
    return pd.read_csv(path, sep=";", dtype=str, encoding="utf-8-sig").fillna("")


def calcular_cobertura(df: pd.DataFrame) -> list[dict]:
    filas = []
    total = len(df)

    for campo in CAMPOS_CORE_PRIORITARIOS:
        if campo not in df.columns:
            filas.append({
                "campo": campo,
                "existe": False,
                "filas_total": total,
                "filas_materiales": 0,
                "porcentaje_materialidad": 0.0,
                "valores_unicos_materiales": 0,
                "valores_duplicados_materiales": 0,
                "primeros_ejemplos_materiales": "",
            })
            continue

        serie = df[campo].astype(str).fillna("").str.strip()
        mask_material = serie.map(valor_es_material)
        materiales = serie[mask_material]
        filas_materiales = int(mask_material.sum())
        unicos_materiales = int(materiales.nunique(dropna=True))
        duplicados_materiales = int(filas_materiales - unicos_materiales)
        ejemplos = materiales.drop_duplicates().head(8).tolist()

        porcentaje = round((filas_materiales / total) * 100, 2) if total else 0.0

        filas.append({
            "campo": campo,
            "existe": True,
            "filas_total": total,
            "filas_materiales": filas_materiales,
            "porcentaje_materialidad": porcentaje,
            "valores_unicos_materiales": unicos_materiales,
            "valores_duplicados_materiales": duplicados_materiales,
            "primeros_ejemplos_materiales": " | ".join(ejemplos),
        })

    return filas


def detectar_anomalias(df: pd.DataFrame) -> list[dict]:
    anomalias = []
    total = len(df)

    if "_producto_key_origen" in df.columns:
        serie = df["_producto_key_origen"].astype(str).str.strip()
        vacios = int((~serie.map(valor_es_material)).sum())
        duplicados = int(serie[serie.map(valor_es_material)].duplicated().sum())
        if vacios:
            anomalias.append({
                "tipo": "KEY_ORIGEN_VACIA",
                "severidad": "ALTA",
                "detalle": f"Hay {vacios} filas sin _producto_key_origen material.",
            })
        if duplicados:
            anomalias.append({
                "tipo": "KEY_ORIGEN_DUPLICADA",
                "severidad": "MEDIA",
                "detalle": f"Hay {duplicados} ocurrencias duplicadas en _producto_key_origen. Revisar si corresponden a duplicados reales de origen.",
            })
    else:
        anomalias.append({
            "tipo": "KEY_ORIGEN_NO_EXISTE",
            "severidad": "ALTA",
            "detalle": "No existe la columna _producto_key_origen en producto_core.",
        })

    if "codigo" in df.columns and "_codigo_origen" in df.columns:
        codigo = df["codigo"].astype(str).str.strip()
        codigo_origen = df["_codigo_origen"].astype(str).str.strip()
        mask_codigo = codigo.map(valor_es_material)
        mask_codigo_origen = codigo_origen.map(valor_es_material)
        inconsistentes = int((mask_codigo != mask_codigo_origen).sum())
        if inconsistentes:
            anomalias.append({
                "tipo": "CODIGO_VS_CODIGO_ORIGEN_DIFERENTE",
                "severidad": "MEDIA",
                "detalle": f"Hay {inconsistentes} filas donde codigo y _codigo_origen difieren en materialidad.",
            })

    if "nombre_producto" in df.columns:
        nombre = df["nombre_producto"].astype(str).str.strip()
        nombres_materiales = int(nombre.map(valor_es_material).sum())
        if total and nombres_materiales / total < 0.5:
            anomalias.append({
                "tipo": "BAJA_COBERTURA_NOMBRE_PRODUCTO",
                "severidad": "ALTA",
                "detalle": f"nombre_producto tiene {nombres_materiales}/{total} filas materiales. Revisar mapeo y fuente real del nombre.",
            })

    return anomalias


def generar_markdown(resumen: dict, cobertura: list[dict], anomalias: list[dict]) -> str:
    lineas = []
    lineas.append("# Auditoría de PRODUCTO_CORE normalizado")
    lineas.append("")
    lineas.append(f"Fecha de generación: {resumen['fecha_generacion']}")
    lineas.append(f"Script: `auditar_producto_core_v1.py` v{VERSION}")
    lineas.append(f"Archivo auditado: `{resumen['archivo_core']}`")
    lineas.append("")
    lineas.append("## 1. Resumen")
    lineas.append("")
    lineas.append("| Control | Resultado |")
    lineas.append("|---|---:|")
    lineas.append(f"| Filas auditadas | {resumen['filas']} |")
    lineas.append(f"| Columnas auditadas | {resumen['columnas']} |")
    lineas.append(f"| Anomalías detectadas | {len(anomalias)} |")
    lineas.append("")
    lineas.append("## 2. Cobertura de campos prioritarios")
    lineas.append("")
    lineas.append("| Campo | Existe | Filas materiales | % materialidad | Únicos materiales | Duplicados materiales | Ejemplos |")
    lineas.append("|---|---:|---:|---:|---:|---:|---|")
    for row in cobertura:
        lineas.append(
            f"| {row['campo']} | {row['existe']} | {row['filas_materiales']} | "
            f"{row['porcentaje_materialidad']} | {row['valores_unicos_materiales']} | "
            f"{row['valores_duplicados_materiales']} | {row['primeros_ejemplos_materiales']} |"
        )
    lineas.append("")
    lineas.append("## 3. Anomalías")
    lineas.append("")
    if not anomalias:
        lineas.append("No se detectaron anomalías críticas en los controles definidos.")
    else:
        lineas.append("| Tipo | Severidad | Detalle |")
        lineas.append("|---|---|---|")
        for anomalia in anomalias:
            lineas.append(
                f"| {anomalia['tipo']} | {anomalia['severidad']} | {anomalia['detalle']} |"
            )
    lineas.append("")
    lineas.append("## 4. Interpretación")
    lineas.append("")
    lineas.append(
        "Esta auditoría no modifica datos. Su objetivo es medir si `PRODUCTO_CORE` puede funcionar "
        "como tabla base confiable antes de escalar el proceso. Los campos con baja cobertura o con "
        "ambigüedad deben revisarse contra la fuente original y el mapeo antes de hacer cambios de carga."
    )
    lineas.append("")
    return "\n".join(lineas)


def main():
    parser = argparse.ArgumentParser(
        description="Audita cobertura y anomalías básicas de producto_core.csv."
    )
    parser.add_argument(
        "--core",
        default="04_salidas_normalizadas/piloto_productos_hugo_top1000_v7/producto_core.csv",
        help="Ruta del producto_core.csv normalizado a auditar.",
    )
    parser.add_argument(
        "--out-dir",
        default="05_reportes/auditoria_producto_core_v1",
        help="Carpeta de salida para reportes de auditoría.",
    )

    args = parser.parse_args()
    core_path = Path(args.core)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = leer_csv(core_path)
    cobertura = calcular_cobertura(df)
    anomalias = detectar_anomalias(df)

    resumen = {
        "script": "auditar_producto_core_v1.py",
        "version": VERSION,
        "fecha_generacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "archivo_core": str(core_path),
        "filas": int(len(df)),
        "columnas": int(len(df.columns)),
        "anomalias_detectadas": len(anomalias),
    }

    (out_dir / "resumen_producto_core.json").write_text(
        json.dumps({
            "resumen": resumen,
            "cobertura": cobertura,
            "anomalias": anomalias,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    pd.DataFrame(cobertura).to_csv(
        out_dir / "cobertura_producto_core.csv",
        index=False,
        sep=";",
        encoding="utf-8-sig",
    )

    pd.DataFrame(anomalias).to_csv(
        out_dir / "anomalias_producto_core.csv",
        index=False,
        sep=";",
        encoding="utf-8-sig",
    )

    markdown = generar_markdown(
        resumen=resumen,
        cobertura=cobertura,
        anomalias=anomalias,
    )
    (out_dir / "informe_auditoria_producto_core.md").write_text(markdown, encoding="utf-8")

    print("Auditoría de PRODUCTO_CORE generada correctamente.")
    print(f"Filas auditadas: {len(df)}")
    print(f"Anomalías detectadas: {len(anomalias)}")
    print(f"Salida: {out_dir}")


if __name__ == "__main__":
    main()
