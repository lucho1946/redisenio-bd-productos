# Informe tecnico - Piloto de normalizacion `piloto_v15_v1_18`

Fecha de generacion: 2026-07-08  
Version normalizador: 1.18.0  
Fuente piloto: `01_fuentes\productos_hugo_con_nombre_top1000.csv`  
Mapeo: `01_fuentes\Normalizacion_Tabla_Productos.xlsx`  
Salida: `04_salidas_normalizadas\piloto_productos_hugo_con_nombre_top1000_v15`

## 1. Objetivo

Documentar el avance del piloto de normalizacion de `dbo.productos_hugo` hacia salidas derivadas, usando una muestra controlada de 1000 productos y el mapeo oficial de 445 columnas.

El objetivo de esta fase no es cargar datos a SQL Server ni a Azure, sino validar que las columnas origen se ubiquen en tablas normalizadas correctas, sin contaminar el modelo y conservando trazabilidad.

## 2. Alcance

Este piloto genera archivos CSV derivados. No modifica `dbo.productos_hugo`, no modifica fuentes originales, no crea tablas reales en SQL Server y no carga datos a Azure.

| Control | Resultado |
|---|---:|
| Filas origen | 1000 |
| Columnas origen | 445 |
| Columnas en mapeo | 445 |
| Faltantes en origen | 0 |
| Sobrantes en origen | 0 |
| Tablas generadas | 29 |
| Errores de ejecucion | 0 |
| Version normalizador | 1.18.0 |

## 3. Tablas clave validadas

| Tabla | Resultado v15 / v1.18.0 | Estado |
|---|---:|---|
| PRODUCTO_CORE | 1000 filas | Generada |
| PRODUCTO_AUDITORIA | 6666 filas | Cerrada |
| PRODUCTO_INVENTARIO | 373 filas / 18 columnas | Cerrada |
| PRODUCTO_EQUIVALENTE | 342 filas | Cerrada con validacion BD pendiente |
| PRODUCTO_PRECIO | 6970 filas | Cerrada |
| PRODUCTO_PROVEEDOR | 1844 filas | Cerrada con observacion |
| PRODUCTO_PARAMETRO | 5807 filas | Repetible confirmada |
| PRODUCTO_CATEGORIA | 6866 filas | Cerrada tecnicamente con decision de booleanos tipo MERCADO |

## 4. Correcciones cerradas

### 4.1 PRODUCTO_AUDITORIA - v1.15.0

Se corrigio la perdida estructural de auditoria. La tabla dejo de quedar como una fila resumida por producto y paso a conservar eventos reales de auditoria.

Validacion:

| Control | Resultado |
|---|---:|
| Eventos esperados origen | 6666 |
| Filas generadas | 6666 |
| Productos con auditoria | 1000 |
| Faltantes | 0 |
| Extras | 0 |
| Errores | 0 |

### 4.2 PRODUCTO_INVENTARIO / PRODUCTO_EQUIVALENTE - v1.16.0

Don Andres confirmo que el campo de alternativa en inventario se interpreta como producto alternativo, no como producto alternativo mas cantidad alternativa.

Con ese criterio:

- se retiro de PRODUCTO_INVENTARIO el campo ambiguo `alternativa / alternativa_cantidad`;
- se movieron los codigos de `STOCK_ALTERNATIVA_PRODUCTO` a PRODUCTO_EQUIVALENTE como `PRODUCTO_ALTERNATIVO`;
- no se convirtio `STOCK_ALTERNATIVA_CANTIDAD_PRODUCTO` automaticamente ni en cantidad ni en producto.

| Control v1.16.0 | Resultado |
|---|---:|
| Campo ambiguo removido de inventario | True |
| Columnas inventario antes | 19 |
| Columnas inventario despues | 18 |
| Registros equivalentes iniciales | 268 |
| Alternativos detectados desde inventario | 74 |
| Registros agregados a equivalente | 74 |
| Registros equivalentes finales | 342 |

Estados de los alternativos migrados:

| Estado | Registros |
|---|---:|
| PRODUCTO_ALTERNATIVO_PENDIENTE_VALIDACION_BD | 65 |
| PRODUCTO_ALTERNATIVO_VALIDADO_PILOTO | 9 |

### 4.3 PRODUCTO_CATEGORIA / booleanos tipo MERCADO - v1.18.0

Se auditaron los campos de tipo `MERCADO` porque algunos valores estaban entrando a PRODUCTO_CATEGORIA como `categoria_id`.

Campos revisados:

- `MERCA_CLI`
- `CLASI_MERCA`
- `PSO`
- `MERCA_CLI_MERCA`

Hallazgo del origen:

