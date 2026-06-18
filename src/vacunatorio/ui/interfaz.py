import csv
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from src.vacunatorio.config.constantes import COVID, GRIPE
from src.vacunatorio.config.parametros import Parametros, validar_parametros
from src.vacunatorio.simulacion.motor import Simulacion
from src.vacunatorio.utils.utilidades import formatear_numero


NEGRO = "#000000"
BLANCO = "#ffffff"
AZUL_OSCURO = BLANCO
AMARILLO = BLANCO
VERDE = BLANCO
VERDE_SERVIDOR = BLANCO
AZUL = BLANCO
MAGENTA = BLANCO
NARANJA = BLANCO
CELESTE = BLANCO
ROJO = BLANCO
ROSA = BLANCO
AZUL_ESTADISTICAS = BLANCO
AMARILLO_PACIENTE = BLANCO
ROSA_PACIENTE = BLANCO
TEXTO_OSCURO = NEGRO
BORDE_TABLA = NEGRO


def hoja(identificador, texto, ancho, color, texto_color=NEGRO):
    return {
        "id": identificador,
        "texto": texto,
        "ancho": ancho,
        "color": BLANCO,
        "texto_color": NEGRO,
    }


def grupo(texto, color, hijos, texto_color=TEXTO_OSCURO):
    return {
        "texto": texto,
        "color": BLANCO,
        "texto_color": NEGRO,
        "hijos": hijos,
    }


class TablaEncabezadoAgrupado:
    alturas = (22, 25, 25)

    def __init__(self, padre, alto=15):
        self.marco = ttk.Frame(padre)
        self.marco.pack(fill="both", expand=True)
        self.columnas = []

        alto_encabezado = sum(self.alturas)
        self.encabezado = tk.Canvas(
            self.marco,
            height=alto_encabezado,
            bg=BLANCO,
            highlightthickness=0,
        )
        self.tabla = ttk.Treeview(self.marco, show="", height=alto)
        self.scroll_y = ttk.Scrollbar(self.marco, orient="vertical", command=self.tabla.yview)
        self.scroll_x = ttk.Scrollbar(self.marco, orient="horizontal", command=self.mover_horizontal)

        self.tabla.configure(
            yscrollcommand=self.scroll_y.set,
            xscrollcommand=self.actualizar_scroll_horizontal,
        )

        self.encabezado.grid(row=0, column=0, sticky="ew")
        self.tabla.grid(row=1, column=0, sticky="nsew")
        self.scroll_y.grid(row=1, column=1, sticky="ns")
        self.scroll_x.grid(row=2, column=0, sticky="ew")
        self.marco.rowconfigure(1, weight=1)
        self.marco.columnconfigure(0, weight=1)

    def bind(self, *args, **kwargs):
        return self.tabla.bind(*args, **kwargs)

    def selection(self):
        return self.tabla.selection()

    def insert(self, *args, **kwargs):
        return self.tabla.insert(*args, **kwargs)

    def delete(self, *items):
        if items:
            return self.tabla.delete(*items)
        hijos = self.tabla.get_children()
        if hijos:
            return self.tabla.delete(*hijos)
        return None

    def get_children(self):
        return self.tabla.get_children()

    def configurar_columnas(self, grupos):
        self.delete()
        self.columnas = self.extraer_hojas(grupos)
        identificadores = [columna["id"] for columna in self.columnas]
        self.tabla["columns"] = identificadores
        for columna in self.columnas:
            self.tabla.column(
                columna["id"],
                width=columna["ancho"],
                minwidth=columna["ancho"],
                anchor="center",
                stretch=False,
            )
        self.dibujar_encabezado(grupos)

    def mover_horizontal(self, *args):
        self.tabla.xview(*args)
        self.encabezado.xview(*args)

    def actualizar_scroll_horizontal(self, primero, ultimo):
        self.scroll_x.set(primero, ultimo)
        self.encabezado.xview_moveto(primero)

    def extraer_hojas(self, nodos):
        hojas = []
        for nodo in nodos:
            if "hijos" in nodo:
                hojas.extend(self.extraer_hojas(nodo["hijos"]))
            else:
                hojas.append(nodo)
        return hojas

    def ancho_nodo(self, nodo):
        if "hijos" not in nodo:
            return nodo["ancho"]
        return sum(self.ancho_nodo(hijo) for hijo in nodo["hijos"])

    def dibujar_encabezado(self, grupos):
        self.encabezado.delete("all")
        x = 0
        for nodo in grupos:
            self.dibujar_nodo(nodo, x, 0)
            x += self.ancho_nodo(nodo)

        alto = sum(self.alturas)
        self.encabezado.configure(scrollregion=(0, 0, x, alto))

    def dibujar_nodo(self, nodo, x, nivel):
        ancho = self.ancho_nodo(nodo)
        y = sum(self.alturas[:nivel])

        if "hijos" in nodo:
            alto = self.alturas[nivel]
        else:
            alto = sum(self.alturas[nivel:])

        self.encabezado.create_rectangle(
            x,
            y,
            x + ancho,
            y + alto,
            fill=nodo["color"],
            outline=BORDE_TABLA,
            width=1,
        )
        fuente = ("Segoe UI", 9, "bold") if "hijos" in nodo or nivel == 0 else ("Segoe UI", 9)
        self.encabezado.create_text(
            x + ancho / 2,
            y + alto / 2,
            text=nodo["texto"],
            fill=nodo.get("texto_color", TEXTO_OSCURO),
            font=fuente,
            width=max(24, ancho - 6),
            justify="center",
        )

        if "hijos" in nodo:
            x_hijo = x
            for hijo in nodo["hijos"]:
                self.dibujar_nodo(hijo, x_hijo, nivel + 1)
                x_hijo += self.ancho_nodo(hijo)


