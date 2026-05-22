import { useState } from 'react';
import { Bell, Loader2, Trash2, Check, AlertTriangle, Info, Zap } from 'lucide-react';
import { alertsApi } from '../api/client.js';

const TYPE_CONFIG = {
  urgent:  { Icon: Zap,           bg: 'bg-red-50',     border: 'border-red-200',    badge: 'bg-red-100 text-red-700',    label: 'דחוף'   },
  warning: { Icon: AlertTriangle, bg: 'bg-orange-50',  border: 'border-orange-200', badge: 'bg-orange-100 text-orange-700', label: 'אזהרה' },
  info:    { Icon: Info,          bg: 'bg-blue-50',    border: 'border-blue-200',   badge: 'bg-blue-100 text-blue-700',  label: 'מידע'   },
};

export default function AlertsPanel({ alerts, setAlerts, tasks }) {
  const [generating, setGenerating] = useState(false);

  async function handleGenerate() {
    setGenerating(true);
    try {
      const fresh = await alertsApi.generate();
      setAlerts(fresh);
    } finally { setGenerating(false); }
  }

  async function handleRead(id) {
    const updated = await alertsApi.markRead(id);
    setAlerts(as => as.map(a => a.id === id ? updated : a));
  }

  async function handleDelete(id) {
    await alertsApi.remove(id);
    setAlerts(as => as.filter(a => a.id !== id));
  }

  async function handleReadAll() {
    const unread = alerts.filter(a => !a.read);
    await Promise.all(unread.map(a => alertsApi.markRead(a.id)));
    setAlerts(as => as.map(a => ({ ...a, read: true })));
  }

  const unread = alerts.filter(a => !a.read).length;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-gray-800">התראות חכמות</h1>
          {unread > 0 && (
            <span className="bg-red-500 text-white text-xs rounded-full px-2 py-0.5 font-medium">
              {unread} חדש
            </span>
          )}
        </div>
        <div className="flex gap-2">
          {unread > 0 && (
            <button onClick={handleReadAll}
              className="flex items-center gap-2 border border-gray-200 hover:bg-gray-50 text-gray-600 px-3 py-2 rounded-lg text-sm transition-colors">
              <Check size={14} /> סמן הכל כנקרא
            </button>
          )}
          <button
            onClick={handleGenerate}
            disabled={generating || tasks.length === 0}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            {generating ? <Loader2 size={16} className="animate-spin" /> : <Bell size={16} />}
            {generating ? 'מנתח...' : 'ייצר התראות AI'}
          </button>
        </div>
      </div>

      {alerts.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-12 text-center">
          <Bell size={40} className="mx-auto text-gray-200 mb-3" />
          <p className="text-gray-400 text-sm">אין התראות כרגע.</p>
          <p className="text-gray-400 text-xs mt-1">לחץ "ייצר התראות AI" לניתוח המשימות שלך</p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map(alert => {
            const cfg = TYPE_CONFIG[alert.type] ?? TYPE_CONFIG.info;
            const { Icon } = cfg;
            const relatedTask = tasks.find(t => t.id === alert.taskId);
            return (
              <div
                key={alert.id}
                className={`rounded-xl border p-4 flex gap-4 transition-opacity ${cfg.bg} ${cfg.border} ${alert.read ? 'opacity-60' : ''}`}
              >
                <div className="shrink-0 mt-0.5">
                  <Icon size={18} className={alert.type === 'urgent' ? 'text-red-500' : alert.type === 'warning' ? 'text-orange-500' : 'text-blue-500'} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cfg.badge}`}>{cfg.label}</span>
                    {!alert.read && <span className="w-2 h-2 bg-blue-500 rounded-full" />}
                  </div>
                  <p className="text-sm font-medium text-gray-800">{alert.title}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{alert.message}</p>
                  {relatedTask && (
                    <p className="text-xs text-gray-400 mt-1">📌 משימה: {relatedTask.title}</p>
                  )}
                  <p className="text-xs text-gray-300 mt-1">
                    {new Date(alert.createdAt).toLocaleString('he-IL')}
                  </p>
                </div>
                <div className="flex gap-1 shrink-0">
                  {!alert.read && (
                    <button onClick={() => handleRead(alert.id)}
                      className="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded-lg transition-colors">
                      <Check size={14} />
                    </button>
                  )}
                  <button onClick={() => handleDelete(alert.id)}
                    className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors">
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
