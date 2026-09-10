"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync("Code_Accounts.gs", "utf8");
const properties = {
  API_SHARED_KEY: "a".repeat(32),
  AUTH_SIGNING_KEY: "b".repeat(32),
  REQUIRE_HMAC: "true",
  REQUIRE_SERVER_BACKUP_BEFORE_RESET: "true",
  DRIVE_FOLDER_ID: "drive-folder",
  LOCAL_ACCOUNT_ROLES_JSON: JSON.stringify({ developer: "Developer" }),
  ACCOUNT_TELEGRAM_BOT_TOKEN: "123456:abcdefghijklmnopqrstuvwxyz",
  ACCOUNT_TELEGRAM_CHAT_ID: "-1001234567890",
  TELEGRAM_APPROVER_USER_ID: "1234",
  TELEGRAM_WEBHOOK_SECRET: "w".repeat(64),
};
const cacheValues = new Map();

const context = {
  console,
  PropertiesService: {
    getScriptProperties: () => ({
      getProperty: (name) => properties[name] ?? null,
      setProperty: (name, value) => {
        properties[name] = String(value);
      },
    }),
  },
  CacheService: {
    getScriptCache: () => ({
      get: (key) => cacheValues.get(key) ?? null,
      put: (key, value) => cacheValues.set(key, String(value)),
      remove: (key) => cacheValues.delete(key),
    }),
  },
  SpreadsheetApp: { flush: () => {} },
};
vm.createContext(context);
vm.runInContext(source, context, { filename: "Code_Accounts.gs" });

assert.throws(
  () => context.cleanText_("=SUM(A1:A2)", 80, true),
  /formula spreadsheet/
);
assert.equal(context.cleanText_("-", 80, false), "-");
assert.equal(
  context.validPasswordVerifier_(
    `pbkdf2_sha256$310000${"$" + "a".repeat(32)}${"$" + "b".repeat(64)}`
  ),
  true
);
assert.equal(context.validPasswordVerifier_("c".repeat(64)), false);
assert.equal(
  context.validPasswordVerifier_(
    `pbkdf2_sha256$1000001${"$" + "a".repeat(32)}${"$" + "b".repeat(64)}`
  ),
  false
);
assert.equal(context.intValue_("-4", "Jumlah"), -4);
assert.throws(
  () => context.intValue_("1000000001", "Jumlah"),
  /batas aman/
);

const capabilities = context.backendCapabilities_();
for (const capability of [
  "hmac_required",
  "account_auth_rate_limit",
  "idempotent_mutations",
  "formula_guard",
  "mutation_rollback",
  "backup_before_reset",
  "drive_folder_configured",
  "local_roles_enforced",
  "account_approval_configured",
]) {
  assert.equal(capabilities[capability], true, capability);
}
properties.TELEGRAM_WEBHOOK_SECRET = "weak";
assert.equal(context.accountApprovalConfigured_(), false);
properties.TELEGRAM_WEBHOOK_SECRET = "w".repeat(64);

const pbkdf2Verifier =
  `pbkdf2_sha256$310000${"$" + "a".repeat(32)}${"$" + "b".repeat(64)}`;
assert.equal(
  context.canUpgradeLegacyVerifier_(
    "c".repeat(64),
    "c".repeat(64),
    pbkdf2Verifier
  ),
  true
);
assert.equal(
  context.canUpgradeLegacyVerifier_(
    "c".repeat(64),
    "c".repeat(64),
    "d".repeat(64)
  ),
  false
);
for (let attempt = 1; attempt <= 5; attempt += 1) {
  const failure = context.accountAuthFailure_("rate-limited-user");
  assert.equal(failure.status, attempt === 5 ? "LOCKED" : "INVALID");
}
assert.ok(context.accountAuthRetryAfter_("rate-limited-user") > 0);
context.clearAccountAuthFailures_("rate-limited-user");
assert.equal(context.accountAuthRetryAfter_("rate-limited-user"), 0);

class FakeSheet {
  constructor(values) {
    this.values = values.map((row) => [...row]);
  }

  getLastRow() {
    return this.values.length;
  }

  getLastColumn() {
    return Math.max(...this.values.map((row) => row.length), 1);
  }

  getRange(row, column, rowCount, columnCount) {
    const sheet = this;
    return {
      getValues() {
        return Array.from({ length: rowCount }, (_, rowOffset) =>
          Array.from(
            { length: columnCount },
            (_, columnOffset) =>
              sheet.values[row - 1 + rowOffset]?.[column - 1 + columnOffset] ?? ""
          )
        );
      },
      getFormulas() {
        return Array.from({ length: rowCount }, () =>
          Array.from({ length: columnCount }, () => "")
        );
      },
      clearContent() {
        for (let r = row - 1; r < row - 1 + rowCount; r += 1) {
          sheet.values[r] ??= [];
          for (let c = column - 1; c < column - 1 + columnCount; c += 1) {
            sheet.values[r][c] = "";
          }
        }
      },
      setValues(values) {
        values.forEach((sourceRow, rowOffset) => {
          sheet.values[row - 1 + rowOffset] ??= [];
          sourceRow.forEach((value, columnOffset) => {
            sheet.values[row - 1 + rowOffset][column - 1 + columnOffset] = value;
          });
        });
      },
      setValue(value) {
        sheet.values[row - 1] ??= [];
        sheet.values[row - 1][column - 1] = value;
      },
    };
  }

