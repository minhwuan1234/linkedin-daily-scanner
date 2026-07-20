const config = window.APP_CONFIG || {};

const els = {
  refreshButton: document.querySelector("#refreshButton"),
  totalProfiles: document.querySelector("#totalProfiles"),
  scannedToday: document.querySelector("#scannedToday"),
  completeProfiles: document.querySelector("#completeProfiles"),
  lastUpdated: document.querySelector("#lastUpdated"),
  resultSummary: document.querySelector("#resultSummary"),
  searchInput: document.querySelector("#searchInput"),
  sortSelect: document.querySelector("#sortSelect"),
  errorState: document.querySelector("#errorState"),
  emptyState: document.querySelector("#emptyState"),
  tableWrap: document.querySelector("#tableWrap"),
  profileTableBody: document.querySelector("#profileTableBody"),
  drawerBackdrop: document.querySelector("#drawerBackdrop"),
  detailDrawer: document.querySelector("#detailDrawer"),
  drawerName: document.querySelector("#drawerName"),
  drawerContent: document.querySelector("#drawerContent"),
  closeDrawerButton: document.querySelector("#closeDrawerButton")
};

const state = {
  profiles: [],
  filteredProfiles: []
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

  if (Number.isNaN(date.getTime())) return String(value);

  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(date);
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

async function loadProfiles() {
  els.refreshButton.disabled = true;
  els.errorState.hidden = true;

  const { data, error } = await client
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
        "experience_raw_text"
      ].join(",")
    )
    .not("name", "is", null)
    .order("scraped_at", { ascending: false })
    .limit(1000);

  els.refreshButton.disabled = false;

  if (error) {
    els.errorState.textContent =
      `Không thể tải dữ liệu: ${error.message}`;
    els.errorState.hidden = false;
    els.tableWrap.hidden = true;
    els.resultSummary.textContent = "Không tải được dữ liệu.";
    return;
  }

  state.profiles = getLatestSnapshots(data || []);
  updateStats();
  applyFilters();
}

function updateStats() {
  const profiles = state.profiles;

  const latestDate = profiles
    .map((profile) => profile.scraped_at)
    .filter(Boolean)
    .sort()
    .at(-1);

  els.totalProfiles.textContent =
    profiles.length.toLocaleString("vi-VN");

  els.scannedToday.textContent =
    profiles
      .filter((profile) => isToday(profile.scraped_at))
      .length.toLocaleString("vi-VN");

  els.completeProfiles.textContent =
    profiles
      .filter(isComplete)
      .length.toLocaleString("vi-VN");

  els.lastUpdated.textContent = formatDate(latestDate);
}

function applyFilters() {
  const query = els.searchInput.value.trim().toLowerCase();
  const sort = els.sortSelect.value;

  const filtered = state.profiles.filter((profile) => {
    const searchable = [
      profile.name,
      profile.headline,
      profile.location,
      profile.linkedin_url
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
  renderTable();
}

function renderTable() {
  const profiles = state.filteredProfiles;

  els.resultSummary.textContent =
    `${profiles.length.toLocaleString("vi-VN")} profiles`;

  els.emptyState.hidden = profiles.length > 0;
  els.tableWrap.hidden = profiles.length === 0;

  els.profileTableBody.innerHTML = profiles
    .map((profile) => {
      return `
        <tr
          class="profile-row"
          data-profile-id="${escapeHtml(profile.id)}"
          tabindex="0"
        >
          <td>
            <div class="profile-cell">
              <div class="avatar">
                ${escapeHtml(
                  getInitials(profile.name)
                )}
              </div>

              <div class="profile-copy">
                <p class="profile-name">
                  ${escapeHtml(profile.name)}
                </p>

                <p class="profile-headline">
                  ${escapeHtml(
                    profile.headline ||
                    "Không có headline"
                  )}
                </p>
              </div>
            </div>
          </td>

          <td>
            ${escapeHtml(
              profile.location || "—"
            )}
          </td>

          <td>
            ${escapeHtml(
              profile.followers_count_text ||
              "—"
            )}
          </td>

          <td>
            ${escapeHtml(
              profile.connections_count_text ||
              "—"
            )}
          </td>

          <td class="muted-cell">
            ${escapeHtml(
              formatDate(profile.scraped_at)
            )}
          </td>
        </tr>
      `;
    })
    .join("");
}

function openProfileFromRow(row) {
  const profileId = String(
    row.dataset.profileId
  );

  const profile = state.profiles.find(
    (item) => String(item.id) === profileId
  );

  if (!profile) {
    console.error(
      "Không tìm thấy profile:",
      profileId
    );

    return;
  }

  openDrawer(profile);
}


els.profileTableBody.addEventListener(
  "click",
  (event) => {
    const row = event.target.closest(
      ".profile-row"
    );

    if (!row) {
      return;
    }

    openProfileFromRow(row);
  }
);


els.profileTableBody.addEventListener(
  "keydown",
  (event) => {
    if (
      event.key !== "Enter" &&
      event.key !== " "
    ) {
      return;
    }

    const row = event.target.closest(
      ".profile-row"
    );

    if (!row) {
      return;
    }

    event.preventDefault();
    openProfileFromRow(row);
  }
);

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
    : "<p>Không có LinkedIn URL.</p>";

  els.drawerContent.innerHTML = `
    <section class="detail-section">
      <h3>Thông tin chính</h3>

      <dl class="detail-grid">
        <dt>Headline</dt>
        <dd>${escapeHtml(profile.headline || "—")}</dd>

        <dt>Location</dt>
        <dd>${escapeHtml(profile.location || "—")}</dd>

        <dt>Followers</dt>
        <dd>${escapeHtml(profile.followers_count_text || "—")}</dd>

        <dt>Connections</dt>
        <dd>${escapeHtml(profile.connections_count_text || "—")}</dd>

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
        ${escapeHtml(profile.about_text || "Không có dữ liệu About.")}
      </p>
    </section>

    <section class="detail-section">
      <h3>Experience</h3>
      <p class="detail-pre">
        ${escapeHtml(profile.experience_raw_text || "Không có dữ liệu Experience.")}
      </p>
    </section>
  `;

  els.drawerBackdrop.hidden = false;
  els.detailDrawer.classList.add("is-open");
  els.detailDrawer.setAttribute(
    "aria-hidden",
    "false"
  );
  document.body.style.overflow = "hidden";
}

function closeDrawer() {
  els.drawerBackdrop.hidden = true;
  els.detailDrawer.classList.remove("is-open");
  els.detailDrawer.setAttribute(
    "aria-hidden",
    "true"
  );
  document.body.style.overflow = "";
}

els.refreshButton.addEventListener(
  "click",
  loadProfiles
);

els.searchInput.addEventListener(
  "input",
  applyFilters
);

els.sortSelect.addEventListener(
  "change",
  applyFilters
);

els.closeDrawerButton.addEventListener(
  "click",
  closeDrawer
);

els.drawerBackdrop.addEventListener(
  "click",
  closeDrawer
);

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeDrawer();
  }
});

loadProfiles();
