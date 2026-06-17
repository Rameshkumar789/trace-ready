import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const DATA_DIR = "../data/regulatory/intelligence/generalization";
const OUTPUT_DIR = "../outputs/phase13-web2000-real-eval";
const INPUT_FILE = `${OUTPUT_DIR}/phase13-web2000-input.xlsx`;
const OUTPUT_FILE = `${OUTPUT_DIR}/phase13-web2000-results.xlsx`;

const [summary, records, results, metrics, sources] = await Promise.all([
  readJson(`${DATA_DIR}/phase13-web2000-summary.json`),
  readJson(`${DATA_DIR}/phase13-web2000-input-records.json`),
  readJson(`${DATA_DIR}/phase13-web2000-results.json`),
  readJson(`${DATA_DIR}/phase13-web2000-metrics.json`),
  readJson(`${DATA_DIR}/phase13-web2000-source-register.json`),
]);

await fs.mkdir(OUTPUT_DIR, { recursive: true });
await buildInputWorkbook();
await buildOutputWorkbook();
console.log(JSON.stringify({ inputFile: INPUT_FILE, outputFile: OUTPUT_FILE, records: records.length, metrics }, null, 2));

async function buildInputWorkbook() {
  const workbook = Workbook.create();
  const summarySheet = workbook.worksheets.add("Summary");
  const inputSheet = workbook.worksheets.add("Input_Records_2000");
  const sourcesSheet = workbook.worksheets.add("Source_Register");

  writeSummary(summarySheet, summary, metrics, "TraceReady Phase 13 Fresh Web-2000 Input Workbook");
  writeInputRecords(inputSheet, records);
  writeSources(sourcesSheet, sources);
  for (const sheet of [summarySheet, inputSheet, sourcesSheet]) {
    styleUsedRange(sheet);
  }
  await verifyWorkbook(workbook, [
    ["Summary", "A1:B18"],
    ["Input_Records_2000", "A1:O22"],
    ["Source_Register", "A1:D6"],
  ]);
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(INPUT_FILE);
}

async function buildOutputWorkbook() {
  const workbook = Workbook.create();
  const summarySheet = workbook.worksheets.add("Summary");
  const resultSheet = workbook.worksheets.add("Results_2000");
  const failuresSheet = workbook.worksheets.add("Failures");
  const metricsSheet = workbook.worksheets.add("Metrics");
  const sourcesSheet = workbook.worksheets.add("Source_Register");

  const recordsById = new Map(records.map((record) => [record.record_id, record]));
  writeSummary(summarySheet, summary, metrics, "TraceReady Phase 13 Fresh Web-2000 Results Workbook");
  writeResults(resultSheet, results, recordsById);
  writeFailures(failuresSheet, results, recordsById);
  writeMetrics(metricsSheet, metrics);
  writeSources(sourcesSheet, sources);
  for (const sheet of [summarySheet, resultSheet, failuresSheet, metricsSheet, sourcesSheet]) {
    styleUsedRange(sheet);
  }
  metricsSheet.charts.add("bar", {
    title: "Pass vs Fail",
    categories: ["Pass", "Fail"],
    series: [{ name: "Records", values: [metrics.pass_count, metrics.fail_count] }],
    hasLegend: false,
    from: { row: 1, col: 6 },
    extent: { widthPx: 420, heightPx: 260 },
  });
  metricsSheet.charts.add("bar", {
    title: "Precision, Recall, Exact Match",
    categories: ["Precision", "Recall", "Exact Match"],
    series: [{ name: "Rate", values: [metrics.precision, metrics.recall, metrics.exact_match_rate] }],
    hasLegend: false,
    from: { row: 16, col: 6 },
    extent: { widthPx: 420, heightPx: 260 },
  });
  await verifyWorkbook(workbook, [
    ["Summary", "A1:B18"],
    ["Results_2000", "A1:P22"],
    ["Failures", "A1:M22"],
    ["Metrics", "A1:K40"],
    ["Source_Register", "A1:D6"],
  ]);
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(OUTPUT_FILE);
}

