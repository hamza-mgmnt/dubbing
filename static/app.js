document.addEventListener("DOMContentLoaded", () => {
  // Initialize Lucide icons
  lucide.createIcons();

  // Elements
  const dropzone = document.getElementById("dropzone");
  const videoInput = document.getElementById("videoInput");
  const dropzoneContent = document.getElementById("dropzoneContent");
  const sourcePreviewContainer = document.getElementById("sourcePreviewContainer");
  const sourceVideoPreview = document.getElementById("sourceVideoPreview");
  const sourceFileName = document.getElementById("sourceFileName");
  const removeVideoBtn = document.getElementById("removeVideoBtn");

  const targetLanguageSelect = document.getElementById("targetLanguage");
  const whisperModelSelect = document.getElementById("whisperModel");
  const hfTokenInput = document.getElementById("hfToken");
  const startDubBtn = document.getElementById("startDubBtn");

  const progressSection = document.getElementById("progressSection");
  const progressBar = document.getElementById("progressBar");
  const progressPercentage = document.getElementById("progressPercentage");
  const currentStatusText = document.getElementById("currentStatusText");
  const logConsole = document.getElementById("logConsole");

  const resultSection = document.getElementById("resultSection");
  const dubbedVideoPlayer = document.getElementById("dubbedVideoPlayer");
  const downloadBtn = document.getElementById("downloadBtn");
  const transcriptContainer = document.getElementById("transcriptContainer");
  const speakerCountBadge = document.getElementById("speakerCountBadge");

  let selectedFile = null;
  let activeEventSource = null;

  // Speaker Color Palettes
  const SPEAKER_COLORS = [
    { bg: "bg-indigo-500/15", border: "border-indigo-500/30", text: "text-indigo-400", badge: "bg-indigo-500/20 text-indigo-300" },
    { bg: "bg-fuchsia-500/15", border: "border-fuchsia-500/30", text: "text-fuchsia-400", badge: "bg-fuchsia-500/20 text-fuchsia-300" },
    { bg: "bg-emerald-500/15", border: "border-emerald-500/30", text: "text-emerald-400", badge: "bg-emerald-500/20 text-emerald-300" },
    { bg: "bg-amber-500/15", border: "border-amber-500/30", text: "text-amber-400", badge: "bg-amber-500/20 text-amber-300" },
    { bg: "bg-sky-500/15", border: "border-sky-500/30", text: "text-sky-400", badge: "bg-sky-500/20 text-sky-300" },
  ];

  // 1. Fetch Supported Languages
  async function loadLanguages() {
    try {
      const res = await fetch("/api/languages");
      if (res.ok) {
        const languages = await res.json();
        targetLanguageSelect.innerHTML = "";
        languages.forEach(lang => {
          const opt = document.createElement("option");
          opt.value = lang.code;
          opt.textContent = `${lang.flag} ${lang.name}`;
          if (lang.code === "hi") opt.selected = true;
          targetLanguageSelect.appendChild(opt);
        });
      }
    } catch (e) {
      console.warn("Could not load dynamic language list, using fallback.", e);
    }
  }
  loadLanguages();

  // 2. Drag and Drop handlers
  dropzone.addEventListener("click", (e) => {
    if (e.target.closest("#removeVideoBtn") || e.target.closest("video")) return;
    videoInput.click();
  });

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("border-indigo-500", "bg-indigo-500/5");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("border-indigo-500", "bg-indigo-500/5");
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("border-indigo-500", "bg-indigo-500/5");
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  videoInput.addEventListener("change", () => {
    if (videoInput.files && videoInput.files[0]) {
      handleFileSelected(videoInput.files[0]);
    }
  });

  function handleFileSelected(file) {
    if (!file.type.startsWith("video/") && !file.name.match(/\.(mp4|mkv|mov|webm)$/i)) {
      alert("Please upload a valid video file (.mp4, .mkv, .mov, or .webm)");
      return;
    }
    selectedFile = file;
    sourceFileName.textContent = `${file.name} (${(file.size / (1024 * 1024)).toFixed(1)} MB)`;
    sourceVideoPreview.src = URL.createObjectURL(file);

    dropzoneContent.classList.add("hidden");
    sourcePreviewContainer.classList.remove("hidden");
    startDubBtn.disabled = false;
    lucide.createIcons();
  }

  removeVideoBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    selectedFile = null;
    videoInput.value = "";
    sourceVideoPreview.src = "";
    sourcePreviewContainer.classList.add("hidden");
    dropzoneContent.classList.remove("hidden");
    startDubBtn.disabled = true;
  });

  // 3. Log Helper
  function appendLog(message, isError = false) {
    const logItem = document.createElement("div");
    const timestamp = new Date().toLocaleTimeString();
    logItem.className = isError ? "text-rose-400 font-medium" : "text-slate-300";
    logItem.innerHTML = `<span class="text-slate-500">[${timestamp}]</span> ${message}`;
    logConsole.appendChild(logItem);
    logConsole.scrollTop = logConsole.scrollHeight;
  }

  // 4. Start Dubbing Action
  startDubBtn.addEventListener("click", async () => {
    if (!selectedFile) return;

    // Reset and show progress
    startDubBtn.disabled = true;
    progressSection.classList.remove("hidden");
    resultSection.classList.add("hidden");
    logConsole.innerHTML = "";
    progressBar.style.width = "5%";
    progressPercentage.textContent = "5%";
    currentStatusText.textContent = "Uploading video file...";
    appendLog("Uploading video to server...");

    const audioMode = document.querySelector('input[name="audioMode"]:checked')?.value || "replace";

    const formData = new FormData();
    formData.append("video", selectedFile);
    formData.append("target_language", targetLanguageSelect.value);
    formData.append("whisper_model", whisperModelSelect.value);
    formData.append("audio_mode", audioMode);
    if (hfTokenInput.value.trim()) {
      formData.append("hf_token", hfTokenInput.value.trim());
    }

    try {
      const response = await fetch("/api/dub", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const data = await response.json();
      const taskId = data.task_id;
      appendLog(`Task registered (ID: ${taskId}). Commencing pipeline...`);

      // Start listening to live updates
      listenToProgress(taskId);
    } catch (err) {
      appendLog(`Error starting dubbing task: ${err.message}`, true);
      currentStatusText.textContent = "Error occurred";
      startDubBtn.disabled = false;
    }
  });

  // 5. SSE Progress Listener with Polling Fallback
  function listenToProgress(taskId) {
    if (activeEventSource) {
      activeEventSource.close();
    }

    let completed = false;

    // Connect Server-Sent Events
    try {
      activeEventSource = new EventSource(`/api/events/${taskId}`);

      activeEventSource.onmessage = (event) => {
        try {
          const state = JSON.parse(event.data);
          updateProgressUI(state);
          if (state.status === "completed" || state.status === "error") {
            completed = true;
            activeEventSource.close();
          }
        } catch (e) {
          console.error("Failed to parse event data", e);
        }
      };

      activeEventSource.onerror = () => {
        // Fallback to polling if SSE encounters issues
        activeEventSource.close();
        if (!completed) {
          pollProgress(taskId);
        }
      };
    } catch (e) {
      pollProgress(taskId);
    }
  }

  // Polling Fallback
  async function pollProgress(taskId) {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/status/${taskId}`);
        if (!res.ok) return;
        const state = await res.json();
        updateProgressUI(state);

        if (state.status === "completed" || state.status === "error") {
          clearInterval(interval);
        }
      } catch (err) {
        console.error("Polling error", err);
      }
    }, 2000);
  }

  function updateProgressUI(state) {
    const pct = state.percent || 0;
    progressBar.style.width = `${pct}%`;
    progressPercentage.textContent = `${pct}%`;

    if (state.message) {
      currentStatusText.textContent = state.message;
      appendLog(state.message);
    }

    if (state.status === "completed" && state.result) {
      appendLog("Processing complete! Rendering preview...", false);
      displayResults(state.result);
      startDubBtn.disabled = false;
    } else if (state.status === "error") {
      appendLog(`Pipeline error: ${state.error || state.message}`, true);
      currentStatusText.textContent = "Pipeline failed";
      startDubBtn.disabled = false;
    }
  }

  // 6. Display Final Dubbed Video & Transcript Breakdown
  function displayResults(result) {
    resultSection.classList.remove("hidden");
    resultSection.scrollIntoView({ behavior: "smooth" });

    // Video Player & Download link
    const videoUrl = `/outputs/${result.output_filename}`;
    dubbedVideoPlayer.src = videoUrl;
    dubbedVideoPlayer.load();

    downloadBtn.href = `/api/download/${result.output_filename}`;
    downloadBtn.setAttribute("download", result.output_filename);

    // Diarized Transcript
    const segments = result.segments || [];
    transcriptContainer.innerHTML = "";

    // Count unique speakers
    const uniqueSpeakers = [...new Set(segments.map(s => s.speaker))];
    speakerCountBadge.textContent = `${uniqueSpeakers.length} Speaker${uniqueSpeakers.length > 1 ? 's' : ''} Detected`;

    segments.forEach((seg, index) => {
      const spkIdx = uniqueSpeakers.indexOf(seg.speaker);
      const palette = SPEAKER_COLORS[spkIdx % SPEAKER_COLORS.length];

      const item = document.createElement("div");
      item.className = `p-4 rounded-xl border ${palette.border} ${palette.bg} transition-all space-y-2`;

      item.innerHTML = `
        <div class="flex flex-wrap items-center justify-between gap-2 text-xs">
          <div class="flex items-center gap-2">
            <span class="px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider text-[11px] ${palette.badge}">
              ${seg.speaker}
            </span>
            <span class="text-slate-400 font-mono">
              ${formatTimestamp(seg.start)} ➔ ${formatTimestamp(seg.end)}
            </span>
          </div>
          <span class="text-[11px] text-slate-400 bg-slate-900/60 px-2 py-0.5 rounded-md border border-slate-800">
            Voice: <span class="${palette.text} font-medium">${seg.voice?.label || 'Default'}</span>
          </span>
        </div>

        <div class="space-y-1 text-xs">
          <div class="text-slate-400">
            <span class="text-slate-500 font-semibold mr-1">Original:</span>"${escapeHtml(seg.text)}"
          </div>
          <div class="text-white font-medium text-sm">
            <span class="text-indigo-400 font-semibold text-xs mr-1">Dubbed:</span>"${escapeHtml(seg.translated_text || seg.text)}"
          </div>
        </div>
      `;

      transcriptContainer.appendChild(item);
    });

    lucide.createIcons();
  }

  function formatTimestamp(sec) {
    const m = Math.floor(sec / 60).toString().padStart(2, "0");
    const s = Math.floor(sec % 60).toString().padStart(2, "0");
    const ms = Math.floor((sec % 1) * 10).toString();
    return `${m}:${s}.${ms}`;
  }

  function escapeHtml(str) {
    return (str || "").replace(/[&<>"']/g, (m) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    }[m]));
  }
});
