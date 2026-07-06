from pathlib import Path
import argparse
import json
from datetime import datetime

import pandas as pd


VERSION = "1.2.0"


def leer_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"No existe el reporte JSON: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def leer_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"No existe el CSV: {path}")
    return pd.read_csv(path, sep=";", dtype=str, encoding="utf-8-sig").fillna("")


def obtener_filas_tabla(detalle: pd.DataFrame, tabla_destino: str) -> dict:
    if detalle.empty or "tabla_destino" not in detalle.columns:
        return {}

    filas = detalle[detalle["tabla_destino"].astype(str).str.upper() == tabla_destino.upper()]
    if filas.empty:
        return {}

    return filas.iloc[0].to_dict()


def valor_entero(registro: dict, campo: str, default: int = 0) -> int:
    try:
        valor = str(registro.get(campo, "")).strip()
        if not valor:
            return default
        return int(float(valor))
    except Exception:
        return default


def texto(registro: dict, campo: str, default: str = "") -> str:
    valor = str(registro.get(campo, "")).strip()
    return valor or default


def observacion_producto_core(core: dict) -> str:
    filas = valor_entero(core, "filas_generadas")
    if filas > 0:
        return (
            "Tabla base generada. En la muestra con nombre, los controles posteriores validaron "
            "código, llave técnica, nombre_producto, item_erp e idn1 con cobertura completa."
        )
    return "Tabla base sin filas generadas; requiere revisión de fuente y mapeo."


def observacion_inventario(inventario: dict) -> str:
    filas = valor_entero(inventario, "filas_generadas")
    if filas > 0:
        return (
            "Se generaron registros de inventario. En la versión 1.5.0 se limpió cantidad para evitar "
            "textos de disponibilidad; stock queda como candidato numérico de inventario físico pendiente "
            "de validación semántica antes de escalar."
        )
    return (
        "Se conserva sin filas por revisión semántica pendiente. Los datos observados en la muestra "
        "parecen tiempo de entrega o disponibilidad, no inventario físico."
    )


def texto_inventario(version_script: str, inventario: dict) -> str:
    filas = valor_entero(inventario, "filas_generadas")
    if filas > 0:
        return (
            "Se detectó que el campo `cantidad` podía mezclar textos de disponibilidad o tiempo de entrega "
            "con señales numéricas. En la versión 1.5.0 se agregó una limpieza conservadora para que `cantidad` "
            "solo conserve valores numéricos positivos. Los textos como días, agotado, consultar o descontinuado "
            "ya no deben aprobarse como cantidad física. El campo `stock` conserva valores numéricos y queda como "
            "candidato de inventario físico, pendiente de validación semántica antes de una carga masiva."
        )
    return (
        "No se forzó la generación de inventario. Algunos valores observados en campos relacionados con existencia "
        "parecen corresponder a tiempos de entrega, por ejemplo días o semanas, y no a cantidad física. "
        "Por eso la tabla se conserva en el contrato de salida, pero sin registros en este piloto."
    )


def decision_inventario(inventario: dict) -> str:
    filas = valor_entero(inventario, "filas_generadas")
    if filas > 0:
        return (
            "- Mantener `PRODUCTO_INVENTARIO` como tabla generada. `cantidad` queda limpia de disponibilidad textual; "
            "`stock` queda como candidato numérico de inventario físico pendiente de validación semántica."
        )
    return "- Mantener `PRODUCTO_INVENTARIO` como tabla generada, pero sin filas hasta resolver su significado semántico."


