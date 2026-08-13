const config = window.APP_CONFIG || {};

const els = {
  refreshButton: document.querySelector("#refreshButton"),
  killProcessButton: document.querySelector("#killProcessButton"),
  stopScanButton: document.querySelector("#stopScanButton"),
  stopScanButtonText: document.querySelector("#stopScanButtonText"),
  systemBadge: document.querySelector("#systemBadge"),
  systemBadgeText: document.querySelector("#systemBadgeText"),
  globalError: document.querySelector("#globalError"),

  totalProfiles: document.querySelector("#totalProfiles"),
  pendingCount: document.querySelector("#pendingCount"),
  processingCount: document.querySelector("#processingCount"),
  completedCount: document.querySelector("#completedCount"),
  failedCount: document.querySelector("#failedCount"),

  profilesTabCount: document.querySelector("#profilesTabCount"),
  queueTabCount: document.querySelector("#queueTabCount"),

  activeProcessBadge: document.querySelector("#activeProcessBadge"),
  activeProcessContent: document.querySelector("#activeProcessContent"),
  readyAccountSummary: document.querySelector("#readyAccountSummary"),
  overviewAccountList: document.querySelector("#overviewAccountList"),
  activityTimeline: document.querySelector("#activityTimeline"),
  lastUpdated: document.querySelector("#lastUpdated"),

  resultSummary: document.querySelector("#resultSummary"),
  searchInput: document.querySelector("#searchInput"),
  sortSelect: document.querySelector("#sortSelect"),
  errorState: document.querySelector("#errorState"),
  emptyState: document.querySelector("#emptyState"),
  tableWrap: document.querySelector("#tableWrap"),
  profileTableBody: document.querySelector("#profileTableBody"),

  queueSummary: document.querySelector("#queueSummary"),
  queueSearchInput: document.querySelector("#queueSearchInput"),
  queueStatusFilter: document.querySelector("#queueStatusFilter"),
  queueEmptyState: document.querySelector("#queueEmptyState"),
  queueTableWrap: document.querySelector("#queueTableWrap"),
  queueTableBody: document.querySelector("#queueTableBody"),
  accountsGrid: document.querySelector("#accountsGrid"),

  healthOverallBadge: document.querySelector("#healthOverallBadge"),
  healthServiceList: document.querySelector("#healthServiceList"),
  workerDetailGrid: document.querySelector("#workerDetailGrid"),
  healthHeartbeatAge: document.querySelector("#healthHeartbeatAge"),
  healthStaleJobs: document.querySelector("#healthStaleJobs"),
  healthUnsentLark: document.querySelector("#healthUnsentLark"),
  healthNeedsLogin: document.querySelector("#healthNeedsLogin"),
  
  youtubeTabCount: document.querySelector("#youtubeTabCount"),
  youtubeResearchForm: document.querySelector("#youtubeResearchForm"),
  youtubeKeywordInput: document.querySelector("#youtubeKeywordInput"),
  youtubeStartButton: document.querySelector("#youtubeStartButton"),
  youtubeStartButtonText: document.querySelector("#youtubeStartButtonText"),
  youtubeJobBadge: document.querySelector("#youtubeJobBadge"),
  youtubeProgressText: document.querySelector("#youtubeProgressText"),
  youtubeProgressBar: document.querySelector("#youtubeProgressBar"),
  youtubeStageText: document.querySelector("#youtubeStageText"),
  youtubeResultCount: document.querySelector("#youtubeResultCount"),
  youtubeLastError: document.querySelector("#youtubeLastError"),
  youtubeResultSummary: document.querySelector("#youtubeResultSummary"),
  youtubeSearchInput: document.querySelector("#youtubeSearchInput"),
  youtubeKeywordFilter: document.querySelector("#youtubeKeywordFilter"),
  youtubeLocationFilter: document.querySelector("#youtubeLocationFilter"),
  youtubeEmailFilter: document.querySelector("#youtubeEmailFilter"),
  youtubeSubscriberFilter: document.querySelector("#youtubeSubscriberFilter"),
  youtubeSortSelect: document.querySelector("#youtubeSortSelect"),
  youtubeEmptyState: document.querySelector("#youtubeEmptyState"),
  youtubeTableWrap: document.querySelector("#youtubeTableWrap"),
  youtubeTableBody: document.querySelector("#youtubeTableBody"),

    // OUTREACH
  outreachConnectForm:
    document.querySelector("#outreachConnectForm"),

  outreachUrlInput:
    document.querySelector("#outreachUrlInput"),

  outreachStartButton:
    document.querySelector("#outreachStartButton"),

  outreachStartButtonText:
    document.querySelector("#outreachStartButtonText"),

  outreachDetectedCount:
    document.querySelector("#outreachDetectedCount"),

  outreachJobBadge:
    document.querySelector("#outreachJobBadge"),

  outreachJobCode:
    document.querySelector("#outreachJobCode"),

  outreachJobEmpty:
    document.querySelector("#outreachJobEmpty"),

  outreachJobResult:
    document.querySelector("#outreachJobResult"),

  outreachInputCount:
    document.querySelector("#outreachInputCount"),

  outreachReadyCount:
    document.querySelector("#outreachReadyCount"),

  outreachProcessedCount:
    document.querySelector("#outreachProcessedCount"),

  outreachSuccessCount:
    document.querySelector("#outreachSuccessCount"),

  outreachFailedCount:
    document.querySelector("#outreachFailedCount"),

  outreachDuplicateCount:
    document.querySelector("#outreachDuplicateCount"),

  outreachInvalidCount:
    document.querySelector("#outreachInvalidCount"),

  outreachProgressText:
    document.querySelector("#outreachProgressText"),

  outreachProgressBar:
    document.querySelector("#outreachProgressBar"),

  outreachProgressPercent:
    document.querySelector("#outreachProgressPercent"),

  outreachJobStatus:
    document.querySelector("#outreachJobStatus"),

  outreachCreatedAt:
    document.querySelector("#outreachCreatedAt"),

  outreachStartedAt:
    document.querySelector("#outreachStartedAt"),

  outreachCompletedAt:
    document.querySelector("#outreachCompletedAt"),

  outreachJobMessage:
    document.querySelector("#outreachJobMessage"),

  outreachLastError:
    document.querySelector("#outreachLastError"),

  outreachCurrentTargets:
  document.querySelector("#outreachCurrentTargets"),

  outreachCurrentTargetCount:
    document.querySelector("#outreachCurrentTargetCount"),

  outreachCurrentTargetsToggle:
    document.querySelector("#outreachCurrentTargetsToggle"),

  outreachCurrentTargetsArrow:
    document.querySelector("#outreachCurrentTargetsArrow"),

  outreachError:
    document.querySelector("#outreachError"),

  outreachSchedulerBadge:
    document.querySelector("#outreachSchedulerBadge"),

  outreachCurrentAccount:
    document.querySelector("#outreachCurrentAccount"),

  outreachUsedTurn:
    document.querySelector("#outreachUsedTurn"),

  outreachRemainingTurn:
    document.querySelector("#outreachRemainingTurn"),

  outreachSchedulerUpdatedAt:
    document.querySelector("#outreachSchedulerUpdatedAt"),

  outreachAccountCount:
    document.querySelector("#outreachAccountCount"),

  outreachAccountsList:
    document.querySelector("#outreachAccountsList"),

  outreachDashboardUpdatedAt:
    document.querySelector("#outreachDashboardUpdatedAt"),

  outreachHistoryEmpty:
    document.querySelector("#outreachHistoryEmpty"),

  outreachHistoryTableWrap:
    document.querySelector("#outreachHistoryTableWrap"),

  outreachHistoryBody:
    document.querySelector("#outreachHistoryBody"),

    // DRAWER
  drawerBackdrop:
    document.querySelector("#drawerBackdrop"),

  detailDrawer:
    document.querySelector("#detailDrawer"),

  drawerName:
    document.querySelector("#drawerName"),

  drawerContent:
    document.querySelector("#drawerContent"),

  closeDrawerButton:
    document.querySelector("#closeDrawerButton")
};

const state = {
  profiles: [],
  filteredProfiles: [],
  sources: [],
  filteredSources: [],
  accounts: [],
  worker: null,
  youtubeJobs: [],
  youtubeChannels: [],
  activeYoutubeJob: null,
  youtubeSubmitting: false,
  youtubePollTimer: null,
  youtubeRealtimeChannel: null,
  youtubeRealtimeReloadTimer: null,
  outreachSubmitting: false,
  outreachCurrentJob: null,
  outreachScheduler: null,
  outreachAccounts: [],
  outreachRecentJobs: [],
  outreachPollTimer: null,
  outreachDashboardLoading: false,
  tableErrors: {},
  commandPending: false
};

function assertConfig() {
  const validUrl =
    typeof config.supabaseUrl === "string" &&
    config.supabaseUrl.startsWith("https://");

  const validKey =
    typeof config.supabasePublishableKey === "string" &&
    !config.supabasePublishableKey.includes("YOUR_");

  if (!validUrl || !validKey) {
    throw new Error(
      "Thiếu Supabase URL hoặc publishable/anon key trong config.js."
    );
  }
}

assertConfig();

const client = window.supabase.createClient(
  config.supabaseUrl,
  config.supabasePublishableKey
);

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDate(value) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(date);
}

function formatAge(value) {
  if (!value) return "Không có dữ liệu";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Không xác định";
  }

  const seconds = Math.max(
    0,
    Math.floor((Date.now() - date.getTime()) / 1000)
  );

  if (seconds < 60) return `${seconds} giây trước`;

  const minutes = Math.floor(seconds / 60);

  if (minutes < 60) return `${minutes} phút trước`;

  const hours = Math.floor(minutes / 60);

  if (hours < 24) return `${hours} giờ trước`;

  return `${Math.floor(hours / 24)} ngày trước`;
}

function isToday(value) {
  if (!value) return false;

  const date = new Date(value);
  const now = new Date();

  return (
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  );
}

function isComplete(profile) {
  return Boolean(
    profile.name &&
    profile.headline &&
    profile.location
  );
}

