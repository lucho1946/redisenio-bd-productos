# Informe tecnico - Piloto de normalizacion `piloto_v16_v1_19`

Fecha de generacion: 2026-07-08  
Version normalizador: 1.19.0  
Fuente piloto: `01_fuentes\productos_hugo_con_nombre_top1000.csv`  
Mapeo: `01_fuentes\Normalizacion_Tabla_Productos.xlsx`  
Salida: `04_salidas_normalizadas\piloto_productos_hugo_con_nombre_top1000_v16`

## 1. Objetivo

Documentar el avance del piloto de normalizacion de `dbo.productos_hugo` hacia salidas derivadas, usando una muestra controlada de 1000 productos y el mapeo oficial de 445 columnas.

El objetivo no es cargar datos a SQL Server ni a Azure, sino validar que las columnas origen se ubiquen en tablas normalizadas correctas, sin contaminar el modelo y conservando trazabilidad.

## 2. Resultado general

| Control | Resultado |
|---|---:|
| Filas origen | 1000 |
| Columnas origen | 445 |
| Columnas en mapeo | 445 |
| Tablas generadas | 29 |
| Errores de ejecucion | 0 |
| Version normalizador | 1.19.0 |

## 3. Correcciones cerradas

### PRODUCTO_AUDITORIA - v1.15.0

Se conserva auditoria vertical por evento real.

| Control | Resultado |
|---|---:|
| Eventos esperados origen | 6666 |
| Filas generadas | 6666 |
| Faltantes | 0 |
| Extras | 0 |

### PRODUCTO_INVENTARIO / PRODUCTO_EQUIVALENTE - v1.16.0

Se retiro de PRODUCTO_INVENTARIO el campo ambiguo `alternativa / alternativa_cantidad` y se movieron los codigos de `STOCK_ALTERNATIVA_PRODUCTO` a PRODUCTO_EQUIVALENTE como `PRODUCTO_ALTERNATIVO`.

| Control | Resultado |
|---|---:|
| PRODUCTO_INVENTARIO columnas | 18 |
| PRODUCTO_EQUIVALENTE filas | 342 |
| Alternativos agregados | 74 |
| Pendientes validacion BD | 65 |
| Validados en piloto | 9 |

### PRODUCTO_CATEGORIA / booleanos tipo MERCADO - v1.18.0

Se excluyeron valores booleanos positivos de campos tipo MERCADO porque `SI`, `YES`, `TRUE` o `1` no describen una categoria.

| Campo | Registros removidos |
|---|---:|
| MERCA_CLI=SI | 800 |
| PSO=SI | 4 |
| Total | 804 |

### PRODUCTO_CATEGORIA / CLASI_MERCA duplicado - v1.19.0

Se auditaron las 68 filas restantes de tipo MERCADO. El resultado fue:

| Estado | Registros |
|---|---:|
| CLASI_MERCA duplica CLASIFICACION del mismo producto | 61 |
| CLASI_MERCA no duplicado exacto | 7 |
| Booleanos remanentes | 0 |

Decision aplicada:

- Los 61 `CLASI_MERCA` que duplicaban una `CLASIFICACION` del mismo producto se excluyeron de PRODUCTO_CATEGORIA.
- Los 7 `CLASI_MERCA` no duplicados se conservan provisionalmente como dimension de mercado pendiente de definicion.
- No se elimina informacion de la fuente original.

## 4. Resultado final PRODUCTO_CATEGORIA

| Control | Resultado |
|---|---:|
| Filas antes de limpieza MERCADO | 7670 |
| Filas despues de v1.18.0 | 6866 |
| Filas despues de v1.19.0 | 6805 |
| Booleanos MERCADO removidos | 804 |
| CLASI_MERCA duplicados removidos | 61 |
| MERCADO restante | 7 |

Distribucion final:

| tipo_categoria | Filas |
|---|---:|
| CLASIFICACION | 5798 |
| ERP_WO | 1000 |
| MERCADO | 7 |

MERCADO restante:

| categoria_origen | categoria_id |
|---|---|
| CLASI_MERCA | Indicadores+de+cuadrante |
| CLASI_MERCA | Vacuometros+secos+caja+negra |
| CLASI_MERCA | Medidores+de+concentracion+de+gases |
| CLASI_MERCA | Medidores+de+flujo |
| CLASI_MERCA | Metros+digitales |
| CLASI_MERCA | Medidores+de+humedad+digitales+portatiles |
| CLASI_MERCA | Fuentes+de+alimentacion |

## 5. Decisiones vigentes

- No modificar fuentes originales.
- No modificar `dbo.productos_hugo`.
- No cargar datos a SQL Server ni Azure.
- No registrar booleanos como categorias.
- No duplicar `CLASI_MERCA` cuando ya existe como `CLASIFICACION` del mismo producto.
- Conservar provisionalmente los 7 `CLASI_MERCA` no duplicados hasta definir si son dimension de mercado, agrupador comercial o categoria relacionada.

## 6. Pendientes

1. Definir ubicacion final de indicadores heredados como `MERCA_CLI` y `PSO`.
2. Revisar con negocio/modelo los 7 `CLASI_MERCA` restantes.
3. Validar contra BD completa los 65 productos alternativos pendientes.
4. Ejecutar una muestra mas representativa antes de escalar a toda la tabla.
5. Definir criterios de aceptacion para una carga real futura.

## 7. Conclusion

El piloto v16 con normalizador v1.19.0 queda como avance tecnico validado. Se corrigieron problemas reales de estructura y semantica en PRODUCTO_CATEGORIA sin modificar fuentes originales y sin cargar datos a SQL Server/Azure.

La tabla queda libre de booleanos tipo MERCADO y sin duplicados exactos de CLASI_MERCA contra CLASIFICACION del mismo producto. Los 7 casos restantes quedan conservados provisionalmente porque requieren definicion de modelo o validacion de negocio.
