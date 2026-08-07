"""
app.py (NiceGUI version)
Sunbed sales tracker with two tabs:
  - Register: today's form, summary and sales list (no dates involved)
  - History: pick a past day, compare a date range, or compare two days
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


def export_excel(fecha):
    sales = db.obtener_ventas_dia(fecha)
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
    ui.download(buffer.read(), f"sunbed_sales_{fecha}.xlsx")


def render_day_summary(fecha):
    """Builds a compact summary card for a given date, in the current UI context."""
    summary = db.resumen_dia(fecha)
    with ui.card().classes("flex-1 min-w-64"):
        ui.label(fecha).classes("text-lg font-medium mb-1")
        with ui.row().classes("w-full gap-4"):
            with ui.column().classes("gap-0"):
                ui.label("Sunbeds").classes("text-sm text-gray-500")
                ui.label(str(summary["total_hamacas"])).classes("text-xl")
            with ui.column().classes("gap-0"):
                ui.label("Total").classes("text-sm text-gray-500")
                ui.label(f"{summary['total_importe']:.2f} EUR").classes("text-xl")
        if summary["por_tipo"]:
            ui.separator().classes("my-2")
            for tipo, datos in summary["por_tipo"].items():
                with ui.row().classes("w-full justify-between"):
                    ui.label(tipo).classes("text-sm")
                    ui.label(f"{datos['cantidad']} - {datos['importe']:.2f} EUR").classes("text-sm")
        if summary["desglose"]:
            ui.separator().classes("my-2")
            for metodo, importe in summary["desglose"].items():
                with ui.row().classes("w-full justify-between items-center"):
                    ui.badge(metodo, color=method_color(metodo))
                    ui.label(f"{importe:.2f} EUR").classes("text-sm")


# ============================================================
# REGISTER TAB (always today, editable)
# ============================================================

@ui.refreshable
def today_summary_ui():
    fecha = db.hoy()
    summary = db.resumen_dia(fecha)

    with ui.row().classes("w-full gap-4"):
        with ui.card().classes("flex-1"):
            ui.label("Sunbeds sold").classes("text-sm text-gray-500")
            ui.label(str(summary["total_hamacas"])).classes("text-2xl")
        with ui.card().classes("flex-1"):
            ui.label("Total").classes("text-sm text-gray-500")
            ui.label(f"{summary['total_importe']:.2f} EUR").classes("text-2xl")

    if summary["por_tipo"]:
        with ui.row().classes("w-full gap-4 mt-2"):
            for tipo, datos in summary["por_tipo"].items():
                with ui.card().classes("flex-1"):
                    ui.label(tipo).classes("text-sm text-gray-500")
                    ui.label(f"{datos['cantidad']} sunbeds - {datos['importe']:.2f} EUR").classes("text-base")

    if summary["desglose"]:
        with ui.column().classes("w-full gap-1 mt-3"):
            for metodo, importe in summary["desglose"].items():
                with ui.row().classes("w-full justify-between items-center"):
                    ui.badge(metodo, color=method_color(metodo))
                    ui.label(f"{importe:.2f} EUR")

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
def today_sales_list_ui():
    sales = db.obtener_ventas_dia(db.hoy())
    if not sales:
        ui.label("No sales yet today.").classes("text-gray-400")
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
                    ui.button(icon="edit", on_click=lambda s=sale: load_for_edit(s)).props("flat round dense")
                    ui.button(icon="delete", on_click=lambda s=sale: delete_sale(s["id"])).props("flat round dense")


def load_for_edit(sale):
    editing_id["value"] = sale["id"]
    type_input.value = sale["tipo"]
    quantity_state["value"] = sale["cantidad"]
    quantity_label.text = str(sale["cantidad"])
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
    quantity_label.text = "1"
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
    today_sales_list_ui.refresh()
    today_summary_ui.refresh()


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
    today_sales_list_ui.refresh()
    today_summary_ui.refresh()
    ui.notify("Sale saved", type="positive")


def increase_quantity():
    quantity_state["value"] += 1
    quantity_label.text = str(quantity_state["value"])


def decrease_quantity():
    if quantity_state["value"] > 1:
        quantity_state["value"] -= 1
        quantity_label.text = str(quantity_state["value"])


def on_method_change():
    room_selector.set_visibility(method_input.value == "Room charge")


# ============================================================
# HISTORY TAB (day view, range comparison, two-day comparison)
# ============================================================

def refresh_day_view(container, fecha):
    container.clear()
    with container:
        if not fecha:
            return
        render_day_summary(fecha)
        ui.button("Download Excel", icon="download", on_click=lambda: export_excel(fecha)).classes("mt-2")
        ui.label("Sales").classes("text-lg mt-3")
        sales = db.obtener_ventas_dia(fecha)
        if not sales:
            ui.label("No sales for this day.").classes("text-gray-400")
        else:
            for sale in sales:
                with ui.card().classes("w-full"):
                    with ui.row().classes("w-full items-center justify-between"):
                        with ui.column().classes("gap-0"):
                            ui.label(f"{sale['cantidad']}x {sale['tipo']} - {sale['hamacas'] or '-'}").classes("font-medium")
                            with ui.row().classes("items-center gap-2"):
                                ui.badge(sale["metodo_pago"], color=method_color(sale["metodo_pago"]))
                                ui.label(sale["hora"]).classes("text-sm text-gray-500")
                        ui.label(f"{sale['importe']:.2f} EUR").classes("font-medium")


def show_range(container, fecha_inicio, fecha_fin):
    container.clear()
    with container:
        if not fecha_inicio or not fecha_fin:
            ui.label("Pick both dates.").classes("text-gray-400")
            return
        data = db.resumen_rango(fecha_inicio, fecha_fin)
        if not data:
            ui.label("No sales in this range.").classes("text-gray-400")
            return
        total_hamacas = sum(d["total_hamacas"] for d in data)
        total_importe = sum(d["total_importe"] for d in data)
        ui.label(f"Range total: {total_hamacas} sunbeds - {total_importe:.2f} EUR").classes("font-medium mb-3")

        max_total = max(d["total_importe"] for d in data) or 1
        for d in data:
            pct = round((d["total_importe"] / max_total) * 100)
            with ui.column().classes("w-full gap-1 mb-2"):
                with ui.row().classes("w-full justify-between"):
                    ui.label(d["fecha"])
                    ui.label(f"{d['total_hamacas']} sunbeds - {d['total_importe']:.2f} EUR").classes("text-sm text-gray-500")
                with ui.element("div").classes("w-full bg-gray-700 rounded"):
                    ui.element("div").classes("bg-blue-500 rounded").style(f"width:{pct}%; height:8px;")


def show_compare(container, fecha_a, fecha_b):
    container.clear()
    with container:
        if not fecha_a or not fecha_b:
            ui.label("Pick both days.").classes("text-gray-400")
            return
        with ui.row().classes("w-full gap-4 flex-col md:flex-row"):
            render_day_summary(fecha_a)
            render_day_summary(fecha_b)


# ============================================================
# PAGE
# ============================================================

@ui.page("/")
def main_page():
    global type_input, beds_input, method_input, room_input, room_selector
    global save_btn, cancel_btn, edit_notice, quantity_label

    dark = ui.dark_mode(True)
    today = db.hoy()

    with ui.row().classes("w-full items-center justify-between"):
        ui.label("Sunbed Sales").classes("text-2xl")
        ui.button(icon="dark_mode", on_click=lambda: dark.toggle()).props("flat round")

    with ui.tabs().classes("w-full") as tabs:
        register_tab = ui.tab("Register", icon="add_circle")
        history_tab = ui.tab("History", icon="history")

    with ui.tab_panels(tabs, value=register_tab).classes("w-full"):

        # ---------------- REGISTER TAB ----------------
        with ui.tab_panel(register_tab):
            edit_notice = ui.label("").classes("text-blue-500")
            edit_notice.visible = False

            with ui.row().classes("w-full gap-6 flex-col md:flex-row items-start"):
                with ui.card().classes("w-full md:w-96"):
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

                with ui.column().classes("w-full flex-1 gap-4"):
                    with ui.card().classes("w-full"):
                        ui.label("Today's summary").classes("text-lg mb-1")
                        today_summary_ui()
                        ui.button("Download Excel", on_click=lambda: export_excel(db.hoy()), icon="download").classes("mt-2")

                    ui.label("Today's sales").classes("text-lg")
                    today_sales_list_ui()

        # ---------------- HISTORY TAB ----------------
        with ui.tab_panel(history_tab):

            # -- View a specific day --
            ui.label("View a day").classes("text-lg mb-1")
            with ui.row().classes("items-center gap-3"):
                day_view_input = ui.input("Date").props(f'type=date max="{today}"').classes("w-40")
            day_view_container = ui.column().classes("w-full gap-2 mt-2")
            day_view_input.on(
                "update:model-value",
                lambda e: refresh_day_view(day_view_container, day_view_input.value),
            )

            ui.separator().classes("my-4")

            # -- Compare a range --
            with ui.expansion("Compare a date range", icon="date_range").classes("w-full"):
                with ui.row().classes("items-center gap-3"):
                    range_from = ui.input("From").props("type=date").classes("w-40")
                    range_to = ui.input("To").props(f'type=date max="{today}"').classes("w-40")
                    ui.button("Show", on_click=lambda: show_range(range_container, range_from.value, range_to.value))
                range_container = ui.column().classes("w-full mt-3")

            # -- Compare two specific days --
            with ui.expansion("Compare two days", icon="compare_arrows").classes("w-full mt-2"):
                with ui.row().classes("items-center gap-3"):
                    compare_a = ui.input("Day A").props(f'type=date max="{today}"').classes("w-40")
                    compare_b = ui.input("Day B").props(f'type=date max="{today}"').classes("w-40")
                    ui.button("Compare", on_click=lambda: show_compare(compare_container, compare_a.value, compare_b.value))
                compare_container = ui.column().classes("w-full mt-3")


ui.run(host="0.0.0.0", port=8081, title="Sunbed Sales", reload=False)
