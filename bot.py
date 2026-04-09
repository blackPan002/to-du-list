import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.getenv("BOT_TOKEN", "8322782866:AAGIVaPDeU_dU601ryIm2qJltWXBBVcIV5M")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

user_tasks = {}
last_main_message = {}

class AddTask(StatesGroup):
    waiting_for_text = State()

class DeleteTask(StatesGroup):
    waiting_for_id = State()

class DoneTask(StatesGroup):
    waiting_for_id = State()


def main_menu_keyboard():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📋 Просмотр списка", callback_data="prosmotr")],
        [types.InlineKeyboardButton(text="➕ Добавить задачу", callback_data="add")],
        [types.InlineKeyboardButton(text="🗑 Удалить задачу", callback_data="delete")],
        [types.InlineKeyboardButton(text="✅ Отметить выполненной", callback_data="done")],
    ])

def back_keyboard():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
    ])

def format_tasks(user_id: int) -> str:
    tasks = user_tasks.get(user_id, [])
    if not tasks:
        return "📭 Список задач пуст"
    lines = []
    for task in tasks:
        icon = "✅" if task["done"] else "🔲"
        lines.append(f"{icon} {task['id']}. {task['text']}")
    return "📋 Ваши задачи:\n\n" + "\n".join(lines)

def next_id(user_id: int) -> int:
    tasks = user_tasks.get(user_id, [])
    return max((t["id"] for t in tasks), default=0) + 1


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    await state.clear()
    await message.delete()

    if user_id in last_main_message:
        try:
            await bot.delete_message(chat_id=user_id, message_id=last_main_message[user_id])
        except Exception:
            pass

    sent = await message.answer(
        "📝 <b>To-Do List</b>\nВыберите действие:",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )
    last_main_message[user_id] = sent.message_id


@dp.callback_query()
async def handle_callbacks(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = callback.data

    if data == "back_to_menu":
        await state.clear()
        await callback.message.edit_text(
            "📝 <b>To-Do List</b>\nВыберите действие:",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )

    elif data == "prosmotr":
        await callback.message.edit_text(
            format_tasks(user_id),
            reply_markup=back_keyboard()
        )

    elif data == "add":
        await callback.message.edit_text(
            "✏️ Напишите текст задачи:",
            reply_markup=back_keyboard()
        )
        await state.set_state(AddTask.waiting_for_text)

    elif data == "delete":
        await callback.message.edit_text(
            f"{format_tasks(user_id)}\n\n🗑 Введите номер задачи для удаления:",
            reply_markup=back_keyboard()
        )
        await state.set_state(DeleteTask.waiting_for_id)

    elif data == "done":
        await callback.message.edit_text(
            f"{format_tasks(user_id)}\n\n✅ Введите номер задачи для отметки:",
            reply_markup=back_keyboard()
        )
        await state.set_state(DoneTask.waiting_for_id)

    await callback.answer()


@dp.message(AddTask.waiting_for_text)
async def process_add_task(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()
    await message.delete()

    if user_id not in user_tasks:
        user_tasks[user_id] = []

    task_id = next_id(user_id)
    user_tasks[user_id].append({"id": task_id, "text": text, "done": False})
    await state.clear()

    try:
        await bot.edit_message_text(
            chat_id=user_id,
            message_id=last_main_message[user_id],
            text=f"✅ Задача добавлена!\n\n{format_tasks(user_id)}",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
    except Exception:
        pass


@dp.message(DeleteTask.waiting_for_id)
async def process_delete_task(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    await message.delete()

    try:
        task_id = int(message.text.strip())
    except ValueError:
        await bot.edit_message_text(
            chat_id=user_id,
            message_id=last_main_message[user_id],
            text="❌ Введите число!\n\n" + format_tasks(user_id),
            reply_markup=back_keyboard()
        )
        return

    tasks = user_tasks.get(user_id, [])
    task = next((t for t in tasks if t["id"] == task_id), None)

    if not task:
        await bot.edit_message_text(
            chat_id=user_id,
            message_id=last_main_message[user_id],
            text="❌ Задача не найдена!\n\n" + format_tasks(user_id),
            reply_markup=back_keyboard()
        )
        return

    user_tasks[user_id] = [t for t in tasks if t["id"] != task_id]
    await state.clear()

    await bot.edit_message_text(
        chat_id=user_id,
        message_id=last_main_message[user_id],
        text=f"🗑 Задача удалена!\n\n{format_tasks(user_id)}",
        reply_markup=main_menu_keyboard()
    )


@dp.message(DoneTask.waiting_for_id)
async def process_done_task(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    await message.delete()

    try:
        task_id = int(message.text.strip())
    except ValueError:
        await bot.edit_message_text(
            chat_id=user_id,
            message_id=last_main_message[user_id],
            text="❌ Введите число!\n\n" + format_tasks(user_id),
            reply_markup=back_keyboard()
        )
        return

    tasks = user_tasks.get(user_id, [])
    task = next((t for t in tasks if t["id"] == task_id), None)

    if not task:
        await bot.edit_message_text(
            chat_id=user_id,
            message_id=last_main_message[user_id],
            text="❌ Задача не найдена!\n\n" + format_tasks(user_id),
            reply_markup=back_keyboard()
        )
        return

    task["done"] = not task["done"]
    status = "выполнена ✅" if task["done"] else "не выполнена 🔲"
    await state.clear()

    await bot.edit_message_text(
        chat_id=user_id,
        message_id=last_main_message[user_id],
        text=f"Задача отмечена как {status}\n\n{format_tasks(user_id)}",
        reply_markup=main_menu_keyboard()
    )


async def main():
    print("🚀 To-Do бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
