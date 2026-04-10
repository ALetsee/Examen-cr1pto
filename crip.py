#!/usr/bin/env python3
import random
import sys
import os

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    VERDE    = Fore.LIGHTGREEN_EX
    AMARILLO = Fore.YELLOW
    ROJO     = Fore.LIGHTRED_EX
    RESET    = Style.RESET_ALL
    NEGRITA  = Style.BRIGHT
except ImportError:
    VERDE = AMARILLO = ROJO = RESET = NEGRITA = ""

# LECTURA DE TECLAS
if os.name == 'nt':
    import msvcrt
    def _leer_tecla():
        t = msvcrt.getch()
        if t == b'\xe0':
            t2 = msvcrt.getch()
            if t2 == b'H': return 'up'
            if t2 == b'P': return 'down'
        elif t == b'\r':   return 'enter'
        elif t == b'\x03': raise KeyboardInterrupt
        elif t == b'\x1b': return 'esc'
        return 'otro'
else:
    import tty, termios
    def _leer_tecla():
        fd  = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            t = sys.stdin.read(1)
            if t == '\x03': raise KeyboardInterrupt
            if t == '\x1b':
                t2 = sys.stdin.read(1)
                t3 = sys.stdin.read(1)
                if t2 == '[':
                    if t3 == 'A': return 'up'
                    if t3 == 'B': return 'down'
                return 'esc'
            if t in ('\r', '\n'): return 'enter'
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        return 'otro'

# MENU 
def _limpiar():
    os.system('cls' if os.name == 'nt' else 'clear')

def _tamaño_consola():
    try:
        return os.get_terminal_size()
    except OSError:
        return os.terminal_size((80, 24))

