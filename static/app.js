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

function togglePasswordVisibility(inputId, iconId) {
  const input = $(inputId);
  const icon = $(iconId);
  if (input.type === "password") {
    input.type = "text";
    icon.innerText = "Hide";
  } else {
    input.type = "password";
    icon.innerText = "👁️";
  }
}

function toggleCollapse(containerId) {
  const container = $(containerId);
  const content = container.querySelector(".collapsible-content");
  const isCollapsed = content.classList.contains("collapsed");

  if (isCollapsed) {
    content.classList.remove("collapsed");
    container.classList.remove("collapsed-container");
  } else {
    content.classList.add("collapsed");
    container.classList.add("collapsed-container");
  }
}

async function fetchSections() {
  try {
    const r = await fetch("/api/sections");
    if (!r.ok) throw new Error(`HTTP error! status: ${r.status}`);
    const secs = await r.json();
    sectionsCache = secs;
    const container = $("sections");
    container.innerHTML = "";
    if (secs.length === 0) {
      container.innerHTML = "<div style='color:red; padding:20px;'>No sections found in database. Please check logs.</div>";
    }
    secs.forEach((s) => {
      const card = document.createElement("div");
      card.className = "section-card";

      const titleWrap = document.createElement("div");
      titleWrap.className = "section-title-wrap";

      const title = document.createElement("div");
      title.className = "title";
      title.innerText = s.name;

      const editBtn = document.createElement("span");
      editBtn.className = "edit-section-btn";
      editBtn.innerHTML = "✏️";
      editBtn.title = "Rename Section";
      editBtn.onclick = (ev) => {
        ev.stopPropagation();
        openRenameModal(s.id, s.name);
      };

      const daysList = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
      const isDaySection = daysList.includes(s.name);

      titleWrap.appendChild(title);
      if (!isDaySection) {
        titleWrap.appendChild(editBtn);
      }

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
        if (ev.target.tagName.toLowerCase() === "input" || ev.target.classList.contains("edit-section-btn")) return;
        selectSection(s.id, card);
      };

      right.appendChild(label);
      card.appendChild(titleWrap);
      card.appendChild(right);
      container.appendChild(card);
    });
    // select first section by default
    const first = container.querySelector(".section-card");
    if (first && currentSection === null) first.click();
  } catch (err) {
    console.error("fetchSections Error:", err);
    $("sections").innerHTML = `<div style='color:red; padding:20px;'>Error loading sections: ${err.message}</div>`;
  }
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

function formatTime12(time24) {
  if (!time24) return "";
  const [h, m] = time24.split(":");
  let hours = parseInt(h);
  const minutes = m;
  const ampm = hours >= 12 ? "PM" : "AM";
  hours = hours % 12;
  hours = hours ? hours : 12; // the hour '0' should be '12'
  return `${hours}:${minutes} ${ampm}`;
}

