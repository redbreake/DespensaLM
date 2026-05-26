import re
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from despensa.models import Producto

# Texto del inventario original proporcionado por el usuario
TEXTO_INVENTARIO_DEFECTO = """
🧼 Limpieza y Cuidado del Hogar

Insecticidas y Limpiadores en Aerosol

Raid (Azul, aerosol): 3 unidades

Raid (Amarillo, aerosol): 1 unidad

Cif Bioactive (Gatillo verde): 1 unidad

Panubio (Lustramuebles / Limpiador aerosol): 1 unidad

Poett (Aerosol): 1 unidad

Lysoform (Aerosol): 1 unidad

Blem / Ceramono (Aerosol extremo izquierdo): 1 unidad

Jabón para Ropa y Suavizantes

Ala Lavado Total (Líquido, envase flexible grande): 1 unidad

Ala (Polvo, paquetes chicos/medianos): 4 unidades

Skip Expert (Líquido, envase flexible): 1 unidad

Vivere (Suavizante, envase flexible rosa): 1 unidad

Esencial (Suavizante/Perfumina, envase flexible verde): 2 unidades

Zorro (Polvo, paquetes blancos a la derecha): 3 unidades

Ala (Líquido, botella rosa chica): 1 unidad

Ala (Líquido, botella blanca chica): 1 unidad

Desinfectantes y Limpiadores Líquidos

Ayudín (Líquido, botellas amarillas grandes/medianas): 16 unidades

Ayudín (Líquido, botellas blancas de lavandina): 2 unidades

Poett (Líquido para pisos, botellas azules): 5 unidades

Cif Gel (Botella blanca chica): 1 unidad

Detergente líquido (Botella amarilla traslúcida, extremo derecho): 1 unidad

Utensilios de Limpieza y Papel

Higienol Export (Papel higiénico, paquetes de 4): 3 paquetes

Cautiva (Papel higiénico, paquete de 4): 1 paquete

Cotidianas (Línea económica, rollos): 1 paquete grande

Rollos sueltos de papel (marcas varias como 90 o 06): 6 unidades

Fibralimp / Paños abrasivos (paquetes de esponjas/virulana): 4 paquetes

Trapos de piso / Rejillas (color blanco/crudo): 2 pilas grandes

Cepillos de limpieza (en la canasta plástica): 2 unidades

👶 Cuidado Personal y Bebés

Pañales

Pampers Supersec (Paquetes verdes/rojos, talle G): 3 unidades

Pampers Supersec (Paquetes verdes/rojos, talle P): 4 unidades

Babysec Premium Soft (Paquetes blancos/violetas, talle XXG): 4 unidades

Desodorantes y Shampoos

Rexona (Aerosol masculino, variedades azul/negro): 3 unidades

Rexona Clinical (Aerosol verde): 1 unidad

Dove Sensitive Care (Aerosol blanco): 2 unidades

Axe Gold (Aerosol negro): 1 unidad

Sedal (Shampoo/Acondicionador, botellas rosas): 3 unidades

Glade (Aerosol para ambientes, pack duplo morado): 1 pack (2 aerosoles)

Wassington Pomada Líquida (Cuidado de calzado): 1 unidad

Jabones en pan / tocador (Plusbelle, Lux, Astro, Sedile): 11 unidades individuales

🍷 Bodega (Vinos y Bebidas Blancas)

Vinos Tintos y Blancos

Colón Selecto (Etiqueta floral morada): 6 unidades

Alma Mora (Etiqueta blanca): 3 unidades

Emilia (Etiqueta blanca con letras negras): 1 unidad

Santa Ana Etiqueta Negra: 2 unidades

Finca Las Moras (Cabernet, etiqueta blanca): 2 unidades

Alaris Dulce Cosecha (Vino blanco): 3 unidades

La Celia (Reserva, etiqueta blanca): 1 unidad

Bianchi (Etiqueta amarilla): 1 unidad

Callia (Etiqueta negra/azul): 1 unidad

San Felipe / Carcassone (Botella caramañola/redonda): 1 unidad

Don Valentín Lacoste: 1 unidad

Viñas de Alvear (Etiqueta amarilla): 4 unidades

Toro (Clásico / Viejo): 2 unidades

Santa Filomena: 2 unidades

Santa Isabel: 1 unidad

Vino en botella damajuana chica: 1 unidad

Otras botellas de vino tinto sin etiqueta frontal visible: ~12 unidades

Aperitivos y Licores

Fernet Branca (Botella oscura tradicional): 2 unidades

Fernet Capri (Etiqueta verde/amarilla): 2 unidades

Gancia (Americano, botella verde): 1 unidad

Frizee / Blue (Botellas azules): 2 unidades

Licor New Style (Café al Cognac / Chocolate): 4 unidades

Licor Tres Plumas / Bols (Menta, botella verde): 1 unidad

Petakon / Blenders Pride / Doble V (Petacas de whisky/licor): 12 unidades

Bols Genebra / Llave (Botella oscura a la derecha): 1 unidad

🥤 Bebidas Sin Alcohol y Lácteos

Gaseosas y Aguas

Manaos Cola: 2 botellas grandes

Manaos Naranja: 3 botellas grandes

Manaos Pomelo Blanco: 1 botella grande

Coca-Cola (Original): 1 botella grande

Paso de los Toros (Pomelo/Tónica): 3 botellas

Agua Mineral Villamanaos (Bidones): 2 unidades

Placer (Saborizados pomelo/manzana): 2 botellas

Aqua Rius (Saborizado rosa): 1 botella

Jugos y Leches

Cepita del Valle (Sabores naranja, multifruta, etc.): 7 botellas

Leche Entera CoLaPa (Cartón / Tetra Brik): 4 unidades Almacén y Yerbas

Yerba Mate y Harinas

Yerba Mate Romance (Paquetes rojos, 500g): 3 unidades

Yerba Mate Romance Sabor Suave (Paquetes verdes): 3 unidades

Yerba Mate Rosamonte (Paquete tradicional): 1 unidad

Yerba Mate Primicia: 1 unidad

Harina de Maíz Indelma (Polenta): 1 unidad

Fecula de Mandioca Aldema (Paquetes blancos/rojos): 2 unidades

Harina Morixe (Pizzas Caseras): 1 unidad

Almidón / Harina (Paquetes blancos al lado de Morixe): 2 unidades

Yerba CBSé (Paquete rosa): 1 unidad

Yerba Don Justo (Paquete amarillo): 1 unidad

Dulces, Cafés y Conservas

Dulce de Leche Milkaut (Potes): 2 unidades

Café Soluble Instantáneo (Frascos de vidrio, tapa negra): 3 unidades

Mermeladas / Dulces en pote (tapa amarilla/naranja): 5 unidades

Conservas en lata S&P (Tomates perita / puré): 3 unidades

Conservas en lata Oinca (Jardinera / Arvejas): 3 unidades

Conservas en lata Pan de Azúcar (Cárnicos / Atún): 2 unidades

Conserva en lata Pennisi (Caballa): 1 unidad

Conservas en lata de pescado / atún chicas (marcas varias): 3 unidades

Puré de Tomate Arcor (Tetra brick): 2 unidades

Puré de Tomate Vicente (Cajitas rojas): 5 unidades

Puré de Tomate La Campagnola (Envase flexible / Sabor Pizza): 1 unidad

Aceites, Caldos y Harinas en Góndola Inferior

Aceite de Girasol Cocinero (Botellas plásticas): 5 unidades

Jugo de Limón Terma (Botellas amarillas): 3 unidades

Exquisita Bizcochuelo (Chocolate / Varios): 2 unidades

Avena en paquete (Amarillo): 2 unidades

Paquetes de fideos / pasta seca (en estante): 2 unidades

Paquetes de arroz / azúcar (en estante inferior): ~12 unidades

🥤 Heladera (Bebidas Frías)

Gaseosas y Aguas en Frío

Sprite (Botellas grandes): 2 unidades

Sprite (Botella mediana): 1 unidad

Coca-Cola (Botella grande): 1 unidad

Fanta Naranja (Botella grande): 1 unidad

Fanta Manzana (Botella mediana): 1 unidad

Gaseosas Cola / Marcas varias en frío: 3 botellas

Cepita del Valle Fresh (Pomelo / Naranja): 3 botellas grandes

Cepita del Valle Jugo (Botella mediana): 1 unidad

Agua Saborizada Aqua Rius: 1 botella grande

Cerveza Heineken (Botella de vidrio): 1 unidad

Cerveza Imperial (Botella de vidrio): 1 unidad

🧼 Higiene, Cuidado Personal y Limpieza

Papel y Rollos de Cocina

Higienol Premium (Paquetes de 4 rollos): 12 paquetes

Higienol Fresh / Export (Paquetes de 4 rollos): 3 paquetes

Campanita Texturado (Paquetes de 4 rollos): 2 paquetes

Elite Doble Hoja (Paquete de 4 rollos): 1 paquete

Sussex Clásico (Paquete grande): 1 paquete

Bonux (Paquetes de rollos de cocina): 2 paquetes de 3 unidades

Vual Rollos de Cocina: 1 paquete de 3 unidades

Sussex Rollos de Cocina (Paquete chico): 1 paquete

Higiene Femenina y Adultos

Toallitas Doncella (Paquetes verdes): 4 unidades

Toallitas Doncella (Paquetes morados): 3 unidades

Toallitas Always Xtra (Paquete azul): 1 unidad

Toallitas Calipso (Paquetes azules): 3 unidades

Toallitas Ladysoft (Paquetes verdes): 2 unidades

Algodón Soft (Potes/Bolsas redondas): 2 unidades

Hisopos / Cotonetes (Potes chicos): 2 unidades

Toallitas húmedas Ayudín (Paquete azul): 2 unidades

Cuidado Corporal y Otros

Desodorante Dove (Aerosol masculino): 1 unidad

Champú / Enjuague Algabo (Envases azules): 2 unidades

Jabón Líquido / Cremas corporales (Varias marcas): 6 botellas chicas

Crema Dental Kolynos (Packs familiares): 2 packs grandes

Desodorante de ambientes en aerosol: 1 unidad

Esmaltes para uñas (Frascos chicos en estante): 6 unidades

Quitaesmalte / Acetona (Frasco de vidrio): 1 unidad

Naipes / Cartas Naveta (Mazo en caja): 1 mazo

🧸 Bazar, Juguetes y Varios

Camiones de juguete grandes (Plástico, naranja y azul): 2 unidades

Autos de juguete medianos/chicos (Plástico, rojo y azul): 3 unidades

Jarra / Termo plástico (Azul, estante superior): 2 unidades

Baldes / Canastos plásticos pequeños: 2 unidades

Mate de madera/metal con bombilla: 1 unidad

Pava de aluminio labrada: 1 unidad

Vasos plásticos estampados (Popcorn): 1 unidad

Platos playos sueltos (Pila en estante): 5 unidades

Peines plásticos para el cabello: 2 unidades
"""


