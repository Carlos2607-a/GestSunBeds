"""
app.py (NiceGUI version)
Sunbed sales tracker. Responsive layout, dark theme, date picker for past
days, room sub-selector for "Room charge", and a detailed/expandable
daily summary.
Requires database.py in the same folder.
"""

import io
from datetime import datetime

import pandas as pd
from nicegui import ui

import database as db

db.init_db()

PRICES = {"First row": 50.0, "Rest": 45.0}
METHODS = ["Card", "Cash", "On account", "Room charge"]
ROOMS = ["Malaga", "Cordoba", "Jerez", "Granada", "Sevilla"]
METHOD_COLORS = {
    "Card": "blue",
    "Cash": "green",
    "On account": "orange",
    "Room charge": "purple",
}

editing_id = {"value": None}
quantity_state = {"value": 1}
selected_date = {"value": db.hoy()}


def is_today():
    return selected_date["value"] == db.hoy()


def format_beds(text):
    """Turns '4, 12' into 'H4, H12'. Leaves an already-prefixed 'H4' as is."""
    parts = [p.strip() for p in text.split(",") if p.strip()]
    formatted = []
    for p in parts:
        formatted.append(p.upper() if p.upper().startswith("H") else f"H{p}")
    return ", ".join(formatted)


def method_color(method):
    """Room charge is stored as 'Room charge - Malaga', so match by prefix."""
    if method.startswith("Room charge"):
        return "purple"
    return METHOD_COLORS.get(method, "gray")


def update_quantity_label():
    quantity_label.text = str(quantity_state["value"])


def increase_quantity():
    quantity_state["value"] += 1
    update_quantity_label()


def decrease_quantity():
    if quantity_state["value"] > 1:
        quantity_state["value"] -= 1
        update_quantity_label()


def on_method_change():
    room_selector.set_visibility(method_input.value == "Room charge")


@ui.refreshable
def summary_ui():
    summary = db.resumen_dia(selected_date["value"])

    # ---- Totals ----
    with ui.row().classes("w-full gap-4"):
        with ui.card().classes("flex-1"):
            ui.label("Sunbeds sold").classes("text-sm text-gray-500")
            ui.label(str(summary["total_hamacas"])).classes("text-2xl")
        with ui.card().classes("flex-1"):
            ui.label("Total").classes("text-sm text-gray-500")
            ui.label(f"{summary['total_importe']:.2f} EUR").classes("text-2xl")

    # ---- By type (First row / Rest) ----
    if summary["por_tipo"]:
        with ui.row().classes("w-full gap-4 mt-2"):
            for tipo, datos in summary["por_tipo"].items():
                with ui.card().classes("flex-1"):
                    ui.label(tipo).classes("text-sm text-gray-500")
                    ui.label(f"{datos['cantidad']} sunbeds - {datos['importe']:.2f} EUR").classes("text-base")

    # ---- Quick breakdown by payment method ----
    if summary["desglose"]:
        with ui.column().classes("w-full gap-1 mt-3"):
            for metodo, importe in summary["desglose"].items():
                with ui.row().classes("w-full justify-between items-center"):
                    ui.badge(metodo, color=method_color(metodo))
                    ui.label(f"{importe:.2f} EUR")

    # ---- Expandable detail ----
    if summary["total_hamacas"] > 0:
        with ui.expansion("See more detail", icon="expand_more").classes("w-full mt-3"):
            ui.label("Payment methods").classes("text-sm text-gray-500 mt-1")
            for metodo, datos in summary["por_metodo"].items():
                with ui.row().classes("w-full justify-between items-center"):
                    ui.badge(metodo, color=method_color(metodo))
                    ui.label(f"{datos['cantidad']} sunbeds - {datos['importe']:.2f} EUR")

            if summary["por_habitacion"]:
                ui.label("Room charge breakdown").classes("text-sm text-gray-500 mt-3")
                for room, datos in summary["por_habitacion"].items():
                    with ui.row().classes("w-full justify-between items-center"):
                        ui.label(room)
                        ui.label(f"{datos['cantidad']} sunbeds - {datos['importe']:.2f} EUR")

            ui.label("By sunbed type").classes("text-sm text-gray-500 mt-3")
            for tipo, datos in summary["por_tipo"].items():
                with ui.row().classes("w-full justify-between items-center"):
                    ui.label(tipo)
                    ui.label(f"{datos['cantidad']} sunbeds - {datos['importe']:.2f} EUR")


@ui.refreshable
def sales_list_ui():
    sales = db.obtener_ventas_dia(selected_date["value"])
    if not sales:
        ui.label("No sales for this day.").classes("text-gray-400")
        return
    for sale in sales:
        with ui.card().classes("w-full"):
            with ui.row().classes("w-full items-center justify-between"):
                with ui.column().classes("gap-0"):
                    ui.label(f"{sale['cantidad']}x {sale['tipo']} - {sale['hamacas'] or '-'}").classes("font-medium")
                    with ui.row().classes("items-center gap-2"):
                        ui.badge(sale["metodo_pago"], color=method_color(sale["metodo_pago"]))
                        ui.label(sale["hora"]).classes("text-sm text-gray-500")
                with ui.row().classes("items-center gap-1"):
                    ui.label(f"{sale['importe']:.2f} EUR").classes("font-medium")
                    if is_today():
                        ui.button(icon="edit", on_click=lambda s=sale: load_for_edit(s)).props("flat round dense")
                        ui.button(icon="delete", on_click=lambda s=sale: delete_sale(s["id"])).props("flat round dense")


