/* Rubin IDAC Dashboard — render logic.
 *
 * Loads idacs.json (built by scripts/build.py from data/idacs/*.yaml) and
 * paints: summary stats, world map, comparison table, data-products matrix,
 * and a full profile card per IDAC.
 */
(() => {
  "use strict";

  const PRODUCT_LABELS = {
    object_table_subset: "Object Table (subset)",
    object_table:        "Object Table",
    source_table:        "Source Table",
    forced_source_table: "ForcedSource Table",
    dia_object_table:    "DIAObject Table",
    dia_source_table:    "DIASource Table",
    solar_system_tables: "Solar System Tables",
    co_added_images:     "Co-added Images",
    visit_images:        "Visit Images",
    difference_images:   "Difference Images",
    template_images:     "Template Images",
    other_data_products: "Other Data Products",
  };
  const PRODUCT_KEYS = Object.keys(PRODUCT_LABELS);

  const REPO  = document.body.dataset.repo || "";
  const BRANCH = document.body.dataset.branch || "main";

  // ----- utilities ---------------------------------------------------------

  function fmtNum(n, digits = 0) {
    if (n === null || n === undefined || Number.isNaN(n)) return "—";
    return n.toLocaleString(undefined, { maximumFractionDigits: digits });
  }

  function escapeHtml(s) {
    return String(s ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function el(html) {
    const t = document.createElement("template");
    t.innerHTML = html.trim();
    return t.content.firstElementChild;
  }

  function productCount(idac) {
    return PRODUCT_KEYS.reduce((acc, k) => acc + (idac.data_products[k] ? 1 : 0), 0);
  }

  // ----- repo links --------------------------------------------------------

  function repoLink(path = "") {
    if (!REPO) return "#";
    return path
      ? `${REPO}/blob/${BRANCH}/${path}`
      : REPO;
  }
  document.getElementById("repo-link").href = repoLink();
  document.getElementById("repo-link-footer").href = repoLink();

  // ----- stats -------------------------------------------------------------

  function renderStats(idacs) {
    const total = idacs.reduce((a, r) => ({
      storage: a.storage + (r.capacity.storage_pb_years || 0),
      cpu:     a.cpu     + (r.capacity.cpu_mhrs || 0),
      gpu:     a.gpu     + (r.capacity.gpu_mhrs || 0),
      users:   a.users   + (r.capacity.expected_local_users || 0),
    }), { storage: 0, cpu: 0, gpu: 0, users: 0 });

    const items = [
      { label: "IDACs",                value: idacs.length,       unit: "",        icon: "🌐" },
      { label: "Total Storage",        value: fmtNum(total.storage), unit: "PB-yr", icon: "💾" },
      { label: "Total CPU",            value: fmtNum(total.cpu),     unit: "Mhrs",  icon: "🖥️" },
      { label: "Total GPU",            value: fmtNum(total.gpu),     unit: "Mhrs",  icon: "⚡" },
      { label: "Expected Local Users", value: fmtNum(total.users),   unit: "",      icon: "👥" },
    ];

    const row = document.getElementById("stats-row");
    row.innerHTML = items.map(it => `
      <div class="col-sm-6 col-lg">
        <div class="card card-sm">
          <div class="card-body">
            <div class="row align-items-center">
              <div class="col-auto">
                <span class="bg-primary-lt avatar stat-card-icon">${it.icon}</span>
              </div>
              <div class="col">
                <div class="font-weight-medium">${it.value} <span class="text-muted small">${it.unit}</span></div>
                <div class="text-muted small">${it.label}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `).join("");
  }

  // ----- map ---------------------------------------------------------------

  function renderMap(idacs) {
    const map = L.map("map", { worldCopyJump: true, scrollWheelZoom: false }).setView([25, 10], 2);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 9, minZoom: 2,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);

    const maxStorage = Math.max(...idacs.map(r => r.capacity.storage_pb_years || 0), 1);

    idacs.forEach(idac => {
      const { lat, lng, city, institution } = idac.location;
      const storage = idac.capacity.storage_pb_years || 0;
      const radius = 6 + 18 * Math.sqrt(storage / maxStorage);
      const m = L.circleMarker([lat, lng], {
        radius,
        color: "#a93a18",
        weight: 2,
        fillColor: "#d35224",
        fillOpacity: 0.65,
      }).addTo(map);

      m.bindPopup(`
        <b>${escapeHtml(idac.country)}</b><br>
        ${escapeHtml(city)} &mdash; ${escapeHtml(institution)}<br>
        Storage: ${fmtNum(storage)} PB-yr<br>
        CPU: ${fmtNum(idac.capacity.cpu_mhrs)} Mhrs
        ${idac.capacity.gpu_mhrs ? `<br>GPU: ${fmtNum(idac.capacity.gpu_mhrs)} Mhrs` : ""}
        <br><a href="#${idac.slug}">Open full profile &rarr;</a>
      `);
    });

    setTimeout(() => map.invalidateSize(), 50);
  }

  // ----- comparison table --------------------------------------------------

  let sortState = { key: "storage_pb_years", dir: "desc" };

  function valueFor(idac, key) {
    if (key === "country") return idac.country;
    if (key === "product_count") return productCount(idac);
    return idac.capacity[key];
  }

  function renderComparisonTable(idacs) {
    const tbody = document.querySelector("#comparison-table tbody");
    const sorted = [...idacs].sort((a, b) => {
      const va = valueFor(a, sortState.key);
      const vb = valueFor(b, sortState.key);
      // Push nulls to the bottom regardless of direction.
      if (va === null || va === undefined) return 1;
      if (vb === null || vb === undefined) return -1;
      if (typeof va === "string") {
        return sortState.dir === "asc" ? va.localeCompare(vb) : vb.localeCompare(va);
      }
      return sortState.dir === "asc" ? va - vb : vb - va;
    });

    tbody.innerHTML = sorted.map(idac => `
      <tr>
        <td><a href="#${idac.slug}" class="text-reset" style="font-weight:500;">${escapeHtml(idac.country)}</a>
          <div class="text-muted small">${escapeHtml(idac.location.city)}</div></td>
        <td class="text-end">${fmtNum(idac.capacity.storage_pb_years)}</td>
        <td class="text-end">${fmtNum(idac.capacity.free_storage_pb_years, 1)}</td>
        <td class="text-end">${fmtNum(idac.capacity.cpu_mhrs)}</td>
        <td class="text-end">${fmtNum(idac.capacity.free_cpu_mhrs, 1)}</td>
        <td class="text-end">${idac.capacity.gpu_mhrs ? fmtNum(idac.capacity.gpu_mhrs) : '<span class="text-muted">—</span>'}</td>
        <td class="text-end">${fmtNum(idac.capacity.expected_local_users)}</td>
        <td><span class="badge bg-primary-lt">${productCount(idac)} / ${PRODUCT_KEYS.length}</span></td>
      </tr>
    `).join("");

    document.querySelectorAll("#comparison-table th.sortable").forEach(th => {
      th.classList.remove("sort-asc", "sort-desc");
      if (th.dataset.key === sortState.key) {
        th.classList.add(sortState.dir === "asc" ? "sort-asc" : "sort-desc");
      }
    });
  }

  function wireSortHandlers(idacs) {
    document.querySelectorAll("#comparison-table th.sortable").forEach(th => {
      th.addEventListener("click", () => {
        const key = th.dataset.key;
        if (sortState.key === key) {
          sortState.dir = sortState.dir === "asc" ? "desc" : "asc";
        } else {
          sortState.key = key;
          sortState.dir = (key === "country") ? "asc" : "desc";
        }
        renderComparisonTable(idacs);
      });
    });
  }

  // ----- data-products matrix ---------------------------------------------

  function renderMatrix(idacs) {
    const table = document.getElementById("products-matrix");
    const headers = ["<th>Country</th>"].concat(
      PRODUCT_KEYS.map(k => `<th class="product">${escapeHtml(PRODUCT_LABELS[k])}</th>`)
    ).join("");

    const sorted = [...idacs].sort((a, b) => a.country.localeCompare(b.country));
    const rows = sorted.map(idac => {
      const cells = PRODUCT_KEYS.map(k => {
        const yes = idac.data_products[k];
        return yes
          ? `<td class="yes" title="${escapeHtml(PRODUCT_LABELS[k])}">✓</td>`
          : `<td class="no" title="${escapeHtml(PRODUCT_LABELS[k])} — not hosted">·</td>`;
      }).join("");
      return `<tr><td class="country-cell"><a href="#${idac.slug}">${escapeHtml(idac.country)}</a></td>${cells}</tr>`;
    }).join("");

    table.innerHTML = `<thead><tr>${headers}</tr></thead><tbody>${rows}</tbody>`;
  }

  // ----- per-IDAC profile cards -------------------------------------------

  function textBlock(text, emptyMsg = "Not specified.") {
    if (!text || !text.trim()) {
      return `<div class="field-body is-empty">${escapeHtml(emptyMsg)}</div>`;
    }
    return `<div class="field-body">${escapeHtml(text.trim())}</div>`;
  }

  function hardwareSection(hw) {
    const rows = [
      ["CPU architecture",  hw.cpu_architecture],
      ["GPU architecture",  hw.gpu_architecture],
      ["Storage",           hw.storage_type],
      ["Network",           hw.network],
    ].filter(([, v]) => v && v.trim());

    if (!rows.length) {
      return `<div class="field-body is-empty">Hardware details TBD.</div>`;
    }
    return `<dl class="row mb-0" style="font-size:13px;">
      ${rows.map(([k, v]) => `
        <dt class="col-sm-4 text-muted" style="font-weight:500;">${escapeHtml(k)}</dt>
        <dd class="col-sm-8 mb-1">${escapeHtml(v)}</dd>
      `).join("")}
    </dl>`;
  }

  function chips(items, opts = {}) {
    const cls = opts.cls || "";
    if (!items || !items.length) {
      return `<div class="chip-list"><span class="chip muted">${escapeHtml(opts.empty || "none listed")}</span></div>`;
    }
    return `<div class="chip-list">${
      items.map(t => `<span class="chip ${cls}">${escapeHtml(t)}</span>`).join("")
    }</div>`;
  }

  function docsList(docs) {
    const live = (docs || []).filter(d => d.url && d.url.trim());
    if (!live.length) {
      return `<div class="field-body is-empty">No onboarding links provided yet.</div>`;
    }
    return `<ul class="list-unstyled mb-0">${live.map(d => `
      <li class="mb-1">
        <a class="doc-link" href="${escapeHtml(d.url)}" target="_blank" rel="noopener">
          ${escapeHtml(d.title || d.url)}
        </a>
      </li>
    `).join("")}</ul>`;
  }

  function contactsList(cs) {
    if (!cs || !cs.length) {
      return `<div class="field-body is-empty">No contacts listed.</div>`;
    }
    return cs.map(c => `
      <div class="contact-row">
        <span class="name">${escapeHtml(c.name || "")}</span>
        ${c.email ? `<span class="email"><a href="mailto:${escapeHtml(c.email)}">${escapeHtml(c.email)}</a></span>` : ""}
        ${c.role ? `<span class="role">${escapeHtml(c.role)}</span>` : ""}
      </div>
    `).join("");
  }

  function renderProfiles(idacs) {
    const sorted = [...idacs].sort((a, b) => a.country.localeCompare(b.country));
    const wrap = document.getElementById("idac-profiles");

    wrap.innerHTML = sorted.map(idac => {
      const c = idac.capacity;
      const productNames = PRODUCT_KEYS.filter(k => idac.data_products[k]).map(k => PRODUCT_LABELS[k]);

      return `
        <div class="col-md-6" id="${idac.slug}">
          <div class="card profile-card h-100">
            <div class="card-body">

              <h3 class="card-title">${escapeHtml(idac.country)}</h3>
              <div class="card-subtitle">
                ${escapeHtml(idac.location.city)} &mdash; ${escapeHtml(idac.location.institution)}
              </div>

              <div class="mini-stats">
                <div class="mini-stat">
                  <div class="label">Storage</div>
                  <div class="value">${fmtNum(c.storage_pb_years)} <span class="text-muted small">PB-yr</span></div>
                  <div class="sub">${c.free_storage_pb_years !== null ? fmtNum(c.free_storage_pb_years, 1) + " PB-yr free" : "&nbsp;"}</div>
                </div>
                <div class="mini-stat">
                  <div class="label">CPU</div>
                  <div class="value">${fmtNum(c.cpu_mhrs)} <span class="text-muted small">Mhrs</span></div>
                  <div class="sub">${c.free_cpu_mhrs !== null ? fmtNum(c.free_cpu_mhrs, 1) + " Mhrs free" : "&nbsp;"}</div>
                </div>
                <div class="mini-stat">
                  <div class="label">GPU</div>
                  <div class="value">${c.gpu_mhrs !== null ? fmtNum(c.gpu_mhrs) + ' <span class="text-muted small">Mhrs</span>' : '<span class="text-muted">—</span>'}</div>
                  <div class="sub">${c.free_gpu_mhrs !== null ? fmtNum(c.free_gpu_mhrs, 1) + " Mhrs free" : "&nbsp;"}</div>
                </div>
                <div class="mini-stat">
                  <div class="label">Expected Local Users</div>
                  <div class="value">${fmtNum(c.expected_local_users)}</div>
                  <div class="sub">${c.hosted_data_pb_years !== null ? fmtNum(c.hosted_data_pb_years, 1) + " PB-yr hosted data" : "&nbsp;"}</div>
                </div>
              </div>

              <div class="field-label">Rubin data products hosted</div>
              ${chips(productNames, { empty: "none listed" })}

              <div class="field-label">Rubin data releases</div>
              ${chips(idac.data_releases, { cls: "release", empty: "TBD" })}

              <div class="field-label">Hardware architecture</div>
              ${hardwareSection(idac.hardware)}

              <div class="field-label">Software services &amp; platform</div>
              ${textBlock(idac.software_services)}

              <div class="field-label">Complementary datasets hosted</div>
              ${textBlock(idac.complementary_datasets, "No complementary datasets listed.")}

              <div class="field-label">Science use cases</div>
              ${textBlock(idac.use_cases)}

              <div class="field-label">Science Collaboration agreements</div>
              ${textBlock(idac.science_collaboration_agreements, "None recorded yet.")}

              <div class="field-label">Onboarding &amp; documentation</div>
              ${docsList(idac.documentation)}

              <div class="field-label">Contacts</div>
              ${contactsList(idac.contacts)}

              ${idac.notes && idac.notes.trim() ? `
                <div class="field-label">Notes</div>
                ${textBlock(idac.notes)}
              ` : ""}

              <a class="edit-link" href="${repoLink(idac._source_file)}" target="_blank" rel="noopener">
                ✎ Edit this profile on GitHub (${escapeHtml(idac._source_file || "")})
              </a>

            </div>
          </div>
        </div>
      `;
    }).join("");
  }

  // ----- bootstrap ---------------------------------------------------------

  function showError(msg) {
    document.getElementById("loading").style.display = "none";
    const e = document.getElementById("error");
    e.style.display = "block";
    e.innerHTML = `<strong>Could not load IDAC data.</strong><br>${escapeHtml(msg)}<br><br>
      Has <code>scripts/build.py</code> been run since the last data change?`;
  }

  async function init() {
    try {
      const res = await fetch("idacs.json", { cache: "no-cache" });
      if (!res.ok) throw new Error("HTTP " + res.status + " loading idacs.json");
      const payload = await res.json();
      const idacs = payload.idacs || [];
      if (!idacs.length) throw new Error("idacs.json contains no IDAC records.");

      document.getElementById("loading").style.display = "none";
      document.getElementById("dashboard").style.display = "block";
      document.getElementById("generated-stamp").textContent =
        "data built " + new Date(payload.generated_at).toISOString().slice(0, 10);

      renderStats(idacs);
      renderMap(idacs);
      renderComparisonTable(idacs);
      wireSortHandlers(idacs);
      renderMatrix(idacs);
      renderProfiles(idacs);

      // If we landed on a #slug, scroll there after render.
      if (location.hash) {
        const target = document.querySelector(location.hash);
        if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    } catch (err) {
      console.error(err);
      showError(err.message || String(err));
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
