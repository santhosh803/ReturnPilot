import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach a DRF auth token when one is stored. The backend only enforces auth when
// REQUIRE_API_AUTH is set; when it isn't, an absent token is harmless.
export const setAuthToken = (token) => {
  if (token) {
    localStorage.setItem("rp_token", token);
  } else {
    localStorage.removeItem("rp_token");
  }
};

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("rp_token");
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
  return config;
});

export const login = async (username, password) => {
  const res = await api.post("/auth/token/", { username, password });
  if (res.data?.token) {
    setAuthToken(res.data.token);
  }
  return res.data;
};

export const getAnalytics = async () => {
  const res = await api.get("/analytics/");
  return res.data;
};

export const getReturns = async (status = "", search = "") => {
  let url = "/returns/";
  const params = new URLSearchParams();
  if (status) params.append("status", status);
  if (search) params.append("search", search);
  const qs = params.toString();
  if (qs) url += `?${qs}`;

  const res = await api.get(url);
  return res.data.results || res.data;
};

export const getOrders = async (search = "") => {
  let url = "/orders/";
  if (search) url += `?search=${encodeURIComponent(search)}`;
  const res = await api.get(url);
  return res.data.results || res.data;
};

export const getCustomers = async (search = "") => {
  let url = "/customers/";
  if (search) url += `?search=${encodeURIComponent(search)}`;
  const res = await api.get(url);
  return res.data.results || res.data;
};

export const sendAgentChat = async (message, sessionId = null) => {
  const res = await api.post("/agent/chat/", {
    message,
    session_id: sessionId,
  });
  return res.data;
};

export const approveAgentReturn = async ({
  sessionId,
  returnId,
  decision,
  reason = "",
}) => {
  const res = await api.post("/agent/approve/", {
    session_id: sessionId,
    return_id: returnId,
    decision,
    reason,
  });
  return res.data;
};

export const getAgentSessions = async () => {
  const res = await api.get("/agent/sessions/");
  return res.data.results || res.data;
};

export default api;