def load_for_edit(sale):
    editing_id["value"] = sale["id"]
    type_input.value = sale["tipo"]
    quantity_state["value"] = sale["cantidad"]
    update_quantity_label()
    beds_input.value = sale["hamacas"] or ""

    stored_method = sale["metodo_pago"]
    if stored_method.startswith("Room charge"):
        method_input.value = "Room charge"
        room_name = stored_method.split(" - ", 1)[1] if " - " in stored_method else ROOMS[0]
        room_input.value = room_name
    else:
        method_input.value = stored_method
    on_method_change()

    save_btn.text = "Save changes"
    cancel_btn.visible = True
    edit_notice.text = f"Editing sale #{sale['id']}"
    edit_notice.visible = True


def cancel_edit():
    editing_id["value"] = None
    type_input.value = "First row"
    quantity_state["value"] = 1
    update_quantity_label()
    beds_input.value = ""
    method_input.value = METHODS[0]
    room_input.value = ROOMS[0]
    on_method_change()
    save_btn.text = "Register sale"
    cancel_btn.visible = False
    edit_notice.visible = False


def delete_sale(sale_id):
    db.eliminar_venta(sale_id)
    if editing_id["value"] == sale_id:
        cancel_edit()
    sales_list_ui.refresh()
    summary_ui.refresh()


def save_sale():
    sale_type = type_input.value
    quantity = quantity_state["value"]
    beds = format_beds(beds_input.value or "")
    unit_price = PRICES[sale_type]

    if method_input.value == "Room charge":
        method = f"Room charge - {room_input.value}"
    else:
        method = method_input.value

    if editing_id["value"] is not None:
        db.actualizar_venta(editing_id["value"], sale_type, unit_price, quantity, beds, method)
    else:
        db.crear_venta(sale_type, unit_price, quantity, beds, method)

    cancel_edit()
    sales_list_ui.refresh()
    summary_ui.refresh()
    ui.notify("Sale saved", type="positive")


def export_excel():
    sales = db.obtener_ventas_dia(selected_date["value"])
    if not sales:
        ui.notify("No sales to export for this day", type="warning")
        return

    df = pd.DataFrame(sales).rename(columns={
        "fecha": "Date", "hora": "Time", "tipo": "Type",
        "precio_unitario": "Unit price", "cantidad": "Quantity",
        "hamacas": "Sunbeds", "metodo_pago": "Payment method", "importe": "Amount",
    })[["Date", "Time", "Type", "Unit price", "Quantity", "Sunbeds", "Payment method", "Amount"]]

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sales")
    buffer.seek(0)

    ui.download(buffer.read(), f"sunbed_sales_{selected_date['value']}.xlsx")


def on_date_change(event):
    selected_date["value"] = event.value
    day_label.text = "Today" if is_today() else selected_date["value"]
    cancel_edit()
    summary_ui.refresh()
    sales_list_ui.refresh()
    form_card.set_visibility(is_today())


def go_to_today():
    date_input.value = db.hoy()


@ui.page("/")
def main_page():
    global type_input, beds_input, method_input, room_input, room_selector
    global save_btn, cancel_btn, edit_notice, quantity_label
    global date_input, day_label, form_card

    dark = ui.dark_mode(True)

    with ui.row().classes("w-full items-center justify-between"):
        ui.label("Sunbed Sales").classes("text-2xl")
        ui.button(icon="dark_mode", on_click=lambda: dark.toggle()).props("flat round")

    edit_notice = ui.label("").classes("text-blue-500")
    edit_notice.visible = False

    with ui.row().classes("w-full items-center gap-3"):
        date_input = ui.date(value=selected_date["value"], on_change=on_date_change) \
            .props(f'max="{db.hoy()}"')
        day_label = ui.label("Today").classes("text-lg")
        ui.button("Back to today", on_click=go_to_today).props("flat dense")

    with ui.row().classes("w-full gap-6 flex-col md:flex-row items-start"):

        # ---- Left column: registration form (only for today) ----
        with ui.card().classes("w-full md:w-96") as form_card:
            ui.label("New sale").classes("text-lg mb-1")
            type_input = ui.radio(list(PRICES.keys()), value="First row").props("inline")

            with ui.row().classes("items-center gap-4 mt-2"):
                ui.label("Quantity")
                ui.button(icon="remove", on_click=decrease_quantity).props("flat round dense")
                quantity_label = ui.label("1").classes("text-lg w-6 text-center")
                ui.button(icon="add", on_click=increase_quantity).props("flat round dense")

            beds_input = ui.input("Sunbed number(s)", placeholder="E.g. 4, 12").classes("w-full mt-2")

            ui.label("Payment method").classes("text-sm text-gray-500 mt-2")
            method_input = ui.radio(METHODS, value=METHODS[0], on_change=on_method_change).props("inline")

            with ui.column().classes("w-full gap-1") as room_selector:
                ui.label("Room").classes("text-sm text-gray-500 mt-1")
                room_input = ui.radio(ROOMS, value=ROOMS[0]).props("inline")
            room_selector.set_visibility(False)

            with ui.row().classes("mt-3"):
                save_btn = ui.button("Register sale", on_click=save_sale)
                cancel_btn = ui.button("Cancel", on_click=cancel_edit, color="gray")
                cancel_btn.visible = False

        # ---- Right column: summary + list ----
        with ui.column().classes("w-full flex-1 gap-4"):
            with ui.card().classes("w-full"):
                ui.label("Summary").classes("text-lg mb-1")
                summary_ui()
                ui.button("Download Excel", on_click=export_excel, icon="download").classes("mt-2")

            ui.label("Sales").classes("text-lg")
            sales_list_ui()


ui.run(host="0.0.0.0", port=8081, title="Sunbed Sales", reload=False)
