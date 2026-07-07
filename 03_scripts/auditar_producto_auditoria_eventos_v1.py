from pathlib import Path
import argparse
import json
import re
from datetime import datetime, timezone

import pandas as pd


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


def normalizar_nombre_columna(texto: str) -> str:
    texto = str(texto or "").strip().upper()
    texto = re.sub(r"\s+", " ", texto)
    return texto


def valor_es_material(valor) -> bool:
    if valor is None:
        return False

    if pd.isna(valor):
        return False

    texto = str(valor).strip()
    if not texto:
        return False

    return texto.lower() not in VALORES_NO_MATERIALES


def leer_csv(path: Path) -> pd.DataFrame:
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

    mejor = sorted(candidatos, key=lambda x: x["cols"], reverse=True)[0]
    print(
        f"CSV detectado: {path} | sep={repr(mejor['sep'])} | "
        f"encoding={mejor['encoding']} | columnas={mejor['cols']}"
    )
    return mejor["df"].fillna("")


def leer_excel_o_csv(path: Path, sheet_name: str | None = None) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {path}")

    suffix = path.suffix.lower()

    if suffix in [".xlsx", ".xlsm", ".xls"]:
        if sheet_name:
            return pd.read_excel(path, sheet_name=sheet_name, dtype=str).fillna("")
        return pd.read_excel(path, sheet_name=0, dtype=str).fillna("")

    if suffix == ".csv":
        return leer_csv(path)

    raise ValueError(f"Formato no soportado: {path.suffix}")


def construir_mapa_columnas(df: pd.DataFrame) -> dict[str, str]:
    return {normalizar_nombre_columna(c): c for c in df.columns}


def obtener_valor(row: pd.Series, columnas_norm: dict[str, str], columna: str) -> str:
    if not columna:
        return ""

    col_norm = normalizar_nombre_columna(columna)
    col_real = columnas_norm.get(col_norm)

    if not col_real:
        return ""

    valor = row.get(col_real, "")
    if not valor_es_material(valor):
        return ""

    return str(valor).strip()


def construir_producto_key(row: pd.Series, columnas_norm: dict[str, str], idx: int) -> str:
    for col in ["CODIGO", "CÓDIGO", "ITEM", "REFERENCIA"]:
        valor = obtener_valor(row, columnas_norm, col)
        if valor_es_material(valor):
            return valor

    return f"ROW_{idx + 1}"


def construir_codigo_origen(row: pd.Series, columnas_norm: dict[str, str]) -> str:
    for col in ["CODIGO", "CÓDIGO"]:
        valor = obtener_valor(row, columnas_norm, col)
        if valor_es_material(valor):
            return valor

    return ""


def auditar_cobertura_columnas(df_origen: pd.DataFrame) -> pd.DataFrame:
    columnas_norm = construir_mapa_columnas(df_origen)
    registros = []

    columnas_auditoria = []
    for definicion in EVENTOS_AUDITORIA:
        for campo in ["fecha", "usuario", "terminal", "observacion"]:
            columna = definicion[campo]
            if columna:
                columnas_auditoria.append(columna)

    columnas_auditoria = sorted(set(columnas_auditoria))

    for columna in columnas_auditoria:
        col_real = columnas_norm.get(normalizar_nombre_columna(columna))
        if not col_real:
            registros.append({
                "columna_origen": columna,
                "existe_en_origen": "NO",
                "valores_materiales": 0,
                "filas_origen": len(df_origen),
            })
            continue

        serie = df_origen[col_real]
        registros.append({
            "columna_origen": columna,
            "existe_en_origen": "SI",
            "valores_materiales": int(serie.map(valor_es_material).sum()),
            "filas_origen": len(df_origen),
        })

    return pd.DataFrame(registros)


def estado_evento_auditoria(
    fecha: str,
    usuario: str,
    terminal: str,
    observacion: str,
) -> str:
    tiene_fecha = valor_es_material(fecha)
    tiene_usuario = valor_es_material(usuario)
    tiene_terminal = valor_es_material(terminal)
    tiene_observacion = valor_es_material(observacion)

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


