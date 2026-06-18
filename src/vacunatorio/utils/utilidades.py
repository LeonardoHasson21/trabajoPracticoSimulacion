import math

from src.vacunatorio.config.constantes import INFINITO


def formatear_numero(valor, decimales=4):
    if valor is None or valor == "":
        return "-"
    if valor == INFINITO:
        return "-"
    if isinstance(valor, int):
        return str(valor)
    if isinstance(valor, float):
        return f"{valor:.{decimales}f}"
    return str(valor)


def tiempo_exponencial(media_segundos, rnd):
    return -media_segundos * math.log(1 - rnd)


def grupo_uniforme_1_a_4(rnd):
    return min(4, int(rnd * 4) + 1)
