from pathlib import Path
import argparse
import json
import re
import sys
from datetime import datetime, timezone

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import normalizar_tabla_productos_v1 as base
import normalizar_tabla_productos_v1_15 as v115


VERSION = "1.16.0"
CAMPO_ALTERNATIVA_AMBIGUO = "alternativa / alternativa_cantidad"
COLUMNA_PRODUCTO_ALTERNATIVO = "STOCK_ALTERNATIVA_PRODUCTO"


def limpiar_texto(valor) -> str:
    if valor is None or pd.isna(valor):
        return ""
    return str(valor).strip()


def limpiar_codigo_alternativo(valor: str) -> str:
    texto = limpiar_texto(valor)
    texto = texto.replace("\t", "").replace(" ", "")
    return texto.upper()


def parece_codigo_producto(valor: str) -> bool:
    codigo = limpiar_codigo_alternativo(valor)
    if not codigo:
        return False
    if re.fullmatch(r"P\d{4,}", codigo):
        return True
    if re.fullmatch(r"\d{4,}", codigo):
        return True
    return False


def construir_variantes_codigo(valor: str) -> list[str]:
    codigo = limpiar_codigo_alternativo(valor)
    if not codigo:
        return []

    variantes = [codigo]
    if codigo.startswith("P") and codigo[1:].isdigit():
        variantes.append(codigo[1:])
    elif codigo.isdigit():
        variantes.append(f"P{codigo}")

    resultado = []
    for item in variantes:
        if item not in resultado:
            resultado.append(item)
    return resultado


def detectar_columna_real(columnas_origen_norm: dict[str, str], columna: str) -> str:
    return columnas_origen_norm.get(base.normalizar_nombre_columna(columna), "")


def construir_codigos_piloto(df_origen: pd.DataFrame) -> set[str]:
    columna_codigo = base.detectar_columna_codigo(df_origen)
    if not columna_codigo or columna_codigo not in df_origen.columns:
        return set()
    return set(df_origen[columna_codigo].astype(str).fillna("").str.strip().str.upper())


def estado_producto_alternativo(valor: str, codigos_piloto: set[str]) -> str:
    codigo = limpiar_codigo_alternativo(valor)
    if not codigo:
        return "SIN_VALOR"

    variantes = construir_variantes_codigo(codigo)
    if any(variante in codigos_piloto for variante in variantes):
        return "PRODUCTO_ALTERNATIVO_VALIDADO_PILOTO"

    if parece_codigo_producto(codigo):
        return "PRODUCTO_ALTERNATIVO_PENDIENTE_VALIDACION_BD"

    return "PRODUCTO_ALTERNATIVO_REVISION_HUMANA"


def quitar_alternativa_de_inventario(salida_dir: Path) -> dict:
    path = salida_dir / "producto_inventario.csv"
    if not path.exists():
        return {
            "archivo": str(path),
            "archivo_existe": False,
            "campo_removido": False,
            "filas": 0,
            "columnas_antes": 0,
            "columnas_despues": 0,
        }

    df = pd.read_csv(path, sep=";", dtype=str, encoding="utf-8-sig").fillna("")
    columnas_antes = len(df.columns)
    campo_existe = CAMPO_ALTERNATIVA_AMBIGUO in df.columns

    if campo_existe:
        df = df.drop(columns=[CAMPO_ALTERNATIVA_AMBIGUO])
        df.to_csv(path, index=False, sep=";", encoding="utf-8-sig")

    return {
        "archivo": str(path),
        "archivo_existe": True,
        "campo_removido": bool(campo_existe),
        "campo_removido_nombre": CAMPO_ALTERNATIVA_AMBIGUO if campo_existe else "",
        "filas": int(len(df)),
        "columnas_antes": int(columnas_antes),
        "columnas_despues": int(len(df.columns)),
    }


