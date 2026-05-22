import { useState } from 'react';
import { Loader2, Zap, TrendingUp, Clock, CheckCircle2 } from 'lucide-react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { tasksApi } from '../api/client.js';

const PRIORITY_COLOR = { urgent: '#ef4444', high: '#f97316', medium: '#eab308', low: '#22c55e' };
const PRIORITY_LABEL = { urgent: 'דחוף', high: 'גבוה', medium: 'בינוני', low: 'נמוך' };
const STATUS_COLORS  = { todo: '#94a3b8', in_progress: '#3b82f6', done: '#22c55e' };

function StatCard({ label, value, sub, Icon, color }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 flex items-center gap-4">
      <div className={`p-3 rounded-lg ${color}`}>
        <Icon size={22} className="text-white" />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-800">{value}</p>
        <p className="text-sm text-gray-500">{label}</p>
        {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

export default function Dashboard({ tasks, setTasks }) {
  const [busy, setBusy] = useState(false);

  const total      = tasks.length;
  const urgent     = tasks.filter(t => t.priority === 'urgent').length;
  const inProgress = tasks.filter(t => t.status === 'in_progress').length;
  const done       = tasks.filter(t => t.status === 'done').length;

  const topAI = [...tasks]
    .filter(t => t.aiPriority && t.status !== 'done')
    .sort((a, b) => b.aiPriority - a.aiPriority)
    .slice(0, 6);

  const statusData = [
    { name: 'לביצוע',  value: tasks.filter(t => t.status === 'todo').length,        fill: STATUS_COLORS.todo },
    { name: 'בביצוע',  value: inProgress,                                            fill: STATUS_COLORS.in_progress },
    { name: 'הושלם',   value: done,                                                  fill: STATUS_COLORS.done },
  ].filter(d => d.value > 0);

  const categoryData = [...new Set(tasks.map(t => t.category))].map(cat => ({
    name: cat,
    סה_כ: tasks.filter(t => t.category === cat).length,
    הושלם: tasks.filter(t => t.category === cat && t.status === 'done').length,
  }));

  async function handlePrioritize() {
    setBusy(true);
    try { setTasks(await tasksApi.aiPrioritize()); }
    finally { setBusy(false); }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">לוח בקרה</h1>
        <button
          onClick={handlePrioritize}
          disabled={busy || total === 0}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          {busy ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />}
          תעדף עם AI
        </button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="סה״כ משימות"  value={total}      Icon={CheckCircle2} color="bg-slate-500" />
        <StatCard label="דחופות"        value={urgent}     Icon={Zap}          color="bg-red-500"   />
        <StatCard label="בביצוע"        value={inProgress} Icon={Clock}        color="bg-blue-500"  />
        <StatCard label="הושלמו"        value={done}       Icon={TrendingUp}   color="bg-green-500"
          sub={total ? `${Math.round(done / total * 100)}% השלמה` : ''} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* AI Priority list */}
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <h2 className="text-base font-semibold text-gray-700 mb-4">
            {topAI.length ? '🤖 עדיפות AI — המשימות הקריטיות' : 'עדיין אין ניקוד AI — לחץ "תעדף עם AI"'}
          </h2>
          {topAI.length === 0 && tasks.length > 0 && (
            <p className="text-sm text-gray-400">לחץ על "תעדף עם AI" בכדי לקבל ניתוח</p>
          )}
          <div className="space-y-3">
            {topAI.map((t, i) => (
              <div key={t.id} className="flex items-center gap-3">
                <span className="text-lg font-bold text-gray-300 w-6">#{i + 1}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">{t.title}</p>
                  {t.aiReason && <p className="text-xs text-gray-400 truncate">{t.aiReason}</p>}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium`}
                    style={{ background: PRIORITY_COLOR[t.priority] + '20', color: PRIORITY_COLOR[t.priority] }}>
                    {PRIORITY_LABEL[t.priority]}
                  </span>
                  <div className="w-20 bg-gray-100 rounded-full h-2">
                    <div className="h-2 rounded-full bg-blue-500" style={{ width: `${t.aiPriority}%` }} />
                  </div>
                  <span className="text-xs text-gray-500 w-6 text-left">{t.aiPriority}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Pie chart */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <h2 className="text-base font-semibold text-gray-700 mb-2">סטטוס משימות</h2>
          {statusData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={statusData} dataKey="value" nameKey="name"
                  cx="50%" cy="50%" outerRadius={70} label={({ name, value }) => `${name} (${value})`}>
                  {statusData.map((d, i) => <Cell key={i} fill={d.fill} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-400 text-sm">אין נתונים</div>
          )}
        </div>
      </div>

      {/* Bar chart by category */}
      {categoryData.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <h2 className="text-base font-semibold text-gray-700 mb-4">משימות לפי קטגוריה</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={categoryData} layout="vertical" margin={{ right: 20 }}>
              <XAxis type="number" fontSize={12} />
              <YAxis dataKey="name" type="category" width={90} fontSize={12} />
              <Tooltip />
              <Legend />
              <Bar dataKey="סה_כ"  fill="#3b82f6" name="סה״כ"    radius={[0, 4, 4, 0]} />
              <Bar dataKey="הושלם" fill="#22c55e" name="הושלם"   radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
