from pathlib import Path
import argparse
import json
from datetime import datetime

import pandas as pd


VERSION = "2.0.0"


TABLAS_CLAVE = [
    "PRODUCTO_CORE",
    "PRODUCTO_AUDITORIA",
    "PRODUCTO_INVENTARIO",
    "PRODUCTO_EQUIVALENTE",
    "PRODUCTO_PRECIO",
    "PRODUCTO_PROVEEDOR",
    "PRODUCTO_PARAMETRO",
]


def leer_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"No existe el reporte JSON: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def leer_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"No existe el CSV: {path}")
    return pd.read_csv(path, sep=";", dtype=str, encoding="utf-8-sig").fillna("")


def entero(valor, default: int = 0) -> int:
    try:
        texto = str(valor).strip()
        if not texto:
            return default
        return int(float(texto))
    except Exception:
        return default


def buscar_tabla(detalle: pd.DataFrame, tabla: str) -> dict:
    if detalle.empty or "tabla_destino" not in detalle.columns:
        return {}
    filas = detalle[detalle["tabla_destino"].astype(str).str.upper() == tabla.upper()]
    if filas.empty:
        return {}
    return filas.iloc[0].to_dict()


def texto(registro: dict, campo: str, default: str = "") -> str:
    valor = str(registro.get(campo, "")).strip()
    return valor or default


def resumen_tabla(detalle: pd.DataFrame, tabla: str) -> tuple[str, int, str]:
    row = buscar_tabla(detalle, tabla)
    modo = texto(row, "modo_generacion", "")
    filas = entero(row.get("filas_generadas", 0))
    return tabla, filas, modo


