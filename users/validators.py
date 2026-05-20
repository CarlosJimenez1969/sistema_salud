"""Validadores reutilizables para el modelo User."""


def validar_cedula_ecuatoriana(cedula: str) -> bool:
    """Valida cédula ecuatoriana (10 dígitos + algoritmo módulo 10).

    Returns True si la cédula es válida, False en caso contrario.
    """
    if not cedula or not cedula.isdigit() or len(cedula) != 10:
        return False

    provincia = int(cedula[:2])
    if provincia < 1 or provincia > 24:
        return False

    tercer_digito = int(cedula[2])
    if tercer_digito > 5:
        return False

    coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    suma = 0
    for i in range(9):
        producto = int(cedula[i]) * coeficientes[i]
        if producto > 9:
            producto -= 9
        suma += producto

    digito_verificador = (10 - (suma % 10)) % 10
    return digito_verificador == int(cedula[9])
