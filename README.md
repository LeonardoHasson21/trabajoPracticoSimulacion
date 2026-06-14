# Simulacion Vacunatorio

Aplicacion de escritorio en Python para simular el sistema del vacunatorio del TP.

## Como ejecutar

Desde esta carpeta:

```powershell
python -B app.py
```

No requiere instalar librerias externas porque usa `tkinter`, que viene incluido con Python.

Para correr pruebas rapidas de la simulacion:

```powershell
python -B tests/pruebas_simulacion.py
```

Para correr una prueba intensiva con muchos escenarios:

```powershell
python -B tests/stress_simulacion.py
```

La opcion `-B` evita que Python cree carpetas `__pycache__`.

## Estructura del codigo

- `app.py`: punto de entrada de la aplicacion.
- `src/vacunatorio/config/`: constantes del enunciado, parametros y validaciones.
- `src/vacunatorio/dominio/`: entidades simples del sistema, como `Paciente`.
- `src/vacunatorio/simulacion/`: motor de eventos y calculo de Runge-Kutta.
- `src/vacunatorio/ui/`: pantalla hecha con `tkinter`.
- `src/vacunatorio/utils/`: funciones auxiliares compartidas.
- `tests/pruebas_simulacion.py`: pruebas por consola.
- `tests/stress_simulacion.py`: prueba intensiva con invariantes del sistema.

## Que permite modificar

- Tiempo maximo de simulacion.
- Maximo de iteraciones, hasta 100000.
- Iteracion inicial `j` y cantidad de iteraciones `i` a mostrar.
- Semilla aleatoria.
- Medias de llegada de COVID y gripe.
- Dosis por caja de cada vacuna.
- Tiempo de aplicacion por paciente.
- Frecuencia y duracion de la interrupcion.
- Condiciones numericas de Runge-Kutta: R inicial, t inicial, t final y paso h.

El vector muestra las `i` iteraciones solicitadas desde `j` hasta `j + i - 1` y, ademas, agrega la ultima fila de cierre de la simulacion. Por eso, si la fila final esta fuera del rango pedido, se vera como una fila adicional.

## Decisiones de modelado

- Las llegadas de COVID y gripe son independientes.
- En cada llegada arriba un grupo de 1 a 4 personas con probabilidad uniforme.
- COVID se vacuna solo cuando hay al menos 5 pacientes. Si hay mas, se vacuna la mayor cantidad posible en multiplos de 5, porque las cajas tienen 5 dosis.
- Gripe usa una caja abierta de 10 dosis. Si no hay caja abierta y llega gente para gripe, se abre una nueva.
- Las dosis sobrantes de gripe vencen luego del tiempo calculado por Runge-Kutta.
- El enfermero alterna la preferencia entre COVID y gripe. Si toca COVID pero no hay 5 pacientes, intenta con gripe.
- La interrupcion es periodica. Si ocurre durante una vacunacion, pausa al enfermero y al finalizar continua con el tiempo restante.

## Runge-Kutta

El enunciado indica:

```text
41,4 * R = dR/dt + 0,0575 * R
```

En el programa se despeja:

```text
dR/dt = (41,4 - 0,0575) * R
```

Como esa ecuacion no tiene maximo natural cuando `R` inicial es positivo, el programa toma como tiempo de vencimiento el maximo valor de `R` dentro del intervalo de integracion configurado en la pantalla.

Los coeficientes `41,4` y `0,0575` no se pueden modificar desde la interfaz porque son datos fijos del enunciado.

## Estadisticas calculadas

La aplicacion muestra mas de 8 estadisticas, entre ellas:

- Personas COVID llegadas.
- Personas gripe llegadas.
- Personas COVID vacunadas.
- Personas gripe vacunadas.
- Espera promedio COVID.
- Espera promedio gripe.
- Porcentaje de utilizacion del enfermero.
- Porcentaje de pacientes vacunados.
- Maxima cola COVID.
- Maxima cola gripe.
- Cajas abiertas.
- Dosis de gripe descartadas.
- Interrupciones ocurridas.
- Tiempo total interrumpido.
