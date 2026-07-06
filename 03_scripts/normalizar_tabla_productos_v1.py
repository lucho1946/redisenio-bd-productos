from pathlib import Path
import argparse
import json
import re
from datetime import datetime, timezone

import pandas as pd


VERSION = "1.1.0"


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


COLUMNAS_PRECIO_MATERIALES = {
    "valor",
    "precio",
    "precio_venta",
    "precio_lista",
    "precio_compra",
    "precio_publico",
    "precio_unitario",
    "valor_unitario",
    "costo",
    "costo_promedio",
}


COLUMNAS_PROVEEDOR_MATERIALES = {
    "proveedor",
    "proveedor_id",
    "nombre_proveedor",
    "codigo_proveedor",
    "referencia_proveedor",
    "link",
    "url",
    "url_proveedor",
    "link_proveedor",
    "stock_rectificado",
    "proveedor_estado",
}


COLUMNAS_INVENTARIO_NUMERICAS_MATERIALES = {
    "existencia",
    "stock",
    "stock_total",
    "cantidad",
    "cantidad_disponible",
    "inventario",
    "saldo",
}


COLUMNAS_INVENTARIO_TEXTO_MATERIALES = {
    "bodega",
    "sede",
    "ubicacion",
    "estado_inventario",
    "fecha_inventario",
    "inventario_fecha",
}


COLUMNAS_TRAZABILIDAD = {"_origen_row", "_codigo_origen"}


def normalizar_nombre_columna(texto: str) -> str:
    """
    Normaliza nombres de columnas para comparaciones internas.
    No cambia los nombres reales usados en las salidas.
    """
    texto = str(texto or "").strip().upper()
    texto = re.sub(r"\s+", " ", texto)
    return texto


def normalizar_nombre_materialidad(texto: str) -> str:
    """
    Normaliza nombres de campos destino para reglas de materialidad.
    Convierte nombres a minúsculas y separadores homogéneos.
    """
    texto = str(texto or "").strip().lower()
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    texto = re.sub(r"_+", "_", texto).strip("_")
    return texto


def limpiar_nombre_archivo(texto: str) -> str:
    """
    Convierte el nombre de tabla destino en nombre seguro de archivo.
    """
    texto = str(texto or "").strip().lower()
    texto = re.sub(r"[^a-zA-Z0-9_]+", "_", texto)
    texto = re.sub(r"_+", "_", texto).strip("_")
    return texto or "sin_nombre"


def leer_excel_o_csv(path: Path, sheet_name: str | None = None) -> pd.DataFrame:
    """
    Lee Excel o CSV.
    Para CSV prueba varios separadores y conserva el que produzca más columnas.
    Esto evita que un CSV separado por coma se lea como una sola columna.
    """
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {path}")

    suffix = path.suffix.lower()

    if suffix in [".xlsx", ".xlsm", ".xls"]:
        if sheet_name:
            return pd.read_excel(path, sheet_name=sheet_name, dtype=str)
        return pd.read_excel(path, sheet_name=0, dtype=str)

    if suffix == ".csv":
        candidatos = []

        for encoding in ["utf-8-sig", "utf-8", "latin1"]:
            for sep in [";", ",", "\t", "|"]:
                try:
                    df = pd.read_csv(
                        path,
                        dtype=str,
                        sep=sep,
                        encoding=encoding,
                        low_memory=False,
                    )
                    candidatos.append({
                        "df": df,
                        "sep": sep,
                        "encoding": encoding,
                        "cols": len(df.columns),
                    })
                except Exception:
                    pass

        if not candidatos:
            raise ValueError(f"No se pudo leer el CSV: {path}")

        mejor = sorted(
            candidatos,
            key=lambda x: x["cols"],
            reverse=True,
        )[0]

        print(
            f"CSV detectado: sep={repr(mejor['sep'])}, "
            f"encoding={mejor['encoding']}, "
            f"columnas={mejor['cols']}"
        )

        return mejor["df"]

    raise ValueError(f"Formato no soportado: {path.suffix}")


def cargar_mapeo(path_mapeo: Path) -> pd.DataFrame:
    """
    Carga la hoja MAPEO_445_COLUMNAS del archivo de normalización.
    """
    df = pd.read_excel(path_mapeo, sheet_name="MAPEO_445_COLUMNAS", dtype=str)
    df = df.fillna("")

    columnas_requeridas = [
        "COLUMNA_ORIGEN",
        "TIPO",
        "LEN",
        "TABLA_DESTINO",
        "CAMPO_DESTINO",
        "TRANSFORMACION",
    ]

    faltantes = [c for c in columnas_requeridas if c not in df.columns]
    if faltantes:
        raise ValueError(
            "El mapeo no tiene las columnas requeridas: "
            + ", ".join(faltantes)
        )

    df["COLUMNA_ORIGEN_NORM"] = df["COLUMNA_ORIGEN"].map(normalizar_nombre_columna)
    df["TABLA_DESTINO"] = df["TABLA_DESTINO"].astype(str).str.strip()
    df["CAMPO_DESTINO"] = df["CAMPO_DESTINO"].astype(str).str.strip()
    df["TRANSFORMACION"] = df["TRANSFORMACION"].astype(str).str.strip()

    return df


