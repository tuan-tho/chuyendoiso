// =======================
//  frontend/common/script.js
// =======================
const API_BASE = "http://127.0.0.1:8000"; // Backend FastAPI

// ✅ Đường dẫn backend
const REPORTS_PATH  = "/reports";
const CHECKINS_PATH = "/checkins";
// ✅ Upload ảnh check-in/out
const CHECKINS_UPLOAD_PATH = `${CHECKINS_PATH}/upload`;

/* LOCAL STORAGE (đa phiên) */
const NS = "ktx";
const LS = window.localStorage;

const kToken   = (u) => `${NS}:token:${u}`;
const kUser    = (u) => `${NS}:user:${u}`;
const kLastAct = ()  => `${NS}:lastActiveUser`;

/** Lưu phiên cho 1 user */
function saveSessionFor(user, token) {
  if (!user?.username || !token) return;
  LS.setItem(kToken(user.username), token);
  LS.setItem(kUser(user.username), JSON.stringify(user));
  LS.setItem(kLastAct(), user.username);
}

/** Xoá phiên của 1 user */
function clearSessionFor(username) {
  if (!username) return;
  LS.removeItem(kToken(username));
  LS.removeItem(kUser(username));
  const cur = LS.getItem(kLastAct());
  if (cur === username) LS.removeItem(kLastAct());
}

/** Danh sách username đã đăng nhập */
function listSessions() {
  const arr = [];
  for (let i = 0; i < LS.length; i++) {
    const key = LS.key(i);
    if (key && key.startsWith(`${NS}:user:`)) {
      arr.push(key.split(":").pop());
    }
  }
  return arr.sort();
}

/* PHIÊN HIỆN TẠI */
function getUsernameFromQuery() {
  const u = new URLSearchParams(location.search).get("u");
  return u && u.trim() ? u.trim() : null;
}

function getCurrentUsername() {
  return getUsernameFromQuery() || LS.getItem(kLastAct()) || null;
}

function setActiveUser(username) {
  if (username) LS.setItem(kLastAct(), username);
}

/** Context phiên hiện tại */
function getCurrentContext() {
  const username = getCurrentUsername();
  if (!username) return { username: null, user: null, token: null };
  const userStr = LS.getItem(kUser(username));
  const token = LS.getItem(kToken(username));
  const user = userStr ? JSON.parse(userStr) : null;
  return { username, user, token };
}

/** Lấy token / user đang dùng */
function getToken() { return getCurrentContext().token; }
function getUser()  { return getCurrentContext().user; }

/** Logout phiên hiện tại */
function logoutCurrent() {
  const { username } = getCurrentContext();
  if (username) clearSessionFor(username);
  location.href = "../common/login.html";
}

/* FETCH HELPER (đính kèm Bearer) */
let _authRedirected = false;
async function apiFetch(path, options = {}) {
  path = path.replace(/\/{2,}/g, "/");
  const token = getToken();
  const headers = new Headers(options.headers || {});

  // Không set Content-Type khi body là FormData
  if (!headers.has("Content-Type") && options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 401) {
    if (!_authRedirected) {
      _authRedirected = true;
      alert("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.");
      logoutCurrent();
    }
    throw new Error("Unauthorized");
  }
  return res;
}

