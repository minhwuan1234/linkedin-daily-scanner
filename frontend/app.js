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

  rateLimitAccountCardTemplate:
    document.querySelector("#rateLimitAccountCardTemplate"),

  rateLimitDrawerButton:
    document.querySelector("#rateLimitDrawerButton"),

  rateLimitSidebarBadge:
    document.querySelector("#rateLimitSidebarBadge"),

  rateLimitDrawer:
    document.querySelector("#rateLimitDrawer"),

  rateLimitDrawerBackdrop:
    document.querySelector("#rateLimitDrawerBackdrop"),

  rateLimitDrawerClose:
    document.querySelector("#rateLimitDrawerClose"),

  outreachDashboardUpdatedAt:
    document.querySelector("#outreachDashboardUpdatedAt"),

  outreachHistoryEmpty:
    document.querySelector("#outreachHistoryEmpty"),

  outreachHistoryTableWrap:
    document.querySelector("#outreachHistoryTableWrap"),

  outreachHistoryBody:
    document.querySelector("#outreachHistoryBody"),

  outreachHistoryRowTemplate:
    document.querySelector("#outreachHistoryRowTemplate"),

  outreachHistoryCount:
    document.querySelector("#outreachHistoryCount"),

  outreachHistoryPagination:
    document.querySelector("#outreachHistoryPagination"),

  outreachHistoryPageMeta:
    document.querySelector("#outreachHistoryPageMeta"),

  outreachHistoryPrevPage:
    document.querySelector("#outreachHistoryPrevPage"),

  outreachHistoryNextPage:
    document.querySelector("#outreachHistoryNextPage"),

  outreachAcceptanceJobCount:
    document.querySelector("#outreachAcceptanceJobCount"),

  outreachAcceptanceEmpty:
    document.querySelector("#outreachAcceptanceEmpty"),

  outreachAcceptanceTableWrap:
    document.querySelector("#outreachAcceptanceTableWrap"),

  outreachAcceptanceBody:
    document.querySelector("#outreachAcceptanceBody"),

  outreachAcceptanceRowTemplate:
    document.querySelector("#outreachAcceptanceRowTemplate"),

  outreachAcceptancePagination:
    document.querySelector("#outreachAcceptancePagination"),

  outreachAcceptancePageMeta:
    document.querySelector("#outreachAcceptancePageMeta"),

  outreachAcceptancePrevPage:
    document.querySelector("#outreachAcceptancePrevPage"),

  outreachAcceptanceNextPage:
    document.querySelector("#outreachAcceptanceNextPage"),


  outreachAcceptedPoolPanel:
    document.querySelector("#outreachAcceptedPoolPanel"),

  outreachAcceptedPoolSummary:
    document.querySelector("#outreachAcceptedPoolSummary"),

  outreachAcceptedPoolEmpty:
    document.querySelector("#outreachAcceptedPoolEmpty"),

  outreachAcceptedPoolTableWrap:
    document.querySelector("#outreachAcceptedPoolTableWrap"),

  outreachAcceptedPoolBody:
    document.querySelector("#outreachAcceptedPoolBody"),

  outreachAcceptedPoolRowTemplate:
    document.querySelector("#outreachAcceptedPoolRowTemplate"),

  outreachAcceptedSelectedCount:
    document.querySelector("#outreachAcceptedSelectedCount"),

  outreachAcceptedAccountFilter:
    document.querySelector("#outreachAcceptedAccountFilter"),

  outreachAcceptedSelectPage:
    document.querySelector("#outreachAcceptedSelectPage"),

  outreachAcceptedPagination:
    document.querySelector("#outreachAcceptedPagination"),

  outreachAcceptedPageMeta:
    document.querySelector("#outreachAcceptedPageMeta"),

  outreachAcceptedPrevPage:
    document.querySelector("#outreachAcceptedPrevPage"),

  outreachAcceptedNextPage:
    document.querySelector("#outreachAcceptedNextPage"),

  messagePreparationCount:
    document.querySelector("#messagePreparationCount"),

  messagePreparationHeadline:
    document.querySelector("#messagePreparationHeadline"),

  messagePreparationMeta:
    document.querySelector("#messagePreparationMeta"),

  messagePrepareSelectedButton:
    document.querySelector("#messagePrepareSelectedButton"),

  messagePrepareAllButton:
    document.querySelector("#messagePrepareAllButton"),

  messagePrepareConfirmModal:
    document.querySelector("#messagePrepareConfirmModal"),

  messagePrepareConfirmTitle:
    document.querySelector("#messagePrepareConfirmTitle"),

  messagePrepareConfirmMeta:
    document.querySelector("#messagePrepareConfirmMeta"),

  messagePrepareConfirmError:
    document.querySelector("#messagePrepareConfirmError"),

  messagePrepareConfirmCloseButton:
    document.querySelector("#messagePrepareConfirmCloseButton"),

  messagePrepareConfirmCancelButton:
    document.querySelector("#messagePrepareConfirmCancelButton"),

  messagePrepareConfirmButton:
    document.querySelector("#messagePrepareConfirmButton"),

  messagePreparationError:
    document.querySelector("#messagePreparationError"),

  messageBatchCount:
    document.querySelector("#messageBatchCount"),

  messageBatchEmpty:
    document.querySelector("#messageBatchEmpty"),

  messageBatchList:
    document.querySelector("#messageBatchList"),

  messageBatchPagination:
    document.querySelector("#messageBatchPagination"),

  messageBatchPageMeta:
    document.querySelector("#messageBatchPageMeta"),

  messageBatchPrevPage:
    document.querySelector("#messageBatchPrevPage"),

  messageBatchNextPage:
    document.querySelector("#messageBatchNextPage"),


  messageBatchRowTemplate:
    document.querySelector("#messageBatchRowTemplate"),

  messageSendModal:
    document.querySelector("#messageSendModal"),

  messageSendDialogMeta:
    document.querySelector("#messageSendDialogMeta"),

  messageTemplateInput:
    document.querySelector("#messageTemplateInput"),

  messageSendError:
    document.querySelector("#messageSendError"),

  messageSendCloseButton:
    document.querySelector("#messageSendCloseButton"),

  messageSendCancelButton:
    document.querySelector("#messageSendCancelButton"),

  messageSendConfirmButton:
    document.querySelector("#messageSendConfirmButton"),

  pageEyebrow:
    document.querySelector("#pageEyebrow"),

  pageTitle:
    document.querySelector("#pageTitle"),

  pageSubtitle:
    document.querySelector("#pageSubtitle"),

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
  outreachProcessTab: "connect",
  outreachHistoryPage: 1,
  outreachHistoryPageSize: 5,
  outreachAcceptancePage: 1,
  outreachAcceptancePageSize: 10,
  messageBatchPage: 1,
  messageBatchPageSize: 8,
  outreachPollTimer: null,
  outreachDashboardLoading: false,
  outreachAcceptanceSubmittingJobIds: new Set(),
  outreachAcceptedPool: {
    summary: {
      total: 0,
      not_sent: 0,
      sent: 0
    },
    items: []
  },
  outreachAcceptedPoolFilter: "all",
  outreachAcceptedAccountFilter: "all",
  outreachAcceptedPoolPage: 1,
  outreachAcceptedPoolPageSize: 15,
  outreachAcceptedSelectedProspectIds: new Set(),
  messagePreparation: {
    count: 0,
    items: []
  },
  messageBatches: [],
  messagePreparationSubmitting: false,
  messagePreparationSelectedSubmitting: false,
  messagePrepareConfirmMode: null,
  messageBatchQueueSubmittingIds: new Set(),
  messageSendSelectedBatchId: null,
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


function openRateLimitDrawer() {
  if (!els.rateLimitDrawer) {
    return;
  }

  els.rateLimitDrawer.classList.add(
    "is-open"
  );

  els.rateLimitDrawer.setAttribute(
    "aria-hidden",
    "false"
  );

  els.rateLimitDrawerButton?.setAttribute(
    "aria-expanded",
    "true"
  );

  document.body.classList.add(
    "has-rate-limit-drawer-open"
  );
}


function closeRateLimitDrawer() {
  if (!els.rateLimitDrawer) {
    return;
  }

  els.rateLimitDrawer.classList.remove(
    "is-open"
  );

  els.rateLimitDrawer.setAttribute(
    "aria-hidden",
    "true"
  );

  els.rateLimitDrawerButton?.setAttribute(
    "aria-expanded",
    "false"
  );

  document.body.classList.remove(
    "has-rate-limit-drawer-open"
  );
}


