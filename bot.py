from datetime import datetime
from threading import Thread

import telebot
import schedule
import time

from peewee import DoesNotExist
from models import User, Goal

bot = telebot.TeleBot('7112069676:AAEWaxVIyp7tbUtDqp98_r0ZS4_NddF6W9o')

@bot.message_handler(commands = ['start'])
def start_handler(message):
    if not User.select().where(User.chat_id == message.chat.id):    # Перевірка для того, щоб не записувати в БД id користувача, якщо він вже є в БД
        User.create(
            chat_id=message.chat.id                                 # При натисканні на Start, id користувача одразу записується в БД
        )

    bot.send_message(
        message.chat.id,
        f"Привіт {message.chat.first_name} {message.chat.last_name or ''}! Я допоможу тобі бути більш продуктивним та відстежувати власні цілі та досягнення, напиши мені свою задачу, щоб я міг зберегти її для тебе або можеш ознайомитись з моїм функціоналом за допомогою команди /help")

# Список команд

@bot.message_handler(commands=['help'])
def help_handler(message):
    help_text = (
        "/start - Почати роботу з ботом\n"
        "/today, /t - Показати цілі на сьогодні\n"
        "/goal_done, /d - Позначити ціль як виконану\n"
        "/delete_goal, /del - Видалити ціль\n"
        "/help - Показати це повідомлення"
    )
    bot.send_message(message.chat.id, help_text)

# Створення списку цілей
def create_all_goal_message(chat_id):
    user = User.get(User.chat_id == chat_id)
    goals = Goal.select().where(Goal.user == user,
                                Goal.date == datetime.today())
    message_text = []

    for goal in goals:
        if goal.is_done:
            message_text.append(f"<b><s>{goal.user_goal_number}. {goal.task}</s></b>\n")
        else:
            message_text.append(f"<b>{goal.user_goal_number}. {goal.task}</b>\n")
    return "".join(message_text)

# Список цілей на сьогодні

@bot.message_handler(commands=['today', 't'])
def get_goal_list(message):
    goal_list = bot.send_message(
        message.chat.id,
        create_all_goal_message(message.chat.id),
        parse_mode='HTML'
    )


# Ціль виконано

@bot.message_handler(commands=['goal_done', 'd'])
def make_done(message):
    try:
        user = User.get(User.chat_id == message.chat.id)
        goals = Goal.select().where(Goal.user == user, Goal.is_done == False)

        if not goals.exists():
            bot.send_message(message.chat.id, "У тебе немає збережених цілей.")
            return

        goal_list = "\n".join([f"{goal.user_goal_number}: {goal.task}" for goal in goals])
        bot.send_message(message.chat.id,
                         f"Твої незавершені цілі:\n{goal_list}\n\nВведи номер цілі, яку хочеш позначити як виконану:")

        bot.register_next_step_handler(message, process_make_done_step)

    except DoesNotExist:
        bot.send_message(message.chat.id, "Спочатку створи ціль.")

def process_make_done_step(message):
    try:
        goal_id = int(message.text)
        user = User.get(User.chat_id == message.chat.id)
        goal = Goal.get(Goal.user_goal_number == goal_id, Goal.user == user, Goal.is_done == False)

        goal.is_done = True
        goal.save()
        bot.send_message(message.chat.id, f"{goal.user_goal_number}. {goal.task} виконано!")

    except ValueError:
        bot.send_message(message.chat.id, "Будь ласка, введи дійсний номер.")
    except DoesNotExist:
        bot.send_message(message.chat.id, "Ціль з таким номером не знайдено або вона вже виконана.")


# Ціль видалено

@bot.message_handler(commands=['delete_goal', 'del'])
def delete_goal_handler(message):
    try:
        user = User.get(User.chat_id == message.chat.id)
        goals = Goal.select().where(Goal.user == user)

        if not goals.exists():
            bot.send_message(message.chat.id, "У тебе немає збережених цілей.")
            return

        goal_list = "\n".join([f"{goal.user_goal_number}: {goal.task}" for goal in goals])
        bot.send_message(message.chat.id, f"Твої цілі:\n{goal_list}\n\nВведи номер цілі, яку хочеш видалити:")

        bot.register_next_step_handler(message, process_delete_goal_step)

    except DoesNotExist:
        bot.send_message(message.chat.id, "Спочатку створи ціль")

def process_delete_goal_step(message):
    try:
        goal_id = int(message.text)
        user = User.get(User.chat_id == message.chat.id)
        goal = Goal.get(Goal.user_goal_number == goal_id, Goal.user == user)

        goal.delete_instance()
        bot.send_message(message.chat.id, "Ціль успішно видалено!")

    except ValueError:
        bot.send_message(message.chat.id, "Будь ласка, введи дійсний номер цілі.")
    except DoesNotExist:
        bot.send_message(message.chat.id, "Ціль з таким номером не знайдено або вона вже виконана.")


@bot.message_handler(content_types=['text'])
def create_goal_handler(message):
    if message.text.startswith('/'):
        return  # Ігнорує всі команди

    user = User.get(User.chat_id == message.chat.id)

    # Кількість цілей користувача

    user_goals_count = Goal.select().where(Goal.user == user).count()
    new_user_goal_number = user_goals_count + 1

    Goal.create(
        task=message.text,
        is_done=False,
        user=user,
        date=datetime.today(),
        user_goal_number=new_user_goal_number
    )

    bot.send_message(
        message.chat.id,
        "Твоя ціль збережена!"
    )

# Перевірка на наявність невиконаних цілей
def check_notify():
    for user in User.select():
        goals = Goal.select().where(Goal.user == user,
                                    Goal.date == datetime.today(),
                                    Goal.is_done == False)
        if goals:
            bot.send_message(
                user.chat_id,
                create_all_goal_message(user.chat_id),
                parse_mode='HTML'
            )

# Нагадування
def run_scheduler():
    schedule.every(1).hours.do(check_notify)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    Thread(target=run_scheduler).start()
    bot.infinity_polling()