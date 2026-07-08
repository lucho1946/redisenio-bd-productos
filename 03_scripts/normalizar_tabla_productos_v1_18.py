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
import normalizar_tabla_productos_v1_15 as v115
import normalizar_tabla_productos_v1_16 as v116


VERSION = "1.18.0"
TIPO_CATEGORIA_MERCADO = "MERCADO"
VALORES_BOOLEANOS_POSITIVOS = {"SI", "SÍ", "YES", "TRUE", "1"}


def normalizar_valor(valor) -> str:
    if valor is None or pd.isna(valor):
        return ""
    return str(valor).strip().upper()


def auditar_columnas_mercado_en_origen(df_origen: pd.DataFrame, columnas_mercado: list[str]) -> dict:
    columnas_origen_norm = {
        base.normalizar_nombre_columna(c): c for c in df_origen.columns
    }

    resultado = {}

    for columna in columnas_mercado:
        col_real = columnas_origen_norm.get(base.normalizar_nombre_columna(columna), "")

        if not col_real:
            resultado[columna] = {
                "columna_existe": False,
                "total_no_vacio": 0,
                "top_valores": {},
            }
            continue

        serie = df_origen[col_real].fillna("").astype(str).str.strip()

        resultado[columna] = {
            "columna_existe": True,
            "columna_real": col_real,
            "total_no_vacio": int((serie != "").sum()),
            "top_valores": {
                str(k): int(v)
                for k, v in serie.value_counts(dropna=False).head(20).to_dict().items()
            },
        }

    return resultado