function renderRateLimitSidebarSummary(
  accounts
) {
  const rows =
    Array.isArray(accounts)
      ? accounts
      : [];

  if (
    !els.rateLimitSidebarBadge ||
    !els.rateLimitDrawerButton
  ) {
    return;
  }

  els.rateLimitDrawerButton.classList.remove(
    "is-warning",
    "is-critical"
  );

  if (!rows.length) {
    els.rateLimitSidebarBadge.textContent =
      "—";

    return;
  }

  let nearCap = 0;
  let exhausted = 0;

  rows.forEach((account) => {
    const weeklySent = Number(
      account.weekly_success_count || 0
    );

    const weeklyLimit = Math.max(
      1,
      Number(
        account.weekly_limit || 100
      )
    );

    const remaining = Number(
      account.weekly_remaining ?? (
        weeklyLimit - weeklySent
      )
    );

    if (
      remaining <= 0 ||
      account.quota_available === false
    ) {
      exhausted += 1;
      return;
    }

    if (
      weeklySent / weeklyLimit >= 0.9
    ) {
      nearCap += 1;
    }
  });

  if (exhausted > 0) {
    els.rateLimitSidebarBadge.textContent =
      `${exhausted} cap`;

    els.rateLimitDrawerButton.classList.add(
      "is-critical"
    );

    return;
  }

  if (nearCap > 0) {
    els.rateLimitSidebarBadge.textContent =
      `${nearCap} near`;

    els.rateLimitDrawerButton.classList.add(
      "is-warning"
    );

    return;
  }

  els.rateLimitSidebarBadge.textContent =
    `${rows.length} ok`;
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
  const rows =
    Array.isArray(accounts)
      ? accounts
      : [];

  if (els.outreachAccountCount) {
    els.outreachAccountCount.textContent =
      `${rows.length} accounts`;
  }

  renderRateLimitSidebarSummary(
    rows
  );

  if (
    !els.outreachAccountsList ||
    !els.rateLimitAccountCardTemplate
  ) {
    return;
  }

  els.outreachAccountsList.replaceChildren();

  if (!rows.length) {
    const empty =
      document.createElement("div");

    empty.className =
      "outreach-job-empty";

    empty.textContent =
      "Chưa có dữ liệu account.";

    els.outreachAccountsList.append(
      empty
    );

    return;
  }

  rows.forEach((account) => {
    const fragment =
      els.rateLimitAccountCardTemplate
        .content
        .cloneNode(true);

    const card =
      fragment.querySelector(
        ".rate-limit-account-card"
      );

    const current =
      Boolean(
        account.is_current_account
      );

    const status =
      String(
        account.status ||
        "unknown"
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

    const weeklySent =
      Number(
        account.weekly_success_count || 0
      );

    const weeklyLimit =
      Math.max(
        1,
        Number(
          account.weekly_limit || 100
        )
      );

    const weeklyRemaining =
      Math.max(
        0,
        Number(
          account.weekly_remaining ?? (
            weeklyLimit - weeklySent
          )
        )
      );

    const quotaAvailable =
      account.quota_available !== false &&
      weeklyRemaining > 0;

    const weeklyPercent =
      Math.max(
        0,
        Math.min(
          100,
          weeklySent /
          weeklyLimit *
          100
        )
      );

    const setText = (
      selector,
      value
    ) => {
      const element =
        fragment.querySelector(
          selector
        );

      if (element) {
        element.textContent =
          String(value);
      }
    };

    setText(
      "[data-rate-account-name]",
      getOutreachAccountDisplayName(
        account.account_id
      )
    );

    setText(
      "[data-rate-account-status]",
      status
    );

    setText(
      "[data-rate-turn]",
      `${used} / ${limit}`
    );

    setText(
      "[data-rate-turn-remaining]",
      remaining
    );

    setText(
      "[data-rate-weekly-label]",
      `${weeklySent} / ${weeklyLimit}`
    );

    setText(
      "[data-rate-weekly-sent]",
      `${weeklySent} / ${weeklyLimit}`
    );

    setText(
      "[data-rate-weekly-remaining]",
      weeklyRemaining
    );

    setText(
      "[data-rate-assigned]",
      assigned
    );

    setText(
      "[data-rate-success]",
      completed
    );

    setText(
      "[data-rate-failed]",
      failed
    );

    setText(
      "[data-rate-last-job]",
      account.last_job_code || "—"
    );

    setText(
      "[data-rate-last-used]",
      formatDate(
        account.last_used_at
      )
    );

    const statusPill =
      fragment.querySelector(
        "[data-rate-account-status]"
      );

    if (statusPill) {
      statusPill.className =
        `pill ${
          quotaAvailable
            ? "pill-neutral"
            : "pill-red"
        }`;
    }

    const currentLabel =
      fragment.querySelector(
        "[data-rate-account-current]"
      );

    if (currentLabel) {
      currentLabel.hidden =
        !current;
    }

    const limitedLabel =
      fragment.querySelector(
        "[data-rate-account-limited]"
      );

    if (limitedLabel) {
      limitedLabel.hidden =
        quotaAvailable;
    }

    const progressBar =
      fragment.querySelector(
        "[data-rate-weekly-progress]"
      );

    if (progressBar) {
      progressBar.style.width =
        `${weeklyPercent}%`;
    }

    const lastUrl =
      fragment.querySelector(
        "[data-rate-last-url]"
      );

    if (lastUrl) {
      const url =
        String(
          account.last_linkedin_url ||
          ""
        ).trim();

      lastUrl.textContent =
        url || "—";

      if (url) {
        lastUrl.href =
          url;
      } else {
        lastUrl.removeAttribute(
          "href"
        );
      }
    }

    const lastError =
      fragment.querySelector(
        "[data-rate-last-error]"
      );

    if (lastError) {
      const errorText =
        String(
          account.last_error ||
          ""
        ).trim();

      lastError.hidden =
        !errorText;

      lastError.textContent =
        errorText;
    }

    card?.classList.toggle(
      "is-current",
      current
    );

    els.outreachAccountsList.append(
      fragment
    );
  });
}

// ---------------------------------------------------------
// ACCEPTANCE CHECK
// ---------------------------------------------------------


function getOutreachAcceptanceLabel(
  acceptance
) {
  if (!acceptance) {
    return "Not checked";
  }

  const status = normaliseStatus(
    acceptance.status
  );

  if (status === "pending") {
    return "Queued";
  }

  if (status === "running") {
    return "Checking";
  }

  if (status === "completed") {
    return "Completed";
  }

  if (status === "failed") {
    return "Check failed";
  }

  return statusLabel(status);
}


async function queueOutreachAcceptanceCheck(
  jobId
) {
  const cleanedJobId = String(
    jobId || ""
  ).trim();

  if (!cleanedJobId) {
    throw new Error(
      "Không tìm thấy Outreach job_id."
    );
  }

  if (
    state
      .outreachAcceptanceSubmittingJobIds
      .has(cleanedJobId)
  ) {
    return;
  }

  state
    .outreachAcceptanceSubmittingJobIds
    .add(cleanedJobId);

  renderOutreachAcceptanceJobs(
    state.outreachRecentJobs
  );

  try {
    const response = await fetch(
      `/api/outreach/connect/jobs/${encodeURIComponent(
        cleanedJobId
      )}/check-acceptance`,
      {
        method: "POST",
        headers: {
          "Accept": "application/json"
        },
        cache: "no-store"
      }
    );

    let result = {};

    try {
      result = await response.json();
    } catch (error) {
      result = {};
    }

    if (
      !response.ok ||
      !result.ok
    ) {
      throw new Error(
        result.detail ||
        result.error ||
        "Không thể queue Acceptance Check."
      );
    }

    await loadOutreachDashboard();

  } finally {
    state
      .outreachAcceptanceSubmittingJobIds
      .delete(cleanedJobId);

    renderOutreachAcceptanceJobs(
      state.outreachRecentJobs
    );
  }
}


function getLatestAcceptanceCheckedAt(acceptance){if(!acceptance)return null;return acceptance.completed_at||acceptance.updated_at||acceptance.started_at||null}
function getAcceptanceDisplayStatus(acceptance){return acceptance?normaliseStatus(acceptance.status||"not_checked"):"not_checked"}
function getAcceptanceStatusLabel(acceptance){const s=getAcceptanceDisplayStatus(acceptance),n=Number(acceptance?.run_number||0);if(s==="not_checked")return"Not checked";const l=s==="pending"?"Queued":s==="running"?"Checking":s==="completed"?"Completed":s==="failed"?"Check failed":statusLabel(s);return n>0?`#${n} ${l}`:l}
function updateSimplePagination({container,meta,prev,next,currentPage,totalPages,totalItems,startIndex,pageLength}){if(!container)return;container.hidden=totalItems<=0;if(totalItems<=0)return;if(meta)meta.textContent=`Page ${currentPage} / ${totalPages} · ${startIndex+1}-${startIndex+pageLength} of ${totalItems}`;if(prev)prev.disabled=currentPage<=1;if(next)next.disabled=currentPage>=totalPages}
function renderOutreachHistory(jobs){const rows=Array.isArray(jobs)?jobs:[];if(els.outreachHistoryCount)els.outreachHistoryCount.textContent=`${rows.length} jobs`;if(!els.outreachHistoryEmpty||!els.outreachHistoryTableWrap||!els.outreachHistoryBody||!els.outreachHistoryRowTemplate)return;if(!rows.length){els.outreachHistoryEmpty.hidden=false;els.outreachHistoryTableWrap.hidden=true;els.outreachHistoryBody.replaceChildren();if(els.outreachHistoryPagination)els.outreachHistoryPagination.hidden=true;return}const ps=Number(state.outreachHistoryPageSize||5),tp=Math.max(1,Math.ceil(rows.length/ps));state.outreachHistoryPage=Math.min(tp,Math.max(1,state.outreachHistoryPage));const si=(state.outreachHistoryPage-1)*ps,pr=rows.slice(si,si+ps);els.outreachHistoryEmpty.hidden=true;els.outreachHistoryTableWrap.hidden=false;els.outreachHistoryBody.replaceChildren();pr.forEach(job=>{const f=els.outreachHistoryRowTemplate.content.cloneNode(true),s=normaliseStatus(job.status),vals={"[data-connect-job-code]":job.job_code||"—","[data-connect-job-profiles]":Number(job.target_count||0),"[data-connect-job-processed]":Number(job.processed_count||0),"[data-connect-job-success]":Number(job.success_count||0),"[data-connect-job-failed]":Number(job.failed_count||0),"[data-connect-job-created]":formatDate(job.created_at)};Object.entries(vals).forEach(([q,v])=>{const e=f.querySelector(q);if(e)e.textContent=String(v)});const se=f.querySelector("[data-connect-job-status]");if(se){se.textContent=statusLabel(s);se.className=`pill ${getOutreachPillClass(s)}`}els.outreachHistoryBody.append(f)});updateSimplePagination({container:els.outreachHistoryPagination,meta:els.outreachHistoryPageMeta,prev:els.outreachHistoryPrevPage,next:els.outreachHistoryNextPage,currentPage:state.outreachHistoryPage,totalPages:tp,totalItems:rows.length,startIndex:si,pageLength:pr.length})}
function renderOutreachAcceptanceJobs(
  jobs
) {
  const rows =
    Array.isArray(jobs)
      ? jobs
      : [];

  if (els.outreachAcceptanceJobCount) {
    els.outreachAcceptanceJobCount.textContent =
      `${rows.length} jobs`;
  }

  if (
    !els.outreachAcceptanceEmpty ||
    !els.outreachAcceptanceTableWrap ||
    !els.outreachAcceptanceBody ||
    !els.outreachAcceptanceRowTemplate
  ) {
    return;
  }

  if (!rows.length) {
    els.outreachAcceptanceEmpty.hidden = false;
    els.outreachAcceptanceTableWrap.hidden = true;
    els.outreachAcceptanceBody.replaceChildren();

    if (els.outreachAcceptancePagination) {
      els.outreachAcceptancePagination.hidden = true;
    }

    return;
  }

  const pageSize = Number(
    state.outreachAcceptancePageSize || 10
  );

  const totalPages = Math.max(
    1,
    Math.ceil(rows.length / pageSize)
  );

  state.outreachAcceptancePage =
    Math.min(
      totalPages,
      Math.max(
        1,
        state.outreachAcceptancePage
      )
    );

  const startIndex =
    (state.outreachAcceptancePage - 1) *
    pageSize;

  const pageRows =
    rows.slice(
      startIndex,
      startIndex + pageSize
    );

  els.outreachAcceptanceEmpty.hidden = true;
  els.outreachAcceptanceTableWrap.hidden = false;
  els.outreachAcceptanceBody.replaceChildren();

  pageRows.forEach((job) => {
    const acceptance =
      job.acceptance || null;

    const acceptanceStatus =
      getAcceptanceDisplayStatus(
        acceptance
      );

    const connectStatus =
      normaliseStatus(
        job.status
      );

    const fragment =
      els.outreachAcceptanceRowTemplate
        .content
        .cloneNode(true);

    const setText = (
      selector,
      value
    ) => {
      const element =
        fragment.querySelector(
          selector
        );

      if (element) {
        element.textContent =
          String(value);
      }
    };

    setText(
      "[data-acceptance-job-code]",
      job.job_code || "—"
    );

    setText(
      "[data-acceptance-created]",
      formatDate(job.created_at)
    );

    setText(
      "[data-acceptance-profile-count]",
      Number(job.target_count || 0)
    );

    setText(
      "[data-acceptance-accepted]",
      acceptance
        ? Number(
            acceptance.new_accepted_count || 0
          )
        : "—"
    );

    setText(
      "[data-acceptance-pending]",
      acceptance
        ? Number(
            acceptance.still_pending_count || 0
          )
        : "—"
    );

    setText(
      "[data-acceptance-unknown]",
      acceptance
        ? Number(
            acceptance.declined_or_unknown_count || 0
          )
        : "—"
    );

    setText(
      "[data-acceptance-failed]",
      acceptance
        ? Number(
            acceptance.failed_count || 0
          )
        : "—"
    );

    const lastCheckedAt =
      getLatestAcceptanceCheckedAt(
        acceptance
      );

    setText(
      "[data-acceptance-last-checked]",
      lastCheckedAt
        ? formatDate(lastCheckedAt)
        : "Never"
    );

    const connectStatusElement =
      fragment.querySelector(
        "[data-acceptance-connect-status]"
      );

    if (connectStatusElement) {
      connectStatusElement.textContent =
        statusLabel(connectStatus);

      connectStatusElement.className =
        `pill ${getOutreachPillClass(
          connectStatus
        )}`;
    }

    const acceptanceStatusElement =
      fragment.querySelector(
        "[data-acceptance-status]"
      );

    if (acceptanceStatusElement) {
      acceptanceStatusElement.textContent =
        getAcceptanceStatusLabel(
          acceptance
        );

      acceptanceStatusElement.className =
        `pill ${getOutreachPillClass(
          acceptanceStatus
        )}`;
    }

    const button =
      fragment.querySelector(
        "[data-acceptance-check-button]"
      );

    if (button) {
      const jobId =
        String(job.id || "").trim();

      const submitting =
        state
          .outreachAcceptanceSubmittingJobIds
          .has(jobId);

      const busy =
        acceptanceStatus === "pending" ||
        acceptanceStatus === "running";

      const canCheck =
        Boolean(jobId) &&
        connectStatus === "completed" &&
        !busy &&
        !submitting;

      button.dataset.jobId = jobId;
      button.disabled = !canCheck;

      button.textContent =
        submitting
          ? "Queueing..."
          : acceptanceStatus === "pending"
            ? "Queued"
            : acceptanceStatus === "running"
              ? "Checking..."
              : "Check Acceptance";

      button.addEventListener(
        "click",
        async () => {
          try {
            await queueOutreachAcceptanceCheck(
              jobId
            );
          } catch (error) {
            console.error(
              "Acceptance check error:",
              error
            );
          }
        }
      );
    }

    els.outreachAcceptanceBody.append(
      fragment
    );
  });

  updateSimplePagination({
    container:
      els.outreachAcceptancePagination,
    meta:
      els.outreachAcceptancePageMeta,
    prev:
      els.outreachAcceptancePrevPage,
    next:
      els.outreachAcceptanceNextPage,
    currentPage:
      state.outreachAcceptancePage,
    totalPages,
    totalItems:
      rows.length,
    startIndex,
    pageLength:
      pageRows.length
  });
}


// ---------------------------------------------------------
// ACCEPTED POOL
// ---------------------------------------------------------


function ensureOutreachAcceptedPoolPanel() {
  return (
    els.outreachAcceptedPoolPanel ||
    document.querySelector("#outreachAcceptedPoolPanel")
  );
}


function getEligibleMessageProspectIds() {
  const items =
    Array.isArray(
      state.messagePreparation?.items
    )
      ? state.messagePreparation.items
      : [];

  return new Set(
    items
      .map(
        (item) =>
          String(
            item.prospect_id || ""
          ).trim()
      )
      .filter(Boolean)
  );
}


function getAcceptedPoolAvailableAccounts() {
  const items =
    Array.isArray(
      state.outreachAcceptedPool?.items
    )
      ? state.outreachAcceptedPool.items
      : [];

  const accountIds = new Set();

  items.forEach((item) => {
    const accountId =
      String(
        item.assigned_account_id ||
        ""
      ).trim();

    if (accountId) {
      accountIds.add(accountId);
    }
  });

  return Array.from(accountIds);
}


function renderAcceptedPoolAccountFilter() {
  const select =
    els.outreachAcceptedAccountFilter;

  if (!select) {
    return;
  }

  const accountIds =
    getAcceptedPoolAvailableAccounts();

  const currentValue =
    state.outreachAcceptedAccountFilter ||
    "all";

  const fragment =
    document.createDocumentFragment();

  const allOption =
    document.createElement("option");

  allOption.value = "all";
  allOption.textContent = "All accounts";

  fragment.append(allOption);

  accountIds.forEach((accountId) => {
    const option =
      document.createElement("option");

    option.value = accountId;

    option.textContent =
      getOutreachAccountDisplayName(
        accountId
      );

    fragment.append(option);
  });

  select.replaceChildren(fragment);

  const stillExists =
    currentValue === "all" ||
    accountIds.includes(currentValue);

  state.outreachAcceptedAccountFilter =
    stillExists
      ? currentValue
      : "all";

  select.value =
    state.outreachAcceptedAccountFilter;
}


function getAcceptedPoolUiBucket(
  item,
  eligibleIds = null
) {
  const messageBucket =
    String(
      item?.message_bucket ||
      "not_sent"
    ).toLowerCase();

  if (messageBucket === "sent") {
    return "sent";
  }

  const prospectId =
    String(
      item?.prospect_id ||
      ""
    ).trim();

  const readyIds =
    eligibleIds ||
    getEligibleMessageProspectIds();

  if (
    prospectId &&
    readyIds.has(prospectId)
  ) {
    return "ready";
  }

  return "prepared";
}


function getAcceptedPoolFilteredItems() {
  const items =
    Array.isArray(
      state.outreachAcceptedPool?.items
    )
      ? state.outreachAcceptedPool.items
      : [];

  const filter =
    state.outreachAcceptedPoolFilter ||
    "all";

  const accountFilter =
    state.outreachAcceptedAccountFilter ||
    "all";

  const eligibleIds =
    getEligibleMessageProspectIds();

  return items.filter((item) => {
    const statusMatches =
      filter === "all" ||
      getAcceptedPoolUiBucket(
        item,
        eligibleIds
      ) === filter;

    const itemAccountId =
      String(
        item.assigned_account_id ||
        ""
      ).trim();

    const accountMatches =
      accountFilter === "all" ||
      itemAccountId ===
        accountFilter;

    return (
      statusMatches &&
      accountMatches
    );
  });
}

function getAcceptedPoolUiSummary() {
  const items =
    Array.isArray(
      state.outreachAcceptedPool?.items
    )
      ? state.outreachAcceptedPool.items
      : [];

  const eligibleIds =
    getEligibleMessageProspectIds();

  const summary = {
    all: items.length,
    ready: 0,
    prepared: 0,
    sent: 0
  };

  items.forEach((item) => {
    const bucket =
      getAcceptedPoolUiBucket(
        item,
        eligibleIds
      );

    if (
      Object.prototype.hasOwnProperty.call(
        summary,
        bucket
      )
    ) {
      summary[bucket] += 1;
    }
  });

  return summary;
}


function reconcileAcceptedPoolSelection() {
  const eligibleIds =
    getEligibleMessageProspectIds();

  for (
    const prospectId of Array.from(
      state.outreachAcceptedSelectedProspectIds
    )
  ) {
    if (!eligibleIds.has(prospectId)) {
      state
        .outreachAcceptedSelectedProspectIds
        .delete(prospectId);
    }
  }
}


function getAcceptedPoolPageData() {
  const filteredItems =
    getAcceptedPoolFilteredItems();

  const pageSize = 15;

  const totalPages = Math.max(
    1,
    Math.ceil(
      filteredItems.length /
      pageSize
    )
  );

  const currentPage = Math.min(
    totalPages,
    Math.max(
      1,
      Number(
        state.outreachAcceptedPoolPage ||
        1
      )
    )
  );

  state.outreachAcceptedPoolPage =
    currentPage;

  const startIndex =
    (
      currentPage -
      1
    ) *
    pageSize;

  return {
    filteredItems,
    pageItems:
      filteredItems.slice(
        startIndex,
        startIndex + pageSize
      ),
    currentPage,
    totalPages,
    startIndex
  };
}


function renderAcceptedPoolPagination(
  pageData
) {
  if (!els.outreachAcceptedPagination) {
    return;
  }

  const {
    filteredItems,
    pageItems,
    currentPage,
    totalPages,
    startIndex
  } = pageData;

  els.outreachAcceptedPagination.hidden =
    filteredItems.length === 0;

  if (!filteredItems.length) {
    return;
  }

  if (els.outreachAcceptedPageMeta) {
    els.outreachAcceptedPageMeta.textContent =
      `Page ${currentPage} / ${totalPages} · ${startIndex + 1}-${startIndex + pageItems.length} of ${filteredItems.length}`;
  }

  if (els.outreachAcceptedPrevPage) {
    els.outreachAcceptedPrevPage.disabled =
      currentPage <= 1;
  }

  if (els.outreachAcceptedNextPage) {
    els.outreachAcceptedNextPage.disabled =
      currentPage >= totalPages;
  }
}


function updateAcceptedPoolPageSelectControl(
  pageItems
) {
  const control =
    els.outreachAcceptedSelectPage;

  if (!control) {
    return;
  }

  const eligibleIds =
    getEligibleMessageProspectIds();

  const selectableIds =
    pageItems
      .map(
        (item) =>
          String(
            item.prospect_id || ""
          ).trim()
      )
      .filter(
        (id) =>
          Boolean(id) &&
          eligibleIds.has(id)
      );

  const selectedCount =
    selectableIds.filter(
      (id) =>
        state
          .outreachAcceptedSelectedProspectIds
          .has(id)
    ).length;

  control.disabled =
    selectableIds.length === 0;

  control.checked =
    selectableIds.length > 0 &&
    selectedCount ===
      selectableIds.length;

  control.indeterminate =
    selectedCount > 0 &&
    selectedCount <
      selectableIds.length;
}


function renderOutreachAcceptedPool() {
  const panel =
    ensureOutreachAcceptedPoolPanel();

  if (!panel) {
    return;
  }

  reconcileAcceptedPoolSelection();

  renderAcceptedPoolAccountFilter();

  const uiSummary =
    getAcceptedPoolUiSummary();

  const pageData =
    getAcceptedPoolPageData();

  const filteredItems =
    pageData.filteredItems;

  const pageItems =
    pageData.pageItems;

  if (els.outreachAcceptedPoolSummary) {
    els.outreachAcceptedPoolSummary.textContent =
      `${uiSummary.all} accepted profiles · ${uiSummary.ready} ready · ${uiSummary.prepared} prepared · ${uiSummary.sent} sent`;
  }

  if (els.outreachAcceptedSelectedCount) {
    const selectedCount =
      state
        .outreachAcceptedSelectedProspectIds
        .size;

    els.outreachAcceptedSelectedCount.textContent =
      `${selectedCount} selected`;

    els.outreachAcceptedSelectedCount.className =
      `pill ${
        selectedCount > 0
          ? "pill-purple"
          : "pill-neutral"
      }`;
  }

  panel
    .querySelectorAll(
      "[data-accepted-filter]"
    )
    .forEach((button) => {
      const filter =
        button.dataset.acceptedFilter ||
        "all";

      const count =
        Number(
          uiSummary[filter] ||
          0
        );

      const label =
        filter === "ready"
          ? "Ready"
          : filter === "prepared"
            ? "Prepared"
            : filter === "sent"
              ? "Sent"
              : "All";

      button.textContent =
        `${label} ${count}`;

      button.classList.toggle(
        "is-active",
        filter ===
          state.outreachAcceptedPoolFilter
      );
    });

  if (!filteredItems.length) {
    if (els.outreachAcceptedPoolEmpty) {
      els.outreachAcceptedPoolEmpty.hidden =
        false;

      els.outreachAcceptedPoolEmpty.textContent =
        uiSummary.all > 0
          ? "Không có recipient trong filter này."
          : "Chưa có user accepted.";
    }

    if (els.outreachAcceptedPoolTableWrap) {
      els.outreachAcceptedPoolTableWrap.hidden =
        true;
    }

    els.outreachAcceptedPoolBody
      ?.replaceChildren();

    if (els.outreachAcceptedPagination) {
      els.outreachAcceptedPagination.hidden =
        true;
    }

    updateAcceptedPoolPageSelectControl(
      []
    );

    renderMessagePreparation();

    return;
  }

  if (els.outreachAcceptedPoolEmpty) {
    els.outreachAcceptedPoolEmpty.hidden =
      true;
  }

  if (els.outreachAcceptedPoolTableWrap) {
    els.outreachAcceptedPoolTableWrap.hidden =
      false;
  }

  renderAcceptedPoolPagination(
    pageData
  );

  if (
    !els.outreachAcceptedPoolBody ||
    !els.outreachAcceptedPoolRowTemplate
  ) {
    return;
  }

  const eligibleIds =
    getEligibleMessageProspectIds();

  els.outreachAcceptedPoolBody
    .replaceChildren();

  pageItems.forEach((item) => {
    const prospectId =
      String(
        item.prospect_id ||
        ""
      ).trim();

    const linkedinUrl =
      String(
        item.linkedin_url ||
        ""
      ).trim();

    const uiBucket =
      getAcceptedPoolUiBucket(
        item,
        eligibleIds
      );

    const canSelect =
      uiBucket === "ready" &&
      Boolean(prospectId);

    const isSelected =
      canSelect &&
      state
        .outreachAcceptedSelectedProspectIds
        .has(prospectId);

    const fragment =
      els.outreachAcceptedPoolRowTemplate
        .content
        .cloneNode(true);

    const row =
      fragment.querySelector("tr");

    const checkbox =
      fragment.querySelector(
        "[data-accepted-select]"
      );

    const link =
      fragment.querySelector(
        "[data-accepted-link]"
      );

    const account =
      fragment.querySelector(
        "[data-accepted-account]"
      );

    const acceptedAt =
      fragment.querySelector(
        "[data-accepted-at]"
      );

    const message =
      fragment.querySelector(
        "[data-accepted-message]"
      );

    row?.classList.toggle(
      "is-selected",
      isSelected
    );

    if (checkbox) {
      checkbox.disabled =
        !canSelect;

      checkbox.checked =
        isSelected;

      checkbox.title =
        uiBucket === "prepared"
          ? "Recipient is already in a prepared message batch."
          : uiBucket === "sent"
            ? "Message already sent."
            : "Select recipient for a new message batch.";

      checkbox.addEventListener(
        "change",
        () => {
          if (!canSelect) {
            return;
          }

          if (checkbox.checked) {
            state
              .outreachAcceptedSelectedProspectIds
              .add(prospectId);
          } else {
            state
              .outreachAcceptedSelectedProspectIds
              .delete(prospectId);
          }

          renderOutreachAcceptedPool();
        }
      );
    }

    if (link) {
      link.href =
        linkedinUrl ||
        "#";

      link.textContent =
        linkedinUrl ||
        "—";
    }

    if (account) {
      account.textContent =
        getOutreachAccountDisplayName(
          item.assigned_account_id
        );
    }

    if (acceptedAt) {
      acceptedAt.textContent =
        formatDate(
          item.accepted_at ||
          item.acceptance_checked_at
        );
    }

    if (message) {
      const messageLabel =
        uiBucket === "sent"
          ? "Sent"
          : uiBucket === "prepared"
            ? "Prepared"
            : "Ready";

      message.textContent =
        messageLabel;

      message.className =
        `pill ${
          uiBucket === "sent"
            ? "pill-green"
            : uiBucket === "ready"
              ? "pill-purple"
              : "pill-neutral"
        }`;
    }

    els.outreachAcceptedPoolBody.append(
      fragment
    );
  });

  updateAcceptedPoolPageSelectControl(
    pageItems
  );

  renderMessagePreparation();
}


async function loadOutreachAcceptedPool() {
  try {
    const response = await fetch(
      "/api/outreach/accepted-pool",
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
        "Không thể load Accepted Pool."
      );
    }

    const pool =
      result.accepted_pool || {};

    state.outreachAcceptedPool = {
      summary: {
        total: Number(
          pool.summary?.total || 0
        ),
        not_sent: Number(
          pool.summary?.not_sent || 0
        ),
        sent: Number(
          pool.summary?.sent || 0
        )
      },
      items: Array.isArray(
        pool.items
      )
        ? pool.items
        : []
    };

  } catch (error) {
    console.error(
      "Accepted Pool error:",
      error
    );

    state.outreachAcceptedPool = {
      summary: {
        total: 0,
        not_sent: 0,
        sent: 0
      },
      items: []
    };
  }
}


