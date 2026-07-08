# Informe tecnico - Piloto de normalizacion `piloto_v17_v1_20`

Fecha de generacion: 2026-07-08  
Version normalizador: 1.20.0  
Fuente piloto: `01_fuentes\productos_hugo_con_nombre_top1000.csv`  
Mapeo: `01_fuentes\Normalizacion_Tabla_Productos.xlsx`  
Salida: `04_salidas_normalizadas\piloto_productos_hugo_con_nombre_top1000_v17`

## 1. Objetivo

Documentar el cierre tecnico del piloto de normalizacion de `dbo.productos_hugo` hacia salidas derivadas, usando una muestra controlada de 1000 productos y el mapeo oficial de 445 columnas.

El objetivo de esta fase fue validar estructura, materialidad y ubicacion correcta de los datos, sin modificar la fuente original, sin cargar SQL Server y sin tocar Azure.

## 2. Resultado general

| Control | Resultado |
|---|---:|
| Filas origen | 1000 |
| Columnas origen | 445 |
| Columnas en mapeo | 445 |
| Tablas generadas | 29 |
| Errores de ejecucion | 0 |
| Version normalizador | 1.20.0 |

## 3. Tablas clave auditadas en profundidad

Esta seccion no significa que solo estas tablas existan. El piloto genero 29 salidas. Estas son las tablas que se revisaron en profundidad porque concentraban mayor riesgo estructural o semantico.

| Tabla | Resultado | Estado |
|---|---:|---|
| PRODUCTO_CORE | 1000 filas | Generada |
| PRODUCTO_AUDITORIA | 6666 filas | Cerrada |
| PRODUCTO_INVENTARIO | 373 filas / 18 columnas | Cerrada |
| PRODUCTO_EQUIVALENTE | 342 filas | Cerrada con validacion BD pendiente |
| PRODUCTO_PRECIO | 6970 filas | Revisada |
| PRODUCTO_PROVEEDOR | 1844 filas | Revisada con observacion |
| PRODUCTO_PARAMETRO | 5807 filas | Repetible confirmada |
| PRODUCTO_CATEGORIA | 6798 filas | Cerrada tecnicamente |

## 4. Correcciones principales

### PRODUCTO_AUDITORIA - v1.15.0

Se corrigio la perdida estructural de auditoria. La tabla paso a conservar eventos reales.

| Control | Resultado |
|---|---:|
| Eventos esperados | 6666 |
| Filas generadas | 6666 |
| Faltantes | 0 |
| Extras | 0 |

### PRODUCTO_INVENTARIO / PRODUCTO_EQUIVALENTE - v1.16.0

Se retiro de PRODUCTO_INVENTARIO el campo ambiguo `alternativa / alternativa_cantidad` y se movieron codigos de `STOCK_ALTERNATIVA_PRODUCTO` a PRODUCTO_EQUIVALENTE como `PRODUCTO_ALTERNATIVO`.

| Control | Resultado |
|---|---:|
| PRODUCTO_INVENTARIO columnas | 18 |
| PRODUCTO_EQUIVALENTE filas | 342 |
| Alternativos agregados | 74 |
| Validados en piloto | 9 |
| Pendientes validacion BD completa | 65 |

### PRODUCTO_CATEGORIA - v1.18.0 a v1.20.0

Se depuro PRODUCTO_CATEGORIA para evitar que valores de mercado, booleanos o agrupadores comerciales quedaran como categorias tecnicas.

| Correccion | Registros removidos |
|---|---:|
| Booleanos tipo MERCADO: MERCA_CLI=SI | 800 |
| Booleanos tipo MERCADO: PSO=SI | 4 |
| CLASI_MERCA duplicado contra CLASIFICACION | 61 |
| CLASI_MERCA restante documentado como agrupador / mercado | 7 |
| Total removido de PRODUCTO_CATEGORIA | 872 |

Resultado final PRODUCTO_CATEGORIA:

| tipo_categoria | Filas |
|---|---:|
| CLASIFICACION | 5798 |
| ERP_WO | 1000 |
| MERCADO | 0 |
| Total | 6798 |

## 5. Decision sobre CLASI_MERCA

CLASI_MERCA no queda aprobado automaticamente como categoria dentro de PRODUCTO_CATEGORIA.

Motivo:

- Es un campo de mercado.
- Muchos registros duplicaban clasificaciones ya existentes.
- Los restantes funcionan mejor como agrupadores comerciales, alias o dimension de navegacion pendiente.
- Mantenerlos como categoria mezclaria clasificacion tecnica con navegacion/mercado.

Decision:

- Se excluyen de PRODUCTO_CATEGORIA.
- Se documentan como informacion heredada de mercado.
- Quedan pendientes de definicion de modelo si mas adelante se crea una dimension comercial o de navegacion.

## 6. Pendientes reales

| # | Pendiente | Motivo |
|---:|---|---|
| 1 | Validar contra BD completa los 65 productos alternativos pendientes | En piloto solo se validaron contra la muestra de 1000 |
| 2 | Definir modelo para informacion heredada de mercado | MERCA_CLI, PSO y CLASI_MERCA ya no se mezclan como categoria |
| 3 | Ejecutar muestra mas representativa | Antes de escalar a toda productos_hugo |
| 4 | Definir criterios de aceptacion para carga real | Antes de produccion o SQL Server |

## 7. Conclusion

El piloto v17 con normalizador v1.20.0 queda cerrado tecnicamente.

Se generaron 29 salidas normalizadas desde una muestra controlada de 1000 productos. Se corrigieron problemas estructurales y semanticos importantes sin modificar fuentes originales, sin cargar SQL Server y sin tocar Azure.

PRODUCTO_CATEGORIA queda limpia de valores tipo MERCADO y conserva solo clasificaciones tecnicas y ERP_WO. La informacion de mercado queda documentada, no aprobada como categoria definitiva.

Este cierre corresponde a piloto auditado. Todavia no se recomienda carga masiva hasta ejecutar una muestra mas representativa y definir criterios de aceptacion.