def postprocesar_booleanos_mercado_en_categoria(
    df_origen: pd.DataFrame,
    salida_dir: Path,
) -> dict:
    path_categoria = salida_dir / "producto_categoria.csv"
    reportes_dir = Path("05_reportes")
    reportes_dir.mkdir(parents=True, exist_ok=True)

    columnas_mercado_origen = ["MERCA_CLI", "CLASI_MERCA", "PSO", "MERCA_CLI_MERCA"]
    auditoria_origen = auditar_columnas_mercado_en_origen(
        df_origen=df_origen,
        columnas_mercado=columnas_mercado_origen,
    )

    if not path_categoria.exists():
        return {
            "archivo": str(path_categoria),
            "archivo_existe": False,
            "filas_antes": 0,
            "filas_despues": 0,
            "filas_removidas": 0,
            "auditoria_origen": auditoria_origen,
            "estado": "PRODUCTO_CATEGORIA_NO_EXISTE",
        }

    df = pd.read_csv(path_categoria, sep=";", dtype=str, encoding="utf-8-sig").fillna("")
    filas_antes = int(len(df))

    tipo_categoria_norm = df["tipo_categoria"].map(normalizar_valor)
    categoria_id_norm = df["categoria_id"].map(normalizar_valor)

    mask_booleano_mercado = (
        tipo_categoria_norm.eq(TIPO_CATEGORIA_MERCADO)
        & categoria_id_norm.isin(VALORES_BOOLEANOS_POSITIVOS)
    )

    df_removidas = df.loc[mask_booleano_mercado].copy()
    df_final = df.loc[~mask_booleano_mercado].copy()

    df_final.to_csv(path_categoria, index=False, sep=";", encoding="utf-8-sig")

    path_removidas = reportes_dir / "mercado_booleanos_indicador_removidos_v118.csv"
    df_removidas.to_csv(path_removidas, index=False, sep=";", encoding="utf-8-sig")

    removidas_por_origen_valor = {}
    if len(df_removidas):
        conteo = (
            df_removidas
            .groupby(["categoria_origen", "categoria_id"])
            .size()
            .reset_index(name="filas")
        )
        removidas_por_origen_valor = {
            f"{row['categoria_origen']}={row['categoria_id']}": int(row["filas"])
            for _, row in conteo.iterrows()
        }

    restantes_booleanos = df_final[
        df_final["tipo_categoria"].map(normalizar_valor).eq(TIPO_CATEGORIA_MERCADO)
        & df_final["categoria_id"].map(normalizar_valor).isin(VALORES_BOOLEANOS_POSITIVOS)
    ]

    return {
        "archivo": str(path_categoria),
        "archivo_existe": True,
        "filas_antes": filas_antes,
        "filas_despues": int(len(df_final)),
        "filas_removidas": int(len(df_removidas)),
        "criterio_remocion": "tipo_categoria=MERCADO y categoria_id booleano positivo",
        "valores_booleanos_positivos": sorted(VALORES_BOOLEANOS_POSITIVOS),
        "removidas_por_origen_valor": removidas_por_origen_valor,
        "booleanos_mercado_restantes": int(len(restantes_booleanos)),
        "archivo_evidencia_removidos": str(path_removidas),
        "auditoria_origen": auditoria_origen,
        "decision_tecnica": (
            "Los valores booleanos positivos de campos tipo MERCADO no se conservan como categoria_id "
            "porque SI/YES/TRUE/1 no describen una familia ni dimension de producto. "
            "El dato no se elimina de la fuente; queda documentado como indicador heredado pendiente de ubicacion definitiva."
        ),
        "estado": "BOOLEANOS_MERCADO_EXCLUIDOS_DE_PRODUCTO_CATEGORIA",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Normaliza productos v1.18.0: excluye booleanos positivos tipo MERCADO de PRODUCTO_CATEGORIA."
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
    df_origen = base.leer_excel_o_csv(source_path, args.sheet).fillna("")

    print("Leyendo mapeo...")
    df_mapeo = base.cargar_mapeo(mapping_path)

    print("Validando columnas...")
    columnas_origen_norm = {
        base.normalizar_nombre_columna(c): c for c in df_origen.columns
    }
    columnas_mapeo_norm = set(df_mapeo["COLUMNA_ORIGEN_NORM"])

    faltan_en_origen = sorted(columnas_mapeo_norm - set(columnas_origen_norm))
    sobran_en_origen = sorted(set(columnas_origen_norm) - columnas_mapeo_norm)

    print("Generando tablas normalizadas base v1.15.0...")
    resultado = v115.generar_tablas_normalizadas(
        df_origen=df_origen,
        df_mapeo=df_mapeo,
        salida_dir=salida_dir,
    )

    print("Aplicando decision de PRODUCTO_INVENTARIO v1.16.0...")
    postproceso_v116 = v116.postprocesar_inventario_y_equivalentes(
        df_origen=df_origen,
        salida_dir=salida_dir,
    )

    print("Aplicando decision tecnica de booleanos tipo MERCADO v1.18.0...")
    postproceso_mercado_booleanos = postprocesar_booleanos_mercado_en_categoria(
        df_origen=df_origen,
        salida_dir=salida_dir,
    )

    reporte = {
        "script": "normalizar_tabla_productos_v1_18.py",
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
        "postproceso_v116": postproceso_v116,
        "postproceso_mercado_booleanos_v118": postproceso_mercado_booleanos,
        "controles": {
            "fuente_modificada": False,
            "carga_sql_server_realizada": False,
            "carga_azure_realizada": False,
            "salidas_derivadas_generadas": True,
            "producto_auditoria_verticalizado_por_evento": True,
            "producto_inventario_campo_alternativa_ambiguo_removido": postproceso_v116["producto_inventario"].get("campo_removido", False),
            "producto_equivalente_recibe_alternativos_desde_inventario": True,
            "stock_alternativa_cantidad_producto_aprobado_como_cantidad": False,
            "booleanos_mercado_aprobados_como_categoria": False,
            "booleanos_mercado_documentados_como_indicador_pendiente_ubicacion": True,
            "reglas_por_producto_fila_valor": False,
        },
        "decision_tecnica_v118": (
            "Los valores booleanos positivos de campos tipo MERCADO se excluyen de PRODUCTO_CATEGORIA "
            "para no registrar SI/YES/TRUE/1 como categoria_id. "
            "Los textos descriptivos no booleanos de tipo MERCADO se conservan."
        ),
        "nota": (
            "v1.18.0 reutiliza la logica cerrada de v1.16.0. "
            "Luego excluye valores booleanos positivos de tipo MERCADO en PRODUCTO_CATEGORIA por evidencia de que no describen categoria comercial. "
            "No modifica fuentes originales ni carga datos a SQL Server/Azure."
        ),
    }

    reporte_path = reportes_dir / "reporte_normalizacion_tabla_productos_v118.json"
    reporte_path.write_text(
        json.dumps(reporte, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    errores_path = reportes_dir / "errores_normalizacion_tabla_productos_v118.csv"
    pd.DataFrame(resultado["errores"]).to_csv(
        errores_path,
        index=False,
        sep=";",
        encoding="utf-8-sig",
    )

    detalle_tablas_path = reportes_dir / "detalle_tablas_generadas_v118.csv"
    pd.DataFrame(resultado["reportes_tablas"]).to_csv(
        detalle_tablas_path,
        index=False,
        sep=";",
        encoding="utf-8-sig",
    )

    postproceso_path = reportes_dir / "reporte_postproceso_mercado_booleanos_v118.json"
    postproceso_path.write_text(
        json.dumps(postproceso_mercado_booleanos, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\nProceso terminado.")
    print(f"Version: {VERSION}")
    print(f"Tablas generadas: {len(resultado['tablas_generadas'])}")
    print(f"Reporte: {reporte_path}")
    print(f"Errores: {errores_path}")
    print(f"Detalle tablas: {detalle_tablas_path}")
    print(f"Postproceso mercado booleanos: {postproceso_path}")
    print("\nResumen v1.18.0:")
    print(json.dumps(postproceso_mercado_booleanos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
