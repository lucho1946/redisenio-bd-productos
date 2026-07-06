from pathlib import Path
import argparse
import json
from datetime import datetime

import pandas as pd


VERSION = "1.0.0"

CAMPOS_PRIORITARIOS = [
    "cantidad",
    "stock",
    "dias_estimados",
    "fecha_stock",
    "stock_id",
    "existencia_maxima",
    "existencia_minima",
    "punto_reorden",
    "cant_stock_importado",
    "stock_pendiente_producto",
    "alternativa / alternativa_cantidad",
    "obs_stock",
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

PALABRAS_DISPONIBILIDAD = [
    "DIA",
    "DIAS",
    "SEMANA",
    "SEMANAS",
    "AGOTADO",
    "CONSULTAR",
    "CONSULTENOS",
    "LLEGA",
    "PRONTO",
    "DESCONTINUADO",
    "EQUIVALENTE",
    "BODEGA",
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


def normalizar_numero(valor):
    if valor is None or pd.isna(valor):
        return None

    texto = str(valor).strip()
    if not texto:
        return None

    texto = texto.replace("$", "").replace(" ", "")

    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    else:
        texto = texto.replace(",", ".")

    try:
        return float(texto)
    except ValueError:
        return None


def valor_es_numero_positivo(valor) -> bool:
    numero = normalizar_numero(valor)
    return numero is not None and numero > 0


def valor_parece_disponibilidad_textual(valor) -> bool:
    if not valor_es_material(valor):
        return False
    texto = str(valor).upper()
    return any(palabra in texto for palabra in PALABRAS_DISPONIBILIDAD)


def leer_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {path}")
    return pd.read_csv(path, sep=";", dtype=str, encoding="utf-8-sig").fillna("")


def auditar_campo(df: pd.DataFrame, campo: str) -> dict:
    total = len(df)

    if campo not in df.columns:
        return {
            "campo": campo,
            "existe": False,
            "filas_total": total,
            "filas_materiales": 0,
            "filas_numero_positivo": 0,
            "filas_texto_disponibilidad": 0,
            "porcentaje_materialidad": 0.0,
            "ejemplos": "",
        }

    serie = df[campo].astype(str).fillna("").str.strip()
    mask_material = serie.map(valor_es_material)
    mask_numero_positivo = serie.map(valor_es_numero_positivo)
    mask_texto_disponibilidad = serie.map(valor_parece_disponibilidad_textual)

    materiales = serie[mask_material]
    ejemplos = materiales.drop_duplicates().head(12).tolist()

    filas_materiales = int(mask_material.sum())
    porcentaje = round((filas_materiales / total) * 100, 2) if total else 0.0

    return {
        "campo": campo,
        "existe": True,
        "filas_total": total,
        "filas_materiales": filas_materiales,
        "filas_numero_positivo": int(mask_numero_positivo.sum()),
        "filas_texto_disponibilidad": int(mask_texto_disponibilidad.sum()),
        "porcentaje_materialidad": porcentaje,
        "ejemplos": " | ".join(ejemplos),
    }


def detectar_anomalias(df: pd.DataFrame, auditoria: list[dict]) -> list[dict]:
    anomalias = []

    por_campo = {row["campo"]: row for row in auditoria}

    cantidad = por_campo.get("cantidad", {})
    if cantidad.get("filas_texto_disponibilidad", 0) > 0:
        anomalias.append({
            "tipo": "CANTIDAD_CONTIENE_DISPONIBILIDAD_TEXTUAL",
            "severidad": "ALTA",
            "detalle": (
                "El campo cantidad contiene textos de disponibilidad o tiempo de entrega. "
                "No debe aprobarse como cantidad física sin limpieza semántica."
            ),
        })

    stock = por_campo.get("stock", {})
    if stock.get("filas_numero_positivo", 0) > 0:
        anomalias.append({
            "tipo": "STOCK_POSITIVO_DETECTADO",
            "severidad": "MEDIA",
            "detalle": (
                "El campo stock contiene números positivos. Puede ser inventario físico, "
                "pero debe separarse de cantidad/disponibilidad textual antes de aprobación."
            ),
        })

    if "_producto_key_origen" not in df.columns:
        anomalias.append({
            "tipo": "SIN_KEY_TECNICA",
            "severidad": "ALTA",
            "detalle": "No existe _producto_key_origen para relacionar inventario con producto_core.",
        })

    return anomalias


def generar_markdown(resumen: dict, auditoria: list[dict], anomalias: list[dict]) -> str:
    lineas = []
    lineas.append("# Auditoría semántica de PRODUCTO_INVENTARIO")
    lineas.append("")
    lineas.append(f"Fecha de generación: {resumen['fecha_generacion']}")
    lineas.append(f"Script: `auditar_producto_inventario_v1.py` v{VERSION}")
    lineas.append(f"Archivo auditado: `{resumen['archivo_inventario']}`")
    lineas.append("")
    lineas.append("## 1. Resumen")
    lineas.append("")
    lineas.append("| Control | Resultado |")
    lineas.append("|---|---:|")
    lineas.append(f"| Filas auditadas | {resumen['filas']} |")
    lineas.append(f"| Columnas auditadas | {resumen['columnas']} |")
    lineas.append(f"| Anomalías detectadas | {len(anomalias)} |")
    lineas.append("")
    lineas.append("## 2. Auditoría por campo")
    lineas.append("")
    lineas.append("| Campo | Existe | Materiales | Números positivos | Texto disponibilidad | % materialidad | Ejemplos |")
    lineas.append("|---|---:|---:|---:|---:|---:|---|")
    for row in auditoria:
        lineas.append(
            f"| {row['campo']} | {row['existe']} | {row['filas_materiales']} | "
            f"{row['filas_numero_positivo']} | {row['filas_texto_disponibilidad']} | "
            f"{row['porcentaje_materialidad']} | {row['ejemplos']} |"
        )
    lineas.append("")
    lineas.append("## 3. Anomalías")
    lineas.append("")
    if not anomalias:
        lineas.append("No se detectaron anomalías con los controles definidos.")
    else:
        lineas.append("| Tipo | Severidad | Detalle |")
        lineas.append("|---|---|---|")
        for item in anomalias:
            lineas.append(f"| {item['tipo']} | {item['severidad']} | {item['detalle']} |")
    lineas.append("")
    lineas.append("## 4. Interpretación")
    lineas.append("")
    lineas.append(
        "Esta auditoría separa señales de inventario físico de textos de disponibilidad o tiempo de entrega. "
        "Si `cantidad` contiene textos como días, agotado o consultar, no debe aprobarse como cantidad física. "
        "Si `stock` contiene números positivos, puede ser candidato a inventario, pero requiere decisión semántica "
        "antes de escalar el proceso."
    )
    lineas.append("")
    return "\n".join(lineas)


def main():
    parser = argparse.ArgumentParser(
        description="Audita semánticamente producto_inventario.csv."
    )
    parser.add_argument(
        "--inventario",
        required=True,
        help="Ruta del producto_inventario.csv normalizado.",
    )
    parser.add_argument(
        "--out-dir",
        default="05_reportes/auditoria_producto_inventario_v1",
        help="Carpeta de salida para reportes de auditoría.",
    )

    args = parser.parse_args()
    inventario_path = Path(args.inventario)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = leer_csv(inventario_path)
    auditoria = [auditar_campo(df, campo) for campo in CAMPOS_PRIORITARIOS]
    anomalias = detectar_anomalias(df, auditoria)

    resumen = {
        "script": "auditar_producto_inventario_v1.py",
        "version": VERSION,
        "fecha_generacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "archivo_inventario": str(inventario_path),
        "filas": int(len(df)),
        "columnas": int(len(df.columns)),
        "anomalias_detectadas": len(anomalias),
    }

    payload = {
        "resumen": resumen,
        "auditoria": auditoria,
        "anomalias": anomalias,
    }

    (out_dir / "resumen_producto_inventario.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    pd.DataFrame(auditoria).to_csv(
        out_dir / "auditoria_campos_producto_inventario.csv",
        index=False,
        sep=";",
        encoding="utf-8-sig",
    )

    pd.DataFrame(anomalias).to_csv(
        out_dir / "anomalias_producto_inventario.csv",
        index=False,
        sep=";",
        encoding="utf-8-sig",
    )

    markdown = generar_markdown(resumen, auditoria, anomalias)
    (out_dir / "informe_auditoria_producto_inventario.md").write_text(
        markdown,
        encoding="utf-8",
    )

    print("Auditoría de PRODUCTO_INVENTARIO generada correctamente.")
    print(f"Filas auditadas: {len(df)}")
    print(f"Anomalías detectadas: {len(anomalias)}")
    print(f"Salida: {out_dir}")


if __name__ == "__main__":
    main()
