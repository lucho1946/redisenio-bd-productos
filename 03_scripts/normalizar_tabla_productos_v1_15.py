from pathlib import Path
import argparse
import json
import sys
from datetime import datetime, timezone

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import normalizar_tabla_productos_v1 as base


VERSION = "1.15.0"


EVENTOS_AUDITORIA = [
    {
        "auditoria_origen": "COSTO",
        "campo_auditado": "COSTO",
        "fecha": "FECHA_COSTO",
        "usuario": "MODIFICO_COSTO",
        "terminal": "",
        "observacion": "",
    },
    {
        "auditoria_origen": "UTILIDAD",
        "campo_auditado": "UTILIDAD",
        "fecha": "UTILIDAD_FECHA",
        "usuario": "UTILIDAD_MODIFICO",
        "terminal": "",
        "observacion": "",
    },
    {
        "auditoria_origen": "PV",
        "campo_auditado": "PV",
        "fecha": "PV_FECHA",
        "usuario": "PV_MODIFICO",
        "terminal": "",
        "observacion": "",
    },
    {
        "auditoria_origen": "CCD",
        "campo_auditado": "CCD",
        "fecha": "CCD_FECHA",
        "usuario": "CCD_MODIFICO",
        "terminal": "",
        "observacion": "",
    },
    {
        "auditoria_origen": "D",
        "campo_auditado": "D",
        "fecha": "D_FECHA",
        "usuario": "D_MODIFICO",
        "terminal": "",
        "observacion": "",
    },
    {
        "auditoria_origen": "CD",
        "campo_auditado": "CD",
        "fecha": "CD_FECHA",
        "usuario": "CD_MODIFICO",
        "terminal": "",
        "observacion": "",
    },
    {
        "auditoria_origen": "FPD",
        "campo_auditado": "FPD",
        "fecha": "FPD_FECHA",
        "usuario": "FPD_MODIFICO",
        "terminal": "",
        "observacion": "",
    },
    {
        "auditoria_origen": "FCD",
        "campo_auditado": "FCD",
        "fecha": "FCD_FECHA",
        "usuario": "FCD_MODIFICO",
        "terminal": "",
        "observacion": "",
    },
    {
        "auditoria_origen": "UR",
        "campo_auditado": "UR",
        "fecha": "UR_FECHA",
        "usuario": "UR_MODIFICO",
        "terminal": "",
        "observacion": "",
    },
    {
        "auditoria_origen": "UM",
        "campo_auditado": "UM",
        "fecha": "FECHA_UM",
        "usuario": "USUARIO_UM",
        "terminal": "",
        "observacion": "UM_OBSERVACION",
    },
    {
        "auditoria_origen": "ELABORO",
        "campo_auditado": "ELABORO",
        "fecha": "",
        "usuario": "USUARIO_ELABORO",
        "terminal": "",
        "observacion": "",
    },
    {
        "auditoria_origen": "LINK_PROV",
        "campo_auditado": "LINK_PROV",
        "fecha": "LINK_PROV_FECHA",
        "usuario": "",
        "terminal": "LINK_PROV_TERMINAL",
        "observacion": "",
    },
    {
        "auditoria_origen": "COMPRA_OBSERVACION",
        "campo_auditado": "COMPRA_OBSERVACION",
        "fecha": "COMPRA_OBSERVACION_FECHA",
        "usuario": "",
        "terminal": "COMPRA_OBSERVACION_TERMINAL",
        "observacion": "",
    },
    {
        "auditoria_origen": "PESO",
        "campo_auditado": "PESO",
        "fecha": "PESO_FECHA",
        "usuario": "",
        "terminal": "PESO_TERMINAL",
        "observacion": "",
    },
    {
        "auditoria_origen": "DIMENSIONES",
        "campo_auditado": "DIMENSIONES",
        "fecha": "DIMENSIONES_FECHA",
        "usuario": "",
        "terminal": "DIMENSIONES_TERMINAL",
        "observacion": "",
    },
    {
        "auditoria_origen": "ORIGEN",
        "campo_auditado": "ORIGEN",
        "fecha": "ORIGEN_FECHA",
        "usuario": "",
        "terminal": "ORIGEN_TERMINAL",
        "observacion": "",
    },
    {
        "auditoria_origen": "TRANSPORTE",
        "campo_auditado": "TRANSPORTE",
        "fecha": "TRANSPORTE_FECHA",
        "usuario": "",
        "terminal": "TRANSPORTE_TERMINAL",
        "observacion": "",
    },
    {
        "auditoria_origen": "IMAGEN",
        "campo_auditado": "IMAGEN",
        "fecha": "IMAGEN_FECHA",
        "usuario": "",
        "terminal": "IMAGEN_TERMINAL",
        "observacion": "",
    },
]


