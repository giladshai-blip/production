import { Router } from 'express';
import { v4 as uuid } from 'uuid';
import { db } from '../services/db.js';
import { analyzeTasks, generateSubtasks } from '../services/openai.js';

const router = Router();

router.post('/analyze', async (_req, res) => {
  try {
    const tasks = db.getTasks();
    if (!tasks.length) return res.json({ analysis: 'אין משימות לניתוח עדיין.' });
    const analysis = await analyzeTasks(tasks);
    res.json({ analysis });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: e.message });
  }
});

router.post('/subtasks/:id', async (req, res) => {
  try {
    const task = db.getTask(req.params.id);
    if (!task) return res.status(404).json({ error: 'Not found' });
    const subtasks = await generateSubtasks(task);
    const created = subtasks.map(st =>
      db.createTask({
        id: uuid(), title: st.title, description: st.description,
        category: task.category, priority: task.priority,
        aiPriority: null, aiReason: null,
        status: 'todo', dueDate: task.dueDate,
        parentId: task.id,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      })
    );
    res.json(created);
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: e.message });
  }
});

export default router;