function getPostCaptions(profile) {
  return [
    profile.post_1_caption,
    profile.post_2_caption,
    profile.post_3_caption,
    profile.post_4_caption,
    profile.post_5_caption
  ]
    .map((caption) => String(caption || "").trim())
    .filter(Boolean);
}

function getInitials(name) {
  const text = String(name || "").trim();

  if (!text) return "—";

  return text
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() || "")
    .join("");
}

function getLatestSnapshots(rows) {
  const latestBySource = new Map();

  for (const row of rows) {
    if (!latestBySource.has(row.source_id)) {
      latestBySource.set(row.source_id, row);
    }
  }

  return Array.from(latestBySource.values());
}

function normaliseStatus(value) {
  return String(value || "unknown")
    .trim()
    .toLowerCase();
}

function statusLabel(value) {
  const status = normaliseStatus(value);

  const labels = {
    pending: "Pending",
    processing: "Processing",
    completed: "Completed",
    failed: "Failed",
    disabled: "Disabled",
    available: "Available",
    scanning: "Scanning",
    cooldown: "Cooldown",
    needs_login: "Needs login",
    error: "Error",
    starting: "Starting",
    idle: "Idle",
    stopping: "Stopping",
    offline: "Offline"
  };

  return labels[status] || status;
}

function statusBadge(value) {
  const status = normaliseStatus(value);

  return `
    <span class="status-badge status-${escapeHtml(status)}">
      ${escapeHtml(statusLabel(status))}
    </span>
  `;
}

function countByStatus(status) {
  return state.sources.filter(
    (source) => normaliseStatus(source.job_status) === status
  ).length;
}

async function safeQuery(name, queryPromise, fallback) {
  try {
    const result = await queryPromise;

    if (result.error) {
      throw result.error;
    }

    delete state.tableErrors[name];

    return result.data ?? fallback;
  } catch (error) {
    state.tableErrors[name] = error.message || String(error);
    return fallback;
  }
}


function updateWorkerControlButtons() {
  const workerStatus = normaliseStatus(
    state.worker?.status
  );

  const isPaused = workerStatus === "paused";

  els.stopScanButton.classList.toggle(
    "is-resume",
    isPaused
  );

  els.stopScanButtonText.textContent =
    isPaused
      ? "Resume scan"
      : "Stop scan";

  els.stopScanButton.disabled =
    state.commandPending ||
    !state.worker?.worker_id;

  els.killProcessButton.disabled =
    state.commandPending ||
    !state.worker?.worker_id ||
    !state.worker?.current_source_id;
}

async function sendWorkerCommand(command) {
  const workerId = String(
    state.worker?.worker_id || ""
  ).trim();

  if (!workerId) {
    throw new Error(
      "Không tìm thấy worker_id đang hoạt động."
    );
  }

  const labels = {
    kill_current: "kill lượt quét hiện tại",
    stop_scan: "tạm dừng scanner",
    resume_scan: "tiếp tục scanner"
  };

  const confirmed = window.confirm(
    `Xác nhận ${labels[command] || command}?`
  );

  if (!confirmed) {
    return;
  }

  state.commandPending = true;
  updateWorkerControlButtons();

  try {
    const response = await fetch(
      "/api/worker/commands",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          worker_id: workerId,
          command
        })
      }
    );

    const result = await response.json();

    if (!response.ok || !result.ok) {
      throw new Error(
        result.detail ||
        result.error ||
        "Không thể gửi worker command."
      );
    }

    els.globalError.hidden = false;
    els.globalError.innerHTML = `
      <strong>Đã gửi command.</strong><br />
      ${escapeHtml(labels[command] || command)}
      — worker sẽ xử lý trong vài giây.
    `;

    window.setTimeout(
      loadDashboard,
      1500
    );
  } finally {
    state.commandPending = false;
    updateWorkerControlButtons();
  }
}



function formatCompactNumber(value, fallback = "—") {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return fallback;
  }

  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1
  }).format(number);
}

function youtubeStageLabel(value) {
  const stage = normaliseStatus(value);

  const labels = {
    queued: "Queued",
    starting: "Starting",
    searching: "Searching YouTube",
    collecting_channels: "Collecting channels",
    scanning_channels: "Scanning channels",
    saving_results: "Saving results",
    completed: "Completed",
    failed: "Failed"
  };

  return labels[stage] || statusLabel(stage);
}

function youtubeBadgeClass(status) {
  const cleaned = normaliseStatus(status);

  if (cleaned === "completed") return "pill-green";
  if (cleaned === "failed") return "pill-red";
  if (cleaned === "pending") return "pill-amber";
  if (cleaned === "processing") return "pill-purple";

  return "pill-neutral";
}

async function fetchAllYoutubeRows(queryFactory, pageSize = 1000) {
  const rows = [];
  let from = 0;

  while (true) {
    const result = await queryFactory(
      from,
      from + pageSize - 1
    );

    if (result.error) {
      throw result.error;
    }

    const batch = result.data || [];
    rows.push(...batch);

    if (batch.length < pageSize) {
      break;
    }

    from += pageSize;
  }

  return rows;
}

function populateYoutubeFilterOptions() {
  const currentKeyword =
    els.youtubeKeywordFilter?.value || "all";
  const currentLocation =
    els.youtubeLocationFilter?.value || "all";

  const keywords = Array.from(
    new Set(
      (state.youtubeJobs || [])
        .map((job) => String(job.keyword || "").trim())
        .filter(Boolean)
    )
  ).sort((a, b) => a.localeCompare(b));

  const locations = Array.from(
    new Set(
      (state.youtubeChannels || [])
        .map((channel) => String(channel.location || "").trim())
        .filter(Boolean)
    )
  ).sort((a, b) => a.localeCompare(b));

  els.youtubeKeywordFilter.innerHTML = [
    '<option value="all">Tất cả keyword</option>',
    ...keywords.map(
      (keyword) =>
        `<option value="${escapeHtml(keyword)}">${escapeHtml(keyword)}</option>`
    )
  ].join("");

  els.youtubeLocationFilter.innerHTML = [
    '<option value="all">Tất cả location</option>',
    ...locations.map(
      (location) =>
        `<option value="${escapeHtml(location)}">${escapeHtml(location)}</option>`
    )
  ].join("");

  els.youtubeKeywordFilter.value =
    keywords.includes(currentKeyword)
      ? currentKeyword
      : "all";

  els.youtubeLocationFilter.value =
    locations.includes(currentLocation)
      ? currentLocation
      : "all";
}

async function loadYoutubeResearch() {
  try {
    state.youtubeJobs = await fetchAllYoutubeRows(
      (from, to) =>
        client
          .from("youtube_scan_jobs")
          .select(
            "id,keyword,status,current_stage,progress_percent,max_results,result_count,last_error,created_at,updated_at,completed_at"
          )
          .order("created_at", { ascending: false })
          .range(from, to)
    );

    delete state.tableErrors.youtubeJobs;
    state.activeYoutubeJob =
      state.youtubeJobs[0] || null;
  } catch (error) {
    state.tableErrors.youtubeJobs =
      error.message || String(error);
    state.youtubeJobs = [];
    state.activeYoutubeJob = null;
  }

  try {
    state.youtubeChannels = await fetchAllYoutubeRows(
      (from, to) =>
        client
          .from("youtube_scan_channels")
          .select(
            "id,job_id,channel_url,channel_name,subscriber_count_text,subscriber_count,video_count_text,video_count,channel_description,location,email,email_status,total_views_text,total_views,channel_links,scan_status,scanned_at"
          )
          .order("scanned_at", { ascending: false })
          .range(from, to)
    );

    delete state.tableErrors.youtubeChannels;
  } catch (error) {
    state.tableErrors.youtubeChannels =
      error.message || String(error);
    state.youtubeChannels = [];
  }

  populateYoutubeFilterOptions();
  renderYoutubeResearch();
  updateYoutubePolling();
}