def generar_equivalentes_desde_inventario(
    df_origen: pd.DataFrame,
    salida_dir: Path,
) -> dict:
    columnas_origen_norm = {
        base.normalizar_nombre_columna(c): c for c in df_origen.columns
    }
    columna_alt_real = detectar_columna_real(columnas_origen_norm, COLUMNA_PRODUCTO_ALTERNATIVO)

    path_equivalente = salida_dir / "producto_equivalente.csv"
    if path_equivalente.exists():
        df_equivalente = pd.read_csv(
            path_equivalente,
            sep=";",
            dtype=str,
            encoding="utf-8-sig",
        ).fillna("")
    else:
        df_equivalente = pd.DataFrame(columns=[
            "_origen_row",
            "_producto_key_origen",
            "_codigo_origen",
            "equivalente_origen",
            "tipo_equivalente",
            "fuente_equivalente",
            "referencia_equivalente",
            "marca_equivalente",
            "verificado",
            "link_proveedor",
            "estado_equivalente",
        ])

    if not columna_alt_real:
        return {
            "archivo": str(path_equivalente),
            "columna_origen": COLUMNA_PRODUCTO_ALTERNATIVO,
            "columna_origen_existe": False,
            "registros_alternativos_detectados": 0,
            "registros_agregados": 0,
            "registros_equivalente_final": int(len(df_equivalente)),
            "estados": {},
        }

    producto_key_origen = base.construir_producto_key_origen(df_origen)
    columna_codigo = base.detectar_columna_codigo(df_origen)
    codigo_origen_real = base.construir_codigo_origen_real(
        df_origen=df_origen,
        columna_codigo=columna_codigo,
    )
    codigos_piloto = construir_codigos_piloto(df_origen)

    registros = []
    for idx in df_origen.index:
        valor_original = limpiar_texto(df_origen.at[idx, columna_alt_real])
        if not base.valor_es_material(valor_original):
            continue

        valor_limpio = limpiar_codigo_alternativo(valor_original)
        estado = estado_producto_alternativo(valor_limpio, codigos_piloto)

        registros.append({
            "_origen_row": int(idx) + 1,
            "_producto_key_origen": producto_key_origen.loc[idx],
            "_codigo_origen": codigo_origen_real.loc[idx],
            "equivalente_origen": COLUMNA_PRODUCTO_ALTERNATIVO,
            "tipo_equivalente": "PRODUCTO_ALTERNATIVO",
            "fuente_equivalente": "INVENTARIO",
            "referencia_equivalente": valor_limpio,
            "marca_equivalente": "",
            "verificado": "SI_PILOTO" if estado == "PRODUCTO_ALTERNATIVO_VALIDADO_PILOTO" else "NO",
            "link_proveedor": "",
            "estado_equivalente": estado,
        })

    df_nuevos = pd.DataFrame(registros, columns=df_equivalente.columns)
    registros_detectados = int(len(df_nuevos))

    if registros_detectados:
        df_final = pd.concat([df_equivalente, df_nuevos], ignore_index=True)
        df_final = df_final.drop_duplicates(
            subset=[
                "_producto_key_origen",
                "_codigo_origen",
                "equivalente_origen",
                "tipo_equivalente",
                "referencia_equivalente",
            ],
            keep="first",
        )
    else:
        df_final = df_equivalente.copy()

    registros_agregados = int(len(df_final) - len(df_equivalente))
    df_final.to_csv(path_equivalente, index=False, sep=";", encoding="utf-8-sig")

    estados = {}
    if registros_detectados:
        estados = {
            str(k): int(v)
            for k, v in df_nuevos["estado_equivalente"].value_counts().to_dict().items()
        }

    return {
        "archivo": str(path_equivalente),
        "columna_origen": COLUMNA_PRODUCTO_ALTERNATIVO,
        "columna_origen_existe": True,
        "registros_alternativos_detectados": registros_detectados,
        "registros_agregados": registros_agregados,
        "registros_equivalente_inicial": int(len(df_equivalente)),
        "registros_equivalente_final": int(len(df_final)),
        "estados": estados,
        "decision_don_andres": "STOCK_ALTERNATIVA_PRODUCTO se interpreta como producto alternativo, no como cantidad alternativa.",
        "nota_conservadora": (
            "Solo se migra STOCK_ALTERNATIVA_PRODUCTO. "
            "STOCK_ALTERNATIVA_CANTIDAD_PRODUCTO no se aprueba como cantidad de inventario ni se convierte automaticamente."
        ),
    }


def postprocesar_inventario_y_equivalentes(
    df_origen: pd.DataFrame,
    salida_dir: Path,
) -> dict:
    inventario = quitar_alternativa_de_inventario(salida_dir)
    equivalentes = generar_equivalentes_desde_inventario(
        df_origen=df_origen,
        salida_dir=salida_dir,
    )

    return {
        "producto_inventario": inventario,
        "producto_equivalente": equivalentes,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Normaliza productos v1.16.0: auditoria vertical y alternativos de inventario en PRODUCTO_EQUIVALENTE."
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
    postproceso = postprocesar_inventario_y_equivalentes(
        df_origen=df_origen,
        salida_dir=salida_dir,
    )

    reporte = {
        "script": "normalizar_tabla_productos_v1_16.py",
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
        "postproceso_v116": postproceso,
        "controles": {
            "fuente_modificada": False,
            "carga_azure_realizada": False,
            "salidas_derivadas_generadas": True,
            "producto_auditoria_verticalizado_por_evento": True,
            "producto_inventario_campo_alternativa_ambiguo_removido": postproceso["producto_inventario"].get("campo_removido", False),
            "producto_equivalente_recibe_alternativos_desde_inventario": True,
            "stock_alternativa_cantidad_producto_aprobado_como_cantidad": False,
            "reglas_por_producto_fila_valor": False,
        },
        "decision_don_andres": (
            "El campo de alternativa en inventario se interpreta como producto alternativo, "
            "no como producto alternativo mas cantidad alternativa."
        ),
        "nota": (
            "v1.16.0 reutiliza la logica cerrada de v1.15.0. "
            "Luego retira de PRODUCTO_INVENTARIO el campo ambiguo alternativa / alternativa_cantidad "
            "y agrega a PRODUCTO_EQUIVALENTE relaciones de PRODUCTO_ALTERNATIVO desde STOCK_ALTERNATIVA_PRODUCTO. "
            "No modifica fuentes originales ni carga datos a SQL Server/Azure."
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

    postproceso_path = reportes_dir / "reporte_postproceso_inventario_v116.json"
    postproceso_path.write_text(
        json.dumps(postproceso, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\nProceso terminado.")
    print(f"Version: {VERSION}")
    print(f"Tablas generadas: {len(resultado['tablas_generadas'])}")
    print(f"Reporte: {reporte_path}")
    print(f"Errores: {errores_path}")
    print(f"Detalle tablas: {detalle_tablas_path}")
    print(f"Postproceso inventario: {postproceso_path}")
    print("\nResumen v1.16.0:")
    print(json.dumps(postproceso, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