  appendRow(values) {
    this.values.push([...values]);
  }
}

const rollbackSheet = new FakeSheet([["header"], [10]]);
assert.throws(
  () =>
    context.withSheetRollback_([rollbackSheet], () => {
      rollbackSheet.values[1][0] = 3;
      rollbackSheet.values.push(["partial append"]);
      throw new Error("simulated write failure");
    }),
  /simulated write failure/
);
assert.deepEqual(rollbackSheet.values.slice(0, 2), [["header"], [10]]);
assert.equal(rollbackSheet.values[2][0], "");

let evidenceWasSaved = false;
const originalFindHistoryRow = context.findHistoryRow_;
const originalFindStockRow = context.findStockRow_;
const originalFindAuditRow = context.findAuditRow_;
context.resolveActor_ = () => ({ username: "staff", role: "Staff" });
context.requireRoles_ = () => {};
context.ensureSchema_ = () => {};
context.getSpreadsheet_ = () => ({
  getSheetByName: () => ({}),
});
context.findHistoryRow_ = () => ({
  type: "KELUAR",
  item: "Primer",
  amount: 2,
  note: "Proyek A",
  proofUrl: "https://drive.test/proof",
});
context.findAuditRow_ = () => ({
  detail: "Primer 2 pcs; stok 10 -> 8",
});
context.findStockRow_ = () => ({
  name: "Primer",
  quantity: 8,
  minimum: 5,
  status: "Aktif",
});
context.saveEvidence_ = () => {
  evidenceWasSaved = true;
  return "";
};

const replay = context.handleTransaction_({
  tipe: "KELUAR",
  barang: "Primer",
  jumlah: 2,
  keterangan: "Proyek A",
  tx_id: "TRX-1",
  expected_stock_before: 10,
});
assert.equal(replay.idempotent_replay, true);
assert.equal(replay.stok_akhir, 8);
assert.equal(evidenceWasSaved, false);

context.findHistoryRow_ = originalFindHistoryRow;
context.findStockRow_ = originalFindStockRow;
context.findAuditRow_ = originalFindAuditRow;
context.nowText_ = () => "08-09-2026 12:00:00";
context.bumpRevision_ = () => "2";
let evidenceSaveCount = 0;
context.saveEvidence_ = () => {
  evidenceSaveCount += 1;
  return "https://drive.test/proof";
};
const stockSheet = new FakeSheet([
  ["Nama Barang", "Jumlah Stok", "Status", "Batas Minimum"],
  ["Primer", 10, "Aktif", 5],
]);
const historySheet = new FakeSheet([[
  "ID Transaksi", "Waktu", "Tanggal", "Tipe", "Barang", "Jumlah",
  "Pembeli / Keterangan", "Bukti URL", "Status", "Referensi",
]]);
const auditSheet = new FakeSheet([[
  "Waktu", "User", "Role", "Aksi", "ID Transaksi", "Detail",
]]);
context.getSpreadsheet_ = () => ({
  getSheetByName(name) {
    return { stok: stockSheet, riwayat: historySheet, audit: auditSheet }[name];
  },
});
const transactionPayload = {
  tipe: "KELUAR",
  barang: "Primer",
  jumlah: 2,
  keterangan: "Proyek A",
  tx_id: "TRX-NEW",
  expected_stock_before: 10,
  waktu: "08-09-2026 12:00",
  tanggal: "08-09-2026",
};
const created = context.handleTransaction_(transactionPayload);
assert.equal(created.stok_akhir, 8);
assert.equal(created.idempotent_replay, false);
assert.equal(stockSheet.values[1][1], 8);
assert.equal(historySheet.values.length, 2);
assert.equal(auditSheet.values.length, 2);
assert.equal(evidenceSaveCount, 1);

const retried = context.handleTransaction_(transactionPayload);
assert.equal(retried.idempotent_replay, true);
assert.equal(stockSheet.values[1][1], 8);
assert.equal(historySheet.values.length, 2);
assert.equal(auditSheet.values.length, 2);
assert.equal(evidenceSaveCount, 1);

assert.throws(
  () => context.handleTransaction_({ ...transactionPayload, jumlah: 1 }),
  /payload yang berbeda/
);
assert.equal(stockSheet.values[1][1], 8);

console.log("Backend contract tests passed.");
