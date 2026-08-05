"""
app.py (version NiceGUI)
Interfaz para registrar ventas de hamacas.
Requiere database.py en la misma carpeta.
"""

import io
from datetime import datetime

import pandas as pd
from nicegui import ui

import database as db

db.init_db()

PRECIOS = {"Primera linea": 50.0, "Resto": 45.0}
METODOS = ["Datafono", "Efectivo", "A cuenta", "Habitacion"]

editando_id = {"value": None}
cantidad_state = {"value": 1}


def format_hamacas(texto):
    """Convierte '4, 12' en 'H4, H12'. Si ya trae la H, la respeta."""
    partes = [p.strip() for p in texto.split(",") if p.strip()]
    formateadas = []
    for p in partes:
        if p.upper().startswith("H"):
            formateadas.append(p.upper())
        else:
            formateadas.append(f"H{p}")
    return ", ".join(formateadas)


def actualizar_cantidad_label():
    cantidad_label.text = str(cantidad_state["value"])


def sumar_cantidad():
    cantidad_state["value"] += 1
    actualizar_cantidad_label()


def restar_cantidad():
    if cantidad_state["value"] > 1:
        cantidad_state["value"] -= 1
        actualizar_cantidad_label()


@ui.refreshable
def resumen_ui():
    resumen = db.resumen_dia()
    with ui.row().classes("w-full gap-4"):
        with ui.card().classes("flex-1"):
            ui.label("Hamacas vendidas").classes("text-sm text-gray-500")
            ui.label(str(resumen["total_hamacas"])).classes("text-2xl")
        with ui.card().classes("flex-1"):
            ui.label("Total").classes("text-sm text-gray-500")
            ui.label(f"{resumen['total_importe']:.2f} EUR").classes("text-2xl")
    if resumen["desglose"]:
        with ui.column().classes("w-full gap-1 mt-2"):
            for metodo_pago, importe in resumen["desglose"].items():
                with ui.row().classes("w-full justify-between"):
                    ui.label(metodo_pago)
                    ui.label(f"{importe:.2f} EUR")


@ui.refreshable
def lista_ui():
    ventas = db.obtener_ventas_dia()
    if not ventas:
        ui.label("Sin ventas todavia.").classes("text-gray-400")
        return
    for venta in ventas:
        with ui.row().classes("w-full items-center justify-between border-t py-2"):
            with ui.column().classes("gap-0"):
                ui.label(f"{venta['cantidad']}x {venta['tipo']} - {venta['hamacas'] or '-'}").classes("font-medium")
                ui.label(f"{venta['metodo_pago']} - {venta['hora']}").classes("text-sm text-gray-500")
            with ui.row().classes("items-center gap-1"):
                ui.label(f"{venta['importe']:.2f} EUR").classes("font-medium")
                ui.button(icon="edit", on_click=lambda v=venta: cargar_edicion(v)).props("flat round dense")
                ui.button(icon="delete", on_click=lambda v=venta: borrar(v["id"])).props("flat round dense")


def cargar_edicion(venta):
    editando_id["value"] = venta["id"]
    tipo_input.value = venta["tipo"]
    cantidad_state["value"] = venta["cantidad"]
    actualizar_cantidad_label()
    hamacas_input.value = venta["hamacas"] or ""
    metodo_input.value = venta["metodo_pago"]
    registrar_btn.text = "Guardar cambios"
    cancelar_btn.visible = True
    aviso_edicion.text = f"Editando venta #{venta['id']}"
    aviso_edicion.visible = True


def cancelar_edicion():
    editando_id["value"] = None
    tipo_input.value = "Primera linea"
    cantidad_state["value"] = 1
    actualizar_cantidad_label()
    hamacas_input.value = ""
    metodo_input.value = METODOS[0]
    registrar_btn.text = "Registrar venta"
    cancelar_btn.visible = False
    aviso_edicion.visible = False


def borrar(venta_id):
    db.eliminar_venta(venta_id)
    if editando_id["value"] == venta_id:
        cancelar_edicion()
    lista_ui.refresh()
    resumen_ui.refresh()


def guardar():
    tipo = tipo_input.value
    cantidad = cantidad_state["value"]
    hamacas = format_hamacas(hamacas_input.value or "")
    metodo = metodo_input.value
    precio = PRECIOS[tipo]

    if editando_id["value"] is not None:
        db.actualizar_venta(editando_id["value"], tipo, precio, cantidad, hamacas, metodo)
    else:
        db.crear_venta(tipo, precio, cantidad, hamacas, metodo)

    cancelar_edicion()
    lista_ui.refresh()
    resumen_ui.refresh()
    ui.notify("Venta guardada", type="positive")


def exportar():
    ventas = db.obtener_ventas_dia()
    if not ventas:
        ui.notify("No hay ventas que exportar hoy", type="warning")
        return

    df = pd.DataFrame(ventas).rename(columns={
        "fecha": "Fecha", "hora": "Hora", "tipo": "Tipo",
        "precio_unitario": "Precio unitario", "cantidad": "Cantidad",
        "hamacas": "Hamacas", "metodo_pago": "Metodo de pago", "importe": "Importe",
    })[["Fecha", "Hora", "Tipo", "Precio unitario", "Cantidad", "Hamacas", "Metodo de pago", "Importe"]]

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Ventas")
    buffer.seek(0)

    ui.download(buffer.read(), f"ventas_hamacas_{datetime.now().strftime('%Y-%m-%d')}.xlsx")


@ui.page("/")
def main_page():
    global tipo_input, hamacas_input, metodo_input
    global registrar_btn, cancelar_btn, aviso_edicion, cantidad_label

    ui.label("Ventas de hamacas").classes("text-2xl mb-2")

    aviso_edicion = ui.label("").classes("text-blue-600")
    aviso_edicion.visible = False

    with ui.card().classes("w-full max-w-md"):
        tipo_input = ui.radio(list(PRECIOS.keys()), value="Primera linea").props("inline")

        with ui.row().classes("items-center gap-4 mt-2"):
            ui.label("Cantidad")
            ui.button(icon="remove", on_click=restar_cantidad).props("flat round dense")
            cantidad_label = ui.label("1").classes("text-lg w-6 text-center")
            ui.button(icon="add", on_click=sumar_cantidad).props("flat round dense")

        hamacas_input = ui.input("Numero de hamaca(s)", placeholder="Ej: 4, 12").classes("w-full mt-2")
        metodo_input = ui.radio(METODOS, value=METODOS[0]).props("inline")

        with ui.row().classes("mt-2"):
            registrar_btn = ui.button("Registrar venta", on_click=guardar)
            cancelar_btn = ui.button("Cancelar", on_click=cancelar_edicion, color="gray")
            cancelar_btn.visible = False

    ui.separator().classes("my-4")
    ui.label("Resumen del dia").classes("text-lg")
    resumen_ui()
    ui.button("Descargar Excel del dia", on_click=exportar, icon="download").classes("mt-2")

    ui.separator().classes("my-4")
    ui.label("Ventas de hoy").classes("text-lg")
    lista_ui()


ui.run(host="0.0.0.0", port=8080, title="Ventas de hamacas")