def estado_producto_auditoria(fecha, usuario, terminal, observacion) -> str:
    """
    Estado trazable del evento de auditoria sin inventar fecha, usuario ni terminal.
    """
    tiene_fecha = base.valor_es_material(fecha)
    tiene_usuario = base.valor_es_material(usuario)
    tiene_terminal = base.valor_es_material(terminal)
    tiene_observacion = base.valor_es_material(observacion)

    if tiene_fecha and (tiene_usuario or tiene_terminal or tiene_observacion):
        return "EVENTO_AUDITORIA_CON_CONTEXTO"

    if tiene_fecha:
        return "EVENTO_AUDITORIA_SOLO_FECHA"

    if tiene_usuario:
        return "EVENTO_AUDITORIA_SOLO_USUARIO"

    if tiene_terminal:
        return "EVENTO_AUDITORIA_SOLO_TERMINAL"

    if tiene_observacion:
        return "EVENTO_AUDITORIA_SOLO_OBSERVACION"

    return "SIN_EVENTO"


def generar_producto_auditoria_vertical(
    df_origen: pd.DataFrame,
    grupo: pd.DataFrame,
    columnas_origen_norm: dict[str, str],
    producto_key_origen: pd.Series,
    codigo_origen_real: pd.Series,
    tabla_destino: str,
    errores: list[dict],
) -> tuple[pd.DataFrame, dict]:
    """
    Genera PRODUCTO_AUDITORIA en formato vertical por evento de auditoria.

    Decision conservadora v1.15.0:
    - Se agrupan campos que pertenecen al mismo evento: fecha, usuario, terminal y observacion.
    - No se inventa fecha, usuario, terminal ni observacion.
    - No se mezcla un componente de un dominio con otro.
    - No se crea fila vacia.
    - No se usan reglas por producto, codigo, fila o valor especifico.
    """
    registros = []
    columnas_procesadas = 0
    columnas_no_encontradas = 0
    campos_destino_vacios = 0

    columnas_mapeadas = {
        base.normalizar_nombre_columna(str(r["COLUMNA_ORIGEN"]).strip()): str(r["COLUMNA_ORIGEN"]).strip()
        for _, r in grupo.iterrows()
    }

    for col_norm, col_origen in columnas_mapeadas.items():
        if not col_origen:
            campos_destino_vacios += 1
            continue

        if col_norm in columnas_origen_norm:
            columnas_procesadas += 1
        else:
            columnas_no_encontradas += 1
            errores.append({
                "tabla_destino": tabla_destino,
                "columna_origen": col_origen,
                "campo_destino": "",
                "error": "COLUMNA_ORIGEN_NO_EXISTE",
                "detalle": "La columna del mapeo no existe en el archivo origen.",
            })

    for idx in df_origen.index:
        for definicion in EVENTOS_AUDITORIA:
            fecha = str(base.valor_origen_seguro(
                df_origen,
                columnas_origen_norm,
                definicion["fecha"],
                idx,
            ) or "").strip()

            usuario = str(base.valor_origen_seguro(
                df_origen,
                columnas_origen_norm,
                definicion["usuario"],
                idx,
            ) or "").strip()

            terminal = str(base.valor_origen_seguro(
                df_origen,
                columnas_origen_norm,
                definicion["terminal"],
                idx,
            ) or "").strip()

            observacion = str(base.valor_origen_seguro(
                df_origen,
                columnas_origen_norm,
                definicion["observacion"],
                idx,
            ) or "").strip()

            if not any([
                base.valor_es_material(fecha),
                base.valor_es_material(usuario),
                base.valor_es_material(terminal),
                base.valor_es_material(observacion),
            ]):
                continue

            registros.append({
                "_origen_row": int(idx) + 1,
                "_producto_key_origen": producto_key_origen.loc[idx],
                "_codigo_origen": codigo_origen_real.loc[idx],
                "auditoria_origen": definicion["auditoria_origen"],
                "campo_auditado": definicion["campo_auditado"],
                "fecha_auditoria": fecha if base.valor_es_material(fecha) else "",
                "usuario_auditoria": usuario if base.valor_es_material(usuario) else "",
                "terminal_auditoria": terminal if base.valor_es_material(terminal) else "",
                "observacion_auditoria": observacion if base.valor_es_material(observacion) else "",
                "estado_producto_auditoria": estado_producto_auditoria(
                    fecha=fecha,
                    usuario=usuario,
                    terminal=terminal,
                    observacion=observacion,
                ),
            })

    columnas = [
        "_origen_row",
        "_producto_key_origen",
        "_codigo_origen",
        "auditoria_origen",
        "campo_auditado",
        "fecha_auditoria",
        "usuario_auditoria",
        "terminal_auditoria",
        "observacion_auditoria",
        "estado_producto_auditoria",
    ]

    registros_tabla = pd.DataFrame(registros, columns=columnas)

    estadisticas = {
        "columnas_procesadas": columnas_procesadas,
        "columnas_no_encontradas": columnas_no_encontradas,
        "campos_destino_vacios": campos_destino_vacios,
        "modo_generacion": "VERTICAL_POR_EVENTO_AUDITORIA_ORIGEN",
    }

    return registros_tabla, estadisticas