// ---------------------------------------------------------
// MESSAGE PREPARATION
// ---------------------------------------------------------


async function loadMessagePreparation() {
  try {
    const response = await fetch(
      "/api/outreach/messages/preparation",
      {
        method: "GET",
        headers: {
          "Accept": "application/json"
        },
        cache: "no-store"
      }
    );

    const result = await response.json();

    if (!response.ok || !result.ok) {
      throw new Error(
        result.detail ||
        result.error ||
        "Không thể load message preparation."
      );
    }

    const preparation =
      result.preparation || {};

    state.messagePreparation = {
      count: Number(preparation.count || 0),
      items: Array.isArray(preparation.items)
        ? preparation.items
        : []
    };

    reconcileAcceptedPoolSelection();

    if (els.messagePreparationError) {
      els.messagePreparationError.hidden = true;
      els.messagePreparationError.textContent = "";
    }
  } catch (error) {
    console.error("Message preparation error:", error);

    state.messagePreparation = {
      count: 0,
      items: []
    };

    if (els.messagePreparationError) {
      els.messagePreparationError.hidden = false;
      els.messagePreparationError.textContent =
        error.message || String(error);
    }
  }
}


async function loadMessageBatches() {
  try {
    const response = await fetch(
      "/api/outreach/messages/batches",
      {
        method: "GET",
        headers: {
          "Accept": "application/json"
        },
        cache: "no-store"
      }
    );

    const result = await response.json();

    if (!response.ok || !result.ok) {
      throw new Error(
        result.detail ||
        result.error ||
        "Không thể load prepared batches."
      );
    }

    state.messageBatches =
      Array.isArray(result.batches)
        ? result.batches
        : [];
  } catch (error) {
    console.error("Message batch list error:", error);
    state.messageBatches = [];
  }
}


