from pathlib import Path
import argparse
import json
import re
from datetime import datetime, timezone

import pandas as pd


VERSION = "1.0.0"


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


def normalizar_nombre_columna(texto: str) -> str:
    texto = str(texto or "").strip().upper()
    texto = re.sub(r"\s+", " ", texto)
    return texto


def normalizar_nombre_materialidad(texto: str) -> str:
    texto = str(texto or "").strip().lower()
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    texto = re.sub(r"_+", "_", texto).strip("_")
    return texto


def leer_excel_o_csv(path: Path, sheet_name: str | None = None) -> pd.DataFrame:
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

        mejor = sorted(candidatos, key=lambda x: x["cols"], reverse=True)[0]
        print(
            f"CSV detectado: sep={repr(mejor['sep'])}, "
            f"encoding={mejor['encoding']}, columnas={mejor['cols']}"
        )
        return mejor["df"]

    raise ValueError(f"Formato no soportado: {path.suffix}")


def cargar_mapeo(path_mapeo: Path) -> pd.DataFrame:
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


def valor_es_material(valor) -> bool:
    if valor is None:
        return False

    if pd.isna(valor):
        return False

    texto = str(valor).strip()
    if not texto:
        return False

    return texto.lower() not in VALORES_NO_MATERIALES


def valor_es_numero_positivo(valor) -> bool:
    if valor is None:
        return False

    if pd.isna(valor):
        return False

    texto = str(valor).strip()
    if not texto:
        return False

    texto = texto.replace("$", "").replace(" ", "")

    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    else:
        texto = texto.replace(",", ".")

    try:
        return float(texto) > 0
    except ValueError:
        return False


def resumir_valores_materiales(serie: pd.Series, limite: int = 8) -> list[str]:
    valores = []
    vistos = set()

    for valor in serie.fillna("").astype(str):
        texto = valor.strip()
        if not texto:
            continue
        if texto.lower() in VALORES_NO_MATERIALES:
            continue
        if texto in vistos:
            continue
        vistos.add(texto)
        valores.append(texto[:120])
        if len(valores) >= limite:
            break

    return valores


def auditar_materialidad(
    df_origen: pd.DataFrame,
    df_mapeo: pd.DataFrame,
    tablas: list[str],
) -> tuple[list[dict], list[dict]]:
    columnas_origen_norm = {
        normalizar_nombre_columna(c): c for c in df_origen.columns
    }

    tablas_norm = {t.strip().upper() for t in tablas}
    filas_detalle = []
    filas_resumen = []

    for tabla_destino, grupo in df_mapeo.groupby("TABLA_DESTINO", dropna=False):
        tabla_destino = str(tabla_destino or "").strip()
        if tabla_destino.upper() not in tablas_norm:
            continue

        columnas_existentes = 0
        columnas_con_materialidad = 0
        columnas_con_numero_positivo = 0
        filas_con_alguna_materialidad = pd.Series(False, index=df_origen.index)
        filas_con_algun_numero_positivo = pd.Series(False, index=df_origen.index)

        for _, regla in grupo.iterrows():
            col_origen = str(regla["COLUMNA_ORIGEN"]).strip()
            col_origen_norm = normalizar_nombre_columna(col_origen)
            campo_destino = str(regla["CAMPO_DESTINO"]).strip()
            campo_destino_norm = str(regla["CAMPO_DESTINO_NORM"]).strip()

            if col_origen_norm not in columnas_origen_norm:
                filas_detalle.append({
                    "tabla_destino": tabla_destino,
                    "campo_destino": campo_destino,
                    "campo_destino_norm": campo_destino_norm,
                    "columna_origen": col_origen,
                    "columna_existe_en_origen": False,
                    "filas_total": int(len(df_origen)),
                    "filas_no_vacias": 0,
                    "filas_materiales": 0,
                    "filas_numero_positivo": 0,
                    "ejemplos_materiales": "[]",
                })
                continue

            columnas_existentes += 1
            col_real = columnas_origen_norm[col_origen_norm]
            serie = df_origen[col_real].fillna("")

            mask_no_vacio = serie.astype(str).str.strip() != ""
            mask_material = serie.map(valor_es_material)
            mask_numero_positivo = serie.map(valor_es_numero_positivo)

            filas_con_alguna_materialidad = filas_con_alguna_materialidad | mask_material
            filas_con_algun_numero_positivo = filas_con_algun_numero_positivo | mask_numero_positivo

            if int(mask_material.sum()) > 0:
                columnas_con_materialidad += 1

            if int(mask_numero_positivo.sum()) > 0:
                columnas_con_numero_positivo += 1

            filas_detalle.append({
                "tabla_destino": tabla_destino,
                "campo_destino": campo_destino,
                "campo_destino_norm": campo_destino_norm,
                "columna_origen": col_origen,
                "columna_existe_en_origen": True,
                "filas_total": int(len(df_origen)),
                "filas_no_vacias": int(mask_no_vacio.sum()),
                "filas_materiales": int(mask_material.sum()),
                "filas_numero_positivo": int(mask_numero_positivo.sum()),
                "ejemplos_materiales": json.dumps(
                    resumir_valores_materiales(serie),
                    ensure_ascii=False,
                ),
            })

        filas_resumen.append({
            "tabla_destino": tabla_destino,
            "columnas_mapeadas": int(len(grupo)),
            "columnas_existentes_en_origen": int(columnas_existentes),
            "columnas_con_materialidad": int(columnas_con_materialidad),
            "columnas_con_numero_positivo": int(columnas_con_numero_positivo),
            "filas_origen": int(len(df_origen)),
            "filas_con_alguna_materialidad": int(filas_con_alguna_materialidad.sum()),
            "filas_con_algun_numero_positivo": int(filas_con_algun_numero_positivo.sum()),
        })

    return filas_detalle, filas_resumen


