import { useState, useEffect, useCallback } from 'react';
import { LayoutDashboard, CheckSquare, Brain, Bell, Loader2 } from 'lucide-react';
import { tasksApi, alertsApi } from './api/client.js';
import Dashboard    from './components/Dashboard.jsx';
import TaskManager  from './components/TaskManager.jsx';
import AIPanel      from './components/AIPanel.jsx';
import AlertsPanel  from './components/AlertsPanel.jsx';

const NAV = [
  { id: 'dashboard', label: 'לוח בקרה',    Icon: LayoutDashboard },
  { id: 'tasks',     label: 'משימות',       Icon: CheckSquare },
  { id: 'ai',        label: 'ניתוח AI',     Icon: Brain },
  { id: 'alerts',    label: 'התראות',       Icon: Bell },
];

export default function App() {
  const [page,   setPage]   = useState('dashboard');
  const [tasks,  setTasks]  = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [busy,   setBusy]   = useState(true);

  const loadTasks  = useCallback(async () => setTasks(await tasksApi.getAll()),   []);
  const loadAlerts = useCallback(async () => setAlerts(await alertsApi.getAll()), []);

  useEffect(() => {
    Promise.all([loadTasks(), loadAlerts()]).finally(() => setBusy(false));
  }, [loadTasks, loadAlerts]);

  const unread = alerts.filter(a => !a.read).length;

  if (busy) return (
    <div className="h-screen flex items-center justify-center bg-gray-50">
      <Loader2 className="animate-spin text-blue-600" size={40} />
    </div>
  );

  return (
    <div className="flex h-screen bg-gray-50 font-sans" dir="rtl">
      {/* Sidebar */}
      <aside className="w-60 bg-slate-900 text-white flex flex-col shrink-0">
        <div className="px-6 py-5 border-b border-slate-700">
          <div className="flex items-center gap-2">
            <Brain size={22} className="text-blue-400" />
            <span className="text-lg font-bold tracking-tight">מנהל חכם AI</span>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV.map(({ id, label, Icon }) => (
            <button
              key={id}
              onClick={() => setPage(id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors
                ${page === id
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'}`}
            >
              <Icon size={18} />
              <span>{label}</span>
              {id === 'alerts' && unread > 0 && (
                <span className="mr-auto bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                  {unread}
                </span>
              )}
            </button>
          ))}
        </nav>

        <div className="px-5 py-4 border-t border-slate-700 text-xs text-slate-400">
          {tasks.length} משימות · {tasks.filter(t => t.status === 'done').length} הושלמו
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">
        {page === 'dashboard' && (
          <Dashboard tasks={tasks} alerts={alerts} onRefresh={loadTasks} setTasks={setTasks} />
        )}
        {page === 'tasks' && (
          <TaskManager tasks={tasks} setTasks={setTasks} onRefresh={loadTasks} />
        )}
        {page === 'ai' && (
          <AIPanel tasks={tasks} onSubtasksCreated={loadTasks} />
        )}
        {page === 'alerts' && (
          <AlertsPanel alerts={alerts} setAlerts={setAlerts} tasks={tasks} />
        )}
      </main>
    </div>
  );
}