function renderYoutubeResearch() {
  const job = state.activeYoutubeJob;

  const jobsById = new Map(
    (state.youtubeJobs || []).map(
      (item) => [String(item.id), item]
    )
  );

  const channels = state.youtubeChannels || [];

  const searchValue = String(
    els.youtubeSearchInput?.value || ""
  ).trim().toLowerCase();

  const keywordFilter =
    els.youtubeKeywordFilter?.value || "all";
  const locationFilter =
    els.youtubeLocationFilter?.value || "all";
  const emailFilter =
    els.youtubeEmailFilter?.value || "all";
  const subscriberFilter =
    els.youtubeSubscriberFilter?.value || "all";

  const minSubscribers =
    subscriberFilter === "all"
      ? 0
      : Number(subscriberFilter);

  let filteredChannels = channels.filter(
    (channel) => {
      const channelJob = jobsById.get(
        String(channel.job_id || "")
      );

      const keyword = String(
        channelJob?.keyword || ""
      ).trim();

      const location = String(
        channel.location || ""
      ).trim();

      const hasEmail = Boolean(
        String(channel.email || "").trim()
      );

      if (
        searchValue &&
        ![
          channel.channel_name,
          channel.channel_url,
          channel.location,
          channel.email,
          keyword
        ]
          .map((value) =>
            String(value || "").toLowerCase()
          )
          .some((value) =>
            value.includes(searchValue)
          )
      ) {
        return false;
      }

      if (
        keywordFilter !== "all" &&
        keyword !== keywordFilter
      ) {
        return false;
      }

      if (
        locationFilter !== "all" &&
        location !== locationFilter
      ) {
        return false;
      }

      if (
        emailFilter === "available" &&
        !hasEmail
      ) {
        return false;
      }

      if (
        emailFilter === "missing" &&
        hasEmail
      ) {
        return false;
      }

      if (
        minSubscribers > 0 &&
        Number(channel.subscriber_count || 0) <
          minSubscribers
      ) {
        return false;
      }

      return true;
    }
  );

  const sortValue =
    els.youtubeSortSelect?.value || "newest";

  filteredChannels.sort((a, b) => {
    if (sortValue === "subscribers") {
      return Number(b.subscriber_count || 0) -
        Number(a.subscriber_count || 0);
    }

    if (sortValue === "views") {
      return Number(b.total_views || 0) -
        Number(a.total_views || 0);
    }

    if (sortValue === "name") {
      return String(a.channel_name || "")
        .localeCompare(
          String(b.channel_name || "")
        );
    }

    return (
      new Date(b.scanned_at || 0).getTime() -
      new Date(a.scanned_at || 0).getTime()
    );
  });

  if (els.youtubeTabCount) {
    els.youtubeTabCount.textContent =
      String(channels.length);
  }

  const youtubeError =
    state.tableErrors.youtubeJobs ||
    state.tableErrors.youtubeChannels ||
    "";

  if (youtubeError) {
    els.youtubeLastError.hidden = false;
    els.youtubeLastError.textContent =
      `Không đọc được dữ liệu YouTube từ Supabase: ${youtubeError}`;
  }

  if (!job) {
    els.youtubeJobBadge.className =
      "pill pill-neutral";
    els.youtubeJobBadge.textContent = "Idle";
    els.youtubeProgressText.textContent =
      "Chưa có job";
    els.youtubeProgressBar.style.width = "0%";
    els.youtubeStageText.textContent = "Idle";
    els.youtubeResultCount.textContent =
      `${channels.length} total channels`;
  } else {
    const progress = Math.max(
      0,
      Math.min(
        100,
        Number(job.progress_percent || 0)
      )
    );

    const latestCount = channels.filter(
      (channel) =>
        String(channel.job_id) ===
        String(job.id)
    ).length;

    els.youtubeJobBadge.className =
      `pill ${youtubeBadgeClass(job.status)}`;
    els.youtubeJobBadge.textContent =
      statusLabel(job.status);
    els.youtubeProgressText.textContent =
      `${progress}%`;
    els.youtubeProgressBar.style.width =
      `${progress}%`;
    els.youtubeStageText.textContent =
      youtubeStageLabel(
        job.current_stage || job.status
      );
    els.youtubeResultCount.textContent =
      `${Math.max(
        Number(job.result_count || 0),
        latestCount
      )} / ${Number(job.max_results || 40)} latest · ${channels.length} total`;

    const lastError = String(
      job.last_error || ""
    ).trim();

    if (lastError) {
      els.youtubeLastError.hidden = false;
      els.youtubeLastError.textContent =
        lastError;
    } else if (!youtubeError) {
      els.youtubeLastError.hidden = true;
      els.youtubeLastError.textContent = "";
    }
  }

  els.youtubeResultSummary.textContent =
    `${filteredChannels.length} / ${channels.length} channel đang hiển thị`;

  els.youtubeStartButton.disabled =
    state.youtubeSubmitting ||
    normaliseStatus(job?.status) ===
      "processing" ||
    normaliseStatus(job?.status) ===
      "pending";

  els.youtubeStartButtonText.textContent =
    state.youtubeSubmitting
      ? "Creating job..."
      : "Start research";

  els.youtubeEmptyState.hidden =
    filteredChannels.length > 0;
  els.youtubeTableWrap.hidden =
    filteredChannels.length === 0;

  els.youtubeTableBody.innerHTML =
    filteredChannels
      .map((channel) => {
        const channelJob = jobsById.get(
          String(channel.job_id || "")
        );

        const keyword =
          channelJob?.keyword || "—";

        const links = Array.isArray(
          channel.channel_links
        )
          ? channel.channel_links
          : [];

        const linksHtml = links.length
          ? links
              .map((link) => `
                <a
                  class="youtube-link-chip"
                  href="${escapeHtml(link.url || "#")}"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  ${escapeHtml(link.title || "Link")}
                </a>
              `)
              .join("")
          : '<span class="table-muted">—</span>';

        const emailText = channel.email
          ? channel.email
          : statusLabel(
              channel.email_status ||
              "unavailable"
            );

        return `
          <tr>
            <td>
              <div class="youtube-channel-cell">
                <strong>${escapeHtml(
                  channel.channel_name ||
                  "Unnamed channel"
                )}</strong>
                <a
                  href="${escapeHtml(
                    channel.channel_url || "#"
                  )}"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  ${escapeHtml(
                    channel.channel_url || "—"
                  )}
                </a>
              </div>
            </td>
            <td>
              <span class="youtube-keyword-chip">
                ${escapeHtml(keyword)}
              </span>
            </td>
            <td>${escapeHtml(
              channel.subscriber_count_text ||
              formatCompactNumber(
                channel.subscriber_count
              )
            )}</td>
            <td>${escapeHtml(
              channel.video_count_text ||
              formatCompactNumber(
                channel.video_count
              )
            )}</td>
            <td>${escapeHtml(
              channel.location || "—"
            )}</td>
            <td>${escapeHtml(emailText)}</td>
            <td>${escapeHtml(
              channel.total_views_text ||
              formatCompactNumber(
                channel.total_views
              )
            )}</td>
            <td>
              <div class="youtube-link-list">
                ${linksHtml}
              </div>
            </td>
            <td>${escapeHtml(
              formatDate(channel.scanned_at)
            )}</td>
          </tr>
        `;
      })
      .join("");
}

async function createYoutubeResearchJob(event) {
  event.preventDefault();

  const keyword = String(
    els.youtubeKeywordInput.value || ""
  ).trim();

  if (!keyword) {
    window.alert("Hãy nhập keyword YouTube.");
    return;
  }

  state.youtubeSubmitting = true;
  renderYoutubeResearch();

  try {
    const response = await fetch(
      "/api/youtube/jobs",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          keyword,
          max_results: 40
        })
      }
    );

    const result = await response.json();

    if (!response.ok || !result.ok) {
      throw new Error(
        result.detail ||
        result.error ||
        "Không thể tạo YouTube research job."
      );
    }

    els.youtubeKeywordInput.value = "";
    await loadYoutubeResearch();
  } catch (error) {
    window.alert(error.message || String(error));
  } finally {
    state.youtubeSubmitting = false;
    renderYoutubeResearch();
  }
}

// =========================================================
// OUTREACH
// =========================================================


const OUTREACH_POLL_INTERVAL_MS = 3000;
const OUTREACH_ACCOUNT_DISPLAY_NAMES = {
  outreach_account_01: "Minh Anh",
  outreach_account_02: "Hân",
  outreach_account_03: "Minh Ánh",
  outreach_account_04: "Linh Giang",
  outreach_account_05: "Huyền Linh"
};

function getOutreachAccountDisplayName(accountId) {
  return (
    OUTREACH_ACCOUNT_DISPLAY_NAMES[accountId] ||
    accountId ||
    "—"
  );
}

// ---------------------------------------------------------
// URL INPUT
// ---------------------------------------------------------


function parseOutreachUrls() {
  const rawText = String(
    els.outreachUrlInput?.value || ""
  );

  const matches = rawText.match(
    /https?:\/\/(?:[a-z0-9-]+\.)?linkedin\.com\/in\/[^\s,;]+/gi
  );

  if (!matches) {
    return [];
  }

  return matches
    .map((url) =>
      url
        .trim()
        .replace(/[),.;]+$/g, "")
    )
    .filter(Boolean);
}

function updateOutreachDetectedCount() {
  const urls = parseOutreachUrls();

  if (!els.outreachDetectedCount) {
    return;
  }

  els.outreachDetectedCount.textContent =
    `${urls.length} URLs detected`;
}


// ---------------------------------------------------------
// SUBMIT BUTTON
// ---------------------------------------------------------


function renderOutreachSubmittingState() {
  if (!els.outreachStartButton) {
    return;
  }

  els.outreachStartButton.disabled =
    state.outreachSubmitting;

  if (els.outreachStartButtonText) {
    els.outreachStartButtonText.textContent =
      state.outreachSubmitting
        ? "Creating job..."
        : "Start Connect";
  }
}


// ---------------------------------------------------------
// STATUS
// ---------------------------------------------------------


function getOutreachPillClass(status) {
  const normalized = String(
    status || ""
  ).toLowerCase();

  if (normalized === "completed") {
    return "pill-green";
  }

  if (normalized === "failed") {
    return "pill-red";
  }

  if (normalized === "running") {
    return "pill-purple";
  }

  if (normalized === "pending") {
    return "pill-amber";
  }

  return "pill-neutral";
}


// ---------------------------------------------------------
// CURRENT JOB
// ---------------------------------------------------------


