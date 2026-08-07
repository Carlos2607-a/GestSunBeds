"""
app.py (NiceGUI version)
Sunbed + Big Bed sales tracker with login (seller / admin roles).
Requires database.py in the same folder.
"""

import hashlib
import io
from datetime import datetime

import pandas as pd
from nicegui import app, ui

import database as db

db.init_db()

# ============================================================
# USERS -- CHANGE THESE before going live.
# ============================================================

def _hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

USERS = {
    "hamaquero": {"password_hash": _hash("playa2026"), "role": "seller"},
    "admin": {"password_hash": _hash("admin2026"), "role": "admin"},
}

# ---- Sunbeds ----
SUNBED_PRICES = {"First row": 50.0, "Rest": 45.0}

# ---- Big Beds ----
BIGBED_UNITS = [f"Lux{i}" for i in range(1, 9)]
BIGBED_PACKAGES = [325.0, 355.0, 375.0, 395.0]

PRODUCTS = ["Sunbed", "Big Bed"]

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


def format_code(text, prefix):
    """Turns '4, 12' into 'H4, H12' (or 'Lux1, Lux3' for Big Beds)."""
    parts = [p.strip() for p in text.split(",") if p.strip()]
    formatted = []
    for p in parts:
        formatted.append(p if p.upper().startswith(prefix.upper()) else f"{prefix}{p}")
    return ", ".join(formatted)


def method_color(method):
    if method.startswith("Room charge"):
        return "purple"
    return METHOD_COLORS.get(method, "gray")


def export_excel(fecha, producto=None):
    sales = db.obtener_ventas_dia(fecha, producto)
    if not sales:
        ui.notify("No sales to export for this day", type="warning")
        return
    df = pd.DataFrame(sales).rename(columns={
        "fecha": "Date", "hora": "Time", "producto": "Product", "tipo": "Type",
        "precio_unitario": "Unit price", "cantidad": "Quantity",
        "hamacas": "Unit(s)", "metodo_pago": "Payment method", "importe": "Amount",
    })[["Date", "Time", "Product", "Type", "Unit price", "Quantity", "Unit(s)", "Payment method", "Amount"]]
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sales")
    buffer.seek(0)
    suffix = f"_{producto.lower().replace(' ', '')}" if producto else ""
    ui.download(buffer.read(), f"sales_{fecha}{suffix}.xlsx")


def render_product_summary(fecha, producto, label):
    """Compact summary card for one product on one day."""
    summary = db.resumen_dia(fecha, producto)
    with ui.card().classes("w-full"):
        ui.label(label).classes("text-lg mb-1")
        with ui.row().classes("w-full gap-4"):
            with ui.card().classes("flex-1"):
                ui.label("Sold").classes("text-sm text-gray-500")
                ui.label(str(summary["total_hamacas"])).classes("text-2xl")
            with ui.card().classes("flex-1"):
                ui.label("Total").classes("text-sm text-gray-500")
                ui.label(f"{summary['total_importe']:.2f} EUR").classes("text-2xl")

        if summary["por_tipo"]:
            with ui.row().classes("w-full gap-4 mt-2 flex-wrap"):
                for tipo, datos in summary["por_tipo"].items():
                    with ui.card().classes("flex-1 min-w-32"):
                        ui.label(tipo).classes("text-sm text-gray-500")
                        ui.label(f"{datos['cantidad']} - {datos['importe']:.2f} EUR").classes("text-base")

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
                        ui.label(f"{datos['cantidad']} - {datos['importe']:.2f} EUR")

                if summary["por_habitacion"]:
                    ui.label("Room charge breakdown").classes("text-sm text-gray-500 mt-3")
                    for room, datos in summary["por_habitacion"].items():
                        with ui.row().classes("w-full justify-between items-center"):
                            ui.label(room)
                            ui.label(f"{datos['cantidad']} - {datos['importe']:.2f} EUR")

        ui.button(f"Download {label} Excel", icon="download",
                   on_click=lambda: export_excel(fecha, producto)).classes("mt-3")


