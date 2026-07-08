# Decision tecnica - CLASI_MERCA en PRODUCTO_CATEGORIA

Proyecto: redisenio_bd_productos  
Piloto: v17  
Normalizador: v1.20.0  
Tabla revisada: PRODUCTO_CATEGORIA  
Campo origen: CLASI_MERCA  

## 1. Contexto

Durante la revision de PRODUCTO_CATEGORIA se detecto que algunos campos tipo MERCADO estaban entrando como categorias.

Primero se corrigieron valores booleanos que no eran categorias reales:

| Campo | Valor | Registros removidos |
|---|---|---:|
| MERCA_CLI | SI | 800 |
| PSO | SI | 4 |

Despues se revisaron los registros de CLASI_MERCA:

| Estado | Registros |
|---|---:|
| CLASI_MERCA que duplicaban una CLASIFICACION del mismo producto | 61 |
| CLASI_MERCA restantes no duplicados exactos | 7 |

Los 61 duplicados fueron removidos en v1.19.0.

Los 7 restantes fueron analizados con contexto y se concluyo que no deben quedar como categoria definitiva dentro de PRODUCTO_CATEGORIA, porque representan agrupadores comerciales, relaciones de mercado o posibles categorias padre, no la clasificacion tecnica principal del producto.

## 2. Decision aplicada en v1.20.0

Se excluyen de PRODUCTO_CATEGORIA los 7 CLASI_MERCA restantes.

El dato no se elimina del origen. Queda documentado como informacion heredada de mercado, pendiente de definicion de modelo para una posible dimension comercial, alias o agrupador de navegacion.

## 3. Casos documentados

| # | Producto | CLASI_MERCA | Decision |
|---:|---|---|---|
| 1 | 100509 | Indicadores+de+cuadrante | Documentar como relacion comercial / revision de modelo |
| 2 | 141003 | Vacuometros+secos+caja+negra | Documentar como agrupador o categoria comercial pendiente |
| 3 | 284603 | Medidores+de+concentracion+de+gases | Documentar como relacion comercial / revision de modelo |
| 4 | 171803 | Medidores+de+flujo | Documentar como categoria padre / agrupador |
| 5 | 245002 | Metros+digitales | Documentar como categoria padre / agrupador |
| 6 | 201203 | Medidores+de+humedad+digitales+portatiles | Documentar como categoria padre / agrupador |
| 7 | 186605 | Fuentes+de+alimentacion | Documentar como categoria padre / agrupador |

## 4. Resultado final

| Control | Resultado |
|---|---:|
| PRODUCTO_CATEGORIA antes de v1.20.0 | 6805 |
| CLASI_MERCA restantes removidos | 7 |
| PRODUCTO_CATEGORIA final | 6798 |
| MERCADO restante en PRODUCTO_CATEGORIA | 0 |

Distribucion final:

| tipo_categoria | Filas |
|---|---:|
| CLASIFICACION | 5798 |
| ERP_WO | 1000 |

## 5. Estado

PRODUCTO_CATEGORIA queda cerrada tecnicamente para el piloto.

No quedan registros tipo MERCADO dentro de PRODUCTO_CATEGORIA. La informacion de mercado queda documentada como pendiente de modelo, no aprobada como categoria definitiva.
