// static/app.js
let currentSection = null;
let sounds = [];
let sectionsCache = [];

// single global audio object the client controls
window.currentAudio = null;
let lastPlayId = 0;

function $(id) {
  return document.getElementById(id);
}

async function fetchSections() {
  const r = await fetch("/api/sections");
  const secs = await r.json();
  sectionsCache = secs;
  const container = $("sections");
  container.innerHTML = "";
  secs.forEach((s) => {
    const card = document.createElement("div");
    card.className = "section-card";
    const title = document.createElement("div");
    title.className = "title";
    title.innerText = s.name;
    const right = document.createElement("div");

    // toggle
    const label = document.createElement("label");
    label.className = "switch";
    const chk = document.createElement("input");
    chk.type = "checkbox";
    chk.checked = s.enabled === 1 || s.enabled === true;
    chk.onchange = () => toggleSection(s.id, chk.checked);
    const span = document.createElement("span");
    span.className = "slider";
    label.appendChild(chk);
    label.appendChild(span);

    card.onclick = (ev) => {
      if (ev.target.tagName.toLowerCase() === "input") return;
      selectSection(s.id, card);
    };

    right.appendChild(label);
    card.appendChild(title);
    card.appendChild(right);
    container.appendChild(card);
  });
  // select first section by default
  const first = container.querySelector(".section-card");
  if (first && currentSection === null) first.click();
}

async function toggleSection(sectionId, enabled) {
  await fetch("/api/set_section_enabled", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ section_id: sectionId, enabled: enabled }),
  });
  refreshActive();
}

async function loadSounds() {
  const r = await fetch("/api/sounds");
  sounds = await r.json();
}

async function selectSection(id, elem) {
  document
    .querySelectorAll(".section-card")
    .forEach((c) => c.classList.remove("active"));
  elem.classList.add("active");
  currentSection = id;
  await loadAndRenderSlots(id);
}

function timeNow() {
  const d = new Date();
  return d.toLocaleTimeString();
}

function markDirty(slotId) {
  const btn = document.querySelector(`#save-btn-${slotId}`);
  if (btn) btn.classList.add("unsaved");
}

async function loadAndRenderSlots(sectionId) {
  await loadSounds();
  const r = await fetch(`/api/slots/${sectionId}`);
  const slots = await r.json();
  const area = $("slots-area");
  let html = `<h3>${document.querySelector(".section-card.active")
    ? document.querySelector(".section-card.active .title").innerText
    : "Section"
    } — Slots</h3>`;
  html += `<div class="slots-wrap"><table class="slots-table"><thead><tr><th>#</th><th>Time</th><th>Sound</th><th>Enabled</th><th>Actions</th></tr></thead><tbody>`;
  slots.forEach((s) => {
    const timeVal = s.time || "";
    const soundOptions = sounds
      .map(
        (sound) =>
          `<option value="${sound.id}" ${sound.id === s.sound_id ? "selected" : ""
          }>${sound.name}</option>`
      )
      .join("");
    const filenameForAttr = s.filename ? encodeURIComponent(s.filename) : "";
    html += `<tr id="slot-row-${s.id}">
      <td style="width:58px">${s.slot_no}</td>
      <td style="width:160px"><input type="time" id="time-${s.id
      }" value="${timeVal}" step="60" onchange="markDirty(${s.id})"></td>
      <td style="width:240px"><select id="sound-${s.id}" onchange="markDirty(${s.id
      })">${soundOptions}</select></td>
      <td style="width:80px"><input type="checkbox" id="enabled-${s.id}" ${s.enabled ? "checked" : ""
      } onchange="markDirty(${s.id})"></td>
      <td class="table-actions">
        <button id="save-btn-${s.id}" class="save-btn" onclick="saveSlot(${s.id
      })">Save</button>
        <button onclick="playSlot(${s.id
      }, '${filenameForAttr}')" style="background:#28a745">Play</button>
      </td>
    </tr>`;
  });
  html += `</tbody></table></div>`;
  area.innerHTML = html;
}

