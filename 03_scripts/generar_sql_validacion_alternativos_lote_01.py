from pathlib import Path
import pandas as pd


INPUT = Path("05_reportes/producto_alternativo_pendiente_validacion_bd_lote_01.csv")
OUTPUT = Path("05_reportes/validar_producto_alternativo_pendiente_lote_01_contra_bd.sql")

df = pd.read_csv(INPUT, sep=";", dtype=str, encoding="utf-8-sig").fillna("")

refs = sorted(
    set(
        str(x).strip()
        for x in df["referencia_equivalente"]
        if str(x).strip()
    )
)

if not refs:
    raise ValueError("No hay referencias_equivalente para validar.")

values_sql = ",\n".join(
    f"('{ref.replace("'", "''")}')"
    for ref in refs
)

sql = f"""
-- Validacion de productos alternativos pendientes contra dbo.productos_hugo
-- Lote 01 / normalizador v1.20.0
-- No modifica datos. Solo lectura.

IF OBJECT_ID('tempdb..#pendientes') IS NOT NULL DROP TABLE #pendientes;
IF OBJECT_ID('tempdb..#coincidencias') IS NOT NULL DROP TABLE #coincidencias;

CREATE TABLE #pendientes (
    referencia_equivalente VARCHAR(100)
);

INSERT INTO #pendientes (referencia_equivalente)
VALUES
{values_sql};

SELECT
    p.referencia_equivalente,
    h.ITEM,
    h.CODIGO,
    h.REFERENCIA,
    h.REF_ALTERNATIVA,
    h.MARCA_LET,
    'CODIGO' AS campo_coincidencia
INTO #coincidencias
FROM #pendientes p
INNER JOIN dbo.productos_hugo h
    ON LTRIM(RTRIM(CAST(h.CODIGO AS VARCHAR(MAX)))) = p.referencia_equivalente

UNION ALL

SELECT
    p.referencia_equivalente,
    h.ITEM,
    h.CODIGO,
    h.REFERENCIA,
    h.REF_ALTERNATIVA,
    h.MARCA_LET,
    'REFERENCIA' AS campo_coincidencia
FROM #pendientes p
INNER JOIN dbo.productos_hugo h
    ON LTRIM(RTRIM(CAST(h.REFERENCIA AS VARCHAR(MAX)))) = p.referencia_equivalente

UNION ALL

SELECT
    p.referencia_equivalente,
    h.ITEM,
    h.CODIGO,
    h.REFERENCIA,
    h.REF_ALTERNATIVA,
    h.MARCA_LET,
    'REF_ALTERNATIVA' AS campo_coincidencia
FROM #pendientes p
INNER JOIN dbo.productos_hugo h
    ON LTRIM(RTRIM(CAST(h.REF_ALTERNATIVA AS VARCHAR(MAX)))) = p.referencia_equivalente

UNION ALL

SELECT
    p.referencia_equivalente,
    h.ITEM,
    h.CODIGO,
    h.REFERENCIA,
    h.REF_ALTERNATIVA,
    h.MARCA_LET,
    'ITEM' AS campo_coincidencia
FROM #pendientes p
INNER JOIN dbo.productos_hugo h
    ON LTRIM(RTRIM(CAST(h.ITEM AS VARCHAR(MAX)))) = p.referencia_equivalente;

-- Resultado 1: resumen por referencia pendiente
SELECT
    p.referencia_equivalente,
    COUNT(c.ITEM) AS coincidencias_total,
    COUNT(DISTINCT c.ITEM) AS productos_distintos_encontrados,
    CASE
        WHEN COUNT(c.ITEM) = 0 THEN 'NO_ENCONTRADO_EN_BD'
        WHEN COUNT(DISTINCT c.ITEM) = 1 THEN 'ENCONTRADO_EN_BD'
        ELSE 'MULTIPLES_COINCIDENCIAS'
    END AS estado_validacion_bd
FROM #pendientes p
LEFT JOIN #coincidencias c
    ON c.referencia_equivalente = p.referencia_equivalente
GROUP BY p.referencia_equivalente
ORDER BY estado_validacion_bd, p.referencia_equivalente;

-- Resultado 2: detalle de coincidencias encontradas
SELECT
    referencia_equivalente,
    ITEM,
    CODIGO,
    REFERENCIA,
    REF_ALTERNATIVA,
    MARCA_LET,
    campo_coincidencia
FROM #coincidencias
ORDER BY referencia_equivalente, ITEM, campo_coincidencia;
"""

OUTPUT.write_text(sql.strip() + "\n", encoding="utf-8")

print(f"Referencias únicas: {len(refs)}")
print(f"SQL generado: {OUTPUT}")