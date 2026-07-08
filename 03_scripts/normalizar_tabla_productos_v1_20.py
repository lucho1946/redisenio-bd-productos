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
import normalizar_tabla_productos_v1_18 as v118
import normalizar_tabla_productos_v1_19 as v119


VERSION = "1.20.0"


def postprocesar_clasi_merca_restante(
    salida_dir: Path,
) -> dict:
    path_categoria = salida_dir / "producto_categoria.csv"
    reportes_dir = Path("05_reportes")
    reportes_dir.mkdir(parents=True, exist_ok=True)

    if not path_categoria.exists():
        return {
            "archivo": str(path_categoria),
            "archivo_existe": False,
            "filas_antes": 0,
            "filas_despues": 0,
            "filas_removidas": 0,
            "estado": "PRODUCTO_CATEGORIA_NO_EXISTE",
        }

    df = pd.read_csv(path_categoria, sep=";", dtype=str, encoding="utf-8-sig").fillna("")
    filas_antes = int(len(df))

    mask_clasi_merca_restante = (
        df["tipo_categoria"].eq("MERCADO")
        & df["categoria_origen"].eq("CLASI_MERCA")
    )

    df_removidas = df.loc[mask_clasi_merca_restante].copy()
    df_final = df.loc[~mask_clasi_merca_restante].copy()

    df_final.to_csv(path_categoria, index=False, sep=";", encoding="utf-8-sig")

    path_removidas = reportes_dir / "clasi_merca_restantes_removidos_v120.csv"
    df_removidas.to_csv(path_removidas, index=False, sep=";", encoding="utf-8-sig")

    mercado_restante = df_final[df_final["tipo_categoria"].eq("MERCADO")].copy()

    return {
        "archivo": str(path_categoria),
        "archivo_existe": True,
        "filas_antes": filas_antes,
        "filas_despues": int(len(df_final)),
        "filas_removidas": int(len(df_removidas)),
        "criterio_remocion": "tipo_categoria=MERCADO y categoria_origen=CLASI_MERCA restante",
        "archivo_evidencia_removidos": str(path_removidas),
        "mercado_restante_total": int(len(mercado_restante)),
        "mercado_restante_por_origen": {
            str(k): int(v)
            for k, v in mercado_restante["categoria_origen"].value_counts().to_dict().items()
        },
        "decision_tecnica": (
            "Los CLASI_MERCA restantes no se conservan en PRODUCTO_CATEGORIA como categoria definitiva. "
            "Se documentan como agrupadores o dimensiones comerciales pendientes de modelo, para evitar mezclar "
            "clasificacion tecnica con navegacion o mercado."
        ),
        "estado": "CLASI_MERCA_RESTANTE_EXCLUIDO_DE_PRODUCTO_CATEGORIA",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Normaliza productos v1.20.0: excluye CLASI_MERCA restante de PRODUCTO_CATEGORIA."
    )
    parser.add_argument("--source", required=True)
    parser.add_argument("--mapping", default="01_fuentes/Normalizacion_Tabla_Productos.xlsx")
    parser.add_argument("--sheet", default=None)
    parser.add_argument("--out", default="04_salidas_normalizadas")

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

    print("Aplicando decision de booleanos MERCADO v1.18.0...")
    postproceso_mercado_booleanos = v118.postprocesar_booleanos_mercado_en_categoria(
        df_origen=df_origen,
        salida_dir=salida_dir,
    )

    print("Aplicando decision de CLASI_MERCA duplicado v1.19.0...")
    postproceso_clasi_merca_duplicado = v119.postprocesar_clasi_merca_duplicado(
        salida_dir=salida_dir,
    )

    print("Aplicando decision de CLASI_MERCA restante v1.20.0...")
    postproceso_clasi_merca_restante = postprocesar_clasi_merca_restante(
        salida_dir=salida_dir,
    )

    reporte = {
        "script": "normalizar_tabla_productos_v1_20.py",
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
        "postproceso_clasi_merca_duplicado_v119": postproceso_clasi_merca_duplicado,
        "postproceso_clasi_merca_restante_v120": postproceso_clasi_merca_restante,
        "controles": {
            "fuente_modificada": False,
            "carga_sql_server_realizada": False,
            "carga_azure_realizada": False,
            "salidas_derivadas_generadas": True,
            "booleanos_mercado_aprobados_como_categoria": False,
            "clasi_merca_duplicado_aprobado_como_categoria_adicional": False,
            "clasi_merca_restante_aprobado_como_categoria_definitiva": False,
            "clasi_merca_documentado_como_dimension_comercial_pendiente": True,
            "reglas_por_producto_fila_valor": False,
        },
        "decision_tecnica_v120": (
            "CLASI_MERCA no se conserva automaticamente en PRODUCTO_CATEGORIA. "
            "Los duplicados se excluyen y los restantes se documentan como agrupadores/dimensiones comerciales pendientes de modelo."
        ),
    }

    reporte_path = reportes_dir / "reporte_normalizacion_tabla_productos_v120.json"
    reporte_path.write_text(
        json.dumps(reporte, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    postproceso_path = reportes_dir / "reporte_postproceso_clasi_merca_restante_v120.json"
    postproceso_path.write_text(
        json.dumps(postproceso_clasi_merca_restante, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\nProceso terminado.")
    print(f"Version: {VERSION}")
    print(f"Tablas generadas: {len(resultado['tablas_generadas'])}")
    print(f"Reporte: {reporte_path}")
    print(f"Postproceso CLASI_MERCA restante: {postproceso_path}")
    print("\nResumen v1.20.0:")
    print(json.dumps(postproceso_clasi_merca_restante, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
