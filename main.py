import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import mysql.connector
from PIL import Image, ImageTk

IMAGES = Path(__file__).parent / "images"
WHITE, CYAN, BLUE = "#FFFFFF", "#00FFFF", "#0000FF"

ROLE_TABLES = {
    "Гость": ["Товары"],
    "Авторизированный клиент": ["Товары"],
    "Менеджер": ["Товары", "Заказы"],
    "Администратор": ["Товары", "Заказы", "Пользователи", "Пункты выдачи"],
}
TABLES = {"Товары": "product", "Заказы": "customer_order",
          "Пользователи": "user_account", "Пункты выдачи": "pickup_point"}

conn = mysql.connector.connect(host="localhost", database="zalupa_db",
                               user="root", password="", charset="utf8mb4")
cur = conn.cursor(dictionary=True)
images = {}

def select(query, params=()):
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.commit()
    return rows

def load_image(name, size):
    if (name, size) not in images:
        try:
            picture = Image.open(IMAGES / name)
            picture.thumbnail(size)
            images[(name, size)] = ImageTk.PhotoImage(picture)
        except OSError:
            return None
    return images[(name, size)]

def cell(value):
    if value is None:
        return "—"
    return value.strftime("%d.%m.%Y") if hasattr(value, "strftime") else value

def new_window(title, size):
    images.clear()
    window = tk.Tk()
    window.title(title)
    window.geometry(size)
    window.configure(bg=WHITE)
    window.option_add("*Font", ("Calibri", 12))
    icon = load_image("icon.jpg", (64, 64))
    if icon:
        window.iconphoto(True, icon)
    return window

def run_login_window():
    user = None
    window = new_window("МебельОрг — Вход", "380x470")
    logo = load_image("icon.png", (200, 140))
    if logo:
        tk.Label(window, image=logo, bg=WHITE).pack(pady=(15, 5))
    tk.Label(window, text="Вход в систему", bg=WHITE,
             font=("Calibri", 18, "bold")).pack(pady=10)
    tk.Label(window, text="Логин", bg=WHITE).pack()
    login_entry = tk.Entry(window, width=30, bg=CYAN)
    login_entry.pack(pady=(0, 8))
    tk.Label(window, text="Пароль", bg=WHITE).pack()
    password_entry = tk.Entry(window, width=30, show="*", bg=CYAN)
    password_entry.pack(pady=(0, 12))

    def finish(found_user):
        nonlocal user
        user = found_user
        window.destroy()

    def on_login():
        login, password = login_entry.get().strip(), password_entry.get()
        if not login or not password:
            messagebox.showwarning("Вход", "Введите логин и пароль")
            return
        rows = select("SELECT full_name, role_name FROM user_account"
                      " WHERE login = %s AND password = %s", (login, password))
        if rows:
            finish(rows[0])
        else:
            messagebox.showerror("Вход", "Неверный логин или пароль")
            password_entry.delete(0, tk.END)

    tk.Button(window, text="Войти", command=on_login, bg=BLUE, fg="white",
              relief="flat", pady=5).pack(fill="x", padx=60)
    tk.Button(window, text="Войти как гость", bg=CYAN, relief="flat", pady=5,
              command=lambda: finish({"full_name": "Гость", "role_name": "Гость"})
              ).pack(fill="x", padx=60, pady=8)
    window.bind("<Return>", lambda event: on_login())
    window.mainloop()
    return user

def run_main_window(user):
    tables = ROLE_TABLES.get(user["role_name"], ["Товары"])
    logout = False
    window = new_window(f"МебельОрг — Таблицы ({user['role_name']})", "1100x700")
    header = tk.Frame(window, bg=CYAN)
    header.pack(fill="x")
    body = tk.Frame(window, bg=WHITE)
    body.pack(fill="both", expand=True)

    def on_logout():
        nonlocal logout
        logout = True
        window.destroy()

    def show_table(table_name):
        for widget in body.winfo_children():
            widget.destroy()
        rows = select(f"SELECT * FROM {TABLES[table_name]}")
        titles = [c for c in cur.column_names if c != "password"]
        tree = ttk.Treeview(body, show="headings", columns=titles)
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        for title in titles:
            tree.heading(title, text=title)
            tree.column(title, width=120, anchor="w")
        for row in rows:
            tree.insert("", "end", values=[cell(row[t]) for t in titles])

    logo = load_image("icon.png", (70, 50))
    if logo:
        tk.Label(header, image=logo, bg=CYAN).pack(side="left", padx=8, pady=4)
    for name in tables:
        tk.Button(header, text=name, bg=WHITE, relief="flat", padx=12,
                  command=lambda n=name: show_table(n)).pack(side="left", padx=4, pady=8)
    tk.Button(header, text="Выйти", command=on_logout, bg=BLUE, fg="white",
              relief="flat", padx=14, pady=5).pack(side="right", padx=10)
    tk.Label(header, text=user["full_name"], bg=CYAN,
             font=("Calibri", 13, "bold")).pack(side="right", padx=10)
    show_table(tables[0])
    window.mainloop()
    return logout

while True:
    current_user = run_login_window()
    if current_user is None or not run_main_window(current_user):
        break