| Campo | Comportamiento en piloto |
|---|---|
| MERCA_CLI | 800 `SI`, 200 `NO` |
| PSO | 4 `SI`, 1 `NO`, 995 vacios |
| CLASI_MERCA | 68 textos descriptivos no booleanos |
| MERCA_CLI_MERCA | 1000 vacios |

Interpretacion tecnica:

`MERCA_CLI` y `PSO` se comportan como indicadores binarios SI/NO, no como categorias ni familias de producto. En cambio, `CLASI_MERCA` trae textos descriptivos que pueden representar dimensiones o categorias de mercado, por lo que se conservan.

Problema detectado:

Antes de v1.18.0, valores como `SI` estaban entrando a PRODUCTO_CATEGORIA como si `SI` fuera una categoria. Esto contaminaba la tabla porque `SI` no describe un tipo de producto.

Decision tecnica aplicada:

- Se excluyen de PRODUCTO_CATEGORIA los valores booleanos positivos de campos tipo `MERCADO`.
- Criterio de exclusion: `tipo_categoria = MERCADO` y `categoria_id` en `SI`, `SÍ`, `YES`, `TRUE`, `1`.
- El dato no se elimina de la fuente original.
- Las filas removidas quedan documentadas como evidencia.
- No se crea una tabla nueva todavia.
- Estos valores quedan como indicadores heredados pendientes de ubicacion definitiva en el modelo.

Resultado:

| Control v1.18.0 | Resultado |
|---|---:|
| Filas PRODUCTO_CATEGORIA antes | 7670 |
| Filas PRODUCTO_CATEGORIA despues | 6866 |
| Filas removidas | 804 |
| MERCA_CLI=SI removidas | 800 |
| PSO=SI removidas | 4 |
| Booleanos tipo MERCADO restantes | 0 |

Distribucion final de PRODUCTO_CATEGORIA:

| tipo_categoria | Filas |
|---|---:|
| CLASIFICACION | 5798 |
| ERP_WO | 1000 |
| MERCADO | 68 |

MERCADO restante:

| categoria_origen | Filas |
|---|---:|
| CLASI_MERCA | 68 |

Archivo de evidencia:

`05_reportes\mercado_booleanos_indicador_removidos_v118.csv`

Reporte tecnico:

`05_reportes\reporte_postproceso_mercado_booleanos_v118.json`

## 5. Comparacion controlada v13 vs v15

El cambio funcional frente a v13 fue controlado:

| Tabla | Cambio esperado |
|---|---|
| PRODUCTO_CATEGORIA | Baja de 7670 a 6866 filas por exclusion de 804 registros booleanos tipo MERCADO |
| PRODUCTO_EQUIVALENTE | Se mantiene en 342 filas |
| PRODUCTO_INVENTARIO | Se mantiene en 18 columnas |
| Resto de tablas | Sin cambios esperados por v1.18.0 |

## 6. Decisiones vigentes

- No modificar fuentes originales.
- No modificar `dbo.productos_hugo`.
- No cargar datos a SQL Server ni Azure en esta fase.
- Mantener PRODUCTO_AUDITORIA vertical por evento.
- Mantener PRODUCTO_INVENTARIO solo para informacion real de inventario.
- Mantener productos alternativos dentro de PRODUCTO_EQUIVALENTE.
- No convertir `STOCK_ALTERNATIVA_CANTIDAD_PRODUCTO` automaticamente en cantidad ni en producto.
- No registrar valores booleanos positivos de tipo MERCADO como categorias.
- Documentar esos valores como indicadores heredados pendientes de ubicacion definitiva.
- Conservar textos descriptivos no booleanos de tipo MERCADO.
- Los alternativos no validados contra el piloto quedan pendientes de validacion contra BD completa.

## 7. Pendientes

1. Validar contra BD completa los 65 productos alternativos pendientes.
2. Definir ubicacion final de indicadores heredados como `MERCA_CLI` y `PSO`.
3. Revisar si las 68 filas de `CLASI_MERCA` deben quedar como dimension de mercado o relacionarse con categorias comerciales existentes.
4. Ejecutar una muestra mas representativa antes de escalar a toda la tabla.
5. Definir criterios de aceptacion para una carga real futura.

## 8. Conclusion

El piloto v15 con normalizador v1.18.0 queda como avance tecnico validado. Se corrigieron problemas reales de estructura y semantica sin modificar fuentes originales y sin cargar datos a SQL Server/Azure.

La correccion de booleanos tipo MERCADO evita contaminar PRODUCTO_CATEGORIA con valores como `SI`, conservando trazabilidad y dejando esos datos como indicadores pendientes de ubicacion definitiva.

El piloto todavia debe considerarse version auditada, no version final de carga masiva.