function getMessageBatchSendLabel(
  batchStatus,
  queueSubmitting
) {
  if (queueSubmitting) {
    return "Queueing...";
  }

  if (batchStatus === "queued") {
    return "Queued";
  }

  if (batchStatus === "processing") {
    return "Sending...";
  }

  if (batchStatus === "completed") {
    return "Completed";
  }

  if (batchStatus === "failed") {
    return "Failed";
  }

  return "Send messages";
}


function renderMessagePreparation() {
  const count = Number(
    state.messagePreparation?.count || 0
  );

  if (els.messagePreparationCount) {
    els.messagePreparationCount.textContent =
      `${count} eligible`;

    els.messagePreparationCount.className =
      `pill ${count > 0 ? "pill-purple" : "pill-neutral"}`;
  }

  if (els.messagePreparationHeadline) {
    els.messagePreparationHeadline.textContent =
      count > 0
        ? `${count} accepted users sẵn sàng để prepare`
        : "Chưa có recipient cần prepare";
  }

  if (els.messagePreparationMeta) {
    els.messagePreparationMeta.textContent =
      count > 0
        ? "Prepare All sẽ snapshot toàn bộ danh sách hiện tại thành một batch cố định."
        : "Accepted users chưa nằm trong prepared batch sẽ xuất hiện ở đây.";
  }

  const selectedCount =
    state.outreachAcceptedSelectedProspectIds.size;

  if (els.messagePrepareSelectedButton) {
    els.messagePrepareSelectedButton.disabled =
      state.messagePreparationSubmitting ||
      state.messagePreparationSelectedSubmitting ||
      selectedCount <= 0;

    els.messagePrepareSelectedButton.textContent =
      state.messagePreparationSelectedSubmitting
        ? "Preparing..."
        : selectedCount > 0
          ? `Prepare selected ${selectedCount}`
          : "Prepare selected";
  }

  if (els.messagePrepareAllButton) {
    els.messagePrepareAllButton.disabled =
      state.messagePreparationSubmitting ||
      state.messagePreparationSelectedSubmitting ||
      count <= 0;

    els.messagePrepareAllButton.textContent =
      state.messagePreparationSubmitting
        ? "Preparing..."
        : count > 0
          ? `Prepare all ${count}`
          : "Prepare all";
  }

  const batches =
    Array.isArray(state.messageBatches)
      ? state.messageBatches
      : [];

  if (els.messageBatchCount) {
    els.messageBatchCount.textContent =
      `${batches.length} batches`;
  }

  if (els.messageBatchEmpty) {
    els.messageBatchEmpty.hidden =
      batches.length > 0;
  }

  if (
    !els.messageBatchList ||
    !els.messageBatchRowTemplate
  ) {
    return;
  }

  const batchPageSize = Number(
    state.messageBatchPageSize || 8
  );

  const batchTotalPages = Math.max(
    1,
    Math.ceil(batches.length / batchPageSize)
  );

  state.messageBatchPage = Math.min(
    batchTotalPages,
    Math.max(1, state.messageBatchPage)
  );

  const batchStartIndex =
    (state.messageBatchPage - 1) * batchPageSize;

  const visibleBatches = batches.slice(
    batchStartIndex,
    batchStartIndex + batchPageSize
  );

  els.messageBatchList.replaceChildren();

  visibleBatches.forEach((batch) => {
    const batchId = String(
      batch.id || ""
    ).trim();

    const batchStatus = normaliseStatus(
      batch.status || "prepared"
    );

    const queueSubmitting =
      state
        .messageBatchQueueSubmittingIds
        .has(batchId);

    const canSend =
      Boolean(batchId) &&
      batchStatus === "prepared" &&
      !queueSubmitting;

    const fragment =
      els.messageBatchRowTemplate
        .content
        .cloneNode(true);

    const code =
      fragment.querySelector(
        "[data-message-batch-code]"
      );

    const meta =
      fragment.querySelector(
        "[data-message-batch-meta]"
      );

    const status =
      fragment.querySelector(
        "[data-message-batch-status]"
      );

    const detailButton =
      fragment.querySelector(
        "[data-message-batch-detail]"
      );

    const sendButton =
      fragment.querySelector(
        "[data-message-batch-send]"
      );

    if (code) {
      code.textContent =
        batch.batch_code ||
        "Prepared batch";
    }

    if (meta) {
      meta.textContent =
        `${Number(batch.target_count || 0)} recipients · ${formatDate(
          batch.created_at
        )}`;
    }

    if (status) {
      status.textContent =
        batchStatus;
    }

    if (detailButton) {
      detailButton.dataset.messageBatchDetailId =
        batchId;

      detailButton.addEventListener(
        "click",
        () => {
          openPreparedMessageBatch(
            batchId
          );
        }
      );
    }

    if (sendButton) {
      sendButton.dataset.messageBatchSendId =
        batchId;

      sendButton.disabled =
        !canSend;

      sendButton.textContent =
        getMessageBatchSendLabel(
          batchStatus,
          queueSubmitting
        );

      sendButton.addEventListener(
        "click",
        () => {
          openMessageSendModal(
            batchId
          );
        }
      );
    }

    els.messageBatchList.append(
      fragment
    );
  });

  updateSimplePagination({
    container: els.messageBatchPagination,
    meta: els.messageBatchPageMeta,
    prev: els.messageBatchPrevPage,
    next: els.messageBatchNextPage,
    currentPage: state.messageBatchPage,
    totalPages: batchTotalPages,
    totalItems: batches.length,
    startIndex: batchStartIndex,
    pageLength: visibleBatches.length
  });
}


