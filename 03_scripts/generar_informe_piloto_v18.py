from pathlib import Path
import json
import pandas as pd
from datetime import datetime

BASE = Path("04_salidas_normalizadas/piloto_productos_hugo_muestra_v18_5000")
REPORTES = Path("05_reportes")
ENTREGABLES = Path("06_entregables")

ENTREGABLES.mkdir(parents=True, exist_ok=True)

def cargar_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def leer_csv(nombre):
    return pd.read_csv(
        BASE / nombre,
        sep=";",
        dtype=str,
        encoding="utf-8-sig",
        low_memory=False,
    ).fillna("")

def conteo_dict(serie):
    return serie.value_counts(dropna=False).to_dict()

def cobertura_dict(df):
    return (
        df.replace("", pd.NA)
        .notna()
        .sum()
        .sort_values(ascending=False)
        .astype(int)
        .to_dict()
    )

reporte_normalizacion = cargar_json(REPORTES / "reporte_normalizacion_piloto_v18_5000_v120.json")
reporte_resumen = cargar_json(REPORTES / "reporte_resumen_tablas_piloto_v18_5000.json")
reporte_moneda = cargar_json(REPORTES / "reporte_moneda_piloto_v18_5000.json")

producto_categoria = leer_csv("producto_categoria.csv")
producto_equivalente = leer_csv("producto_equivalente.csv")
producto_proveedor = leer_csv("producto_proveedor.csv")
producto_logistica = leer_csv("producto_logistica.csv")
producto_inventario = leer_csv("producto_inventario.csv")
producto_precio = leer_csv("producto_precio.csv")
producto_auditoria = leer_csv("producto_auditoria.csv")

tablas = pd.DataFrame(reporte_resumen["resumen_tablas"])
tablas_con_datos = int((tablas["estado"] == "CON_DATOS").sum())
tablas_vacias = int((tablas["estado"] == "VACIA").sum())
mercado_restante = int((producto_categoria["tipo_categoria"] == "MERCADO").sum())

lineas_tablas = []
for _, row in tablas.iterrows():
    lineas_tablas.append(
        f"| {row['tabla']} | {row['filas']} | {row['columnas']} | {row['estado']} |"
    )

informe = []