def construir_eventos_origen(df_origen: pd.DataFrame) -> pd.DataFrame:
    columnas_norm = construir_mapa_columnas(df_origen)
    registros = []

    for idx, row in df_origen.iterrows():
        producto_key = construir_producto_key(row, columnas_norm, idx)
        codigo_origen = construir_codigo_origen(row, columnas_norm)

        for definicion in EVENTOS_AUDITORIA:
            fecha = obtener_valor(row, columnas_norm, definicion["fecha"])
            usuario = obtener_valor(row, columnas_norm, definicion["usuario"])
            terminal = obtener_valor(row, columnas_norm, definicion["terminal"])
            observacion = obtener_valor(row, columnas_norm, definicion["observacion"])

            if not any([
                valor_es_material(fecha),
                valor_es_material(usuario),
                valor_es_material(terminal),
                valor_es_material(observacion),
            ]):
                continue

            registros.append({
                "_origen_row": int(idx) + 1,
                "_producto_key_origen": producto_key,
                "_codigo_origen": codigo_origen,
                "auditoria_origen": definicion["auditoria_origen"],
                "campo_auditado": definicion["campo_auditado"],
                "fecha_auditoria": fecha,
                "usuario_auditoria": usuario,
                "terminal_auditoria": terminal,
                "observacion_auditoria": observacion,
                "estado_producto_auditoria": estado_evento_auditoria(
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

    return pd.DataFrame(registros, columns=columnas)


def leer_salida_actual(path_salida_actual: Path | None) -> pd.DataFrame:
    if not path_salida_actual:
        return pd.DataFrame()

    if not path_salida_actual.exists():
        print(f"Advertencia: no existe salida actual: {path_salida_actual}")
        return pd.DataFrame()

    return leer_csv(path_salida_actual)


def comparar_con_salida_actual(eventos_origen: pd.DataFrame, salida_actual: pd.DataFrame) -> dict:
    resumen = {
        "filas_eventos_origen_esperados": int(len(eventos_origen)),
        "productos_eventos_origen": int(eventos_origen["_producto_key_origen"].nunique()) if not eventos_origen.empty else 0,
        "filas_salida_actual": int(len(salida_actual)),
        "productos_salida_actual": int(salida_actual["_producto_key_origen"].nunique()) if "_producto_key_origen" in salida_actual.columns else 0,
        "comparacion_detallada_posible": False,
        "motivo": "",
        "faltantes": None,
        "extras": None,
    }

    columnas_nuevas = {
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
    }

    if salida_actual.empty:
        resumen["motivo"] = "No se entrego salida actual o esta vacia."
        return resumen

    if not columnas_nuevas.issubset(set(salida_actual.columns)):
        resumen["motivo"] = (
            "La salida actual todavia tiene estructura heredada. "
            "No permite comparar por auditoria_origen/campo_auditado. "
            "Solo se compara cobertura general de filas."
        )
        return resumen

    claves = [
        "_origen_row",
        "_producto_key_origen",
        "auditoria_origen",
        "campo_auditado",
        "fecha_auditoria",
        "usuario_auditoria",
        "terminal_auditoria",
        "observacion_auditoria",
    ]

    origen_keys = set(map(tuple, eventos_origen[claves].fillna("").astype(str).values.tolist()))
    salida_keys = set(map(tuple, salida_actual[claves].fillna("").astype(str).values.tolist()))

    resumen["comparacion_detallada_posible"] = True
    resumen["motivo"] = "La salida tiene columnas v1.15.0 compatibles para comparacion por eventos."
    resumen["faltantes"] = int(len(origen_keys - salida_keys))
    resumen["extras"] = int(len(salida_keys - origen_keys))

    return resumen


def main():
    parser = argparse.ArgumentParser(
        description="Audita PRODUCTO_AUDITORIA por eventos antes de implementar v1.15.0"
    )

    parser.add_argument(
        "--source",
        required=True,
        help="Archivo origen de productos_hugo del piloto. Puede ser CSV o Excel.",
    )
    parser.add_argument(
        "--sheet",
        default=None,
        help="Hoja del Excel origen, si aplica.",
    )
    parser.add_argument(
        "--salida-actual",
        default="04_salidas_normalizadas/piloto_productos_hugo_con_nombre_top1000_v11/producto_auditoria.csv",
        help="CSV actual de producto_auditoria para comparar cobertura.",
    )
    parser.add_argument(
        "--out-dir",
        default="05_reportes",
        help="Carpeta de reportes.",
    )

    args = parser.parse_args()

    source_path = Path(args.source)
    salida_actual_path = Path(args.salida_actual) if args.salida_actual else None
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Leyendo origen...")
    df_origen = leer_excel_o_csv(source_path, args.sheet)

    print("Construyendo cobertura por columnas...")
    cobertura = auditar_cobertura_columnas(df_origen)

    print("Construyendo eventos esperados desde origen...")
    eventos_origen = construir_eventos_origen(df_origen)

    print("Leyendo salida actual...")
    salida_actual = leer_salida_actual(salida_actual_path)

    print("Comparando...")
    comparacion = comparar_con_salida_actual(eventos_origen, salida_actual)

    distribucion_por_evento = (
        eventos_origen["auditoria_origen"]
        .value_counts()
        .sort_index()
        .to_dict()
        if not eventos_origen.empty
        else {}
    )

    distribucion_por_estado = (
        eventos_origen["estado_producto_auditoria"]
        .value_counts()
        .sort_index()
        .to_dict()
        if not eventos_origen.empty
        else {}
    )

    reporte = {
        "script": "auditar_producto_auditoria_eventos_v1.py",
        "fecha_ejecucion_utc": datetime.now(timezone.utc).isoformat(),
        "archivo_origen": str(source_path),
        "salida_actual": str(salida_actual_path) if salida_actual_path else "",
        "filas_origen": int(len(df_origen)),
        "columnas_origen": int(len(df_origen.columns)),
        "total_valores_materiales_columnas_auditoria": int(cobertura["valores_materiales"].sum()),
        "eventos_origen_esperados": int(len(eventos_origen)),
        "eventos_por_auditoria_origen": distribucion_por_evento,
        "eventos_por_estado": distribucion_por_estado,
        "salida_actual": comparacion,
        "decision": "NO_IMPLEMENTAR_AUN" if not comparacion["comparacion_detallada_posible"] else "VALIDAR_RESULTADO_V115",
    }

    cobertura_path = out_dir / "producto_auditoria_cobertura_columnas.csv"
    eventos_path = out_dir / "producto_auditoria_eventos_origen_esperados.csv"
    muestra_path = out_dir / "producto_auditoria_muestra_eventos_origen.csv"
    reporte_path = out_dir / "producto_auditoria_comparacion_eventos.json"

    cobertura.to_csv(cobertura_path, index=False, sep=";", encoding="utf-8-sig")
    eventos_origen.to_csv(eventos_path, index=False, sep=";", encoding="utf-8-sig")
    eventos_origen.head(100).to_csv(muestra_path, index=False, sep=";", encoding="utf-8-sig")

    with reporte_path.open("w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)

    print()
    print("AUDITORIA PRODUCTO_AUDITORIA POR EVENTOS")
    print("=" * 80)
    print(f"FILAS ORIGEN: {len(df_origen)}")
    print(f"TOTAL VALORES MATERIALES COLUMNAS AUDITORIA: {reporte['total_valores_materiales_columnas_auditoria']}")
    print(f"EVENTOS ORIGEN ESPERADOS: {len(eventos_origen)}")
    print(f"FILAS SALIDA ACTUAL: {comparacion['filas_salida_actual']}")
    print(f"PRODUCTOS SALIDA ACTUAL: {comparacion['productos_salida_actual']}")
    print(f"COMPARACION DETALLADA POSIBLE: {comparacion['comparacion_detallada_posible']}")
    print(f"MOTIVO: {comparacion['motivo']}")
    print()
    print("Archivos generados:")
    print(f"- {cobertura_path}")
    print(f"- {eventos_path}")
    print(f"- {muestra_path}")
    print(f"- {reporte_path}")


if __name__ == "__main__":
    main()
