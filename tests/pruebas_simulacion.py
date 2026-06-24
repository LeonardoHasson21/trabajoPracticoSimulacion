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
    EVENTO_INTERRUPCION_DESCARTADA,
    GRIPE,
)
from src.vacunatorio.config.parametros import Parametros
from src.vacunatorio.dominio.modelos import Paciente
from src.vacunatorio.simulacion.motor import ESTADO_ENFERMERO_INTERRUMPIDO, Simulacion
from src.vacunatorio.ui.interfaz import Aplicacion


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
    assert filas[-1]["_objetos"] == []
    assert filas[-1]["Pacientes presentes"] == "-"


def probar_interrupcion_exactamente_en_x_no_se_procesa():
    p = Parametros(
        tiempo_simulacion=3600,
        media_interrupcion=10**9,
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
        "Grupo llegada",
        "Inicio vacunacion",
    }
    assert fila["Pacientes presentes"] == len(fila["_objetos"])


def probar_interrupcion_parametrizable():
    p = Parametros(
        tiempo_simulacion=1000,
        media_interrupcion=100,
        duracion_interrupcion=20,
        mostrar_desde=0,
        mostrar_cantidad=50,
    )
    resultado = Simulacion(p).simular()

    assert buscar_estadistica(resultado, "Interrupciones ocurridas") >= 1
    assert buscar_estadistica(resultado, "Tiempo total interrumpido (seg)") > 0


def probar_gripe_atiende_todos_los_pacientes_en_cola():
    simulacion = Simulacion(Parametros(dosis_caja_gripe=10))
    simulacion.crear_pacientes(GRIPE, 3)
    simulacion.crear_pacientes(GRIPE, 3)

    inicio = simulacion.iniciar_lote_gripe()

    assert inicio is True
    assert simulacion.lote_actual_pacientes == [1, 2, 3, 4, 5, 6]
    assert list(simulacion.cola_gripe) == []
    assert all(simulacion.pacientes[i].estado == "En vacunacion" for i in range(1, 7))


def probar_gripe_abre_otra_caja_y_atiende_completo_si_faltan_dosis():
    simulacion = Simulacion(Parametros(dosis_caja_gripe=10))
    simulacion.crear_pacientes(GRIPE, 3)
    simulacion.crear_pacientes(GRIPE, 2)
    simulacion.dosis_gripe_abiertas = 2
    simulacion.vencimiento_gripe = 100
    simulacion.cajas_gripe_abiertas = 1

    inicio = simulacion.iniciar_lote_gripe()

    assert inicio is True
    assert simulacion.lote_actual_pacientes == [1, 2, 3, 4, 5]
    assert list(simulacion.cola_gripe) == []
    assert simulacion.pacientes[3].grupo_llegada != simulacion.pacientes[4].grupo_llegada
    assert simulacion.cajas_gripe_abiertas == 2
    assert simulacion.dosis_gripe_abiertas == 7
    assert simulacion.vencimiento_gripe == simulacion.reloj + simulacion.tiempo_vencimiento_gripe


def probar_columnas_de_pacientes_muestran_tipo_e_id_real():
    aplicacion = Aplicacion.__new__(Aplicacion)
    filas = [
        {
            "_objetos": [
                {"ID": 12, "Vacuna": GRIPE, "Estado": "Esperando", "Llegada (seg)": 5},
                {"ID": 91, "Vacuna": COVID, "Estado": "Esperando", "Llegada (seg)": 8},
            ]
        }
    ]

    encabezado = aplicacion.construir_encabezado_vector(filas)
    grupos_pacientes = {
        grupo["texto"]: grupo
        for grupo in encabezado
        if grupo["texto"].startswith("PACIENTES ")
    }

    assert grupos_pacientes["PACIENTES GRIPE"]["hijos"][0]["texto"] == "Paciente Gripe ID 12"
    assert grupos_pacientes["PACIENTES COVID"]["hijos"][0]["texto"] == "Paciente COVID ID 91"
    assert aplicacion.valor_vector(filas[0], "__paciente_Gripe_12_estado") == "Esperando"
    assert aplicacion.valor_vector(filas[0], "__paciente_COVID_91_llegada") == 8


def probar_paginacion_limita_columnas_sin_perder_ids():
    aplicacion = Aplicacion.__new__(Aplicacion)
    aplicacion.ids_pacientes_vector = {
        GRIPE: list(range(1, 21)),
        COVID: list(range(21, 41)),
    }
    aplicacion.pagina_pacientes_vector = 0

    primera_pagina = aplicacion.ids_pacientes_pagina_actual()
    assert primera_pagina[GRIPE] == list(range(1, 17))
    assert primera_pagina[COVID] == []
    assert aplicacion.cantidad_paginas_pacientes() == 3

    aplicacion.pagina_pacientes_vector = 1
    segunda_pagina = aplicacion.ids_pacientes_pagina_actual()
    assert segunda_pagina[GRIPE] == list(range(17, 21))
    assert segunda_pagina[COVID] == list(range(21, 33))

    ids_mostrados = set()
    for pagina in range(aplicacion.cantidad_paginas_pacientes()):
        aplicacion.pagina_pacientes_vector = pagina
        seleccion = aplicacion.ids_pacientes_pagina_actual()
        ids_mostrados.update(seleccion[GRIPE])
        ids_mostrados.update(seleccion[COVID])
    assert ids_mostrados == set(range(1, 41))


