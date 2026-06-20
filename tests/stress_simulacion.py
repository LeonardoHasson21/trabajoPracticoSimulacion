import random
import sys
from pathlib import Path

sys.dont_write_bytecode = True

RAIZ_PROYECTO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_PROYECTO))

from src.vacunatorio.config.constantes import (  # noqa: E402
    COVID,
    EVENTO_FIN_MAX_ITERACIONES,
    EVENTO_FIN_SIMULACION,
    GRIPE,
    INFINITO,
)
from src.vacunatorio.config.parametros import Parametros  # noqa: E402
from src.vacunatorio.simulacion.motor import Simulacion  # noqa: E402


EVENTOS_FINALES = {EVENTO_FIN_SIMULACION, EVENTO_FIN_MAX_ITERACIONES}


def ejecutar_y_validar(nombre, parametros):
    simulacion = Simulacion(parametros)
    resultado = simulacion.simular()

    validar_resultado(nombre, simulacion, resultado)
    return simulacion, resultado


def validar_resultado(nombre, simulacion, resultado):
    p = simulacion.p
    filas = resultado["filas"]
    assert resultado["estadisticas"], f"{nombre}: no genero estadisticas"
    assert resultado["rk"], f"{nombre}: no genero tabla Runge-Kutta"

    assert filas, f"{nombre}: no genero la fila final obligatoria"
    assert len(filas) <= p.mostrar_cantidad + 1, f"{nombre}: mostro mas filas que i mas final"
    assert simulacion.reloj == p.tiempo_simulacion or simulacion.iteracion >= p.max_iteraciones, f"{nombre}: no corto correctamente"

    filas_rango = [fila for fila in filas if fila["Evento"] not in EVENTOS_FINALES]
    fila_final = filas[-1]
    assert fila_final["Evento"] in EVENTOS_FINALES, f"{nombre}: no mostro la fila final al final"

    if filas_rango:
        primera = filas_rango[0]["Iteracion"]
        ultima_visible = filas_rango[-1]["Iteracion"]
        assert primera >= p.mostrar_desde, f"{nombre}: empezo antes de j"
        assert ultima_visible < p.mostrar_desde + p.mostrar_cantidad, f"{nombre}: mostro despues de j+i-1"

    for anterior, actual in zip(filas, filas[1:]):
        assert actual["Reloj (seg)"] >= anterior["Reloj (seg)"], f"{nombre}: el reloj retrocedio"
        assert actual["Iteracion"] >= anterior["Iteracion"], f"{nombre}: la iteracion retrocedio"

    if fila_final["Evento"] == EVENTO_FIN_SIMULACION:
        assert fila_final["Reloj (seg)"] == p.tiempo_simulacion, f"{nombre}: final visible no esta en X"
    if fila_final["Evento"] == EVENTO_FIN_MAX_ITERACIONES:
        assert simulacion.iteracion == p.max_iteraciones, f"{nombre}: max iter visible incorrecto"

    assert 0 <= simulacion.dosis_gripe_abiertas <= p.dosis_caja_gripe, f"{nombre}: dosis gripe fuera de rango"
    assert simulacion.covid_vacunados <= simulacion.covid_llegados, f"{nombre}: vacuno mas COVID de los que llegaron"
    assert simulacion.gripe_vacunados <= simulacion.gripe_llegados, f"{nombre}: vacuno mas gripe de los que llegaron"

    activos_covid = sum(1 for paciente in simulacion.pacientes.values() if paciente.vacuna == COVID)
    activos_gripe = sum(1 for paciente in simulacion.pacientes.values() if paciente.vacuna == GRIPE)
    assert simulacion.covid_llegados == simulacion.covid_vacunados + activos_covid, f"{nombre}: balance COVID roto"
    assert simulacion.gripe_llegados == simulacion.gripe_vacunados + activos_gripe, f"{nombre}: balance gripe roto"

    ids_cola = set(simulacion.cola_covid) | set(simulacion.cola_gripe)
    ids_lote = set(simulacion.lote_actual_pacientes)
    assert ids_cola.isdisjoint(ids_lote), f"{nombre}: paciente en cola y lote a la vez"
    assert ids_cola.issubset(simulacion.pacientes), f"{nombre}: cola apunta a paciente inexistente"
    assert ids_lote.issubset(simulacion.pacientes), f"{nombre}: lote apunta a paciente inexistente"

    if simulacion.lote_actual_tipo == GRIPE and simulacion.lote_actual_pacientes:
        pacientes_lote = [simulacion.pacientes[i] for i in simulacion.lote_actual_pacientes]
        grupos_lote = {paciente.grupo_llegada for paciente in pacientes_lote}
        assert len(grupos_lote) == 1, f"{nombre}: lote de gripe mezcla grupos"
        assert len(pacientes_lote) == pacientes_lote[0].grupo, f"{nombre}: grupo de gripe dividido"

    assert simulacion.max_cola_covid >= len(simulacion.cola_covid), f"{nombre}: max cola COVID inconsistente"
    assert simulacion.max_cola_gripe >= len(simulacion.cola_gripe), f"{nombre}: max cola gripe inconsistente"
    assert 0 <= simulacion.tiempo_ocupado <= p.tiempo_simulacion, f"{nombre}: ocupacion fuera de rango"
    assert simulacion.proxima_llegada_covid >= simulacion.reloj, f"{nombre}: proxima llegada COVID quedo en el pasado"
    assert simulacion.proxima_llegada_gripe >= simulacion.reloj, f"{nombre}: proxima llegada gripe quedo en el pasado"

    if simulacion.fin_vacunacion != INFINITO:
        assert simulacion.fin_vacunacion >= simulacion.reloj, f"{nombre}: fin vacunacion quedo en el pasado"
    if simulacion.vencimiento_gripe != INFINITO:
        assert simulacion.vencimiento_gripe >= simulacion.reloj, f"{nombre}: vencimiento quedo en el pasado"


