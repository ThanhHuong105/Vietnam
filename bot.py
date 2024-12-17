import logging
import pandas as pd
import random
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Bot Constants
TOKEN = "7815935889:AAEkxqMcB8dY-cFrv7wf1zG2jSALT_htJ-A"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1huvzJxg_hRw4w3urQOYusq_-JGdxaSzMHtBltM9w7UA/export?format=csv"

# Logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Load Questions
def load_questions():
    try:
        data = pd.read_csv(SHEET_URL)
        questions = data.to_dict(orient="records")
        random.shuffle(questions)
        return questions[:20]
    except Exception as e:
        logger.error(f"Error loading questions: {e}")
        return []

# Start Command
def start(update: Update, context: CallbackContext):
    context.user_data["questions"] = load_questions()
    context.user_data["current_question"] = 0
    context.user_data["score"] = 0

    update.message.reply_text(
        "🎉 Chào mừng bạn đến với Gameshow 'Hiểu biết về Việt Nam'!\n\n"
        "📜 *Luật chơi:*\n"
        "- Có 20 câu hỏi.\n"
        "- Mỗi câu trả lời đúng được 1 điểm.\n"
        "- Nếu không trả lời trong 60 giây, bạn sẽ bị tính 0 điểm.\n\n"
        "🔥 Bạn đã sẵn sàng? Nhấn /quiz để bắt đầu!"
    )

# Ask Question
def ask_question(update: Update, context: CallbackContext):
    user_data = context.user_data
    current = user_data["current_question"]
    questions = user_data["questions"]

    if current < len(questions):
        question = questions[current]
        options = [question["Option 1"], question["Option 2"], question["Option 3"], question["Option 4"]]

        reply_markup = ReplyKeyboardMarkup([[1, 2, 3, 4]], one_time_keyboard=True)
        update.message.reply_text(
            f"💬 Câu {current + 1}: {question['Question']}\n\n"
            f"1️⃣ {options[0]}\n"
            f"2️⃣ {options[1]}\n"
            f"3️⃣ {options[2]}\n"
            f"4️⃣ {options[3]}",
            reply_markup=reply_markup,
        )

        context.user_data["current_question"] += 1
    else:
        finish_quiz(update, context)

# Handle Answer
def handle_answer(update: Update, context: CallbackContext):
    user_data = context.user_data
    questions = user_data["questions"]
    current = user_data["current_question"] - 1

    try:
        user_answer = int(update.message.text)
        correct_answer = int(questions[current]["Answer"])
        explanation = questions[current]["Explanation"]

        if user_answer == correct_answer:
            user_data["score"] += 1
            update.message.reply_text(f"👍 Chính xác!\n📖 Giải thích: {explanation}")
        else:
            update.message.reply_text(f"❌ Sai rồi! Đáp án đúng là {correct_answer}.\n📖 Giải thích: {explanation}")

    except Exception as e:
        update.message.reply_text("⚠️ Vui lòng chọn 1, 2, 3 hoặc 4.")
        logger.error(f"Error processing answer: {e}")
        return

    ask_question(update, context)

# Finish Quiz
def finish_quiz(update: Update, context: CallbackContext):
    score = context.user_data["score"]
    update.message.reply_text(
        f"🎉 Kết thúc quiz! Tổng điểm của bạn là {score}/20.\n"
        f"🥇 Xuất sắc!" if score > 15 else "🥈 Khá tốt!" if score > 10 else "🥉 Cần cố gắng hơn!"
    )

# Main Function
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("quiz", ask_question))
    dp.add_handler(MessageHandler(Filters.regex("^[1-4]$"), handle_answer))

    updater.start_polling()
    logger.info("Bot is running...")
    updater.idle()

if __name__ == "__main__":
    main()
