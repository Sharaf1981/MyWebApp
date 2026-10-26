# MyWebApp — مساعدي الشخصي / Personal Assistant

مساعد شخصي على الويب: مهام وتذكيرات، ملاحظات، ومحادثة ذكية (Claude) تقدر تضيف وتعدّل المهام والملاحظات بنفسها.
واجهة عربي/إنجليزي، وبتشتغل على الموبايل والكمبيوتر، مع وضع ليلي تلقائي.

A web personal assistant: tasks & reminders, notes, and an AI chat (Claude) that can manage them for you.
Arabic/English UI, responsive, automatic dark mode.

## التشغيل / Run

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # من / from https://console.anthropic.com
python app.py
```

افتح / open: http://localhost:5000

## أمثلة للمحادثة / Chat examples

- «فكّرني أدفع فاتورة الكهربا يوم الخميس، أولوية عالية»
- «إيه المهام اللي لسه ماخلصتش؟»
- «احفظ ملاحظة: أفكار لعيد ميلاد سارة — كتاب، ساعة»
- "Mark the electricity bill task as done"

## البنية / Structure

| File | Purpose |
|---|---|
| `app.py` | Flask routes (REST API for tasks, notes, chat) |
| `assistant/db.py` | SQLite storage (`assistant.db`, override with `ASSISTANT_DB`) |
| `assistant/ai.py` | Claude chat with tools for tasks & notes |
| `templates/index.html`, `static/` | Bilingual front end |

ملاحظة: سجل المحادثة محفوظ في الذاكرة ويتمسح لما السيرفر يعيد التشغيل؛ المهام والملاحظات محفوظة في قاعدة البيانات.
Note: chat history lives in memory and resets on server restart; tasks and notes persist in SQLite.
