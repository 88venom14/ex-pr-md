import tkinter as tk
from pathlib import Path
from tkinter import font as tk_font, messagebox, ttk

import mysql.connector
from PIL import Image, ImageTk

IMAGES_DIR = Path(__file__).resolve().parent / "images"
ICON_FILE, LOGO_FILE, PLACEHOLDER_FILE = "icon.jpg", "icon.png", "picture.png"

FONT = "Calibri"
COLOR_MAIN, COLOR_EXTRA, COLOR_ACCENT = "#FFFFFF", "#00FFFF", "#0000FF"
COLOR_BIG_DISCOUNT, COLOR_NO_STOCK = "#008080", "#D3D3D3"

ROLE_TABLES = {
    "Гость": ["Товары"],
    "Авторизированный клиент": ["Товары"],
    "Менеджер": ["Товары", "Заказы"],
    "Администратор": ["Товары", "Заказы", "Пользователи", "Пункты выдачи"],
}

TABLES = {
    "Заказы": (
        "SELECT o.order_id, o.order_date, o.delivery_date, p.address,"
        " o.client, o.receive_code, o.status, o.items"
        " FROM customer_order o"
        " LEFT JOIN pickup_point p ON p.pickup_point_id = o.pickup_point_id"
        " ORDER BY o.order_id",
        ("№", "Дата заказа", "Дата доставки", "Пункт выдачи", "Клиент",
         "Код", "Статус", "Состав заказа"),
    ),
    "Пользователи": (
        "SELECT user_id, full_name, role_name, login FROM user_account"
        " ORDER BY user_id",
        ("№", "ФИО", "Роль", "Логин"),
    ),
    "Пункты выдачи": (
        "SELECT pickup_point_id, address FROM pickup_point ORDER BY pickup_point_id",
        ("№", "Адрес"),
    ),
}

SQL_LOGIN = ("SELECT full_name, role_name FROM user_account"
             " WHERE login = %s AND password = %s")
SQL_PRODUCTS = (
    "SELECT article, product_name, category_name, description,"
    " manufacturer_name, supplier_name, price, unit_name,"
    " stock_quantity, discount_percent, photo_file FROM product ORDER BY article"
)

try:
    conn = mysql.connector.connect(
        host="localhost", database="zalupa_db", user="root", password="",
        charset="utf8mb4", use_unicode=True,
    )
except mysql.connector.Error as error:
    raise SystemExit(f"Нет подключения к базе zalupa_db: {error}\n"
                     "Сначала выполните: python import_data.py")
cur = conn.cursor(dictionary=True)
cur.execute("SHOW TABLES")
if not cur.fetchall():
    raise SystemExit("В базе zalupa_db нет таблиц. Выполните: python import_data.py")

images = {}

def select(query, params=()):
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.commit()
    return rows

def find_file(file_name):
    if not file_name or not IMAGES_DIR.is_dir():
        return None
    return next((p for p in IMAGES_DIR.iterdir()
                 if p.name.lower() == file_name.lower()), None)

def load_image(file_name, size):
    key = (file_name, size)
    if key not in images:
        path = find_file(file_name)
        if path is None:
            return None
        try:
            with Image.open(path) as picture:
                picture.thumbnail(size)
                images[key] = ImageTk.PhotoImage(picture)
        except OSError:
            return None
    return images[key]

def load_product_photo(file_name):
    return (load_image(file_name, (150, 110))
            or load_image(PLACEHOLDER_FILE, (150, 110)))

def get_row_color(discount, stock):
    if stock == 0:
        return COLOR_NO_STOCK
    return COLOR_BIG_DISCOUNT if discount > 15 else COLOR_MAIN

def money(value):
    return f"{value:,.2f}".replace(",", " ") + " руб."

def format_cell(value):
    if value is None:
        return "—"
    return value.strftime("%d.%m.%Y") if hasattr(value, "strftime") else value

def make_button(parent, text, command, accent=True):
    bg, fg = (COLOR_ACCENT, "white") if accent else (COLOR_EXTRA, "black")
    return tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                     activebackground=bg, activeforeground=fg,
                     relief="flat", padx=14, pady=5, cursor="hand2")

def new_window(title, size):
    images.clear()
    window = tk.Tk()
    window.title(title)
    window.geometry(size)
    window.configure(bg=COLOR_MAIN)
    window.option_add("*Font", (FONT, 12))
    icon = load_image(ICON_FILE, (64, 64))
    if icon:
        window.iconphoto(True, icon)
    return window

def run_login_window():
    result = {"user": None}
    window = new_window("МебельОрг — Вход", "380x470")

    logo = load_image(LOGO_FILE, (200, 140))
    if logo:
        tk.Label(window, image=logo, bg=COLOR_MAIN).pack(pady=(15, 5))
    tk.Label(window, text="Вход в систему", bg=COLOR_MAIN,
             font=(FONT, 18, "bold")).pack(pady=10)
    tk.Label(window, text="Логин", bg=COLOR_MAIN).pack()
    login_entry = tk.Entry(window, width=30, bg=COLOR_EXTRA)
    login_entry.pack(pady=(0, 8))
    tk.Label(window, text="Пароль", bg=COLOR_MAIN).pack()
    password_entry = tk.Entry(window, width=30, show="*", bg=COLOR_EXTRA)
    password_entry.pack(pady=(0, 12))

    def finish(user):
        result["user"] = user
        window.destroy()

    def on_login():
        login, password = login_entry.get().strip(), password_entry.get()
        if not login or not password:
            messagebox.showwarning("Вход", "Введите логин и пароль")
            return
        rows = select(SQL_LOGIN, (login, password))
        if rows:
            finish(rows[0])
        else:
            messagebox.showerror("Вход", "Неверный логин или пароль")
            password_entry.delete(0, tk.END)

    make_button(window, "Войти", on_login).pack(fill="x", padx=60)
    make_button(window, "Войти как гость",
                lambda: finish({"full_name": "Гость", "role_name": "Гость"}),
                accent=False).pack(fill="x", padx=60, pady=8)
    window.bind("<Return>", lambda event: on_login())
    window.mainloop()
    return result["user"]