def escenarios_fijos():
    return [
        ("default_8_horas", Parametros()),
        ("corte_por_tiempo_corto", Parametros(tiempo_simulacion=60, mostrar_desde=0, mostrar_cantidad=20)),
        ("corte_por_iteraciones", Parametros(tiempo_simulacion=999999, max_iteraciones=250, mostrar_desde=20, mostrar_cantidad=30)),
        ("interrupcion_frecuente", Parametros(tiempo_simulacion=5000, media_interrupcion=30, duracion_interrupcion=10)),
        ("interrupcion_muy_larga", Parametros(tiempo_simulacion=5000, media_interrupcion=200, duracion_interrupcion=180)),
        ("llegadas_rapidas", Parametros(tiempo_simulacion=2000, media_llegada_covid=5, media_llegada_gripe=6)),
        ("llegadas_lentas", Parametros(tiempo_simulacion=20000, media_llegada_covid=2000, media_llegada_gripe=2500)),
        ("cajas_chicas", Parametros(tiempo_simulacion=5000, dosis_caja_covid=2, dosis_caja_gripe=3)),
        ("cajas_grandes", Parametros(tiempo_simulacion=5000, dosis_caja_covid=20, dosis_caja_gripe=50)),
        ("runge_kutta_largo", Parametros(tiempo_simulacion=5000, rk_t_final=0.5, rk_paso=0.005)),
        ("maximo_100000_iteraciones", Parametros(
            tiempo_simulacion=999999,
            max_iteraciones=100000,
            mostrar_desde=99980,
            mostrar_cantidad=20,
            media_llegada_covid=4,
            media_llegada_gripe=5,
            media_interrupcion=5000,
            duracion_interrupcion=20,
        )),
    ]


def escenarios_aleatorios(cantidad=150):
    rng = random.Random(20260614)
    for indice in range(cantidad):
        max_iteraciones = rng.choice([100, 500, 2000, 10000])
        mostrar_cantidad = rng.randint(0, 60)
        mostrar_desde = rng.randint(0, max(0, max_iteraciones - 1))
        yield (
            f"aleatorio_{indice}",
            Parametros(
                tiempo_simulacion=rng.uniform(60, 50000),
                max_iteraciones=max_iteraciones,
                mostrar_desde=mostrar_desde,
                mostrar_cantidad=mostrar_cantidad,
                semilla=rng.randint(1, 999999),
                media_llegada_covid=rng.uniform(2, 1200),
                media_llegada_gripe=rng.uniform(2, 1200),
                dosis_caja_covid=rng.randint(1, 30),
                dosis_caja_gripe=rng.randint(1, 60),
                tiempo_por_paciente=rng.uniform(1, 120),
                media_interrupcion=rng.uniform(5, 5000),
                duracion_interrupcion=rng.uniform(0, 900),
                rk_r_inicial=rng.uniform(0.1, 5),
                rk_t_inicial=0,
                rk_t_final=rng.uniform(0.01, 0.4),
                rk_paso=rng.uniform(0.001, 0.05),
                rk_coef_r=rng.uniform(-60, 60),
                rk_coef_t=rng.uniform(-30, 30),
                rk_constante=rng.uniform(-30, 30),
            ),
        )


if __name__ == "__main__":
    total = 0
    for nombre, parametros in escenarios_fijos():
        ejecutar_y_validar(nombre, parametros)
        total += 1

    for nombre, parametros in escenarios_aleatorios():
        ejecutar_y_validar(nombre, parametros)
        total += 1

    print(f"Stress OK: {total} escenarios intensivos pasaron correctamente.")