function getMessageBatchById(
  batchId
) {
  const cleanedBatchId = String(
    batchId || ""
  ).trim();

  return (
    Array.isArray(state.messageBatches)
      ? state.messageBatches
      : []
  ).find(
    (item) =>
      String(item?.id || "").trim() ===
      cleanedBatchId
  ) || null;
}


function openMessageSendModal(
  batchId
) {
  const batch = getMessageBatchById(
    batchId
  );

  if (!batch) {
    return;
  }

  if (
    normaliseStatus(batch.status) !==
    "prepared"
  ) {
    return;
  }

  state.messageSendSelectedBatchId =
    String(batch.id || "").trim();

  if (els.messageSendDialogMeta) {
    els.messageSendDialogMeta.textContent =
      `${batch.batch_code || "Message batch"} · ${Number(
        batch.target_count || 0
      )} recipients`;
  }

  if (els.messageTemplateInput) {
    els.messageTemplateInput.value =
      "Hi {first_name},\n\n";
  }

  if (els.messageSendError) {
    els.messageSendError.hidden = true;
    els.messageSendError.textContent = "";
  }

  if (els.messageSendModal) {
    els.messageSendModal.hidden = false;
  }

  requestAnimationFrame(() => {
    els.messageTemplateInput?.focus();
  });
}