def probar_gripe_abre_varias_cajas_si_el_parametro_es_chico():
    simulacion = Simulacion(Parametros(dosis_caja_gripe=1))
    simulacion.crear_pacientes(GRIPE, 4)

    inicio = simulacion.iniciar_lote_gripe()

    assert inicio is True
    assert simulacion.lote_actual_pacientes == [1, 2, 3, 4]
    assert simulacion.cajas_gripe_abiertas == 4
    assert simulacion.dosis_gripe_abiertas == 0


def probar_interrupcion_exponencial_muestra_rnd():
    p = Parametros(tiempo_simulacion=10, media_interrupcion=100)
    fila_inicial = Simulacion(p).simular()["filas"][0]

    assert fila_inicial["RND interrupcion"] != "-"
    assert fila_inicial["Tiempo interrupcion"] > 0
    assert fila_inicial["Prox interrupcion"] == fila_inicial["Tiempo interrupcion"]


def probar_interrupcion_descartada_no_modifica_la_actual():
    simulacion = Simulacion(Parametros(mostrar_desde=0, mostrar_cantidad=10))
    simulacion.reloj = 100
    simulacion.enfermero_estado = ESTADO_ENFERMERO_INTERRUMPIDO
    simulacion.fin_interrupcion = 180

    simulacion.procesar_llegada_interrupcion()

    assert simulacion.fin_interrupcion == 180
    assert simulacion.interrupciones == 0
    assert simulacion.filas[-1]["Evento"] == EVENTO_INTERRUPCION_DESCARTADA
    assert simulacion.proxima_interrupcion > simulacion.reloj


def probar_tiempo_interrumpido_se_acumula_con_el_reloj():
    simulacion = Simulacion(Parametros())
    simulacion.reloj = 10
    simulacion.ultima_actualizacion_ocupacion = 10
    simulacion.enfermero_estado = ESTADO_ENFERMERO_INTERRUMPIDO

    simulacion.avanzar_reloj(37.5)

    assert simulacion.tiempo_interrumpido == 27.5


def probar_interrupcion_pausa_lote_y_marca_pacientes():
    simulacion = Simulacion(Parametros(mostrar_desde=0, mostrar_cantidad=10, duracion_interrupcion=20))
    simulacion.crear_pacientes(GRIPE, 3)
    simulacion.iniciar_lote_gripe()
    simulacion.reloj = 5

    simulacion.procesar_llegada_interrupcion()

    assert simulacion.enfermero_estado == ESTADO_ENFERMERO_INTERRUMPIDO
    assert all(simulacion.pacientes[i].estado == "Interrumpido" for i in [1, 2, 3])
    assert simulacion.fin_vacunacion == float("inf")
    assert simulacion.restante_vacunacion > 0

    simulacion.reloj = simulacion.fin_interrupcion
    simulacion.procesar_fin_interrupcion()

    assert simulacion.enfermero_estado == "Ocupado"
    assert all(simulacion.pacientes[i].estado == "En vacunacion" for i in [1, 2, 3])


def probar_porcentajes_gripe_sobre_dosis_procesadas():
    simulacion = Simulacion(Parametros())
    simulacion.gripe_vacunados = 8
    simulacion.dosis_gripe_descartadas = 2
    simulacion.gripe_llegados = 100
    estadisticas = dict(simulacion.estadisticas())

    assert estadisticas["Porcentaje de Vacunas de gripe aplicadas"] == 80
    assert estadisticas["Porcentaje de Vacunas de Gripe Vencidas"] == 20


def probar_utilizacion_usa_tiempo_real_transcurrido():
    simulacion = Simulacion(Parametros(tiempo_simulacion=1000))
    simulacion.reloj = 100
    simulacion.tiempo_ocupado = 25

    assert buscar_estadistica(
        {"estadisticas": simulacion.estadisticas()},
        "Porcentaje de utilizacion enfermero",
    ) == 25


if __name__ == "__main__":
    probar_filtro_i_j_y_fila_final()
    probar_fila_final_se_muestra_aunque_no_caiga_en_rango()
    probar_interrupcion_exactamente_en_x_no_se_procesa()
    probar_corte_por_max_iteraciones()
    probar_parametros_de_caja_y_tiempo()
    probar_runge_kutta_configurable()
    probar_vector_muestra_atributos_de_pacientes_presentes()
    probar_interrupcion_parametrizable()
    probar_gripe_atiende_todos_los_pacientes_en_cola()
    probar_gripe_abre_otra_caja_y_atiende_completo_si_faltan_dosis()
    probar_gripe_abre_varias_cajas_si_el_parametro_es_chico()
    probar_columnas_de_pacientes_muestran_tipo_e_id_real()
    probar_paginacion_limita_columnas_sin_perder_ids()
    probar_interrupcion_exponencial_muestra_rnd()
    probar_interrupcion_descartada_no_modifica_la_actual()
    probar_tiempo_interrumpido_se_acumula_con_el_reloj()
    probar_interrupcion_pausa_lote_y_marca_pacientes()
    probar_porcentajes_gripe_sobre_dosis_procesadas()
    probar_utilizacion_usa_tiempo_real_transcurrido()
    print("Todas las pruebas pasaron correctamente.")