async function saveSlot(slotId) {
  const timeVal = document.getElementById(`time-${slotId}`).value;
  const soundId = parseInt(document.getElementById(`sound-${slotId}`).value);
  const enabled = document.getElementById(`enabled-${slotId}`).checked;
  const sectionId = currentSection;
  if (timeVal && !/^([01]\d|2[0-3]):([0-5]\d)$/.test(timeVal)) {
    alert("Enter time in HH:MM 24-hour format");
    return;
  }
  const body = {
    id: slotId,
    time: timeVal,
    sound_id: soundId,
    enabled: enabled,
    section_id: sectionId,
  };
  await fetch("/api/update_slot", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const btn = document.querySelector(`#save-btn-${slotId}`);
  if (btn) btn.classList.remove("unsaved");
  const row = document.querySelector(`#slot-row-${slotId}`);
  if (row) {
    row.style.background = "#f9fff2";
    setTimeout(() => (row.style.background = ""), 500);
  }
  refreshActive();
}

// --- local audio controller (single global) ---
function playLocalUrl(url) {
  console.log("playLocalUrl: called");
  if (!url) return;
  try {
    // stop previous if exists
    if (window.currentAudio) {
      try {
        window.currentAudio.pause();
      } catch (e) { }
      try {
        window.currentAudio.currentTime = 0;
      } catch (e) { }
      window.currentAudio = null;
    }

    window.currentAudio = new Audio(url);
    window.currentAudio.play().catch((err) => {
      console.log("playLocalUrl: autoplay blocked or failed:", err);
    });

    window.currentAudio.onended = () => {
      try {
        window.currentAudio.currentTime = 0;
      } catch (e) { }
      window.currentAudio = null;
    };
  } catch (err) {
    console.error("playLocalUrl error:", err);
  }
}

async function playSlot(slotId, encodedFilename) {
  let filename = null;
  try {
    filename = encodedFilename ? decodeURIComponent(encodedFilename) : null;
  } catch (e) {
    filename = encodedFilename || null;
  }

  // Generate a new play ID
  const myPlayId = ++lastPlayId;
  console.log(`playSlot: filename=${filename}, playId=${myPlayId}`);

  // 1) Ask server for the URL to play
  try {
    const res = await fetch(`/api/play_slot/${slotId}`, { method: "POST" });
    const json = await res.json();

    // Check if we are still the active request
    if (myPlayId !== lastPlayId) {
      console.log(`playSlot: Aborting play for id=${myPlayId} because current is ${lastPlayId}`);
      return;
    }

    if (json.success && json.url) {
      // 2) Play locally
      playLocalUrl(json.url);
      $(
        "upload-status"
      ).innerText = `Playing ${json.url} — press Stop Sound to stop`;
    } else {
      // fallback: if server didn't return a url but filename was provided
      if (filename) {
        const url = `/sounds/${encodeURIComponent(filename)}`;
        playLocalUrl(url);
        $(
          "upload-status"
        ).innerText = `Playing ${filename} — press Stop Sound to stop`;
      } else {
        $("upload-status").innerText = "Play failed: no URL";
      }
    }
  } catch (err) {
    if (myPlayId !== lastPlayId) return; // ignore errors from stale requests

    console.error("playSlot error:", err);
    if (filename) {
      const url = `/sounds/${encodeURIComponent(filename)}`;
      playLocalUrl(url);
      $(
        "upload-status"
      ).innerText = `Playing ${filename} — press Stop Sound to stop`;
    } else {
      $("upload-status").innerText = "Play failed";
    }
  }
}

async function uploadSound() {
  const fileEl = document.getElementById("soundfile");
  if (!fileEl.files.length) return alert("Choose a file");
  const file = fileEl.files[0];
  const fd = new FormData();
  fd.append("file", file);
  const name = document.getElementById("soundname").value;
  if (name) fd.append("name", name);
  const res = await fetch("/api/upload_sound", { method: "POST", body: fd });
  const json = await res.json();
  if (json.success) {
    $("upload-status").innerText = "Uploaded: " + json.filename;
    await loadSounds();
    if (currentSection) loadAndRenderSlots(currentSection);
  } else {
    $("upload-status").innerText = "Upload failed";
  }
}

async function refreshActive() {
  const r = await fetch("/api/active_alarms");
  const items = await r.json();
  console.log("Active alarms", items);
  const target = $("upcoming");
  target.innerHTML = "";
  items.forEach((it) => {
    const s = it.slot;
    const el = document.createElement("div");
    el.style.padding = "6px 0";
    el.innerHTML = `<strong>${s.section_name} — slot ${s.slot_no}</strong> at ${s.time} (in ${it.minutes_from_now} min) — next: ${it.next_at}`;
    target.appendChild(el);
  });
}

async function stopSound() {
  console.log("Client STOP");

  // Invalidate any pending play requests
  lastPlayId++;

  // Stop browser audio
  if (window.currentAudio) {
    try {
      window.currentAudio.pause();
      window.currentAudio.currentTime = 0;
      // aggressively clear source to stop buffering/downloading
      window.currentAudio.src = "";
      window.currentAudio.load();
      console.log("Audio stopped hard");
    } catch (e) {
      console.error("Error stopping audio:", e);
    }
    window.currentAudio = null;
  } else {
    console.log("No audio to stop");
  }

  // Inform server (keeps server state consistent)
  try {
    await fetch("/api/stop_sound", { method: "POST" });
  } catch (e) {
    console.warn("stopSound: server call failed", e);
  }

  $("upload-status").innerText = "Stopped";
}

function startClock() {
  setInterval(() => {
    $("now").innerText = new Date().toLocaleTimeString();
  }, 1000);
}

async function start() {
  startClock();
  await fetchSections();
  await loadSounds();
  await refreshActive();
  setInterval(refreshActive, 30000);
}

window.onload = start;
window.playSlot = playSlot;
window.saveSlot = saveSlot;
window.markDirty = markDirty;
window.stopSound = stopSound;
window.uploadSound = uploadSound;