function renderOutreachJob(job) {
  if (!els.outreachJobEmpty) {
    return;
  }

  if (!job) {
    els.outreachJobEmpty.hidden = false;

    if (els.outreachJobResult) {
      els.outreachJobResult.hidden = true;
    }

    if (els.outreachJobCode) {
      els.outreachJobCode.textContent =
        "Chưa có job";
    }

    if (els.outreachJobBadge) {
      els.outreachJobBadge.textContent =
        "Idle";

      els.outreachJobBadge.className =
        "pill pill-neutral";
    }

    if (els.outreachCurrentTargetCount) {
      els.outreachCurrentTargetCount.textContent =
        "0 profiles";
    }

    if (els.outreachCurrentTargets) {
      els.outreachCurrentTargets.innerHTML = "";
      els.outreachCurrentTargets.hidden = true;
    }

    if (els.outreachCurrentTargetsArrow) {
      els.outreachCurrentTargetsArrow.textContent =
        "▾";
    }

    return;
  }

  els.outreachJobEmpty.hidden = true;

  if (els.outreachJobResult) {
    els.outreachJobResult.hidden = false;
  }

  const status = String(
    job.status || "pending"
  ).toLowerCase();

  const targetCount =
    Number(job.target_count || 0);

  const processedCount =
    Number(job.processed_count || 0);

  let progressPercent =
    Number(job.progress_percent || 0);

  if (
    !Number.isFinite(progressPercent) ||
    progressPercent < 0
  ) {
    progressPercent = 0;
  }

  progressPercent = Math.min(
    100,
    progressPercent
  );

  if (els.outreachJobCode) {
    els.outreachJobCode.textContent =
      job.job_code || "—";
  }

  if (els.outreachJobBadge) {
    els.outreachJobBadge.textContent =
      statusLabel(status);

    els.outreachJobBadge.className =
      `pill ${getOutreachPillClass(status)}`;
  }

  if (els.outreachInputCount) {
    els.outreachInputCount.textContent =
      String(job.input_count ?? 0);
  }

  if (els.outreachReadyCount) {
    els.outreachReadyCount.textContent =
      String(targetCount);
  }

  if (els.outreachProcessedCount) {
    els.outreachProcessedCount.textContent =
      String(processedCount);
  }

  if (els.outreachSuccessCount) {
    els.outreachSuccessCount.textContent =
      String(job.success_count ?? 0);
  }

  if (els.outreachFailedCount) {
    els.outreachFailedCount.textContent =
      String(job.failed_count ?? 0);
  }

  if (els.outreachDuplicateCount) {
    els.outreachDuplicateCount.textContent =
      String(job.duplicate_count ?? 0);
  }

  if (els.outreachInvalidCount) {
    els.outreachInvalidCount.textContent =
      String(job.invalid_count ?? 0);
  }

  if (els.outreachJobStatus) {
    els.outreachJobStatus.textContent =
      statusLabel(status);
  }

  if (els.outreachProgressText) {
    els.outreachProgressText.textContent =
      `${processedCount} / ${targetCount}`;
  }

  if (els.outreachProgressBar) {
    els.outreachProgressBar.style.width =
      `${progressPercent}%`;
  }

  if (els.outreachProgressPercent) {
    els.outreachProgressPercent.textContent =
      `${progressPercent}%`;
  }

  if (els.outreachCreatedAt) {
    els.outreachCreatedAt.textContent =
      formatDate(job.created_at);
  }

  if (els.outreachStartedAt) {
    els.outreachStartedAt.textContent =
      formatDate(job.started_at);
  }

  if (els.outreachCompletedAt) {
    els.outreachCompletedAt.textContent =
      formatDate(job.completed_at);
  }

  if (els.outreachJobMessage) {
    els.outreachJobMessage.textContent =
      (
        `${processedCount}/${targetCount} processed`
        + ` · ${job.success_count ?? 0} success`
        + ` · ${job.failed_count ?? 0} failed`
      );
  }

  if (els.outreachLastError) {
    const lastError = String(
      job.last_error || ""
    ).trim();

    els.outreachLastError.hidden =
      !lastError;

    els.outreachLastError.textContent =
      lastError;
  }

  const targets = Array.isArray(
    job.targets
  )
    ? job.targets
    : [];

  if (els.outreachCurrentTargetCount) {
    els.outreachCurrentTargetCount.textContent =
      `${targets.length} profiles`;
  }

  if (els.outreachCurrentTargets) {
    els.outreachCurrentTargets.innerHTML =
      renderOutreachTargetRows(
        targets
      );

    // Current Job luôn collapse sau mỗi dashboard refresh.
    els.outreachCurrentTargets.hidden = true;
  }

  if (els.outreachCurrentTargetsArrow) {
    els.outreachCurrentTargetsArrow.textContent =
      "▾";
  }
}


// ---------------------------------------------------------
// SCHEDULER
// ---------------------------------------------------------


function renderOutreachScheduler(
  scheduler
) {
  if (!scheduler) {
    if (els.outreachSchedulerBadge) {
      els.outreachSchedulerBadge.textContent =
        "No data";

      els.outreachSchedulerBadge.className =
        "pill pill-neutral";
    }

    if (els.outreachCurrentAccount) {
      els.outreachCurrentAccount.textContent =
        "—";
    }

    if (els.outreachUsedTurn) {
      els.outreachUsedTurn.textContent =
        "0 / 0";
    }

    if (els.outreachRemainingTurn) {
      els.outreachRemainingTurn.textContent =
        "0";
    }

    if (els.outreachSchedulerUpdatedAt) {
      els.outreachSchedulerUpdatedAt.textContent =
        "—";
    }

    return;
  }


  const used =
    Number(
      scheduler.used_in_current_turn || 0
    );

  const limit =
    Number(
      scheduler.turn_limit || 0
    );

  const remaining =
    Number(
      scheduler.remaining_in_current_turn || 0
    );


  if (els.outreachSchedulerBadge) {
    els.outreachSchedulerBadge.textContent =
      `${used}/${limit}`;

    els.outreachSchedulerBadge.className =
      "pill pill-purple";
  }


  if (els.outreachCurrentAccount) {
    els.outreachCurrentAccount.textContent =
      getOutreachAccountDisplayName(
        scheduler.current_account_id
      );
  }

  if (els.outreachUsedTurn) {
    els.outreachUsedTurn.textContent =
      `${used} / ${limit}`;
  }


  if (els.outreachRemainingTurn) {
    els.outreachRemainingTurn.textContent =
      String(remaining);
  }


  if (els.outreachSchedulerUpdatedAt) {
    els.outreachSchedulerUpdatedAt.textContent =
      formatDate(
        scheduler.updated_at
      );
  }
}


// ---------------------------------------------------------
// ACCOUNTS
// ---------------------------------------------------------
function getOutreachTargetPillClass(
  status
) {
  const normalized = String(
    status || ""
  ).toLowerCase();

  if (
    normalized === "completed" ||
    normalized === "invitation_sent" ||
    normalized === "already_connected"
  ) {
    return "pill-green";
  }

  if (normalized === "failed") {
    return "pill-red";
  }

  if (normalized === "running") {
    return "pill-purple";
  }

  if (normalized === "pending") {
    return "pill-amber";
  }

  return "pill-neutral";
}


function renderOutreachTargetRows(
  targets
) {
  const rows = Array.isArray(targets)
    ? targets
    : [];

  if (!rows.length) {
    return `
      <div class="outreach-job-empty outreach-target-empty">
        Chưa có profile target.
      </div>
    `;
  }

  return rows
    .map((target, index) => {
      const targetStatus = String(
        target.target_status || "pending"
      );

      const connectStatus = String(
        target.connect_status || "pending"
      );

      const error = String(
        target.last_error || ""
      ).trim();

      const linkedinUrl = String(
        target.linkedin_url || ""
      );

      const normalizedUrl = String(
        target.normalized_url || ""
      );

      return `
        <div class="outreach-target-card">

          <div class="outreach-target-main">

            <div class="outreach-target-index">
              ${index + 1}
            </div>

            <div class="outreach-target-url-block">

              <a
                class="outreach-target-url"
                href="${escapeHtml(linkedinUrl)}"
                target="_blank"
                rel="noopener noreferrer"
              >
                ${escapeHtml(linkedinUrl || "—")}
              </a>

              ${
                normalizedUrl &&
                normalizedUrl !== linkedinUrl
                  ? `
                    <span class="outreach-target-normalized">
                      ${escapeHtml(normalizedUrl)}
                    </span>
                  `
                  : ""
              }

            </div>

            <div class="outreach-target-statuses">

              <span class="pill ${getOutreachTargetPillClass(targetStatus)}">
                ${escapeHtml(targetStatus)}
              </span>

              <span class="pill ${getOutreachTargetPillClass(connectStatus)}">
                ${escapeHtml(connectStatus)}
              </span>

            </div>

          </div>


          <div class="outreach-target-meta">

            <div>
              <span>
                Account
              </span>

              <strong>
                ${escapeHtml(
                getOutreachAccountDisplayName(
                  target.assigned_account_id || "—"
                  )
                )}
              </strong>
            </div>


            <div>
              <span>
                Retry
              </span>

              <strong>
                ${Number(
                  target.retry_count || 0
                )}
              </strong>
            </div>


            <div>
              <span>
                Last attempt
              </span>

              <strong>
                ${escapeHtml(
                  formatDate(
                    target.last_connect_attempt_at
                  )
                )}
              </strong>
            </div>


            <div>
              <span>
                Completed
              </span>

              <strong>
                ${escapeHtml(
                  formatDate(
                    target.completed_at
                  )
                )}
              </strong>
            </div>


            <div>
              <span>
                Accepted
              </span>

              <strong>
                ${escapeHtml(
                  formatDate(
                    target.accepted_at
                  )
                )}
              </strong>
            </div>


            <div>
              <span>
                Message
              </span>

              <strong>
                ${escapeHtml(
                  target.message_status || "—"
                )}
              </strong>
            </div>

          </div>


          ${
            error
              ? `
                <div class="outreach-target-error">
                  ${escapeHtml(error)}
                </div>
              `
              : ""
          }

        </div>
      `;
    })
    .join("");
}