def main():
    parser = argparse.ArgumentParser(
        description="Audita materialidad real por tabla destino antes de filtrar salidas normalizadas."
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Archivo origen con datos reales de productos. Puede ser .xlsx o .csv.",
    )
    parser.add_argument(
        "--mapping",
        default="01_fuentes/Normalizacion_Tabla_Productos.xlsx",
        help="Archivo Excel con hoja MAPEO_445_COLUMNAS.",
    )
    parser.add_argument(
        "--sheet",
        default=None,
        help="Hoja del archivo origen. Si se omite, usa la primera hoja.",
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        default=[
            "PRODUCTO_PRECIO",
            "PRODUCTO_PROVEEDOR",
            "PRODUCTO_INVENTARIO",
        ],
        help="Tablas destino a auditar.",
    )
    parser.add_argument(
        "--out-dir",
        default="05_reportes",
        help="Carpeta donde se escribirán los reportes.",
    )

    args = parser.parse_args()

    source_path = Path(args.source)
    mapping_path = Path(args.mapping)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Leyendo archivo origen...")
    df_origen = leer_excel_o_csv(source_path, args.sheet)
    df_origen = df_origen.fillna("")

    print("Leyendo mapeo...")
    df_mapeo = cargar_mapeo(mapping_path)

    print("Auditando materialidad...")
    detalle, resumen = auditar_materialidad(
        df_origen=df_origen,
        df_mapeo=df_mapeo,
        tablas=args.tables,
    )

    detalle_path = out_dir / "auditoria_materialidad_tablas_v1.csv"
    resumen_path = out_dir / "resumen_materialidad_tablas_v1.csv"
    json_path = out_dir / "reporte_materialidad_tablas_v1.json"

    pd.DataFrame(detalle).to_csv(
        detalle_path,
        index=False,
        sep=";",
        encoding="utf-8-sig",
    )

    pd.DataFrame(resumen).to_csv(
        resumen_path,
        index=False,
        sep=";",
        encoding="utf-8-sig",
    )

    reporte = {
        "script": "auditar_materialidad_tablas_v1.py",
        "version": VERSION,
        "fecha_ejecucion_utc": datetime.now(timezone.utc).isoformat(),
        "archivo_origen": str(source_path),
        "archivo_mapeo": str(mapping_path),
        "tablas_auditadas": args.tables,
        "filas_origen": int(len(df_origen)),
        "columnas_origen": int(len(df_origen.columns)),
        "detalle_csv": str(detalle_path),
        "resumen_csv": str(resumen_path),
        "controles": {
            "fuente_modificada": False,
            "salidas_normalizadas_modificadas": False,
            "carga_azure_realizada": False,
        },
        "nota": (
            "Este reporte no decide reglas finales. Solo mide si las columnas mapeadas "
            "tienen valores materiales antes de filtrar filas normalizadas."
        ),
    }

    json_path.write_text(
        json.dumps(reporte, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\nAuditoría terminada.")
    print(f"Detalle: {detalle_path}")
    print(f"Resumen: {resumen_path}")
    print(f"Reporte JSON: {json_path}")


if __name__ == "__main__":
    main()