def _dibujar_menu(opciones, indice, titulo):
    _limpiar()
    ancho_consola, alto_consola = _tamaño_consola()
    ancho_menu = 50
    filas = []
    filas.append(("#" * ancho_menu, None))
    filas.append(("#" + titulo.center(ancho_menu - 2) + "#", None))
    filas.append(("#" + " " * (ancho_menu - 2) + "#", None))
    for i, op in enumerate(opciones):
        prefix = "> " if i == indice else "  "
        filas.append(("#" + (prefix + op).center(ancho_menu - 2) + "#", i))
    filas.append(("#" * ancho_menu, None))
    margen_v = max((alto_consola - len(filas)) // 2, 0)
    margen_h = max((ancho_consola - ancho_menu) // 2, 0)
    pad = " " * margen_h
    print("\n" * margen_v, end="")
    for linea, op_idx in filas:
        if op_idx is not None and op_idx == indice:
            start = linea.find(opciones[op_idx])
            end   = start + len(opciones[op_idx])
            linea = (linea[:start]
                     + VERDE + NEGRITA + opciones[op_idx] + RESET
                     + linea[end:])
            linea = linea.replace(">", VERDE + NEGRITA + ">" + RESET, 1)
        print(pad + linea)

def menu_interactivo(opciones, titulo=""):
    indice = 0
    _dibujar_menu(opciones, indice, titulo)
    while True:
        tecla = _leer_tecla()
        if tecla == 'up':
            indice = (indice - 1) % len(opciones)
            _dibujar_menu(opciones, indice, titulo)
        elif tecla == 'down':
            indice = (indice + 1) % len(opciones)
            _dibujar_menu(opciones, indice, titulo)
        elif tecla == 'enter':
            return indice
        elif tecla == 'esc':
            return len(opciones) - 1


# PARAMETROS ESTATICOS  y² = x³ - x + 188  (mod 751)
PUNTO_INFINITO = None
P      = 751
COEF_A = 750   # -1 mod 751
COEF_B = 188

# ARITMETICA MODULAR
def inverso_modular(numero, primo):
    if numero == 0:
        raise ZeroDivisionError("El 0 no tiene inverso modular")
    if numero < 0:
        return primo - inverso_modular(-numero, primo)
    coef_anterior, coef_actual   = 1, 0
    resto_anterior, resto_actual = numero, primo
    while resto_actual != 0:
        cociente = resto_anterior // resto_actual
        resto_anterior, resto_actual = resto_actual, resto_anterior - cociente * resto_actual
        coef_anterior, coef_actual   = coef_actual, coef_anterior - cociente * coef_actual
    if resto_anterior != 1:
        raise ValueError("Los valores no son coprimos")
    return coef_anterior % primo

# OPERACIONES EN LA CURVA ELIPTICA
def sumar_puntos(punto_A, punto_B, coef_a, primo):
    if punto_A is PUNTO_INFINITO: return punto_B
    if punto_B is PUNTO_INFINITO: return punto_A
    x1, y1 = punto_A
    x2, y2 = punto_B
    if x1 == x2 and (y1 + y2) % primo == 0:
        return PUNTO_INFINITO
    if punto_A != punto_B:
        pendiente = ((y2 - y1) * inverso_modular(x2 - x1, primo)) % primo
    else:
        if y1 == 0: return PUNTO_INFINITO
        pendiente = ((3 * x1**2 + coef_a) * inverso_modular(2 * y1, primo)) % primo
    x3 = (pendiente**2 - x1 - x2) % primo
    y3 = (pendiente * (x1 - x3) - y1) % primo
    return (x3, y3)

def multiplicar_punto_por_escalar(escalar, punto, coef_a, primo):
    if escalar % primo == 0 or punto is PUNTO_INFINITO:
        return PUNTO_INFINITO
    if escalar < 0:
        return multiplicar_punto_por_escalar(
            -escalar, (punto[0], (-punto[1]) % primo), coef_a, primo
        )
    acumulado = PUNTO_INFINITO
    sumando   = punto
    while escalar > 0:
        if escalar & 1:
            acumulado = sumar_puntos(acumulado, sumando, coef_a, primo)
        sumando = sumar_puntos(sumando, sumando, coef_a, primo)
        escalar >>= 1
    return acumulado

def negar_punto(punto, primo):
    if punto is PUNTO_INFINITO: return PUNTO_INFINITO
    return (punto[0], (-punto[1]) % primo)

# PUNTO GENERADOR G
def calcular_orden_del_punto(punto, coef_a, primo, limite=2000):
    actual = PUNTO_INFINITO
    for n in range(1, limite + 1):
        actual = sumar_puntos(actual, punto, coef_a, primo)
        if actual is PUNTO_INFINITO:
            return n
    return None

def buscar_punto_generador(coef_a, coef_b, primo, orden_minimo=300):
    for x in range(primo):
        rhs = (x**3 + coef_a * x + coef_b) % primo
        for y in range(primo):
            if (y * y) % primo == rhs:
                candidato = (x, y)
                orden = calcular_orden_del_punto(candidato, coef_a, primo)
                if orden and orden > orden_minimo:
                    return candidato, orden
    raise ValueError("No se encontro un punto generador con orden suficiente")

# TABLA ASCII <-> PUNTOS ECC
def construir_tabla_ascii(punto_base, coef_a, primo):
    ascii_a_punto = {}
    punto_a_ascii = {}
    for v in range(1, 256):
        pt = multiplicar_punto_por_escalar(v, punto_base, coef_a, primo)
        if pt is not PUNTO_INFINITO:
            ascii_a_punto[v]  = pt
            punto_a_ascii[pt] = v
    return ascii_a_punto, punto_a_ascii

# CIFRADO / DESCIFRADO ElGamal ECC
def cifrar_punto_elgamal(punto_mensaje, nonce, punto_base, clave_publica, coef_a, primo):
    C1 = multiplicar_punto_por_escalar(nonce, punto_base, coef_a, primo)
    S  = multiplicar_punto_por_escalar(nonce, clave_publica, coef_a, primo)
    C2 = sumar_puntos(punto_mensaje, S, coef_a, primo)
    return C1, C2

def descifrar_punto_elgamal(C1, C2, clave_privada, coef_a, primo):
    S = multiplicar_punto_por_escalar(clave_privada, C1, coef_a, primo)
    return sumar_puntos(C2, negar_punto(S, primo), coef_a, primo)

# SETUP COMPARTIDO
def _setup():
    disc = (4 * COEF_A**3 + 27 * COEF_B**2) % P
    print(VERDE + f"\nCurva: y^2 = x^3 - x + {COEF_B}  (mod {P})" + RESET)
    if disc == 0:
        print(ROJO + "Error: curva singular." + RESET)
        return None
    try:
        punto_base, orden = buscar_punto_generador(COEF_A, COEF_B, P)
    except ValueError as e:
        print(ROJO + str(e) + RESET)
        return None
    print(VERDE + f"Punto G = {punto_base}  |  orden(G) = {orden}" + RESET)
    return P, COEF_A, COEF_B, punto_base, orden

#  CIFRAR
def flujo_cifrar():
    resultado = _setup()
    if resultado is None:
        input("\n> ")
        return

    primo, coef_a, coef_b, punto_base, orden_base = resultado
    ascii_a_punto, _ = construir_tabla_ascii(punto_base, coef_a, primo)

    random.seed(42)
    clave_privada = random.randint(2, orden_base - 2)
    clave_publica = multiplicar_punto_por_escalar(clave_privada, punto_base, coef_a, primo)

    print(NEGRITA + f"\nClave privada d  : {clave_privada}" + RESET)
    print(NEGRITA + f"Clave publica Q  : {clave_publica}" + RESET)

    while True:
        try:
            mensaje = input("\nMensaje a cifrar: ").strip()
        except EOFError:
            print(ROJO + "\nEntrada interrumpida." + RESET)
            input("\n> ")
            return

        if not mensaje:
            print(ROJO + "Error: el mensaje no puede estar vacio." + RESET)
            continue

        invalidos = [c for c in mensaje if ord(c) not in ascii_a_punto]
        if invalidos:
            print(ROJO + f"Error: caracteres sin mapeo ECC -> {set(invalidos)}" + RESET)
            continue
        break

    print(AMARILLO + "\nBloques cifrados:" + RESET)
    for c in mensaje:
        nonce = random.randint(2, orden_base - 2)
        C1, C2 = cifrar_punto_elgamal(
            ascii_a_punto[ord(c)], nonce, punto_base, clave_publica, coef_a, primo
        )
        print(f"  '{c}' -> {C1[0]},{C1[1]},{C2[0]},{C2[1]}")

    print(VERDE + f"\nd = {clave_privada}  |  G = {punto_base}  |  p={primo}  a=-1  b={coef_b}" + RESET)
    input("\n> ")

#  DESCIFRAR
def flujo_descifrar():
    resultado = _setup()
    if resultado is None:
        input("\n> ")
        return

    primo, coef_a, coef_b, punto_base, _ = resultado
    _, punto_a_ascii = construir_tabla_ascii(punto_base, coef_a, primo)

    while True:
        try:
            entrada_d = input("\nClave privada d = ").strip()
        except EOFError:
            print(ROJO + "\nEntrada interrumpida." + RESET)
            input("\n> ")
            return

        if not entrada_d:
            print(ROJO + "Error: ingresa un valor para d." + RESET)
            continue
        try:
            clave_privada = int(entrada_d)
            if clave_privada < 2:
                raise ValueError
        except ValueError:
            print(ROJO + "Error: d debe ser un entero >= 2." + RESET)
            continue
        break

    print(AMARILLO + "\nFormato por bloque: x1,y1,x2,y2" + RESET)
    print("Linea vacia para terminar.\n")

    mensaje_descifrado = ""
    idx = 0

    while True:
        try:
            entrada = input(f"Bloque {idx}: ").strip()
        except EOFError:
            break

        if not entrada:
            break

        try:
            partes = [v.strip() for v in entrada.split(',')]
            if len(partes) != 4:
                raise ValueError("Se requieren exactamente 4 valores.")
            vals = [int(v) for v in partes]
            C1 = (vals[0], vals[1])
            C2 = (vals[2], vals[3])
        except ValueError as e:
            print(ROJO + f"Error de formato: {e}  ->  usa x1,y1,x2,y2" + RESET)
            continue

        punto_rec = descifrar_punto_elgamal(C1, C2, clave_privada, coef_a, primo)

        if punto_rec not in punto_a_ascii:
            print(ROJO + f"Error: el punto {punto_rec} no esta en la tabla ASCII. "
                  f"Verifica que d={clave_privada} sea correcto." + RESET)
            input("\n> ")
            return

        mensaje_descifrado += chr(punto_a_ascii[punto_rec])
        idx += 1

    if mensaje_descifrado:
        print(VERDE + NEGRITA + f"\nMensaje descifrado: {mensaje_descifrado}" + RESET)
    else:
        print(AMARILLO + "No se ingresaron bloques." + RESET)
    input("\n> ")

# MAIN
OPCIONES = ["Cifrar mensaje", "Descifrar mensaje", "Salir"]

def main():
    try:
        while True:
            eleccion = menu_interactivo(OPCIONES, titulo=" ")
            if eleccion == 0:
                flujo_cifrar()
            elif eleccion == 1:
                flujo_descifrar()
            elif eleccion == 2:
                _limpiar()
                print(VERDE + " " + RESET)
                sys.exit(0)
    except KeyboardInterrupt:
        _limpiar()
        print(AMARILLO + "\n" + RESET)
        sys.exit(0)

if __name__ == "__main__":
    main()