function renderOutreachAccounts(
  accounts
) {
  const rows = Array.isArray(accounts)
    ? accounts
    : [];

  if (els.outreachAccountCount) {
    els.outreachAccountCount.textContent =
      `${rows.length} accounts`;
  }

  if (!els.outreachAccountsList) {
    return;
  }

  if (!rows.length) {
    els.outreachAccountsList.innerHTML = `
      <div class="outreach-job-empty">
        Chưa có dữ liệu account.
      </div>
    `;

    return;
  }


  els.outreachAccountsList.innerHTML =
    rows
      .map((account) => {
        const accountId =
          escapeHtml(
            getOutreachAccountDisplayName(
              account.account_id
            )
          );

        const status =
          escapeHtml(
            account.status || "unknown"
          );

        const current =
          Boolean(
            account.is_current_account
          );

        const used =
          Number(
            account.used_in_current_turn || 0
          );

        const limit =
          Number(
            account.turn_limit || 0
          );

        const remaining =
          Number(
            account.remaining_in_current_turn || 0
          );

        const assigned =
          Number(
            account.total_assigned || 0
          );

        const completed =
          Number(
            account.completed_count || 0
          );

        const failed =
          Number(
            account.failed_count || 0
          );

        const dailySent =
          Number(
            account.daily_success_count || 0
          );

        const dailyLimit =
          Number(
            account.daily_limit || 50
          );

        const dailyRemaining =
          Number(
            account.daily_remaining ?? (
              dailyLimit - dailySent
            )
          );

        const weeklySent =
          Number(
            account.weekly_success_count || 0
          );

        const weeklyLimit =
          Number(
            account.weekly_limit || 250
          );

        const weeklyRemaining =
          Number(
            account.weekly_remaining ?? (
              weeklyLimit - weeklySent
            )
          );

        const quotaAvailable =
          account.quota_available !== false &&
          dailyRemaining > 0 &&
          weeklyRemaining > 0;

        const lastError = String(
          account.last_error || ""
        ).trim();

        return `
          <div class="
            outreach-account-card
            ${current ? "is-current" : ""}
          ">

            <div class="outreach-account-card-header">

              <div>
                <strong>
                  ${accountId}
                </strong>

                ${
                  current
                    ? `
                      <span class="outreach-current-label">
                        Current
                      </span>
                    `
                    : ""
                }

                ${
                  !quotaAvailable
                    ? `
                      <span class="outreach-current-label">
                        Limit reached
                      </span>
                    `
                    : ""
                }
              </div>

              <span class="pill pill-neutral">
                ${status}
              </span>

            </div>


            <div class="outreach-account-quota">

              <div>
                <span>
                  Turn
                </span>

                <strong>
                  ${used} / ${limit}
                </strong>
              </div>

              <div>
                <span>
                  Remaining
                </span>

                <strong>
                  ${remaining}
                </strong>
              </div>

            </div>


            <div class="outreach-account-quota">

              <div>
                <span>
                  Daily sent
                </span>

                <strong>
                  ${dailySent} / ${dailyLimit}
                </strong>
              </div>

              <div>
                <span>
                  Daily remaining
                </span>

                <strong>
                  ${Math.max(dailyRemaining, 0)}
                </strong>
              </div>

              <div>
                <span>
                  Weekly sent
                </span>

                <strong>
                  ${weeklySent} / ${weeklyLimit}
                </strong>
              </div>

              <div>
                <span>
                  Weekly remaining
                </span>

                <strong>
                  ${Math.max(weeklyRemaining, 0)}
                </strong>
              </div>

            </div>


            <div class="outreach-account-stats">

              <div>
                <span>
                  Assigned
                </span>

                <strong>
                  ${assigned}
                </strong>
              </div>

              <div>
                <span>
                  Success
                </span>

                <strong>
                  ${completed}
                </strong>
              </div>

              <div>
                <span>
                  Failed
                </span>

                <strong>
                  ${failed}
                </strong>
              </div>

            </div>


            <div class="outreach-account-last">

              <div>
                <span>
                  Last job
                </span>

                <strong>
                  ${escapeHtml(
                    account.last_job_code || "—"
                  )}
                </strong>
              </div>


              <div>
                <span>
                  Last used
                </span>

                <strong>
                  ${escapeHtml(
                    formatDate(
                      account.last_used_at
                    )
                  )}
                </strong>
              </div>


              <div>
                <span>
                  Last URL
                </span>

                ${
                  account.last_linkedin_url
                    ? `
                      <a
                        href="${escapeHtml(account.last_linkedin_url)}"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        ${escapeHtml(account.last_linkedin_url)}
                      </a>
                    `
                    : `
                      <strong>
                        —
                      </strong>
                    `
                }

              </div>

            </div>


            ${
              lastError
                ? `
                  <div class="outreach-target-error">
                    ${escapeHtml(lastError)}
                  </div>
                `
                : ""
            }

          </div>
        `;
      })
      .join("");
}


// ---------------------------------------------------------
// HISTORY
// ---------------------------------------------------------


function renderOutreachHistory(
  jobs
) {
  const rows = Array.isArray(jobs)
    ? jobs
    : [];

  if (
    !els.outreachHistoryEmpty ||
    !els.outreachHistoryTableWrap ||
    !els.outreachHistoryBody
  ) {
    return;
  }


  if (!rows.length) {
    els.outreachHistoryEmpty.hidden = false;
    els.outreachHistoryTableWrap.hidden = true;
    els.outreachHistoryBody.innerHTML = "";
    return;
  }


  els.outreachHistoryEmpty.hidden = true;
  els.outreachHistoryTableWrap.hidden = false;


  els.outreachHistoryBody.innerHTML =
    rows
      .map((job, index) => {
        const status = String(
          job.status || ""
        ).toLowerCase();

        const targets = Array.isArray(
          job.targets
        )
          ? job.targets
          : [];

        const detailId =
          `outreach-job-detail-${index}`;

        return `
          <tr class="outreach-history-main-row">

            <td>
              <strong>
                ${escapeHtml(
                  job.job_code || "—"
                )}
              </strong>

              <button
                type="button"
                class="outreach-history-expand"
                data-target="${detailId}"
              >
                ${targets.length} profiles
                <span>
                  ▾
                </span>
              </button>
            </td>

            <td>
              <span class="pill ${getOutreachPillClass(status)}">
                ${escapeHtml(
                  statusLabel(status)
                )}
              </span>
            </td>

            <td>
              ${Number(job.input_count || 0)}
            </td>

            <td>
              ${Number(job.target_count || 0)}
            </td>

            <td>
              ${Number(job.processed_count || 0)}
            </td>

            <td>
              ${Number(job.success_count || 0)}
            </td>

            <td>
              ${Number(job.failed_count || 0)}
            </td>

            <td>
              ${Number(job.duplicate_count || 0)}
            </td>

            <td>
              ${Number(job.invalid_count || 0)}
            </td>

            <td>
              ${escapeHtml(
                formatDate(job.created_at)
              )}
            </td>

          </tr>


          <tr
            id="${detailId}"
            class="outreach-history-detail-row"
            hidden
          >
            <td colspan="10">

              <div class="outreach-history-detail">

                <div class="outreach-history-detail-header">

                  <strong>
                    ${escapeHtml(
                      job.job_code || "—"
                    )}
                  </strong>

                  <span class="panel-meta">
                    ${targets.length} profiles
                  </span>

                </div>

                ${renderOutreachTargetRows(
                  targets
                )}

              </div>

            </td>
          </tr>
        `;
      })
      .join("");


  els.outreachHistoryBody
    .querySelectorAll(
      ".outreach-history-expand"
    )
    .forEach((button) => {
      button.addEventListener(
        "click",
        () => {
          const targetId =
            button.dataset.target;

          const detail =
            document.getElementById(
              targetId
            );

          if (!detail) {
            return;
          }

          const willOpen =
            detail.hidden;

          detail.hidden =
            !willOpen;

          button.classList.toggle(
            "is-open",
            willOpen
          );

          const arrow =
            button.querySelector(
              "span"
            );

          if (arrow) {
            arrow.textContent =
              willOpen
                ? "▴"
                : "▾";
          }
        }
      );
    });
}


// ---------------------------------------------------------
// FULL DASHBOARD RENDER
// ---------------------------------------------------------


function renderOutreachDashboard() {
  renderOutreachJob(
    state.outreachCurrentJob
  );

  renderOutreachScheduler(
    state.outreachScheduler
  );

  renderOutreachAccounts(
    state.outreachAccounts
  );

  renderOutreachHistory(
    state.outreachRecentJobs
  );

  if (els.outreachDashboardUpdatedAt) {
    els.outreachDashboardUpdatedAt.textContent =
      `Updated ${formatDate(
        new Date().toISOString()
      )}`;
  }
}


// ---------------------------------------------------------
// LOAD DASHBOARD
// ---------------------------------------------------------


async function loadOutreachDashboard() {
  if (state.outreachDashboardLoading) {
    return;
  }

  state.outreachDashboardLoading = true;

  try {
    const response = await fetch(
      "/api/outreach/dashboard",
      {
        method: "GET",
        headers: {
          "Accept": "application/json"
        },
        cache: "no-store"
      }
    );

    const result =
      await response.json();

    if (
      !response.ok ||
      !result.ok
    ) {
      throw new Error(
        result.detail ||
        result.error ||
        "Không thể load Outreach dashboard."
      );
    }


    const dashboard =
      result.dashboard || {};


    state.outreachCurrentJob =
      dashboard.current_job || null;

    state.outreachScheduler =
      dashboard.scheduler || null;

    state.outreachAccounts =
      Array.isArray(
        dashboard.accounts
      )
        ? dashboard.accounts
        : [];

    state.outreachRecentJobs =
      Array.isArray(
        dashboard.recent_jobs
      )
        ? dashboard.recent_jobs
        : [];


    if (els.outreachError) {
      els.outreachError.hidden = true;
      els.outreachError.textContent = "";
    }


    renderOutreachDashboard();

  } catch (error) {
    console.error(
      "Outreach dashboard error:",
      error
    );

    if (els.outreachError) {
      els.outreachError.hidden = false;

      els.outreachError.textContent =
        error.message || String(error);
    }

  } finally {
    state.outreachDashboardLoading = false;
  }
}


// ---------------------------------------------------------
// POLLING
// ---------------------------------------------------------


function startOutreachPolling() {
  if (state.outreachPollTimer) {
    return;
  }

  state.outreachPollTimer =
    window.setInterval(
      loadOutreachDashboard,
      OUTREACH_POLL_INTERVAL_MS
    );
}


// ---------------------------------------------------------
// CREATE CONNECT JOB
// ---------------------------------------------------------


async function createOutreachConnectJob(
  event
) {
  event.preventDefault();

  const urls =
    parseOutreachUrls();

  if (!urls.length) {
    window.alert(
      "Hãy nhập ít nhất một LinkedIn profile URL."
    );

    return;
  }


  state.outreachSubmitting = true;

  renderOutreachSubmittingState();


  if (els.outreachError) {
    els.outreachError.hidden = true;
    els.outreachError.textContent = "";
  }


  try {
    const response = await fetch(
      "/api/outreach/connect/jobs",
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json"
        },

        body: JSON.stringify({
          urls
        })
      }
    );


    const result =
      await response.json();


    if (
      !response.ok ||
      !result.ok
    ) {
      throw new Error(
        result.detail ||
        result.error ||
        "Không thể tạo Outreach Connect job."
      );
    }


    state.outreachCurrentJob =
      result.job || null;


    renderOutreachJob(
      state.outreachCurrentJob
    );


    if (els.outreachUrlInput) {
      els.outreachUrlInput.value =
        "";
    }


    updateOutreachDetectedCount();


    // Load lại ngay từ DB.
    // Không cần chờ poll 3 giây.
    await loadOutreachDashboard();


  } catch (error) {
    if (els.outreachError) {
      els.outreachError.hidden = false;

      els.outreachError.textContent =
        error.message || String(error);
    }

  } finally {
    state.outreachSubmitting = false;

    renderOutreachSubmittingState();
  }
}