/* AUTH FLOW */
async function login(username, password) {
  try {
    const body = new URLSearchParams({ username, password });
    const res = await fetch(`${API_BASE}/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body
    });

    if (!res.ok) throw new Error(`Sai tài khoản hoặc mật khẩu (${res.status})`);

    const { access_token } = await res.json();

    const meRes = await fetch(`${API_BASE}/auth/users/me`, {
      headers: { Authorization: `Bearer ${access_token}` }
    });
    if (!meRes.ok) throw new Error("Không thể lấy thông tin người dùng.");
    const user = await meRes.json();

    saveSessionFor(user, access_token);

    const target = user.role === "admin"
      ? `../admin/admin.html?u=${encodeURIComponent(user.username)}`
      : `../student/student.html?u=${encodeURIComponent(user.username)}`;

    location.href = target;
  } catch (err) {
    alert("Đăng nhập thất bại: " + (err.message || err));
  }
}

/** Bảo vệ trang theo vai trò */
function requireAuth(allowedRoles = ["student", "admin"]) {
  const ctx = getCurrentContext();
  if (!ctx.token || !ctx.user || !allowedRoles.includes(ctx.user.role)) {
    location.href = "../common/login.html";
  }
}

/* GIỮ ?u= KHI ĐIỀU HƯỚNG */
function linkWithUser(href) {
  const u = getCurrentUsername();
  if (!u) return href;
  try {
    const url = new URL(href, location.href);
    url.searchParams.set("u", u);
    return url.pathname + "?" + url.searchParams.toString();
  } catch {
    const hasQ = href.includes("?");
    return href + (hasQ ? "&" : "?") + "u=" + encodeURIComponent(u);
  }
}

/** Gắn ?u= cho các link có data-keep-user */
function rewriteLinksKeepUser() {
  const u = getCurrentUsername();
  if (!u) return;
  document.querySelectorAll("a[data-keep-user]").forEach(a => {
    const orig = a.getAttribute("href");
    if (orig) a.setAttribute("href", linkWithUser(orig));
  });
}

document.addEventListener("DOMContentLoaded", () => {
  rewriteLinksKeepUser();
  const ctx = getCurrentContext();
  const elU = document.querySelector("[data-current-username]");
  const elR = document.querySelector("[data-current-role]");
  if (ctx.user) {
    if (elU) elU.textContent = ctx.user.username;
    if (elR) elR.textContent = ctx.user.role;
  }
});

/* API – USERS / AUTH */
async function apiMe() {
  const r = await apiFetch("/auth/users/me");
  if (!r.ok) return null;
  return r.json();
}

/* Helper URL ảnh dùng chung */
function resolveImg(url){
  if (!url) return null;
  return url.startsWith("http") ? url : `${API_BASE}${url}`;
}

/* API – REPORTS */
async function apiUploadImage(file) {
  const fd = new FormData();
  fd.append("file", file);
  const res = await apiFetch(`${REPORTS_PATH}/upload`, {
    method: "POST",
    body: fd,
  });
  if (!res.ok) {
    const t = await res.text().catch(()=> "");
    throw new Error(`Upload ảnh thất bại: ${res.status} ${t}`);
  }
  const { url } = await res.json();
  return url.startsWith("http") ? url : `${API_BASE}${url}`;
}

// Tạo báo cáo
async function apiCreateReport(payload) {
  const res = await apiFetch(REPORTS_PATH, {
    method: "POST",
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const t = await res.text().catch(()=> "");
    throw new Error(`Gửi sự cố thất bại: ${res.status} ${t}`);
  }
  return res.json();
}

// Danh sách sự cố của riêng tôi (mặc định mới nhất trước)
async function apiListReportsMine(order = "desc") {
  const res = await apiFetch(`${REPORTS_PATH}/mine?order=${encodeURIComponent(order)}`);
  if (!res.ok) {
    const t = await res.text().catch(()=> "");
    throw new Error(`Không tải được danh sách của bạn: ${res.status} ${t}`);
  }
  return res.json();
}

// (Admin) – Danh sách tất cả
async function apiListReportsAll(order = "desc") {
  const res = await apiFetch(`${REPORTS_PATH}?order=${encodeURIComponent(order)}`);
  if (!res.ok) {
    const t = await res.text().catch(()=> "");
    throw new Error(`Không tải được danh sách sự cố: ${res.status} ${t}`);
  }
  return res.json();
}

// (Chi tiết)
async function apiGetReport(reportId) {
  const res = await apiFetch(`${REPORTS_PATH}/${reportId}`);
  if (!res.ok) {
    const t = await res.text().catch(()=> "");
    throw new Error(`Không tải được sự cố #${reportId}: ${res.status} ${t}`);
  }
  return res.json();
}

// (Admin) – Cập nhật report (status / admin_reply)
async function apiUpdateReport(reportId, patch) {
  const res = await apiFetch(`${REPORTS_PATH}/${reportId}`, {
    method: "PATCH",
    body: JSON.stringify(patch)
  });
  if (!res.ok) {
    const t = await res.text().catch(()=> "");
    throw new Error(`Cập nhật sự cố #${reportId} thất bại: ${res.status} ${t}`);
  }
  return res.json();
}

// alias thuận tiện: trên SV gọi apiListReports() sẽ chính là mine
async function apiListReports() { return apiListReportsMine(); }

/* API – CHECKINS */

// Upload ảnh check-in/out
async function apiUploadCheckinImage(file) {
  const fd = new FormData();
  fd.append("file", file);
  const res = await apiFetch(CHECKINS_UPLOAD_PATH, {
    method: "POST",
    body: fd,
  });
  if (!res.ok) {
    const t = await res.text().catch(()=> "");
    throw new Error(`Upload ảnh check-in/out thất bại: ${res.status} ${t}`);
  }
  const { url } = await res.json();
  return url.startsWith("http") ? url : `${API_BASE}${url}`;
}

async function apiCreateCheckin(payload) {
  // Nếu truyền image_file (File), tự upload rồi gắn image_url
  if (payload && payload.image_file instanceof File) {
    const url = await apiUploadCheckinImage(payload.image_file);
    payload = { ...payload, image_url: url };
    delete payload.image_file;
  }

  const res = await apiFetch(CHECKINS_PATH, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const t = await res.text().catch(() => "");
    throw new Error(`Tạo yêu cầu checkin/checkout thất bại: ${res.status} ${t}`);
  }
  return res.json();
}

async function apiMyCheckins() {
  const res = await apiFetch(`${CHECKINS_PATH}/mine`);
  if (!res.ok) {
    const t = await res.text().catch(() => "");
    throw new Error(`Lấy lịch sử checkin/checkout thất bại: ${res.status} ${t}`);
  }
  return res.json();
}

async function apiListCheckinsAll() {
  const res = await apiFetch(CHECKINS_PATH);
  if (!res.ok) {
    const t = await res.text().catch(() => "");
    throw new Error(`Không tải được danh sách check-in/out: ${res.status} ${t}`);
  }
  return res.json();
}

async function apiUpdateCheckin(id, patch) {
  const res = await apiFetch(`${CHECKINS_PATH}/${id}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
  if (!res.ok) {
    const t = await res.text().catch(() => "");
    throw new Error(`Cập nhật check-in/out #${id} thất bại: ${res.status} ${t}`);
  }
  return res.json();
}

/* XUẤT RA GLOBAL */
window.ktxAuth = {
  login,
  logoutCurrent,
  requireAuth,
  apiFetch,
  getUser,
  getToken,
  listSessions,
  setActiveUser,
  getCurrentUsername,
  linkWithUser,
  apiMe,
  resolveImg,                 // 👈 export helper URL ảnh
  apiUploadImage,
  apiCreateReport,
  apiListReportsMine,
  apiListReportsAll,
  apiGetReport,
  apiUpdateReport,
  apiListReports,
  apiUploadCheckinImage,      // 👈 export upload ảnh check-in/out
  apiCreateCheckin,
  apiMyCheckins,
  apiListCheckinsAll,
  apiUpdateCheckin,
};

// ✅ Đảm bảo mọi trang truy cập được API_BASE đúng
window.ktxAuth.apiBase = API_BASE;
window.ktxAuth.baseURL = API_BASE;