def render_day_summary_combined(fecha):
    """Used for range/compare views: totals across BOTH products together."""
    summary = db.resumen_dia(fecha)
    with ui.card().classes("flex-1 min-w-64"):
        ui.label(fecha).classes("text-lg font-medium mb-1")
        with ui.row().classes("w-full gap-4"):
            with ui.column().classes("gap-0"):
                ui.label("Units sold").classes("text-sm text-gray-500")
                ui.label(str(summary["total_hamacas"])).classes("text-xl")
            with ui.column().classes("gap-0"):
                ui.label("Total").classes("text-sm text-gray-500")
                ui.label(f"{summary['total_importe']:.2f} EUR").classes("text-xl")
        if summary["desglose"]:
            ui.separator().classes("my-2")
            for metodo, importe in summary["desglose"].items():
                with ui.row().classes("w-full justify-between items-center"):
                    ui.badge(metodo, color=method_color(metodo))
                    ui.label(f"{importe:.2f} EUR").classes("text-sm")


# ============================================================
# REGISTER TAB
# ============================================================

@ui.refreshable
def today_summaries_ui():
    with ui.column().classes("w-full gap-4"):
        render_product_summary(db.hoy(), "Sunbed", "Sunbeds")
        render_product_summary(db.hoy(), "Big Bed", "Big Beds")


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
                    ui.label(f"[{sale['producto']}] {sale['cantidad']}x {sale['tipo']} - {sale['hamacas'] or '-'}").classes("font-medium")
                    with ui.row().classes("items-center gap-2"):
                        ui.badge(sale["metodo_pago"], color=method_color(sale["metodo_pago"]))
                        ui.label(sale["hora"]).classes("text-sm text-gray-500")
                with ui.row().classes("items-center gap-1"):
                    ui.label(f"{sale['importe']:.2f} EUR").classes("font-medium")
                    ui.button(icon="edit", on_click=lambda s=sale: load_for_edit(s)).props("flat round dense")
                    ui.button(icon="delete", on_click=lambda s=sale: delete_sale(s["id"])).props("flat round dense")


def on_product_change():
    is_sunbed = product_input.value == "Sunbed"
    sunbed_fields.set_visibility(is_sunbed)
    bigbed_fields.set_visibility(not is_sunbed)


def on_custom_price_change():
    custom_price_input.set_visibility(custom_price_switch.value)


def load_for_edit(sale):
    editing_id["value"] = sale["id"]
    product_input.value = sale["producto"]
    quantity_state["value"] = sale["cantidad"]
    quantity_label.text = str(sale["cantidad"])

    if sale["producto"] == "Sunbed":
        type_input.value = sale["tipo"]
        beds_input.value = sale["hamacas"] or ""
    else:
        unit_input.value = sale["hamacas"] or ""
        if sale["precio_unitario"] in BIGBED_PACKAGES:
            package_input.value = sale["precio_unitario"]
            custom_price_switch.value = False
        else:
            custom_price_switch.value = True
            custom_price_input.value = sale["precio_unitario"]
    on_product_change()
    on_custom_price_change()

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
    product_input.value = "Sunbed"
    quantity_state["value"] = 1
    quantity_label.text = "1"
    type_input.value = "First row"
    beds_input.value = ""
    unit_input.value = ""
    package_input.value = BIGBED_PACKAGES[0]
    custom_price_switch.value = False
    custom_price_input.value = None
    method_input.value = METHODS[0]
    room_input.value = ROOMS[0]
    on_product_change()
    on_custom_price_change()
    on_method_change()
    save_btn.text = "Register sale"
    cancel_btn.visible = False
    edit_notice.visible = False


def delete_sale(sale_id):
    db.eliminar_venta(sale_id)
    if editing_id["value"] == sale_id:
        cancel_edit()
    today_sales_list_ui.refresh()
    today_summaries_ui.refresh()


def save_sale():
    quantity = quantity_state["value"]
    producto = product_input.value

    if producto == "Sunbed":
        tipo = type_input.value
        unit_price = SUNBED_PRICES[tipo]
        unidades = format_code(beds_input.value or "", "H")
    else:
        if custom_price_switch.value:
            if not custom_price_input.value or custom_price_input.value <= 0:
                ui.notify("Enter a valid custom price", type="warning")
                return
            unit_price = float(custom_price_input.value)
            tipo = "Custom price"
        else:
            unit_price = float(package_input.value)
            tipo = f"Package {int(unit_price)}"
        unidades = format_code(unit_input.value or "", "Lux")

    if method_input.value == "Room charge":
        method = f"Room charge - {room_input.value}"
    else:
        method = method_input.value

    if editing_id["value"] is not None:
        db.actualizar_venta(editing_id["value"], producto, tipo, unit_price, quantity, unidades, method)
    else:
        db.crear_venta(producto, tipo, unit_price, quantity, unidades, method)

    cancel_edit()
    today_sales_list_ui.refresh()
    today_summaries_ui.refresh()
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


