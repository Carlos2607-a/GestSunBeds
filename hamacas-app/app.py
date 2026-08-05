"""
app.py (NiceGUI version)
Sunbed sales tracker. Responsive layout (phone vs tablet/iPad) and dark theme.
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


def update_quantity_label():
    quantity_label.text = str(quantity_state["value"])


def increase_quantity():
    quantity_state["value"] += 1
    update_quantity_label()


def decrease_quantity():
    if quantity_state["value"] > 1:
        quantity_state["value"] -= 1
        update_quantity_label()


@ui.refreshable
def summary_ui():
    summary = db.resumen_dia()
    with ui.row().classes("w-full gap-4"):
        with ui.card().classes("flex-1"):
            ui.label("Sunbeds sold").classes("text-sm text-gray-500")
            ui.label(str(summary["total_hamacas"])).classes("text-2xl")
        with ui.card().classes("flex-1"):
            ui.label("Total").classes("text-sm text-gray-500")
            ui.label(f"{summary['total_importe']:.2f} EUR").classes("text-2xl")
    if summary["desglose"]:
        with ui.column().classes("w-full gap-1 mt-2"):
            for method, amount in summary["desglose"].items():
                color = METHOD_COLORS.get(method, "gray")
                with ui.row().classes("w-full justify-between items-center"):
                    ui.badge(method, color=color)
                    ui.label(f"{amount:.2f} EUR")


@ui.refreshable
def sales_list_ui():
    sales = db.obtener_ventas_dia()
    if not sales:
        ui.label("No sales yet today.").classes("text-gray-400")
        return
    for sale in sales:
        with ui.card().classes("w-full"):
            with ui.row().classes("w-full items-center justify-between"):
                with ui.column().classes("gap-0"):
                    ui.label(f"{sale['cantidad']}x {sale['tipo']} - {sale['hamacas'] or '-'}").classes("font-medium")
                    with ui.row().classes("items-center gap-2"):
                        ui.badge(sale["metodo_pago"], color=METHOD_COLORS.get(sale["metodo_pago"], "gray"))
                        ui.label(sale["hora"]).classes("text-sm text-gray-500")
                with ui.row().classes("items-center gap-1"):
                    ui.label(f"{sale['importe']:.2f} EUR").classes("font-medium")
                    ui.button(icon="edit", on_click=lambda s=sale: load_for_edit(s)).props("flat round dense")
                    ui.button(icon="delete", on_click=lambda s=sale: delete_sale(s["id"])).props("flat round dense")


def load_for_edit(sale):
    editing_id["value"] = sale["id"]
    type_input.value = sale["tipo"]
    quantity_state["value"] = sale["cantidad"]
    update_quantity_label()
    beds_input.value = sale["hamacas"] or ""
    method_input.value = sale["metodo_pago"]
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
    method = method_input.value
    unit_price = PRICES[sale_type]

    if editing_id["value"] is not None:
        db.actualizar_venta(editing_id["value"], sale_type, unit_price, quantity, beds, method)
    else:
        db.crear_venta(sale_type, unit_price, quantity, beds, method)

    cancel_edit()
    sales_list_ui.refresh()
    summary_ui.refresh()
    ui.notify("Sale saved", type="positive")


def export_excel():
    sales = db.obtener_ventas_dia()
    if not sales:
        ui.notify("No sales to export today", type="warning")
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

    ui.download(buffer.read(), f"sunbed_sales_{datetime.now().strftime('%Y-%m-%d')}.xlsx")


@ui.page("/")
def main_page():
    global type_input, beds_input, method_input
    global save_btn, cancel_btn, edit_notice, quantity_label

    dark = ui.dark_mode(True)

    with ui.row().classes("w-full items-center justify-between"):
        ui.label("Sunbed Sales").classes("text-2xl")
        ui.button(icon="dark_mode", on_click=lambda: dark.toggle()).props("flat round")

    edit_notice = ui.label("").classes("text-blue-500")
    edit_notice.visible = False

    # Responsive wrapper: stacked on phones, side-by-side from tablet width up
    with ui.row().classes("w-full gap-6 flex-col md:flex-row items-start"):

        # ---- Left column: registration form ----
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
            method_input = ui.radio(METHODS, value=METHODS[0]).props("inline")

            with ui.row().classes("mt-3"):
                save_btn = ui.button("Register sale", on_click=save_sale)
                cancel_btn = ui.button("Cancel", on_click=cancel_edit, color="gray")
                cancel_btn.visible = False

        # ---- Right column: summary + list ----
        with ui.column().classes("w-full flex-1 gap-4"):
            with ui.card().classes("w-full"):
                ui.label("Today's summary").classes("text-lg mb-1")
                summary_ui()
                ui.button("Download Excel", on_click=export_excel, icon="download").classes("mt-2")

            ui.label("Today's sales").classes("text-lg")
            sales_list_ui()


ui.run(host="0.0.0.0", port=8080, title="Sunbed Sales")