/* ====== Admin – Quản lý tài khoản ====== */

const API = window.API_BASE || "http://localhost:8000";
const token = localStorage.getItem("token");

// ---- API wrappers ----
async function apiAdminListUsers() {
  const res = await fetch(`${API}/users`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!res.ok) throw new Error("Load users failed");
  return res.json(); // [{id, username, full_name, email, role, faculty, room, bed, address}]
}

async function apiAdminUpdateUser(id, payload) {
  const res = await fetch(`${API}/users/${id}`, {
    method: "PATCH", // 👈 quan trọng: PATCH + /users/{id}
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    let msg = "";
    try { msg = (await res.json()).detail || res.statusText; } catch {}
    throw new Error(`Update failed: ${res.status} ${msg}`);
  }
  return res.json();
}

async function apiAdminCreateUser(payload) {
  const res = await fetch(`${API}/users`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    let msg = "";
    try { msg = (await res.json()).detail || res.statusText; } catch {}
    throw new Error(`Create failed: ${res.status} ${msg}`);
  }
  return res.json();
}

async function apiAdminDeleteUser(id) {
  const res = await fetch(`${API}/users/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!res.ok) {
    let msg = "";
    try { msg = (await res.json()).detail || res.statusText; } catch {}
    throw new Error(`Delete failed: ${res.status} ${msg}`);
  }
  return res.json();
}

// ---- Render bảng người dùng ----
// Yêu cầu HTML:
//  - <tbody id="tbl-users-body"></tbody>
//  - Nút thêm mới:  #btn-add-user
//  - Modal edit có form #edit-form (data-id gán user id khi mở)
//  - Các input trong modal dùng data-field="full_name|email|phone|faculty|room|bed|address|role|username"
async function renderAdminUsers() {
  const tbody = document.getElementById("tbl-users-body");
  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="8">Đang tải...</td></tr>`;

  try {
    const rows = await apiAdminListUsers();
    tbody.innerHTML = "";
    for (const u of rows) {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${u.id}</td>
        <td>${u.username || "-"}</td>
        <td>${u.full_name || "-"}</td>
        <td>${u.email || "-"}</td>
        <td>${u.faculty || "-"}</td>
        <td>${u.room || "-"}</td>
        <td>${u.bed || "-"}</td>
        <td>${u.address || "-"}</td>
        <td>${u.role}</td>
        <td>
          <button class="btn ghost" data-edit="${u.id}">Sửa</button>
          <button class="btn danger" data-del="${u.id}">Xóa</button>
        </td>
      `;
      tbody.appendChild(tr);
    }

    // nút sửa
    tbody.querySelectorAll("[data-edit]").forEach(btn => {
      btn.addEventListener("click", () => openEditModal(rows.find(x => x.id === Number(btn.dataset.edit))));
    });
    // nút xóa
    tbody.querySelectorAll("[data-del]").forEach(btn => {
      btn.addEventListener("click", async () => {
        if (!confirm("Xóa tài khoản này?")) return;
        await apiAdminDeleteUser(Number(btn.dataset.del));
        await renderAdminUsers();
      });
    });

  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="8">Lỗi tải danh sách</td></tr>`;
    alert(e.message);
  }
}

// ---- Mở modal & fill dữ liệu ----
function setField(idOrSelector, value) {
  const el = typeof idOrSelector === "string"
    ? document.querySelector(idOrSelector)
    : idOrSelector;
  if (el) el.value = value ?? "";
}

function openEditModal(userRow) {
  const form = document.getElementById("edit-form");
  if (!form) return;
  form.dataset.id = userRow.id;

  setField('[data-field="username"]',   userRow.username);
  setField('[data-field="full_name"]',  userRow.full_name);
  setField('[data-field="email"]',      userRow.email);
  setField('[data-field="phone"]',      userRow.phone);
  setField('[data-field="faculty"]',    userRow.faculty);
  setField('[data-field="room"]',       userRow.room);
  setField('[data-field="bed"]',        userRow.bed);      // 👈 từ profile
  setField('[data-field="address"]',    userRow.address);  // 👈 từ profile
  setField('[data-field="role"]',       userRow.role);

  // hiển thị modal (tùy bạn đang dùng cách nào)
  document.getElementById("modal-edit")?.classList.add("open");
}

// ---- Lưu trong modal ----
async function handleSaveUser(e) {
  e?.preventDefault?.();
  const form = document.getElementById("edit-form");
  if (!form) return;
  const id = Number(form.dataset.id);

  const payload = {
    // username cho phép đổi (nếu bạn muốn giữ nguyên, bỏ dòng này)
    username:  document.querySelector('[data-field="username"]')?.value.trim() || null,
    full_name: document.querySelector('[data-field="full_name"]')?.value.trim() || null,
    email:     document.querySelector('[data-field="email"]')?.value.trim() || null,
    phone:     document.querySelector('[data-field="phone"]')?.value.trim() || null,
    faculty:   document.querySelector('[data-field="faculty"]')?.value.trim() || null,
    room:      document.querySelector('[data-field="room"]')?.value.trim() || null,
    bed:       document.querySelector('[data-field="bed"]')?.value.trim() || null,     // 👈 PROFILE
    address:   document.querySelector('[data-field="address"]')?.value.trim() || null, // 👈 PROFILE
    role:      document.querySelector('[data-field="role"]')?.value || null,
  };

  try {
    await apiAdminUpdateUser(id, payload); // 👈 PATCH /users/{id}
    document.getElementById("modal-edit")?.classList.remove("open");
    await renderAdminUsers();
  } catch (e) {
    alert(e.message);
  }
}

// ---- Thêm mới (nếu có form riêng) ----
async function handleCreateUser(e) {
  e?.preventDefault?.();
  const payload = {
    username:  document.querySelector('[data-new="username"]')?.value.trim(),
    password:  document.querySelector('[data-new="password"]')?.value,
    full_name: document.querySelector('[data-new="full_name"]')?.value.trim() || null,
    email:     document.querySelector('[data-new="email"]')?.value.trim() || null,
    phone:     document.querySelector('[data-new="phone"]')?.value.trim() || null,
    faculty:   document.querySelector('[data-new="faculty"]')?.value.trim() || null,
    room:      document.querySelector('[data-new="room"]')?.value.trim() || null,
    bed:       document.querySelector('[data-new="bed"]')?.value.trim() || null,       // 👈 PROFILE
    address:   document.querySelector('[data-new="address"]')?.value.trim() || null,   // 👈 PROFILE
    role:      document.querySelector('[data-new="role"]')?.value || "student",
  };
  try {
    await apiAdminCreateUser(payload); // POST /users
    await renderAdminUsers();
  } catch (e) {
    alert(e.message);
  }
}

// ---- Khởi tạo trang Users ----
// Gọi hàm này trong trang users.html sau khi DOM ready
function initAdminUsersPage() {
  renderAdminUsers();
  document.getElementById("edit-form")?.addEventListener("submit", handleSaveUser);
  document.getElementById("btn-save-user")?.addEventListener("click", handleSaveUser);
  document.getElementById("btn-add-user")?.addEventListener("click", handleCreateUser);
}
window.initAdminUsersPage = initAdminUsersPage;
