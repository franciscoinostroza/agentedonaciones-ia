import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import get_cliente, IA_MODEL
from search.busqueda import (
    CATEGORIAS,
    buscar_empresas_local,
    buscar_unificado,
    mostrar_resultados,
    exportar_csv,
)
from database.empresas import EMPRESAS
from cartas.generador import generar_carta, guardar_carta, generar_todas_cartas


IA_ACTIVA = bool(get_cliente())


def main():
    ia_tag = f"[IA: {IA_MODEL}]" if IA_ACTIVA else "[IA: sin configurar]"
    print(f"""
╔══════════════════════════════════════════════╗
║     AGENTE DE BÚSQUEDA DE DONACIONES        ║
║         Merendero IEA - Argentina            ║
║              {ia_tag}              ║
╚══════════════════════════════════════════════╝
""")

    while True:
        print("  ¿Qué necesita el merendero?")
        print("  (Ej: 'materiales para baños', 'computadoras', 'libros y cuadernos')\n")
        print("  Comandos:  :categorias  :provincias  :todas  :csv  :cartas  :ia  :salir")
        entrada = input("\n  > ").strip()

        if not entrada:
            continue

        if entrada == ":salir":
            print("\n  ¡Gracias! Buena suerte con las donaciones para IEA.\n")
            break

        elif entrada == ":categorias":
            print()
            for k, v in CATEGORIAS.items():
                print(f"    {k}: {v}")
            print()
            continue

        elif entrada == ":provincias":
            provincias = sorted(set(e["provincia"] for e in EMPRESAS))
            print("\n  Provincias con empresas registradas:")
            for p in provincias:
                print(f"    - {p}")
            print()
            continue

        elif entrada == ":todas":
            resultados = buscar_empresas_local()
            mostrar_resultados(resultados)
            continue

        elif entrada == ":csv":
            resultados = buscar_empresas_local()
            if resultados:
                archivo = input("  Archivo (Enter = empresas_donantes.csv): ").strip()
                exportar_csv(resultados, archivo or "empresas_donantes.csv")
            continue

        elif entrada == ":cartas":
            print("\n  Generar cartas para todas las empresas de una categoría:")
            for k, v in CATEGORIAS.items():
                print(f"    {k}: {v}")
            cat = input("  Categoría (Enter = todas): ").strip().lower()
            nombre = input("  Nombre del responsable: ").strip()
            tel = input("  Teléfono: ").strip()
            email = input("  Email: ").strip()
            if cat in CATEGORIAS:
                empresas = buscar_empresas_local(categoria=cat)
            else:
                empresas = buscar_empresas_local()
            if empresas:
                rutas = generar_todas_cartas(empresas, contacto_nombre=nombre, contacto_telefono=tel, contacto_email=email)
                print(f"\n  Se generaron {len(rutas)} cartas en 'cartas_generadas/'\n")
            continue

        elif entrada == ":ia":
            if IA_ACTIVA:
                print(f"\n  IA configurada: {IA_MODEL}")
                print(f"  Base URL: opencode.ai/zen/v1")
                print(f"  La búsqueda unificada ya usa IA automáticamente.\n")
            else:
                print("\n  IA no configurada. Para activarla:")
                print("    1. Andá a https://opencode.ai/auth")
                print("    2. Creá una API key")
                print("    3. Pegala en C:\\agente-donaciones\\.env\n")
            continue

        # BÚSQUEDA UNIFICADA (default)
        print(f"\n  Buscando '{entrada}' en BD local", end="")
        if IA_ACTIVA:
            print(" + web con IA...\n")
        else:
            print("...\n")

        def _progreso(msg):
            print(f"  {msg}")

        resultados = buscar_unificado(entrada, usar_ia=IA_ACTIVA, on_progress=_progreso if IA_ACTIVA else None)
        mostrar_resultados(resultados)

        if resultados:
            exp = input("  ¿Exportar a CSV? (s/n): ").strip().lower()
            if exp == "s":
                exportar_csv(resultados)

            gen = input("  ¿Generar cartas para estas empresas? (s/n): ").strip().lower()
            if gen == "s":
                contacto = input("    Responsable: ").strip()
                tel = input("    Teléfono: ").strip()
                email = input("    Email: ").strip()
                for emp in resultados:
                    carta = generar_carta(emp, contacto_nombre=contacto, contacto_telefono=tel, contacto_email=email)
                    ruta = guardar_carta(carta, emp["nombre"] or "empresa")
                    print(f"    Carta: {ruta}")

        print()


if __name__ == "__main__":
    main()
