import { readFileSync, writeFileSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const DB_PATH = join(__dirname, '../data/db.json');
const DEFAULT = { tasks: [], alerts: [] };

function read() {
  if (!existsSync(DB_PATH)) { write(DEFAULT); return structuredClone(DEFAULT); }
  return JSON.parse(readFileSync(DB_PATH, 'utf-8'));
}

function write(data) {
  writeFileSync(DB_PATH, JSON.stringify(data, null, 2));
}

export const db = {
  getTasks:   ()       => read().tasks,
  getTask:    (id)     => read().tasks.find(t => t.id === id),

  createTask: (task)   => { const d = read(); d.tasks.push(task);        write(d); return task; },
  updateTask: (id, up) => {
    const d = read(), i = d.tasks.findIndex(t => t.id === id);
    if (i < 0) return null;
    d.tasks[i] = { ...d.tasks[i], ...up, updatedAt: new Date().toISOString() };
    write(d); return d.tasks[i];
  },
  deleteTask: (id)     => {
    const d = read(), i = d.tasks.findIndex(t => t.id === id);
    if (i < 0) return false;
    d.tasks.splice(i, 1); write(d); return true;
  },

  getAlerts:    ()       => read().alerts,
  createAlert:  (alert)  => { const d = read(); d.alerts.push(alert); write(d); return alert; },
  updateAlert:  (id, up) => {
    const d = read(), i = d.alerts.findIndex(a => a.id === id);
    if (i < 0) return null;
    d.alerts[i] = { ...d.alerts[i], ...up }; write(d); return d.alerts[i];
  },
  deleteAlert:  (id)     => {
    const d = read(), i = d.alerts.findIndex(a => a.id === id);
    if (i < 0) return false;
    d.alerts.splice(i, 1); write(d); return true;
  },
  clearAlerts:  ()       => { const d = read(); d.alerts = []; write(d); },
};
