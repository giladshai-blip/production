import { useState } from 'react';
import { Brain, Sparkles, Loader2, ChevronDown, ChevronUp, Plus } from 'lucide-react';
import { aiApi } from '../api/client.js';

export default function AIPanel({ tasks, onSubtasksCreated }) {
  const [analysis,     setAnalysis]     = useState('');
  const [analyzing,    setAnalyzing]    = useState(false);
  const [selectedTask, setSelectedTask] = useState('');
  const [subtasks,     setSubtasks]     = useState([]);
  const [generating,   setGenerating]   = useState(false);
  const [expanded,     setExpanded]     = useState(null);

  async function handleAnalyze() {
    setAnalyzing(true);
    setAnalysis('');
    try {
      const { analysis } = await aiApi.analyze();
      setAnalysis(analysis);
    } finally { setAnalyzing(false); }
  }

  async function handleSubtasks() {
    if (!selectedTask) return;
    setGenerating(true);
    setSubtasks([]);
    try {
      const created = await aiApi.generateSubtasks(selectedTask);
      setSubtasks(created);
      onSubtasksCreated();
    } finally { setGenerating(false); }
  }

  const activeTasks = tasks.filter(t => t.status !== 'done');

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">ניתוח AI</h1>

      {/* Analysis */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Brain size={20} className="text-blue-600" />
          <h2 className="text-base font-semibold text-gray-700">ניתוח פרודוקטיביות</h2>
        </div>
        <p className="text-sm text-gray-500">
          AI ינתח את כל המשימות שלך ויספק תובנות, דפוסים והמלצות לשיפור.
        </p>
        <button
          onClick={handleAnalyze}
          disabled={analyzing || tasks.length === 0}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          {analyzing ? <Loader2 size={16} className="animate-spin" /> : <Brain size={16} />}
          {analyzing ? 'מנתח...' : 'נתח משימות'}
        </button>

        {analysis && (
          <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
            {analysis}
          </div>
        )}
      </div>

      {/* Subtask generator */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Sparkles size={20} className="text-purple-600" />
          <h2 className="text-base font-semibold text-gray-700">פירוק אוטומטי לתת-משימות</h2>
        </div>
        <p className="text-sm text-gray-500">בחר משימה וה-AI יפרק אותה לתת-משימות מעשיות.</p>

        <div className="flex gap-3">
          <select
            className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            value={selectedTask}
            onChange={e => { setSelectedTask(e.target.value); setSubtasks([]); }}
          >
            <option value="">בחר משימה...</option>
            {activeTasks.map(t => (
              <option key={t.id} value={t.id}>{t.title}</option>
            ))}
          </select>
          <button
            onClick={handleSubtasks}
            disabled={!selectedTask || generating}
            className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            {generating ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
            {generating ? 'מייצר...' : 'צור תת-משימות'}
          </button>
        </div>

        {subtasks.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-medium text-gray-600">✅ נוצרו {subtasks.length} תת-משימות:</p>
            {subtasks.map(t => (
              <div key={t.id}
                className="border border-gray-100 rounded-lg p-3 cursor-pointer hover:bg-gray-50"
                onClick={() => setExpanded(expanded === t.id ? null : t.id)}>
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-gray-700">{t.title}</p>
                  {expanded === t.id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </div>
                {expanded === t.id && t.description && (
                  <p className="text-xs text-gray-400 mt-1">{t.description}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Tips */}
      <div className="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl border border-blue-100 p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">💡 טיפים לשימוש יעיל ב-AI</h3>
        <ul className="space-y-1.5 text-sm text-gray-600">
          <li>• הוסף תיאורים מפורטים למשימות — ה-AI יעדף ויפרק טוב יותר</li>
          <li>• הגדר מועדי אחרון — ה-AI לוקח בחשבון דחיפות זמן</li>
          <li>• הפעל "תעדף עם AI" מהלוח הראשי לאחר הוספת משימות חדשות</li>
          <li>• השתמש בפירוק תת-משימות למשימות גדולות ומורכבות</li>
        </ul>
      </div>
    </div>
  );
}