def generar_markdown(reporte: dict, detalle: pd.DataFrame, piloto_nombre: str) -> str:
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

    core = obtener_filas_tabla(detalle, "PRODUCTO_CORE")
    precio = obtener_filas_tabla(detalle, "PRODUCTO_PRECIO")
    proveedor = obtener_filas_tabla(detalle, "PRODUCTO_PROVEEDOR")
    inventario = obtener_filas_tabla(detalle, "PRODUCTO_INVENTARIO")
    parametro = obtener_filas_tabla(detalle, "PRODUCTO_PARAMETRO")

    filas_origen = reporte.get("filas_origen", "")
    columnas_origen = reporte.get("columnas_origen", "")
    columnas_mapeo = reporte.get("columnas_mapeo", "")
    faltan_en_origen = reporte.get("faltan_en_origen", "")
    sobran_en_origen = reporte.get("sobran_en_origen", "")
    tablas_generadas = reporte.get("tablas_generadas", "")
    errores = reporte.get("errores", [])
    version_script = reporte.get("version", "")

    total_errores = len(errores) if isinstance(errores, list) else 0

    lineas = []
    lineas.append(f"# Informe técnico — Piloto de normalización de productos `{piloto_nombre}`")
    lineas.append("")
    lineas.append(f"Fecha de generación: {fecha}")
    lineas.append("")
    lineas.append("## 1. Objetivo")
    lineas.append("")
    lineas.append(
        "Validar el proceso de separación y normalización de la tabla `dbo.productos_hugo` "
        "a partir del mapeo `Normalizacion_Tabla_Productos.xlsx`, usando una muestra controlada "
        "antes de escalar a una población mayor."
    )
    lineas.append("")
    lineas.append("## 2. Alcance del piloto")
    lineas.append("")
    lineas.append(
        "Este piloto genera archivos CSV derivados por tabla destino. No crea tablas reales en SQL Server, "
        "no carga datos a Azure y no modifica la fuente original."
    )
    lineas.append("")
    lineas.append("| Control | Resultado |")
    lineas.append("|---|---:|")
    lineas.append(f"| Filas origen | {filas_origen} |")
    lineas.append(f"| Columnas origen | {columnas_origen} |")
    lineas.append(f"| Columnas en mapeo | {columnas_mapeo} |")
    lineas.append(f"| Faltantes en origen | {faltan_en_origen} |")
    lineas.append(f"| Sobrantes en origen | {sobran_en_origen} |")
    lineas.append(f"| Tablas generadas | {tablas_generadas} |")
    lineas.append(f"| Errores de ejecución | {total_errores} |")
    lineas.append(f"| Versión del script | {version_script} |")
    lineas.append("")
    lineas.append("## 3. Resultados principales")
    lineas.append("")
    lineas.append("| Tabla | Modo de generación | Filas generadas | Observación |")
    lineas.append("|---|---|---:|---|")
    lineas.append(
        f"| PRODUCTO_CORE | {texto(core, 'modo_generacion', 'HORIZONTAL')} | "
        f"{valor_entero(core, 'filas_generadas')} | {observacion_producto_core(core)} |"
    )
    lineas.append(
        f"| PRODUCTO_PRECIO | {texto(precio, 'modo_generacion', 'VERTICAL_POR_FUENTE_PRECIO')} | "
        f"{valor_entero(precio, 'filas_generadas')} | Se verticalizó para conservar múltiples fuentes de precio por producto. |"
    )
    lineas.append(
        f"| PRODUCTO_PROVEEDOR | {texto(proveedor, 'modo_generacion', 'HORIZONTAL')} | "
        f"{valor_entero(proveedor, 'filas_generadas')} | Se corrigió la pérdida de proveedor por sobrescritura de campos. |"
    )
    lineas.append(
        f"| PRODUCTO_INVENTARIO | {texto(inventario, 'modo_generacion', 'HORIZONTAL')} | "
        f"{valor_entero(inventario, 'filas_generadas')} | {observacion_inventario(inventario)} |"
    )
    lineas.append(
        f"| PRODUCTO_PARAMETRO | {texto(parametro, 'modo_generacion', 'VERTICAL_POR_PARAMETRO_ORIGEN')} | "
        f"{valor_entero(parametro, 'filas_generadas')} | Se corrigio estructuralmente para conservar una fila por producto y por valor de parametro encontrado. No se inventa parametro_id; queda pendiente de homologacion oficial. |"
    )
    lineas.append("")
    lineas.append("## 4. Problemas detectados y correcciones aplicadas")
    lineas.append("")
    lineas.append("### 4.1 Materialidad")
    lineas.append("")
    lineas.append(
        "La primera salida técnica generaba filas cuando encontraba cualquier valor no vacío. "
        "Eso permitía que ceros, `NO`, `NULL`, `false` o banderas por defecto crearan registros sin valor real. "
        "Se agregó una regla de materialidad para exigir datos útiles antes de generar filas."
    )
    lineas.append("")
    lineas.append("### 4.2 Precios")
    lineas.append("")
    lineas.append(
        "Se detectó que varias columnas origen de precio apuntaban al mismo campo destino `valor`, "
        "lo que podía sobrescribir información. La tabla `PRODUCTO_PRECIO` quedó en formato vertical: "
        "una fila por producto y por fuente de precio."
    )
    lineas.append("")
    lineas.append("### 4.3 Proveedor")
    lineas.append("")
    lineas.append(
        "Se protegieron los campos destino para que una columna posterior vacía o no material no sobrescriba "
        "un dato real cargado previamente. Con esto `PRODUCTO_PROVEEDOR` conserva los proveedores reales del piloto."
    )
    lineas.append("")
    lineas.append("### 4.4 Inventario")
    lineas.append("")
    lineas.append(texto_inventario(version_script, inventario))
    lineas.append("")
    lineas.append("### 4.5 Parametros")
    lineas.append("")
    lineas.append(
        "Se detecto que `PRODUCTO_PARAMETRO` estaba quedando como una fila por producto, aunque el mapeo indica "
        "que campos como `CAR_IND_*`, `CAR_COM_*` y `DIMENSION` deben comportarse como valores de parametro. "
        "En la version 1.6.0 se corrigio la estructura a formato vertical por `parametro_origen`: una fila por "
        "producto y por valor material encontrado. Como las columnas `ID_PARAMETRO_*` no traen datos en la muestra, "
        "no se inventa `parametro_id`; el campo queda vacio y marcado como `PENDIENTE_PARAMETRO_ID`."
    )
    lineas.append("")

    lineas.append("### 4.6 Identificadores")
    lineas.append("")
    lineas.append(
        "Se separó el código real de ViaIndustrial de una llave técnica de trazabilidad. `codigo` y `_codigo_origen` "
        "se mantienen únicamente para el código real cuando existe. Para relacionar tablas derivadas se agregó "
        "`_producto_key_origen`, que usa una prioridad técnica: CODIGO, ITEM, REFERENCIA y finalmente ROW_n. "
        "Esto evita confundir ITEM o REFERENCIA con el código público del producto."
    )
    lineas.append("")
    lineas.append("## 5. Decisiones técnicas vigentes")
    lineas.append("")
    lineas.append("- No modificar `dbo.productos_hugo`.")
    lineas.append("- No crear tablas reales todavía.")
    lineas.append("- No cargar datos a Azure.")
    lineas.append("- No escalar a toda la tabla hasta completar auditoría de contenido.")
    lineas.append(decision_inventario(inventario))
    lineas.append("- Mantener `PRODUCTO_PRECIO` verticalizado por fuente.")
    lineas.append("- Mantener `PRODUCTO_PARAMETRO` verticalizado por `parametro_origen`, sin inventar `parametro_id`.")
    lineas.append("- Mantener separados `codigo`, `item_erp`, `referencia` y `_producto_key_origen`.")
    lineas.append("")
    lineas.append("## 6. Pendientes antes de escalar")
    lineas.append("")
    lineas.append("1. Consolidar comparación entre los pilotos `top1000_v7` y `productos_hugo_con_nombre_top1000_v2`.")
    lineas.append("2. Revisar semánticamente los campos de inventario y disponibilidad antes de aprobar carga masiva.")
    lineas.append("3. Auditar otras tablas repetibles que podrían requerir verticalización, como parámetros, documentos, media, equivalentes o certificados.")
    lineas.append("4. Ejecutar una muestra más representativa que no dependa solo de `TOP 1000`.")
    lineas.append("5. Generar una recomendación de escalamiento con controles y criterios de aceptación.")
    lineas.append("")
    lineas.append("## 7. Conclusión")
    lineas.append("")
    lineas.append(
        "El piloto ya no solo separa columnas según el mapeo. Ahora incorpora reglas de calidad, "
        "trazabilidad y preservación de datos materiales. La salida es más sólida técnicamente y permite "
        "continuar con una auditoría controlada antes de escalar. Todavía debe considerarse piloto auditado, "
        "no versión final de carga masiva."
    )
    lineas.append("")
    return "\n".join(lineas)


def main():
    parser = argparse.ArgumentParser(
        description="Genera informe técnico del piloto de normalización de productos."
    )
    parser.add_argument(
        "--reporte-json",
        default="05_reportes/reporte_normalizacion_tabla_productos_v1.json",
        help="Reporte JSON generado por normalizar_tabla_productos_v1.py",
    )
    parser.add_argument(
        "--detalle-tablas",
        default="05_reportes/detalle_tablas_generadas_v1.csv",
        help="CSV con detalle de tablas generadas",
    )
    parser.add_argument(
        "--piloto",
        default="productos_hugo_con_nombre_top1000_v3",
        help="Nombre del piloto reportado",
    )
    parser.add_argument(
        "--out",
        default="05_reportes/informe_auditoria_piloto_normalizacion_productos_v3.md",
        help="Ruta del informe Markdown de salida",
    )

    args = parser.parse_args()

    reporte = leer_json(Path(args.reporte_json))
    detalle = leer_csv(Path(args.detalle_tablas))

    markdown = generar_markdown(
        reporte=reporte,
        detalle=detalle,
        piloto_nombre=args.piloto,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")

    print("Informe generado correctamente.")
    print(f"Salida: {out_path}")


if __name__ == "__main__":
    main()
