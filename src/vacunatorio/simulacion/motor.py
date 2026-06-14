import random
from dataclasses import dataclass, field

from src.vacunatorio.config.constantes import (
    COVID,
    EVENTO_FIN_INTERRUPCION,
    EVENTO_FIN_MAX_ITERACIONES,
    EVENTO_FIN_SIMULACION,
    EVENTO_FIN_VACUNACION,
    EVENTO_INICIALIZACION,
    EVENTO_INICIO_INTERRUPCION,
    EVENTO_LLEGADA_COVID,
    EVENTO_LLEGADA_GRIPE,
    EVENTO_VENCIMIENTO_GRIPE,
    GRIPE,
    INFINITO,
)
from src.vacunatorio.config.parametros import validar_parametros
from src.vacunatorio.dominio.modelos import Paciente
from src.vacunatorio.simulacion.runge_kutta import calcular_runge_kutta
from src.vacunatorio.utils.utilidades import grupo_uniforme_1_a_4, tiempo_exponencial


@dataclass
class Simulacion:
    p: object
    reloj: float = 0.0
    iteracion: int = 0
    rng: random.Random = field(init=False)
    pacientes: dict = field(default_factory=dict)
    cola_covid: list = field(default_factory=list)
    cola_gripe: list = field(default_factory=list)

    enfermero_estado: str = "Libre"
    lote_actual_tipo: str = ""
    lote_actual_pacientes: list = field(default_factory=list)
    fin_vacunacion: float = INFINITO
    restante_vacunacion: float = 0.0
    proxima_preferencia: str = COVID

    dosis_gripe_abiertas: int = 0
    vencimiento_gripe: float = INFINITO
    caja_gripe_id: int = 0

    proxima_llegada_covid: float = INFINITO
    proxima_llegada_gripe: float = INFINITO
    proxima_interrupcion: float = INFINITO
    fin_interrupcion: float = INFINITO

    id_paciente: int = 0
    covid_llegados: int = 0
    gripe_llegados: int = 0
    covid_vacunados: int = 0
    gripe_vacunados: int = 0
    dosis_gripe_descartadas: int = 0
    cajas_covid_abiertas: int = 0
    cajas_gripe_abiertas: int = 0
    interrupciones: int = 0
    tiempo_interrumpido: float = 0.0
    tiempo_ocupado: float = 0.0
    ultima_actualizacion_ocupacion: float = 0.0
    suma_espera_covid: float = 0.0
    suma_espera_gripe: float = 0.0
    max_cola_covid: int = 0
    max_cola_gripe: int = 0

    filas: list = field(default_factory=list)
    tabla_rk: list = field(default_factory=list)
    tiempo_vencimiento_gripe: float = 0.0

    def __post_init__(self):
        validar_parametros(self.p)
        self.rng = random.Random(self.p.semilla)
        self.tabla_rk, self.tiempo_vencimiento_gripe = calcular_runge_kutta(self.p)

    def simular(self):
        self.inicializar()

        while self.iteracion < self.p.max_iteraciones:
            evento, tiempo_evento = self.proximo_evento()

            if tiempo_evento == INFINITO or tiempo_evento >= self.p.tiempo_simulacion:
                self.finalizar_en_tiempo_x()
                break

            self.avanzar_reloj(tiempo_evento)
            self.iteracion += 1
            self.procesar_evento(evento)

            if self.reloj >= self.p.tiempo_simulacion:
                self.agregar_fila_final_si_falta()
                break

        if self.iteracion >= self.p.max_iteraciones and self.reloj < self.p.tiempo_simulacion:
            self.agregar_fila(EVENTO_FIN_MAX_ITERACIONES, mostrar_objetos=False)

        return {
            "filas": self.filas,
            "estadisticas": self.estadisticas(),
            "rk": self.tabla_rk,
        }

    def inicializar(self):
        rnd_covid = self.rnd()
        rnd_gripe = self.rnd()
        self.proxima_llegada_covid = tiempo_exponencial(self.p.media_llegada_covid, rnd_covid)
        self.proxima_llegada_gripe = tiempo_exponencial(self.p.media_llegada_gripe, rnd_gripe)
        self.proxima_interrupcion = self.p.intervalo_interrupcion
        self.agregar_fila(
            EVENTO_INICIALIZACION,
            rnd_llegada_covid=rnd_covid,
            tiempo_llegada_covid=self.proxima_llegada_covid,
            rnd_llegada_gripe=rnd_gripe,
            tiempo_llegada_gripe=self.proxima_llegada_gripe,
        )

    def rnd(self):
        return min(0.999999999, max(0.000000001, self.rng.random()))

    def proximo_evento(self):
        eventos = [
            (EVENTO_LLEGADA_COVID, self.proxima_llegada_covid),
            (EVENTO_LLEGADA_GRIPE, self.proxima_llegada_gripe),
            (EVENTO_FIN_VACUNACION, self.fin_vacunacion),
            (EVENTO_INICIO_INTERRUPCION, self.proxima_interrupcion),
            (EVENTO_FIN_INTERRUPCION, self.fin_interrupcion),
            (EVENTO_VENCIMIENTO_GRIPE, self.vencimiento_gripe),
        ]
        return min(eventos, key=lambda item: item[1])

    def avanzar_reloj(self, nuevo_reloj):
        if self.enfermero_estado == "Ocupado":
            self.tiempo_ocupado += nuevo_reloj - self.ultima_actualizacion_ocupacion
        self.ultima_actualizacion_ocupacion = nuevo_reloj
        self.reloj = nuevo_reloj

    def finalizar_en_tiempo_x(self):
        self.avanzar_reloj(self.p.tiempo_simulacion)
        self.iteracion += 1
        self.agregar_fila(EVENTO_FIN_SIMULACION, mostrar_objetos=False)

    def agregar_fila_final_si_falta(self):
        if not self.filas or self.filas[-1]["Evento"] != EVENTO_FIN_SIMULACION:
            self.agregar_fila(EVENTO_FIN_SIMULACION, mostrar_objetos=False)

    def procesar_evento(self, evento):
        if evento == EVENTO_LLEGADA_COVID:
            self.procesar_llegada(COVID)
        elif evento == EVENTO_LLEGADA_GRIPE:
            self.procesar_llegada(GRIPE)
        elif evento == EVENTO_FIN_VACUNACION:
            self.procesar_fin_vacunacion()
        elif evento == EVENTO_INICIO_INTERRUPCION:
            self.procesar_inicio_interrupcion()
        elif evento == EVENTO_FIN_INTERRUPCION:
            self.procesar_fin_interrupcion()
        elif evento == EVENTO_VENCIMIENTO_GRIPE:
            self.procesar_vencimiento_gripe()

    def procesar_llegada(self, vacuna):
        rnd_grupo = self.rnd()
        grupo = grupo_uniforme_1_a_4(rnd_grupo)
        pacientes_nuevos = self.crear_pacientes(vacuna, grupo)

        self.max_cola_covid = max(self.max_cola_covid, len(self.cola_covid))
        self.max_cola_gripe = max(self.max_cola_gripe, len(self.cola_gripe))

        if vacuna == COVID:
            rnd_llegada = self.rnd()
            intervalo = tiempo_exponencial(self.p.media_llegada_covid, rnd_llegada)
            self.proxima_llegada_covid = self.reloj + intervalo
            self.intentar_iniciar_vacunacion()
            self.agregar_fila(
                EVENTO_LLEGADA_COVID,
                rnd_grupo=rnd_grupo,
                grupo=grupo,
                rnd_llegada_covid=rnd_llegada,
                tiempo_llegada_covid=intervalo,
                pacientes_evento=pacientes_nuevos,
            )
        else:
            rnd_llegada = self.rnd()
            intervalo = tiempo_exponencial(self.p.media_llegada_gripe, rnd_llegada)
            self.proxima_llegada_gripe = self.reloj + intervalo
            self.intentar_iniciar_vacunacion()
            self.agregar_fila(
                EVENTO_LLEGADA_GRIPE,
                rnd_grupo=rnd_grupo,
                grupo=grupo,
                rnd_llegada_gripe=rnd_llegada,
                tiempo_llegada_gripe=intervalo,
                pacientes_evento=pacientes_nuevos,
            )

    def crear_pacientes(self, vacuna, grupo):
        pacientes_nuevos = []
        for _ in range(grupo):
            self.id_paciente += 1
            paciente = Paciente(self.id_paciente, vacuna, self.reloj, grupo)
            self.pacientes[paciente.id] = paciente
            pacientes_nuevos.append(paciente.id)

            if vacuna == COVID:
                self.cola_covid.append(paciente.id)
                self.covid_llegados += 1
            else:
                self.cola_gripe.append(paciente.id)
                self.gripe_llegados += 1

        return pacientes_nuevos

    def procesar_fin_vacunacion(self):
        tipo = self.lote_actual_tipo
        cantidad = len(self.lote_actual_pacientes)

        for paciente_id in self.lote_actual_pacientes:
            paciente = self.pacientes[paciente_id]
            paciente.estado = "Vacunado"
            espera = paciente.inicio_vacunacion - paciente.llegada
            if tipo == COVID:
                self.suma_espera_covid += max(0, espera)
            else:
                self.suma_espera_gripe += max(0, espera)
            del self.pacientes[paciente_id]

        if tipo == COVID:
            self.covid_vacunados += cantidad
        elif tipo == GRIPE:
            self.gripe_vacunados += cantidad

        self.enfermero_estado = "Libre"
        self.lote_actual_tipo = ""
        self.lote_actual_pacientes = []
        self.fin_vacunacion = INFINITO
        self.restante_vacunacion = 0.0

        self.intentar_iniciar_vacunacion()
        self.agregar_fila(EVENTO_FIN_VACUNACION)

    def procesar_inicio_interrupcion(self):
        self.interrupciones += 1
        self.tiempo_interrumpido += self.p.duracion_interrupcion
        self.proxima_interrupcion = self.reloj + self.p.intervalo_interrupcion
        self.fin_interrupcion = self.reloj + self.p.duracion_interrupcion

        if self.enfermero_estado == "Ocupado":
            self.restante_vacunacion = self.fin_vacunacion - self.reloj
            self.fin_vacunacion = INFINITO

        self.enfermero_estado = "Interrumpido"
        self.agregar_fila(EVENTO_INICIO_INTERRUPCION)

    def procesar_fin_interrupcion(self):
        self.fin_interrupcion = INFINITO

        if self.lote_actual_pacientes and self.restante_vacunacion > 0:
            self.enfermero_estado = "Ocupado"
            self.fin_vacunacion = self.reloj + self.restante_vacunacion
            self.restante_vacunacion = 0.0
        else:
            self.enfermero_estado = "Libre"
            self.intentar_iniciar_vacunacion()

        self.agregar_fila(EVENTO_FIN_INTERRUPCION)

    def procesar_vencimiento_gripe(self):
        descartadas = self.dosis_gripe_abiertas
        self.dosis_gripe_descartadas += descartadas
        self.dosis_gripe_abiertas = 0
        self.vencimiento_gripe = INFINITO
        self.agregar_fila(EVENTO_VENCIMIENTO_GRIPE, dosis_descartadas_evento=descartadas)
        self.intentar_iniciar_vacunacion()

    def abrir_caja_gripe_si_hace_falta(self):
        if self.dosis_gripe_abiertas == 0 and self.cola_gripe:
            self.caja_gripe_id += 1
            self.cajas_gripe_abiertas += 1
            self.dosis_gripe_abiertas = self.p.dosis_caja_gripe
            self.vencimiento_gripe = self.reloj + self.tiempo_vencimiento_gripe

    def intentar_iniciar_vacunacion(self):
        if self.enfermero_estado != "Libre":
            return

        if self.proxima_preferencia == COVID:
            if self.iniciar_lote_covid():
                return
            self.iniciar_lote_gripe()
        else:
            if self.iniciar_lote_gripe():
                return
            self.iniciar_lote_covid()

    def iniciar_lote_covid(self):
        cantidad = (len(self.cola_covid) // self.p.dosis_caja_covid) * self.p.dosis_caja_covid
        if cantidad <= 0:
            return False

        self.lote_actual_pacientes = [self.cola_covid.pop(0) for _ in range(cantidad)]
        self.lote_actual_tipo = COVID
        self.cajas_covid_abiertas += cantidad // self.p.dosis_caja_covid
        self.enfermero_estado = "Ocupado"
        self.fin_vacunacion = self.reloj + self.p.tiempo_por_paciente * cantidad
        self.proxima_preferencia = GRIPE
        self.marcar_lote_en_vacunacion()
        return True

    def iniciar_lote_gripe(self):
        if not self.cola_gripe:
            return False

        self.abrir_caja_gripe_si_hace_falta()
        cantidad = min(len(self.cola_gripe), self.dosis_gripe_abiertas)
        if cantidad <= 0:
            return False

        self.lote_actual_pacientes = [self.cola_gripe.pop(0) for _ in range(cantidad)]
        self.lote_actual_tipo = GRIPE
        self.dosis_gripe_abiertas -= cantidad
        if self.dosis_gripe_abiertas == 0:
            self.vencimiento_gripe = INFINITO

        self.enfermero_estado = "Ocupado"
        self.fin_vacunacion = self.reloj + self.p.tiempo_por_paciente * cantidad
        self.proxima_preferencia = COVID
        self.marcar_lote_en_vacunacion()
        return True

    def marcar_lote_en_vacunacion(self):
        for paciente_id in self.lote_actual_pacientes:
            self.pacientes[paciente_id].estado = "En vacunacion"
            self.pacientes[paciente_id].inicio_vacunacion = self.reloj

    def agregar_fila(self, evento, mostrar_objetos=True, **extras):
        guardar = (
            self.p.mostrar_desde
            <= self.iteracion
            < self.p.mostrar_desde + self.p.mostrar_cantidad
        )
        es_fila_final = evento in {EVENTO_FIN_SIMULACION, EVENTO_FIN_MAX_ITERACIONES}
        if not guardar and not es_fila_final:
            return

        fila = {
            "Iteracion": self.iteracion,
            "Reloj (seg)": self.reloj,
            "Evento": evento,
            "RND llegada COVID": extras.get("rnd_llegada_covid", "-"),
            "Tiempo llegada COVID": extras.get("tiempo_llegada_covid", "-"),
            "Prox llegada COVID": self.proxima_llegada_covid,
            "RND llegada gripe": extras.get("rnd_llegada_gripe", "-"),
            "Tiempo llegada gripe": extras.get("tiempo_llegada_gripe", "-"),
            "Prox llegada gripe": self.proxima_llegada_gripe,
            "RND grupo llegada": extras.get("rnd_grupo", "-"),
            "Tam grupo llegada": extras.get("grupo", "-"),
            "Cola COVID": len(self.cola_covid),
            "Cola gripe": len(self.cola_gripe),
            "Estado enfermero": self.enfermero_estado,
            "Lote actual": self.lote_actual_tipo or "-",
            "Pacientes lote": len(self.lote_actual_pacientes),
            "Fin vacunacion": self.fin_vacunacion,
            "Preferencia prox": self.proxima_preferencia,
            "Dosis gripe abiertas": self.dosis_gripe_abiertas,
            "Vencimiento gripe": self.vencimiento_gripe,
            "Dosis descartadas evento": extras.get("dosis_descartadas_evento", 0),
            "Prox interrupcion": self.proxima_interrupcion,
            "Fin interrupcion": self.fin_interrupcion,
            "COVID llegados": self.covid_llegados,
            "Gripe llegados": self.gripe_llegados,
            "COVID vacunados": self.covid_vacunados,
            "Gripe vacunados": self.gripe_vacunados,
            "Cajas COVID": self.cajas_covid_abiertas,
            "Cajas gripe": self.cajas_gripe_abiertas,
            "Dosis gripe descartadas": self.dosis_gripe_descartadas,
            "Pacientes presentes": len(self.pacientes) if mostrar_objetos else "-",
            "Detalle pacientes": self.descripcion_pacientes_presentes() if mostrar_objetos else "-",
            "_objetos": self.objetos_pacientes_presentes() if mostrar_objetos else [],
        }
        self.filas.append(fila)

    def descripcion_pacientes_presentes(self):
        partes = []
        for paciente in self.pacientes.values():
            partes.append(
                f"ID {paciente.id} {paciente.vacuna} {paciente.estado} "
                f"lleg={paciente.llegada:.1f} grupo={paciente.grupo}"
            )
        return " | ".join(partes) if partes else "-"

    def objetos_pacientes_presentes(self):
        objetos = []
        for paciente in self.pacientes.values():
            objetos.append(
                {
                    "ID": paciente.id,
                    "Vacuna": paciente.vacuna,
                    "Estado": paciente.estado,
                    "Llegada (seg)": paciente.llegada,
                    "Grupo": paciente.grupo,
                    "Inicio vacunacion": paciente.inicio_vacunacion if paciente.inicio_vacunacion else "-",
                }
            )
        return objetos

    def estadisticas(self):
        total_vacunados = self.covid_vacunados + self.gripe_vacunados
        total_llegados = self.covid_llegados + self.gripe_llegados
        return [
            ("Personas COVID llegadas", self.covid_llegados),
            ("Personas gripe llegadas", self.gripe_llegados),
            ("Personas COVID vacunadas", self.covid_vacunados),
            ("Personas gripe vacunadas", self.gripe_vacunados),
            ("Espera promedio COVID (seg)", self.suma_espera_covid / self.covid_vacunados if self.covid_vacunados else 0),
            ("Espera promedio gripe (seg)", self.suma_espera_gripe / self.gripe_vacunados if self.gripe_vacunados else 0),
            ("Porcentaje de utilizacion enfermero", 100 * self.tiempo_ocupado / self.p.tiempo_simulacion),
            ("Porcentaje de pacientes vacunados", 100 * total_vacunados / total_llegados if total_llegados else 0),
            ("Maxima cola COVID", self.max_cola_covid),
            ("Maxima cola gripe", self.max_cola_gripe),
            ("Cajas COVID abiertas", self.cajas_covid_abiertas),
            ("Cajas gripe abiertas", self.cajas_gripe_abiertas),
            ("Dosis gripe descartadas", self.dosis_gripe_descartadas),
            ("Interrupciones ocurridas", self.interrupciones),
            ("Tiempo total interrumpido (seg)", self.tiempo_interrumpido),
            ("Tiempo vencimiento gripe por RK (seg)", self.tiempo_vencimiento_gripe),
        ]
