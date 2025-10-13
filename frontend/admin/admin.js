/***** Admin JS – render danh sách báo cáo & checkin-out, cập nhật trạng thái *****/

function reportStatusChip(s){
  if(s==='resolved') return ['Đã giải quyết','success'];
  if(s==='in_progress') return ['Đang xử lý','info'];
  return ['Mở','danger'];
}
function checkinStatusChip(s){
  if(s==='approved') return ['Đã duyệt','success'];
  if(s==='rejected') return ['Từ chối','danger'];
  return ['Chờ duyệt','info'];
}

async function renderAdminReports(){
  const wrap = document.getElementById('admin-report-list'); if(!wrap) return;
  wrap.innerHTML = 'Đang tải...';
  try{
    const list = await apiAdminListReports();
    wrap.innerHTML = '';
    list.forEach(r=>{
      const [label, cls] = reportStatusChip(r.status);
      const item = document.createElement('div');
      item.className = 'card'; item.style.margin='10px 0';
      item.innerHTML = `
        <div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap">
          <div><b>${r.title}</b><div class="muted">${new Date(r.created_at).toLocaleString()}</div></div>
          <div><span class="chip ${cls}">${label}</span></div>
        </div>
        ${r.category?`<div class="muted" style="margin-top:6px">Danh mục: ${r.category} – Ưu tiên: ${r.priority||'normal'}</div>`:''}
        ${r.description?`<div style="margin-top:6px">${r.description}</div>`:''}
        <div style="margin-top:8px">
          <label>Phản hồi:</label>
          <textarea rows="2" data-reply style="width:100%;border:1px solid #e5e7eb;border-radius:10px;padding:8px">${r.admin_reply||''}</textarea>
        </div>
        <div style="display:flex;gap:8px;margin-top:8px">
          <button class="btn ghost" data-action="open">Mở</button>
          <button class="btn ghost" data-action="in_progress">Đang xử lý</button>
          <button class="btn primary" data-action="resolved">Đã giải quyết & Lưu phản hồi</button>
        </div>
      `;
      item.querySelectorAll('button').forEach(btn=>{
        btn.addEventListener('click', async ()=>{
          const status = btn.getAttribute('data-action');
          const reply = item.querySelector('textarea[data-reply]').value;
          await apiAdminUpdateReport(r.id, { status, admin_reply: reply });
          await renderAdminReports();
        });
      });
      wrap.appendChild(item);
    });
  }catch(e){ wrap.innerHTML = 'Không tải được dữ liệu'; }
}

async function renderAdminCheckins(){
  const wrap = document.getElementById('admin-checkin-list'); if(!wrap) return;
  wrap.innerHTML = 'Đang tải...';
  try{
    const list = await apiAdminListCheckins();
    wrap.innerHTML = '';
    list.forEach(it=>{
      const [label, cls] = checkinStatusChip(it.status);
      const row = document.createElement('div');
      row.className = 'card'; row.style.margin='10px 0';
      row.innerHTML = `
        <div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap">
          <div><b>${it.type==='checkin'?'Check-in':'Check-out'}</b> – ${it.date} ${it.time?it.time:''}</div>
          <div><span class="chip ${cls}">${label}</span></div>
        </div>
        ${it.note?`<div style="margin-top:6px">${it.note}</div>`:''}
        <div style="margin-top:8px">
          <label>Phản hồi:</label>
          <textarea rows="2" data-reply style="width:100%;border:1px solid #e5e7eb;border-radius:10px;padding:8px">${it.admin_reply||''}</textarea>
        </div>
        <div style="display:flex;gap:8px;margin-top:8px">
          <button class="btn ghost" data-action="pending">Đặt về Chờ duyệt</button>
          <button class="btn primary" data-action="approved">Duyệt</button>
          <button class="btn" data-action="rejected">Từ chối</button>
        </div>
      `;
      row.querySelectorAll('button').forEach(btn=>{
        btn.addEventListener('click', async ()=>{
          const status = btn.getAttribute('data-action');
          const reply = row.querySelector('textarea[data-reply]').value;
          await apiAdminUpdateCheckin(it.id, { status, admin_reply: reply });
          await renderAdminCheckins();
        });
      });
      wrap.appendChild(row);
    });
  }catch(e){ wrap.innerHTML = 'Không tải được dữ liệu'; }
}

function initAdminDashboard(){
  renderAdminReports(); renderAdminCheckins();
  setInterval(()=>{renderAdminReports();renderAdminCheckins();},30000);
}

window.initAdminDashboard = initAdminDashboard;