function timeNow() {
  const d = new Date();
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true });
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
  const contentArea = area.querySelector(".collapsible-content");

  // Update header text if needed (the header stays fixed now)
  const header = area.querySelector(".collapsible-header");
  const sectionName = document.querySelector(".section-card.active")
    ? document.querySelector(".section-card.active .title").innerText
    : "Section";
  header.firstChild.textContent = `${sectionName} — Slots `;

  let html = `<div class="slots-wrap"><table class="slots-table"><thead><tr><th>#</th><th>Time</th><th>Sound</th><th>Enabled</th><th>Actions</th></tr></thead><tbody>`;
  slots.forEach((s) => {
    const timeVal = s.time || "09:00";
    const [h24, m] = timeVal.split(":");
    let h12 = parseInt(h24);
    const period = h12 >= 12 ? "PM" : "AM";
    h12 = h12 % 12 || 12;
    const h12Str = h12.toString();

    // Hour options 1-12
    let hourOptions = "";
    for (let i = 1; i <= 12; i++) {
      hourOptions += `<option value="${i}" ${i === h12 ? "selected" : ""}>${i}</option>`;
    }

    // Minute options 00-59
    let minOptions = "";
    for (let i = 0; i < 60; i++) {
      const val = i.toString().padStart(2, '0');
      minOptions += `<option value="${val}" ${val === m ? "selected" : ""}>${val}</option>`;
    }

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
      <td style="width:220px" class="time-picker-cell">
        <select id="hour-${s.id}" onchange="markDirty(${s.id})">${hourOptions}</select> :
        <select id="min-${s.id}" onchange="markDirty(${s.id})">${minOptions}</select>
        <select id="ampm-${s.id}" onchange="markDirty(${s.id})">
            <option value="AM" ${period === "AM" ? "selected" : ""}>AM</option>
            <option value="PM" ${period === "PM" ? "selected" : ""}>PM</option>
        </select>
      </td>
      <td style="width:240px"><select id="sound-${s.id}" onchange="markDirty(${s.id
      })">${soundOptions}</select></td>
      <td style="width:80px"><input type="checkbox" id="enabled-${s.id}" ${s.enabled ? "checked" : ""
      } onchange="markDirty(${s.id})"></td>
      <td class="table-actions">
        <button id="save-btn-${s.id}" class="save-btn" onclick="saveSlot(${s.id
      })">Save</button>
       
      </td>
    </tr>`;
  });
  html += `</tbody></table></div>`;
  contentArea.innerHTML = html;
}

async function saveSlot(slotId) {
  const h = parseInt(document.getElementById(`hour-${slotId}`).value);
  const m = document.getElementById(`min-${slotId}`).value;
  const period = document.getElementById(`ampm-${slotId}`).value;

  let h24 = h;
  if (period === "PM" && h < 12) h24 += 12;
  if (period === "AM" && h === 12) h24 = 0;

  const timeVal = `${h24.toString().padStart(2, '0')}:${m}`;

  const soundId = parseInt(document.getElementById(`sound-${slotId}`).value);
  const enabled = document.getElementById(`enabled-${slotId}`).checked;
  const sectionId = currentSection;

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
  const nameEl = document.getElementById("soundname");
  const name = nameEl ? nameEl.value : "";
  if (name) fd.append("name", name);
  const res = await fetch("/api/upload_sound", { method: "POST", body: fd });
  const json = await res.json();
  if (json.success) {
    $("upload-status").innerText = "Uploaded: " + json.filename;
    $("upload-status").style.color = "lightgreen";
    await loadSounds();
    if (currentSection) loadAndRenderSlots(currentSection);
  } else {
    $("upload-status").innerText = "Upload failed: " + (json.error || "Unknown error");
    $("upload-status").style.color = "red";
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
    el.innerHTML = `<strong>${s.section_name} — slot ${s.slot_no}</strong> at ${formatTime12(s.time)} (in ${it.minutes_from_now} min) — next: ${it.next_at}`;
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
    $("now").innerText = timeNow();
  }, 1000);
}

// License related
async function checkLicense() {
  try {
    const res = await fetch("/api/license_status");
    const json = await res.json();

    // Expiry text
    if (json.expiry_date) {
      const expiryText = `(License expires: ${json.expiry_date})`;
      if ($("display-expiry")) $("display-expiry").innerText = expiryText;
    }

    // Banner logic
    const banner = document.getElementById("license-banner");
    if (json.status === "warning") {
      banner.style.display = "block";
      document.getElementById("days-left").innerText = json.days_left;
    } else {
      banner.style.display = "none";
    }

    // Overlay logic
    const overlay = document.getElementById("license-overlay");
    if (json.status === "expired") {
      overlay.style.display = "flex";
      // Ensure we are on Step 1 when it first appears
      if (document.getElementById("renew-step-1").style.display === "none" &&
        document.getElementById("renew-step-2").style.display === "none") {
        document.getElementById("renew-step-1").style.display = "block";
        document.getElementById("renew-step-2").style.display = "none";
        document.getElementById("renew-msg").innerText = "";
      }
      // Auto-stop any playing sound
      stopSound();
    } else {
      overlay.style.display = "none";
    }
  } catch (e) {
    console.warn("License check failed", e);
  }
}

// School Info
async function fetchSchoolInfo() {
  try {
    const r = await fetch("/api/school_info");
    const json = await r.json();
    if (json.school_name) {
      $("display-name").innerText = json.school_name;
    }
    if (json.school_logo) $("display-logo").src = json.school_logo;

  } catch (e) {
    console.warn("fetchSchoolInfo failed", e);
  }
}

// Admin Settings
let adminSettingsPassword = null;

function openAdminSettings() {
  $("admin-settings-modal").style.display = "flex";
  $("admin-settings-auth").style.display = "block";
  $("admin-settings-form").style.display = "none";
  $("admin-settings-pass").value = "";
  $("admin-settings-msg").innerText = "";
  adminSettingsPassword = null;
}

async function verifyAdminSettings() {
  const pwd = $("admin-settings-pass").value;
  const msg = $("admin-settings-msg");
  msg.innerText = "Verifying...";
  try {
    const res = await fetch("/api/verify_admin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: pwd })
    });
    const json = await res.json();
    if (json.success) {
      adminSettingsPassword = pwd;
      $("admin-settings-auth").style.display = "none";
      $("admin-settings-form").style.display = "block";
      msg.innerText = "";

      // Fetch current info to pre-fill
      const infoRes = await fetch("/api/school_info");
      const info = await infoRes.json();

      $("edit-school-name").value = info.school_name || "";
      $("edit-auto-start").checked = info.auto_start === "1";

      // Fetch Device info for pairing
      try {
        const dRes = await fetch("/api/device_info");
        const dJson = await dRes.json();
        if (dJson.device_id) {
          $("admin-device-id").value = dJson.device_id;
          $("admin-device-qr").src = "/api/device_qr?v=" + new Date().getTime(); // cache bust
        }
      } catch (de) {
        console.warn("Could not fetch device info", de);
      }
    } else {
      msg.innerText = json.error || "Verification failed";
      msg.style.color = "red";
    }
  } catch (e) {
    msg.innerText = "Error: " + e;
    msg.style.color = "red";
  }
}

let audioSettingsPassword = null;

function openAudioSettingsModal() {
  $("audio-settings-modal").style.display = "flex";
  $("audio-settings-auth").style.display = "block";
  $("audio-settings-form").style.display = "none";
  $("audio-settings-pass").value = "";
  $("audio-settings-auth-msg").innerText = "";
  audioSettingsPassword = null;
}

async function verifyAudioSettings() {
  const pwd = $("audio-settings-pass").value;
  const msg = $("audio-settings-auth-msg");
  msg.innerText = "Verifying...";
  try {
    const res = await fetch("/api/verify_admin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: pwd })
    });
    const json = await res.json();
    if (json.success) {
      audioSettingsPassword = pwd;
      $("audio-settings-auth").style.display = "none";
      $("audio-settings-form").style.display = "block";
      msg.innerText = "";
      await loadAudioSettingsDevices();
    } else {
      msg.innerText = json.error || "Verification failed";
      msg.style.color = "red";
    }
  } catch (e) {
    msg.innerText = "Error: " + e;
    msg.style.color = "red";
  }
}

async function loadAudioSettingsDevices() {
  const msg = $("audio-settings-msg");
  msg.innerText = "Loading devices...";
  msg.style.color = "white";

  try {
    const infoRes = await fetch("/api/school_info");
    const info = await infoRes.json();

    const deviceRes = await fetch("/api/audio_devices");
    const deviceJson = await deviceRes.json();

    if (deviceJson.success) {
      const bellSelect = $("audio-settings-bell-dev");
      const sysSelect = $("audio-settings-system-dev");

      const optionsHtml = '<option value="Default">Default System Output</option>' +
        deviceJson.devices.map(dev => `<option value="${dev}">${dev}</option>`).join("");

      bellSelect.innerHTML = optionsHtml;
      sysSelect.innerHTML = optionsHtml;

      bellSelect.value = info.audio_device || "Default";
      sysSelect.value = info.system_audio_dev || "Default";
      msg.innerText = "";
    }
  } catch (e) {
    msg.innerText = "Error loading settings: " + e.message;
    msg.style.color = "red";
  }
}

function closeAudioSettingsModal() {
  $("audio-settings-modal").style.display = "none";
}

async function saveAudioSettings() {
  const bellDev = $("audio-settings-bell-dev").value;
  const sysDev = $("audio-settings-system-dev").value;
  const msg = $("audio-settings-msg");

  msg.innerText = "Saving...";
  msg.style.color = "white";

  try {
    // 1. Update Bell Device
    await fetch("/api/set_audio_device", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: audioSettingsPassword, device: bellDev })
    });

    // 2. Update System Audio Isolation
    await fetch("/api/set_system_audio", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: audioSettingsPassword, device: sysDev })
    });

    msg.innerText = "Audio settings saved!";
    msg.style.color = "lightgreen";
    setTimeout(() => closeAudioSettingsModal(), 1000);
  } catch (e) {
    msg.innerText = "Error saving: " + e.message;
    msg.style.color = "red";
  }
}

async function saveAdminSettings() {
  const name = $("edit-school-name").value;
  const logoFile = $("edit-school-logo").files[0];
  const msg = $("admin-settings-msg");

  msg.innerText = "Saving...";
  msg.style.color = "white";

  try {
    // 1. Upload logo if selected
    if (logoFile) {
      const fd = new FormData();
      fd.append("file", logoFile);
      fd.append("password", adminSettingsPassword);
      const logoRes = await fetch("/api/upload_logo", { method: "POST", body: fd });
      const logoJson = await logoRes.json();
      if (!logoJson.success) throw new Error(logoJson.error || "Logo upload failed");
    }

    // 2. Update Metadata
    const res = await fetch("/api/update_school_info", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        password: adminSettingsPassword,
        school_name: name,
        auto_start: $("edit-auto-start").checked ? "1" : "0"
      })
    });

    const json = await res.json();
    if (json.success) {
      msg.innerText = "Settings saved! Reloading...";
      msg.style.color = "lightgreen";
      setTimeout(() => location.reload(), 1500);
    } else {
      msg.innerText = json.error || "Save failed";
      msg.style.color = "red";
    }
  } catch (e) {
    msg.innerText = "Error: " + e.message;
    msg.style.color = "red";
  }
}

function copyAdminDeviceId() {
  const copyText = $("admin-device-id");
  copyText.select();
  copyText.setSelectionRange(0, 99999); // For mobile devices
  navigator.clipboard.writeText(copyText.value);
  alert("Device ID copied to clipboard!");
}

// Section Renaming
function openRenameModal(id, currentName) {
  $("section-rename-modal").style.display = "flex";
  $("new-section-name").value = currentName;
  $("rename-section-id").value = id;
  $("section-rename-msg").innerText = "";
}

async function saveSectionName() {
  const id = $("rename-section-id").value;
  const newName = $("new-section-name").value;
  const msg = $("section-rename-msg");

  if (!newName) {
    msg.innerText = "Please enter a name";
    msg.style.color = "red";
    return;
  }

  msg.innerText = "Updating...";
  try {
    const res = await fetch("/api/update_section_name", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ section_id: id, name: newName })
    });
    const json = await res.json();
    if (json.success) {
      msg.innerText = "Renamed successfully!";
      msg.style.color = "lightgreen";
      await fetchSections();
      setTimeout(closeModals, 1000);
    } else {
      msg.innerText = json.error || "Failed to rename";
      msg.style.color = "red";
    }
  } catch (e) {
    msg.innerText = "Error: " + e;
    msg.style.color = "red";
  }
}

// Multi-step Renewal (Lock Screen)
let renewPassword = null;

async function renewVerify() {
  const pwd = document.getElementById("renew-admin-pass").value;
  const msg = document.getElementById("renew-msg");

  msg.innerText = "Verifying...";
  msg.style.color = "white";

  try {
    const res = await fetch("/api/verify_admin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: pwd })
    });
    const json = await res.json();

    if (json.success) {
      renewPassword = pwd;
      document.getElementById("renew-step-1").style.display = "none";
      document.getElementById("renew-step-2").style.display = "block";
      document.getElementById("renew-msg").innerText = "";
    } else {
      msg.innerText = json.error || "Verification failed";
      msg.style.color = "red";
    }
  } catch (e) {
    msg.innerText = "Error: " + e;
    msg.style.color = "red";
  }
}

async function renewSetDate() {
  const dateVal = document.getElementById("renew-next-date").value;
  const msg = document.getElementById("renew-msg");

  if (!dateVal) {
    msg.innerText = "Please pick a date";
    msg.style.color = "red";
    return;
  }

  msg.innerText = "Updating...";
  msg.style.color = "white";

  try {
    const res = await fetch("/api/set_license_custom", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: renewPassword, date: dateVal })
    });
    const json = await res.json();

    if (json.success) {
      msg.innerText = "License Renewed! reloading...";
      msg.style.color = "lightgreen";
      setTimeout(() => location.reload(), 1500);
    } else {
      msg.innerText = json.error || "Renewal failed";
      msg.style.color = "red";
    }
  } catch (e) {
    msg.innerText = "Error: " + e;
    msg.style.color = "red";
  }
}

// Custom Date Modal (Two-Step)
let verifiedPassword = null;

function openLicenseModal() {
  document.getElementById("auth-modal").style.display = "flex";
  document.getElementById("auth-pass").value = "";
  document.getElementById("auth-msg").innerText = "";
}

function closeModals() {
  document.getElementById("auth-modal").style.display = "none";
  document.getElementById("expiry-modal").style.display = "none";
  document.getElementById("admin-settings-modal").style.display = "none";
  document.getElementById("section-rename-modal").style.display = "none";
  verifiedPassword = null;
}

async function verifyAndNext() {
  const pwd = document.getElementById("auth-pass").value;
  const msg = document.getElementById("auth-msg");

  msg.innerText = "Verifying...";
  msg.style.color = "white";

  try {
    const res = await fetch("/api/verify_admin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: pwd })
    });
    const json = await res.json();

    if (json.success) {
      verifiedPassword = pwd;
      document.getElementById("auth-modal").style.display = "none";
      document.getElementById("expiry-modal").style.display = "flex";
      document.getElementById("new-expiry-date").value = "";
      document.getElementById("expiry-msg").innerText = "";
    } else {
      msg.innerText = json.error || "Verification failed";
      msg.style.color = "red";
    }
  } catch (e) {
    msg.innerText = "Error: " + e;
    msg.style.color = "red";
  }
}

async function updateLicenseDate() {
  const dateVal = document.getElementById("new-expiry-date").value;
  const msg = document.getElementById("expiry-msg");

  if (!dateVal) {
    msg.innerText = "Please pick a date";
    msg.style.color = "red";
    return;
  }

  msg.innerText = "Updating...";
  msg.style.color = "white";

  try {
    const res = await fetch("/api/set_license_custom", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: verifiedPassword, date: dateVal })
    });
    const json = await res.json();

    if (json.success) {
      msg.innerText = "Date Updated! Reloading...";
      msg.style.color = "lightgreen";
      setTimeout(() => location.reload(), 1500);
    } else {
      msg.innerText = json.error || "Update failed";
      msg.style.color = "red";
    }
  } catch (e) {
    msg.innerText = "Error: " + e;
    msg.style.color = "red";
  }
}

async function start() {
  startClock();
  await fetchSchoolInfo();
  await fetchSections();
  await loadSounds();
  await checkLicense(); // Check immediately
  await refreshActive();

  // Set initial collapsed state (containers are collapsed by default in HTML/CSS)
  $("sections-container").classList.add("collapsed-container");
  $("slots-area").classList.add("collapsed-container");

  setInterval(refreshActive, 30000);
  setInterval(checkLicense, 60000); // Check every minute
}

window.onload = start;
window.playSlot = playSlot;
window.saveSlot = saveSlot;
window.markDirty = markDirty;
window.stopSound = stopSound;
window.uploadSound = uploadSound;
window.renewVerify = renewVerify;
window.renewSetDate = renewSetDate;
window.openLicenseModal = openLicenseModal;
window.closeModals = closeModals;
window.verifyAndNext = verifyAndNext;
window.updateLicenseDate = updateLicenseDate;
window.openAdminSettings = openAdminSettings;
window.verifyAdminSettings = verifyAdminSettings;
window.saveAdminSettings = saveAdminSettings;
window.saveSectionName = saveSectionName;
