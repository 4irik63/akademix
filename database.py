from typing import Optional
import aiosqlite
from datetime import datetime

from config import DB_PATH


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    username TEXT,
    full_name TEXT,
    work_type TEXT NOT NULL,
    subject TEXT NOT NULL,
    deadline TEXT NOT NULL,
    details TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    assigned_admin_id INTEGER,
    created_at TEXT NOT NULL
);
"""


async def init_db() -> None:
    """Создаёт таблицу заказов, если её ещё нет. Вызывается при старте бота."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_TABLE_SQL)
        await db.commit()


async def get_order_count() -> int:
    """Возвращает общее количество заказов — используется для равномерного
    распределения новых заказов между админами по кругу (round-robin)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM orders") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def create_order(
    user_id: int,
    username: Optional[str],
    full_name: str,
    work_type: str,
    subject: str,
    deadline: str,
    details: str,
    assigned_admin_id: Optional[int] = None,
) -> int:
    """Сохраняет новый заказ в базу и возвращает его номер (id)."""
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO orders
                (user_id, username, full_name, work_type, subject, deadline, details, status, assigned_admin_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'new', ?, ?)
            """,
            (user_id, username, full_name, work_type, subject, deadline, details, assigned_admin_id, created_at),
        )
        await db.commit()
        return cursor.lastrowid


async def get_order(order_id: int) -> Optional[aiosqlite.Row]:
    """Возвращает один заказ по его номеру."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cursor:
            return await cursor.fetchone()


async def get_user_orders(user_id: int) -> list:
    """Возвращает все заказы конкретного пользователя (для истории заказов)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (user_id,)
        ) as cursor:
            return await cursor.fetchall()


async def get_admin_orders(admin_id: int) -> list:
    """Возвращает заказы, назначенные конкретному администратору."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM orders WHERE assigned_admin_id = ? ORDER BY id DESC", (admin_id,)
        ) as cursor:
            return await cursor.fetchall()


async def get_orders_by_status(status: Optional[str] = None) -> list:
    """Возвращает заказы с указанным статусом. Если status=None — все заказы.
    Используется в админ-панели, доступна обоим администраторам сразу."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            query = "SELECT * FROM orders WHERE status = ? ORDER BY id DESC"
            params = (status,)
        else:
            query = "SELECT * FROM orders ORDER BY id DESC"
            params = ()
        async with db.execute(query, params) as cursor:
            return await cursor.fetchall()


async def get_active_orders() -> list:
    """Возвращает все заказы, кроме отменённых — используется в разделе
    «Все заказы» админ-панели, чтобы архив (отменённые) не мешался в списке."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM orders WHERE status != 'cancelled' ORDER BY id DESC"
        ) as cursor:
            return await cursor.fetchall()


async def update_order_status(order_id: int, status: str) -> None:
    """Меняет статус заказа (new / in_progress / done / cancelled и т.п.)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
        await db.commit()