function closeMessageSendModal() {
  state.messageSendSelectedBatchId =
    null;

  if (els.messageSendError) {
    els.messageSendError.hidden = true;
    els.messageSendError.textContent = "";
  }

  if (els.messageSendModal) {
    els.messageSendModal.hidden = true;
  }
}


async function queueMessageBatchForSending(
  batchId,
  messageTemplate
) {
  const cleanedBatchId = String(
    batchId || ""
  ).trim();

  const cleanedTemplate = String(
    messageTemplate || ""
  ).trim();

  if (!cleanedBatchId) {
    throw new Error(
      "Không tìm thấy Message Batch ID."
    );
  }

  if (!cleanedTemplate) {
    throw new Error(
      "Message template không được để trống."
    );
  }

  if (
    state
      .messageBatchQueueSubmittingIds
      .has(cleanedBatchId)
  ) {
    return;
  }

  const batch = getMessageBatchById(
    cleanedBatchId
  );

  if (!batch) {
    throw new Error(
      "Không tìm thấy Message Batch."
    );
  }

  if (
    normaliseStatus(batch.status) !==
    "prepared"
  ) {
    throw new Error(
      "Chỉ batch có status prepared mới được gửi."
    );
  }

  state
    .messageBatchQueueSubmittingIds
    .add(cleanedBatchId);

  if (els.messageSendConfirmButton) {
    els.messageSendConfirmButton.disabled =
      true;

    els.messageSendConfirmButton.textContent =
      "Queueing...";
  }

  renderMessagePreparation();

  try {
    const response = await fetch(
      `/api/outreach/messages/batches/${encodeURIComponent(
        cleanedBatchId
      )}/queue`,
      {
        method: "POST",
        headers: {
          "Accept": "application/json",
          "Content-Type": "application/json"
        },
        cache: "no-store",
        body: JSON.stringify({
          message_template: cleanedTemplate
        })
      }
    );

    const result = await response.json();

    if (
      !response.ok ||
      !result.ok
    ) {
      throw new Error(
        result.detail ||
        result.error ||
        "Không thể queue Message Batch."
      );
    }

    closeMessageSendModal();

    await Promise.all([
      loadMessageBatches(),
      loadMessagePreparation()
    ]);

  } finally {
    state
      .messageBatchQueueSubmittingIds
      .delete(cleanedBatchId);

    if (els.messageSendConfirmButton) {
      els.messageSendConfirmButton.disabled =
        false;

      els.messageSendConfirmButton.textContent =
        "Queue & Send";
    }

    renderMessagePreparation();
  }
}