function updateYoutubePolling() {
  const status = normaliseStatus(
    state.activeYoutubeJob?.status
  );
  const shouldPoll =
    status === "pending" ||
    status === "processing";

  if (shouldPoll && !state.youtubePollTimer) {
    state.youtubePollTimer = window.setInterval(
      loadYoutubeResearch,
      2000
    );
  }

  if (!shouldPoll && state.youtubePollTimer) {
    window.clearInterval(state.youtubePollTimer);
    state.youtubePollTimer = null;
  }
}


function scheduleYoutubeRealtimeReload() {
  if (state.youtubeRealtimeReloadTimer) {
    window.clearTimeout(
      state.youtubeRealtimeReloadTimer
    );
  }

  state.youtubeRealtimeReloadTimer = window.setTimeout(
    async () => {
      state.youtubeRealtimeReloadTimer = null;
      await loadYoutubeResearch();
    },
    250
  );
}

function setupYoutubeRealtime() {
  if (state.youtubeRealtimeChannel) {
    client.removeChannel(
      state.youtubeRealtimeChannel
    );
  }

  state.youtubeRealtimeChannel = client
    .channel("youtube-research-dashboard")
    .on(
      "postgres_changes",
      {
        event: "*",
        schema: "public",
        table: "youtube_scan_jobs"
      },
      scheduleYoutubeRealtimeReload
    )
    .on(
      "postgres_changes",
      {
        event: "*",
        schema: "public",
        table: "youtube_scan_channels"
      },
      scheduleYoutubeRealtimeReload
    )
    .subscribe((status) => {
      if (status === "CHANNEL_ERROR") {
        console.warn(
          "YouTube Supabase realtime channel error. " +
          "Polling fallback remains active."
        );
      }
    });
}


async function loadDashboard() {
  els.refreshButton.disabled = true;
  els.refreshButton.querySelector(".button-icon").textContent = "…";
  els.globalError.hidden = true;
  state.tableErrors = {};

  const profileQuery = client
    .from("linkedin_profile_snapshots")
    .select(
      [
        "id",
        "source_id",
        "scraped_at",
        "name",
        "linkedin_url",
        "headline",
        "location",
        "followers_count_text",
        "connections_count_text",
        "about_text",
        "experience_raw_text",
        "post_1_caption",
        "post_2_caption",
        "post_3_caption",
        "post_4_caption",
        "post_5_caption"
      ].join(",")
    )
    .not("name", "is", null)
    .order("scraped_at", { ascending: false })
    .limit(1000);

  const sourceQuery = client
    .from("linkedin_sources")
    .select(
      [
        "id",
        "name",
        "linkedin_url",
        "source_type",
        "enabled",
        "job_status",
        "assigned_account_id",
        "processing_started_at",
        "processing_heartbeat_at",
        "retry_count",
        "last_error",
        "last_scanned_at",
        "completed_at",
        "lark_chat_id",
        "lark_result_sent_at",
        "lark_result_error"
      ].join(",")
    )
    .order("id", { ascending: false })
    .limit(2000);

  const accountQuery = client
    .from("linkedin_scanner_accounts")
    .select(
      [
        "account_id",
        "display_name",
        "profile_directory",
        "enabled",
        "status",
        "current_source_id",
        "batch_processed_count",
        "consecutive_failures",
        "cooldown_until",
        "last_used_at",
        "last_success_at",
        "last_error_at",
        "last_error",
        "updated_at"
      ].join(",")
    )
    .order("account_id", { ascending: true });

  const workerQuery = client
    .from("linkedin_worker_health")
    .select(
      [
        "worker_id",
        "worker_name",
        "status",
        "worker_version",
        "hostname",
        "pid",
        "current_account_id",
        "current_source_id",
        "last_heartbeat_at",
        "started_at",
        "last_batch_started_at",
        "last_batch_completed_at",
        "last_success_at",
        "last_error_at",
        "last_error",
        "updated_at"
      ].join(",")
    )
    .order("last_heartbeat_at", { ascending: false })
    .limit(1);

  const [
    profiles,
    sources,
    accounts,
    workers
  ] = await Promise.all([
    safeQuery("profiles", profileQuery, []),
    safeQuery("sources", sourceQuery, []),
    safeQuery("accounts", accountQuery, []),
    safeQuery("worker", workerQuery, [])
  ]);

  state.profiles = getLatestSnapshots(profiles || []);
  state.sources = sources || [];
  state.accounts = accounts || [];
  state.worker = workers?.[0] || null;

  els.refreshButton.disabled = false;
  els.refreshButton.querySelector(".button-icon").textContent = "↻";

  renderAll();
  await loadYoutubeResearch();
}

function renderAll() {
  updateStats();
  applyProfileFilters();
  applyQueueFilters();
  renderOverview();
  renderAccounts();
  renderHealth();
  renderGlobalError();
  updateWorkerControlButtons();
}

function updateStats() {
  const latestDate = state.profiles
    .map((profile) => profile.scraped_at)
    .filter(Boolean)
    .sort()
    .at(-1);

  els.totalProfiles.textContent =
    state.profiles.length.toLocaleString("vi-VN");

  els.pendingCount.textContent =
    countByStatus("pending").toLocaleString("vi-VN");

  els.processingCount.textContent =
    countByStatus("processing").toLocaleString("vi-VN");

  els.completedCount.textContent =
    countByStatus("completed").toLocaleString("vi-VN");

  els.failedCount.textContent =
    countByStatus("failed").toLocaleString("vi-VN");

  els.profilesTabCount.textContent =
    state.profiles.length.toLocaleString("vi-VN");

  els.queueTabCount.textContent =
    state.sources.length.toLocaleString("vi-VN");

  els.lastUpdated.textContent =
    latestDate
      ? `Snapshot gần nhất: ${formatAge(latestDate)}`
      : "Chưa có snapshot";
}

function renderGlobalError() {
  const entries = Object.entries(state.tableErrors);

  if (!entries.length) {
    els.globalError.hidden = true;
    return;
  }

  els.globalError.innerHTML = `
    <strong>Một số nguồn dữ liệu chưa đọc được.</strong><br />
    ${entries
      .map(
        ([name, message]) =>
          `${escapeHtml(name)}: ${escapeHtml(message)}`
      )
      .join("<br />")}
  `;

  els.globalError.hidden = false;
}