async function readJson(path) {
  return JSON.parse(await fs.readFile(path, "utf8"));
}

function writeSummary(sheet, summaryValue, metricsValue, title) {
  const rows = [
    [title, ""],
    ["Generated At", summaryValue.generatedAt],
    ["Record Count", summaryValue.recordCount],
    ["Source Count", summaryValue.sourceCount],
    ["Exact Match Rate", metricsValue.exact_match_rate],
    ["Precision", metricsValue.precision],
    ["Recall", metricsValue.recall],
    ["False Positive Rate", metricsValue.false_positive_rate],
    ["False Negative Rate", metricsValue.false_negative_rate],
    ["Pass Count", metricsValue.pass_count],
    ["Fail Count", metricsValue.fail_count],
    ["Scope", "Fresh public internet holdout using Open Food Facts bulk rows and GS1 EPCIS public example events."],
    ["Live Model Outputs Used", "No"],
    ["Limitation 1", summaryValue.importantLimitations[0]],
    ["Limitation 2", summaryValue.importantLimitations[1]],
    ["Limitation 3", summaryValue.importantLimitations[2]],
    ["Limitation 4", summaryValue.importantLimitations[3]],
    ["Limitation 5", summaryValue.importantLimitations[4]],
  ];
  writeMatrix(sheet, "A1:B18", rows);
  sheet.getRange("A1:B1").format = {
    fill: { type: "solid", color: "#17324D" },
    font: { color: "#FFFFFF", bold: true, size: 14 },
  };
  sheet.getRange("A2:A18").format.font = { bold: true };
  sheet.getRange("B5:B9").format.numberFormat = "0.00%";
}

function writeInputRecords(sheet, inputRecords) {
  const headers = [
    "record_id",
    "source_record_id",
    "scenario_family",
    "source_name",
    "source_url",
    "source_basis",
    "source_file",
    "event_type",
    "biz_step",
    "product",
    "product_category",
    "lot_or_batch",
    "observed_text",
    "expected_ctes",
    "expected_abstentions",
    "gold_label_method",
  ];
  const rows = [headers, ...inputRecords.map((record) => headers.map((header) => toCell(record[header])))];
  writeMatrix(sheet, rangeFor(rows), rows);
}

function writeResults(sheet, outputResults, recordsById) {
  const headers = [
    "record_id",
    "source_record_id",
    "scenario_family",
    "source_name",
    "source_file",
    "event_type",
    "biz_step",
    "observed_text",
    "expected_ctes",
    "predicted_ctes",
    "expected_abstentions",
    "predicted_abstentions",
    "status",
    "errors",
    "gold_label_method",
    "source_url",
  ];
  const rows = [
    headers,
    ...outputResults.map((result) => {
      const record = recordsById.get(result.record_id) || {};
      return headers.map((header) => toCell(result[header] ?? record[header]));
    }),
  ];
  writeMatrix(sheet, rangeFor(rows), rows);
}

function writeFailures(sheet, outputResults, recordsById) {
  const headers = [
    "record_id",
    "source_name",
    "source_file",
    "event_type",
    "biz_step",
    "observed_text",
    "expected_ctes",
    "predicted_ctes",
    "expected_abstentions",
    "predicted_abstentions",
    "status",
    "errors",
    "source_url",
  ];
  const failureRows = outputResults
    .filter((result) => result.status === "fail")
    .map((result) => {
      const record = recordsById.get(result.record_id) || {};
      return headers.map((header) => toCell(result[header] ?? record[header]));
    });
  const rows = [headers, ...failureRows];
  writeMatrix(sheet, rangeFor(rows), rows);
}

