const API = "http://127.0.0.1:8000";
let token = localStorage.getItem("token");

document.getElementById("signup").onclick = async () => {
  const u = uval(), p = pval();
  await fetch(`${API}/signup?username=${u}&password=${p}`, { method: "POST" });
  alert("회원가입 완료");
};

document.getElementById("login").onclick = async () => {
  const u = uval(), p = pval();
  const res = await fetch(`${API}/login?username=${u}&password=${p}`, { method: "POST" });
  const data = await res.json();
  token = data.token;
  localStorage.setItem("token", token);
  loadMemos();
};

document.getElementById("save").onclick = async () => {
  const text = document.getElementById("text").value;
  await fetch(`${API}/memo?text=${encodeURIComponent(text)}`, {
    method: "POST",
    headers: { "Authorization": token }
  });
  document.getElementById("text").value = "";
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
    li.innerText = `${m.text} (${m.created_at})`;
    ul.appendChild(li);
  }
}

function uval(){ return document.getElementById("u").value; }
function pval(){ return document.getElementById("p").value; }

if (token) loadMemos();
