"""
database.py
Maneja toda la interaccion con SQLite: crear la tabla, registrar ventas,
editarlas, borrarlas y calcular el resumen del dia.
Todas las horas se guardan en hora de Madrid (Europe/Madrid), sin importar
en que zona horaria este configurado el servidor.
"""

import sqlite3
from datetime import datetime
from contextlib import contextmanager
from zoneinfo import ZoneInfo

DB_PATH = "ventas.db"
TZ = ZoneInfo("Europe/Madrid")


def ahora():
    """Fecha y hora actual, siempre en hora de Madrid."""
    return datetime.now(TZ)


def hoy():
    """Fecha de hoy (YYYY-MM-DD) en hora de Madrid."""
    return ahora().strftime("%Y-%m-%d")


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
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
    momento = ahora()
    importe = precio_unitario * cantidad
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO ventas (fecha, hora, tipo, precio_unitario, cantidad, hamacas, metodo_pago, importe)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            momento.strftime("%Y-%m-%d"),
            momento.strftime("%H:%M"),
            tipo,
            precio_unitario,
            cantidad,
            hamacas,
            metodo_pago,
            importe,
        ))


def actualizar_venta(venta_id, tipo, precio_unitario, cantidad, hamacas, metodo_pago):
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
    if fecha is None:
        fecha = hoy()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM ventas WHERE fecha = ? ORDER BY id DESC", (fecha,)
        ).fetchall()
        return [dict(row) for row in rows]


def resumen_dia(fecha=None):
    """
    Resumen completo del dia:
    - total_hamacas, total_importe (como antes)
    - desglose: importe por metodo de pago (como antes, para no romper nada)
    - por_tipo: cantidad e importe por tipo (Primera linea / Resto)
    - por_metodo: cantidad e importe por metodo de pago
    - por_habitacion: cantidad e importe por habitacion (solo ventas "Room charge - X")
    """
    ventas = obtener_ventas_dia(fecha)
    total_hamacas = sum(v["cantidad"] for v in ventas)
    total_importe = sum(v["importe"] for v in ventas)

    desglose = {}
    por_tipo = {}
    por_metodo = {}
    por_habitacion = {}

    for v in ventas:
        # desglose simple (compatibilidad con lo que ya habia)
        desglose[v["metodo_pago"]] = desglose.get(v["metodo_pago"], 0) + v["importe"]

        # por tipo (Primera linea / Resto)
        tipo = v["tipo"]
        if tipo not in por_tipo:
            por_tipo[tipo] = {"cantidad": 0, "importe": 0.0}
        por_tipo[tipo]["cantidad"] += v["cantidad"]
        por_tipo[tipo]["importe"] += v["importe"]

        # por metodo de pago (con cantidad, no solo importe)
        metodo = v["metodo_pago"]
        if metodo not in por_metodo:
            por_metodo[metodo] = {"cantidad": 0, "importe": 0.0}
        por_metodo[metodo]["cantidad"] += v["cantidad"]
        por_metodo[metodo]["importe"] += v["importe"]

        # por habitacion (solo si el metodo empieza por "Room charge - ")
        if metodo.startswith("Room charge - "):
            habitacion = metodo.split(" - ", 1)[1]
            if habitacion not in por_habitacion:
                por_habitacion[habitacion] = {"cantidad": 0, "importe": 0.0}
            por_habitacion[habitacion]["cantidad"] += v["cantidad"]
            por_habitacion[habitacion]["importe"] += v["importe"]

    return {
        "total_hamacas": total_hamacas,
        "total_importe": total_importe,
        "desglose": desglose,
        "por_tipo": por_tipo,
        "por_metodo": por_metodo,
        "por_habitacion": por_habitacion,
    }
