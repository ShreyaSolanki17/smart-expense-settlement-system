const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";

async function request(path, { method = "GET", token, body } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Token ${token}` } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    throw new Error(data?.detail || JSON.stringify(data) || res.statusText);
  }
  return data;
}

export const api = {
  register: (username, password) =>
    request("/auth/register/", { method: "POST", body: { username, password } }),
  login: (username, password) =>
    request("/auth/login/", { method: "POST", body: { username, password } }),
  demoLogin: () => request("/auth/demo/", { method: "POST" }),
  me: (token) => request("/auth/me/", { token }),
  searchUsers: (token, q) => request(`/users/?q=${encodeURIComponent(q)}`, { token }),

  listGroups: (token) => request("/groups/", { token }),
  createGroup: (token, name, memberIds) =>
    request("/groups/", { method: "POST", token, body: { name, member_ids: memberIds } }),

  listExpenses: (token, groupId) => request(`/expenses/?group=${groupId}`, { token }),
  createExpense: (token, { group, description, amount, paid_by }) =>
    request("/expenses/", { method: "POST", token, body: { group, description, amount, paid_by } }),

  getBalances: (token, groupId) => request(`/groups/${groupId}/balances/`, { token }),
  createSettlement: (token, { group, from_user, to_user, amount }) =>
    request("/settlements/", {
      method: "POST",
      token,
      body: { group, from_user, to_user, amount },
    }),

  listNotifications: (token) => request("/notifications/", { token }),
  markNotificationRead: (token, id) =>
    request(`/notifications/${id}/mark_read/`, { method: "POST", token }),
};
