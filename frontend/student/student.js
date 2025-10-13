/***** Student JS – render "Sự cố của tôi", xử lý Check-in/Check-out *****/

function statusToChip(status){
  if(status==='resolved') return ['Đã giải quyết','success','done'];
  if(status==='in_progress') return ['Đang xử lý','info','progress'];
  return ['Mở','danger','open'];
}

async function renderMyIncidents(){
  const wrap = document.querySelector('.mi-list');
  if(!wrap) return;
  try{
    const items = await apiMyReports();
    wrap.innerHTML = '';
    items.forEach(r=>{
      const [label, cls, data] = statusToChip(r.status);
      const article = document.createElement('article');
      article.className = 'ticket mini'; article.dataset.status = data;
      article.innerHTML = `
        <div class="ticket-main">
          <a class="ticket-title" href="#">${r.title}</a>
          <div class="ticket-meta">
            <span class="meta"><span class="material-symbols-outlined">schedule</span> ${new Date(r.created_at).toLocaleString()}</span>
            ${r.category ? `<span class="meta"><span class="material-symbols-outlined">sell</span> ${r.category}</span>` : ''}
          </div>
          ${r.admin_reply ? `<div class="muted" style="margin-top:6px">Phản hồi QL: ${r.admin_reply}</div>` : ''}
        </div>
        <div class="ticket-aside"><span class="chip ${cls}">${label}</span></div>
      `;
      wrap.appendChild(article);
    });
  }catch(e){ console.error(e); }
}

function initStudentHome(){
  // tabs filter
  document.querySelectorAll('.tab').forEach(t=>{
    t.addEventListener('click', ()=>{
      document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
      t.classList.add('active');
      const f=t.dataset.filter;
      document.querySelectorAll('.mi-list .ticket').forEach(row=>{
        row.style.display = (f==='all' || row.dataset.status===f) ? '' : 'none';
      });
    });
  });
  renderMyIncidents();
  setInterval(renderMyIncidents, 30000);
}

function initCheckinPage(){
  const f1 = document.getElementById('formCheckin');
  const f2 = document.getElementById('formCheckout');
  if(f1){
    f1.addEventListener('submit', async (e)=>{
      e.preventDefault();
      try{
        await apiCreateCheckin({
          type:'checkin',
          date: document.getElementById('ci-date').value,
          time: document.getElementById('ci-time').value,
          note: document.getElementById('ci-note').value
        });
        alert('Đã gửi yêu cầu Check-in'); f1.reset(); renderMyCheckins();
      }catch(err){ alert(err.message || 'Lỗi gửi yêu cầu'); }
    });
  }
  if(f2){
    f2.addEventListener('submit', async (e)=>{
      e.preventDefault();
      try{
        await apiCreateCheckin({
          type:'checkout',
          date: document.getElementById('co-date').value,
          time: document.getElementById('co-time').value,
          note: document.getElementById('co-note').value
        });
        alert('Đã gửi yêu cầu Check-out'); f2.reset(); renderMyCheckins();
      }catch(err){ alert(err.message || 'Lỗi gửi yêu cầu'); }
    });
  }
  renderMyCheckins();
  setInterval(renderMyCheckins, 30000);
}

async function renderMyCheckins(){
  const box = document.getElementById('myCheckins'); if(!box) return;
  box.innerHTML = '<div class="muted">Đang tải...</div>';
  try{
    const list = await apiMyCheckins();
    if(!list.length){ box.innerHTML = '<div class="muted">Chưa có yêu cầu nào.</div>'; return; }
    box.innerHTML = '';
    list.forEach(it=>{
      const chip = it.status==='approved' ? ['Đã duyệt','success'] : (it.status==='rejected' ? ['Từ chối','danger'] : ['Chờ duyệt','info']);
      const div = document.createElement('div');
      div.style.cssText = "border:1px solid #e5e7eb;border-radius:12px;padding:12px;margin:10px 0;background:#fff";
      div.innerHTML = `
        <div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap">
          <div><b>${it.type==='checkin'?'Check-in':'Check-out'}</b> – ${it.date} ${it.time?it.time:''}</div>
          <div><span class="chip ${chip[1]}">${chip[0]}</span></div>
        </div>
        ${it.note ? `<div class="muted" style="margin-top:6px">${it.note}</div>`:''}
        ${it.admin_reply ? `<div style="margin-top:6px"><b>Phản hồi QL:</b> ${it.admin_reply}</div>`:''}
      `;
      box.appendChild(div);
    });
  }catch(e){ box.innerHTML = '<div class="muted">Không tải được dữ liệu</div>'; }
}
