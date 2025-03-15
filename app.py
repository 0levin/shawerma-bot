import os
import json
import random
import logging
from collections import Counter
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(
    filename="bot.log",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    encoding="utf-8"
)
logger = logging.getLogger(__name__)

# Константы
SHAWERMA_FILE = "shawerma.json"
ORDERS_FILE = "orders.json"
TOKEN = ""

def load_data(file):
    """Загрузка данных из JSON-файла."""
    try:
        if not os.path.exists(file) or os.path.getsize(file) == 0:
            return []
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Ошибка загрузки файла {file}: {e}")
        return []

def save_data(data, file):
    """Сохранение данных в JSON-файл."""
    try:
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info(f"Файл {file} сохранён")
    except IOError as e:
        logger.error(f"Ошибка сохранения файла {file}: {e}")

shawerma_json = load_data(SHAWERMA_FILE)

def create_menu_buttons(shawerma_data, extra_buttons=None):
    """Создание кнопок меню из данных шаурмы."""
    buttons = [
        [InlineKeyboardButton(f"{item['name']} - {item['price']} ₽", callback_data=f"item_{item['name']}")]
        for item in shawerma_data
    ]
    if extra_buttons:
        buttons.extend(extra_buttons)
    return InlineKeyboardMarkup(buttons)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    user = update.effective_user
    greetings_name = user.first_name or user.username
    context.user_data['user'] = user.first_name or user.username
    context.user_data['chosen_items'] = []

    greetings = ["Хэлоу", "Намасте", "Асалам алейкум", "Коничива", "Нихао", "Привет", "Бонжорно", "Салют"]
    random_greeting = random.choice(greetings)

    buttons = [
        [InlineKeyboardButton("Выбрать", callback_data="menu")],
        [InlineKeyboardButton("Отмена", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(
        f"{random_greeting}, <b>{greetings_name}</b>. Выберите позиции из меню.",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик отмены заказа."""
    await update.callback_query.answer()
    context.user_data['chosen_items'].clear()

    messages = [
        "Возвращайся, если передумаешь",
        "Китайская еда - тоже вариант",
        "Ланчбокс - тоже вариант",
        "Не есть - не вариант"
    ]
    random_message = random.choice(messages)

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Выбрать", callback_data="menu")]])
    await update.callback_query.message.reply_text(
        f"{random_message}, <b>{context.user_data['user']}</b>.",
        parse_mode="HTML",
        reply_markup=reply_markup
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отображение меню."""
    await update.callback_query.answer()
    reply_markup = create_menu_buttons(shawerma_json, [[InlineKeyboardButton("Отмена", callback_data="cancel")]])
    await update.callback_query.message.reply_text(
        "Выберите позицию из меню:",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление выбранного элемента в заказ."""
    await update.callback_query.answer()
    chosen_item = update.callback_query.data.split("_")[1]
    context.user_data['chosen_items'].append(chosen_item)

    extra_buttons = [
        [InlineKeyboardButton("Отмена", callback_data="cancel")],
        [InlineKeyboardButton("Сделать заказ", callback_data="order")]
    ]
    reply_markup = create_menu_buttons(shawerma_json, extra_buttons)
    transformed_chosen_items = ", ".join(context.user_data['chosen_items'])

    await update.callback_query.message.reply_text(
        f"Ваш заказ:\n<b>{transformed_chosen_items}</b>\n\nЧто-то еще?",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Фиксация заказа."""
    await update.callback_query.answer()
    user = context.user_data.get('user')
    chosen_items = context.user_data.get('chosen_items', [])

    if not chosen_items:
        await update.callback_query.message.reply_text("Ваш заказ пуст!")
        return

    orders = load_data(ORDERS_FILE)
    orders.append({"user": user, "order": chosen_items.copy()})
    save_data(orders, ORDERS_FILE)

    transformed_chosen_items = ", ".join(chosen_items)
    context.user_data['chosen_items'].clear()

    buttons = [
        [InlineKeyboardButton("Изменить заказ", callback_data="change")],
        [InlineKeyboardButton("Посмотреть все заказы", callback_data="allorders")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    await update.callback_query.message.reply_text(
        f"Ваш заказ принят. 🙂 Состав заказа: <b>{transformed_chosen_items}</b>",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def all_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отображение всех заказов."""
    await update.callback_query.answer()
    orders = load_data(ORDERS_FILE)
    current_user = context.user_data.get('user')
    
    if not orders:
        orders_text = "Заказов пока нет."
    else:
        orders_text = "\n".join(f"<b>{o['user']}</b>: {', '.join(o['order'])}" for o in orders)

    total_items = Counter(item for o in orders for item in o['order'])
    total_items_text = "\n".join(f"<b>{item}</b>: {count}" for item, count in total_items.items())

    buttons = [[InlineKeyboardButton("Изменить заказ" if any(o['user'] == current_user for o in orders) else "Меню",
                callback_data="change" if any(o['user'] == current_user for o in orders) else "menu")]]
    reply_markup = InlineKeyboardMarkup(buttons)

    await update.callback_query.message.reply_text(
        f"<b>Заказы:</b>\n\n{orders_text}\n_\n\n<b>Итог:</b>\n\n{total_items_text}",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Изменение заказа."""
    await update.callback_query.answer()
    orders = load_data(ORDERS_FILE)
    user = context.user_data.get('user')
    user_order = next((o for o in orders if o['user'] == user), None)

    if not user_order or not user_order['order']:
        await update.callback_query.message.reply_text("У вас нет активных заказов!")
        return

    buttons = [[InlineKeyboardButton(item, callback_data=f"approvechange_{item}")] for item in user_order['order']]
    buttons.append([InlineKeyboardButton("Отмена", callback_data="allorders")])
    reply_markup = InlineKeyboardMarkup(buttons)

    await update.callback_query.message.reply_text(
        "Выберите позицию заказа для удаления:",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def approve_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления позиции из заказа."""
    await update.callback_query.answer()
    chosen_item = update.callback_query.data.split("_")[1]
    user = context.user_data.get('user')
    orders = load_data(ORDERS_FILE)

    user_order = next((o for o in orders if o['user'] == user), None)
    if user_order and chosen_item in user_order['order']:
        user_order['order'].remove(chosen_item)
        if not user_order['order']:
            orders.remove(user_order)
        save_data(orders, ORDERS_FILE)

    buttons = [[InlineKeyboardButton("Посмотреть все заказы", callback_data="allorders")]]
    if user_order and user_order['order']:
        buttons.append([InlineKeyboardButton("Изменить заказ", callback_data="change")])
    reply_markup = InlineKeyboardMarkup(buttons)

    await update.callback_query.message.reply_text(
        f"Позиция <b>{chosen_item}</b> удалена.",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

def main():
    """Запуск бота."""
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu, pattern="^menu$"))
    app.add_handler(CallbackQueryHandler(cancel, pattern="^cancel$"))
    app.add_handler(CallbackQueryHandler(approve, pattern="^item_"))
    app.add_handler(CallbackQueryHandler(order, pattern="^order$"))
    app.add_handler(CallbackQueryHandler(all_orders, pattern="^allorders$"))
    app.add_handler(CallbackQueryHandler(change, pattern="^change$"))
    app.add_handler(CallbackQueryHandler(approve_change, pattern="^approvechange_"))
    
    logger.info("Бот активирован и работает.")
    app.run_polling()

if __name__ == "__main__":
    main()
