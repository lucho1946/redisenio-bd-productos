from pathlib import Path
import argparse
import json
import re
from datetime import datetime, timezone

import pandas as pd


VERSION = "1.12.0"


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
    "proveedor_id_fk",
    "nombre_proveedor",
    "codigo_proveedor",
    "referencia_proveedor",
    "link",
    "url",
    "url_proveedor",
    "link_proveedor",
    "stock_rectificado",
    "stock_rectificado_stock_encontrado",
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


COLUMNAS_TRAZABILIDAD = {
    "_origen_row",
    "_producto_key_origen",
    "_codigo_origen",
}


DOCUMENTOS_PRODUCTO_DEFINICION = {
    "LINK_CAT": {"tipo_documento": "CATALOGO", "idioma": "es"},
    "LINK_GUIA_RAP": {"tipo_documento": "GUIA_RAPIDA", "idioma": "es"},
    "LINK_MAN": {"tipo_documento": "MANUAL", "idioma": "es"},
    "OTRO_LINK_1": {"tipo_documento": "OTRO", "idioma": "es"},
    "VIDEO": {"tipo_documento": "VIDEO", "idioma": ""},
    "LINK_CAT_ESP": {"tipo_documento": "CATALOGO", "idioma": "es"},
    "LINK_GUIA_RAP_ESP": {"tipo_documento": "GUIA_RAPIDA", "idioma": "es"},
    "LINK_MAN_ESP": {"tipo_documento": "MANUAL", "idioma": "es"},
    "LINK_OTRA_INFO_ESP": {"tipo_documento": "OTRO", "idioma": "es"},
    "LINK_CAT_ING": {"tipo_documento": "CATALOGO", "idioma": "en"},
    "LINK_GUIA_RAP_ING": {"tipo_documento": "GUIA_RAPIDA", "idioma": "en"},
    "LINK_MAN_ING": {"tipo_documento": "MANUAL", "idioma": "en"},
    "LINK_OTRA_INFO_ING": {"tipo_documento": "OTRO", "idioma": "en"},
    "LINK_PROD": {"tipo_documento": "PAGINA_PRODUCTO", "idioma": ""},
    "LINK_PROD2": {"tipo_documento": "PAGINA_PRODUCTO_2", "idioma": ""},
    "LINK_PROX": {"tipo_documento": "PROXIMO", "idioma": ""},
}


CERTIFICADOS_PRODUCTO_DEFINICION = {
    "CERTIFICADO_1": {"tipo_certificado": "GENERAL"},
    "CERTIFICADO_2": {"tipo_certificado": "GENERAL"},
    "CERTIFICADO_3": {"tipo_certificado": "GENERAL"},
    "CERTIFICADO_CALIBRACION": {"tipo_certificado": "CALIBRACION"},
    "COD_PROV_CALIBRACION": {"tipo_certificado": "CALIBRACION"},
}


CAMPANAS_PRODUCTO_DEFINICION = {
    "ID_CAMPANA_1": {
        "orden": 1,
    },
    "ID_CAMPANA_2": {
        "orden": 2,
    },
    "ID_CAMPANA_3": {
        "orden": 3,
    },
    "ID_CAMPANA_4": {
        "orden": 4,
    },
}


MEDIA_PRODUCTO_DEFINICION = {
    "FOTO_PROD": {
        "tipo_media": "FOTO",
        "orden": 1,
        "es_principal": "1",
    },
    "DIBUJO_2": {
        "tipo_media": "DIBUJO",
        "orden": 2,
        "es_principal": "0",
    },
    "DIBUJO_3": {
        "tipo_media": "DIBUJO",
        "orden": 3,
        "es_principal": "0",
    },
    "DIBUJO_4": {
        "tipo_media": "DIBUJO",
        "orden": 4,
        "es_principal": "0",
    },
}


KEYWORDS_PRODUCTO_DEFINICION = {
    "PALABRAS_CLAVE": {
        "tipo_keyword": "GENERAL",
        "orden": 0,
    },
    "PALABRA_CLAVE_1": {
        "tipo_keyword": "GENERAL",
        "orden": 1,
    },
    "PALABRA_CLAVE_2": {
        "tipo_keyword": "GENERAL",
        "orden": 2,
    },
    "PALABRA_CLAVE_3": {
        "tipo_keyword": "GENERAL",
        "orden": 3,
    },
    "PALABRA_CLAVE_4": {
        "tipo_keyword": "GENERAL",
        "orden": 4,
    },
    "PALABRA_CLAVE_5": {
        "tipo_keyword": "GENERAL",
        "orden": 5,
    },
    "PALABRA_CLAVE_6": {
        "tipo_keyword": "GENERAL",
        "orden": 6,
    },
    "PALABRA_CLAVE_7": {
        "tipo_keyword": "GENERAL",
        "orden": 7,
    },
    "PALABRA_CLAVE_8": {
        "tipo_keyword": "GENERAL",
        "orden": 8,
    },
    "PALABRA_CLAVE_VAR_1": {
        "tipo_keyword": "VARIABLE",
        "orden": 1,
    },
    "PALABRA_CLAVE_VAR_2": {
        "tipo_keyword": "VARIABLE",
        "orden": 2,
    },
    "PALABRA_CLAVE_VAR_3": {
        "tipo_keyword": "VARIABLE",
        "orden": 3,
    },
    "BUSCA_APLICACION": {
        "tipo_keyword": "APLICACION",
        "orden": 1,
    },
}


EQUIVALENTES_PRODUCTO_DEFINICION = {
    "REF_ALTERNATIVA": {
        "tipo_equivalente": "REF_ALTERNATIVA",
        "fuente_equivalente": "ORIGEN",
        "marca_origen": "",
        "verificado_origen": "",
    },
    "EQUIVALENTE": {
        "tipo_equivalente": "EQUIVALENTE",
        "fuente_equivalente": "ORIGEN",
        "marca_origen": "MARCA_EQUIVALENTE",
        "verificado_origen": "EQUIVALENTE_VERIFICADO",
    },
    "EQUIVALENTE_2": {
        "tipo_equivalente": "EQUIVALENTE",
        "fuente_equivalente": "ORIGEN",
        "marca_origen": "MARCA_EQUIVALENTE_2",
        "verificado_origen": "EQUIVALENTE_VERIFICADO_2",
    },
    "EQUIVALENTE_IA": {
        "tipo_equivalente": "IA",
        "fuente_equivalente": "IA",
        "marca_origen": "",
        "verificado_origen": "",
    },
}


EXTENSIONES_DOCUMENTALES = (
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".mp4",
    ".mov",
    ".avi",
    ".zip",
    ".rar",
)


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
    df["CAMPO_DESTINO_NORM"] = df["CAMPO_DESTINO"].map(normalizar_nombre_materialidad)
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


