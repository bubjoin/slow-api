const API = "";
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
  if (!token) {
    alert("회원가입 후 이용하세요!");
  }
  loadMemos();
};

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

if (token) loadMemos();