def register_content():
    global product_input, type_input, beds_input, unit_input, package_input
    global custom_price_switch, custom_price_input, sunbed_fields, bigbed_fields
    global method_input, room_input, room_selector
    global save_btn, cancel_btn, edit_notice, quantity_label

    editing_id["value"] = None
    quantity_state["value"] = 1

    edit_notice = ui.label("").classes("text-blue-500")
    edit_notice.visible = False

    with ui.row().classes("w-full gap-6 flex-col md:flex-row items-start"):
        with ui.card().classes("w-full md:w-96"):
            ui.label("New sale").classes("text-lg mb-1")

            product_input = ui.radio(PRODUCTS, value="Sunbed", on_change=on_product_change).props("inline")

            with ui.row().classes("items-center gap-4 mt-2"):
                ui.label("Quantity")
                ui.button(icon="remove", on_click=decrease_quantity).props("flat round dense")
                quantity_label = ui.label("1").classes("text-lg w-6 text-center")
                ui.button(icon="add", on_click=increase_quantity).props("flat round dense")

            # ---- Sunbed-specific fields ----
            with ui.column().classes("w-full gap-2 mt-2") as sunbed_fields:
                type_input = ui.radio(list(SUNBED_PRICES.keys()), value="First row").props("inline")
                beds_input = ui.input("Sunbed number(s)", placeholder="E.g. 4, 12").classes("w-full")

            # ---- Big Bed-specific fields ----
            with ui.column().classes("w-full gap-2 mt-2") as bigbed_fields:
                unit_input = ui.input("Big Bed unit(s)", placeholder="E.g. 1, 3 -> Lux1, Lux3").classes("w-full")
                ui.label("Package").classes("text-sm text-gray-500")
                package_input = ui.radio(BIGBED_PACKAGES, value=BIGBED_PACKAGES[0]).props("inline")
                custom_price_switch = ui.switch("Exception: custom price", on_change=on_custom_price_change)
                custom_price_input = ui.number("Custom price (EUR)", min=0, step=5).classes("w-full")
                custom_price_input.set_visibility(False)
            bigbed_fields.set_visibility(False)

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
            today_summaries_ui()
            ui.label("Today's sales").classes("text-lg")
            today_sales_list_ui()


# ============================================================
# HISTORY TAB (admin only) -- combined totals for range/compare,
# split Sunbed/Big Bed totals for the single-day view.
# ============================================================

def refresh_day_view(container, fecha):
    container.clear()
    with container:
        if not fecha:
            return
        render_product_summary(fecha, "Sunbed", "Sunbeds")
        render_product_summary(fecha, "Big Bed", "Big Beds")

        ui.label("All sales that day").classes("text-lg mt-3")
        sales = db.obtener_ventas_dia(fecha)
        if not sales:
            ui.label("No sales for this day.").classes("text-gray-400")
        else:
            for sale in sales:
                with ui.card().classes("w-full"):
                    with ui.row().classes("w-full items-center justify-between"):
                        with ui.column().classes("gap-0"):
                            ui.label(f"[{sale['producto']}] {sale['cantidad']}x {sale['tipo']} - {sale['hamacas'] or '-'}").classes("font-medium")
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
        ui.label("Combined totals (Sunbeds + Big Beds)").classes("text-sm text-gray-500 mb-1")
        data = db.resumen_rango(fecha_inicio, fecha_fin)
        if not data:
            ui.label("No sales in this range.").classes("text-gray-400")
            return
        total_hamacas = sum(d["total_hamacas"] for d in data)
        total_importe = sum(d["total_importe"] for d in data)
        ui.label(f"Range total: {total_hamacas} units - {total_importe:.2f} EUR").classes("font-medium mb-3")

        max_total = max(d["total_importe"] for d in data) or 1
        for d in data:
            pct = round((d["total_importe"] / max_total) * 100)
            with ui.column().classes("w-full gap-1 mb-2"):
                with ui.row().classes("w-full justify-between"):
                    ui.label(d["fecha"])
                    ui.label(f"{d['total_hamacas']} units - {d['total_importe']:.2f} EUR").classes("text-sm text-gray-500")
                with ui.element("div").classes("w-full bg-gray-700 rounded"):
                    ui.element("div").classes("bg-blue-500 rounded").style(f"width:{pct}%; height:8px;")


def show_compare(container, fecha_a, fecha_b):
    container.clear()
    with container:
        if not fecha_a or not fecha_b:
            ui.label("Pick both days.").classes("text-gray-400")
            return
        ui.label("Combined totals (Sunbeds + Big Beds)").classes("text-sm text-gray-500 mb-1")
        with ui.row().classes("w-full gap-4 flex-col md:flex-row"):
            render_day_summary_combined(fecha_a)
            render_day_summary_combined(fecha_b)


