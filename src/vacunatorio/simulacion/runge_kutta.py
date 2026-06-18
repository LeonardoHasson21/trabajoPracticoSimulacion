def derivada_r(t, r, coef_r, coef_t, constante):
    return coef_r * r + coef_t * t + constante


def calcular_runge_kutta(parametros):
    """
    Resuelve por RK4:
        41,4 * R = dR/dt + 0,0575 * R

    Despeje:
        dR/dt = (41,4 - 0,0575) * R

    Planteo usado:
        dR/dt = 41,3425 * R + 0 * t + c, con c = 0

    El tiempo de vencimiento se toma como el valor maximo de R dentro del
    intervalo calculado. Los coeficientes de R, t y la constante son editables
    desde la interfaz para probar otros valores, incluso negativos.
    """
    filas = []
    t = parametros.rk_t_inicial
    r = parametros.rk_r_inicial
    h = parametros.rk_paso
    coef_r = parametros.rk_coef_r
    coef_t = parametros.rk_coef_t
    constante = parametros.rk_constante
    maximo = r
    indice = 0

    while t <= parametros.rk_t_final + 1e-12 and indice < 10000:
        k1 = derivada_r(t, r, coef_r, coef_t, constante)
        r_k1 = r + h / 2 * k1
        t_k2 = t + h / 2
        k2 = derivada_r(t_k2, r_k1, coef_r, coef_t, constante)
        r_k2 = r + h / 2 * k2
        t_k3 = t + h / 2
        k3 = derivada_r(t_k3, r_k2, coef_r, coef_t, constante)
        r_k3 = r + h * k3
        t_k4 = t + h
        k4 = derivada_r(t_k4, r_k3, coef_r, coef_t, constante)
        t_siguiente = t + h
        r_siguiente = r + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)

        filas.append(
            {
                "t": t,
                "E": r,
                "K1": k1,
                "E+H/2*K1": r_k1,
                "t+H/2 K2": t_k2,
                "K2": k2,
                "E+H/2*K2": r_k2,
                "t+H/2 K3": t_k3,
                "K3": k3,
                "E+H*K3": r_k3,
                "t+H": t_k4,
                "K4": k4,
                "t(i+1)": t_siguiente,
                "E(i+1)": r_siguiente,
            }
        )

        maximo = max(maximo, r)
        t += h
        r = r_siguiente
        indice += 1

    maximo = max(maximo, r)
    return filas, maximo