def build_product_card(parent, product):
    discount = float(product["discount_percent"] or 0)
    price = float(product["price"])
    color = get_row_color(discount, product["stock_quantity"])

    card = tk.Frame(parent, bg=color, highlightbackground="black", highlightthickness=1)
    card.pack(fill="x", pady=4)
    card.columnconfigure(1, weight=1)
    tk.Label(card, image=load_product_photo(product["photo_file"]),
             bg=color).grid(row=0, column=0, padx=8, pady=8)

    info = tk.Frame(card, bg=color)
    info.grid(row=0, column=1, sticky="w", padx=8)
    tk.Label(info, text=f"{product['category_name']} | {product['product_name']}",
             bg=color, font=(FONT, 12, "bold"), wraplength=520,
             justify="left").pack(anchor="w")
    details = (
        f"Описание: {product['description']}\n"
        f"Производитель: {product['manufacturer_name']}\n"
        f"Поставщик: {product['supplier_name']}\n"
        f"Единица измерения: {product['unit_name']}\n"
        f"Количество на складе: {product['stock_quantity']}"
    )
    tk.Label(info, text=details, bg=color, wraplength=520,
             justify="left").pack(anchor="w")

    price_row = tk.Frame(info, bg=color)
    price_row.pack(anchor="w", pady=(4, 0))
    tk.Label(price_row, text="Цена: ", bg=color).pack(side="left")
    if discount > 0:
        old_font = tk_font.Font(family=FONT, size=12, overstrike=True)
        tk.Label(price_row, text=money(price), bg=color, fg="red",
                 font=old_font).pack(side="left")
        price = round(price * (1 - discount / 100), 2)
        tk.Label(price_row, text="  " + money(price), bg=color).pack(side="left")
    else:
        tk.Label(price_row, text=money(price), bg=color).pack(side="left")

    tk.Label(card, text=f"Действующая скидка\n{discount:g}%", bg=color,
             font=(FONT, 12, "bold"), width=24).grid(row=0, column=2, padx=10)

def show_products(body):
    container = tk.Frame(body, bg=COLOR_MAIN)
    container.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    canvas = tk.Canvas(container, bg=COLOR_MAIN, highlightthickness=0)
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    list_frame = tk.Frame(canvas, bg=COLOR_MAIN)
    window_id = canvas.create_window((0, 0), window=list_frame, anchor="nw")
    list_frame.bind("<Configure>",
                    lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window_id, width=e.width))

    def on_wheel(event):
        up = getattr(event, "num", 0) == 4 or getattr(event, "delta", 0) > 0
        canvas.yview_scroll(-1 if up else 1, "units")

    for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        canvas.bind_all(sequence, on_wheel)

    for product in select(SQL_PRODUCTS):
        build_product_card(list_frame, product)

def show_simple_table(body, table_name):
    query, titles = TABLES[table_name]
    frame = tk.Frame(body, bg=COLOR_MAIN)
    frame.pack(fill="both", expand=True, padx=10, pady=10)
    tree = ttk.Treeview(frame, show="headings", columns=titles)
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    tree.pack(side="left", fill="both", expand=True)
    for title in titles:
        tree.heading(title, text=title)
        tree.column(title, width=120, anchor="w")
    for row in select(query):
        tree.insert("", "end", values=[format_cell(c) for c in row.values()])

def run_main_window(user):
    role = user["role_name"]
    tables = ROLE_TABLES.get(role, ["Товары"])
    result = {"logout": False}
    window = new_window(f"МебельОрг — Таблицы ({role})", "1100x700")

    header = tk.Frame(window, bg=COLOR_EXTRA)
    header.pack(fill="x")
    body = tk.Frame(window, bg=COLOR_MAIN)
    body.pack(fill="both", expand=True)

    def on_logout():
        result["logout"] = True
        window.destroy()

    def show_table(table_name):
        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            window.unbind_all(sequence)
        for widget in body.winfo_children():
            widget.destroy()
        if table_name == "Товары":
            show_products(body)
        else:
            show_simple_table(body, table_name)

    logo = load_image(LOGO_FILE, (70, 50))
    if logo:
        tk.Label(header, image=logo, bg=COLOR_EXTRA).pack(side="left", padx=8, pady=4)
    for name in tables:
        tk.Button(header, text=name, bg=COLOR_MAIN, relief="flat", padx=12,
                  command=lambda n=name: show_table(n)).pack(side="left", padx=4, pady=8)
    make_button(header, "Выйти", on_logout).pack(side="right", padx=10)
    tk.Label(header, text=user["full_name"], bg=COLOR_EXTRA,
             font=(FONT, 13, "bold")).pack(side="right", padx=10)

    show_table(tables[0])
    window.mainloop()
    return result["logout"]

def main():
    while True:
        user = run_login_window()
        if user is None or not run_main_window(user):
            break

if __name__ == "__main__":
    main()