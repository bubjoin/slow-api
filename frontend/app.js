const API = "";
let token = localStorage.getItem("token");
let currentProjectId = null; // Day 7 핵심

let socket = null;

// ===== request_id (day 14) =====
function generateRequestId() {
  return crypto.randomUUID();
}

// ===== 로그인 / 회원가입 =====
document.getElementById("signup").onclick = async () => {
  const u = uval(), p = pval();
  await fetch(`/signup?username=${u}&password=${p}`, { method: "POST" });
  alert("회원가입 완료");
};

document.getElementById("login").onclick = async () => {
  const u = uval(), p = pval();
  const res = await fetch(`/login?username=${u}&password=${p}`, { method: "POST" });
  const data = await res.json();
  token = data.token;
  localStorage.setItem("token", token);
  loadProjects();
  loadMemos();
};

// ===== 프로젝트 =====
document.getElementById("create-project").onclick = async () => {
  const name = document.getElementById("project-name").value;

  await fetch(`/projects?name=${encodeURIComponent(name)}`, {
    method: "POST",
    headers: { "Authorization": token }
  });

  loadProjects();
};

async function loadProjects() {
  if (!token) return;

  const res = await fetch("/projects", {
    headers: { "Authorization": token }
  });
  const projects = await res.json();

  const ul = document.getElementById("project-list");
  ul.innerHTML = "";

  for (const p of projects) {
    const li = document.createElement("li");
    li.innerText = p.name;
    li.onclick = () => {
      currentProjectId = p.id;
      connectWebSocket(); // Day 8 추가
      loadEvents();
      loadMembers();
    };
    ul.appendChild(li);
  }
}

// ===== 프로젝트 일정 =====
document.getElementById("add-event").onclick = async () => {
  if (!currentProjectId) {
    alert("프로젝트를 먼저 선택하세요");
    return;
  }

  const title = document.getElementById("event-title").value;
  const date = document.getElementById("event-date").value;

  const requestId = generateRequestId();

  await fetch(
    `/projects/${currentProjectId}/events` +
    `?title=${encodeURIComponent(title)}` +
    `&date=${date}` +
    `&request_id=${requestId}`,
    {
      method: "POST",
      headers: { "Authorization": token }
    }
  );

  await fetch(
    `/projects/${currentProjectId}/events` +
    `?title=${encodeURIComponent(title)}` +
    `&date=${date}` +
    `&request_id=${requestId}`,
    {
      method: "POST",
      headers: { "Authorization": token }
    }
  );

  loadEvents();
};

// ===== 프로젝트 멤버 =====
document.getElementById("add-member").onclick = async () => {
  if (!currentProjectId) {
    alert("프로젝트를 먼저 선택하세요");
    return;
  }

  const user = document.getElementById("member-user").value;

  await fetch(
    `/projects/${currentProjectId}/members?target_user=${encodeURIComponent(user)}`,
    {
      method: "POST",
      headers: { "Authorization": token }
    }
  );

  alert("멤버 추가 완료");
};

// ===== 멤버스 로드 =====
async function loadMembers() {
  if (!token || !currentProjectId) return;

  const res = await fetch(
    `/projects/${currentProjectId}/members`,
    { headers: { "Authorization": token } }
  );
  const members = await res.json();

  const ul = document.getElementById("member-list");
  ul.innerHTML = "";

  for (const m of members) {
    const li = document.createElement("li");
    li.innerText = `${m.user} (${m.role})`;
    ul.appendChild(li);
  }
}

// ===== 이벤트 로드 =====
async function loadEvents() {
  if (!token || !currentProjectId) return;

  const res = await fetch(`/projects/${currentProjectId}/events`, {
    headers: { "Authorization": token }
  });
  const events = await res.json();

  const ul = document.getElementById("event-list");
  ul.innerHTML = "";

  for (const e of events) {
    const li = document.createElement("li");
    li.innerText = `${e.date} - ${e.title} `;
    li.dataset.version = e.version;
  
    const edit = document.createElement("button");
    edit.innerText = "Edit";
    edit.onclick = async () => {
      const newTitle = prompt("New title", e.title);
      const newDate = prompt("New date (YYYY-MM-DD)", e.date);
      if (!newTitle || !newDate) return;
  
      const res = await fetch(
        `/projects/${currentProjectId}/events/${e.id}?title=${encodeURIComponent(newTitle)}&date=${newDate}&version=${e.version}`,
        {
          method: "PUT",
          headers: { "Authorization": token }
        }
      );

      if (res.status === 409) {
        alert("다른 사용자가 먼저 수정했습니다. 새로고침합니다.");
        loadEvents();
        return;
      }

      loadEvents();
    };
  
    const del = document.createElement("button");
    del.innerText = "Delete";
    del.onclick = async () => {
      await fetch(
        `/projects/${currentProjectId}/events/${e.id}`,
        {
          method: "DELETE",
          headers: { "Authorization": token }
        }
      );
      loadEvents();
    };
  
    li.appendChild(edit);
    li.appendChild(del);
    ul.appendChild(li);
  }
}

// ===== WebSocket 연결함수 =====
function connectWebSocket() {
  if (socket) socket.close();

  socket = new WebSocket(
    `ws://${location.host}/ws/projects/${currentProjectId}?token=${token}`
  );

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (
      data.type === "event_created" ||
      data.type === "event_updated" ||
      data.type === "event_deleted"
    ) {
      loadEvents();
    }
  };
}

// ===== 메모 =====
document.getElementById("save").onclick = async () => {
  const text = document.getElementById("text").value;
  await fetch(`${API}/memo?text=${encodeURIComponent(text)}`, {
    method: "POST",
    headers: { "Authorization": token }
  });
  document.getElementById("text").value = "";
  if (!token) {
    alert("로그인 후 이용하세요!");
  }
  loadMemos();
};

async function loadMemos() {
  if (!token) return;
  const res = await fetch(`${API}/memo`, {
    headers: { "Authorization": token }
  });
  const memos = await res.json();
  const ul = document.getElementById("list");
  ul.innerHTML = "";
  for (const m of memos) {
    const li = document.createElement("li");
    li.innerText = m.text + " ";

    const edit = document.createElement("button");
    edit.innerText = "수정";
    edit.onclick = async () => {
      const newText = prompt("수정할 내용", m.text);
      if (!newText) return;
      await fetch(`${API}/memo/${m.id}?text=${encodeURIComponent(newText)}`, {
        method: "PUT",
        headers: { "Authorization": token }
      });
      loadMemos();
    };

    const del = document.createElement("button");
    del.innerText = "삭제";
    del.onclick = async () => {
      await fetch(`${API}/memo/${m.id}`, {
        method: "DELETE",
        headers: { "Authorization": token }
      });
      loadMemos();
    };

    li.appendChild(edit);
    li.appendChild(del);
    ul.appendChild(li);
  }
}

function uval(){ return document.getElementById("u").value; }
function pval(){ return document.getElementById("p").value; }

if (token) {
  loadProjects();
  loadMemos();
}