def limpiar_valor_por_tabla_campo(tabla_destino: str, campo_destino: str, valor):
    """
    Limpieza conservadora por tabla/campo.

    Caso PRODUCTO_INVENTARIO:
    - cantidad solo debe conservar números positivos.
    - textos como '3 DIAS', 'AGOTADO', 'CONSULTAR' o 'DESCONTINUADO'
      no son cantidad física y se dejan vacíos.
    """
    tabla_norm = limpiar_nombre_archivo(tabla_destino)
    campo_norm = normalizar_nombre_materialidad(campo_destino)

    if tabla_norm == "producto_inventario" and campo_norm == "cantidad":
        if valor_es_numero_positivo(valor):
            return valor
        return ""

    return valor


def valor_es_material(valor) -> bool:
    """
    Indica si un valor aporta información real.
    Se usa para no generar filas solo por ceros, NO, false, NULL o vacíos.
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


def detectar_columna_codigo(df_origen: pd.DataFrame) -> str | None:
    """
    Busca la columna de CODIGO real de ViaIndustrial.

    Importante:
    CODIGO no se reemplaza con ITEM ni REFERENCIA.
    CODIGO representa el código público/comercial real del producto cuando existe.
    """
    candidatos = ["CODIGO", "CÓDIGO"]

    cols_norm = {
        normalizar_nombre_columna(c): c for c in df_origen.columns
    }

    for candidato in candidatos:
        key = normalizar_nombre_columna(candidato)
        if key in cols_norm:
            return cols_norm[key]

    return None


def construir_codigo_origen_real(
    df_origen: pd.DataFrame,
    columna_codigo: str | None,
) -> pd.Series:
    """
    Construye _codigo_origen usando únicamente CODIGO real.

    No usa ITEM ni REFERENCIA como reemplazo, porque eso mezclaría conceptos:
    - CODIGO = código público/comercial de ViaIndustrial.
    - ITEM = identificador interno/ERP.
    - REFERENCIA = referencia comercial o técnica.
    """
    resultado = pd.Series([""] * len(df_origen), index=df_origen.index, dtype=str)

    if not columna_codigo:
        return resultado

    serie = df_origen[columna_codigo].fillna("").astype(str).str.strip()
    mask_material = serie.map(valor_es_material)

    resultado.loc[mask_material] = serie.loc[mask_material]

    return resultado


def construir_producto_key_origen(df_origen: pd.DataFrame) -> pd.Series:
    """
    Construye una llave técnica de trazabilidad entre tablas derivadas.

    No reemplaza el código real de ViaIndustrial.

    Prioridad:
    1. CODIGO, si existe y es material.
    2. ITEM, si CODIGO no existe o no es material.
    3. REFERENCIA, si ITEM tampoco existe.
    4. ROW_n como último recurso.

    Esta llave sirve para relacionar CSV derivados del piloto.
    No debe presentarse como código oficial del producto.
    """
    candidatos = ["CODIGO", "CÓDIGO", "ITEM", "REFERENCIA"]

    columnas_origen_norm = {
        normalizar_nombre_columna(c): c for c in df_origen.columns
    }

    resultado = pd.Series([""] * len(df_origen), index=df_origen.index, dtype=str)

    for candidato in candidatos:
        candidato_norm = normalizar_nombre_columna(candidato)

        if candidato_norm not in columnas_origen_norm:
            continue

        col_real = columnas_origen_norm[candidato_norm]
        serie = df_origen[col_real].fillna("").astype(str).str.strip()

        mask_resultado_vacio = resultado.map(lambda valor: not valor_es_material(valor))
        mask_serie_material = serie.map(valor_es_material)

        mask_usar = mask_resultado_vacio & mask_serie_material

        resultado.loc[mask_usar] = serie.loc[mask_usar]

    # Último recurso: número de fila de origen.
    mask_sin_id = resultado.map(lambda valor: not valor_es_material(valor))
    resultado.loc[mask_sin_id] = (
        pd.Series(range(1, len(df_origen) + 1), index=df_origen.index)
        .astype(str)
        .map(lambda n: f"ROW_{n}")
    )

    return resultado


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


def asignar_campo_destino(
    registros_tabla: pd.DataFrame,
    campo_destino: str,
    serie_nueva: pd.Series,
) -> None:
    """
    Asigna valores a un campo destino sin perder información material.

    Si el campo no existe, lo crea.
    Si el campo ya existe, solo reemplaza valores vacíos/no materiales
    con valores nuevos que sí sean materiales.

    Esto evita que una columna origen posterior vacía, 0, NO o NULL
    sobrescriba un dato real ya cargado desde otra columna origen.
    """
    if campo_destino not in registros_tabla.columns:
        registros_tabla[campo_destino] = serie_nueva
        return

    mask_actual_no_material = registros_tabla[campo_destino].map(
        lambda valor: not valor_es_material(valor)
    )
    mask_nuevo_material = serie_nueva.map(valor_es_material)

    mask_reemplazar = mask_actual_no_material & mask_nuevo_material

    registros_tabla.loc[mask_reemplazar, campo_destino] = serie_nueva[mask_reemplazar]


def generar_producto_precio_vertical(
    df_origen: pd.DataFrame,
    grupo: pd.DataFrame,
    columnas_origen_norm: dict[str, str],
    producto_key_origen: pd.Series,
    codigo_origen_real: pd.Series,
    tabla_destino: str,
    errores: list[dict],
) -> tuple[pd.DataFrame, dict]:
    """
    Genera PRODUCTO_PRECIO en formato vertical.

    Razón técnica:
    en el mapeo hay varias columnas origen que caen en el mismo CAMPO_DESTINO='valor'
    (COSTO, PRECIO_VENTA, COSTO_DOLAR, PV_ANTERIOR, etc.). Si se asignan como columnas,
    cada una sobrescribe a la anterior.

    La forma correcta y trazable es generar una fila por producto y por fuente de precio.
    """
    registros = []
    columnas_procesadas = 0
    columnas_no_encontradas = 0
    campos_destino_vacios = 0

    reglas_valor = grupo[
        grupo["CAMPO_DESTINO_NORM"].isin({"valor", "precio", "monto"})
    ].copy()

    for _, regla in reglas_valor.iterrows():
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
            errores.append({
                "tabla_destino": tabla_destino,
                "columna_origen": col_origen,
                "campo_destino": campo_destino,
                "error": "COLUMNA_ORIGEN_NO_EXISTE",
                "detalle": "La columna del mapeo no existe en el archivo origen.",
            })
            continue

        col_real = columnas_origen_norm[col_origen_norm]
        serie = df_origen[col_real].map(
            lambda v: aplicar_transformacion(v, transformacion)
        )
        columnas_procesadas += 1

        mask_material = serie.map(valor_es_numero_positivo)

        for idx in serie[mask_material].index:
            registros.append({
                "_origen_row": int(idx) + 1,
                "_producto_key_origen": producto_key_origen.loc[idx],
                "_codigo_origen": codigo_origen_real.loc[idx],
                "valor": serie.loc[idx],
                "fuente": col_origen,
                "moneda": "",
            })

    columnas = [
        "_origen_row",
        "_producto_key_origen",
        "_codigo_origen",
        "valor",
        "fuente",
        "moneda",
    ]

    registros_tabla = pd.DataFrame(registros, columns=columnas)

    estadisticas = {
        "columnas_procesadas": columnas_procesadas,
        "columnas_no_encontradas": columnas_no_encontradas,
        "campos_destino_vacios": campos_destino_vacios,
        "modo_generacion": "VERTICAL_POR_FUENTE_PRECIO",
    }

    return registros_tabla, estadisticas


def detectar_tipo_parametro_origen(columna_origen: str) -> str:
    """
    Clasifica la columna origen sin inventar el parámetro real.

    Esto NO define el nombre oficial del parámetro.
    Solo conserva el tipo técnico de origen para trazabilidad.
    """
    col = normalizar_nombre_columna(columna_origen)

    if col.startswith("CAR_IND_"):
        return "INDUSTRIAL"

    if col.startswith("CAR_COM_"):
        return "COMERCIAL"

    if col == "DIMENSION":
        return "DIMENSION"

    return "ORIGEN_DESCONOCIDO"


def generar_producto_parametro_vertical(
    df_origen: pd.DataFrame,
    grupo: pd.DataFrame,
    columnas_origen_norm: dict[str, str],
    producto_key_origen: pd.Series,
    codigo_origen_real: pd.Series,
    tabla_destino: str,
    errores: list[dict],
) -> tuple[pd.DataFrame, dict]:
    """
    Genera PRODUCTO_PARAMETRO en formato vertical.

    Decisión conservadora:
    - Se conserva cada valor material de CAR_IND_*, CAR_COM_* y DIMENSION.
    - Se guarda la columna origen como parametro_origen.
    - No se inventa parametro_id.
    - parametro_id (FK) queda vacío hasta tener fuente oficial.
    """
    registros = []
    columnas_procesadas = 0
    columnas_no_encontradas = 0
    campos_destino_vacios = 0

    reglas_valor = grupo[
        grupo["CAMPO_DESTINO_NORM"].isin({"valor_texto", "valor"})
    ].copy()

    for _, regla in reglas_valor.iterrows():
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
            errores.append({
                "tabla_destino": tabla_destino,
                "columna_origen": col_origen,
                "campo_destino": campo_destino,
                "error": "COLUMNA_ORIGEN_NO_EXISTE",
                "detalle": "La columna del mapeo no existe en el archivo origen.",
            })
            continue

        col_real = columnas_origen_norm[col_origen_norm]
        serie = df_origen[col_real].map(
            lambda v: aplicar_transformacion(v, transformacion)
        )

        columnas_procesadas += 1
        mask_material = serie.map(valor_es_material)

        for idx in serie[mask_material].index:
            registros.append({
                "_origen_row": int(idx) + 1,
                "_producto_key_origen": producto_key_origen.loc[idx],
                "_codigo_origen": codigo_origen_real.loc[idx],
                "parametro_origen": col_origen,
                "tipo_parametro_origen": detectar_tipo_parametro_origen(col_origen),
                "valor_texto": serie.loc[idx],
                "parametro_id (FK)": "",
                "estado_parametro": "PENDIENTE_PARAMETRO_ID",
            })

    columnas = [
        "_origen_row",
        "_producto_key_origen",
        "_codigo_origen",
        "parametro_origen",
        "tipo_parametro_origen",
        "valor_texto",
        "parametro_id (FK)",
        "estado_parametro",
    ]

    registros_tabla = pd.DataFrame(registros, columns=columnas)

    estadisticas = {
        "columnas_procesadas": columnas_procesadas,
        "columnas_no_encontradas": columnas_no_encontradas,
        "campos_destino_vacios": campos_destino_vacios,
        "modo_generacion": "VERTICAL_POR_PARAMETRO_ORIGEN",
    }

    return registros_tabla, estadisticas


def obtener_definicion_documento(columna_origen: str) -> dict:
    """
    Devuelve tipo_documento e idioma únicamente para columnas documentales revisadas.
    No deduce tipos por intuición desde el texto del valor.
    """
    col = normalizar_nombre_columna(columna_origen)
    return DOCUMENTOS_PRODUCTO_DEFINICION.get(
        col,
        {"tipo_documento": "", "idioma": ""},
    )


def valor_documento_es_url_o_ruta(valor) -> bool:
    """
    Detecta si el valor parece URL o ruta documental existente.

    Regla conservadora:
    - No transforma referencias textuales en URL.
    - Solo marca como URL/ruta si el propio valor trae protocolo, www, separadores
      de ruta o extensión documental reconocible.
    """
    if not valor_es_material(valor):
        return False

    texto = str(valor).strip()
    texto_lower = texto.lower()

    if re.match(r"^[a-z][a-z0-9+.-]*://", texto_lower):
        return True

    if texto_lower.startswith("www."):
        return True

    if "/" in texto or "\\" in texto:
        return True

    return texto_lower.endswith(EXTENSIONES_DOCUMENTALES)


def estado_documento(valor, tipo_documento: str) -> str:
    """
    Estado trazable del valor documental sin inventar información.
    """
    if not tipo_documento:
        if valor_documento_es_url_o_ruta(valor):
            return "URL_DETECTADA_TIPO_PENDIENTE"
        return "REFERENCIA_DOCUMENTO_LEGADA_TIPO_PENDIENTE"

    if valor_documento_es_url_o_ruta(valor):
        return "URL_DETECTADA"

    return "REFERENCIA_DOCUMENTO_LEGADA"


def generar_producto_documento_vertical(
    df_origen: pd.DataFrame,
    grupo: pd.DataFrame,
    columnas_origen_norm: dict[str, str],
    producto_key_origen: pd.Series,
    codigo_origen_real: pd.Series,
    tabla_destino: str,
    errores: list[dict],
) -> tuple[pd.DataFrame, dict]:
    """
    Genera PRODUCTO_DOCUMENTO en formato vertical.

    Decisión conservadora v1.7.0:
    - Se conserva una fila por producto y por columna documental origen.
    - documento_origen conserva la columna fuente real.
    - tipo_documento e idioma salen del mapeo revisado de LINK_*.
    - No se inventan URLs: si el valor es referencia textual, queda en referencia_documento.
    """
    registros = []
    columnas_procesadas = 0
    columnas_no_encontradas = 0
    campos_destino_vacios = 0
    columnas_ya_procesadas = set()

    reglas_documento = grupo.copy()

    for _, regla in reglas_documento.iterrows():
        col_origen = str(regla["COLUMNA_ORIGEN"]).strip()
        col_origen_norm = normalizar_nombre_columna(col_origen)
        campo_destino = str(regla["CAMPO_DESTINO"]).strip()
        transformacion = str(regla["TRANSFORMACION"]).strip()

        if col_origen_norm in columnas_ya_procesadas:
            continue
        columnas_ya_procesadas.add(col_origen_norm)

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
            errores.append({
                "tabla_destino": tabla_destino,
                "columna_origen": col_origen,
                "campo_destino": campo_destino,
                "error": "COLUMNA_ORIGEN_NO_EXISTE",
                "detalle": "La columna del mapeo no existe en el archivo origen.",
            })
            continue

        col_real = columnas_origen_norm[col_origen_norm]
        definicion = obtener_definicion_documento(col_origen)
        tipo_documento = definicion["tipo_documento"]
        idioma = definicion["idioma"]

        serie = df_origen[col_real].map(
            lambda v: aplicar_transformacion(v, transformacion)
        )

        columnas_procesadas += 1
        mask_material = serie.map(valor_es_material)

        for idx in serie[mask_material].index:
            valor = str(serie.loc[idx]).strip()
            es_url = valor_documento_es_url_o_ruta(valor)

            registros.append({
                "_origen_row": int(idx) + 1,
                "_producto_key_origen": producto_key_origen.loc[idx],
                "_codigo_origen": codigo_origen_real.loc[idx],
                "documento_origen": col_origen,
                "tipo_documento": tipo_documento,
                "idioma": idioma,
                "valor_documento": valor,
                "url": valor if es_url else "",
                "referencia_documento": "" if es_url else valor,
                "es_url": "SI" if es_url else "NO",
                "estado_documento": estado_documento(valor, tipo_documento),
            })

    columnas = [
        "_origen_row",
        "_producto_key_origen",
        "_codigo_origen",
        "documento_origen",
        "tipo_documento",
        "idioma",
        "valor_documento",
        "url",
        "referencia_documento",
        "es_url",
        "estado_documento",
    ]

    registros_tabla = pd.DataFrame(registros, columns=columnas)

    estadisticas = {
        "columnas_procesadas": columnas_procesadas,
        "columnas_no_encontradas": columnas_no_encontradas,
        "campos_destino_vacios": campos_destino_vacios,
        "modo_generacion": "VERTICAL_POR_DOCUMENTO_ORIGEN",
    }

    return registros_tabla, estadisticas



def obtener_definicion_certificado(columna_origen: str) -> dict:
    """
    Devuelve tipo_certificado ?nicamente para columnas de certificado revisadas.
    No deduce certificaciones por intuici?n desde el texto.
    """
    col = normalizar_nombre_columna(columna_origen)
    return CERTIFICADOS_PRODUCTO_DEFINICION.get(
        col,
        {"tipo_certificado": ""},
    )


def estado_certificado(valor_certificado, cod_proveedor: str, tipo_certificado: str) -> str:
    """
    Estado trazable del certificado sin inventar informaci?n.
    """
    tiene_valor = valor_es_material(valor_certificado)
    tiene_codigo = valor_es_material(cod_proveedor)

    if tipo_certificado == "CALIBRACION":
        if tiene_valor and tiene_codigo:
            return "CERTIFICADO_CALIBRACION_CON_COD_PROVEEDOR"
        if tiene_valor:
            return "CERTIFICADO_CALIBRACION_DETECTADO"
        if tiene_codigo:
            return "COD_PROVEEDOR_CALIBRACION_DETECTADO"
        return "CALIBRACION_SIN_DATO_MATERIAL"

    if valor_documento_es_url_o_ruta(valor_certificado):
        return "RUTA_CERTIFICADO_DETECTADA"

    return "REFERENCIA_CERTIFICADO_LEGADA"


def generar_producto_certificado_vertical(
    df_origen: pd.DataFrame,
    grupo: pd.DataFrame,
    columnas_origen_norm: dict[str, str],
    producto_key_origen: pd.Series,
    codigo_origen_real: pd.Series,
    tabla_destino: str,
    errores: list[dict],
) -> tuple[pd.DataFrame, dict]:
    """
    Genera PRODUCTO_CERTIFICADO en formato vertical.

    Decisi?n conservadora v1.8.0:
    - CERTIFICADO_1, CERTIFICADO_2 y CERTIFICADO_3 se conservan como filas GENERAL.
    - CERTIFICADO_CALIBRACION y COD_PROV_CALIBRACION se conservan como una fila CALIBRACION por producto cuando hay dato material.
    - No se inventan certificados, rutas ni c?digos proveedor.
    """
    registros = []
    columnas_procesadas = 0
    columnas_no_encontradas = 0
    campos_destino_vacios = 0

    columnas_requeridas = {
        normalizar_nombre_columna(str(r["COLUMNA_ORIGEN"]).strip()): str(r["COLUMNA_ORIGEN"]).strip()
        for _, r in grupo.iterrows()
    }

    # Certificados generales: una fila por producto y por columna CERTIFICADO_1/2/3.
    for col_origen in ["CERTIFICADO_1", "CERTIFICADO_2", "CERTIFICADO_3"]:
        col_origen_norm = normalizar_nombre_columna(col_origen)

        if col_origen_norm not in columnas_requeridas:
            continue

        if col_origen_norm not in columnas_origen_norm:
            columnas_no_encontradas += 1
            errores.append({
                "tabla_destino": tabla_destino,
                "columna_origen": col_origen,
                "campo_destino": "certificado",
                "error": "COLUMNA_ORIGEN_NO_EXISTE",
                "detalle": "La columna del mapeo no existe en el archivo origen.",
            })
            continue

        col_real = columnas_origen_norm[col_origen_norm]
        serie = df_origen[col_real].map(lambda v: aplicar_transformacion(v, ""))
        columnas_procesadas += 1

        mask_material = serie.map(valor_es_material)

        for idx in serie[mask_material].index:
            valor = str(serie.loc[idx]).strip()
            es_ruta = valor_documento_es_url_o_ruta(valor)

            registros.append({
                "_origen_row": int(idx) + 1,
                "_producto_key_origen": producto_key_origen.loc[idx],
                "_codigo_origen": codigo_origen_real.loc[idx],
                "certificado_origen": col_origen,
                "tipo_certificado": "GENERAL",
                "valor_certificado": valor,
                "url_o_ruta": valor if es_ruta else "",
                "referencia_certificado": "" if es_ruta else valor,
                "cod_proveedor": "",
                "es_url_o_ruta": "SI" if es_ruta else "NO",
                "estado_certificado": estado_certificado(valor, "", "GENERAL"),
            })

    # Certificado de calibraci?n: una fila por producto si hay certificado o c?digo proveedor.
    col_cert_cal_norm = normalizar_nombre_columna("CERTIFICADO_CALIBRACION")
    col_cod_cal_norm = normalizar_nombre_columna("COD_PROV_CALIBRACION")

    serie_cert_cal = pd.Series([""] * len(df_origen), index=df_origen.index, dtype=str)
    serie_cod_cal = pd.Series([""] * len(df_origen), index=df_origen.index, dtype=str)

    if col_cert_cal_norm in columnas_requeridas:
        if col_cert_cal_norm in columnas_origen_norm:
            serie_cert_cal = df_origen[columnas_origen_norm[col_cert_cal_norm]].map(
                lambda v: aplicar_transformacion(v, "")
            )
            columnas_procesadas += 1
        else:
            columnas_no_encontradas += 1
            errores.append({
                "tabla_destino": tabla_destino,
                "columna_origen": "CERTIFICADO_CALIBRACION",
                "campo_destino": "certificado / cod_proveedor",
                "error": "COLUMNA_ORIGEN_NO_EXISTE",
                "detalle": "La columna del mapeo no existe en el archivo origen.",
            })

    if col_cod_cal_norm in columnas_requeridas:
        if col_cod_cal_norm in columnas_origen_norm:
            serie_cod_cal = df_origen[columnas_origen_norm[col_cod_cal_norm]].map(
                lambda v: aplicar_transformacion(v, "")
            )
            columnas_procesadas += 1
        else:
            columnas_no_encontradas += 1
            errores.append({
                "tabla_destino": tabla_destino,
                "columna_origen": "COD_PROV_CALIBRACION",
                "campo_destino": "certificado / cod_proveedor",
                "error": "COLUMNA_ORIGEN_NO_EXISTE",
                "detalle": "La columna del mapeo no existe en el archivo origen.",
            })

    mask_calibracion = serie_cert_cal.map(valor_es_material) | serie_cod_cal.map(valor_es_material)

    for idx in serie_cert_cal[mask_calibracion].index:
        valor = str(serie_cert_cal.loc[idx]).strip()
        cod_proveedor = str(serie_cod_cal.loc[idx]).strip()
        es_ruta = valor_documento_es_url_o_ruta(valor)

        registros.append({
            "_origen_row": int(idx) + 1,
            "_producto_key_origen": producto_key_origen.loc[idx],
            "_codigo_origen": codigo_origen_real.loc[idx],
            "certificado_origen": "CERTIFICADO_CALIBRACION",
            "tipo_certificado": "CALIBRACION",
            "valor_certificado": valor,
            "url_o_ruta": valor if es_ruta else "",
            "referencia_certificado": "" if es_ruta else valor,
            "cod_proveedor": cod_proveedor if valor_es_material(cod_proveedor) else "",
            "es_url_o_ruta": "SI" if es_ruta else "NO",
            "estado_certificado": estado_certificado(valor, cod_proveedor, "CALIBRACION"),
        })

    columnas = [
        "_origen_row",
        "_producto_key_origen",
        "_codigo_origen",
        "certificado_origen",
        "tipo_certificado",
        "valor_certificado",
        "url_o_ruta",
        "referencia_certificado",
        "cod_proveedor",
        "es_url_o_ruta",
        "estado_certificado",
    ]

    registros_tabla = pd.DataFrame(registros, columns=columnas)

    estadisticas = {
        "columnas_procesadas": columnas_procesadas,
        "columnas_no_encontradas": columnas_no_encontradas,
        "campos_destino_vacios": campos_destino_vacios,
        "modo_generacion": "VERTICAL_POR_CERTIFICADO_ORIGEN",
    }

    return registros_tabla, estadisticas






def estado_producto_campana(campana_id, en_promocion: str) -> str:
    """
    Estado trazable de producto-campana sin inventar datos maestros de campana.
    """
    tiene_campana = valor_es_material(campana_id)
    tiene_promocion = str(en_promocion or "").strip() == "1"

    if tiene_campana and tiene_promocion:
        return "CAMPANA_CON_PROMOCION"

    if tiene_campana:
        return "CAMPANA_DETECTADA"

    if tiene_promocion:
        return "PROMOCION_SIN_ID_CAMPANA"

    return "SIN_CAMPANA"


def generar_producto_campana_vertical(
    df_origen: pd.DataFrame,
    grupo: pd.DataFrame,
    columnas_origen_norm: dict[str, str],
    producto_key_origen: pd.Series,
    codigo_origen_real: pd.Series,
    tabla_destino: str,
    errores: list[dict],
) -> tuple[pd.DataFrame, dict]:
    """
    Genera PRODUCTO_CAMPANA en formato vertical y trazable.

    Decision conservadora v1.12.0:
    - ID_CAMPANA_1..ID_CAMPANA_4 generan filas con campana_id.
    - PROMOCION no inventa campana_id.
    - Si PROMOCION=1 y existe ID_CAMPANA, queda como atributo en_promocion=1.
    - Si PROMOCION=1 y no existe ID_CAMPANA, genera fila PROMOCION_SIN_ID_CAMPANA.
    - No se alimenta CAMPANA maestra desde ID_CAMPANA sin fuente oficial.
    - No se usan reglas por producto, codigo, fila o valor especifico.
    """
    registros = []
    columnas_procesadas = 0
    columnas_no_encontradas = 0
    campos_destino_vacios = 0

    columnas_mapeadas = {
        normalizar_nombre_columna(str(r["COLUMNA_ORIGEN"]).strip()): str(r["COLUMNA_ORIGEN"]).strip()
        for _, r in grupo.iterrows()
    }

    for col_norm, col_origen in columnas_mapeadas.items():
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

    promocion_col_norm = normalizar_nombre_columna("PROMOCION")
    promocion_real = columnas_origen_norm.get(promocion_col_norm)

    if promocion_real:
        promocion_serie = df_origen[promocion_real].map(lambda v: aplicar_transformacion(v, ""))
    else:
        promocion_serie = pd.Series([""] * len(df_origen), index=df_origen.index)

    ids_por_producto = {}

    for col_origen, definicion in CAMPANAS_PRODUCTO_DEFINICION.items():
        col_origen_norm = normalizar_nombre_columna(col_origen)

        if col_origen_norm not in columnas_mapeadas:
            continue

        if col_origen_norm not in columnas_origen_norm:
            continue

        col_real = columnas_origen_norm[col_origen_norm]
        serie = df_origen[col_real].map(lambda v: aplicar_transformacion(v, ""))
        mask_material = serie.map(valor_es_material)

        for idx in serie[mask_material].index:
            campana_id = str(serie.loc[idx]).strip()
            en_promocion = "1" if str(promocion_serie.loc[idx]).strip() == "1" else "0"
            ids_por_producto[idx] = ids_por_producto.get(idx, 0) + 1

            registros.append({
                "_origen_row": int(idx) + 1,
                "_producto_key_origen": producto_key_origen.loc[idx],
                "_codigo_origen": codigo_origen_real.loc[idx],
                "campana_origen": col_origen,
                "tipo_participacion": "CAMPANA",
                "orden": definicion["orden"],
                "campana_id": campana_id,
                "en_promocion": en_promocion,
                "estado_producto_campana": estado_producto_campana(
                    campana_id=campana_id,
                    en_promocion=en_promocion,
                ),
            })

    # Productos en promocion sin campana_id material.
    mask_promocion = promocion_serie.map(lambda v: str(v).strip() == "1")

    for idx in promocion_serie[mask_promocion].index:
        if ids_por_producto.get(idx, 0) > 0:
            continue

        registros.append({
            "_origen_row": int(idx) + 1,
            "_producto_key_origen": producto_key_origen.loc[idx],
            "_codigo_origen": codigo_origen_real.loc[idx],
            "campana_origen": "PROMOCION",
            "tipo_participacion": "PROMOCION",
            "orden": "",
            "campana_id": "",
            "en_promocion": "1",
            "estado_producto_campana": estado_producto_campana(
                campana_id="",
                en_promocion="1",
            ),
        })

    columnas = [
        "_origen_row",
        "_producto_key_origen",
        "_codigo_origen",
        "campana_origen",
        "tipo_participacion",
        "orden",
        "campana_id",
        "en_promocion",
        "estado_producto_campana",
    ]

    registros_tabla = pd.DataFrame(registros, columns=columnas)

    estadisticas = {
        "columnas_procesadas": columnas_procesadas,
        "columnas_no_encontradas": columnas_no_encontradas,
        "campos_destino_vacios": campos_destino_vacios,
        "modo_generacion": "VERTICAL_POR_CAMPANA_ORIGEN",
    }

    return registros_tabla, estadisticas


def estado_media(url, tipo_media: str, es_principal: str) -> str:
    """
    Estado trazable de media sin interpretar la imagen ni deducir tipo por extension.
    """
    if not valor_es_material(url):
        return "SIN_URL_MEDIA"

    if tipo_media == "FOTO" and es_principal == "1":
        return "FOTO_PRINCIPAL_DETECTADA"

    if tipo_media == "DIBUJO":
        return "DIBUJO_DETECTADO"

    return "MEDIA_DETECTADA"


def generar_producto_media_vertical(
    df_origen: pd.DataFrame,
    grupo: pd.DataFrame,
    columnas_origen_norm: dict[str, str],
    producto_key_origen: pd.Series,
    codigo_origen_real: pd.Series,
    tabla_destino: str,
    errores: list[dict],
) -> tuple[pd.DataFrame, dict]:
    """
    Genera PRODUCTO_MEDIA en formato vertical.

    Decision conservadora v1.11.0:
    - Cada columna media material genera su propia fila.
    - FOTO_PROD se conserva como FOTO principal.
    - DIBUJO_2, DIBUJO_3 y DIBUJO_4 se conservan como DIBUJO con orden.
    - No se crea fila sin url material.
    - No se deduce tipo por extension.
    - No se usan reglas por producto, codigo, fila o valor especifico.
    """
    registros = []
    columnas_procesadas = 0
    columnas_no_encontradas = 0
    campos_destino_vacios = 0

    columnas_mapeadas = {
        normalizar_nombre_columna(str(r["COLUMNA_ORIGEN"]).strip()): str(r["COLUMNA_ORIGEN"]).strip()
        for _, r in grupo.iterrows()
    }

    for col_norm, col_origen in columnas_mapeadas.items():
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

    for col_origen, definicion in MEDIA_PRODUCTO_DEFINICION.items():
        col_origen_norm = normalizar_nombre_columna(col_origen)

        if col_origen_norm not in columnas_mapeadas:
            continue

        if col_origen_norm not in columnas_origen_norm:
            continue

        col_real = columnas_origen_norm[col_origen_norm]
        serie = df_origen[col_real].map(lambda v: aplicar_transformacion(v, ""))
        mask_material = serie.map(valor_es_material)

        for idx in serie[mask_material].index:
            url = str(serie.loc[idx]).strip()
            tipo_media = definicion["tipo_media"]
            orden = definicion["orden"]
            es_principal = definicion["es_principal"]

            registros.append({
                "_origen_row": int(idx) + 1,
                "_producto_key_origen": producto_key_origen.loc[idx],
                "_codigo_origen": codigo_origen_real.loc[idx],
                "media_origen": col_origen,
                "tipo_media": tipo_media,
                "orden": orden,
                "es_principal": es_principal,
                "url": url,
                "estado_media": estado_media(
                    url=url,
                    tipo_media=tipo_media,
                    es_principal=es_principal,
                ),
            })

    columnas = [
        "_origen_row",
        "_producto_key_origen",
        "_codigo_origen",
        "media_origen",
        "tipo_media",
        "orden",
        "es_principal",
        "url",
        "estado_media",
    ]

    registros_tabla = pd.DataFrame(registros, columns=columnas)

    estadisticas = {
        "columnas_procesadas": columnas_procesadas,
        "columnas_no_encontradas": columnas_no_encontradas,
        "campos_destino_vacios": campos_destino_vacios,
        "modo_generacion": "VERTICAL_POR_MEDIA_ORIGEN",
    }

    return registros_tabla, estadisticas


def estado_keyword(keyword, tipo_keyword: str) -> str:
    """
    Estado trazable de keyword sin interpretar ni tokenizar el contenido.
    """
    if not valor_es_material(keyword):
        return "SIN_KEYWORD"

    if tipo_keyword == "VARIABLE":
        return "KEYWORD_VARIABLE_DETECTADA"

    if tipo_keyword == "APLICACION":
        return "KEYWORD_APLICACION_DETECTADA"

    return "KEYWORD_GENERAL_DETECTADA"


def generar_producto_keyword_vertical(
    df_origen: pd.DataFrame,
    grupo: pd.DataFrame,
    columnas_origen_norm: dict[str, str],
    producto_key_origen: pd.Series,
    codigo_origen_real: pd.Series,
    tabla_destino: str,
    errores: list[dict],
) -> tuple[pd.DataFrame, dict]:
    """
    Genera PRODUCTO_KEYWORD en formato vertical.

    Decision conservadora v1.10.0:
    - Cada columna keyword material genera su propia fila.
    - No se tokenizan frases.
    - No se separan palabras por espacios.
    - No se deducen sinonimos.
    - No se usan reglas por producto, codigo, fila o valor especifico.
    """
    registros = []
    columnas_procesadas = 0
    columnas_no_encontradas = 0
    campos_destino_vacios = 0

    columnas_mapeadas = {
        normalizar_nombre_columna(str(r["COLUMNA_ORIGEN"]).strip()): str(r["COLUMNA_ORIGEN"]).strip()
        for _, r in grupo.iterrows()
    }

    for col_norm, col_origen in columnas_mapeadas.items():
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

    for col_origen, definicion in KEYWORDS_PRODUCTO_DEFINICION.items():
        col_origen_norm = normalizar_nombre_columna(col_origen)

        if col_origen_norm not in columnas_mapeadas:
            continue

        if col_origen_norm not in columnas_origen_norm:
            continue

        col_real = columnas_origen_norm[col_origen_norm]
        serie = df_origen[col_real].map(lambda v: aplicar_transformacion(v, ""))
        mask_material = serie.map(valor_es_material)

        for idx in serie[mask_material].index:
            keyword = str(serie.loc[idx]).strip()
            tipo_keyword = definicion["tipo_keyword"]
            orden = definicion["orden"]

            registros.append({
                "_origen_row": int(idx) + 1,
                "_producto_key_origen": producto_key_origen.loc[idx],
                "_codigo_origen": codigo_origen_real.loc[idx],
                "keyword_origen": col_origen,
                "tipo_keyword": tipo_keyword,
                "orden": orden,
                "keyword": keyword,
                "estado_keyword": estado_keyword(
                    keyword=keyword,
                    tipo_keyword=tipo_keyword,
                ),
            })

    columnas = [
        "_origen_row",
        "_producto_key_origen",
        "_codigo_origen",
        "keyword_origen",
        "tipo_keyword",
        "orden",
        "keyword",
        "estado_keyword",
    ]

    registros_tabla = pd.DataFrame(registros, columns=columnas)

    estadisticas = {
        "columnas_procesadas": columnas_procesadas,
        "columnas_no_encontradas": columnas_no_encontradas,
        "campos_destino_vacios": campos_destino_vacios,
        "modo_generacion": "VERTICAL_POR_KEYWORD_ORIGEN",
    }

    return registros_tabla, estadisticas


def obtener_valor_columna_origen(
    df_origen: pd.DataFrame,
    columnas_origen_norm: dict[str, str],
    columna_origen: str,
    idx,
):
    """
    Obtiene un valor desde una columna origen de forma segura.
    No genera datos nuevos si la columna no existe.
    """
    if not columna_origen:
        return ""

    col_norm = normalizar_nombre_columna(columna_origen)
    if col_norm not in columnas_origen_norm:
        return ""

    col_real = columnas_origen_norm[col_norm]
    return df_origen.at[idx, col_real]


def estado_equivalente(
    referencia_equivalente,
    tipo_equivalente: str,
    verificado,
    link_proveedor,
) -> str:
    """
    Estado trazable de la equivalencia sin deducir relaciones por texto.
    """
    if not valor_es_material(referencia_equivalente):
        return "SIN_REFERENCIA_EQUIVALENTE"

    if tipo_equivalente == "IA":
        return "EQUIVALENTE_IA_DETECTADO"

    if tipo_equivalente == "REF_ALTERNATIVA":
        return "REFERENCIA_ALTERNATIVA_DETECTADA"

    verificado_texto = str(verificado or "").strip()
    if verificado_texto == "1":
        return "EQUIVALENTE_VERIFICADO"

    if verificado_texto == "0":
        return "EQUIVALENTE_NO_VERIFICADO"

    if valor_es_material(link_proveedor):
        return "EQUIVALENTE_CON_LINK_PROVEEDOR"

    return "EQUIVALENTE_DETECTADO"


def generar_producto_equivalente_vertical(
    df_origen: pd.DataFrame,
    grupo: pd.DataFrame,
    columnas_origen_norm: dict[str, str],
    producto_key_origen: pd.Series,
    codigo_origen_real: pd.Series,
    tabla_destino: str,
    errores: list[dict],
) -> tuple[pd.DataFrame, dict]:
    """
    Genera PRODUCTO_EQUIVALENTE en formato vertical.

    Decision conservadora v1.9.0:
    - Cada columna de equivalencia material genera su propia fila.
    - No se genera fila solo por link_proveedor, marca o verificado.
    - No se deducen equivalencias por texto.
    - No se usan reglas por producto, codigo, fila o valor especifico.
    """
    registros = []
    columnas_procesadas = 0
    columnas_no_encontradas = 0
    campos_destino_vacios = 0

    columnas_mapeadas = {
        normalizar_nombre_columna(str(r["COLUMNA_ORIGEN"]).strip()): str(r["COLUMNA_ORIGEN"]).strip()
        for _, r in grupo.iterrows()
    }

    # Contar columnas mapeadas encontradas para el reporte.
    for col_norm, col_origen in columnas_mapeadas.items():
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

    link_col = "LINK_PROVEEDOR_EQUIVALENTE"

    for col_origen, definicion in EQUIVALENTES_PRODUCTO_DEFINICION.items():
        col_origen_norm = normalizar_nombre_columna(col_origen)

        if col_origen_norm not in columnas_mapeadas:
            continue

        if col_origen_norm not in columnas_origen_norm:
            continue

        col_real = columnas_origen_norm[col_origen_norm]
        serie = df_origen[col_real].map(lambda v: aplicar_transformacion(v, ""))

        mask_material = serie.map(valor_es_material)

        for idx in serie[mask_material].index:
            referencia = str(serie.loc[idx]).strip()

            marca = obtener_valor_columna_origen(
                df_origen=df_origen,
                columnas_origen_norm=columnas_origen_norm,
                columna_origen=definicion.get("marca_origen", ""),
                idx=idx,
            )
            marca = str(marca or "").strip()
            if not valor_es_material(marca):
                marca = ""

            verificado = obtener_valor_columna_origen(
                df_origen=df_origen,
                columnas_origen_norm=columnas_origen_norm,
                columna_origen=definicion.get("verificado_origen", ""),
                idx=idx,
            )
            verificado = str(verificado or "").strip()
            if verificado not in {"0", "1"}:
                verificado = ""

            link_proveedor = obtener_valor_columna_origen(
                df_origen=df_origen,
                columnas_origen_norm=columnas_origen_norm,
                columna_origen=link_col,
                idx=idx,
            )
            link_proveedor = str(link_proveedor or "").strip()
            if not valor_es_material(link_proveedor):
                link_proveedor = ""

            tipo_equivalente = definicion["tipo_equivalente"]
            fuente_equivalente = definicion["fuente_equivalente"]

            registros.append({
                "_origen_row": int(idx) + 1,
                "_producto_key_origen": producto_key_origen.loc[idx],
                "_codigo_origen": codigo_origen_real.loc[idx],
                "equivalente_origen": col_origen,
                "tipo_equivalente": tipo_equivalente,
                "fuente_equivalente": fuente_equivalente,
                "referencia_equivalente": referencia,
                "marca_equivalente": marca,
                "verificado": verificado,
                "link_proveedor": link_proveedor,
                "estado_equivalente": estado_equivalente(
                    referencia_equivalente=referencia,
                    tipo_equivalente=tipo_equivalente,
                    verificado=verificado,
                    link_proveedor=link_proveedor,
                ),
            })

    columnas = [
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
    ]

    registros_tabla = pd.DataFrame(registros, columns=columnas)

    estadisticas = {
        "columnas_procesadas": columnas_procesadas,
        "columnas_no_encontradas": columnas_no_encontradas,
        "campos_destino_vacios": campos_destino_vacios,
        "modo_generacion": "VERTICAL_POR_EQUIVALENTE_ORIGEN",
    }

    return registros_tabla, estadisticas


def generar_tabla_horizontal(
    df_origen: pd.DataFrame,
    grupo: pd.DataFrame,
    columnas_origen_norm: dict[str, str],
    producto_key_origen: pd.Series,
    codigo_origen_real: pd.Series,
    tabla_destino: str,
    errores: list[dict],
) -> tuple[pd.DataFrame, dict]:
    """
    Genera una tabla destino en modo horizontal, conservando la lógica general v1.
    """
    columnas_procesadas = 0
    columnas_no_encontradas = 0
    campos_destino_vacios = 0

    registros_tabla = pd.DataFrame()
    registros_tabla["_origen_row"] = range(1, len(df_origen) + 1)
    registros_tabla["_producto_key_origen"] = producto_key_origen
    registros_tabla["_codigo_origen"] = codigo_origen_real

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
        serie_transformada = df_origen[col_real].map(
            lambda v: limpiar_valor_por_tabla_campo(
                tabla_destino=tabla_destino,
                campo_destino=campo_destino,
                valor=aplicar_transformacion(v, transformacion),
            )
        )

        asignar_campo_destino(
            registros_tabla=registros_tabla,
            campo_destino=campo_destino,
            serie_nueva=serie_transformada,
        )

        columnas_procesadas += 1

    # Eliminar filas sin materialidad real, conservando trazabilidad.
    # Antes cualquier valor no vacío generaba fila; eso incluía 0, 0.00, NO, NULL y flags.
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

    estadisticas = {
        "columnas_procesadas": columnas_procesadas,
        "columnas_no_encontradas": columnas_no_encontradas,
        "campos_destino_vacios": campos_destino_vacios,
        "modo_generacion": "HORIZONTAL",
    }

    return registros_tabla, estadisticas


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
    codigo_origen_real = construir_codigo_origen_real(
        df_origen=df_origen,
        columna_codigo=columna_codigo,
    )
    producto_key_origen = construir_producto_key_origen(df_origen)

    reportes_tablas = []
    errores = []
    tablas_generadas = []

    # No cargamos como tabla normalizada lo marcado explícitamente como eliminar.
    tablas_a_ignorar = {"ELIMINAR", "REVISAR/ELIMINAR", ""}

    for tabla_destino, grupo in df_mapeo.groupby("TABLA_DESTINO", dropna=False):
        tabla_destino = str(tabla_destino or "").strip()
        tabla_norm = limpiar_nombre_archivo(tabla_destino)

        if tabla_destino.upper() in tablas_a_ignorar:
            continue

        if tabla_norm == "producto_precio":
            registros_tabla, estadisticas = generar_producto_precio_vertical(
                df_origen=df_origen,
                grupo=grupo,
                columnas_origen_norm=columnas_origen_norm,
                producto_key_origen=producto_key_origen,
                codigo_origen_real=codigo_origen_real,
                tabla_destino=tabla_destino,
                errores=errores,
            )

        elif tabla_norm == "producto_parametro":
            registros_tabla, estadisticas = generar_producto_parametro_vertical(
                df_origen=df_origen,
                grupo=grupo,
                columnas_origen_norm=columnas_origen_norm,
                producto_key_origen=producto_key_origen,
                codigo_origen_real=codigo_origen_real,
                tabla_destino=tabla_destino,
                errores=errores,
            )

        elif tabla_norm == "producto_documento":
            registros_tabla, estadisticas = generar_producto_documento_vertical(
                df_origen=df_origen,
                grupo=grupo,
                columnas_origen_norm=columnas_origen_norm,
                producto_key_origen=producto_key_origen,
                codigo_origen_real=codigo_origen_real,
                tabla_destino=tabla_destino,
                errores=errores,
            )

        elif tabla_norm == "producto_certificado":
            registros_tabla, estadisticas = generar_producto_certificado_vertical(
                df_origen=df_origen,
                grupo=grupo,
                columnas_origen_norm=columnas_origen_norm,
                producto_key_origen=producto_key_origen,
                codigo_origen_real=codigo_origen_real,
                tabla_destino=tabla_destino,
                errores=errores,
            )

        elif tabla_norm == "producto_campana":
            registros_tabla, estadisticas = generar_producto_campana_vertical(
                df_origen=df_origen,
                grupo=grupo,
                columnas_origen_norm=columnas_origen_norm,
                producto_key_origen=producto_key_origen,
                codigo_origen_real=codigo_origen_real,
                tabla_destino=tabla_destino,
                errores=errores,
            )

        elif tabla_norm == "producto_media":
            registros_tabla, estadisticas = generar_producto_media_vertical(
                df_origen=df_origen,
                grupo=grupo,
                columnas_origen_norm=columnas_origen_norm,
                producto_key_origen=producto_key_origen,
                codigo_origen_real=codigo_origen_real,
                tabla_destino=tabla_destino,
                errores=errores,
            )

        elif tabla_norm == "producto_keyword":
            registros_tabla, estadisticas = generar_producto_keyword_vertical(
                df_origen=df_origen,
                grupo=grupo,
                columnas_origen_norm=columnas_origen_norm,
                producto_key_origen=producto_key_origen,
                codigo_origen_real=codigo_origen_real,
                tabla_destino=tabla_destino,
                errores=errores,
            )

        elif tabla_norm == "producto_equivalente":
            registros_tabla, estadisticas = generar_producto_equivalente_vertical(
                df_origen=df_origen,
                grupo=grupo,
                columnas_origen_norm=columnas_origen_norm,
                producto_key_origen=producto_key_origen,
                codigo_origen_real=codigo_origen_real,
                tabla_destino=tabla_destino,
                errores=errores,
            )

        else:
            registros_tabla, estadisticas = generar_tabla_horizontal(
                df_origen=df_origen,
                grupo=grupo,
                columnas_origen_norm=columnas_origen_norm,
                producto_key_origen=producto_key_origen,
                codigo_origen_real=codigo_origen_real,
                tabla_destino=tabla_destino,
                errores=errores,
            )

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
                "producto_parametro",
                "producto_documento",
            ],
            "producto_precio_verticalizado_por_fuente": True,
            "producto_parametro_verticalizado_por_origen": True,
            "producto_parametro_parametro_id_inventado": False,
            "producto_documento_verticalizado_por_origen": True,
            "producto_documento_url_inventada": False,
            "producto_documento_tipo_inventado": False,
            "producto_key_origen_generado": True,
            "codigo_origen_solo_codigo_real": True,
        },
        "nota": (
            "Este script genera tablas derivadas desde el archivo origen y el mapeo. "
            "No modifica el archivo original ni carga datos a Azure. "
            "Desde la versión 1.1.0 aplica reglas de materialidad para evitar filas "
            "generadas solo por ceros, NO o flags por defecto. "
            "Desde la versión 1.2.0 PRODUCTO_PRECIO se genera en formato vertical "
            "para evitar sobrescritura cuando varias columnas origen apuntan a valor. "
            "Desde la versión 1.3.0 se evita que columnas posteriores no materiales "
            "sobrescriban campos destino ya poblados con datos reales. "
            "Desde la versión 1.4.0 se separa el código real de ViaIndustrial "
            "(_codigo_origen) de la llave técnica de trazabilidad (_producto_key_origen). "
            "Desde la versión 1.6.0 PRODUCTO_PARAMETRO se genera en formato vertical "
            "por parametro_origen, sin inventar parametro_id. "
            "Desde la versión 1.7.0 PRODUCTO_DOCUMENTO se genera en formato vertical "
            "por documento_origen, separando URL/ruta real de referencia documental legada."
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