async function openPreparedMessageBatch(batchId) {
  if (!batchId) {
    return;
  }

  try {
    const response = await fetch(
      `/api/outreach/messages/batches/${encodeURIComponent(batchId)}`,
      {
        method: "GET",
        headers: {
          "Accept": "application/json"
        },
        cache: "no-store"
      }
    );

    const result = await response.json();

    if (!response.ok || !result.ok) {
      throw new Error(
        result.detail ||
        result.error ||
        "Không thể load prepared batch."
      );
    }

    const batch = result.batch || {};
    const targets =
      Array.isArray(batch.targets)
        ? batch.targets
        : [];

    if (els.drawerName) {
      els.drawerName.textContent =
        batch.batch_code || "Prepared Message Batch";
    }

    if (els.drawerContent) {
      els.drawerContent.innerHTML = `
        <div class="drawer-section">
          <p class="panel-meta">
            ${escapeHtml(String(batch.target_count || targets.length))}
            recipients · ${escapeHtml(batch.status || "prepared")}
          </p>
        </div>

        <div class="drawer-section">
          ${targets.length
            ? targets.map((target) => `
                <div class="detail-row">
                  <span>${escapeHtml(
                    getOutreachAccountDisplayName(
                      target.assigned_account_id
                    )
                  )}</span>
                  <a
                    href="${escapeHtml(target.linkedin_url || "")}"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    ${escapeHtml(target.linkedin_url || "—")}
                  </a>
                </div>
              `).join("")
            : '<div class="state">Batch chưa có recipient.</div>'
          }
        </div>
      `;
    }

    if (els.drawerBackdrop) {
      els.drawerBackdrop.hidden = false;
    }

    if (els.detailDrawer) {
      els.detailDrawer.classList.add("is-open");
      els.detailDrawer.setAttribute("aria-hidden", "false");
    }
  } catch (error) {
    window.alert(
      error.message || String(error)
    );
  }
}


function openMessagePrepareConfirmModal(
  mode
) {
  const selectedCount =
    state.outreachAcceptedSelectedProspectIds.size;

  const eligibleCount =
    Number(
      state.messagePreparation?.count || 0
    );

  const count =
    mode === "selected"
      ? selectedCount
      : eligibleCount;

  if (count <= 0) {
    return;
  }

  state.messagePrepareConfirmMode =
    mode;

  if (els.messagePrepareConfirmTitle) {
    els.messagePrepareConfirmTitle.textContent =
      mode === "selected"
        ? "Prepare selected recipients"
        : "Prepare all recipients";
  }

  if (els.messagePrepareConfirmMeta) {
    els.messagePrepareConfirmMeta.textContent =
      mode === "selected"
        ? `${count} selected accepted profiles`
        : `${count} currently eligible accepted profiles`;
  }

  if (els.messagePrepareConfirmButton) {
    els.messagePrepareConfirmButton.textContent =
      mode === "selected"
        ? `Prepare selected ${count}`
        : `Prepare all ${count}`;
  }

  if (els.messagePrepareConfirmError) {
    els.messagePrepareConfirmError.hidden =
      true;

    els.messagePrepareConfirmError.textContent =
      "";
  }

  if (els.messagePrepareConfirmModal) {
    els.messagePrepareConfirmModal.hidden =
      false;
  }
}


function closeMessagePrepareConfirmModal() {
  state.messagePrepareConfirmMode =
    null;

  if (els.messagePrepareConfirmError) {
    els.messagePrepareConfirmError.hidden =
      true;

    els.messagePrepareConfirmError.textContent =
      "";
  }

  if (els.messagePrepareConfirmModal) {
    els.messagePrepareConfirmModal.hidden =
      true;
  }
}


async function confirmMessagePreparation() {
  const mode =
    state.messagePrepareConfirmMode;

  if (mode === "selected") {
    await prepareSelectedMessageRecipients(
      true
    );

    return;
  }

  if (mode === "all") {
    await prepareAllMessageRecipients(
      true
    );
  }
}


async function prepareSelectedMessageRecipients(
  confirmed = false
) {
  const prospectIds =
    Array.from(
      state.outreachAcceptedSelectedProspectIds
    );

  if (
    !prospectIds.length ||
    state.messagePreparationSubmitting ||
    state.messagePreparationSelectedSubmitting
  ) {
    return;
  }

  if (!confirmed) {
    openMessagePrepareConfirmModal(
      "selected"
    );

    return;
  }

  state.messagePreparationSelectedSubmitting =
    true;

  if (els.messagePrepareConfirmButton) {
    els.messagePrepareConfirmButton.disabled =
      true;

    els.messagePrepareConfirmButton.textContent =
      "Preparing...";
  }

  renderMessagePreparation();

  try {
    const response = await fetch(
      "/api/outreach/messages/prepare-selected",
      {
        method: "POST",
        headers: {
          "Accept": "application/json",
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          prospect_ids: prospectIds
        })
      }
    );

    const result = await response.json();

    if (!response.ok || !result.ok) {
      throw new Error(
        result.detail ||
        result.error ||
        "Không thể prepare selected recipients."
      );
    }

    state
      .outreachAcceptedSelectedProspectIds
      .clear();

    closeMessagePrepareConfirmModal();

    await Promise.all([
      loadOutreachAcceptedPool(),
      loadMessagePreparation(),
      loadMessageBatches()
    ]);

    renderOutreachAcceptedPool();

  } catch (error) {
    if (els.messagePrepareConfirmError) {
      els.messagePrepareConfirmError.hidden =
        false;

      els.messagePrepareConfirmError.textContent =
        error.message ||
        String(error);
    }

    if (els.messagePreparationError) {
      els.messagePreparationError.hidden =
        false;

      els.messagePreparationError.textContent =
        error.message ||
        String(error);
    }

  } finally {
    state.messagePreparationSelectedSubmitting =
      false;

    if (els.messagePrepareConfirmButton) {
      els.messagePrepareConfirmButton.disabled =
        false;
    }

    renderMessagePreparation();
  }
}


