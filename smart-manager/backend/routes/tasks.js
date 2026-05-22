import { Router } from 'express';
import { v4 as uuid } from 'uuid';
import { db } from '../services/db.js';
import { prioritizeTasks } from '../services/openai.js';

const router = Router();

router.get('/', (_req, res) => res.json(db.getTasks()));

router.post('/', (req, res) => {
  const { title, description = '', category = 'כללי', dueDate = null, priority = 'medium' } = req.body;
  if (!title?.trim()) return res.status(400).json({ error: 'title is required' });
  const task = {
    id: uuid(), title, description, category, dueDate, priority,
    aiPriority: null, aiReason: null,
    status: 'todo',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
  res.status(201).json(db.createTask(task));
});

router.put('/:id', (req, res) => {
  const task = db.updateTask(req.params.id, req.body);
  if (!task) return res.status(404).json({ error: 'Not found' });
  res.json(task);
});

router.delete('/:id', (req, res) => {
  if (!db.deleteTask(req.params.id)) return res.status(404).json({ error: 'Not found' });
  res.json({ success: true });
});

router.post('/ai-prioritize', async (_req, res) => {
  try {
    const active = db.getTasks().filter(t => t.status !== 'done');
    if (!active.length) return res.json([]);
    const priorities = await prioritizeTasks(active);
    priorities.forEach(({ id, aiPriority, aiReason }) => db.updateTask(id, { aiPriority, aiReason }));
    res.json(db.getTasks());
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: e.message });
  }
});

export default router;
