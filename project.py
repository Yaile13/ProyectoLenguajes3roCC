import asyncio
from typing import Dict, List, Optional, Set, Callable
import json
import os
from enum import Enum, auto
from dataclasses import dataclass
from functools import reduce
from concurrent.futures import ThreadPoolExecutor

class EstadoCompra(Enum):
    PENDIENTE = auto()
    COMPRADO = auto()

class CategoriaReceta(Enum):
    DESAYUNO = "Desayuno"
    ALMUERZO = "Almuerzo"
    CENA = "Cena"
    POSTRE = "Postre"

@dataclass
class Receta:
    nombre: str
    categoria: CategoriaReceta
    ingredientes: Set[str]
    pasos: List[str]
    tiempo_preparacion: int  # minutos

@dataclass
class ItemCompra:
    nombre: str
    estado: EstadoCompra = EstadoCompra.PENDIENTE

class GestorRecetas:
    def __init__(self):
        self.recetas: Dict[str, Receta] = {}
        self.lista_compras: Dict[str, ItemCompra] = {}
        self.archivo = "recetas.json"
        
        # Diseño visual
        self.colores = {
            "titulo": "\033[1;36m",  # Cyan brillante
            "exito": "\033[1;32m",   # Verde brillante
            "error": "\033[1;31m",   # Rojo brillante
            "advertencia": "\033[1;33m", # Amarillo brillante
            "normal": "\033[0m"      # Reset
        }

    def filtrar_recetas(self, filtro: Callable[[Receta], bool]) -> List[Receta]:
        return list(filter(filtro, self.recetas.values()))

    def ingredientes_faltantes(self) -> Set[str]:
        return reduce(
            lambda acc, r: acc.union(r.ingredientes),
            self.recetas.values(),
            set()
        ) - set(item.nombre for item in self.lista_compras.values())

    # MÉTODOS ASÍNCRONOS
    async def preparar_receta(self, nombre: str):
        """Simula la preparación paso a paso con async/await"""
        if nombre not in self.recetas:
            self._mostrar_error("¡Receta no encontrada!")
            return False

        receta = self.recetas[nombre]
        self._mostrar_titulo(f"Preparando: {receta.nombre}")
        print(f"\nIngredientes necesarios: {', '.join(receta.ingredientes)}\n")
        
        for i, paso in enumerate(receta.pasos, 1):
            print(f"🔹 Paso {i}/{len(receta.pasos)}: {paso}")
            # Simulamos tiempo de preparación proporcional al paso
            tiempo_paso = max(1, receta.tiempo_preparacion // len(receta.pasos))
            await asyncio.sleep(tiempo_paso)
        
        self._mostrar_exito(f"\n✅ ¡{receta.nombre} listo en {receta.tiempo_preparacion} minutos!")
        return True

    async def guardar_datos(self):
        def _guardar():
            datos = {
                "recetas": {
                    nombre: {
                        "nombre": r.nombre,
                        "categoria": r.categoria.value,
                        "ingredientes": list(r.ingredientes),
                        "pasos": r.pasos,
                        "tiempo_preparacion": r.tiempo_preparacion
                    } for nombre, r in self.recetas.items()
                },
                "lista_compras": [
                    {"nombre": i.nombre, "estado": i.estado.name}
                    for i in self.lista_compras.values()
                ]
            }
            with open(self.archivo, 'w') as f:
                json.dump(datos, f, indent=2)

        await self._ejecutar_en_hilo(_guardar)
        self._mostrar_exito("Datos guardados correctamente")

    async def cargar_datos(self):
        if not os.path.exists(self.archivo):
            return

        def _cargar():
            with open(self.archivo, 'r') as f:
                return json.load(f)

        try:
            datos = await self._ejecutar_en_hilo(_cargar)
            
            # Cargar recetas
            self.recetas = {
                nombre: Receta(
                    nombre=nombre,
                    categoria=CategoriaReceta(datos_r["categoria"]),
                    ingredientes=set(datos_r["ingredientes"]),
                    pasos=datos_r["pasos"],
                    tiempo_preparacion=datos_r["tiempo_preparacion"]
                ) for nombre, datos_r in datos.get("recetas", {}).items()
            }
            
            # Cargar lista de compras
            self.lista_compras = {
                item["nombre"]: ItemCompra(
                    nombre=item["nombre"],
                    estado=EstadoCompra[item["estado"]]
                ) for item in datos.get("lista_compras", [])
            }

        except Exception as e:
            self._mostrar_error(f"Error cargando datos: {str(e)}")

    # MÉTODOS IMPERATIVOS
    def agregar_receta(self, receta: Receta):
        self.recetas[receta.nombre] = receta
        
        # Actualizar lista de compras
        for ingrediente in receta.ingredientes:
            if ingrediente not in self.lista_compras:
                self.lista_compras[ingrediente] = ItemCompra(ingrediente)
        
        self._mostrar_exito(f"Receta '{receta.nombre}' agregada!")

    def eliminar_receta(self, nombre: str):
        if nombre not in self.recetas:
            self._mostrar_error("Receta no encontrada")
            return False
        
        del self.recetas[nombre]
        
        # Actualizar lista de compras
        ingredientes_restantes = reduce(
            lambda acc, r: acc.union(r.ingredientes),
            self.recetas.values(),
            set()
        )
        
        # Eliminar ingredientes que ya no se necesitan
        for ingrediente in list(self.lista_compras.keys()):
            if ingrediente not in ingredientes_restantes:
                del self.lista_compras[ingrediente]
        
        self._mostrar_exito(f"Receta '{nombre}' eliminada")
        return True

    def mostrar_recetas(self):
        self._mostrar_titulo("\n📖 RECETAS DISPONIBLES")
        if not self.recetas:
            print("No hay recetas registradas")
            return False
        
        # Mostrar recetas agrupadas por categoría
        recetas_por_categoria: Dict[CategoriaReceta, List[Receta]] = {}
        for receta in self.recetas.values():
            if receta.categoria not in recetas_por_categoria:
                recetas_por_categoria[receta.categoria] = []
            recetas_por_categoria[receta.categoria].append(receta)
        
        for categoria, recetas in recetas_por_categoria.items():
            print(f"\n🔸 {categoria.value.upper()}:")
            for i, receta in enumerate(recetas, 1):
                print(f"  {i}. {receta.nombre} ({receta.tiempo_preparacion} min)")
                print(f"     Ingredientes: {', '.join(receta.ingredientes)}")
        
        return True

    def mostrar_lista_compras(self):
        self._mostrar_titulo("\n🛒 LISTA DE COMPRAS")
        if not self.lista_compras:
            print("La lista de compras está vacía")
            return False
        
        # Separar items comprados y pendientes
        pendientes = [item for item in self.lista_compras.values() if item.estado == EstadoCompra.PENDIENTE]
        comprados = [item for item in self.lista_compras.values() if item.estado == EstadoCompra.COMPRADO]
        
        if pendientes:
            print("\n🟢 PENDIENTES:")
            for i, item in enumerate(pendientes, 1):
                print(f"  {i}. {item.nombre}")
        
        if comprados:
            print("\n✅ COMPRADOS:")
            for i, item in enumerate(comprados, len(pendientes)+1 if pendientes else 1):
                print(f"  {i}. {item.nombre} (✓)")
        
        return True
    
    async def _ejecutar_en_hilo(self, func: Callable):
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as pool:
            return await loop.run_in_executor(pool, func)

    def _mostrar_titulo(self, texto: str):
        print(f"\n{self.colores['titulo']}{'='*50}")
        print(f"{texto.center(50)}")
        print(f"{'='*50}{self.colores['normal']}")

    def _mostrar_exito(self, texto: str):
        print(f"{self.colores['exito']}{texto}{self.colores['normal']}")

    def _mostrar_error(self, texto: str):
        print(f"{self.colores['error']}{texto}{self.colores['normal']}")

# INTERFAZ DE USUARIO
async def mostrar_menu():
    print("\n" + "="*50)
    print("SISTEMA DE GESTIÓN DE RECETAS".center(50))
    print("="*50)
    print("\n1. Ver recetas")
    print("2. Agregar receta")
    print("3. Eliminar receta")
    print("4. Preparar receta")
    print("5. Ver lista de compras")
    print("6. Gestionar lista de compras")
    print("7. Salir")
    return input("\nSeleccione una opción: ")

async def agregar_receta_interactivo(gestor: GestorRecetas):
    while True:
        gestor._mostrar_titulo("AGREGAR NUEVA RECETA")
        
        nombre = input("Nombre de la receta: ").strip()
        if not nombre:
            gestor._mostrar_error("El nombre no puede estar vacío")
            continue
        
        print("\nCategorías disponibles:")
        for i, cat in enumerate(CategoriaReceta, 1):
            print(f"{i}. {cat.value}")
        
        try:
            opcion = int(input("Seleccione categoría: ")) - 1
            categoria = list(CategoriaReceta)[opcion]
        except (ValueError, IndexError):
            gestor._mostrar_error("Opción no válida")
            continue
        
        print("\nIngredientes (separados por coma):")
        ingredientes = {i.strip() for i in input().split(",") if i.strip()}
        
        print("\nPasos de preparación (1 por línea, termina con 'fin'):")
        pasos = []
        while True:
            paso = input("> ").strip()
            if paso.lower() == 'fin':
                break
            if paso:
                pasos.append(paso)
        
        if not pasos:
            gestor._mostrar_error("Debe ingresar al menos un paso de preparación")
            continue
        
        try:
            tiempo = int(input("\nTiempo de preparación (minutos): "))
            if tiempo <= 0:
                raise ValueError
        except ValueError:
            gestor._mostrar_error("Debe ingresar un número válido mayor a 0")
            continue
        
        nueva_receta = Receta(
            nombre=nombre,
            categoria=categoria,
            ingredientes=ingredientes,
            pasos=pasos,
            tiempo_preparacion=tiempo
        )
        
        gestor.agregar_receta(nueva_receta)
        await gestor.guardar_datos()
        break

async def eliminar_receta_interactivo(gestor: GestorRecetas):
    while True:
        if not gestor.mostrar_recetas():
            await asyncio.sleep(1)
            break
        
        try:
            opcion = input("\nSeleccione receta a eliminar (0 para cancelar): ")
            if opcion == "0":
                break
                
            opcion = int(opcion) - 1
            receta = list(gestor.recetas.values())[opcion]
            if gestor.eliminar_receta(receta.nombre):
                await gestor.guardar_datos()
            break
        except (ValueError, IndexError):
            gestor._mostrar_error("Selección no válida")
            continue

async def preparar_receta_interactivo(gestor: GestorRecetas):
    while True:
        if not gestor.mostrar_recetas():
            await asyncio.sleep(1)
            break
        
        try:
            opcion = input("\nSeleccione receta a preparar (0 para cancelar): ")
            if opcion == "0":
                break
                
            opcion = int(opcion) - 1
            receta = list(gestor.recetas.values())[opcion]
            if await gestor.preparar_receta(receta.nombre):
                break
        except (ValueError, IndexError):
            gestor._mostrar_error("Selección no válida")
            continue

async def gestionar_lista_compras(gestor: GestorRecetas):
    while True:
        if not gestor.mostrar_lista_compras():
            await asyncio.sleep(1)
            break
        
        print("\n1. Marcar como comprado")
        print("2. Eliminar item")
        print("3. Volver")
        opcion = input("\nSeleccione: ")
        
        if opcion == "3":
            break
            
        if opcion not in ["1", "2"]:
            gestor._mostrar_error("Opción no válida")
            continue
            
        try:
            num = input("\nNúmero de item (0 para cancelar): ")
            if num == "0":
                continue
                
            num = int(num) - 1
            item = list(gestor.lista_compras.values())[num]
            
            if opcion == "1":
                item.estado = EstadoCompra.COMPRADO
                await gestor.guardar_datos()
                gestor._mostrar_exito("¡Item marcado como comprado!")
            elif opcion == "2":
                del gestor.lista_compras[item.nombre]
                await gestor.guardar_datos()
                gestor._mostrar_exito("¡Item eliminado de la lista!")
                
        except (ValueError, IndexError):
            gestor._mostrar_error("Selección no válida")
            continue

# EJECUCIÓN PRINCIPAL
async def main():
    gestor = GestorRecetas()
    await gestor.cargar_datos()
    
    while True:
        opcion = await mostrar_menu()
        
        if opcion == "1":
            gestor.mostrar_recetas()
            input("\nPresione Enter para continuar...")
        elif opcion == "2":
            await agregar_receta_interactivo(gestor)
        elif opcion == "3":
            await eliminar_receta_interactivo(gestor)
        elif opcion == "4":
            await preparar_receta_interactivo(gestor)
        elif opcion == "5":
            gestor.mostrar_lista_compras()
            input("\nPresione Enter para continuar...")
        elif opcion == "6":
            await gestionar_lista_compras(gestor)
        elif opcion == "7":
            await gestor.guardar_datos()
            gestor._mostrar_exito("\n¡Hasta pronto! 👋\n")
            break
        else:
            gestor._mostrar_error("\nOpción no válida")
            await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nSaliendo del programa...")