def aplicar_transformacion(valor, transformacion: str):
    """
    Transformaciones conservadoras.
    Si la transformación no está implementada, se deja el valor original.
    La idea es no inventar reglas.
    """
    if pd.isna(valor):
        return ""

    valor = str(valor)
    t = str(transformacion or "").strip().upper()

    if not t or t in ["COPIAR", "DIRECTO", "AS_IS", "SIN_TRANSFORMACION"]:
        return valor

    if t in ["LIMPIAR_TEXTO", "TRIM", "STRIP"]:
        return valor.strip()

    if t in ["MAYUSCULAS", "UPPER"]:
        return valor.strip().upper()

    if t in ["MINUSCULAS", "LOWER"]:
        return valor.strip().lower()

    if t in ["VACIO", "NULL", "NO_APLICA"]:
        return ""

    # Transformación no implementada: se conserva el valor.
    return valor


def detectar_columna_codigo(df_origen: pd.DataFrame) -> str | None:
    """
    Busca una columna de código para conservar trazabilidad entre tablas.
    """
    candidatos = ["CODIGO", "CÓDIGO", "ID_PRODUCTO", "PRODUCTO_ID", "COD_PRODUCTO"]
    cols_norm = {normalizar_nombre_columna(c): c for c in df_origen.columns}

    for candidato in candidatos:
        key = normalizar_nombre_columna(candidato)
        if key in cols_norm:
            return cols_norm[key]

    return None


def valor_es_material(valor) -> bool:
    """
    Indica si un valor aporta información real.
    Se usa para no generar filas solo por ceros, NO, false o vacíos.
    """
    if valor is None:
        return False

    if pd.isna(valor):
        return False

    texto = str(valor).strip()
    if not texto:
        return False

    return texto.lower() not in VALORES_NO_MATERIALES


def valor_es_numero_positivo(valor) -> bool:
    """
    Indica si un valor representa un número mayor que cero.
    Es la regla conservadora para precios e inventario cuantitativo.
    """
    if valor is None:
        return False

    if pd.isna(valor):
        return False

    texto = str(valor).strip()
    if not texto:
        return False

    texto = texto.replace("$", "").replace(" ", "")

    # Si viene en formato 1.234,56, se convierte a 1234.56.
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    else:
        texto = texto.replace(",", ".")

    try:
        return float(texto) > 0
    except ValueError:
        return False


def fila_tiene_campos_materiales(fila: pd.Series, campos_objetivo: set[str]) -> bool:
    """
    Evalúa si la fila tiene valores materiales en alguno de los campos indicados.
    """
    for campo, valor in fila.items():
        campo_norm = normalizar_nombre_materialidad(campo)
        if campo_norm in campos_objetivo and valor_es_material(valor):
            return True
    return False


def fila_tiene_numeros_positivos(fila: pd.Series, campos_objetivo: set[str]) -> bool:
    """
    Evalúa si la fila tiene números positivos en alguno de los campos indicados.
    """
    for campo, valor in fila.items():
        campo_norm = normalizar_nombre_materialidad(campo)
        if campo_norm in campos_objetivo and valor_es_numero_positivo(valor):
            return True
    return False


def fila_tiene_materialidad(tabla_destino: str, fila: pd.Series, campos_negocio: list[str]) -> bool:
    """
    Regla de generación de filas por tabla destino.

    Objetivo:
    - Conservar el proceso general de normalización.
    - Evitar filas generadas solo por 0, 0.00, NO o flags por defecto.
    - Aplicar criterios más estrictos en tablas críticas detectadas por auditoría.
    """
    tabla_norm = limpiar_nombre_archivo(tabla_destino)
    fila_negocio = fila[campos_negocio]

    if tabla_norm == "producto_precio":
        return fila_tiene_numeros_positivos(
            fila_negocio,
            COLUMNAS_PRECIO_MATERIALES,
        )

    if tabla_norm == "producto_proveedor":
        return fila_tiene_campos_materiales(
            fila_negocio,
            COLUMNAS_PROVEEDOR_MATERIALES,
        )

    if tabla_norm == "producto_inventario":
        return (
            fila_tiene_numeros_positivos(
                fila_negocio,
                COLUMNAS_INVENTARIO_NUMERICAS_MATERIALES,
            )
            or fila_tiene_campos_materiales(
                fila_negocio,
                COLUMNAS_INVENTARIO_TEXTO_MATERIALES,
            )
        )

    return any(valor_es_material(valor) for valor in fila_negocio)