def generar_markdown(reporte: dict, detalle: pd.DataFrame, nombre: str) -> str:
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    version_script = reporte.get("version", "")
    errores = reporte.get("errores", [])
    total_errores = len(errores) if isinstance(errores, list) else 0
    post = reporte.get("postproceso_v116", {}) or {}
    post_inv = post.get("producto_inventario", {}) or {}
    post_eq = post.get("producto_equivalente", {}) or {}

    lineas = []
    lineas.append(f"# Informe tecnico - Piloto de normalizacion `{nombre}`")
    lineas.append("")
    lineas.append(f"Fecha de generacion: {fecha}")
    lineas.append(f"Generador de informe: v{VERSION}")
    lineas.append("")

    lineas.append("## 1. Objetivo")
    lineas.append("")
    lineas.append(
        "Documentar el avance del piloto de normalizacion de `dbo.productos_hugo` "
        "hacia 29 salidas derivadas, usando el mapeo `Normalizacion_Tabla_Productos.xlsx` "
        "y una muestra controlada de 1000 productos."
    )
    lineas.append("")

    lineas.append("## 2. Alcance")
    lineas.append("")
    lineas.append(
        "Este piloto genera archivos CSV derivados. No modifica `dbo.productos_hugo`, "
        "no crea tablas reales en SQL Server y no carga datos a Azure."
    )
    lineas.append("")
    lineas.append("| Control | Resultado |")
    lineas.append("|---|---:|")
    lineas.append(f"| Filas origen | {reporte.get('filas_origen', '')} |")
    lineas.append(f"| Columnas origen | {reporte.get('columnas_origen', '')} |")
    lineas.append(f"| Columnas en mapeo | {reporte.get('columnas_mapeo', '')} |")
    lineas.append(f"| Faltantes en origen | {reporte.get('faltan_en_origen', '')} |")
    lineas.append(f"| Sobrantes en origen | {reporte.get('sobran_en_origen', '')} |")
    lineas.append(f"| Tablas generadas | {reporte.get('tablas_generadas', '')} |")
    lineas.append(f"| Errores de ejecucion | {total_errores} |")
    lineas.append(f"| Version normalizador | {version_script} |")
    lineas.append("")

    lineas.append("## 3. Tablas clave")
    lineas.append("")
    lineas.append("| Tabla | Filas | Modo de generacion |")
    lineas.append("|---|---:|---|")
    for tabla in TABLAS_CLAVE:
        nombre_tabla, filas, modo = resumen_tabla(detalle, tabla)
        lineas.append(f"| {nombre_tabla} | {filas} | {modo} |")
    lineas.append("")

    lineas.append("## 4. Correcciones cerradas")
    lineas.append("")
    lineas.append("### 4.1 PRODUCTO_AUDITORIA - v1.15.0")
    lineas.append("")
    lineas.append(
        "Se corrigio la perdida estructural de auditoria. La tabla dejo de quedar como una fila por producto "
        "y paso a conservar eventos reales de auditoria. La validacion previa confirmo 6666 eventos esperados, "
        "6666 filas generadas, 0 faltantes, 0 extras y 0 errores."
    )
    lineas.append("")

    lineas.append("### 4.2 PRODUCTO_INVENTARIO / PRODUCTO_EQUIVALENTE - v1.16.0")
    lineas.append("")
    lineas.append(
        "Don Andres confirmo que el campo de alternativa en inventario se interpreta como producto alternativo, "
        "no como producto alternativo mas cantidad alternativa. Con ese criterio se retiro de PRODUCTO_INVENTARIO "
        "el campo ambiguo `alternativa / alternativa_cantidad` y se movieron los codigos de `STOCK_ALTERNATIVA_PRODUCTO` "
        "a PRODUCTO_EQUIVALENTE como `PRODUCTO_ALTERNATIVO`."
    )
    lineas.append("")
    lineas.append("| Control v1.16.0 | Resultado |")
    lineas.append("|---|---:|")
    lineas.append(f"| Campo ambiguo removido de inventario | {post_inv.get('campo_removido', '')} |")
    lineas.append(f"| Columnas inventario antes | {post_inv.get('columnas_antes', '')} |")
    lineas.append(f"| Columnas inventario despues | {post_inv.get('columnas_despues', '')} |")
    lineas.append(f"| Registros equivalentes iniciales | {post_eq.get('registros_equivalente_inicial', '')} |")
    lineas.append(f"| Alternativos detectados desde inventario | {post_eq.get('registros_alternativos_detectados', '')} |")
    lineas.append(f"| Registros agregados a equivalente | {post_eq.get('registros_agregados', '')} |")
    lineas.append(f"| Registros equivalentes finales | {post_eq.get('registros_equivalente_final', '')} |")
    lineas.append("")

    estados = post_eq.get("estados", {}) or {}
    if estados:
        lineas.append("Estados de los alternativos migrados:")
        lineas.append("")
        lineas.append("| Estado | Registros |")
        lineas.append("|---|---:|")
        for estado, cantidad in estados.items():
            lineas.append(f"| {estado} | {cantidad} |")
        lineas.append("")

    lineas.append("## 5. Comparacion controlada v12 vs v13")
    lineas.append("")
    lineas.append(
        "La comparacion manual confirmo que solo cambiaron las tablas esperadas: "
        "PRODUCTO_INVENTARIO perdio 1 columna, y PRODUCTO_EQUIVALENTE gano 74 filas. "
        "Las demas tablas conservaron el mismo numero de filas y columnas."
    )
    lineas.append("")

    lineas.append("## 6. Decisiones vigentes")
    lineas.append("")
    lineas.append("- No modificar fuentes originales.")
    lineas.append("- No modificar `dbo.productos_hugo`.")
    lineas.append("- No cargar datos a SQL Server ni Azure en esta fase.")
    lineas.append("- Mantener PRODUCTO_AUDITORIA vertical por evento.")
    lineas.append("- Mantener PRODUCTO_INVENTARIO solo para informacion real de inventario.")
    lineas.append("- Mantener productos alternativos dentro de PRODUCTO_EQUIVALENTE.")
    lineas.append("- No convertir `STOCK_ALTERNATIVA_CANTIDAD_PRODUCTO` automaticamente en cantidad ni en producto.")
    lineas.append("- Los alternativos no validados contra el piloto quedan pendientes de validacion contra BD completa.")
    lineas.append("")

    lineas.append("## 7. Pendientes")
    lineas.append("")
    lineas.append("1. Validar contra BD completa los 65 productos alternativos pendientes.")
    lineas.append("2. Seguir auditando tablas con materialidad alta, especialmente proveedor, precio e inventario.")
    lineas.append("3. Ejecutar una muestra mas representativa antes de escalar a toda la tabla.")
    lineas.append("4. Definir criterios de aceptacion para una carga real futura.")
    lineas.append("")

    lineas.append("## 8. Conclusion")
    lineas.append("")
    lineas.append(
        "El piloto v13 con normalizador v1.16.0 queda como avance tecnico validado. "
        "Se corrigieron problemas reales de estructura sin modificar fuentes originales y sin contaminar el modelo. "
        "Todavia debe considerarse piloto auditado, no version final de carga masiva."
    )
    lineas.append("")

    return "\n".join(lineas)


def main():
    parser = argparse.ArgumentParser(description="Genera informe actualizado del piloto de normalizacion v13.")
    parser.add_argument("--detalle", required=True, help="CSV detalle_tablas_generadas_v1.csv")
    parser.add_argument("--reporte", required=True, help="JSON reporte_normalizacion_tabla_productos_v1.json")
    parser.add_argument("--nombre", default="piloto_v13_v1_16", help="Nombre del piloto para el titulo")
    parser.add_argument("--out", required=True, help="Ruta de salida .md")
    args = parser.parse_args()

    detalle = leer_csv(Path(args.detalle))
    reporte = leer_json(Path(args.reporte))
    markdown = generar_markdown(reporte, detalle, args.nombre)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(markdown, encoding="utf-8")

    print("Informe actualizado generado correctamente.")
    print(f"Salida: {out}")


if __name__ == "__main__":
    main()
