import logging
import pandas as pd
import random
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler

# Bot Constants
TOKEN = "7815935889:AAEkxqMcB8dY-cFrv7wf1zG2jSALT_htJ-A"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1huvzJxg_hRw4w3urQOYusq_-JGdxaSzMHtBltM9w7UA/export?format=csv"

# States
QUIZ, WAIT_ANSWER = range(2)

# Logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Load Questions
def load_questions():
    try:
        data = pd.read_csv(SHEET_URL)
        questions = data.to_dict(orient="records")

        # Kiểm tra dữ liệu hợp lệ
        valid_questions = []
        for q in questions:
            if all(k in q for k in ["Question", "Option 1", "Option 2", "Option 3", "Option 4", "Answer", "Explanation"]) and q["Answer"] in [1, 2, 3, 4]:
                valid_questions.append(q)
            else:
                logger.warning(f"Invalid question data: {q}")

        random.shuffle(valid_questions)
        return valid_questions[:20]
    except Exception as e:
        logger.error(f"Error loading questions: {e}")
        return []

# Start Command
def start(update: Update, context: CallbackContext):
    context.user_data["questions"] = load_questions()
    context.user_data["current_question"] = 0
    context.user_data["score"] = 0

    if not context.user_data["questions"]:
        update.message.reply_text("⚠️ Không thể tải câu hỏi. Vui lòng thử lại sau.")
        return

    update.message.reply_text(
        "🎉 Chào mừng bạn đến với Gameshow 'Hiểu biết về Việt Nam'!\n\n"
        "📜 *Luật chơi:*\n"
        "- Có 20 câu hỏi.\n"
        "- Mỗi câu trả lời đúng được 1 điểm.\n"
        "- Nếu không trả lời trong 60 giây, bạn sẽ bị tính 0 điểm.\n\n"
        "🔥 Bạn đã sẵn sàng? Nhấn /quiz để bắt đầu trả lời các câu hỏi!"
    )

# Quiz Command
def quiz(update: Update, context: CallbackContext):
    context.user_data["questions"] = load_questions()
    context.user_data["current_question"] = 0
    context.user_data["score"] = 0

    if not context.user_data["questions"]:
        update.message.reply_text("⚠️ Không thể tải câu hỏi. Vui lòng thử lại sau.")
        return

    ask_question(update, context)

# Ask Next Question
def ask_question(update: Update, context: CallbackContext):
    user_data = context.user_data
    current = user_data["current_question"]
    questions = user_data["questions"]

    # Hủy job timeout cũ nếu tồn tại
    if "timeout_job" in user_data and user_data["timeout_job"] is not None:
        user_data["timeout_job"].schedule_removal()

    if current < len(questions):
        question = questions[current]
        options = [question["Option 1"], question["Option 2"], question["Option 3"], question["Option 4"]]
        user_data["current_question"] += 1

        reply_markup = ReplyKeyboardMarkup([[1, 2, 3, 4]], one_time_keyboard=True)
        update.message.reply_text(
            f"💬 Câu {current + 1}: {question['Question']}\n\n"
            f"1️⃣ {options[0]}\n"
            f"2️⃣ {options[1]}\n"
            f"3️⃣ {options[2]}\n"
            f"4️⃣ {options[3]}",
            reply_markup=reply_markup,
        )

        # Đặt timeout mới
        timeout_job = context.job_queue.run_once(timeout_handler, 60, context=update.message.chat_id)
        user_data["timeout_job"] = timeout_job
    else:
        finish_quiz(update, context)

# Timeout Handler
def timeout_handler(context: CallbackContext):
    chat_id = context.job.context
    bot = context.bot

    user_data = context.dispatcher.user_data.get(chat_id, {})
    current = user_data.get("current_question", 0)
    questions = user_data.get("questions", [])

    if current < len(questions):
        bot.send_message(
            chat_id=chat_id,
            text=f"⏳ Hết thời gian cho câu này! Tổng điểm hiện tại của bạn là {user_data['score']}/20."
        )
        ask_question_via_context(context, chat_id)
    else:
        finish_quiz_via_context(context, chat_id)

# Ask Question via Context
def ask_question_via_context(context: CallbackContext, chat_id):
    user_data = context.dispatcher.user_data[chat_id]
    current = user_data.get("current_question", 0)
    questions = user_data.get("questions", [])

    if current < len(questions):
        question = questions[current]
        options = [question["Option 1"], question["Option 2"], question["Option 3"], question["Option 4"]]
        user_data["current_question"] += 1

        context.bot.send_message(
            chat_id=chat_id,
            text=f"💬 *Câu {current + 1}:* {question['Question']}\n\n"
                 f"1️⃣ {options[0]}\n"
                 f"2️⃣ {options[1]}\n"
                 f"3️⃣ {options[2]}\n"
                 f"4️⃣ {options[3]}",
            reply_markup=ReplyKeyboardMarkup([[1, 2, 3, 4]], one_time_keyboard=True),
        )

        timeout_job = context.job_queue.run_once(timeout_handler, 60, context=chat_id)
        user_data["timeout_job"] = timeout_job

# Handle Answer
def handle_answer(update: Update, context: CallbackContext):
    user_data = context.user_data
    current = user_data["current_question"] - 1
    questions = user_data["questions"]

    try:
        user_answer = int(update.message.text)
    except ValueError:
        update.message.reply_text("⚠️ Vui lòng chọn 1, 2, 3 hoặc 4.")
        return

    correct_answer = int(questions[current]["Answer"])
    explanation = questions[current]["Explanation"]

    if user_answer == correct_answer:
        user_data["score"] += 1
        update.message.reply_text(
            f"👍 Chính xác! Tổng điểm của bạn hiện tại là {user_data['score']}/20.\n\n📖 Lý giải: {explanation}"
        )
    else:
        update.message.reply_text(
            f"😥 Sai rồi! Đáp án đúng là {correct_answer}.\n\n📖 Lý giải: {explanation}\n\n"
            f"Tổng điểm hiện tại của bạn là {user_data['score']}/20."
        )

    ask_question(update, context)

# Finish Quiz
def finish_quiz(update: Update, context: CallbackContext):
    user_data = context.user_data
    score = user_data.get("score", 0)

    if score >= 15:
        result = "🥇 Bạn là chuyên gia về Việt Nam!"
    elif 12 <= score < 15:
        result = "🥈 Bạn có kiến thức khá tốt về Việt Nam!"
    else:
        result = "🥉 Hãy tìm hiểu thêm về Việt Nam nhé!"

    update.message.reply_text(
        f"🎉 *Chúc mừng bạn đã hoàn thành cuộc thi 'Hiểu biết về Việt Nam'!*\n\n"
        f"🏆 *Tổng điểm của bạn:* {score}/20.\n{result}"
    )

# Main Function
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("quiz", quiz))
    dp.add_handler(MessageHandler(Filters.regex("^[1-4]$"), handle_answer))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
