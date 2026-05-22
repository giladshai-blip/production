import OpenAI from 'openai';

const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const MODEL = 'gpt-4o-mini';

async function jsonChat(system, user) {
  const res = await client.chat.completions.create({
    model: MODEL,
    response_format: { type: 'json_object' },
    temperature: 0.3,
    messages: [
      { role: 'system', content: system },
      { role: 'user',   content: user },
    ],
  });
  return JSON.parse(res.choices[0].message.content);
}

export async function prioritizeTasks(tasks) {
  const data = await jsonChat(
    `אתה מנהל משימות חכם. קבל רשימת משימות והחזר ציון עדיפות AI (1-100) לכל אחת לפי דחיפות, חשיבות, מועד אחרון והשפעה עסקית.
החזר JSON בלבד: {"priorities": [{"id": "...", "aiPriority": 85, "aiReason": "..."}]}`,
    `תעדף:\n${JSON.stringify(tasks.map(t => ({ id: t.id, title: t.title, priority: t.priority, dueDate: t.dueDate, status: t.status, description: t.description })))}`,
  );
  return data.priorities ?? [];
}

export async function analyzeTasks(tasks) {
  const res = await client.chat.completions.create({
    model: MODEL,
    temperature: 0.5,
    messages: [
      {
        role: 'system',
        content: 'אתה יועץ פרודוקטיביות. נתח את רשימת המשימות וספק: (1) תובנות עיקריות, (2) דפוסים שזיהית, (3) 3 המלצות מעשיות. ענה בעברית בצורה תמציתית, השתמש בנקודות.',
      },
      {
        role: 'user',
        content: `נתח:\n${JSON.stringify(tasks)}`,
      },
    ],
  });
  return res.choices[0].message.content;
}

export async function generateAlerts(tasks) {
  const data = await jsonChat(
    `אתה מערכת התראות חכמה. זהה משימות שדורשות תשומת לב (דחופות, באיחור, תקועות).
החזר JSON: {"alerts": [{"type": "urgent|warning|info", "title": "...", "message": "...", "taskId": "..."}]}
הגבל ל-5 התראות רלוונטיות לכל היותר.`,
    `בדוק:\n${JSON.stringify(tasks.map(t => ({ id: t.id, title: t.title, priority: t.priority, dueDate: t.dueDate, status: t.status })))}`,
  );
  return data.alerts ?? [];
}

export async function generateSubtasks(task) {
  const data = await jsonChat(
    `אתה מנהל פרויקטים מנוסה. פרק משימה ל-3-5 תת-משימות ברורות ומעשיות.
החזר JSON: {"subtasks": [{"title": "...", "description": "..."}]}`,
    `פרק: כותרת="${task.title}", תיאור="${task.description ?? ''}"`,
  );
  return data.subtasks ?? [];
}
