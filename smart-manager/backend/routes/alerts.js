import { Router } from 'express';
import { v4 as uuid } from 'uuid';
import { db } from '../services/db.js';
import { generateAlerts } from '../services/openai.js';

const router = Router();

router.get('/', (_req, res) => res.json(db.getAlerts()));

router.post('/generate', async (_req, res) => {
  try {
    const tasks = db.getTasks();
    if (!tasks.length) return res.json([]);
    const raw = await generateAlerts(tasks);
    db.clearAlerts();
    const alerts = raw.map(a => db.createAlert({
      id: uuid(), ...a, read: false,
      createdAt: new Date().toISOString(),
    }));
    res.json(alerts);
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: e.message });
  }
});

router.put('/:id/read', (req, res) => {
  const a = db.updateAlert(req.params.id, { read: true });
  if (!a) return res.status(404).json({ error: 'Not found' });
  res.json(a);
});

router.delete('/:id', (req, res) => {
  if (!db.deleteAlert(req.params.id)) return res.status(404).json({ error: 'Not found' });
  res.json({ success: true });
});

export default router;