function applyProfileFilters() {
  const query = els.searchInput.value
    .trim()
    .toLowerCase();

  const sort = els.sortSelect.value;

  const filtered = state.profiles.filter((profile) => {
    const searchable = [
      profile.name,
      profile.headline,
      profile.location,
      profile.linkedin_url,
      ...getPostCaptions(profile)
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();

    return !query || searchable.includes(query);
  });

  filtered.sort((a, b) => {
    if (sort === "name") {
      return (a.name || "").localeCompare(
        b.name || "",
        "vi"
      );
    }

    const first = new Date(a.scraped_at || 0).getTime();
    const second = new Date(b.scraped_at || 0).getTime();

    return sort === "oldest"
      ? first - second
      : second - first;
  });

  state.filteredProfiles = filtered;

  renderProfileTable();
}

function renderProfileTable() {
  const profiles = state.filteredProfiles;

  els.resultSummary.textContent =
    `${profiles.length.toLocaleString("vi-VN")} profiles`;

  els.emptyState.hidden = profiles.length > 0;
  els.tableWrap.hidden = profiles.length === 0;

  els.profileTableBody.innerHTML = profiles
    .map((profile) => {
      const postCount = getPostCaptions(profile).length;

      return `
        <tr>
          <td>
            <div class="profile-cell">
              <div class="avatar">
                ${escapeHtml(getInitials(profile.name))}
              </div>

              <div class="profile-copy">
                <p class="profile-name">
                  ${escapeHtml(profile.name)}
                </p>

                <p class="profile-headline">
                  ${escapeHtml(
                    profile.headline || "Không có headline"
                  )}
                </p>
              </div>
            </div>
          </td>

          <td>
            ${escapeHtml(profile.location || "—")}
          </td>

          <td>
            ${escapeHtml(
              profile.followers_count_text || "—"
            )}
          </td>

          <td>
            ${escapeHtml(
              profile.connections_count_text || "—"
            )}
          </td>

          <td>
            <span class="post-count-badge">
              ${postCount}
            </span>
          </td>

          <td class="muted-cell">
            ${escapeHtml(formatDate(profile.scraped_at))}
          </td>

          <td class="action-cell">
            <button
              class="row-button"
              type="button"
              data-profile-id="${escapeHtml(profile.id)}"
              aria-label="Xem ${escapeHtml(profile.name)}"
            >
              ⋯
            </button>
          </td>
        </tr>
      `;
    })
    .join("");

  els.profileTableBody
    .querySelectorAll("[data-profile-id]")
    .forEach((button) => {
      button.addEventListener("click", () => {
        const profile = state.profiles.find(
          (item) =>
            String(item.id) ===
            String(button.dataset.profileId)
        );

        if (profile) {
          openDrawer(profile);
        }
      });
    });
}

function applyQueueFilters() {
  const query = els.queueSearchInput.value
    .trim()
    .toLowerCase();

  const filter = els.queueStatusFilter.value;

  state.filteredSources = state.sources.filter((source) => {
    const status = normaliseStatus(source.job_status);

    const matchesStatus =
      filter === "all" || status === filter;

    const searchable = [
      source.name,
      source.linkedin_url,
      source.assigned_account_id,
      source.job_status,
      source.last_error
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();

    return (
      matchesStatus &&
      (!query || searchable.includes(query))
    );
  });

  renderQueueTable();
}

function renderQueueTable() {
  const sources = state.filteredSources;

  els.queueSummary.textContent =
    `${sources.length.toLocaleString("vi-VN")} sources`;

  els.queueEmptyState.hidden = sources.length > 0;
  els.queueTableWrap.hidden = sources.length === 0;

  els.queueTableBody.innerHTML = sources
    .map((source) => {
      const sourceName =
        source.name ||
        `Source #${source.id}`;

      return `
        <tr>
          <td>
            <div class="queue-source">
              <strong>${escapeHtml(sourceName)}</strong>
              <span>${escapeHtml(source.linkedin_url || "—")}</span>
            </div>
          </td>

          <td>
            ${statusBadge(source.job_status)}
          </td>

          <td>
            ${escapeHtml(source.assigned_account_id || "—")}
          </td>

          <td>
            ${Number(source.retry_count || 0)}
          </td>

          <td class="muted-cell">
            ${escapeHtml(formatDate(source.processing_started_at))}
          </td>

          <td class="muted-cell">
            ${escapeHtml(formatDate(source.last_scanned_at))}
          </td>
        </tr>
      `;
    })
    .join("");
}

function getCurrentSource() {
  if (!state.worker?.current_source_id) {
    return null;
  }

  return state.sources.find(
    (source) =>
      String(source.id) ===
      String(state.worker.current_source_id)
  ) || null;
}

function renderOverview() {
  renderActiveProcess();
  renderOverviewAccounts();
  renderTimeline();
}

function renderActiveProcess() {
  const worker = state.worker;
  const source = getCurrentSource();

  if (!worker) {
    els.activeProcessBadge.className =
      "pill pill-red";
    els.activeProcessBadge.textContent =
      "Worker chưa đăng ký";

    els.activeProcessContent.innerHTML = `
      <div class="empty-process">
        Chưa có dữ liệu worker trong linkedin_worker_health.
      </div>
    `;

    return;
  }

  const workerStatus = normaliseStatus(worker.status);

  els.activeProcessBadge.className =
    `pill ${
      workerStatus === "scanning"
        ? "pill-purple"
        : workerStatus === "idle"
          ? "pill-green"
          : "pill-amber"
    }`;

  els.activeProcessBadge.textContent =
    statusLabel(workerStatus);

  if (!source) {
    els.activeProcessContent.innerHTML = `
      <div class="active-process-card">
        <div class="active-process-title">
          <div>
            <h3>
              ${escapeHtml(
                worker.worker_name || worker.worker_id || "Mac Worker"
              )}
            </h3>
            <p class="process-url">
              Không có source đang được xử lý.
            </p>
          </div>

          ${statusBadge(worker.status)}
        </div>

        <p class="process-step">
          ${
            workerStatus === "idle"
              ? "Worker đang chờ URL mới."
              : "Worker chưa gắn current_source_id."
          }
        </p>

        <div class="active-process-footer">
          <span>
            Current account:
            ${escapeHtml(worker.current_account_id || "—")}
          </span>

          <span>
            Heartbeat ${escapeHtml(formatAge(worker.last_heartbeat_at))}
          </span>
        </div>
      </div>
    `;

    return;
  }

  const progress =
    normaliseStatus(source.job_status) === "completed"
      ? 100
      : 62;

  els.activeProcessContent.innerHTML = `
    <div class="active-process-card">
      <div class="active-process-title">
        <div>
          <h3>
            ${escapeHtml(source.name || `Source #${source.id}`)}
          </h3>

          <p class="process-url">
            ${escapeHtml(source.linkedin_url || "—")}
          </p>
        </div>

        ${statusBadge(source.job_status)}
      </div>

      <p class="process-step">
        ${
          normaliseStatus(source.job_status) === "processing"
            ? "Worker đang scan profile và cập nhật snapshot."
            : "Đang đồng bộ trạng thái source."
        }
      </p>

      <div class="process-progress">
        <div
          class="process-progress-bar"
          style="width: ${progress}%"
        ></div>
      </div>

      <div class="active-process-footer">
        <span>
          ${escapeHtml(
            source.assigned_account_id ||
            worker.current_account_id ||
            "Chưa assign account"
          )}
        </span>

        <span>
          Heartbeat ${escapeHtml(formatAge(worker.last_heartbeat_at))}
        </span>
      </div>
    </div>
  `;
}

function renderOverviewAccounts() {
  const enabledAccounts = state.accounts.filter(
    (account) => account.enabled !== false
  );

  const readyCount = enabledAccounts.filter(
    (account) =>
      ["available", "idle"].includes(
        normaliseStatus(account.status)
      )
  ).length;

  els.readyAccountSummary.textContent =
    `${readyCount}/${enabledAccounts.length || 0} ready`;

  if (!state.accounts.length) {
    els.overviewAccountList.innerHTML = `
      <div class="empty-process">
        Chưa đọc được linkedin_scanner_accounts.
      </div>
    `;
    return;
  }

  els.overviewAccountList.innerHTML = state.accounts
    .slice(0, 5)
    .map((account) => `
      <div class="compact-account-row">
        <div class="compact-account-copy">
          <strong>${escapeHtml(account.account_id)}</strong>
          <span>
            ${
              account.current_source_id
                ? `Source #${escapeHtml(account.current_source_id)}`
                : account.last_error
                  ? escapeHtml(account.last_error)
                  : "Không có source hiện tại"
            }
          </span>
        </div>

        ${statusBadge(account.status)}
      </div>
    `)
    .join("");
}

function renderTimeline() {
  const entries = [];

  if (state.worker) {
    entries.push({
      type:
        normaliseStatus(state.worker.status) === "error"
          ? "error"
          : "processing",
      icon: "W",
      title: `Worker ${statusLabel(state.worker.status)}`,
      description:
        state.worker.current_source_id
          ? `Đang xử lý source #${state.worker.current_source_id}`
          : "Không có source hiện tại",
      time: formatAge(state.worker.last_heartbeat_at)
    });
  }

  state.sources
    .filter((source) => source.last_scanned_at)
    .slice(0, 4)
    .forEach((source) => {
      entries.push({
        type:
          normaliseStatus(source.job_status) === "failed"
            ? "error"
            : "success",
        icon:
          normaliseStatus(source.job_status) === "failed"
            ? "!"
            : "✓",
        title:
          normaliseStatus(source.job_status) === "failed"
            ? "Source scan thất bại"
            : "Snapshot đã hoàn thành",
        description:
          source.name ||
          source.linkedin_url ||
          `Source #${source.id}`,
        time: formatAge(source.last_scanned_at)
      });
    });

  if (!entries.length) {
    els.activityTimeline.innerHTML = `
      <div class="empty-process">
        Chưa có hoạt động để hiển thị.
      </div>
    `;
    return;
  }

  els.activityTimeline.innerHTML = entries
    .map((entry) => `
      <div class="activity-entry is-${entry.type}">
        <div class="activity-dot">${entry.icon}</div>

        <div class="activity-entry-main">
          <div class="activity-entry-copy">
            <strong>${escapeHtml(entry.title)}</strong>
            <span>${escapeHtml(entry.description)}</span>
          </div>

          <span class="activity-time">
            ${escapeHtml(entry.time)}
          </span>
        </div>
      </div>
    `)
    .join("");
}

