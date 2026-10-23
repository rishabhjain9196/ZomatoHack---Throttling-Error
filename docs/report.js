"use strict";
(() => {
  const data = window.HEATMAP_DATA;
  const byId = id => document.getElementById(id);
  if (!data || !data.zones || !data.profiles) {
    byId("load-error").hidden = false;
    byId("load-error").textContent = "The chart data could not be loaded. Check that report-data.js is beside this page, or use the CSV download.";
    return;
  }
  const colours = {monday: "#186b68", sunday: "#9b751d", "new-year": "#ad442b"};
  const names = {monday: "Monday", sunday: "Sunday", "new-year": "New Year"};
  const number = value => value.toLocaleString("en-GB", {maximumFractionDigits: 1});
  const svg = (width, height, label, content) => `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${label}">${content}</svg>`;
  const text = (x, y, value, anchor = "start") => `<text x="${x}" y="${y}" text-anchor="${anchor}">${value}</text>`;
  const line = (x1, y1, x2, y2, colour = "#d8dfdb") => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${colour}"/>`;
  const scenario = () => byId("scenario").value;
  const timeIndex = () => Number(byId("time").value);
  const currentDemand = () => data.profiles[scenario()][timeIndex()];
  function rows(target, values, colour) {
    const maximum = Math.max(...values.map(value => value.value), 1);
    byId(target).innerHTML = values.map(value => `<div class="rank-row"><span>${value.name}</span><div class="bar"><span style="width:${value.value / maximum * 100}%;background:${colour}"></span></div><strong>${number(value.value)}</strong></div>`).join("");
  }
  function drawMap(demand, scores) {
    const metric = byId("metric").value;
    const values = metric === "score" ? scores : demand;
    const maximum = Math.max(...values, 1);
    const map = data.map;
    let content = `<image href="bengaluru.webp" width="${map.width}" height="${map.height}"/>`;
    data.zones.forEach((zone, index) => {
      const x = ((zone.lon + 180) / 360 * 2 ** map.zoom * 256) - map.left;
      const rad = zone.lat * Math.PI / 180;
      const y = (1 - Math.asinh(Math.tan(rad)) / Math.PI) / 2 * 2 ** map.zoom * 256 - map.top;
      const share = values[index] / maximum;
      const radius = 13 + 25 * Math.sqrt(share);
      content += `<circle cx="${x}" cy="${y}" r="${radius}" fill="#ad442b" fill-opacity="${0.2 + share * 0.55}" stroke="white" stroke-width="2"><title>${zone.name}: ${number(values[index])} ${metric === "score" ? "demand per resource unit" : "synthetic demand units"}</title></circle>${text(x, y + 7, zone.id, "middle")}`;
    });
    byId("map").innerHTML = svg(map.width, map.height, `${names[scenario()]} at ${data.times[timeIndex()]}. Ten Bengaluru zone locations coloured by ${metric}. Exact values are in the table below.`, content);
  }
  function drawProfiles() {
    const width = Math.max(310, byId("profiles").clientWidth);
    const height = 270, left = 52, right = width - 15, top = 16, bottom = 230;
    const totals = Object.fromEntries(Object.entries(data.profiles).map(([key, values]) => [key, values.map(row => row.reduce((a, b) => a + b, 0))]));
    const maximum = Math.ceil(Math.max(...Object.values(totals).flat()) / 500) * 500;
    let content = "";
    for (let index = 0; index <= 4; index++) {
      const y = bottom - index / 4 * (bottom - top);
      content += line(left, y, right, y) + text(left - 8, y + 4, number(maximum * index / 4), "end");
    }
    for (const [key, values] of Object.entries(totals)) {
      const points = values.map((value, index) => `${left + index / 143 * (right - left)},${bottom - value / maximum * (bottom - top)}`).join(" ");
      content += `<polyline points="${points}" fill="none" stroke="${colours[key]}" stroke-width="${key === scenario() ? 3 : 1.6}" opacity="${key === scenario() ? 1 : 0.65}"/>`;
    }
    for (const index of [0, 36, 72, 108, 143]) content += text(left + index / 143 * (right - left), 252, data.times[index], "middle");
    const markerX = left + timeIndex() / 143 * (right - left);
    content += line(markerX, top, markerX, bottom, "#17343b");
    byId("profiles").innerHTML = svg(width, height, "Total synthetic demand by ten-minute interval for the three daily profiles. The vertical line marks the selected time.", content);
    const values = totals[scenario()];
    const peak = Math.max(...values), peakIndex = values.indexOf(peak);
    byId("profile-insight").textContent = `${names[scenario()]} reaches its largest recorded interval total at ${data.times[peakIndex]}, with ${number(peak)} synthetic demand units across ten zones. This is a property of the constructed profile, not a real-world demand estimate.`;
  }
  function drawHeatmap() {
    const values = data.profiles[scenario()];
    const hours = data.zones.map((zone, zoneIndex) => Array.from({length: 24}, (_, hour) => values.slice(hour * 6, hour * 6 + 6).reduce((sum, row) => sum + row[zoneIndex], 0) / 6));
    const maximum = Math.max(...hours.flat(), 1);
    let content = "";
    hours.forEach((row, zoneIndex) => {
      content += text(126, 38 + zoneIndex * 28, data.zones[zoneIndex].name, "end");
      row.forEach((value, hour) => {
        content += `<rect x="${140 + hour * 25}" y="${22 + zoneIndex * 28}" width="23" height="25" rx="2" fill="#186b68" fill-opacity="${0.08 + value / maximum * 0.92}"><title>${data.zones[zoneIndex].name}, ${hour}:00: ${number(value)} average synthetic demand</title></rect>`;
      });
    });
    for (let hour = 0; hour < 24; hour += 2) content += text(151 + hour * 25, 318, `${hour}:00`, "middle");
    content += text(140, 347, `Colour scale: 0 to ${number(maximum)} synthetic demand units per interval.`);
    byId("heatmap").innerHTML = svg(760, 365, `${names[scenario()]} hourly mean synthetic demand for ten zones. Darker cells indicate greater demand. Full values are available in the CSV download.`, content);
    byId("heatmap-scenario").textContent = names[scenario()];
  }
  function drawSequence() {
    const width = Math.max(280, byId("sequence").clientWidth), left = 52, right = width - 8, bottom = 200;
    const maximum = Math.max(...data.dailyTotals) * 1.05;
    const step = (right - left) / 28;
    let content = `<rect x="${left + step * 21}" y="10" width="${step * 7}" height="190" fill="#f5e9df"/>`;
    for (let index = 0; index <= 3; index++) {
      const y = bottom - index / 3 * 175;
      content += line(left, y, right, y) + text(left - 6, y + 4, `${Math.round(maximum * index / 3 / 1000)}k`, "end");
    }
    data.dailyTotals.forEach((value, index) => {
      const height = value / maximum * 175;
      content += `<rect x="${left + index * step + 1}" y="${bottom - height}" width="${Math.max(1, step - 2)}" height="${height}" fill="${index >= 21 ? colours["new-year"] : colours.monday}"><title>Day ${index + 1}: ${number(value)} synthetic demand units</title></rect>`;
    });
    for (const index of [0, 7, 14, 21, 27]) content += text(left + (index + 0.5) * step, 223, index + 1, "middle");
    content += text((left + right) / 2, 247, "Day in the synthetic sequence", "middle");
    byId("sequence").innerHTML = svg(width, 265, "Daily totals across the 28-day synthetic training sequence. The final seven days are shaded for baseline evaluation.", content);
  }
  function drawTransfer() {
    const from = Number(byId("origin").value), to = Number(byId("destination").value);
    const supply = data.zones.map(zone => zone.resources), demand = currentDemand();
    byId("units").max = supply[from];
    const units = Math.min(Number(byId("units").value), supply[from]);
    byId("units").value = units;
    byId("units-output").textContent = units;
    if (from !== to) { supply[from] -= units; supply[to] += units; }
    const score = index => demand[index] / Math.max(supply[index], 1);
    const before = index => demand[index] / Math.max(data.zones[index].resources, 1);
    byId("transfer-result").textContent = from === to
      ? "Both selections refer to the same zone. No units move, and the total remains 492."
      : `${units} units move from ${data.zones[from].name} to ${data.zones[to].name}. The total remains ${supply.reduce((a, b) => a + b, 0)}. ${supply[from] === 0 ? "The origin now has zero units; its score uses the denominator floor of one." : "The scores below show the trade-off."}`;
    const indices = from === to ? [from] : [from, to];
    rows("transfer-bars", indices.flatMap(index => [
      {name: `${data.zones[index].name}: before`, value: before(index)},
      {name: `${data.zones[index].name}: after`, value: score(index)},
    ]), colours.monday);
  }
  function update() {
    const demand = currentDemand();
    const scores = demand.map((value, index) => value / Math.max(data.zones[index].resources, 1));
    const label = `${names[scenario()]} at ${data.times[timeIndex()]}`;
    byId("time-output").textContent = data.times[timeIndex()];
    byId("time").setAttribute("aria-valuetext", data.times[timeIndex()]);
    byId("rank-time").textContent = data.times[timeIndex()];
    const ranking = data.zones.map((zone, index) => ({name: zone.name, value: scores[index]})).sort((a, b) => b.value - a.value);
    rows("ranking", ranking, colours["new-year"]);
    const topDemand = demand.indexOf(Math.max(...demand));
    byId("snapshot-insight").textContent = `${ranking[0].name} has the highest score (${number(ranking[0].value)}) at this time. ${data.zones[topDemand].name} has the highest demand (${number(demand[topDemand])} units). ${ranking[0].name === data.zones[topDemand].name ? "Both measures point to the same zone in this interval." : "The two measures point to different zones."}`;
    byId("zone-caption").textContent = label + ". Demand and resource units are synthetic demo quantities.";
    byId("zone-table").innerHTML = data.zones.map((zone, index) => `<tr><th scope="row">${zone.id}. ${zone.name}</th><td>${number(demand[index])}</td><td>${zone.resources}</td><td>${number(scores[index])}</td></tr>`).join("");
    drawMap(demand, scores);
    drawProfiles();
    drawHeatmap();
    drawTransfer();
  }
  ["origin", "destination"].forEach(id => {
    byId(id).innerHTML = data.zones.map((zone, index) => `<option value="${index}">${zone.name}</option>`).join("");
  });
  byId("destination").value = "5";
  document.querySelectorAll("[data-interactive]").forEach(element => { element.hidden = false; });
  ["scenario", "metric"].forEach(id => byId(id).addEventListener("change", update));
  byId("time").addEventListener("input", update);
  ["origin", "destination"].forEach(id => byId(id).addEventListener("change", drawTransfer));
  byId("units").addEventListener("input", drawTransfer);
  byId("reset").addEventListener("click", () => {
    byId("origin").value = "0"; byId("destination").value = "5"; byId("units").value = "10"; drawTransfer();
  });
  rows("baselines", data.baselines.map(baseline => ({name: baseline.name, value: baseline.mae})), colours.monday);
  const weekly = data.baselines.find(baseline => baseline.lag === 1008);
  const persistence = data.baselines.find(baseline => baseline.lag === 1);
  byId("baseline-insight").textContent = `The previous-week baseline has an MAE of ${number(weekly.mae)}, compared with ${number(persistence.mae)} for the previous interval. Repeated weekly construction makes seasonal baselines useful here; it does not establish performance on real demand.`;
  update();
  drawSequence();
  let resizeTimer;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => { drawProfiles(); drawSequence(); }, 100);
  });
})();