function writeMetrics(sheet, metricsValue) {
  const topRows = [
    ["Metric", "Value"],
    ["Record count", metricsValue.record_count],
    ["Pass count", metricsValue.pass_count],
    ["Fail count", metricsValue.fail_count],
    ["Exact match rate", metricsValue.exact_match_rate],
    ["Precision", metricsValue.precision],
    ["Recall", metricsValue.recall],
    ["False positive rate", metricsValue.false_positive_rate],
    ["False negative rate", metricsValue.false_negative_rate],
  ];
  writeMatrix(sheet, rangeFor(topRows), topRows);
  const cteRows = [
    ["CTE", "Support", "Precision", "Recall", "False Positives", "False Negatives"],
    ...Object.keys(metricsValue.precision_by_cte).sort().map((cte) => [
      cte,
      metricsValue.support_by_cte[cte],
      metricsValue.precision_by_cte[cte],
      metricsValue.recall_by_cte[cte],
      metricsValue.false_positive_by_cte[cte],
      metricsValue.false_negative_by_cte[cte],
    ]),
  ];
  writeMatrix(sheet, `A12:F${11 + cteRows.length}`, cteRows);
  const sourceRows = [
    ["Source", "Count", "Pass", "Fail", "Pass Rate"],
    ...Object.entries(metricsValue.by_source).map(([source, values]) => [
      source,
      values.count,
      values.pass,
      values.fail,
      values.pass_rate,
    ]),
  ];
  writeMatrix(sheet, `A24:E${23 + sourceRows.length}`, sourceRows);
  const familyRows = [
    ["Family", "Count", "Pass", "Fail", "Pass Rate"],
    ...Object.entries(metricsValue.by_family).map(([family, values]) => [
      family,
      values.count,
      values.pass,
      values.fail,
      values.pass_rate,
    ]),
  ];
  writeMatrix(sheet, `A32:E${31 + familyRows.length}`, familyRows);
  sheet.getRange("B5:B9").format.numberFormat = "0.00%";
  sheet.getRange(`C13:D${11 + cteRows.length}`).format.numberFormat = "0.00%";
  sheet.getRange(`E25:E${23 + sourceRows.length}`).format.numberFormat = "0.00%";
  sheet.getRange(`E33:E${31 + familyRows.length}`).format.numberFormat = "0.00%";
}

function writeSources(sheet, sourceRows) {
  const headers = ["source_key", "source_name", "source_url", "source_basis"];
  const rows = [headers, ...sourceRows.map((source) => headers.map((header) => source[header]))];
  writeMatrix(sheet, rangeFor(rows), rows);
}

function styleUsedRange(sheet) {
  sheet.getRange("A1:Z1").format = {
    fill: { type: "solid", color: "#17324D" },
    font: { color: "#FFFFFF", bold: true },
    wrapText: true,
    verticalAlignment: "center",
  };
  sheet.getRange("A:Z").format.wrapText = true;
  sheet.getRange("A:Z").format.autofitColumns();
}

function writeMatrix(sheet, range, rows) {
  sheet.getRange(range).values = rows;
}

function rangeFor(rows) {
  return `A1:${columnName(rows[0].length)}${rows.length}`;
}

function columnName(index) {
  let name = "";
  let current = index;
  while (current > 0) {
    const remainder = (current - 1) % 26;
    name = String.fromCharCode(65 + remainder) + name;
    current = Math.floor((current - 1) / 26);
  }
  return name;
}

function toCell(value) {
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  if (value == null) {
    return "";
  }
  return value;
}

async function verifyWorkbook(workbook, ranges) {
  for (const [sheetName, range] of ranges) {
    const inspected = await workbook.inspect({
      kind: "table",
      range: `${sheetName}!${range}`,
      include: "values,formulas",
      tableMaxRows: 22,
      tableMaxCols: 16,
    });
    console.log(inspected.ndjson);
    await workbook.render({ sheetName, range, scale: 2 });
  }
  const errors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 100 },
    summary: "final formula error scan",
  });
  console.log(errors.ndjson);
}
