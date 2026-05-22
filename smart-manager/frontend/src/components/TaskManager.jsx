import { useState } from 'react';
import { Plus, Pencil, Trash2, ChevronUp, ChevronDown, Loader2 } from 'lucide-react';
import { tasksApi } from '../api/client.js';

const PRIORITY_STYLE = {
  urgent: 'bg-red-100 text-red-700',
  high:   'bg-orange-100 text-orange-700',
  medium: 'bg-yellow-100 text-yellow-700',
  low:    'bg-green-100 text-green-700',
};
const PRIORITY_LABEL = { urgent: 'דחוף', high: 'גבוה', medium: 'בינוני', low: 'נמוך' };
const STATUS_STYLE   = {
  todo:        'bg-gray-100 text-gray-600',
  in_progress: 'bg-blue-100 text-blue-700',
  done:        'bg-green-100 text-green-700',
};
const STATUS_LABEL   = { todo: 'לביצוע', in_progress: 'בביצוע', done: 'הושלם' };
const STATUS_NEXT    = { todo: 'in_progress', in_progress: 'done', done: 'todo' };

const EMPTY_FORM = { title: '', description: '', category: 'כללי', priority: 'medium', dueDate: '' };

function TaskForm({ initial = EMPTY_FORM, onSave, onCancel, saving }) {
  const [form, setForm] = useState(initial);
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 space-y-4" dir="rtl">
        <h2 className="text-lg font-bold text-gray-800">{initial.id ? 'עריכת משימה' : 'משימה חדשה'}</h2>

        <div className="space-y-3">
          <input
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="כותרת המשימה *"
            value={form.title}
            onChange={e => set('title', e.target.value)}
          />
          <textarea
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="תיאור (אופציונלי)"
            rows={3}
            value={form.description}
            onChange={e => set('description', e.target.value)}
          />
          <div className="grid grid-cols-2 gap-3">
            <select
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.priority}
              onChange={e => set('priority', e.target.value)}
            >
              <option value="low">נמוך</option>
              <option value="medium">בינוני</option>
              <option value="high">גבוה</option>
              <option value="urgent">דחוף</option>
            </select>
            <input
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="קטגוריה"
              value={form.category}
              onChange={e => set('category', e.target.value)}
            />
          </div>
          <input
            type="date"
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={form.dueDate ?? ''}
            onChange={e => set('dueDate', e.target.value)}
          />
        </div>

        <div className="flex gap-2 justify-end">
          <button onClick={onCancel}
            className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
            ביטול
          </button>
          <button
            onClick={() => onSave(form)}
            disabled={!form.title.trim() || saving}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            {saving && <Loader2 size={14} className="animate-spin" />}
            {initial.id ? 'עדכן' : 'צור'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function TaskManager({ tasks, setTasks }) {
  const [filterStatus,   setFilterStatus]   = useState('');
  const [filterPriority, setFilterPriority] = useState('');
  const [search,         setSearch]         = useState('');
  const [sortKey,        setSortKey]        = useState('createdAt');
  const [sortAsc,        setSortAsc]        = useState(false);
  const [showForm,       setShowForm]       = useState(false);
  const [editTask,       setEditTask]       = useState(null);
  const [saving,         setSaving]         = useState(false);

  const filtered = tasks
    .filter(t =>
      (!filterStatus   || t.status   === filterStatus)   &&
      (!filterPriority || t.priority === filterPriority) &&
      (!search         || t.title.includes(search) || t.category.includes(search))
    )
    .sort((a, b) => {
      const va = a[sortKey] ?? '', vb = b[sortKey] ?? '';
      return sortAsc ? (va > vb ? 1 : -1) : (va < vb ? 1 : -1);
    });

  function toggleSort(key) {
    if (sortKey === key) setSortAsc(v => !v);
    else { setSortKey(key); setSortAsc(false); }
  }

  const SortIcon = ({ k }) => sortKey === k
    ? (sortAsc ? <ChevronUp size={14} /> : <ChevronDown size={14} />)
    : null;

  async function handleSave(form) {
    setSaving(true);
    try {
      if (editTask?.id) {
        const updated = await tasksApi.update(editTask.id, form);
        setTasks(ts => ts.map(t => t.id === updated.id ? updated : t));
      } else {
        const created = await tasksApi.create(form);
        setTasks(ts => [created, ...ts]);
      }
      setShowForm(false); setEditTask(null);
    } finally { setSaving(false); }
  }

  async function handleDelete(id) {
    if (!confirm('למחוק משימה זו?')) return;
    await tasksApi.remove(id);
    setTasks(ts => ts.filter(t => t.id !== id));
  }

  async function handleStatusToggle(task) {
    const updated = await tasksApi.update(task.id, { status: STATUS_NEXT[task.status] });
    setTasks(ts => ts.map(t => t.id === updated.id ? updated : t));
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">ניהול משימות</h1>
        <button
          onClick={() => { setEditTask(null); setShowForm(true); }}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
        >
          <Plus size={16} /> משימה חדשה
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 bg-white p-4 rounded-xl border border-gray-100 shadow-sm">
        <input
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm flex-1 min-w-40 focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="חיפוש..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <select className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none" value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
          <option value="">כל הסטטוסים</option>
          <option value="todo">לביצוע</option>
          <option value="in_progress">בביצוע</option>
          <option value="done">הושלם</option>
        </select>
        <select className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none" value={filterPriority} onChange={e => setFilterPriority(e.target.value)}>
          <option value="">כל העדיפויות</option>
          <option value="urgent">דחוף</option>
          <option value="high">גבוה</option>
          <option value="medium">בינוני</option>
          <option value="low">נמוך</option>
        </select>
        <span className="text-sm text-gray-400 self-center">{filtered.length} משימות</span>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-100 text-gray-500">
              {[
                ['title',     'כותרת'],
                ['category',  'קטגוריה'],
                ['priority',  'עדיפות'],
                ['aiPriority','AI ציון'],
                ['dueDate',   'מועד אחרון'],
                ['status',    'סטטוס'],
              ].map(([k, label]) => (
                <th key={k}
                  className="text-right px-4 py-3 font-medium cursor-pointer hover:text-gray-700 select-none"
                  onClick={() => toggleSort(k)}>
                  <span className="flex items-center gap-1">{label}<SortIcon k={k} /></span>
                </th>
              ))}
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr><td colSpan={7} className="text-center py-12 text-gray-400">אין משימות</td></tr>
            )}
            {filtered.map(task => (
              <tr key={task.id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3">
                  <p className="font-medium text-gray-800 max-w-xs truncate">{task.title}</p>
                  {task.description && <p className="text-xs text-gray-400 truncate max-w-xs">{task.description}</p>}
                </td>
                <td className="px-4 py-3 text-gray-500">{task.category}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PRIORITY_STYLE[task.priority]}`}>
                    {PRIORITY_LABEL[task.priority]}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {task.aiPriority != null ? (
                    <div className="flex items-center gap-2">
                      <div className="w-16 bg-gray-100 rounded-full h-1.5">
                        <div className="h-1.5 rounded-full bg-blue-500" style={{ width: `${task.aiPriority}%` }} />
                      </div>
                      <span className="text-gray-500 text-xs">{task.aiPriority}</span>
                    </div>
                  ) : <span className="text-gray-300">—</span>}
                </td>
                <td className="px-4 py-3 text-gray-500">
                  {task.dueDate ? new Date(task.dueDate).toLocaleDateString('he-IL') : '—'}
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => handleStatusToggle(task)}
                    className={`text-xs px-2 py-0.5 rounded-full font-medium cursor-pointer ${STATUS_STYLE[task.status]}`}>
                    {STATUS_LABEL[task.status]}
                  </button>
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-1">
                    <button onClick={() => { setEditTask(task); setShowForm(true); }}
                      className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                      <Pencil size={14} />
                    </button>
                    <button onClick={() => handleDelete(task.id)}
                      className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showForm && (
        <TaskForm
          initial={editTask ?? EMPTY_FORM}
          onSave={handleSave}
          onCancel={() => { setShowForm(false); setEditTask(null); }}
          saving={saving}
        />
      )}
    </div>
  );
}