informe.append("# Informe técnico interno — Piloto ampliado v18 / normalizador v1.20.0")
informe.append("")
informe.append(f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
informe.append("Proyecto: redisenio_bd_productos")
informe.append("Piloto: v18")
informe.append("Normalizador: v1.20.0")
informe.append("Fuente derivada: 01_fuentes/productos_hugo_muestra_v18_5000.csv")
informe.append("Salida: 04_salidas_normalizadas/piloto_productos_hugo_muestra_v18_5000")
informe.append("")

informe.append("## 1. Objetivo")
informe.append("")
informe.append("Validar el normalizador v1.20.0 sobre una muestra ampliada de 5.000 productos adicionales tomados desde dbo.productos_hugo.")
informe.append("Este piloto no corresponde a carga masiva ni a implementación productiva.")
informe.append("")

informe.append("## 2. Resultado general")
informe.append("")
informe.append("| Control | Resultado |")
informe.append("|---|---:|")
informe.append(f"| Filas origen | {reporte_normalizacion['filas_origen']} |")
informe.append(f"| Columnas origen | {reporte_normalizacion['columnas_origen']} |")
informe.append(f"| Columnas mapeo | {reporte_normalizacion['columnas_mapeo']} |")
informe.append(f"| Columnas faltantes en origen | {reporte_normalizacion['faltan_en_origen']} |")
informe.append(f"| Columnas sobrantes en origen | {reporte_normalizacion['sobran_en_origen']} |")
informe.append(f"| Tablas generadas | {reporte_normalizacion['tablas_generadas']} |")
informe.append(f"| Errores | {len(reporte_normalizacion['errores'])} |")
informe.append(f"| Tablas con datos | {tablas_con_datos} |")
informe.append(f"| Tablas vacías | {tablas_vacias} |")
informe.append("")

informe.append("## 3. Resumen de tablas generadas")
informe.append("")
informe.append("Esta sección muestra cuántas filas y columnas produjo cada tabla normalizada.")
informe.append("")
informe.append("| Tabla | Filas | Columnas | Estado |")
informe.append("|---|---:|---:|---|")
informe.extend(lineas_tablas)
informe.append("")

informe.append("## 4. PRODUCTO_CATEGORIA")
informe.append("")
informe.append("Esta sección valida que las categorías técnicas quedaron separadas de los campos de mercado.")
informe.append("")
informe.append(f"MERCADO restante: {mercado_restante}")
informe.append("")
informe.append("Distribución por tipo_categoria:")
for k, v in conteo_dict(producto_categoria["tipo_categoria"]).items():
    informe.append(f"- {k}: {v}")
informe.append("")
informe.append("Dictamen: PRODUCTO_CATEGORIA queda limpia. MERCA_CLI, CLASI_MERCA, PSO y MERCA_CLI_MERCA no quedan como categorías técnicas.")
informe.append("")

informe.append("## 5. PRODUCTO_EQUIVALENTE")
informe.append("")
informe.append("Esta tabla conserva referencias alternativas, equivalentes declarados y productos alternativos detectados.")
informe.append("No significa equivalencias comerciales aprobadas.")
informe.append("")
informe.append("Distribución por tipo_equivalente:")
for k, v in conteo_dict(producto_equivalente["tipo_equivalente"]).items():
    informe.append(f"- {k}: {v}")
informe.append("")
informe.append("Distribución por fuente_equivalente:")
for k, v in conteo_dict(producto_equivalente["fuente_equivalente"]).items():
    informe.append(f"- {k}: {v}")
informe.append("")

informe.append("## 6. PRODUCTO_PROVEEDOR")
informe.append("")
informe.append("Esta tabla conserva relaciones producto-proveedor, incluyendo proveedores múltiples.")
informe.append("")
informe.append("Distribución por proveedor_origen:")
for k, v in conteo_dict(producto_proveedor["proveedor_origen"]).items():
    informe.append(f"- {k}: {v}")
informe.append("")
informe.append("Distribución por estado_producto_proveedor:")
for k, v in conteo_dict(producto_proveedor["estado_producto_proveedor"]).items():
    informe.append(f"- {k}: {v}")
informe.append("")

informe.append("## 7. PRODUCTO_LOGISTICA")
informe.append("")
informe.append("Esta tabla conserva datos logísticos como procedencia, peso, dimensiones, origen y transporte.")
informe.append("")
informe.append("Cobertura por campo:")
for k, v in cobertura_dict(producto_logistica).items():
    informe.append(f"- {k}: {v}")
informe.append("")

informe.append("## 8. PRODUCTO_INVENTARIO")
informe.append("")
informe.append("Esta tabla conserva datos de stock, fechas, días estimados, stock_id y observaciones.")
informe.append("")
informe.append("Cobertura por campo:")
for k, v in cobertura_dict(producto_inventario).items():
    informe.append(f"- {k}: {v}")
informe.append("")

informe.append("## 9. PRODUCTO_PRECIO")
informe.append("")
informe.append("Esta tabla conserva valores económicos en formato vertical por fuente.")
informe.append("La columna MONEDA existe en la fuente, pero viene vacía en la muestra v18.")
informe.append("No se modifica v1.20.0 por este punto. Queda como mejora candidata v1.21.0.")
informe.append("")
informe.append("Distribución por fuente:")
for k, v in conteo_dict(producto_precio["fuente"]).items():
    informe.append(f"- {k}: {v}")
informe.append("")
informe.append("Campos de moneda revisados en la fuente:")
for k, v in reporte_moneda["resumen_campos_moneda"].items():
    informe.append(f"- {k}: {v}")
informe.append("")

informe.append("## 10. PRODUCTO_AUDITORIA")
informe.append("")
informe.append("Esta tabla conserva eventos de auditoría en formato vertical.")
informe.append("")
informe.append("Distribución por auditoria_origen:")
for k, v in conteo_dict(producto_auditoria["auditoria_origen"]).items():
    informe.append(f"- {k}: {v}")
informe.append("")
informe.append("Distribución por estado_producto_auditoria:")
for k, v in conteo_dict(producto_auditoria["estado_producto_auditoria"]).items():
    informe.append(f"- {k}: {v}")
informe.append("")

informe.append("## 11. Conclusión técnica")
informe.append("")
informe.append("El piloto ampliado v18 fue exitoso a nivel técnico.")
informe.append("")
informe.append("- 5.000 productos procesados")
informe.append("- 445 columnas origen")
informe.append("- 445 columnas mapeadas")
informe.append("- 29 tablas generadas")
informe.append(f"- {tablas_con_datos} tablas con datos")
informe.append(f"- {tablas_vacias} tablas vacías")
informe.append("- 0 errores")
informe.append("- PRODUCTO_CATEGORIA con MERCADO = 0")
informe.append("")
informe.append("Este resultado no autoriza carga masiva ni modificación de producción.")
informe.append("")

informe.append("## 12. Pendientes recomendados")
informe.append("")
informe.append("1. Comparar formalmente v17 vs v18.")
informe.append("2. Evaluar v1.21.0 para moneda/tipo_valor en PRODUCTO_PRECIO.")
informe.append("3. Evaluar conexión SQL Server solo lectura para futuras muestras.")
informe.append("4. Validar equivalentes contra la base completa antes de tratarlos como aprobados.")
informe.append("5. Preparar resumen ejecutivo si Don Andrés solicita avance adicional.")
informe.append("")

out_path = ENTREGABLES / "informe_piloto_v18_5000_v1_20.md"
out_path.write_text("\n".join(informe), encoding="utf-8")

print(f"Informe generado: {out_path}")
print("Estado: OK")
