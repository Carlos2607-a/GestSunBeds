"""
database.py
Maneja toda la interaccion con SQLite: crear la tabla, registrar ventas,
editarlas, borrarlas y calcular el resumen del dia.
"""

import sqlite3
from datetime import datetime
from contextlib import contextmanager

DB_PATH = "ventas.db"


@contextmanager
def get_connection():
    """Abre y cierra la conexion automaticamente en cada operacion."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Crea la tabla si no existe. Se llama una vez al arrancar la app."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                hora TEXT NOT NULL,
                tipo TEXT NOT NULL,
                precio_unitario REAL NOT NULL,
                cantidad INTEGER NOT NULL,
                hamacas TEXT,
                metodo_pago TEXT NOT NULL,
                importe REAL NOT NULL
            )
        """)


def crear_venta(tipo, precio_unitario, cantidad, hamacas, metodo_pago):
    """Inserta una nueva venta. Calcula el importe automaticamente."""
    ahora = datetime.now()
    importe = precio_unitario * cantidad
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO ventas (fecha, hora, tipo, precio_unitario, cantidad, hamacas, metodo_pago, importe)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ahora.strftime("%Y-%m-%d"),
            ahora.strftime("%H:%M"),
            tipo,
            precio_unitario,
            cantidad,
            hamacas,
            metodo_pago,
            importe,
        ))


def actualizar_venta(venta_id, tipo, precio_unitario, cantidad, hamacas, metodo_pago):
    """Sobrescribe una venta existente (mismo id), recalculando el importe."""
    importe = precio_unitario * cantidad
    with get_connection() as conn:
        conn.execute("""
            UPDATE ventas
            SET tipo = ?, precio_unitario = ?, cantidad = ?, hamacas = ?, metodo_pago = ?, importe = ?
            WHERE id = ?
        """, (tipo, precio_unitario, cantidad, hamacas, metodo_pago, importe, venta_id))


def eliminar_venta(venta_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM ventas WHERE id = ?", (venta_id,))


def obtener_ventas_dia(fecha=None):
    """Devuelve todas las ventas de una fecha (por defecto, hoy), mas recientes primero."""
    if fecha is None:
        fecha = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM ventas WHERE fecha = ? ORDER BY id DESC", (fecha,)
        ).fetchall()
        return [dict(row) for row in rows]


def resumen_dia(fecha=None):
    """Total de hamacas vendidas, total en euros, y desglose por metodo de pago."""
    ventas = obtener_ventas_dia(fecha)
    total_hamacas = sum(v["cantidad"] for v in ventas)
    total_importe = sum(v["importe"] for v in ventas)
    desglose = {}
    for v in ventas:
        desglose[v["metodo_pago"]] = desglose.get(v["metodo_pago"], 0) + v["importe"]
    return {
        "total_hamacas": total_hamacas,
        "total_importe": total_importe,
        "desglose": desglose,
    }