function renderAccounts() {
  if (!state.accounts.length) {
    els.accountsGrid.innerHTML = `
      <div class="panel">
        <div class="empty-process">
          Không có dữ liệu account hoặc anon key chưa có quyền đọc bảng.
        </div>
      </div>
    `;
    return;
  }

  els.accountsGrid.innerHTML = state.accounts
    .map((account, index) => `
      <article class="account-card">
        <div class="account-card-header">
          <div class="account-title">
            <div class="account-index">
              ${String(index + 1).padStart(2, "0")}
            </div>

            <div>
              <strong>${escapeHtml(account.account_id)}</strong>
              <span>
                ${escapeHtml(
                  account.display_name || "Persistent browser session"
                )}
              </span>
            </div>
          </div>

          ${statusBadge(account.status)}
        </div>

        <div class="account-detail-list">
          <div class="account-detail-row">
            <span>Current source</span>
            <strong>
              ${
                account.current_source_id
                  ? `#${escapeHtml(account.current_source_id)}`
                  : "—"
              }
            </strong>
          </div>

          <div class="account-detail-row">
            <span>Batch processed</span>
            <strong>
              ${Number(account.batch_processed_count || 0)}
            </strong>
          </div>

          <div class="account-detail-row">
            <span>Consecutive failures</span>
            <strong>
              ${Number(account.consecutive_failures || 0)}
            </strong>
          </div>

          <div class="account-detail-row">
            <span>Last success</span>
            <strong>
              ${escapeHtml(formatAge(account.last_success_at))}
            </strong>
          </div>

          <div class="account-detail-row">
            <span>Last error</span>
            <strong>
              ${escapeHtml(account.last_error || "—")}
            </strong>
          </div>
        </div>
      </article>
    `)
    .join("");
}

function renderHealth() {
  const worker = state.worker;
  const heartbeatAgeSeconds = worker?.last_heartbeat_at
    ? Math.max(
        0,
        Math.floor(
          (Date.now() - new Date(worker.last_heartbeat_at).getTime()) /
          1000
        )
      )
    : null;

  const workerOnline =
    heartbeatAgeSeconds !== null &&
    heartbeatAgeSeconds <= 90 &&
    !["offline", "stopping"].includes(
      normaliseStatus(worker?.status)
    );

  const needsLoginCount = state.accounts.filter(
    (account) =>
      normaliseStatus(account.status) === "needs_login"
  ).length;

  const staleJobs = state.sources.filter((source) => {
    if (normaliseStatus(source.job_status) !== "processing") {
      return false;
    }

    const heartbeat =
      source.processing_heartbeat_at ||
      source.processing_started_at;

    if (!heartbeat) return true;

    return (
      Date.now() - new Date(heartbeat).getTime() >
      20 * 60 * 1000
    );
  }).length;

  const unsentLark = state.sources.filter(
    (source) =>
      source.lark_chat_id &&
      source.last_scanned_at &&
      !source.lark_result_sent_at
  ).length;

  let overall = "HEALTHY";

  if (
    !workerOnline ||
    state.tableErrors.sources ||
    state.tableErrors.worker
  ) {
    overall = "UNHEALTHY";
  } else if (
    needsLoginCount > 0 ||
    staleJobs > 0 ||
    unsentLark > 0 ||
    countByStatus("failed") > 0
  ) {
    overall = "DEGRADED";
  }

  const overallClass =
    overall === "HEALTHY"
      ? "pill-green"
      : overall === "DEGRADED"
        ? "pill-amber"
        : "pill-red";

  els.healthOverallBadge.className =
    `pill ${overallClass}`;
  els.healthOverallBadge.textContent = overall;

  els.systemBadge.className =
    `system-badge ${
      overall === "HEALTHY"
        ? "is-healthy"
        : overall === "DEGRADED"
          ? "is-degraded"
          : "is-unhealthy"
    }`;

  els.systemBadgeText.textContent =
    overall === "HEALTHY"
      ? "System healthy"
      : overall === "DEGRADED"
        ? "System degraded"
        : "System unhealthy";

  const services = [
    {
      name: "Supabase profiles",
      detail:
        state.tableErrors.profiles ||
        `${state.profiles.length} profiles`,
      healthy: !state.tableErrors.profiles
    },
    {
      name: "Supabase queue",
      detail:
        state.tableErrors.sources ||
        `${state.sources.length} sources`,
      healthy: !state.tableErrors.sources
    },
    {
      name: "Mac Worker",
      detail:
        worker
          ? `${statusLabel(worker.status)} · ${formatAge(worker.last_heartbeat_at)}`
          : "Không có worker record",
      healthy: workerOnline
    },
    {
      name: "LinkedIn accounts",
      detail:
        state.tableErrors.accounts ||
        `${state.accounts.length} accounts · ${needsLoginCount} needs login`,
      healthy:
        !state.tableErrors.accounts &&
        needsLoginCount === 0
    },
    {
      name: "Lark delivery",
      detail: `${unsentLark} kết quả chưa gửi`,
      healthy: unsentLark === 0
    }
  ];

  els.healthServiceList.innerHTML = services
    .map((service) => `
      <div class="health-service-row">
        <div class="health-service-copy">
          <strong>${escapeHtml(service.name)}</strong>
          <span>${escapeHtml(service.detail)}</span>
        </div>

        <span class="status-badge ${
          service.healthy
            ? "status-available"
            : "status-error"
        }">
          ${service.healthy ? "Healthy" : "Issue"}
        </span>
      </div>
    `)
    .join("");

  els.workerDetailGrid.innerHTML = `
    <dt>Worker ID</dt>
    <dd>${escapeHtml(worker?.worker_id || "—")}</dd>

    <dt>Status</dt>
    <dd>${escapeHtml(statusLabel(worker?.status))}</dd>

    <dt>Version</dt>
    <dd>${escapeHtml(worker?.worker_version || "—")}</dd>

    <dt>Hostname</dt>
    <dd>${escapeHtml(worker?.hostname || "—")}</dd>

    <dt>Current account</dt>
    <dd>${escapeHtml(worker?.current_account_id || "—")}</dd>

    <dt>Current source</dt>
    <dd>${escapeHtml(worker?.current_source_id || "—")}</dd>

    <dt>Last heartbeat</dt>
    <dd>${escapeHtml(formatDate(worker?.last_heartbeat_at))}</dd>

    <dt>Last success</dt>
    <dd>${escapeHtml(formatDate(worker?.last_success_at))}</dd>

    <dt>Last error</dt>
    <dd>${escapeHtml(worker?.last_error || "—")}</dd>
  `;

  els.healthHeartbeatAge.textContent =
    heartbeatAgeSeconds === null
      ? "—"
      : formatAge(worker.last_heartbeat_at);

  els.healthStaleJobs.textContent =
    staleJobs.toLocaleString("vi-VN");

  els.healthUnsentLark.textContent =
    unsentLark.toLocaleString("vi-VN");

  els.healthNeedsLogin.textContent =
    needsLoginCount.toLocaleString("vi-VN");
}

function openDrawer(profile) {
  els.drawerName.textContent =
    profile.name || "Chưa có tên";

  const linkedInBlock = profile.linkedin_url
    ? `
      <a
        class="detail-link"
        href="${escapeHtml(profile.linkedin_url)}"
        target="_blank"
        rel="noreferrer"
      >
        Mở LinkedIn profile
      </a>
    `
    : `
      <p>Không có LinkedIn URL.</p>
    `;

  const postCaptions = getPostCaptions(profile);

  const recentPostsBlock = postCaptions.length
    ? `
      <div class="recent-posts-list">
        ${postCaptions
          .map(
            (caption, index) => `
              <article class="recent-post-card">
                <div class="recent-post-meta">
                  <span>Post ${index + 1}</span>
                </div>

                <p>${escapeHtml(caption)}</p>
              </article>
            `
          )
          .join("")}
      </div>
    `
    : `
      <p class="detail-empty">
        Không có bài viết trong 30 ngày gần nhất.
      </p>
    `;

  els.drawerContent.innerHTML = `
    <section class="detail-section">
      <h3>Thông tin chính</h3>

      <dl class="detail-grid">
        <dt>Headline</dt>
        <dd>${escapeHtml(profile.headline || "—")}</dd>

        <dt>Location</dt>
        <dd>${escapeHtml(profile.location || "—")}</dd>

        <dt>Followers</dt>
        <dd>
          ${escapeHtml(profile.followers_count_text || "—")}
        </dd>

        <dt>Connections</dt>
        <dd>
          ${escapeHtml(profile.connections_count_text || "—")}
        </dd>

        <dt>Posts</dt>
        <dd>${postCaptions.length}</dd>

        <dt>Last scan</dt>
        <dd>${escapeHtml(formatDate(profile.scraped_at))}</dd>
      </dl>
    </section>

    <section class="detail-section">
      <h3>LinkedIn</h3>
      ${linkedInBlock}
    </section>

    <section class="detail-section">
      <h3>About</h3>

      <p class="detail-pre">
        ${escapeHtml(
          profile.about_text ||
          "Không có dữ liệu About."
        )}
      </p>
    </section>

    <section class="detail-section">
      <div class="detail-section-heading">
        <h3>Recent posts</h3>

        <span class="detail-count">
          ${postCaptions.length}
        </span>
      </div>

      ${recentPostsBlock}
    </section>

    <section class="detail-section">
      <h3>Experience</h3>

      <p class="detail-pre">
        ${escapeHtml(
          profile.experience_raw_text ||
          "Không có dữ liệu Experience."
        )}
      </p>
    </section>
  `;

  els.drawerBackdrop.hidden = false;
  els.detailDrawer.classList.add("is-open");
  els.detailDrawer.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
}

function closeDrawer() {
  els.drawerBackdrop.hidden = true;
  els.detailDrawer.classList.remove("is-open");
  els.detailDrawer.setAttribute("aria-hidden", "true");
  document.body.style.overflow = "";
}

function switchTab(tabName) {
  document
    .querySelectorAll(".tab-button")
    .forEach((button) => {
      button.classList.toggle(
        "is-active",
        button.dataset.tab === tabName
      );
    });

  document
    .querySelectorAll(".tab-panel")
    .forEach((panel) => {
      panel.hidden =
        panel.id !== `tab-${tabName}`;
    });
}

document
  .querySelectorAll(".tab-button")
  .forEach((button) => {
    button.addEventListener("click", () => {
      switchTab(button.dataset.tab);

      if (button.dataset.tab === "youtube") {
        loadYoutubeResearch();
      }
    });
  });

els.killProcessButton?.addEventListener(
  "click",
  async () => {
    try {
      await sendWorkerCommand("kill_current");
    } catch (error) {
      window.alert(error.message || String(error));
    }
  }
);

els.stopScanButton?.addEventListener(
  "click",
  async () => {
    try {
      const command =
        normaliseStatus(state.worker?.status) === "paused"
          ? "resume_scan"
          : "stop_scan";

      await sendWorkerCommand(command);
    } catch (error) {
      window.alert(error.message || String(error));
    }
  }
);

els.refreshButton?.addEventListener(
  "click",
  loadDashboard
);

els.searchInput?.addEventListener(
  "input",
  applyProfileFilters
);

els.sortSelect?.addEventListener(
  "change",
  applyProfileFilters
);

els.queueSearchInput?.addEventListener(
  "input",
  applyQueueFilters
);

els.queueStatusFilter?.addEventListener(
  "change",
  applyQueueFilters
);

els.youtubeResearchForm?.addEventListener(
  "submit",
  createYoutubeResearchJob
);

els.outreachConnectForm?.addEventListener(
  "submit",
  createOutreachConnectJob
);

els.outreachUrlInput?.addEventListener(
  "input",
  updateOutreachDetectedCount
);

els.youtubeSearchInput?.addEventListener(
  "input",
  renderYoutubeResearch
);

[
  els.youtubeKeywordFilter,
  els.youtubeLocationFilter,
  els.youtubeEmailFilter,
  els.youtubeSubscriberFilter,
  els.youtubeSortSelect
]
  .filter(Boolean)
  .forEach((element) => {
    element.addEventListener(
      "change",
      renderYoutubeResearch
    );
  });

if (els.outreachCurrentTargetsToggle) {
  els.outreachCurrentTargetsToggle.addEventListener(
    "click",
    () => {
      if (!els.outreachCurrentTargets) {
        return;
      }

      const willOpen =
        els.outreachCurrentTargets.hidden;

      els.outreachCurrentTargets.hidden =
        !willOpen;

      if (els.outreachCurrentTargetsArrow) {
        els.outreachCurrentTargetsArrow.textContent =
          willOpen
            ? "▴"
            : "▾";
      }
    }
  );
}

els.closeDrawerButton?.addEventListener(
  "click",
  closeDrawer
);

els.drawerBackdrop?.addEventListener(
  "click",
  closeDrawer
);

document.addEventListener(
  "keydown",
  (event) => {
    if (event.key === "Escape") {
      closeDrawer();
    }
  }
);

updateOutreachDetectedCount();

renderOutreachDashboard();

renderOutreachSubmittingState();

setupYoutubeRealtime();

loadOutreachDashboard();

startOutreachPolling();

loadDashboard();