async function prepareAllMessageRecipients(
  confirmed = false
) {
  const count = Number(
    state.messagePreparation?.count || 0
  );

  if (
    count <= 0 ||
    state.messagePreparationSubmitting ||
    state.messagePreparationSelectedSubmitting
  ) {
    return;
  }

  if (!confirmed) {
    openMessagePrepareConfirmModal(
      "all"
    );

    return;
  }

  state.messagePreparationSubmitting =
    true;

  if (els.messagePrepareConfirmButton) {
    els.messagePrepareConfirmButton.disabled =
      true;

    els.messagePrepareConfirmButton.textContent =
      "Preparing...";
  }

  renderMessagePreparation();

  try {
    const response = await fetch(
      "/api/outreach/messages/prepare-all",
      {
        method: "POST",
        headers: {
          "Accept": "application/json"
        }
      }
    );

    const result = await response.json();

    if (!response.ok || !result.ok) {
      throw new Error(
        result.detail ||
        result.error ||
        "Không thể prepare recipients."
      );
    }

    closeMessagePrepareConfirmModal();

    await Promise.all([
      loadOutreachAcceptedPool(),
      loadMessagePreparation(),
      loadMessageBatches()
    ]);

    renderOutreachAcceptedPool();

  } catch (error) {
    if (els.messagePrepareConfirmError) {
      els.messagePrepareConfirmError.hidden =
        false;

      els.messagePrepareConfirmError.textContent =
        error.message ||
        String(error);
    }

    if (els.messagePreparationError) {
      els.messagePreparationError.hidden =
        false;

      els.messagePreparationError.textContent =
        error.message ||
        String(error);
    }

  } finally {
    state.messagePreparationSubmitting =
      false;

    if (els.messagePrepareConfirmButton) {
      els.messagePrepareConfirmButton.disabled =
        false;
    }

    renderMessagePreparation();
  }
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

  renderOutreachAcceptanceJobs(
    state.outreachRecentJobs
  );

  renderOutreachAcceptedPool();
  renderMessagePreparation();

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


    // Keep Accepted Pool and recipient preparation synchronized
    // with the existing Outreach polling loop.
    await Promise.all([
      loadOutreachAcceptedPool(),
      loadMessagePreparation(),
      loadMessageBatches()
    ]);


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

  const pageCopy = {
    overview: {
      eyebrow: "Workspace",
      title: "Tổng quan",
      subtitle: "Theo dõi trạng thái scanner, queue, worker và hoạt động gần nhất."
    },
    profiles: {
      eyebrow: "Scanner",
      title: "Profiles",
      subtitle: "Snapshot profile LinkedIn đã được thu thập và lưu trong database."
    },
    queue: {
      eyebrow: "Scanner",
      title: "Processing Queue",
      subtitle: "Theo dõi URL đang chờ, đang xử lý và lịch sử scan."
    },
    accounts: {
      eyebrow: "Infrastructure",
      title: "Accounts",
      subtitle: "Trạng thái các LinkedIn browser profiles đang phục vụ scanner."
    },
    youtube: {
      eyebrow: "Research",
      title: "YouTube Research",
      subtitle: "Khởi tạo research job và theo dõi kết quả channel theo thời gian thực."
    },
    outreach: {
      eyebrow: "Outreach",
      title: "Connect & Messaging",
      subtitle: "Connect profiles, kiểm tra acceptance và chuẩn bị recipient cho message workflow."
    },
    health: {
      eyebrow: "System",
      title: "Health",
      subtitle: "Kiểm tra worker heartbeat, service health và các vấn đề cần xử lý."
    }
  };

  const copy =
    pageCopy[tabName] ||
    pageCopy.overview;

  if (els.pageEyebrow) {
    els.pageEyebrow.textContent = copy.eyebrow;
  }

  if (els.pageTitle) {
    els.pageTitle.textContent = copy.title;
  }

  if (els.pageSubtitle) {
    els.pageSubtitle.textContent = copy.subtitle;
  }
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

function setOutreachProcessTab(
  tabName
) {
  const validTabs = new Set([
    "connect",
    "acceptance",
    "recipients",
    "messages"
  ]);

  const requested =
    String(
      tabName || "connect"
    ).trim();

  const cleaned =
    validTabs.has(requested)
      ? requested
      : "connect";

  state.outreachProcessTab =
    cleaned;

  document
    .querySelectorAll(
      "[data-outreach-process-tab]"
    )
    .forEach((button) => {
      const active =
        button.dataset.outreachProcessTab ===
        cleaned;

      button.classList.toggle(
        "is-active",
        active
      );

      button.setAttribute(
        "aria-selected",
        active ? "true" : "false"
      );
    });

  document
    .querySelectorAll(
      "[data-outreach-process-panel]"
    )
    .forEach((panel) => {
      panel.hidden =
        panel.dataset.outreachProcessPanel !==
        cleaned;
    });
}

els.rateLimitDrawerButton?.addEventListener(
  "click",
  openRateLimitDrawer
);

els.rateLimitDrawerClose?.addEventListener(
  "click",
  closeRateLimitDrawer
);

els.rateLimitDrawerBackdrop?.addEventListener(
  "click",
  closeRateLimitDrawer
);

document.addEventListener(
  "keydown",
  (event) => {
    if (
      event.key === "Escape" &&
      els.rateLimitDrawer?.classList.contains(
        "is-open"
      )
    ) {
      closeRateLimitDrawer();
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


document.addEventListener(
  "click",
  (event) => {
    const button =
      event.target.closest(
        "[data-outreach-process-tab]"
      );

    if (!button) {
      return;
    }

    event.preventDefault();

    setOutreachProcessTab(
      button.dataset.outreachProcessTab
    );
  }
);
els.outreachHistoryPrevPage?.addEventListener("click",()=>{state.outreachHistoryPage=Math.max(1,state.outreachHistoryPage-1);renderOutreachHistory(state.outreachRecentJobs)});
els.outreachHistoryNextPage?.addEventListener("click",()=>{state.outreachHistoryPage+=1;renderOutreachHistory(state.outreachRecentJobs)});
els.outreachAcceptancePrevPage?.addEventListener("click",()=>{state.outreachAcceptancePage=Math.max(1,state.outreachAcceptancePage-1);renderOutreachAcceptanceJobs(state.outreachRecentJobs)});
els.outreachAcceptanceNextPage?.addEventListener("click",()=>{state.outreachAcceptancePage+=1;renderOutreachAcceptanceJobs(state.outreachRecentJobs)});
els.messageBatchPrevPage?.addEventListener("click",()=>{state.messageBatchPage=Math.max(1,state.messageBatchPage-1);renderMessagePreparation()});
els.messageBatchNextPage?.addEventListener("click",()=>{state.messageBatchPage+=1;renderMessagePreparation()});

document.addEventListener(
  "click",
  (event) => {
    const button =
      event.target.closest(
        "[data-accepted-filter]"
      );

    if (!button) {
      return;
    }

    state.outreachAcceptedPoolFilter =
      button.dataset.acceptedFilter ||
      "all";

    state.outreachAcceptedPoolPage =
      1;

    renderOutreachAcceptedPool();
  }
);

els.outreachAcceptedAccountFilter?.addEventListener(
  "change",
  () => {
    state.outreachAcceptedAccountFilter =
      els.outreachAcceptedAccountFilter.value ||
      "all";

    state.outreachAcceptedPoolPage =
      1;

    renderOutreachAcceptedPool();
  }
);


els.outreachAcceptedPrevPage?.addEventListener(
  "click",
  () => {
    state.outreachAcceptedPoolPage =
      Math.max(
        1,
        state.outreachAcceptedPoolPage - 1
      );

    renderOutreachAcceptedPool();
  }
);

els.outreachAcceptedNextPage?.addEventListener(
  "click",
  () => {
    state.outreachAcceptedPoolPage += 1;
    renderOutreachAcceptedPool();
  }
);

els.outreachAcceptedSelectPage?.addEventListener(
  "change",
  () => {
    const pageItems =
      getAcceptedPoolPageData().pageItems;

    const eligibleIds =
      getEligibleMessageProspectIds();

    pageItems.forEach((item) => {
      const prospectId =
        String(item.prospect_id || "").trim();

      if (
        !prospectId ||
        !eligibleIds.has(prospectId)
      ) {
        return;
      }

      if (els.outreachAcceptedSelectPage.checked) {
        state.outreachAcceptedSelectedProspectIds.add(prospectId);
      } else {
        state.outreachAcceptedSelectedProspectIds.delete(prospectId);
      }
    });

    renderOutreachAcceptedPool();
  }
);

els.messagePrepareSelectedButton?.addEventListener(
  "click",
  prepareSelectedMessageRecipients
);

els.messagePrepareAllButton?.addEventListener(
  "click",
  prepareAllMessageRecipients
);

els.messagePrepareConfirmCloseButton?.addEventListener(
  "click",
  closeMessagePrepareConfirmModal
);

els.messagePrepareConfirmCancelButton?.addEventListener(
  "click",
  closeMessagePrepareConfirmModal
);

els.messagePrepareConfirmModal
  ?.querySelectorAll(
    "[data-message-prepare-close]"
  )
  .forEach((element) => {
    element.addEventListener(
      "click",
      closeMessagePrepareConfirmModal
    );
  });

els.messagePrepareConfirmButton?.addEventListener(
  "click",
  confirmMessagePreparation
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


if (els.messageSendCloseButton) {
  els.messageSendCloseButton.addEventListener(
    "click",
    closeMessageSendModal
  );
}

if (els.messageSendCancelButton) {
  els.messageSendCancelButton.addEventListener(
    "click",
    closeMessageSendModal
  );
}

if (els.messageSendModal) {
  els.messageSendModal
    .querySelectorAll(
      "[data-message-send-close]"
    )
    .forEach((element) => {
      element.addEventListener(
        "click",
        closeMessageSendModal
      );
    });
}

if (els.messageSendConfirmButton) {
  els.messageSendConfirmButton.addEventListener(
    "click",
    async () => {
      const batchId =
        state.messageSendSelectedBatchId;

      const template =
        els.messageTemplateInput?.value ||
        "";

      try {
        if (els.messageSendError) {
          els.messageSendError.hidden = true;
          els.messageSendError.textContent = "";
        }

        await queueMessageBatchForSending(
          batchId,
          template
        );

      } catch (error) {
        console.error(
          "Queue message batch error:",
          error
        );

        if (els.messageSendError) {
          els.messageSendError.textContent =
            error.message ||
            String(error);

          els.messageSendError.hidden = false;
        }
      }
    }
  );
}

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


document.addEventListener(
  "DOMContentLoaded",
  () => {
    setOutreachProcessTab(
      state.outreachProcessTab || "connect"
    );
  },
  {
    once: true
  }
);
