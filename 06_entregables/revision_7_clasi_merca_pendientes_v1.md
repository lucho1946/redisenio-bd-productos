# Revision de 7 casos CLASI_MERCA pendientes

Proyecto: redisenio_bd_productos  
Piloto: v16  
Normalizador: v1.19.0  
Tabla: PRODUCTO_CATEGORIA  
Campo origen: CLASI_MERCA  

## 1. Contexto

Durante la depuracion de PRODUCTO_CATEGORIA se revisaron los campos tipo MERCADO.

Primero se retiraron valores booleanos que no eran categorias:

| Campo | Valor | Registros |
|---|---|---:|
| MERCA_CLI | SI | 800 |
| PSO | SI | 4 |

Despues se revisaron 68 registros restantes de CLASI_MERCA:

| Estado | Registros |
|---|---:|
| Duplicaban una CLASIFICACION del mismo producto | 61 |
| No duplicaban exactamente | 7 |

Los 61 duplicados fueron retirados en v1.19.0 para evitar doble registro semantico en PRODUCTO_CATEGORIA.

Quedan 7 casos que no duplican exactamente la clasificacion del producto. Estos casos se conservan provisionalmente porque pueden representar una categoria mas general, una dimension de mercado o un agrupador comercial.

## 2. Casos pendientes

| # | Producto | CLASI_MERCA pendiente | Lectura tecnica | Decision recomendada |
|---:|---|---|---|---|
| 1 | 100509 | Indicadores+de+cuadrante | Puede representar una familia comercial distinta a las clasificaciones actuales del producto. | REVISION_MODELO |
| 2 | 141003 | Vacuometros+secos+caja+negra | Parece una categoria comercial mas especifica o paralela a la clasificacion actual. | REVISION_MODELO |
| 3 | 284603 | Medidores+de+concentracion+de+gases | Puede funcionar como agrupador comercial general frente a una clasificacion mas especifica. | REVISION_MODELO |
| 4 | 171803 | Medidores+de+flujo | Puede ser categoria general frente a una clasificacion especifica de hidrocarburos. | REVISION_MODELO |
| 5 | 245002 | Metros+digitales | Puede representar agrupador comercial distinto a distanciometros/metros ultrasonicos. | REVISION_MODELO |
| 6 | 201203 | Medidores+de+humedad+digitales+portatiles | Puede ser agrupador general frente a clasificaciones mas especificas por aplicacion/material. | REVISION_MODELO |
| 7 | 186605 | Fuentes+de+alimentacion | Puede ser categoria general frente a fuentes switcheadas/industriales. | REVISION_MODELO |

## 3. Decision tecnica recomendada

No retirar automaticamente estos 7 casos.

Motivo:

- No son booleanos.
- No duplican exactamente una CLASIFICACION del mismo producto.
- Pueden aportar una dimension comercial o una categoria padre.
- Requieren definicion de modelo antes de decidir si quedan en PRODUCTO_CATEGORIA o en una tabla/dimension separada.

## 4. Estado recomendado

CLASI_MERCA_DUPLICADO: cerrado  
CLASI_MERCA_NO_DUPLICADO: pendiente de decision de modelo  
PRODUCTO_CATEGORIA: cerrada tecnicamente con 7 observaciones  

## 5. Propuesta para Don Andres

Revisar estos 7 casos y confirmar si CLASI_MERCA debe manejarse como:

1. categoria adicional de mercado dentro de PRODUCTO_CATEGORIA;
2. dimension comercial separada;
3. alias/relacion con una categoria existente;
4. campo heredado no reutilizable para el nuevo modelo.

Hasta tener esa decision, los 7 casos se conservan provisionalmente y se documentan como pendiente de modelo.