def generar_tablas_normalizadas(
    df_origen: pd.DataFrame,
    df_mapeo: pd.DataFrame,
    salida_dir: Path,
) -> dict:
    """
    Genera un CSV por cada TABLA_DESTINO del mapeo.
    """
    salida_dir.mkdir(parents=True, exist_ok=True)

    columnas_origen_norm = {
        normalizar_nombre_columna(c): c for c in df_origen.columns
    }

    columna_codigo = detectar_columna_codigo(df_origen)

    reportes_tablas = []
    errores = []
    tablas_generadas = []

    # No cargamos como tabla normalizada lo marcado explícitamente como eliminar.
    tablas_a_ignorar = {"ELIMINAR", "REVISAR/ELIMINAR", ""}

    for tabla_destino, grupo in df_mapeo.groupby("TABLA_DESTINO", dropna=False):
        tabla_destino = str(tabla_destino or "").strip()

        if tabla_destino.upper() in tablas_a_ignorar:
            continue

        registros_tabla = pd.DataFrame()
        registros_tabla["_origen_row"] = range(1, len(df_origen) + 1)

        if columna_codigo:
            registros_tabla["_codigo_origen"] = df_origen[columna_codigo].fillna("")

        columnas_procesadas = 0
        columnas_no_encontradas = 0
        campos_destino_vacios = 0

        for _, regla in grupo.iterrows():
            col_origen = str(regla["COLUMNA_ORIGEN"]).strip()
            col_origen_norm = normalizar_nombre_columna(col_origen)
            campo_destino = str(regla["CAMPO_DESTINO"]).strip()
            transformacion = str(regla["TRANSFORMACION"]).strip()

            if not campo_destino:
                campos_destino_vacios += 1
                errores.append({
                    "tabla_destino": tabla_destino,
                    "columna_origen": col_origen,
                    "error": "SIN_CAMPO_DESTINO",
                    "detalle": "La regla no tiene CAMPO_DESTINO.",
                })
                continue

            if col_origen_norm not in columnas_origen_norm:
                columnas_no_encontradas += 1
                registros_tabla[campo_destino] = ""
                errores.append({
                    "tabla_destino": tabla_destino,
                    "columna_origen": col_origen,
                    "campo_destino": campo_destino,
                    "error": "COLUMNA_ORIGEN_NO_EXISTE",
                    "detalle": "La columna del mapeo no existe en el archivo origen.",
                })
                continue

            col_real = columnas_origen_norm[col_origen_norm]
            registros_tabla[campo_destino] = df_origen[col_real].map(
                lambda v: aplicar_transformacion(v, transformacion)
            )
            columnas_procesadas += 1

        # Eliminar filas sin materialidad real, conservando trazabilidad.
        # Antes cualquier valor no vacío generaba fila; eso incluía 0, 0.00, NO y flags.
        campos_negocio = [
            c for c in registros_tabla.columns
            if c not in COLUMNAS_TRAZABILIDAD
        ]

        if campos_negocio:
            mask_con_datos = registros_tabla.apply(
                lambda row: fila_tiene_materialidad(
                    tabla_destino=tabla_destino,
                    fila=row,
                    campos_negocio=campos_negocio,
                ),
                axis=1,
            )
            registros_tabla = registros_tabla[mask_con_datos].copy()

        nombre_archivo = limpiar_nombre_archivo(tabla_destino) + ".csv"
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
            "columnas_mapeadas_para_tabla": int(len(grupo)),
            "columnas_procesadas": int(columnas_procesadas),
            "columnas_no_encontradas": int(columnas_no_encontradas),
            "campos_destino_vacios": int(campos_destino_vacios),
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
        description="Normaliza la tabla de productos usando Normalizacion_Tabla_Productos.xlsx"
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
    df_origen = leer_excel_o_csv(source_path, args.sheet)
    df_origen = df_origen.fillna("")

    print("Leyendo mapeo...")
    df_mapeo = cargar_mapeo(mapping_path)

    print("Validando columnas...")
    columnas_origen_norm = {
        normalizar_nombre_columna(c): c for c in df_origen.columns
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
        "script": "normalizar_tabla_productos_v1.py",
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
            "tablas_con_materialidad_especifica": [
                "producto_precio",
                "producto_proveedor",
                "producto_inventario",
            ],
        },
        "nota": (
            "Este script genera tablas derivadas desde el archivo origen y el mapeo. "
            "No modifica el archivo original ni carga datos a Azure. "
            "Desde la versión 1.1.0 aplica reglas de materialidad para evitar filas "
            "generadas solo por ceros, NO o flags por defecto."
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
    print(f"Tablas generadas: {len(resultado['tablas_generadas'])}")
    print(f"Reporte: {reporte_path}")
    print(f"Errores: {errores_path}")
    print(f"Detalle tablas: {detalle_tablas_path}")


if __name__ == "__main__":
    main()
