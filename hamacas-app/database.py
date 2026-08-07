"""
database.py
Maneja toda la interaccion con SQLite: crear la tabla, registrar ventas,
editarlas, borrarlas y calcular resumenes.
Todas las horas se guardan en hora de Madrid (Europe/Madrid).
Cada venta tiene un "producto": 'Sunbed' o 'Big Bed', para poder
reportarlos por separado.
"""

import sqlite3
from datetime import datetime
from contextlib import contextmanager
from zoneinfo import ZoneInfo

DB_PATH = "ventas.db"
TZ = ZoneInfo("Europe/Madrid")


def ahora():
    return datetime.now(TZ)


def hoy():
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
                producto TEXT NOT NULL DEFAULT 'Sunbed',
                tipo TEXT NOT NULL,
                precio_unitario REAL NOT NULL,
                cantidad INTEGER NOT NULL,
                hamacas TEXT,
                metodo_pago TEXT NOT NULL,
                importe REAL NOT NULL
            )
        """)
        # Migration: if the table already existed without "producto"
        # (from before Big Beds existed), add it and default old rows to Sunbed.
        cols = [row["name"] for row in conn.execute("PRAGMA table_info(ventas)").fetchall()]
        if "producto" not in cols:
            conn.execute("ALTER TABLE ventas ADD COLUMN producto TEXT NOT NULL DEFAULT 'Sunbed'")


def crear_venta(producto, tipo, precio_unitario, cantidad, hamacas, metodo_pago):
    momento = ahora()
    importe = precio_unitario * cantidad
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO ventas (fecha, hora, producto, tipo, precio_unitario, cantidad, hamacas, metodo_pago, importe)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            momento.strftime("%Y-%m-%d"),
            momento.strftime("%H:%M"),
            producto,
            tipo,
            precio_unitario,
            cantidad,
            hamacas,
            metodo_pago,
            importe,
        ))


def actualizar_venta(venta_id, producto, tipo, precio_unitario, cantidad, hamacas, metodo_pago):
    importe = precio_unitario * cantidad
    with get_connection() as conn:
        conn.execute("""
            UPDATE ventas
            SET producto = ?, tipo = ?, precio_unitario = ?, cantidad = ?, hamacas = ?, metodo_pago = ?, importe = ?
            WHERE id = ?
        """, (producto, tipo, precio_unitario, cantidad, hamacas, metodo_pago, importe, venta_id))


def eliminar_venta(venta_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM ventas WHERE id = ?", (venta_id,))


def obtener_ventas_dia(fecha=None, producto=None):
    """Todas las ventas de una fecha. Si se pasa 'producto', filtra solo ese ('Sunbed' o 'Big Bed')."""
    if fecha is None:
        fecha = hoy()
    with get_connection() as conn:
        if producto:
            rows = conn.execute(
                "SELECT * FROM ventas WHERE fecha = ? AND producto = ? ORDER BY id DESC",
                (fecha, producto),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM ventas WHERE fecha = ? ORDER BY id DESC", (fecha,)
            ).fetchall()
        return [dict(row) for row in rows]


def resumen_dia(fecha=None, producto=None):
    """
    Resumen de un dia, opcionalmente filtrado a un solo producto
    ('Sunbed' o 'Big Bed'). Si producto es None, junta ambos.
    """
    ventas = obtener_ventas_dia(fecha, producto)
    total_hamacas = sum(v["cantidad"] for v in ventas)
    total_importe = sum(v["importe"] for v in ventas)

    desglose = {}
    por_tipo = {}
    por_metodo = {}
    por_habitacion = {}

    for v in ventas:
        desglose[v["metodo_pago"]] = desglose.get(v["metodo_pago"], 0) + v["importe"]

        tipo = v["tipo"]
        if tipo not in por_tipo:
            por_tipo[tipo] = {"cantidad": 0, "importe": 0.0}
        por_tipo[tipo]["cantidad"] += v["cantidad"]
        por_tipo[tipo]["importe"] += v["importe"]

        metodo = v["metodo_pago"]
        if metodo not in por_metodo:
            por_metodo[metodo] = {"cantidad": 0, "importe": 0.0}
        por_metodo[metodo]["cantidad"] += v["cantidad"]
        por_metodo[metodo]["importe"] += v["importe"]

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


def resumen_rango(fecha_inicio, fecha_fin, producto=None):
    """Total por dia dentro de un rango, opcionalmente filtrado por producto."""
    with get_connection() as conn:
        if producto:
            rows = conn.execute("""
                SELECT fecha, SUM(cantidad) AS total_hamacas, SUM(importe) AS total_importe
                FROM ventas
                WHERE fecha BETWEEN ? AND ? AND producto = ?
                GROUP BY fecha
                ORDER BY fecha
            """, (fecha_inicio, fecha_fin, producto)).fetchall()
        else:
            rows = conn.execute("""
                SELECT fecha, SUM(cantidad) AS total_hamacas, SUM(importe) AS total_importe
                FROM ventas
                WHERE fecha BETWEEN ? AND ?
                GROUP BY fecha
                ORDER BY fecha
            """, (fecha_inicio, fecha_fin)).fetchall()
        return [dict(row) for row in rows]