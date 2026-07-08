# Informe final técnico — Piloto v17 / Normalizador v1.20.0

## 1. Contexto

Este informe documenta el cierre técnico del piloto de rediseño y normalización de la tabla de productos.

El trabajo se realizó sobre una muestra controlada de 1.000 productos tomada de `productos_hugo_con_nombre_top1000.csv`, usando el mapeo oficial de 445 columnas definido en `Normalizacion_Tabla_Productos.xlsx`.

No se modificó la fuente original, no se cargó información a SQL Server y no se tocó Azure.

## 2. Alcance del piloto

| Control | Resultado |
|---|---:|
| Piloto | v17 |
| Normalizador | v1.20.0 |
| Productos procesados | 1.000 |
| Columnas origen / mapeo | 445 |
| Tablas generadas | 29 |
| Tablas con datos | 26 |
| Tablas vacías explicadas | 3 |
| Tablas bloqueantes | 0 |

## 3. Resultado general

El piloto v17 / v1.20.0 queda finiquitado técnicamente para presentación.

Las 29 tablas generadas tienen dictamen final:

| Dictamen | Tablas |
|---|---:|
| CERRADA_PILOTO | 23 |
| VACIA_EXPLICADA_EN_MUESTRA | 3 |
| CERRADA_CON_OBSERVACION_DOCUMENTADA | 2 |
| CERRADA_PILOTO_VALIDACION_BD_COMPLETA_FUERA_ALCANCE | 1 |

No quedaron tablas bloqueantes dentro del alcance del piloto.

## 4. Tablas principales cerradas

| Tabla | Resultado |
|---|---:|
| producto_core | 1.000 filas |
| producto_auditoria | 6.666 filas |
| producto_inventario | 373 filas |
| producto_equivalente | 342 filas |
| producto_categoria | 6.798 filas |
| producto_parametro | 5.807 filas |
| producto_precio | 6.970 filas |
| producto_proveedor | 1.844 filas |

## 5. Cierre de PRODUCTO_CATEGORIA

PRODUCTO_CATEGORIA quedó cerrada técnicamente.

Se retiraron campos que no correspondían a categorías técnicas del producto:

| Campo / caso | Registros tratados |
|---|---:|
| MERCA_CLI=SI | 800 |
| PSO=SI | 4 |
| CLASI_MERCA duplicado contra clasificación | 61 |
| CLASI_MERCA restante documentado como mercado / agrupador | 7 |
| Total removido de PRODUCTO_CATEGORIA | 872 |

Resultado final:

| tipo_categoria | Filas |
|---|---:|
| CLASIFICACION | 5.798 |
| ERP_WO | 1.000 |
| MERCADO | 0 |
| Total | 6.798 |

Don Andrés confirmó que `MERCA_CLI` corresponde a merca cliente y no hace parte de productos. Esa aclaración valida la decisión de excluirlo de PRODUCTO_CATEGORIA.

## 6. Dictamen final de las 29 tablas

| Estado final | Interpretación |
|---|---|
| CERRADA_PILOTO | Tabla generada y revisada sin anomalías bloqueantes en el piloto |
| VACIA_EXPLICADA_EN_MUESTRA | Tabla generada, pero sin registros materializables en la muestra |
| CERRADA_CON_OBSERVACION_DOCUMENTADA | Tabla cerrada con observación no bloqueante |
| CERRADA_PILOTO_VALIDACION_BD_COMPLETA_FUERA_ALCANCE | Cerrada para el piloto; validación completa corresponde a fase posterior |

## 7. Observaciones no bloqueantes

### producto_logistica

Queda cerrada con observación documentada. La observación corresponde a baja cobertura de algunos campos logísticos en la muestra, no a error estructural del modelo.

### producto_proveedor

Queda cerrada con observación documentada. No se inventaron proveedores ni se forzaron llaves cuando la fuente no aportaba el dato.

### producto_equivalente

Queda cerrada para el piloto. La validación contra la base completa queda fuera del alcance del piloto porque requiere consultar el universo completo y no solo la muestra de 1.000 productos.

## 8. Tablas vacías explicadas

| Tabla | Explicación |
|---|---|
| campana | Sin registros materializables en la muestra |
| producto_aplicacion | Sin aplicaciones materializables desde las columnas mapeadas en la muestra |
| producto_precio_competencia | Sin precios de competencia materializables en la muestra |

Estas tablas quedan generadas dentro del modelo, pero vacías en el piloto. No bloquean el cierre técnico.

## 9. Conclusión

El piloto v17 / normalizador v1.20.0 queda finiquitado técnicamente para presentación.

Se generaron 29 tablas normalizadas desde la muestra de 1.000 productos. Las tablas críticas fueron auditadas en profundidad, las demás fueron revisadas de forma ligera y las tablas vacías quedaron explicadas.

No hay tablas bloqueantes dentro del alcance del piloto.

Este cierre no equivale todavía a una carga masiva sobre toda la base completa. El siguiente paso natural es usar este piloto como base validada para escalar el proceso de forma controlada.