class Command(BaseCommand):
    help = 'Importa o actualiza una lista de productos en bloque con stock y precios en $0.00'

    def add_arguments(self, parser):
        parser.add_argument(
            '--archivo',
            type=str,
            help='Ruta a un archivo de texto con productos a importar en lugar de la lista por defecto.',
            default=None
        )

    def handle(self, *args, **options):
        archivo_path = options['archivo']
        
        if archivo_path:
            self.stdout.write(self.style.WARNING(f"Leyendo inventario desde: {archivo_path}"))
            try:
                with open(archivo_path, 'r', encoding='utf-8') as f:
                    contenido = f.read()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error leyendo el archivo: {e}"))
                return
        else:
            self.stdout.write(self.style.SUCCESS("Usando lista de inventario por defecto cargada en el comando."))
            contenido = TEXTO_INVENTARIO_DEFECTO

        lineas = contenido.split('\n')
        productos_a_procesar = []

        for linea in lineas:
            linea = linea.strip()
            # Si tiene dos puntos, es una línea de producto viable
            if ':' in linea:
                partes = linea.split(':', 1)
                nombre_crudo = partes[0].strip()
                resto = partes[1].strip()

                # Limpieza adicional del nombre (eliminar guiones o viñetas iniciales)
                nombre_limpio = re.sub(r'^[\s\-\*\•\·\x95]+', '', nombre_crudo).strip()

                # Si el nombre queda vacío o es muy corto, ignoramos
                if not nombre_limpio:
                    continue

                # Extraer primer número encontrado en el resto para determinar el stock
                match = re.search(r'(\d+)', resto)
                stock = int(match.group(1)) if match else 1

                productos_a_procesar.append((nombre_limpio, stock))

        if not productos_a_procesar:
            self.stdout.write(self.style.WARNING("No se detectaron productos para importar en el formato esperado (Nombre: Cantidad)."))
            return

        self.stdout.write(f"Se encontraron {len(productos_a_procesar)} productos para procesar. Iniciando importación...")

        creados = 0
        actualizados = 0

        with transaction.atomic():
            for nombre, stock in productos_a_procesar:
                # get_or_create usando el nombre exacto
                # Nota: precio_costo y precio_venta se crean en Decimal('0.00') para que el usuario los edite manualmente
                producto, creado_ahora = Producto.objects.get_or_create(
                    nombre=nombre,
                    defaults={
                        'precio_costo': Decimal('0.00'),
                        'precio_venta': Decimal('0.00'),
                        'stock_actual': stock,
                        'stock_minimo': 5,
                        'activo_en_catalogo': True
                    }
                )

                if creado_ahora:
                    creados += 1
                    self.stdout.write(self.style.SUCCESS(f"[CREADO] '{nombre}' con stock: {stock}"))
                else:
                    # Si ya existe, actualizamos su stock sumándole o asignándole el nuevo valor.
                    # Asignamos directamente el nuevo stock censado para que coincida con el inventario físico.
                    if producto.stock_actual != stock:
                        producto.stock_actual = stock
                        producto.save()
                        actualizados += 1
                        self.stdout.write(self.style.WARNING(f"[ACTUALIZADO STOCK] '{nombre}' -> Nuevo stock: {stock}"))
                    else:
                        self.stdout.write(f"[SIN CAMBIOS] '{nombre}' ya existe con stock correcto: {stock}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\n¡Importación finalizada con éxito!"
                f"\nTotal procesados: {len(productos_a_procesar)}"
                f"\nCreados nuevos: {creados}"
                f"\nStock actualizado de existentes: {actualizados}"
            )
        )
