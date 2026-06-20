from dataclasses import dataclass


@dataclass(slots=True)
class Paciente:
    id: int
    vacuna: str
    llegada: float
    grupo: int
    grupo_llegada: int = 0
    estado: str = "Esperando"
    inicio_vacunacion: float = 0.0
