import axios from 'axios';

const api = axios.create({ baseURL: '/api' });

export const tasksApi = {
  getAll:       ()        => api.get('/tasks').then(r => r.data),
  create:       (body)    => api.post('/tasks', body).then(r => r.data),
  update:       (id, body)=> api.put(`/tasks/${id}`, body).then(r => r.data),
  remove:       (id)      => api.delete(`/tasks/${id}`).then(r => r.data),
  aiPrioritize: ()        => api.post('/tasks/ai-prioritize').then(r => r.data),
};

export const aiApi = {
  analyze:         ()   => api.post('/ai/analyze').then(r => r.data),
  generateSubtasks:(id) => api.post(`/ai/subtasks/${id}`).then(r => r.data),
};

export const alertsApi = {
  getAll:   ()   => api.get('/alerts').then(r => r.data),
  generate: ()   => api.post('/alerts/generate').then(r => r.data),
  markRead: (id) => api.put(`/alerts/${id}/read`).then(r => r.data),
  remove:   (id) => api.delete(`/alerts/${id}`).then(r => r.data),
};
