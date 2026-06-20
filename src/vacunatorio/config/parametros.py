from dataclasses import dataclass

from src.vacunatorio.config.constantes import COEFICIENTE_RK_DERECHO, COEFICIENTE_RK_IZQUIERDO


@dataclass
class Parametros:
    tiempo_simulacion: float = 8 * 60 * 60
    max_iteraciones: int = 100000
    mostrar_desde: int = 0
    mostrar_cantidad: int = 200
    semilla: int = 12345

    media_llegada_covid: float = 225.0
    media_llegada_gripe: float = 300.0
    dosis_caja_covid: int = 5
    dosis_caja_gripe: int = 10
    tiempo_por_paciente: float = 22.0

    media_interrupcion: float = 3600.0
    duracion_interrupcion: float = 300.0

    rk_r_inicial: float = 1.0
    rk_t_inicial: float = 0.0
    rk_t_final: float = 0.2
    rk_paso: float = 0.01
    rk_coef_r: float = COEFICIENTE_RK_IZQUIERDO - COEFICIENTE_RK_DERECHO
    rk_coef_t: float = 0.0
    rk_constante: float = 0.0


def validar_parametros(p):
    if p.max_iteraciones < 1 or p.max_iteraciones > 100000:
        raise ValueError("El maximo de iteraciones debe estar entre 1 y 100000.")
    if p.tiempo_simulacion <= 0:
        raise ValueError("El tiempo de simulacion debe ser mayor a cero.")
    if p.mostrar_desde < 0 or p.mostrar_cantidad < 0:
        raise ValueError("Los parametros i y j no pueden ser negativos.")
    if p.media_llegada_covid <= 0 or p.media_llegada_gripe <= 0:
        raise ValueError("Las medias de llegada deben ser mayores a cero.")
    if p.dosis_caja_covid <= 0:
        raise ValueError("Las dosis por caja de COVID deben ser mayores a cero.")
    if p.dosis_caja_gripe <= 0:
        raise ValueError("Las dosis por caja de gripe deben ser mayores a cero.")
    if p.tiempo_por_paciente <= 0:
        raise ValueError("El tiempo por paciente debe ser mayor a cero.")
    if p.media_interrupcion <= 0:
        raise ValueError("La media de llegada de interrupciones debe ser mayor a cero.")
    if p.duracion_interrupcion < 0:
        raise ValueError("La duracion de la interrupcion no puede ser negativa.")
    if p.rk_paso <= 0:
        raise ValueError("El paso de Runge-Kutta debe ser mayor a cero.")
    if p.rk_t_final < p.rk_t_inicial:
        raise ValueError("El tiempo final de Runge-Kutta debe ser mayor o igual al inicial.")
