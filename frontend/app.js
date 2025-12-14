const API = "http://127.0.0.1:8000";

document.getElementById("save").onclick = async () => {
    const text = document.getElementById("text").value;

    await fetch(`${API}/memo?text=${encodeURIComponent(text)}`, {
        method: "POST"
    });

    document.getElementById("text").value="";
    loadMemos();
};

async function loadMemos() {
    const res = await fetch(`${API}/memo`);
    const memos = await res.json();

    const ul = document.getElementById("list");
    ul.innerHTML="";

    for (const m of memos) {
        const li = document.createElement("li");
        li.innerText = `${m.text} (${m.created_at})`;
        ul.appendChild(li);
    }
}

loadMemos();
