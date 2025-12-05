// src/main.js
document.addEventListener("DOMContentLoaded", () => {

  // ---------------------------------------------------
  // Demographic groups (UI keys) → pretty labels
  // ---------------------------------------------------
  const GROUPS = {
    race: ["White","Black","Native","Asian","Two or more"],
    gender: ["Male","Female"],
    age: ["18-29","30-44","45-64","65+"],
    education: ["HS or less","Some college","Associate","Bachelor","Graduate"],
    urban_rural: ["Urban","Rural"]
  };

  // ---------------------------------------------------
  // Mapping UI label → CSV column suffix
  // (CSV columns are pct_<suffix>)
  // ---------------------------------------------------
  const KEY_TO_COL = {
    // Race
    "White": "white",
    "Black": "black",
    "Native": "native",
    "Asian": "asian",
    "Two or more": "two_or_more",

    // Age
    "18-29": "18_29",
    "30-44": "30_44",
    "45-64": "45_64",
    "65+": "65_plus",

    // Education
    "HS or less": "hs_or_less",
    "Some college": "some_college",
    "Associate": "assoc",
    "Bachelor": "bachelor",
    "Graduate": "grad",

    // Urban / rural
    "Urban": "urban",
    "Rural": "rural"
  };

  // ---------------------------------------------------
  // Fallback sanitizer: pretty key -> probable CSV suffix
  // (used if KEY_TO_COL doesn't contain the key)
  // ---------------------------------------------------
  function keyToColSuffix(key) {
    if (!key || typeof key !== "string") return null;
    // common replacements
    return key
      .replace(/\+/g, "_plus")
      .replace(/&/g, "and")
      .replace(/\s+or\s+/ig, "_or_")
      .replace(/[^a-z0-9]+/ig, "_")
      .replace(/^_+|_+$/g, "")
      .toLowerCase();
  }

  // ---------------------------------------------------
  // DOM refs
  // ---------------------------------------------------
  const yearSelect = d3.select("#yearSelect");
  const stateSelect = d3.select("#stateSelect");
  const slidersDiv = d3.select("#sliders");
  const chartTitle = d3.select("#chartTitle");
  const svg = d3.select("#pie");
  const legendDiv = d3.select("#legend");
  const status = d3.select("#status");

  // ---------------------------------------------------
  // Pie setup
  // ---------------------------------------------------
  const W = +svg.attr("width") || 360;
  const H = +svg.attr("height") || 360;
  const R = Math.min(W, H) / 2 - 8;

  const g = svg.append("g").attr("transform", `translate(${W/2},${H/2})`);
  const arc = d3.arc().innerRadius(0).outerRadius(R);
  const pieGen = d3.pie().value(d => d.value).sort(null);

  const COLORS = { dem: "#2b8cbe", rep: "#f03b20" };

  // ---------------------------------------------------
  // Runtime state
  // ---------------------------------------------------
  let acs = null;
  let presets = null;
  const sliders = {};
  Object.keys(GROUPS).forEach(g => sliders[g] = Object.fromEntries(GROUPS[g].map(k => [k, 0.5])));

  // ---------------------------------------------------
  // Load CSV + JSON
  // ---------------------------------------------------
  async function loadData() {
    const csvPath = "data/final_state_dataset.csv";
    const jsonPath = "data/election_presets.json";
    try {
      const [csvData, jsonData] = await Promise.all([d3.csv(csvPath), d3.json(jsonPath)]);
      return { csvData, jsonData };
    } catch (err) {
      console.error("loadData error:", err);
      throw err;
    }
  }

  // ---------------------------------------------------
  // Normalize preset entry (0..1)
  // ---------------------------------------------------
  function normalizeEntry(e) {
    if (!e) return { Dem: 0.5, Rep: 0.5 };
    let dem = e.Dem ?? e.dem ?? 0.5;
    let rep = e.Rep ?? e.rep ?? (1 - dem);

    dem = Number(dem);
    rep = Number(rep);

    if (!Number.isFinite(dem)) dem = 0.5;
    if (!Number.isFinite(rep)) rep = 1 - dem;

    // treat >1 as percent
    if (dem > 1) dem = dem / 100;
    if (rep > 1) rep = rep / 100;

    // clamp
    dem = Math.max(0, Math.min(1, dem));
    rep = Math.max(0, Math.min(1, rep));

    return { Dem: dem, Rep: rep };
  }

  // ---------------------------------------------------
  // Build UI
  // ---------------------------------------------------
function buildSlidersUI(year) {
  slidersDiv.html(""); // clear old sliders

  Object.keys(GROUPS).forEach(group => {
    const box = slidersDiv.append("div").attr("class", "group");
    box.append("h4").text(group.toUpperCase());

    GROUPS[group].forEach(key => {
      const row = box.append("div").attr("class", "row");

      // Label with population placeholder
      const labelSel = row.append("label").text(key);
      const labelNode = labelSel.node();

      // Left (Dem) span
      const leftSpan = row.append("span")
        .attr("class", "left-val")
        .style("width","36px")
        .style("text-align","left")
        .style("color","#2b8cbe"); // blue

      // Slider input
      const input = row.append("input")
        .attr("type","range")
        .attr("min",0)
        .attr("max",1)
        .attr("step",0.01)
        .attr("value", sliders[group][key]);

      // Right (Rep) span
      const rightSpan = row.append("span")
        .attr("class", "right-val")
        .style("width","36px")
        .style("text-align","right")
        .style("color","#f03b20"); // red

      // Store meta
      input.node().__meta = { group, key, labelNode, leftSpan, rightSpan };

      // Input handler
      input.on("input", function() {
      const val = Number(this.value);
      sliders[group][key] = val;

      leftSpan.text(Math.round(val*100)+"%");
      rightSpan.text(Math.round((1-val)*100)+"%");

      // Dot color
      const r = Math.round( (1-val)*43 + val*240 );
      const g = Math.round( (1-val)*140 + val*59 );
      const b = Math.round( (1-val)*190 + val*32 );
      this.style.setProperty("--thumb-color", `rgb(${r},${g},${b})`);

      // Gradient 
      const percent = val * 100;
      this.style.background = `linear-gradient(to right, 
        #2b8cbe 0%, 
        #2b8cbe ${percent}%, 
        #888 ${percent}%, 
        #888 ${percent+0.1}%, 
        #f03b20 ${percent+0.1}%, 
        #f03b20 100%)`;

        drawForSelected();
      });

      // initialization
      input.dispatch("input");
    });
  });
}




  // ---------------------------------------------------
  // Update population labels for sliders
  // ---------------------------------------------------
 function updateSliderPopulationLabels(stateRow) {
  slidersDiv.selectAll("input").each(function() {
    const meta = this.__meta;
    if (!meta) return;
    const { key, labelNode } = meta;

    let pct = 0;

    // gender special case
    if (key === "Male" || key === "Female") {
      const m = Number(stateRow["male_pop"]);
      const f = Number(stateRow["female_pop"]);
      if (Number.isFinite(m) && Number.isFinite(f) && (m+f)>0) {
        pct = (key === "Male" ? m/(m+f) : f/(m+f));
      }
    } else {
      const explicit = KEY_TO_COL[key];
      const colSuffix = explicit ?? keyToColSuffix(key);
      if (colSuffix) {
        let raw = Number(stateRow[`pct_${colSuffix}`]);
        if (Number.isFinite(raw)) {
          if (raw > 1) raw = raw / 100;
          pct = raw;
        } else {
          pct = 0;
        }
      } else {
        pct = 0;
      }
    }

    const pctStr = (pct * 100).toFixed(1) + "%";

    // Update the label DOM node safely: ex. "White (65.4%)"
    if (labelNode && labelNode instanceof HTMLElement) {
      d3.select(labelNode).text(`${key} (${pctStr})`);
    }
  });
}

  // ---------------------------------------------------
  // Compute state Dem share with robust logging and fallbacks
  // ---------------------------------------------------
  function computeStateDemShare(row, year) {
    if (!row) return 0.5;
    const yearPresets = (presets && presets[year]) ? presets[year] : {};

    let totalDem = 0;
    let totalPop = 0;

    const groupBreakdown = {}; // for debugging

    Object.keys(GROUPS).forEach(group => {
      groupBreakdown[group] = { popSum: 0, demSum: 0, missingCols: [] };

      GROUPS[group].forEach(key => {
        // population fraction for this subgroup
        let pct = 0;
        if (key === "Male" || key === "Female") {
          const m = Number(row["male_pop"]);
          const f = Number(row["female_pop"]);
          if (Number.isFinite(m) && Number.isFinite(f) && (m+f) > 0) {
            pct = (key === "Male" ? m/(m+f) : f/(m+f));
          } else {
            pct = 0;
            groupBreakdown[group].missingCols.push(`male_pop/female_pop`);
          }
        } else {
          const explicit = KEY_TO_COL[key];
          const colSuffix = explicit ?? keyToColSuffix(key);
          if (!colSuffix) {
            pct = 0;
            groupBreakdown[group].missingCols.push(`no-col-for:${key}`);
          } else {
            const rawVal = row[`pct_${colSuffix}`];
            let raw = Number(rawVal);
            if (!Number.isFinite(raw)) {
              pct = 0;
              groupBreakdown[group].missingCols.push(`pct_${colSuffix}`);
            } else {
              if (raw > 1) raw = raw / 100;
              pct = raw;
            }
          }
        }

        // preference: slider (if numeric) else preset
        const preset = normalizeEntry(yearPresets[group]?.[key]);
        const sliderVal = sliders[group] && typeof sliders[group][key] === "number" ? Number(sliders[group][key]) : null;
        const pref = (sliderVal !== null && Number.isFinite(sliderVal)) ? sliderVal : preset.Dem;

        // accumulate
        totalDem += pct * pref;
        totalPop += pct;

        groupBreakdown[group].popSum += pct;
        groupBreakdown[group].demSum += pct * pref;
      });
    });

    const demShare = totalPop > 0 ? (totalDem / totalPop) : 0.5;

    // Debugging output
    console.debug("DEM DEBUG", {
      state: row.state_name,
      year,
      totalPop,
      totalDem,
      demShare,
      groups: groupBreakdown,
      allSlidersAllOne: areAllSlidersOne()
    });

    // If all slider values are exactly 1, demShare should be 1. 
    if (areAllSlidersOne() && Math.abs(demShare - 1) > 1e-9) {
      console.warn(`DEM sanity check failed for ${row.state_name} ${year}: all sliders=1 but demShare=${demShare}. Check missing columns listed above.`);
    }

    return Math.max(0, Math.min(1, demShare));
  }

  // helper: are all sliders exactly 1?
  function areAllSlidersOne() {
    return Object.keys(GROUPS).every(group =>
      GROUPS[group].every(k => Number(sliders[group][k]) === 1)
    );
  }

  // ---------------------------------------------------
  // Draw pie
  // ---------------------------------------------------
  function drawPie(demShare, stateName, year) {
    g.selectAll("*").remove();
    chartTitle.text(`How ${stateName} Might Vote — ${year}`);

    const data = [{key:"Republican", value:1-demShare}, {key:"Democrat", value:demShare}];

    g.selectAll("path").data(pieGen(data)).join("path")
      .attr("d", arc)
      .attr("fill", d => d.data.key === "Democrat" ? COLORS.dem : COLORS.rep)
      .attr("stroke", "#fff").attr("stroke-width", 1.5);

    g.selectAll("text.lab").data(pieGen(data)).join("text")
      .attr("class", "lab")
      .attr("transform", d => `translate(${arc.centroid(d)})`)
      .attr("text-anchor", "middle")
      .style("font-weight", "700")
      .style("font-size", "12px")
      .text(d => `${d.data.key}: ${(d.data.value*100).toFixed(1)}%`);

    legendDiv.html("");
    legendDiv.append("div").html(`<span class="sw" style="background:${COLORS.dem}"></span>Democrat: ${(demShare*100).toFixed(1)}%`);
    legendDiv.append("div").html(`<span class="sw" style="background:${COLORS.rep}"></span>Republican: ${((1-demShare)*100).toFixed(1)}%`);
  }

  // ---------------------------------------------------
  // Draw for selected
  // ---------------------------------------------------
  function drawForSelected() {
    const stateName = stateSelect.property("value");
    const year = yearSelect.property("value");
    if (!stateName) {
      status.text("Choose a state");
      g.selectAll("*").remove();
      return;
    }
    const row = acs.find(r => r.state_name === stateName);
    if (!row) {
      status.text("State not found");
      return;
    }
    status.text("");
    updateSliderPopulationLabels(row);
    const dem = computeStateDemShare(row, year);
    drawPie(dem, stateName, year);
  }

  // ---------------------------------------------------
  // Initialize
  // ---------------------------------------------------
  (async function init() {
    try {
      const { csvData, jsonData } = await loadData();
      acs = csvData;
      presets = jsonData;

      // years
      const years = Object.keys(presets || {});
      yearSelect.selectAll("option").data(years).join("option")
        .attr("value", d => d).text(d => d);
      const defaultYear = years.includes("2024") ? "2024" : years[years.length - 1];
      if (defaultYear) yearSelect.property("value", defaultYear);

      // states
      const names = acs.map(r => r.state_name).filter(Boolean).sort((a,b) => a.localeCompare(b));
      stateSelect.selectAll("option").data([""].concat(names)).join("option")
        .attr("value", d => d).text(d => d === "" ? "— Select a state —" : d);

      // initialize sliders from presets
      const presY = presets?.[defaultYear] || {};
      Object.keys(GROUPS).forEach(group => GROUPS[group].forEach(key => {
        sliders[group][key] = normalizeEntry(presY[group]?.[key]).Dem;
      }));

      buildSlidersUI(defaultYear);

      yearSelect.on("change", () => {
        const y = yearSelect.property("value");
        const presY = presets?.[y] || {};
        Object.keys(GROUPS).forEach(group => GROUPS[group].forEach(key => {
          sliders[group][key] = normalizeEntry(presY[group]?.[key]).Dem;
        }));
        buildSlidersUI(y);
        drawForSelected();
      });

      stateSelect.on("change", drawForSelected);

      // auto-select first state if none chosen
      if (!stateSelect.property("value") && names.length) {
        stateSelect.property("value", names[0]);
      }

      drawForSelected();

    } catch (err) {
      console.error("init error:", err);
      chartTitle.text("Error loading data — see console");
      status.html(`<span class="error">Failed to load data files.</span>`);
    }
  })();

});
