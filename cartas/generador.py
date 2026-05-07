from datetime import datetime
import os


def generar_carta(empresa, merendero="IEA", contacto_nombre="", contacto_telefono="", contacto_email=""):
    fecha = datetime.now().strftime("%d de %B de %Y")

    meses = {
        "January": "enero", "February": "febrero", "March": "marzo",
        "April": "abril", "May": "mayo", "June": "junio",
        "July": "julio", "August": "agosto", "September": "septiembre",
        "October": "octubre", "November": "noviembre", "December": "diciembre",
    }
    for en, es in meses.items():
        fecha = fecha.replace(en, es)

    carta = f"""
{fecha}

A la atención de: {empresa['nombre']}
Departamento de Responsabilidad Social Empresaria / Donaciones

De nuestra mayor consideración:

Me dirijo a ustedes en nombre del Merendero y Centro Comunitario {merendero},
una organización social sin fines de lucro que trabaja con la comunidad brindando
asistencia alimentaria y espacios de contención para niños, jóvenes y familias
en situación de vulnerabilidad.

Actualmente estamos desarrollando un proyecto de ampliación de nuestras
instalaciones para construir baños adecuados e iniciar cursos y talleres
de formación para la comunidad (alfabetización digital, oficios, apoyo escolar).

Para poder llevar adelante este proyecto, necesitamos contar con los siguientes recursos:

- Materiales de construcción (cemento, cerámicos, sanitarios, grifería, cañerías)
- Equipamiento tecnológico (computadoras, tablets, routers, proyector)
- Útiles y materiales educativos (libros, cuadernos, lápices, marcadores)
- Mobiliario (mesas, sillas, estanterías, pizarrones)

Conocedores del compromiso social de {empresa['nombre']} y de su trayectoria en
acciones de responsabilidad social, solicitamos respetuosamente su colaboración
con donaciones de {empresa['rubro'].lower()} que pudieran estar en condiciones de
ofrecer ({', '.join(empresa.get('tipo_donacion', [])[:4])}).

Cualquier contribución, por pequeña que parezca, representa un paso fundamental
para transformar el espacio comunitario y brindar a nuestra comunidad herramientas
concretas para su desarrollo.

Quedamos a su entera disposición para ampliar información, coordinar una visita
o enviar documentación que consideren necesaria.

Sin otro particular, saludamos atte.

---

{contacto_nombre or '[Nombre del responsable]'}
{merendero} - Centro Comunitario
Tel: {contacto_telefono or '[Teléfono de contacto]'}
Email: {contacto_email or '[Email de contacto]'}
---

"""
    return carta


def guardar_carta(carta, empresa_nombre, carpeta="cartas_generadas"):
    os.makedirs(carpeta, exist_ok=True)
    nombre_archivo = empresa_nombre.lower().replace(" ", "_").replace("/", "_")
    ruta = os.path.join(carpeta, f"carta_{nombre_archivo}.txt")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(carta)
    return ruta


def generar_todas_cartas(empresas, merendero="IEA", contacto_nombre="", contacto_telefono="", contacto_email=""):
    rutas = []
    for emp in empresas:
        carta = generar_carta(emp, merendero, contacto_nombre, contacto_telefono, contacto_email)
        ruta = guardar_carta(carta, emp["nombre"])
        rutas.append(ruta)
    return rutas
