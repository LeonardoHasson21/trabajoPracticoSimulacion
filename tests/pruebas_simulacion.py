import sys
from pathlib import Path

sys.dont_write_bytecode = True

RAIZ_PROYECTO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_PROYECTO))

from src.vacunatorio.config.constantes import (
    COVID,
    EVENTO_FIN_MAX_ITERACIONES,
    EVENTO_FIN_SIMULACION,
    EVENTO_INICIO_INTERRUPCION,
)
from src.vacunatorio.config.parametros import Parametros
from src.vacunatorio.dominio.modelos import Paciente
from src.vacunatorio.simulacion.motor import Simulacion


def buscar_estadistica(resultado, nombre):
    for estadistica, valor in resultado["estadisticas"]:
        if estadistica == nombre:
            return valor
    raise AssertionError(f"No existe la estadistica {nombre}")


def probar_filtro_i_j_y_fila_final():
    p = Parametros(tiempo_simulacion=3600, mostrar_desde=5, mostrar_cantidad=7)
    resultado = Simulacion(p).simular()
    filas = resultado["filas"]
    filas_rango = [fila for fila in filas if fila["Evento"] != EVENTO_FIN_SIMULACION]

    assert len(filas_rango) <= 7
    assert filas_rango[0]["Iteracion"] == 5
    assert filas_rango[-1]["Iteracion"] <= 11
    assert filas[-1]["Evento"] == EVENTO_FIN_SIMULACION
    assert filas[-1]["Reloj (seg)"] == 3600


def probar_fila_final_se_muestra_aunque_no_caiga_en_rango():
    p = Parametros(
        tiempo_simulacion=3600,
        mostrar_desde=0,
        mostrar_cantidad=3,
    )
    filas = Simulacion(p).simular()["filas"]

    assert len(filas) == 4
    assert [fila["Iteracion"] for fila in filas[:3]] == [0, 1, 2]
    assert filas[-1]["Evento"] == EVENTO_FIN_SIMULACION
    assert filas[-1]["Iteracion"] > 2


def probar_interrupcion_exactamente_en_x_no_se_procesa():
    p = Parametros(
        tiempo_simulacion=3600,
        intervalo_interrupcion=3600,
        media_llegada_covid=10**9,
        media_llegada_gripe=10**9,
        mostrar_desde=0,
        mostrar_cantidad=10,
    )
    filas = Simulacion(p).simular()["filas"]
    eventos = [fila["Evento"] for fila in filas]

    assert EVENTO_INICIO_INTERRUPCION not in eventos
    assert eventos[-1] == EVENTO_FIN_SIMULACION


def probar_corte_por_max_iteraciones():
    p = Parametros(tiempo_simulacion=999999, max_iteraciones=3, mostrar_desde=0, mostrar_cantidad=10)
    resultado = Simulacion(p).simular()
    ultima = resultado["filas"][-1]

    assert ultima["Evento"] == EVENTO_FIN_MAX_ITERACIONES
    assert ultima["Iteracion"] == 3
    assert ultima["Reloj (seg)"] < p.tiempo_simulacion


def probar_parametros_de_caja_y_tiempo():
    p = Parametros(dosis_caja_covid=3, tiempo_por_paciente=10)
    simulacion = Simulacion(p)

    for paciente_id in range(1, 5):
        simulacion.pacientes[paciente_id] = Paciente(paciente_id, COVID, 0, 4)
        simulacion.cola_covid.append(paciente_id)

    inicio = simulacion.iniciar_lote_covid()

    assert inicio is True
    assert len(simulacion.lote_actual_pacientes) == 3
    assert len(simulacion.cola_covid) == 1
    assert simulacion.fin_vacunacion == 30
    assert simulacion.cajas_covid_abiertas == 1


def probar_runge_kutta_configurable():
    p = Parametros(
        rk_t_inicial=0,
        rk_t_final=0.04,
        rk_paso=0.02,
        rk_coef_r=50,
        rk_coef_t=-2,
        rk_constante=-10,
    )
    resultado = Simulacion(p).simular()

    assert len(resultado["rk"]) == 3
    assert resultado["rk"][0]["t"] == 0
    assert resultado["rk"][0]["E"] == 1
    assert abs(resultado["rk"][0]["K1"] - 40) < 0.0001
    assert abs(resultado["rk"][0]["E+H/2*K1"] - 1.4) < 0.0001
    assert abs(resultado["rk"][0]["E(i+1)"] - 2.3661) < 0.0001
    assert buscar_estadistica(resultado, "Tiempo vencimiento gripe por RK (seg)") > 0


def probar_vector_muestra_atributos_de_pacientes_presentes():
    p = Parametros(
        tiempo_simulacion=100,
        media_llegada_covid=5,
        media_llegada_gripe=10**9,
        dosis_caja_covid=9999,
        mostrar_desde=0,
        mostrar_cantidad=20,
    )
    filas = Simulacion(p).simular()["filas"]
    fila = next(fila for fila in filas if fila.get("_objetos"))
    paciente = fila["_objetos"][0]

    assert set(paciente) == {
        "ID",
        "Vacuna",
        "Estado",
        "Llegada (seg)",
        "Grupo",
        "Inicio vacunacion",
    }
    assert fila["Pacientes presentes"] == len(fila["_objetos"])


def probar_interrupcion_parametrizable():
    p = Parametros(
        tiempo_simulacion=1000,
        intervalo_interrupcion=100,
        duracion_interrupcion=20,
        mostrar_desde=0,
        mostrar_cantidad=50,
    )
    resultado = Simulacion(p).simular()

    assert buscar_estadistica(resultado, "Interrupciones ocurridas") >= 1
    assert buscar_estadistica(resultado, "Tiempo total interrumpido (seg)") >= 20


if __name__ == "__main__":
    probar_filtro_i_j_y_fila_final()
    probar_fila_final_se_muestra_aunque_no_caiga_en_rango()
    probar_interrupcion_exactamente_en_x_no_se_procesa()
    probar_corte_por_max_iteraciones()
    probar_parametros_de_caja_y_tiempo()
    probar_runge_kutta_configurable()
    probar_vector_muestra_atributos_de_pacientes_presentes()
    probar_interrupcion_parametrizable()
    print("Todas las pruebas pasaron correctamente.")