class Aplicacion(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simulacion Vacunatorio")
        self.geometry("1500x820")
        self.minsize(1200, 700)
        self.resultado = None
        self.filas_vector_actuales = []
        self.variables = {}
        self.crear_interfaz()

    def crear_interfaz(self):
        contenedor = ttk.Frame(self, padding=10)
        contenedor.pack(fill="both", expand=True)

        panel_parametros = ttk.Frame(contenedor)
        panel_parametros.pack(side="left", fill="y", padx=(0, 10))

        ttk.Label(panel_parametros, text="Parametros", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.crear_campos(panel_parametros)

        ttk.Button(panel_parametros, text="Simular", command=self.ejecutar_simulacion).pack(fill="x", pady=(12, 4))
        ttk.Button(panel_parametros, text="Exportar vector CSV", command=self.exportar_csv).pack(fill="x")

        notas = (
            "RK: 41,4 * R = dR/dt + 0,0575 * R.\n"
            "Se plantea como dR/dt = a * R + b * t + c.\n"
            "La interrupcion periodica pausa al enfermero."
        )
        ttk.Label(panel_parametros, text=notas, justify="left").pack(anchor="w", pady=12)

        panel_resultados = ttk.Notebook(contenedor)
        panel_resultados.pack(side="right", fill="both", expand=True)

        self.tab_vector = ttk.Frame(panel_resultados)
        self.tab_estadisticas = ttk.Frame(panel_resultados)
        self.tab_rk = ttk.Frame(panel_resultados)
        panel_resultados.add(self.tab_vector, text="Vector de estado")
        panel_resultados.add(self.tab_estadisticas, text="Estadisticas")
        panel_resultados.add(self.tab_rk, text="Runge-Kutta")

        self.crear_panel_vector()
        self.tabla_estadisticas = self.crear_tabla(self.tab_estadisticas)
        self.tabla_rk = self.crear_tabla(self.tab_rk)

    def crear_panel_vector(self):
        panel_superior = ttk.Frame(self.tab_vector)
        panel_superior.pack(fill="both", expand=True)

        ttk.Label(panel_superior, text="Vector de estado").pack(anchor="w")
        self.tabla_vector = TablaEncabezadoAgrupado(panel_superior)
        self.tabla_vector.bind("<<TreeviewSelect>>", self.mostrar_detalle_pacientes)

        panel_detalle = ttk.LabelFrame(self.tab_vector, text="Detalle de pacientes de la fila seleccionada", padding=6)
        panel_detalle.pack(fill="both", expand=True, pady=(8, 0))

        self.texto_detalle = tk.StringVar(value="Seleccione una fila para ver los pacientes presentes.")
        ttk.Label(panel_detalle, textvariable=self.texto_detalle).pack(anchor="center", pady=(0, 4))
        self.tabla_detalle_pacientes = self.crear_tabla(panel_detalle, alto=8)

    def crear_campos(self, padre):
        grupos = [
            ("Simulacion", [
                ("tiempo_simulacion", "Tiempo X simulacion (seg)", 28800),
                ("max_iteraciones", "Max iteraciones", 100000),
                ("mostrar_desde", "Mostrar desde iteracion j", 0),
                ("mostrar_cantidad", "Mostrar cantidad i", 200),
                ("semilla", "Semilla", 12345),
            ]),
            ("Llegadas y vacunas", [
                ("media_llegada_covid", "Media llegada COVID (seg)", 225),
                ("media_llegada_gripe", "Media llegada gripe (seg)", 300),
                ("dosis_caja_covid", "Dosis caja COVID", 5),
                ("dosis_caja_gripe", "Dosis caja gripe", 10),
                ("tiempo_por_paciente", "Segundos por paciente", 22),
            ]),
            ("Interrupcion", [
                ("intervalo_interrupcion", "Cada cuantos seg ocurre", 3600),
                ("duracion_interrupcion", "Duracion interrupcion (seg)", 300),
            ]),
            ("Runge-Kutta", [
                ("rk_r_inicial", "Dependiente R inicial", 1),
                ("rk_t_inicial", "Independiente t inicial", 0),
                ("rk_t_final", "Independiente t final", 0.2),
                ("rk_paso", "Paso h", 0.01),
                ("rk_coef_r", "Coeficiente a de R", 41.3425),
                ("rk_coef_t", "Coeficiente b de t", 0),
                ("rk_constante", "Constante c", 0),
            ]),
        ]

        for titulo, campos in grupos:
            marco = ttk.LabelFrame(padre, text=titulo, padding=8)
            marco.pack(fill="x", pady=4)
            for atributo, etiqueta, valor in campos:
                fila = ttk.Frame(marco)
                fila.pack(fill="x", pady=2)
                ttk.Label(fila, text=etiqueta, width=28).pack(side="left")
                variable = tk.StringVar(value=str(valor))
                self.variables[atributo] = variable
                ttk.Entry(fila, textvariable=variable, width=12).pack(side="right")

    def leer_parametros(self):
        p = Parametros()
        enteros = {
            "max_iteraciones",
            "mostrar_desde",
            "mostrar_cantidad",
            "semilla",
            "dosis_caja_covid",
            "dosis_caja_gripe",
        }
        for atributo, variable in self.variables.items():
            texto = variable.get().replace(",", ".")
            valor = int(float(texto)) if atributo in enteros else float(texto)
            setattr(p, atributo, valor)
        validar_parametros(p)
        return p

    def ejecutar_simulacion(self):
        try:
            parametros = self.leer_parametros()
            simulacion = Simulacion(parametros)
            self.resultado = simulacion.simular()
            self.cargar_vector(self.resultado["filas"])
            self.cargar_estadisticas(self.resultado["estadisticas"])
            self.cargar_rk(self.resultado["rk"])
        except Exception as error:
            messagebox.showerror("No se pudo simular", str(error))

    def crear_tabla(self, padre, alto=15):
        marco = ttk.Frame(padre)
        marco.pack(fill="both", expand=True)
        tabla = ttk.Treeview(marco, show="headings", height=alto)
        scroll_y = ttk.Scrollbar(marco, orient="vertical", command=tabla.yview)
        scroll_x = ttk.Scrollbar(marco, orient="horizontal", command=tabla.xview)
        tabla.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        tabla.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        marco.rowconfigure(0, weight=1)
        marco.columnconfigure(0, weight=1)
        return tabla

    def configurar_columnas(self, tabla, columnas):
        tabla.delete(*tabla.get_children())
        tabla["columns"] = columnas
        for columna in columnas:
            ancho = self.ancho_columna(columna)
            tabla.heading(columna, text=columna)
            tabla.column(columna, width=ancho, minwidth=ancho, anchor="center", stretch=False)

    def configurar_columnas_con_titulos(self, tabla, columnas):
        tabla.delete(*tabla.get_children())
        identificadores = [identificador for identificador, _titulo in columnas]
        tabla["columns"] = identificadores
        for identificador, titulo in columnas:
            ancho = self.ancho_columna(titulo)
            tabla.heading(identificador, text=titulo)
            tabla.column(identificador, width=ancho, minwidth=ancho, anchor="center", stretch=False)

    def ancho_columna(self, columna):
        anchos_especiales = {
            "Iteracion": 78,
            "Reloj (seg)": 96,
            "Evento": 150,
            "Estado enfermero": 142,
            "Pacientes presentes": 142,
            "RND grupo llegada": 132,
            "Tam grupo llegada": 132,
            "Dosis descartadas evento": 170,
            "Estadistica": 250,
            "Valor": 140,
            "Inicio vacunacion": 128,
            "E+H/2*K1": 112,
            "E+H/2*K2": 112,
            "E+H*K3": 100,
            "t(i+1)": 88,
            "E(i+1)": 88,
        }
        if columna in anchos_especiales:
            return anchos_especiales[columna]
        return max(72, len(columna) * 8 + 18)

    def cargar_vector(self, filas):
        if not filas:
            self.filas_vector_actuales = []
            self.tabla_vector.configurar_columnas([hoja("Estado", "ESTADO", 300, AMARILLO)])
            self.tabla_vector.insert("", "end", values=["No hay filas para el rango solicitado"])
            self.limpiar_detalle_pacientes()
            return

        encabezado = self.construir_encabezado_vector(filas)
        columnas = self.columnas_de_encabezado(encabezado)
        self.tabla_vector.configurar_columnas(encabezado)
        self.filas_vector_actuales = filas
        for indice, fila in enumerate(filas):
            valores = [formatear_numero(self.valor_vector(fila, columna["id"])) for columna in columnas]
            self.tabla_vector.insert("", "end", iid=str(indice), values=valores)
        self.limpiar_detalle_pacientes()

    def columnas_visibles(self, filas):
        encabezado = self.construir_encabezado_vector(filas)
        return [columna["id"] for columna in self.columnas_de_encabezado(encabezado)]

    def columnas_de_encabezado(self, encabezado):
        columnas = []
        for nodo in encabezado:
            if "hijos" in nodo:
                columnas.extend(self.columnas_de_encabezado(nodo["hijos"]))
            else:
                columnas.append(nodo)
        return columnas

    def construir_encabezado_vector(self, filas):
        pacientes_gripe = max(1, self.max_pacientes_en_filas(filas, GRIPE))
        pacientes_covid = max(1, self.max_pacientes_en_filas(filas, COVID))

        return [
            hoja("Iteracion", "ITERACION", 86, AMARILLO),
            hoja("Reloj (seg)", "RELOJ", 100, AMARILLO),
            hoja("Evento", "EVENTOS", 150, AMARILLO),
            grupo("EVENTOS", AZUL_OSCURO, [
                grupo("LLEGADA LOTE PACIENTES COVID", VERDE, [
                    hoja("RND llegada COVID", "Rnd", 86, VERDE),
                    hoja("Tiempo llegada COVID", "Tiempo", 96, VERDE),
                    hoja("Prox llegada COVID", "Seg prox\nllegada", 116, VERDE),
                ]),
                grupo("TAMANO DE GRUPO", MAGENTA, [
                    hoja("RND tam grupo COVID", "Rnd", 86, MAGENTA),
                    hoja("Tam grupo COVID", "Tamano", 90, MAGENTA),
                ]),
                grupo("LLEGADA LOTES PACIENTES GRIPE", AZUL, [
                    hoja("RND llegada gripe", "Rnd", 86, AZUL),
                    hoja("Tiempo llegada gripe", "Tiempo", 96, AZUL),
                    hoja("Prox llegada gripe", "Seg prox\nllegada", 116, AZUL),
                ]),
                grupo("TAMANO DE GRUPO", MAGENTA, [
                    hoja("RND tam grupo gripe", "Rnd", 86, MAGENTA),
                    hoja("Tam grupo gripe", "Tamano", 90, MAGENTA),
                ]),
                grupo("LLEGADA PROXIMA INTERRUPCION", NARANJA, [
                    hoja("RND interrupcion", "Rnd", 86, NARANJA),
                    hoja("Tiempo interrupcion", "Tiempo", 96, NARANJA),
                    hoja("Prox interrupcion", "Seg prox\nllegada", 116, NARANJA),
                ]),
                hoja("Fin interrupcion", "FIN\nINTERRUPCION", 118, CELESTE),
                grupo("FIN VACUNACION LOTE", ROJO, [
                    hoja("Tam lote vacunacion", "Tam lote", 92, ROJO),
                    hoja("Tiempo lote vacunacion", "Tiempo", 96, ROJO),
                    hoja("Fin vacunacion", "Seg prox Fin", 118, ROJO),
                ]),
                grupo("VENCIMIENTO LOTE", ROSA, [
                    hoja("Vencimiento gripe", "Hora\nVencimiento", 116, ROSA),
                    hoja("Vacunas gripe restantes", "Vacunas Gripe\nRestantes", 132, ROSA),
                ]),
            ], BLANCO),
            grupo("SERVIDOR", AZUL_OSCURO, [
                hoja("Cola COVID", "COLA\nCOVID", 110, VERDE_SERVIDOR),
                hoja("Cola gripe", "COLA\nGRIPE", 110, VERDE_SERVIDOR),
                grupo("ENFERMERO", VERDE_SERVIDOR, [
                    hoja("Turno actual", "Turno actual", 116, VERDE_SERVIDOR),
                    hoja("Estado enfermero", "Estado", 126, VERDE_SERVIDOR),
                ]),
                hoja("Tiempo remanente lote", "Tpo Remanente\nlote vacunacion", 134, VERDE_SERVIDOR),
            ], BLANCO),
            grupo("VARIABLES", AZUL_OSCURO, [
                hoja("Gripe vacunados", "Vacunas de Gripe\nAplicadas", 116, AMARILLO),
                hoja("COVID vacunados", "Vacunas de Covid\nAplicadas", 116, AMARILLO),
                hoja("Dosis gripe descartadas", "Vacunas de Gripe\nVencidas", 116, AMARILLO),
                hoja("Ac tiempo vacunacion", "Ac de tiempo\nVacunacion", 140, AMARILLO),
                hoja("Ac cantidad llegadas", "AC de cantidad\nde llegadas", 132, AMARILLO),
                hoja("Ac personas por llegada", "Ac de personas\npor llegada", 132, AMARILLO),
                hoja("Pacientes atendidos", "Pacientes que\nPasaron a ser atendidos", 150, AMARILLO),
                hoja("Ac tiempo espera cola", "Ac de tiempo\nespera en cola", 142, AMARILLO),
                hoja("Ac tiempo sistema", "Ac de tiempo\nen sistema", 142, AMARILLO),
            ], BLANCO),
            grupo("ESTADISTICAS", AZUL_OSCURO, [
                hoja("Porc gripe aplicadas", "Porcentaje de Vacunas\nde gripe aplicadas", 156, AZUL_ESTADISTICAS),
                hoja("Porc covid aplicadas", "Porcentaje de Vacunas\nde COVID aplicadas", 156, AZUL_ESTADISTICAS),
                hoja("Porc gripe vencidas", "Porcentaje de Vacunas\nde Gripe Vencidas", 156, AZUL_ESTADISTICAS),
                hoja("Tiempo promedio atencion", "Tiempo Promedio\nde Atencion", 136, AZUL_ESTADISTICAS),
                hoja("Total pacientes atendidos", "Total pacientes\natendidos", 130, AZUL_ESTADISTICAS),
                hoja("Prom personas llegada", "Promedio de personas\npor llegada", 148, AZUL_ESTADISTICAS),
                hoja("Tiempo promedio espera", "Tiempo Promedio\nde Espera", 134, AZUL_ESTADISTICAS),
                hoja("Tiempo promedio permanencia", "Tiempo Promedio de\npermanencia en sistema", 170, AZUL_ESTADISTICAS),
            ], BLANCO),
            self.grupo_pacientes(GRIPE, "PACIENTES GRIPE", "Paciente Gripe", pacientes_gripe, AMARILLO_PACIENTE),
            self.grupo_pacientes(COVID, "PACIENTES COVID", "Paciente COVID", pacientes_covid, ROSA_PACIENTE),
        ]

    def grupo_pacientes(self, vacuna, titulo, prefijo, cantidad, color):
        hijos = []
        for indice in range(cantidad):
            numero = indice + 1
            hijos.append(
                grupo(f"{prefijo} {numero}", color, [
                    hoja(f"__paciente_{vacuna}_{indice}_estado", "Estado", 86, color),
                    hoja(f"__paciente_{vacuna}_{indice}_llegada", "Hora llegada", 112, color),
                ], NEGRO)
            )
        return grupo(titulo, AZUL_OSCURO, hijos, BLANCO)

    def max_pacientes_en_filas(self, filas, vacuna):
        maximo = 0
        for fila in filas:
            cantidad = sum(1 for paciente in fila.get("_objetos", []) if paciente.get("Vacuna") == vacuna)
            maximo = max(maximo, cantidad)
        return maximo

    def valor_vector(self, fila, columna):
        if columna.startswith("__paciente_"):
            return self.valor_paciente_vector(fila, columna)
        return fila.get(columna, "")

    def valor_paciente_vector(self, fila, columna):
        partes = columna.split("_")
        vacuna = partes[3]
        indice = int(partes[4])
        atributo = partes[5]

        pacientes = [
            paciente
            for paciente in fila.get("_objetos", [])
            if paciente.get("Vacuna") == vacuna
        ]
        if indice >= len(pacientes):
            return ""

        paciente = pacientes[indice]
        if atributo == "estado":
            return paciente.get("Estado", "")
        if atributo == "llegada":
            return paciente.get("Llegada (seg)", "")
        return ""

    def limpiar_detalle_pacientes(self):
        columnas = ["ID", "Vacuna", "Estado", "Llegada (seg)", "Grupo", "Inicio vacunacion"]
        self.configurar_columnas(self.tabla_detalle_pacientes, columnas)
        self.texto_detalle.set("Seleccione una fila para ver los pacientes presentes.")

    def mostrar_detalle_pacientes(self, _evento=None):
        seleccion = self.tabla_vector.selection()
        self.limpiar_detalle_pacientes()
        if not seleccion:
            return

        indice = int(seleccion[0])
        objetos = self.filas_vector_actuales[indice].get("_objetos", [])
        self.texto_detalle.set(f"Pacientes presentes: {len(objetos)}")
        columnas = self.tabla_detalle_pacientes["columns"]
        for objeto in objetos:
            valores = [formatear_numero(objeto[columna]) for columna in columnas]
            self.tabla_detalle_pacientes.insert("", "end", values=valores)

    def cargar_estadisticas(self, estadisticas):
        columnas = ["Estadistica", "Valor"]
        self.configurar_columnas(self.tabla_estadisticas, columnas)
        for nombre, valor in estadisticas:
            self.tabla_estadisticas.insert("", "end", values=[nombre, formatear_numero(valor)])

    def cargar_rk(self, filas):
        if not filas:
            return
        columnas = self.columnas_rk()
        self.configurar_columnas_con_titulos(self.tabla_rk, columnas)
        for fila in filas:
            self.tabla_rk.insert(
                "",
                "end",
                values=[formatear_numero(fila[identificador]) for identificador, _titulo in columnas],
            )

    def columnas_rk(self):
        return [
            ("t", "t"),
            ("E", "E"),
            ("K1", "K1"),
            ("E+H/2*K1", "E+H/2*K1"),
            ("t+H/2 K2", "t+H/2"),
            ("K2", "K2"),
            ("E+H/2*K2", "E+H/2*K2"),
            ("t+H/2 K3", "t+H/2"),
            ("K3", "K3"),
            ("E+H*K3", "E+H*K3"),
            ("t+H", "t+H"),
            ("K4", "K4"),
            ("t(i+1)", "t(i+1)"),
            ("E(i+1)", "E(i+1)"),
        ]

    def exportar_csv(self):
        if not self.resultado:
            messagebox.showinfo("Exportar", "Primero ejecuta una simulacion.")
            return

        ruta = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            title="Guardar vector de estado",
        )
        if not ruta:
            return

        filas = self.resultado["filas"]
        encabezado = self.construir_encabezado_vector(filas)
        columnas = self.columnas_de_encabezado(encabezado)
        with open(ruta, "w", newline="", encoding="utf-8") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow([columna["id"] for columna in columnas])
            for fila in filas:
                escritor.writerow([
                    formatear_numero(self.valor_vector(fila, columna["id"]))
                    for columna in columnas
                ])
        messagebox.showinfo("Exportar", "Vector exportado correctamente.")
