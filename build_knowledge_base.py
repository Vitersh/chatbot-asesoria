# build_knowledge_base.py
import os
import shutil
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.enums import TA_JUSTIFY

DOCS_DIR = "documentos"

DOCS_CONTENT = {
    "01_Conceptos_Codigo_Tributario.pdf": """
    <h1>TEMA: Conceptos Fundamentales del Código Tributario Chileno</h1>
    <p><b>ROL DEL SII:</b> El Servicio de Impuestos Internos (SII) es el organismo encargado de la aplicación y fiscalización de todos los impuestos internos de Chile.</p>
    <p><b>INICIO DE ACTIVIDADES:</b> Es una declaración jurada obligatoria que se presenta al SII antes de comenzar cualquier negocio o actividad profesional que pueda generar renta. Se debe hacer dentro de los dos meses siguientes al inicio de las actividades.</p>
    <p><b>RUT (Rol Único Tributario):</b> Es el número de identificación de cada contribuyente (personas, empresas) ante el SII. Es esencial para cualquier trámite.</p>
    <p><b>OBLIGACIÓN DE RESPALDAR OPERACIONES:</b> El contribuyente tiene la obligación de probar la veracidad de sus declaraciones con documentos como facturas, boletas, libros de contabilidad, etc.</p>
    <p><b>SANCIONES COMUNES (Artículo 97):</b><br/>
    - Retardo en declaraciones: Multa.<br/>
    - No emitir boletas o facturas: Multa y posible clausura del local.<br/>
    - Declaraciones falsas o incompletas: Multa y posibles sanciones penales.</p>
    """,
    "02_Conceptos_Ley_Impuesto_Renta.pdf": """
    <h1>TEMA: Conceptos Clave de la Ley de Impuesto a la Renta (LIR)</h1>
    <p><b>RENTA:</b> La ley grava las rentas, que son los ingresos que constituyen utilidades o beneficios que rinde una cosa o actividad.</p>
    <p><b>INGRESO NO CONSTITUTIVO DE RENTA (INR):</b> Son ingresos que, por ley, NO pagan impuestos. El ejemplo más importante son las pensiones y jubilaciones del sistema previsional chileno (AFP, IPS, PGU).</p>
    <p><b>CATEGORÍAS DE IMPUESTOS:</b><br/>
    - <b>Primera Categoría:</b> Grava las rentas del capital, como las utilidades de las empresas, arriendos de propiedades, intereses, etc.<br/>
    - <b>Segunda Categoría:</b> Grava las rentas del trabajo, como sueldos (Impuesto Único de Segunda Categoría) y honorarios (afectos a Global Complementario).</p>
    <p><b>IMPUESTO GLOBAL COMPLEMENTARIO (IGC):</b> Es el impuesto final que pagan las personas naturales con domicilio en Chile. Es un impuesto anual y progresivo (a más renta, más alta la tasa). Se suman todas las rentas afectas del año (honorarios, arriendos, retiros de empresas) y se les aplica una tabla.</p>
    """,
    "03_Conceptos_Ley_IVA.pdf": """
    <h1>TEMA: Conceptos Clave del Impuesto al Valor Agregado (IVA)</h1>
    <p><b>QUÉ ES:</b> Es un impuesto del 19% que se aplica al precio de la mayoría de los bienes y servicios que se venden en Chile.</p>
    <p><b>HECHO GRAVADO:</b> La acción que gatilla el impuesto. Principalmente son las "ventas" y los "servicios". Desde 2023, la mayoría de los servicios profesionales están afectos a IVA, con algunas exenciones importantes.</p>
    <p><b>DÉBITO FISCAL:</b> Es el IVA (19%) que una empresa cobra a sus clientes en sus ventas. Este dinero no es de la empresa, es del Fisco.</p>
    <p><b>CRÉDITO FISCAL:</b> Es el IVA (19%) que una empresa paga a sus proveedores al comprar productos o servicios necesarios para su negocio.</p>
    <p><b>CÁLCULO Y PAGO (FORMULARIO F29):</b> Cada mes, las empresas deben declarar y pagar el IVA. El cálculo es: Total de Débitos Fiscales del mes MENOS el Total de Créditos Fiscales del mes. Si es positivo, se paga la diferencia. Si es negativo, queda un "remanente de crédito fiscal" para el mes siguiente.</p>
    """,
    "04_Como_Crear_Empresa_en_un_Dia.pdf": """
    <h1>TEMA: Guía Práctica para Crear una Empresa en Chile</h1>
    <p><b>CONTEXTO:</b> La forma moderna y rápida de crear una empresa (SpA, EIRL, Ltda.) es a través del portal "Registro de Empresas y Sociedades" (RES), conocido como "Tu Empresa en un Día".</p>
    <p><b>PASO 1: REQUISITOS:</b> Todos los socios deben tener su Clave Única vigente. Tener claro: nombre de la empresa, socios, capital, y objeto social.</p>
    <p><b>PASO 2: COMPLETAR FORMULARIO:</b> En www.tuempresaenundia.cl, se elige el tipo de sociedad y se completan los datos de la empresa y socios.</p>
    <p><b>PASO 3: FIRMA:</b> Cada socio debe firmar, ya sea con Firma Electrónica Avanzada (FEA) o yendo a una notaría con el "número de atención" del portal.</p>
    <p><b>PASO 4: OBTENCIÓN DE RUT E INICIO DE ACTIVIDADES:</b> Una vez firmada, el portal solicita el RUT al SII. En minutos, la empresa ya tiene RUT. El último paso es hacer el "Inicio de Actividades" en la web del SII para poder facturar.</p>
    """,
    "05_Tipos_de_Sociedades.pdf": """
    <h1>TEMA: Tipos de Empresas Comunes para Emprender</h1>
    <p><b>1. Empresa Individual de Responsabilidad Limitada (E.I.R.L.):</b><br/>- Socios: 1 solo dueño.<br/>- Responsabilidad: Limitada. El patrimonio personal está protegido.<br/>- Ideal para: Quien emprende solo y quiere separar finanzas.</p>
    <p><b>2. Sociedad por Acciones (SpA):</b><br/>- Socios: 1 o más. Muy flexible.<br/>- Responsabilidad: Limitada al monto de sus acciones.<br/>- Ideal para: Startups que planean crecer e incorporar inversionistas.</p>
    <p><b>3. Sociedad de Responsabilidad Limitada (Ltda.):</b><br/>- Socios: De 2 a 50.<br/>- Responsabilidad: Limitada al monto de sus aportes.<br/>- Ideal para: Sociedades cerradas (familiares, amigos) donde se valora la estabilidad de los socios.</p>
    """,
    "06_Regimenes_Tributarios_Pyme.pdf": """
    <h1>TEMA: Regímenes Tributarios para Pymes (Pro Pyme)</h1>
    <p><b>OPCIÓN 1: Pro Pyme General:</b><br/>- Impuesto Empresa: Sí paga, una tasa reducida de IDPC (ej. 12.5%).<br/>- Impuesto Dueños: Pagan Global Complementario SÓLO cuando RETIRAN utilidades.<br/>- Ideal para: Empresas que reinvierten sus ganancias.</p>
    <p><b>OPCIÓN 2: Pro Pyme Transparente:</b><br/>- Impuesto Empresa: NO paga IDPC (tasa 0%).<br/>- Impuesto Dueños: Pagan Global Complementario sobre el 100% de la utilidad de la empresa, la retiren o no.<br/>- Ideal para: Empresas donde los dueños retiran toda la utilidad anualmente.</p>
    """,
    "07_Termino_de_Giro.pdf": """
    <h1>TEMA: Término de Giro</h1>
    <p><b>QUÉ ES:</b> Es el trámite ante el SII para comunicar el fin de las actividades de una empresa. Es la "muerte legal" del negocio para efectos tributarios.</p>
    <p><b>CUÁNDO:</b> Dentro de los dos meses siguientes al cese de actividades.</p>
    <p><b>CONSECUENCIAS DE NO HACERLO:</b> Acumulación de multas e intereses. Es fundamental cerrar el ciclo.</p>
    <p><b>PROCESO:</b> Se presenta el Formulario 2121, se realiza un balance final y el SII fiscaliza que todos los impuestos estén pagados antes de emitir el certificado de término.</p>
    """,
    "08_Guia_Boletas_Honorarios.pdf": """
    <h1>TEMA: Guía sobre Boletas de Honorarios</h1>
    <p><b>CONCEPTO:</b> Documento que emiten trabajadores independientes (segunda categoría) para cobrar por sus servicios.</p>
    <p><b>RETENCIÓN (PPM):</b> Al emitir una boleta, se retiene un porcentaje (ej. 13.75% en 2024). Esta retención es un Pago Provisional Mensual (PPM) obligatorio.</p>
    <p><b>DESTINO DE LA RETENCIÓN:</b> En la Declaración de Renta de abril, el SII usa ese dinero para pagar las cotizaciones previsionales (AFP, Salud) y el impuesto anual (Global Complementario).</p>
    <p><b>DEVOLUCIÓN:</b> Si lo retenido es mayor que el pago de cotizaciones e impuestos, el SII devuelve la diferencia.</p>
    """,
    "09_Guia_Arriendo_y_DFL2.pdf": """
    <h1>TEMA: Impuestos al Arrendar una Propiedad</h1>
    <p><b>REGLA GENERAL:</b> El ingreso por arriendo es una renta y debe declararse en el Global Complementario.</p>
    <p><b>BENEFICIO DFL 2:</b> Las "viviendas económicas" (hasta 140 m²) tienen un beneficio. Si una persona arrienda hasta DOS propiedades DFL 2, el ingreso de esos arriendos es un "Ingreso No Renta", es decir, NO paga impuestos.</p>
    <p><b>PÉRDIDA DEL BENEFICIO:</b> Si se arriendan TRES o más propiedades DFL 2, se pierde el beneficio por TODAS.</p>
    <p><b>GASTOS DEDUCIBLES:</b> Del ingreso por arriendo (cuando se debe declarar), se puede descontar el Impuesto Territorial (contribuciones) pagado.</p>
    """,
    "10_Rebaja_Contribuciones_Adulto_Mayor.pdf": """
    <h1>TEMA: Beneficio Rebaja de Contribuciones para Adultos Mayores</h1>
    <p><b>QUÉ ES:</b> Un descuento en el pago de contribuciones para la vivienda principal de adultos mayores con ingresos bajos.</p>
    <p><b>REQUISITOS:</b> Edad (+60 mujer, +65 hombre), tramo de ingresos bajos, y que la propiedad no supere un avalúo fiscal máximo.</p>
    <p><b>BENEFICIO:</b> Puede ser un descuento del 100% o del 50%, dependiendo del nivel de ingresos.</p>
    <p><b>CÓMO SE OBTIENE:</b> El SII lo aplica de forma automática si se cumplen los requisitos.</p>
    """,
    "11_Exencion_IVA_Servicios_Profesionales.pdf": """
    <h1>TEMA: Exención de IVA para Servicios Profesionales</h1>
    <p><b>REGLA GENERAL (Desde 2023):</b> La mayoría de los servicios están afectos a IVA.</p>
    <p><b>GRAN EXCEPCIÓN:</b> Los servicios prestados por "sociedades de profesionales" y los servicios ambulatorios de salud están EXENTOS de IVA.</p>
    <p><b>REQUISITOS PARA "SOCIEDAD DE PROFESIONALES":</b><br/>1. Debe ser una sociedad de personas (ej. Ltda.).<br/>2. Todos los socios deben ser personas naturales que ejerzan profesiones similares.<br/>3. Su único objeto social debe ser la prestación de dichos servicios.<br/>4. Debe estar registrada como tal ante el SII.</p>
    <p><b>EN SIMPLE:</b> Los servicios de una persona natural que emite boletas de honorarios NO están afectos a IVA. Los de una sociedad de profesionales registrada, tampoco.</p>
    """,
    "12_Facturacion_Electronica.pdf": """
    <h1>TEMA: Facturación Electrónica en Chile</h1>
    <p><b>OBLIGATORIEDAD:</b> Prácticamente todas las empresas en Chile están obligadas a emitir sus documentos tributarios de forma electrónica.</p>
    <p><b>SISTEMAS:</b><br/>1. <b>Sistema Gratuito del SII:</b> Ideal para bajo volumen de facturación.<br/>2. <b>Software de Mercado:</b> Pagados, a menudo se integran con contabilidad y otros sistemas.</p>
    <p><b>VENTAJAS:</b> Ahorro, simplificación de la declaración de impuestos (el F29 se pre-llena), y mejor control de las operaciones.</p>
    """
}