def generar_tablas_normalizadas(
    df_origen: pd.DataFrame,
    df_mapeo: pd.DataFrame,
    salida_dir: Path,
) -> dict:
    """
    Genera un CSV por cada TABLA_DESTINO del mapeo.
    v1.15.0 mantiene la logica vigente de v1.14.0 y agrega PRODUCTO_AUDITORIA vertical.
    """
    salida_dir.mkdir(parents=True, exist_ok=True)

    columnas_origen_norm = {
        base.normalizar_nombre_columna(c): c for c in df_origen.columns
    }

    columna_codigo = base.detectar_columna_codigo(df_origen)
    codigo_origen_real = base.construir_codigo_origen_real(
        df_origen=df_origen,
        columna_codigo=columna_codigo,
    )
    producto_key_origen = base.construir_producto_key_origen(df_origen)

    reportes_tablas = []
    errores = []
    tablas_generadas = []

    tablas_a_ignorar = {"ELIMINAR", "REVISAR/ELIMINAR", ""}

    for tabla_destino, grupo in df_mapeo.groupby("TABLA_DESTINO", dropna=False):
        tabla_destino = str(tabla_destino or "").strip()
        tabla_norm = base.limpiar_nombre_archivo(tabla_destino)

        if tabla_destino.upper() in tablas_a_ignorar:
            continue

        if tabla_norm == "producto_precio":
            registros_tabla, estadisticas = base.generar_producto_precio_vertical(
                df_origen=df_origen,
                grupo=grupo,
                columnas_origen_norm=columnas_origen_norm,
                producto_key_origen=producto_key_origen,
                codigo_origen_real=codigo_origen_real,
                tabla_destino=tabla_destino,
                errores=errores,
            )

        elif tabla_norm == "producto_parametro":
            registros_tabla, estadisticas = base.generar_producto_parametro_vertical(
                df_origen=df_origen,
                grupo=grupo,
                columnas_origen_norm=columnas_origen_norm,
                producto_key_origen=producto_key_origen,
                codigo_origen_real=codigo_origen_real,
                tabla_destino=tabla_destino,
                errores=errores,
            )

        elif tabla_norm == "producto_documento":
            registros_tabla, estadisticas = base.generar_producto_documento_vertical(
                df_origen=df_origen,
                grupo=grupo,
                columnas_origen_norm=columnas_origen_norm,
                producto_key_origen=producto_key_origen,
                codigo_origen_real=codigo_origen_real,
                tabla_destino=tabla_destino,
                errores=errores,
            )

        elif tabla_norm == "producto_certificado":
            registros_tabla, estadisticas = base.generar_producto_certificado_vertical(
                df_origen=df_origen,
                grupo=grupo,
                columnas_origen_norm=columnas_origen_norm,
                producto_key_origen=producto_key_origen,
                codigo_origen_real=codigo_origen_real,
                tabla_destino=tabla_destino,
                errores=errores,
            )

        elif tabla_norm == "producto_categoria":
            registros_tabla, estadisticas = base.generar_producto_categoria_vertical(
                df_origen=df_origen,
                grupo=grupo,
                columnas_origen_norm=columnas_origen_norm,
                producto_key_origen=producto_key_origen,
                codigo_origen_real=codigo_origen_real,
                tabla_destino=tabla_destino,
                errores=errores,
            )

        elif tabla_norm == "producto_proveedor":
            registros_tabla, estadisticas = base.generar_producto_proveedor_vertical(
                df_origen=df_origen,
                grupo=grupo,
                columnas_origen_norm=columnas_origen_norm,
                producto_key_origen=producto_key_origen,
                codigo_origen_real=codigo_origen_real,
                tabla_destino=tabla_destino,
                errores=errores,
            )

        elif tabla_norm == "producto_campana":
            registros_tabla, estadisticas = base.generar_producto_campana_vertical(
                df_origen=df_origen,
                grupo=grupo,
                columnas_origen_norm=columnas_origen_norm,
                producto_key_origen=producto_key_origen,
                codigo_origen_real=codigo_origen_real,
                tabla_destino=tabla_destino,
                errores=errores,
            )

        elif tabla_norm == "producto_media":
            registros_tabla, estadisticas = base.generar_producto_media_vertical(
                df_origen=df_origen,
                grupo=grupo,
                columnas_origen_norm=columnas_origen_norm,
                producto_key_origen=producto_key_origen,
                codigo_origen_real=codigo_origen_real,
                tabla_destino=tabla_destino,
                errores=errores,
            )

        elif tabla_norm == "producto_keyword":
            registros_tabla, estadisticas = base.generar_producto_keyword_vertical(
                df_origen=df_origen,
                grupo=grupo,
                columnas_origen_norm=columnas_origen_norm,
                producto_key_origen=producto_key_origen,
                codigo_origen_real=codigo_origen_real,
                tabla_destino=tabla_destino,
                errores=errores,
            )

        elif tabla_norm == "producto_equivalente":
            registros_tabla, estadisticas = base.generar_producto_equivalente_vertical(
                df_origen=df_origen,
                grupo=grupo,
                columnas_origen_norm=columnas_origen_norm,
                producto_key_origen=producto_key_origen,
                codigo_origen_real=codigo_origen_real,
                tabla_destino=tabla_destino,
                errores=errores,
            )

        elif tabla_norm == "producto_auditoria":
            registros_tabla, estadisticas = generar_producto_auditoria_vertical(
                df_origen=df_origen,
                grupo=grupo,
                columnas_origen_norm=columnas_origen_norm,
                producto_key_origen=producto_key_origen,
                codigo_origen_real=codigo_origen_real,
                tabla_destino=tabla_destino,
                errores=errores,
            )

        else:
            registros_tabla, estadisticas = base.generar_tabla_horizontal(
                df_origen=df_origen,
                grupo=grupo,
                columnas_origen_norm=columnas_origen_norm,
                producto_key_origen=producto_key_origen,
                codigo_origen_real=codigo_origen_real,
                tabla_destino=tabla_destino,
                errores=errores,
            )

        nombre_archivo = base.limpiar_nombre_archivo(tabla_destino) + ".csv"
        path_salida = salida_dir / nombre_archivo

        registros_tabla.to_csv(
            path_salida,
            index=False,
            sep=";",
            encoding="utf-8-sig",
        )

        tablas_generadas.append(str(path_salida))

        reportes_tablas.append({
            "tabla_destino": tabla_destino,
            "archivo_salida": str(path_salida),
            "modo_generacion": estadisticas["modo_generacion"],
            "columnas_mapeadas_para_tabla": int(len(grupo)),
            "columnas_procesadas": int(estadisticas["columnas_procesadas"]),
            "columnas_no_encontradas": int(estadisticas["columnas_no_encontradas"]),
            "campos_destino_vacios": int(estadisticas["campos_destino_vacios"]),
            "filas_origen": int(len(df_origen)),
            "filas_generadas": int(len(registros_tabla)),
        })

    return {
        "tablas_generadas": tablas_generadas,
        "reportes_tablas": reportes_tablas,
        "errores": errores,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Normaliza la tabla de productos con PRODUCTO_AUDITORIA vertical v1.15.0"
    )

    parser.add_argument(
        "--source",
        required=True,
        help="Archivo origen con los datos reales de productos. Puede ser .xlsx o .csv",
    )
    parser.add_argument(
        "--mapping",
        default="01_fuentes/Normalizacion_Tabla_Productos.xlsx",
        help="Archivo Excel con hoja MAPEO_445_COLUMNAS",
    )
    parser.add_argument(
        "--sheet",
        default=None,
        help="Nombre de la hoja del archivo origen. Si se omite, usa la primera hoja.",
    )
    parser.add_argument(
        "--out",
        default="04_salidas_normalizadas",
        help="Carpeta de salida para las tablas normalizadas",
    )

    args = parser.parse_args()

    source_path = Path(args.source)
    mapping_path = Path(args.mapping)
    salida_dir = Path(args.out)

    reportes_dir = Path("05_reportes")
    reportes_dir.mkdir(parents=True, exist_ok=True)

    print("Leyendo archivo origen...")
    df_origen = base.leer_excel_o_csv(source_path, args.sheet)
    df_origen = df_origen.fillna("")

    print("Leyendo mapeo...")
    df_mapeo = base.cargar_mapeo(mapping_path)

    print("Validando columnas...")
    columnas_origen_norm = {
        base.normalizar_nombre_columna(c): c for c in df_origen.columns
    }
    columnas_mapeo_norm = set(df_mapeo["COLUMNA_ORIGEN_NORM"])

    faltan_en_origen = sorted(columnas_mapeo_norm - set(columnas_origen_norm))
    sobran_en_origen = sorted(set(columnas_origen_norm) - columnas_mapeo_norm)

    print("Generando tablas normalizadas...")
    resultado = generar_tablas_normalizadas(
        df_origen=df_origen,
        df_mapeo=df_mapeo,
        salida_dir=salida_dir,
    )

    reporte = {
        "script": "normalizar_tabla_productos_v1_15.py",
        "version": VERSION,
        "fecha_ejecucion_utc": datetime.now(timezone.utc).isoformat(),
        "archivo_origen": str(source_path),
        "archivo_mapeo": str(mapping_path),
        "hoja_origen": args.sheet or "PRIMERA_HOJA",
        "filas_origen": int(len(df_origen)),
        "columnas_origen": int(len(df_origen.columns)),
        "columnas_mapeo": int(len(df_mapeo)),
        "faltan_en_origen": len(faltan_en_origen),
        "sobran_en_origen": len(sobran_en_origen),
        "primeras_faltantes_en_origen": faltan_en_origen[:30],
        "primeras_sobrantes_en_origen": sobran_en_origen[:30],
        "tablas_generadas": len(resultado["tablas_generadas"]),
        "detalle_tablas": resultado["reportes_tablas"],
        "errores": resultado["errores"],
        "controles": {
            "fuente_modificada": False,
            "carga_azure_realizada": False,
            "salidas_derivadas_generadas": True,
            "regla_materialidad_por_tabla": True,
            "producto_auditoria_verticalizado_por_evento": True,
            "producto_auditoria_fecha_inventada": False,
            "producto_auditoria_usuario_inventado": False,
            "producto_auditoria_terminal_inventada": False,
            "producto_auditoria_observacion_inventada": False,
            "producto_auditoria_reglas_por_producto_fila_valor": False,
            "producto_precio_verticalizado_por_fuente": True,
            "producto_parametro_verticalizado_por_origen": True,
            "producto_documento_verticalizado_por_origen": True,
            "producto_categoria_verticalizado_por_origen": True,
            "producto_proveedor_verticalizado_por_origen": True,
        },
        "nota": (
            "Este script genera tablas derivadas desde el archivo origen y el mapeo. "
            "No modifica el archivo original ni carga datos a Azure. "
            "v1.15.0 conserva la logica cerrada de v1.14.0 y agrega PRODUCTO_AUDITORIA "
            "vertical por evento de auditoria, agrupando fecha, usuario, terminal y observacion "
            "sin inventar datos y sin reglas por producto, fila o valor especifico."
        ),
    }

    reporte_path = reportes_dir / "reporte_normalizacion_tabla_productos_v1.json"
    reporte_path.write_text(
        json.dumps(reporte, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    errores_path = reportes_dir / "errores_normalizacion_tabla_productos_v1.csv"
    pd.DataFrame(resultado["errores"]).to_csv(
        errores_path,
        index=False,
        sep=";",
        encoding="utf-8-sig",
    )

    detalle_tablas_path = reportes_dir / "detalle_tablas_generadas_v1.csv"
    pd.DataFrame(resultado["reportes_tablas"]).to_csv(
        detalle_tablas_path,
        index=False,
        sep=";",
        encoding="utf-8-sig",
    )

    print("\nProceso terminado.")
    print(f"Version: {VERSION}")
    print(f"Tablas generadas: {len(resultado['tablas_generadas'])}")
    print(f"Reporte: {reporte_path}")
    print(f"Errores: {errores_path}")
    print(f"Detalle tablas: {detalle_tablas_path}")


if __name__ == "__main__":
    main()
