import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import { mkdirSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import tasksRouter  from './routes/tasks.js';
import aiRouter     from './routes/ai.js';
import alertsRouter from './routes/alerts.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const dataDir = join(__dirname, 'data');
if (!existsSync(dataDir)) mkdirSync(dataDir);

const app  = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

app.use('/api/tasks',  tasksRouter);
app.use('/api/ai',     aiRouter);
app.use('/api/alerts', alertsRouter);
app.get('/api/health', (_req, res) => res.json({ status: 'ok', ts: new Date() }));

app.listen(PORT, () => console.log(`✅  Backend on http://localhost:${PORT}`));