def create_pdf_from_html(filepath, html_content):
    try:
        doc = SimpleDocTemplate(filepath, pagesize=letter, topMargin=72, bottomMargin=72, leftMargin=72, rightMargin=72)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))

        # Convertir el HTML simple a objetos de ReportLab
        story = []
        # Usamos un truco para reemplazar etiquetas h1 y p por párrafos con estilos
        content = html_content.strip().replace("<h1>", "<para style='h1'>").replace("</h1>", "</para>")
        content = content.replace("<p>", "<para style='Normal'>").replace("</p>", "</para>")

        # Dividimos por párrafos para construir la historia
        elements = content.split("</para>")
        for elem in elements:
            if not elem.strip():
                continue

            # Extraemos el estilo y el texto
            style_name = "Normal"
            if "<para style='h1'>" in elem:
                style_name = "h1"
                text = elem.replace("<para style='h1'>", "")
            else:
                text = elem.replace("<para style='Normal'>", "")

            story.append(Paragraph(text, styles[style_name]))
            story.append(Spacer(1, 12))

        doc.build(story)
        return True
    except Exception as e:
        print(f"    [ERROR AL CREAR PDF] No se pudo crear '{os.path.basename(filepath)}': {e}")
        return False


def main():
    if os.path.exists(DOCS_DIR):
        print(f"🧹 Limpiando directorio antiguo '{DOCS_DIR}'...")
        shutil.rmtree(DOCS_DIR)
    os.makedirs(DOCS_DIR)
    print(f"📂 Carpeta '{DOCS_DIR}' creada.")

    print("\n" + "-" * 60)
    print("✍️ CONSTRUYENDO ENCICLOPEDIA TRIBUTARIA LOCAL...")
    print(f"Se crearán {len(DOCS_CONTENT)} documentos esenciales.")
    print("-" * 60)

    success_count, fail_count = 0, 0

    for filename, content in DOCS_CONTENT.items():
        filepath = os.path.join(DOCS_DIR, filename)
        print(f"  -> Creando '{filename}'...")
        if create_pdf_from_html(filepath, content):
            print("     ✅ Archivo creado y guardado.")
            success_count += 1
        else:
            fail_count += 1

    print("\n" + "=" * 60)
    print("🏁 PROCESO FINALIZADO 🏁")
    print("=" * 60)
    print(f"Resumen:\n  ✅ Archivos creados con éxito: {success_count}\n  ❌ Archivos que fallaron: {fail_count}")

    if fail_count == 0:
        print("\n[ÉXITO] ¡La base de conocimiento se ha construido de forma completa y robusta!")

    print("\nAhora puedes ejecutar con confianza tu script principal 'main_chatbot.py'.")
    print("=" * 60)


if __name__ == "__main__":
    main()