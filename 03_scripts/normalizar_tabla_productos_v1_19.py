from pathlib import Path
import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import normalizar_tabla_productos_v1 as base
import normalizar_tabla_productos_v1_15 as v115
import normalizar_tabla_productos_v1_16 as v116
import normalizar_tabla_productos_v1_18 as v118


VERSION = "1.19.0"


def normalizar_categoria(valor) -> str:
    texto = "" if valor is None or pd.isna(valor) else str(valor).strip()
    texto = texto.replace("+", " ")
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.lower()
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def postprocesar_clasi_merca_duplicado(
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

    df["categoria_norm_tmp"] = df["categoria_id"].map(normalizar_categoria)

    clasificaciones = df[df["tipo_categoria"].eq("CLASIFICACION")].copy()

    mapa_clasificaciones = (
        clasificaciones
        .groupby("_producto_key_origen")["categoria_norm_tmp"]
        .apply(lambda s: set([x for x in s if x]))
        .to_dict()
    )

    mask_clasi_merca = (
        df["tipo_categoria"].eq("MERCADO")
        & df["categoria_origen"].eq("CLASI_MERCA")
    )

    def duplica_clasificacion(row) -> bool:
        producto_key = row["_producto_key_origen"]
        valor_norm = row["categoria_norm_tmp"]
        return valor_norm in mapa_clasificaciones.get(producto_key, set())

    mask_duplicado = mask_clasi_merca & df.apply(duplica_clasificacion, axis=1)

    df_removidas = df.loc[mask_duplicado].copy()
    df_final = df.loc[~mask_duplicado].copy()

    df_removidas = df_removidas.drop(columns=["categoria_norm_tmp"], errors="ignore")
    df_final = df_final.drop(columns=["categoria_norm_tmp"], errors="ignore")

    df_final.to_csv(path_categoria, index=False, sep=";", encoding="utf-8-sig")

    path_removidas = reportes_dir / "clasi_merca_duplicados_removidos_v119.csv"
    df_removidas.to_csv(path_removidas, index=False, sep=";", encoding="utf-8-sig")

    mercado_restante = df_final[df_final["tipo_categoria"].eq("MERCADO")].copy()

    return {
        "archivo": str(path_categoria),
        "archivo_existe": True,
        "filas_antes": filas_antes,
        "filas_despues": int(len(df_final)),
        "filas_removidas": int(len(df_removidas)),
        "criterio_remocion": (
            "tipo_categoria=MERCADO, categoria_origen=CLASI_MERCA y categoria_id normalizado "
            "duplica una categoria CLASIFICACION del mismo producto"
        ),
        "archivo_evidencia_removidos": str(path_removidas),
        "mercado_restante_total": int(len(mercado_restante)),
        "mercado_restante_por_origen": {
            str(k): int(v)
            for k, v in mercado_restante["categoria_origen"].value_counts().to_dict().items()
        },
        "decision_tecnica": (
            "CLASI_MERCA que duplica una CLASIFICACION del mismo producto no se conserva como categoria adicional "
            "para evitar doble registro semantico en PRODUCTO_CATEGORIA. "
            "CLASI_MERCA no duplicado se conserva provisionalmente como dimension de mercado pendiente de definicion."
        ),
        "estado": "CLASI_MERCA_DUPLICADO_EXCLUIDO_DE_PRODUCTO_CATEGORIA",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Normaliza productos v1.19.0: excluye booleanos MERCADO y CLASI_MERCA duplicado."
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
    postproceso_clasi_merca = postprocesar_clasi_merca_duplicado(
        salida_dir=salida_dir,
    )

    reporte = {
        "script": "normalizar_tabla_productos_v1_19.py",
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
        "postproceso_clasi_merca_v119": postproceso_clasi_merca,
        "controles": {
            "fuente_modificada": False,
            "carga_sql_server_realizada": False,
            "carga_azure_realizada": False,
            "salidas_derivadas_generadas": True,
            "booleanos_mercado_aprobados_como_categoria": False,
            "clasi_merca_duplicado_aprobado_como_categoria_adicional": False,
            "clasi_merca_no_duplicado_conservado_provisionalmente": True,
            "reglas_por_producto_fila_valor": False,
        },
        "decision_tecnica_v119": (
            "CLASI_MERCA duplicado contra CLASIFICACION del mismo producto se excluye de PRODUCTO_CATEGORIA. "
            "CLASI_MERCA no duplicado se conserva provisionalmente como dimension de mercado pendiente de definicion."
        ),
    }

    reporte_path = reportes_dir / "reporte_normalizacion_tabla_productos_v119.json"
    reporte_path.write_text(
        json.dumps(reporte, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    postproceso_path = reportes_dir / "reporte_postproceso_clasi_merca_v119.json"
    postproceso_path.write_text(
        json.dumps(postproceso_clasi_merca, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\nProceso terminado.")
    print(f"Version: {VERSION}")
    print(f"Tablas generadas: {len(resultado['tablas_generadas'])}")
    print(f"Reporte: {reporte_path}")
    print(f"Postproceso CLASI_MERCA: {postproceso_path}")
    print("\nResumen v1.19.0:")
    print(json.dumps(postproceso_clasi_merca, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