def history_content():
    today = db.hoy()

    ui.label("View a day").classes("text-lg mb-1")
    with ui.row().classes("items-center gap-3"):
        day_view_input = ui.input("Date").props(f'type=date max="{today}"').classes("w-40")
    day_view_container = ui.column().classes("w-full gap-2 mt-2")
    day_view_input.on(
        "update:model-value",
        lambda e: refresh_day_view(day_view_container, day_view_input.value),
    )

    ui.separator().classes("my-4")

    with ui.expansion("Compare a date range", icon="date_range").classes("w-full"):
        with ui.row().classes("items-center gap-3"):
            range_from = ui.input("From").props("type=date").classes("w-40")
            range_to = ui.input("To").props(f'type=date max="{today}"').classes("w-40")
            ui.button("Show", on_click=lambda: show_range(range_container, range_from.value, range_to.value))
        range_container = ui.column().classes("w-full mt-3")

    with ui.expansion("Compare two days", icon="compare_arrows").classes("w-full mt-2"):
        with ui.row().classes("items-center gap-3"):
            compare_a = ui.input("Day A").props(f'type=date max="{today}"').classes("w-40")
            compare_b = ui.input("Day B").props(f'type=date max="{today}"').classes("w-40")
            ui.button("Compare", on_click=lambda: show_compare(compare_container, compare_a.value, compare_b.value))
        compare_container = ui.column().classes("w-full mt-3")


# ============================================================
# LOGIN / WELCOME SCREEN
# ============================================================

def try_login(username_input, password_input, error_label):
    username = username_input.value.strip().lower()
    password = password_input.value

    user = USERS.get(username)
    if user and user["password_hash"] == _hash(password):
        app.storage.user["authenticated"] = True
        app.storage.user["role"] = user["role"]
        app.storage.user["username"] = username
        ui.navigate.to("/app")
    else:
        error_label.text = "Incorrect username or password"
        error_label.visible = True


@ui.page("/")
def login_page():
    with ui.column().classes("w-full items-center justify-center gap-4").style("min-height: 90vh;"):
        ui.icon("beach_access", size="64px").classes("text-blue-400")
        ui.label("Sunbed & Big Bed Sales").classes("text-3xl font-medium")
        ui.label("Beach club sales tracker").classes("text-gray-500 mb-4")

        with ui.card().classes("w-full max-w-sm"):
            username_input = ui.input("Username").classes("w-full")
            password_input = ui.input("Password", password=True, password_toggle_button=True).classes("w-full")
            error_label = ui.label("").classes("text-red-400 text-sm")
            error_label.visible = False

            login_btn = ui.button(
                "Enter",
                on_click=lambda: try_login(username_input, password_input, error_label),
            ).classes("w-full mt-2")
            password_input.on("keydown.enter", lambda: login_btn.run_method("click"))


@ui.page("/app")
def main_app_page():
    if not app.storage.user.get("authenticated"):
        ui.navigate.to("/")
        return

    role = app.storage.user.get("role")
    username = app.storage.user.get("username", "")

    dark = ui.dark_mode(True)

    with ui.row().classes("w-full items-center justify-between"):
        with ui.row().classes("items-center gap-2"):
            ui.icon("beach_access").classes("text-blue-400")
            ui.label("Sunbed & Big Bed Sales").classes("text-2xl")
        with ui.row().classes("items-center gap-2"):
            ui.label(f"{username} ({role})").classes("text-sm text-gray-500")
            ui.button(icon="dark_mode", on_click=lambda: dark.toggle()).props("flat round")
            ui.button(icon="logout", on_click=lambda: (app.storage.user.clear(), ui.navigate.to("/"))).props("flat round")

    if role == "admin":
        with ui.tabs().classes("w-full") as tabs:
            register_tab = ui.tab("Register", icon="add_circle")
            history_tab = ui.tab("History", icon="history")

        with ui.tab_panels(tabs, value=register_tab).classes("w-full"):
            with ui.tab_panel(register_tab):
                register_content()
            with ui.tab_panel(history_tab):
                history_content()
    else:
        register_content()


ui.run(
    host="0.0.0.0",
    port=8081,
    title="Sunbed Sales",
    reload=False,
    storage_secret="CHANGE-THIS-TO-A-LONG-RANDOM-SECRET",
)