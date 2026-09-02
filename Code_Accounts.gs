/**
 * Mirai Backend v7.4
 *
 * Semua credential wajib disimpan di Apps Script > Project Settings >
 * Script Properties. Jangan menaruh token, key, atau ID produksi di file ini.
 *
 * Wajib:
 * - SPREADSHEET_ID
 * - API_SHARED_KEY
 * - AUTH_SIGNING_KEY
 *
 * Opsional:
 * - DRIVE_FOLDER_ID
 * - ACCOUNT_TELEGRAM_BOT_TOKEN
 * - ACCOUNT_TELEGRAM_CHAT_ID
 * - TELEGRAM_APPROVER_USER_ID
 * - TELEGRAM_WEBHOOK_SECRET
 * - LOCAL_ACCOUNT_ROLES_JSON, contoh:
 *   {"andika":"Developer","bos":"Boss"}
 * - REQUIRE_HMAC=true
 * - REQUIRE_SERVER_BACKUP_BEFORE_RESET=true
 */

const BACKEND_VERSION = "7.4-audit-clear";
const SHEET_STOCK = "stok";
const SHEET_HISTORY = "riwayat";
const SHEET_AUDIT = "audit";
const SHEET_ACCOUNTS = "accounts";

const STOCK_HEADERS = [
  "Nama Barang",
  "Jumlah Stok",
  "Status",
  "Batas Minimum",
];
const HISTORY_HEADERS = [
  "ID Transaksi",
  "Waktu",
  "Tanggal",
  "Tipe",
  "Barang",
  "Jumlah",
  "Pembeli / Keterangan",
  "Bukti URL",
  "Status",
  "Referensi",
];
const AUDIT_HEADERS = [
  "Waktu",
  "User",
  "Role",
  "Aksi",
  "ID Transaksi",
  "Detail",
];
const ACCOUNT_HEADERS = [
  "Request ID",
  "Nama Lengkap",
  "Username",
  "Password Verifier",
  "Jabatan",
  "Role Diminta",
  "Role",
  "Status",
  "Dibuat",
  "Diperbarui",
  "Disetujui Oleh",
];

const VALID_ROLES = ["Staff", "Admin", "Boss", "Developer"];
const PUBLIC_ROLES = ["Staff", "Admin"];
const DEFAULT_STOCK = [
  ["Microcement base", 16, "Aktif", 5],
  ["Ready to use", 15, "Aktif", 5],
  ["Mixed resin A", 12, "Aktif", 5],
  ["Ceramic microcement", 4, "Aktif", 5],
  ["Microrock", 17, "Aktif", 5],
  ["Primer ordinary", 7, "Aktif", 5],
  ["Epoxy primer", 3, "Aktif", 5],
  ["Self leveling white finish", 4, "Aktif", 5],
  ["Top coat A", 15, "Aktif", 5],
  ["Top coat B", 1, "Aktif", 5],
  ["Top coat C", 5, "Aktif", 5],
  ["Pewarna no 1", 3, "Aktif", 5],
  ["Pewarna no 2", 10, "Aktif", 5],
  ["Pewarna no 3", 0, "Aktif", 5],
  ["Pewarna no 4", 9, "Aktif", 5],
  ["Metal glaze wax", 0, "Aktif", 5],
  ["Metallic glaze wax", 0, "Aktif", 5],
];

function doGet() {
  return jsonResponse_({
    ok: false,
    message: "GET dinonaktifkan. Gunakan signed POST dari aplikasi WMS.",
    backend_version: BACKEND_VERSION,
  });
}

function doPost(e) {
  try {
    if (e && e.parameter && e.parameter.telegram_secret) {
      return handleTelegramWebhook_(e);
    }

    const payload = parseJsonBody_(e);
    verifySignedRequest_(payload);
    const result = routeRequest_(payload);
    return jsonResponse_(Object.assign({ ok: true }, result || {}));
  } catch (error) {
    console.error("[WMS backend] " + safeError_(error));
    return jsonResponse_({ ok: false, message: safeError_(error) });
  }
}

function routeRequest_(payload) {
  const action = String(payload.action || "").trim();
  switch (action) {
    case "health":
      return handleHealth_(payload);
    case "read":
      return handleRead_(payload);
    case "transaction":
      return withScriptLock_(function () {
        return handleTransaction_(payload);
      });
    case "master_add":
      return withScriptLock_(function () {
        return handleMasterAdd_(payload);
      });
    case "master_update":
      return withScriptLock_(function () {
        return handleMasterUpdate_(payload);
      });
    case "master_delete":
      return withScriptLock_(function () {
        return handleMasterDelete_(payload);
      });
    case "transaction_correct":
      return withScriptLock_(function () {
        return handleTransactionCorrect_(payload);
      });
    case "transaction_void":
      return withScriptLock_(function () {
        return handleTransactionVoid_(payload);
      });
    case "stock_adjust":
      return withScriptLock_(function () {
        return handleStockAdjust_(payload);
      });
    case "reset":
      return withScriptLock_(function () {
        return handleReset_(payload);
      });
    case "audit_clear":
      return withScriptLock_(function () {
        return handleAuditClear_(payload);
      });
    case "server_backup":
      return handleServerBackup_(payload);
    case "backup_status":
      return handleBackupStatus_(payload);
    case "install_backup_trigger":
      return handleInstallBackupTrigger_(payload);
    case "remove_backup_trigger":
      return handleRemoveBackupTrigger_(payload);
    case "account_register":
      return withScriptLock_(function () {
        return handleAccountRegister_(payload);
      });
    case "account_auth":
      return handleAccountAuth_(payload);
    case "account_validate":
      return handleAccountValidate_(payload);
    case "account_list":
      return handleAccountList_(payload);
    case "account_approve":
      return withScriptLock_(function () {
        return handleAccountApprove_(payload);
      });
    case "account_reject":
      return withScriptLock_(function () {
        return handleAccountReject_(payload);
      });
    case "account_update":
      return withScriptLock_(function () {
        return handleAccountUpdate_(payload);
      });
    case "account_delete":
      return withScriptLock_(function () {
        return handleAccountDelete_(payload);
      });
    default:
      throw new Error("Action tidak dikenal.");
  }
}

function handleHealth_(payload) {
  resolveActor_(payload);
  const properties = PropertiesService.getScriptProperties();
  return {
    backend_version: BACKEND_VERSION,
    data_revision: properties.getProperty("DATA_REVISION") || "0",
    server_time: nowText_(),
  };
}

function handleRead_(payload) {
  const actor = resolveActor_(payload);
  const spreadsheet = getSpreadsheet_();
  ensureSchema_(spreadsheet);
  return {
    backend_version: BACKEND_VERSION,
    data_revision:
      PropertiesService.getScriptProperties().getProperty("DATA_REVISION") || "0",
    server_time: nowText_(),
    stok: getSheetValues_(spreadsheet.getSheetByName(SHEET_STOCK)),
    riwayat: getSheetValues_(spreadsheet.getSheetByName(SHEET_HISTORY)),
    audit:
      actor.role === "Developer" || actor.role === "Boss"
        ? getSheetValues_(spreadsheet.getSheetByName(SHEET_AUDIT))
        : [AUDIT_HEADERS],
  };
}

function handleTransaction_(payload) {
  const actor = resolveActor_(payload);
  requireRoles_(actor, VALID_ROLES);
  const type = String(payload.tipe || "").toUpperCase();
  if (type !== "MASUK" && type !== "KELUAR") {
    throw new Error("Tipe transaksi tidak valid.");
  }

  const itemName = cleanText_(payload.barang, 80, true);
  const amount = positiveInt_(payload.jumlah, "Jumlah");
  const note = cleanText_(
    payload.keterangan,
    240,
    type === "KELUAR"
  );
  const txId = cleanText_(payload.tx_id, 80, true);
  const spreadsheet = getSpreadsheet_();
  ensureSchema_(spreadsheet);
  const stockSheet = spreadsheet.getSheetByName(SHEET_STOCK);
  const found = findStockRow_(stockSheet, itemName);
  if (!found) {
    throw new Error("Barang tidak ditemukan.");
  }
  if (found.status !== "Aktif") {
    throw new Error("Barang sedang nonaktif.");
  }

  if (
    payload.expected_stock_before !== undefined &&
    payload.expected_stock_before !== null &&
    intValue_(payload.expected_stock_before, "Stok sebelumnya") !== found.quantity
  ) {
    throw new Error(
      "Stok sudah berubah oleh pengguna lain. Segarkan data lalu ulangi transaksi."
    );
  }

  const finalStock =
    type === "MASUK" ? found.quantity + amount : found.quantity - amount;
  if (finalStock < 0) {
    throw new Error("Stok tidak mencukupi.");
  }

  const proofUrl = saveEvidence_(payload);
  stockSheet.getRange(found.row, 2).setValue(finalStock);
  spreadsheet.getSheetByName(SHEET_HISTORY).appendRow([
    txId,
    cleanText_(payload.waktu, 40, true),
    cleanText_(payload.tanggal, 20, true),
    type,
    found.name,
    amount,
    note,
    proofUrl,
    "AKTIF",
    "",
  ]);
  writeAudit_(
    spreadsheet,
    actor,
    "TRANSACTION_" + type,
    txId,
    found.name + " " + amount + " pcs; stok akhir " + finalStock
  );
  bumpRevision_();

  return {
    tx_id: txId,
    stok_akhir: finalStock,
    file_url: proofUrl,
    alert: stockAlert_(found.name, finalStock, found.minimum),
  };
}

function handleMasterAdd_(payload) {
  const actor = resolveActor_(payload);
  requireRoles_(actor, ["Developer", "Boss", "Admin"]);
  const name = cleanText_(payload.nama, 80, true);
  const initial = nonNegativeInt_(payload.stok_awal, "Stok awal");
  const minimum = positiveInt_(payload.min_stok, "Batas minimum");
  const spreadsheet = getSpreadsheet_();
  ensureSchema_(spreadsheet);
  const stockSheet = spreadsheet.getSheetByName(SHEET_STOCK);
  if (findStockRow_(stockSheet, name)) {
    throw new Error("Nama barang sudah digunakan.");
  }
  stockSheet.appendRow([name, initial, "Aktif", minimum]);
  const txId = cleanText_(payload.tx_id, 80, true);
  spreadsheet.getSheetByName(SHEET_HISTORY).appendRow([
    txId,
    cleanText_(payload.waktu, 40, true),
    "",
    "BARANG BARU",
    name,
    initial,
    "Master item baru",
    "",
    "AKTIF",
    "",
  ]);
  writeAudit_(
    spreadsheet,
    actor,
    "MASTER_ADD",
    txId,
    name + "; stok awal " + initial
  );
  bumpRevision_();
  return { name: name, stok_akhir: initial };
}

function handleMasterUpdate_(payload) {
  const actor = resolveActor_(payload);
  requireRoles_(actor, ["Developer", "Boss", "Admin"]);
  const oldName = cleanText_(payload.old_nama, 80, true);
  const newName = cleanText_(payload.new_nama, 80, true);
  const status = normalizeItemStatus_(payload.status);
  const minimum = positiveInt_(payload.min_stok, "Batas minimum");
  const spreadsheet = getSpreadsheet_();
  ensureSchema_(spreadsheet);
  const sheet = spreadsheet.getSheetByName(SHEET_STOCK);
  const current = findStockRow_(sheet, oldName);
  if (!current) {
    throw new Error("Barang tidak ditemukan.");
  }
  const duplicate = findStockRow_(sheet, newName);
  if (duplicate && duplicate.row !== current.row) {
    throw new Error("Nama barang sudah digunakan item lain.");
  }
  sheet.getRange(current.row, 1, 1, 4).setValues([
    [newName, current.quantity, status, minimum],
  ]);
  writeAudit_(
    spreadsheet,
    actor,
    "MASTER_UPDATE",
    "",
    oldName + " -> " + newName + "; " + status
  );
  bumpRevision_();
  return { name: newName };
}

function handleMasterDelete_(payload) {
  const actor = resolveActor_(payload);
  requireRoles_(actor, ["Developer", "Boss", "Admin"]);
  const name = cleanText_(payload.nama, 80, true);
  const spreadsheet = getSpreadsheet_();
  ensureSchema_(spreadsheet);
  const historyRows = dataRows_(
    spreadsheet.getSheetByName(SHEET_HISTORY),
    HISTORY_HEADERS
  );
  const used = historyRows.some(function (row) {
    return sameText_(row[4], name);
  });
  if (used) {
    throw new Error(
      "Barang memiliki riwayat transaksi dan tidak boleh dihapus. Gunakan status Nonaktif."
    );
  }
  const stockSheet = spreadsheet.getSheetByName(SHEET_STOCK);
  const found = findStockRow_(stockSheet, name);
  if (!found) {
    throw new Error("Barang tidak ditemukan.");
  }
  stockSheet.deleteRow(found.row);
  writeAudit_(spreadsheet, actor, "MASTER_DELETE", "", name);
  bumpRevision_();
  return { deleted: true };
}

function handleStockAdjust_(payload) {
  const actor = resolveActor_(payload);
  requireRoles_(actor, ["Developer", "Boss", "Admin"]);
  const name = cleanText_(payload.barang, 80, true);
  const newStock = nonNegativeInt_(payload.stok_baru, "Stok baru");
  const expected = nonNegativeInt_(
    payload.expected_stock_before,
    "Stok sebelumnya"
  );
  const reason = cleanText_(payload.alasan, 240, true);
  const spreadsheet = getSpreadsheet_();
  ensureSchema_(spreadsheet);
  const stockSheet = spreadsheet.getSheetByName(SHEET_STOCK);
  const found = findStockRow_(stockSheet, name);
  if (!found) {
    throw new Error("Barang tidak ditemukan.");
  }
  if (found.quantity !== expected) {
    throw new Error(
      "Stok sudah berubah oleh pengguna lain. Segarkan data lalu ulangi."
    );
  }

  const difference = newStock - found.quantity;
  stockSheet.getRange(found.row, 2).setValue(newStock);
  const txId = cleanText_(payload.tx_id, 80, true);
  spreadsheet.getSheetByName(SHEET_HISTORY).appendRow([
    txId,
    cleanText_(payload.waktu, 40, true),
    cleanText_(payload.tanggal, 20, true),
    "PENYESUAIAN",
    found.name,
    difference,
    reason,
    "",
    "AKTIF",
    "",
  ]);
  writeAudit_(
    spreadsheet,
    actor,
    "STOCK_ADJUST",
    txId,
    found.name + " " + found.quantity + " -> " + newStock + "; " + reason
  );
  bumpRevision_();
  return {
    tx_id: txId,
    selisih: difference,
    stok_akhir: newStock,
    alert: stockAlert_(found.name, newStock, found.minimum),
  };
}

function handleTransactionVoid_(payload) {
  const actor = resolveActor_(payload);
  requireRoles_(actor, ["Developer", "Boss", "Admin"]);
  const txId = cleanText_(payload.tx_id, 80, true);
  const spreadsheet = getSpreadsheet_();
  ensureSchema_(spreadsheet);
  const historySheet = spreadsheet.getSheetByName(SHEET_HISTORY);
  const tx = findHistoryRow_(historySheet, txId);
  if (!tx || tx.status !== "AKTIF") {
    throw new Error("Transaksi aktif tidak ditemukan.");
  }
  if (tx.type !== "MASUK" && tx.type !== "KELUAR") {
    throw new Error("Jenis transaksi ini tidak dapat di-void.");
  }

  const stockSheet = spreadsheet.getSheetByName(SHEET_STOCK);
  const item = findStockRow_(stockSheet, tx.item);
  if (!item) {
    throw new Error("Master barang transaksi tidak ditemukan.");
  }
  const finalStock =
    tx.type === "MASUK"
      ? item.quantity - tx.amount
      : item.quantity + tx.amount;
  if (finalStock < 0) {
    throw new Error("Void akan membuat stok negatif dan ditolak.");
  }

  stockSheet.getRange(item.row, 2).setValue(finalStock);
  historySheet.getRange(tx.row, 9).setValue("VOID");
  historySheet.getRange(tx.row, 10).setValue("VOID oleh " + actor.username);
  writeAudit_(
    spreadsheet,
    actor,
    "TRANSACTION_VOID",
    txId,
    tx.type + " " + tx.item + " " + tx.amount + " pcs"
  );
  bumpRevision_();
  return { voided: true, stok_akhir: finalStock };
}

function handleTransactionCorrect_(payload) {
  const actor = resolveActor_(payload);
  requireRoles_(actor, ["Developer", "Boss", "Admin"]);
  const oldTxId = cleanText_(payload.tx_id, 80, true);
  const newTxId = cleanText_(payload.new_tx_id, 80, true);
  const newType = String(payload.new_tipe || "").toUpperCase();
  if (newType !== "MASUK" && newType !== "KELUAR") {
    throw new Error("Tipe koreksi tidak valid.");
  }
  const newItemName = cleanText_(payload.new_barang, 80, true);
  const newAmount = positiveInt_(payload.new_jumlah, "Jumlah koreksi");
  const spreadsheet = getSpreadsheet_();
  ensureSchema_(spreadsheet);
  const historySheet = spreadsheet.getSheetByName(SHEET_HISTORY);
  const oldTx = findHistoryRow_(historySheet, oldTxId);
  if (!oldTx || oldTx.status !== "AKTIF") {
    throw new Error("Transaksi aktif tidak ditemukan.");
  }
  if (oldTx.type !== "MASUK" && oldTx.type !== "KELUAR") {
    throw new Error("Jenis transaksi ini tidak dapat dikoreksi.");
  }

  const stockSheet = spreadsheet.getSheetByName(SHEET_STOCK);
  const oldItem = findStockRow_(stockSheet, oldTx.item);
  const newItem = findStockRow_(stockSheet, newItemName);
  if (!oldItem || !newItem) {
    throw new Error("Master barang koreksi tidak ditemukan.");
  }

  const projected = {};
  const stockRows = dataRows_(stockSheet, STOCK_HEADERS);
  stockRows.forEach(function (row) {
    projected[String(row[0]).toLowerCase()] = intValue_(row[1], "Stok");
  });

  const oldKey = oldItem.name.toLowerCase();
  const newKey = newItem.name.toLowerCase();
  projected[oldKey] += oldTx.type === "MASUK" ? -oldTx.amount : oldTx.amount;
  if (projected[oldKey] < 0) {
    throw new Error("Koreksi akan membuat stok lama negatif.");
  }
  projected[newKey] += newType === "MASUK" ? newAmount : -newAmount;
  if (projected[newKey] < 0) {
    throw new Error("Stok tidak mencukupi untuk hasil koreksi.");
  }

  stockSheet.getRange(oldItem.row, 2).setValue(projected[oldKey]);
  if (newItem.row !== oldItem.row) {
    stockSheet.getRange(newItem.row, 2).setValue(projected[newKey]);
  } else {
    stockSheet.getRange(newItem.row, 2).setValue(projected[newKey]);
  }

  historySheet.getRange(oldTx.row, 9).setValue("DIKOREKSI");
  historySheet.getRange(oldTx.row, 10).setValue(newTxId);
  historySheet.appendRow([
    newTxId,
    cleanText_(payload.new_waktu, 40, true),
    cleanText_(payload.new_tanggal, 20, true),
    newType,
    newItem.name,
    newAmount,
    cleanText_(payload.new_keterangan, 240, false),
    oldTx.proofUrl,
    "AKTIF",
    oldTxId,
  ]);
  writeAudit_(
    spreadsheet,
    actor,
    "TRANSACTION_CORRECT",
    oldTxId,
    "Transaksi pengganti " + newTxId
  );
  bumpRevision_();
  return { new_tx_id: newTxId };
}

function handleAuditClear_(payload) {
  const actor = resolveActor_(payload);
  requireRoles_(actor, ["Developer"]);
  if (String(payload.confirm || "") !== "HAPUS-AUDIT") {
    throw new Error("Konfirmasi penghapusan audit tidak valid.");
  }

  const backup = createServerBackup_();
  const spreadsheet = getSpreadsheet_();
  ensureSchema_(spreadsheet);
  const auditSheet = spreadsheet.getSheetByName(SHEET_AUDIT);
  const deletedRows = Math.max(auditSheet.getLastRow() - 1, 0);

  resetSheet_(auditSheet, AUDIT_HEADERS);
  writeAudit_(
    spreadsheet,
    actor,
    "AUDIT_LOG_CLEARED",
    "",
    deletedRows + " catatan audit lama dihapus setelah backup " + backup.backup_name + "."
  );
  bumpRevision_();
  return {
    audit_cleared: true,
    deleted_rows: deletedRows,
    backup_name: backup.backup_name,
    backup_url: backup.backup_url,
  };
}

function handleReset_(payload) {
  const actor = resolveActor_(payload);
  requireRoles_(actor, ["Developer"]);
  if (String(payload.confirm || "") !== "RESET-DATABASE") {
    throw new Error("Konfirmasi reset tidak valid.");
  }

  const requireBackup = getProperty_("REQUIRE_SERVER_BACKUP_BEFORE_RESET", "true")
    .toLowerCase() !== "false";
  if (requireBackup) {
    createServerBackup_();
  }

  const spreadsheet = getSpreadsheet_();
  ensureSchema_(spreadsheet);
  resetSheet_(spreadsheet.getSheetByName(SHEET_STOCK), STOCK_HEADERS);
  spreadsheet
    .getSheetByName(SHEET_STOCK)
    .getRange(2, 1, DEFAULT_STOCK.length, STOCK_HEADERS.length)
    .setValues(DEFAULT_STOCK);
  resetSheet_(spreadsheet.getSheetByName(SHEET_HISTORY), HISTORY_HEADERS);
  resetSheet_(spreadsheet.getSheetByName(SHEET_AUDIT), AUDIT_HEADERS);
  writeAudit_(
    spreadsheet,
    actor,
    "DATABASE_RESET",
    "",
    "Data operasional dikembalikan ke master awal."
  );
  bumpRevision_();
  return { reset: true };
}

function handleServerBackup_(payload) {
  const actor = resolveActor_(payload);
  requireRoles_(actor, ["Developer", "Boss", "Admin"]);
  return createServerBackup_();
}

function handleBackupStatus_(payload) {
  const actor = resolveActor_(payload);
  requireRoles_(actor, ["Developer", "Boss", "Admin"]);
  const properties = PropertiesService.getScriptProperties();
  return {
    last_backup_time: properties.getProperty("LAST_BACKUP_TIME") || "",
    last_backup_url: properties.getProperty("LAST_BACKUP_URL") || "",
    last_backup_name: properties.getProperty("LAST_BACKUP_NAME") || "",
    trigger_installed: backupTriggerInstalled_(),
  };
}

function handleInstallBackupTrigger_(payload) {
  const actor = resolveActor_(payload);
  requireRoles_(actor, ["Developer"]);
  if (!backupTriggerInstalled_()) {
    ScriptApp.newTrigger("scheduledDailyBackup")
      .timeBased()
      .everyDays(1)
      .atHour(1)
      .create();
  }
  return { trigger_installed: true };
}

function handleRemoveBackupTrigger_(payload) {
  const actor = resolveActor_(payload);
  requireRoles_(actor, ["Developer"]);
  ScriptApp.getProjectTriggers().forEach(function (trigger) {
    if (trigger.getHandlerFunction() === "scheduledDailyBackup") {
      ScriptApp.deleteTrigger(trigger);
    }
  });
  return { trigger_installed: false };
}

function scheduledDailyBackup() {
  createServerBackup_();
}

function handleAccountRegister_(payload) {
  const username = normalizeUsername_(payload.username);
  const fullName = cleanText_(payload.full_name, 80, true);
  const position = cleanText_(payload.position, 80, true);
  const requestedRole = normalizeRole_(payload.requested_role);
  if (PUBLIC_ROLES.indexOf(requestedRole) < 0) {
    throw new Error("Pendaftaran publik hanya dapat meminta Staff atau Admin.");
  }
  const verifier = String(payload.password_verifier || "").trim().toLowerCase();
  if (!/^[a-f0-9]{64}$/.test(verifier)) {
    throw new Error("Password verifier tidak valid.");
  }

  const spreadsheet = getSpreadsheet_();
  ensureSchema_(spreadsheet);
  const sheet = spreadsheet.getSheetByName(SHEET_ACCOUNTS);
  if (findAccount_(sheet, username)) {
    throw new Error("Username sudah digunakan.");
  }

  const requestId = "ACC-" + Utilities.getUuid().replace(/-/g, "").slice(0, 16).toUpperCase();
  const now = nowText_();
  sheet.appendRow([
    requestId,
    fullName,
    username,
    verifier,
    position,
    requestedRole,
    "",
    "PENDING",
    now,
    now,
    "",
  ]);
  writeAudit_(
    spreadsheet,
    { username: "Public Registration", role: "Staff" },
    "ACCOUNT_REGISTER",
    requestId,
    username + " meminta role " + requestedRole
  );
  bumpRevision_();
  return { request_id: requestId, status: "PENDING" };
}

function handleAccountAuth_(payload) {
  const username = normalizeUsername_(payload.username);
  const verifier = String(payload.password_verifier || "").trim().toLowerCase();
  if (!/^[a-f0-9]{64}$/.test(verifier)) {
    return { authenticated: false, status: "INVALID" };
  }
  const spreadsheet = getSpreadsheet_();
  ensureSchema_(spreadsheet);
  const account = findAccount_(
    spreadsheet.getSheetByName(SHEET_ACCOUNTS),
    username
  );
  if (!account || !constantTimeEqual_(account.passwordVerifier, verifier)) {
    return { authenticated: false, status: "INVALID" };
  }
  if (account.status !== "ACTIVE") {
    return { authenticated: false, status: account.status };
  }
  return {
    authenticated: true,
    status: "ACTIVE",
    username: account.username,
    full_name: account.fullName,
    role: account.role,
  };
}

function handleAccountValidate_(payload) {
  const username = normalizeUsername_(payload.username);
  const spreadsheet = getSpreadsheet_();
  ensureSchema_(spreadsheet);
  const account = findAccount_(
    spreadsheet.getSheetByName(SHEET_ACCOUNTS),
    username
  );
  if (!account) {
    return { active: false, status: "DELETED" };
  }
  return {
    active: account.status === "ACTIVE",
    status: account.status,
    username: account.username,
    full_name: account.fullName,
    role: account.role || "Staff",
  };
}

function handleAccountList_(payload) {
  const actor = resolveActor_(payload);
  requireRoles_(actor, ["Developer"]);
  const spreadsheet = getSpreadsheet_();
  ensureSchema_(spreadsheet);
  const rows = dataRows_(
    spreadsheet.getSheetByName(SHEET_ACCOUNTS),
    ACCOUNT_HEADERS
  );
  return {
    accounts: rows.map(function (row) {
      return {
        request_id: row[0],
        full_name: row[1],
        username: row[2],
        position: row[4],
        requested_role: row[5],
        role: row[6],
        status: row[7],
        created_at: row[8],
        updated_at: row[9],
        approved_by: row[10],
      };
    }),
  };
}

function handleAccountApprove_(payload) {
  const actor = resolveActor_(payload);
  requireRoles_(actor, ["Developer"]);
  const username = normalizeUsername_(payload.username);
  const role = normalizeRole_(payload.new_role);
  const spreadsheet = getSpreadsheet_();
  ensureSchema_(spreadsheet);
  const sheet = spreadsheet.getSheetByName(SHEET_ACCOUNTS);
  const account = findAccount_(sheet, username);
  if (!account) {
    throw new Error("Akun tidak ditemukan.");
  }
  sheet.getRange(account.row, 7, 1, 5).setValues([
    [role, "ACTIVE", account.createdAt, nowText_(), actor.username],
  ]);
  writeAudit_(
    spreadsheet,
    actor,
    "ACCOUNT_APPROVE",
    account.requestId,
    username + " sebagai " + role
  );
  bumpRevision_();
  return { username: username, role: role, status: "ACTIVE" };
}

function handleAccountReject_(payload) {
  const actor = resolveActor_(payload);
  requireRoles_(actor, ["Developer"]);
  const username = normalizeUsername_(payload.username);
  const spreadsheet = getSpreadsheet_();
  ensureSchema_(spreadsheet);
  const sheet = spreadsheet.getSheetByName(SHEET_ACCOUNTS);
  const account = findAccount_(sheet, username);
  if (!account) {
    throw new Error("Akun tidak ditemukan.");
  }
  sheet.getRange(account.row, 7, 1, 5).setValues([
    ["", "REJECTED", account.createdAt, nowText_(), actor.username],
  ]);
  writeAudit_(
    spreadsheet,
    actor,
    "ACCOUNT_REJECT",
    account.requestId,
    username
  );
  bumpRevision_();
  return { username: username, status: "REJECTED" };
}

function handleAccountUpdate_(payload) {
  const actor = resolveActor_(payload);
  requireRoles_(actor, ["Developer"]);
  const username = normalizeUsername_(payload.username);
  const role = normalizeRole_(payload.new_role);
  const status = String(payload.new_status || "").toUpperCase();
  if (status !== "ACTIVE" && status !== "SUSPENDED") {
    throw new Error("Status akun tidak valid.");
  }
  if (sameText_(actor.username, username)) {
    throw new Error("Akun yang sedang digunakan tidak dapat diubah.");
  }

  const spreadsheet = getSpreadsheet_();
  ensureSchema_(spreadsheet);
  const sheet = spreadsheet.getSheetByName(SHEET_ACCOUNTS);
  const account = findAccount_(sheet, username);
  if (!account) {
    throw new Error("Akun tidak ditemukan.");
  }
  if (
    account.role === "Developer" &&
    (role !== "Developer" || status !== "ACTIVE") &&
    countActiveDevelopers_(sheet) <= 1
  ) {
    throw new Error("Developer aktif terakhir tidak dapat diturunkan atau dinonaktifkan.");
  }

  sheet.getRange(account.row, 7).setValue(role);
  sheet.getRange(account.row, 8).setValue(status);
  sheet.getRange(account.row, 10).setValue(nowText_());
  sheet.getRange(account.row, 11).setValue(actor.username);
  writeAudit_(
    spreadsheet,
    actor,
    "ACCOUNT_UPDATE",
    account.requestId,
    username + " -> " + role + "/" + status
  );
  bumpRevision_();
  return { username: username, role: role, status: status };
}

function handleAccountDelete_(payload) {
  const actor = resolveActor_(payload);
  requireRoles_(actor, ["Developer"]);
  const username = normalizeUsername_(payload.username);
  if (String(payload.confirm || "") !== "DELETE:" + username) {
    throw new Error("Konfirmasi penghapusan akun tidak valid.");
  }
  if (sameText_(actor.username, username)) {
    throw new Error("Akun yang sedang digunakan tidak dapat dihapus.");
  }

  const spreadsheet = getSpreadsheet_();
  ensureSchema_(spreadsheet);
  const sheet = spreadsheet.getSheetByName(SHEET_ACCOUNTS);
  const account = findAccount_(sheet, username);
  if (!account) {
    throw new Error("Akun tidak ditemukan.");
  }
  if (
    account.role === "Developer" &&
    account.status === "ACTIVE" &&
    countActiveDevelopers_(sheet) <= 1
  ) {
    throw new Error("Developer aktif terakhir tidak dapat dihapus.");
  }

  const requestId = account.requestId;
  sheet.deleteRow(account.row);
  writeAudit_(
    spreadsheet,
    actor,
    "ACCOUNT_DELETE_PERMANENT",
    requestId,
    "Record akun dan password verifier dihapus: " + username
  );
  bumpRevision_();
  return { username: username, deleted: true, status: "DELETED" };
}

function resolveActor_(payload) {
  const username = String(payload.actor || "").trim();
  if (!username) {
    throw new Error("Identitas pengguna tidak tersedia.");
  }
  const source = String(payload.auth_source || "local").toLowerCase();
  let role = normalizeRole_(payload.role);

  const spreadsheet = getSpreadsheet_();
  ensureSchema_(spreadsheet);
  const account = findAccount_(
    spreadsheet.getSheetByName(SHEET_ACCOUNTS),
    username
  );

  if (source === "dynamic" || account) {
    if (!account || account.status !== "ACTIVE") {
      throw new Error("Akun telah dinonaktifkan atau dihapus.");
    }
    role = normalizeRole_(account.role);
  } else {
    const trusted = trustedLocalRoles_();
    const keys = Object.keys(trusted);
    if (keys.length) {
      const trustedRole = trusted[String(username).trim().toLowerCase()];
      if (!trustedRole) {
        throw new Error("Akun lokal tidak terdaftar pada backend.");
      }
      role = normalizeRole_(trustedRole);
    }
  }

  return { username: username, role: role, source: source };
}

function trustedLocalRoles_() {
  const raw = getProperty_("LOCAL_ACCOUNT_ROLES_JSON", "");
  if (!raw) {
    return {};
  }
  try {
    const parsed = JSON.parse(raw);
    const result = {};
    Object.keys(parsed || {}).forEach(function (key) {
      result[String(key).trim().toLowerCase()] = normalizeRole_(parsed[key]);
    });
    return result;
  } catch (error) {
    throw new Error("LOCAL_ACCOUNT_ROLES_JSON tidak valid.");
  }
}

function requireRoles_(actor, roles) {
  if (roles.indexOf(actor.role) < 0) {
    throw new Error("Role tidak memiliki izin untuk operasi ini.");
  }
}

function parseJsonBody_(e) {
  if (!e || !e.postData || !e.postData.contents) {
    throw new Error("Body JSON tidak tersedia.");
  }
  try {
    const payload = JSON.parse(e.postData.contents);
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
      throw new Error("Body JSON harus berupa object.");
    }
    return payload;
  } catch (error) {
    throw new Error("Body JSON tidak valid.");
  }
}

function verifySignedRequest_(payload) {
  const expectedApiKey = getRequiredProperty_("API_SHARED_KEY");
  if (!constantTimeEqual_(String(payload.api_key || ""), expectedApiKey)) {
    throw new Error("API key tidak valid.");
  }

  const requireHmac =
    getProperty_("REQUIRE_HMAC", "true").toLowerCase() !== "false";
  if (!requireHmac) {
    return;
  }

  const signingKey = getRequiredProperty_("AUTH_SIGNING_KEY");
  const timestamp = Number(payload.auth_ts);
  if (!Number.isFinite(timestamp)) {
    throw new Error("Timestamp autentikasi tidak valid.");
  }
  const nowSeconds = Math.floor(Date.now() / 1000);
  if (Math.abs(nowSeconds - timestamp) > 300) {
    throw new Error("Request kedaluwarsa.");
  }

  const nonce = String(payload.auth_nonce || "");
  if (!/^[a-f0-9]{32}$/i.test(nonce)) {
    throw new Error("Nonce tidak valid.");
  }
  const cache = CacheService.getScriptCache();
  const nonceKey = "nonce_" + nonce;

  const unsigned = {};
  Object.keys(payload).forEach(function (key) {
    if (
      key !== "api_key" &&
      key !== "auth_ts" &&
      key !== "auth_nonce" &&
      key !== "auth_body_sha256" &&
      key !== "auth_sig"
    ) {
      unsigned[key] = payload[key];
    }
  });
  const canonical = stableStringify_(unsigned);
  const bodyHash = sha256Hex_(canonical);
  if (
    !constantTimeEqual_(
      String(payload.auth_body_sha256 || "").toLowerCase(),
      bodyHash
    )
  ) {
    throw new Error("Hash body tidak valid.");
  }
  const expectedSignature = hmacSha256Hex_(
    bodyHash + "|" + String(payload.auth_ts) + "|" + nonce,
    signingKey
  );
  if (
    !constantTimeEqual_(
      String(payload.auth_sig || "").toLowerCase(),
      expectedSignature
    )
  ) {
    throw new Error("Signature request tidak valid.");
  }
  const nonceLock = LockService.getScriptLock();
  nonceLock.waitLock(5000);
  try {
    if (cache.get(nonceKey)) {
      throw new Error("Request duplikat ditolak.");
    }
    cache.put(nonceKey, "1", 600);
  } finally {
    nonceLock.releaseLock();
  }
}

function stableStringify_(value) {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return (
      "[" +
      value
        .map(function (item) {
          return stableStringify_(item);
        })
        .join(",") +
      "]"
    );
  }
  const keys = Object.keys(value).sort();
  return (
    "{" +
    keys
      .map(function (key) {
        return JSON.stringify(key) + ":" + stableStringify_(value[key]);
      })
      .join(",") +
    "}"
  );
}

function sha256Hex_(text) {
  return bytesToHex_(
    Utilities.computeDigest(
      Utilities.DigestAlgorithm.SHA_256,
      String(text),
      Utilities.Charset.UTF_8
    )
  );
}

function hmacSha256Hex_(text, key) {
  return bytesToHex_(
    Utilities.computeHmacSha256Signature(
      String(text),
      String(key),
      Utilities.Charset.UTF_8
    )
  );
}

function bytesToHex_(bytes) {
  return bytes
    .map(function (value) {
      const normalized = value < 0 ? value + 256 : value;
      return ("0" + normalized.toString(16)).slice(-2);
    })
    .join("");
}

function constantTimeEqual_(left, right) {
  const a = String(left || "");
  const b = String(right || "");
  let mismatch = a.length ^ b.length;
  const length = Math.max(a.length, b.length);
  for (let i = 0; i < length; i += 1) {
    mismatch |= (a.charCodeAt(i % Math.max(1, a.length)) || 0) ^
      (b.charCodeAt(i % Math.max(1, b.length)) || 0);
  }
  return mismatch === 0;
}

function getSpreadsheet_() {
  return SpreadsheetApp.openById(getRequiredProperty_("SPREADSHEET_ID"));
}

function ensureSchema_(spreadsheet) {
  ensureSheet_(spreadsheet, SHEET_STOCK, STOCK_HEADERS);
  ensureSheet_(spreadsheet, SHEET_HISTORY, HISTORY_HEADERS);
  ensureSheet_(spreadsheet, SHEET_AUDIT, AUDIT_HEADERS);
  ensureSheet_(spreadsheet, SHEET_ACCOUNTS, ACCOUNT_HEADERS);
}

function ensureSheet_(spreadsheet, name, headers) {
  let sheet = spreadsheet.getSheetByName(name);
  if (!sheet) {
    sheet = spreadsheet.insertSheet(name);
  }
  const current = sheet.getLastRow()
    ? sheet.getRange(1, 1, 1, Math.max(headers.length, sheet.getLastColumn())).getValues()[0]
    : [];
  const correct = headers.every(function (header, index) {
    return String(current[index] || "").trim() === header;
  });
  if (!correct) {
    if (sheet.getLastRow() === 0) {
      sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    } else {
      throw new Error(
        "Header sheet " + name + " tidak cocok. Jalankan migrasi sebelum menggunakan backend."
      );
    }
  }
  sheet.setFrozenRows(1);
  return sheet;
}

function getSheetValues_(sheet) {
  if (!sheet || sheet.getLastRow() < 1) {
    return [];
  }
  return sheet
    .getRange(1, 1, sheet.getLastRow(), sheet.getLastColumn())
    .getValues();
}

function dataRows_(sheet, headers) {
  if (!sheet || sheet.getLastRow() <= 1) {
    return [];
  }
  return sheet
    .getRange(2, 1, sheet.getLastRow() - 1, headers.length)
    .getValues();
}

function resetSheet_(sheet, headers) {
  sheet.clearContents();
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  sheet.setFrozenRows(1);
}

function findStockRow_(sheet, name) {
  const wanted = String(name || "").trim().toLowerCase();
  const rows = dataRows_(sheet, STOCK_HEADERS);
  for (let index = 0; index < rows.length; index += 1) {
    if (String(rows[index][0] || "").trim().toLowerCase() === wanted) {
      return {
        row: index + 2,
        name: String(rows[index][0]),
        quantity: nonNegativeInt_(rows[index][1], "Stok"),
        status: normalizeItemStatus_(rows[index][2]),
        minimum: positiveInt_(rows[index][3] || 5, "Batas minimum"),
      };
    }
  }
  return null;
}

function findHistoryRow_(sheet, txId) {
  const wanted = String(txId || "").trim();
  const rows = dataRows_(sheet, HISTORY_HEADERS);
  for (let index = 0; index < rows.length; index += 1) {
    if (String(rows[index][0] || "").trim() === wanted) {
      return {
        row: index + 2,
        txId: String(rows[index][0]),
        time: rows[index][1],
        date: rows[index][2],
        type: String(rows[index][3] || "").toUpperCase(),
        item: String(rows[index][4] || ""),
        amount: positiveInt_(rows[index][5], "Jumlah transaksi"),
        note: String(rows[index][6] || ""),
        proofUrl: String(rows[index][7] || ""),
        status: String(rows[index][8] || "").toUpperCase(),
        reference: String(rows[index][9] || ""),
      };
    }
  }
  return null;
}

function findAccount_(sheet, usernameOrRequestId) {
  const wanted = String(usernameOrRequestId || "").trim().toLowerCase();
  const rows = dataRows_(sheet, ACCOUNT_HEADERS);
  for (let index = 0; index < rows.length; index += 1) {
    const requestId = String(rows[index][0] || "").trim().toLowerCase();
    const username = String(rows[index][2] || "").trim().toLowerCase();
    if (username === wanted || requestId === wanted) {
      return {
        row: index + 2,
        requestId: String(rows[index][0] || ""),
        fullName: String(rows[index][1] || ""),
        username: String(rows[index][2] || ""),
        passwordVerifier: String(rows[index][3] || "").toLowerCase(),
        position: String(rows[index][4] || ""),
        requestedRole: String(rows[index][5] || ""),
        role: String(rows[index][6] || ""),
        status: String(rows[index][7] || "").toUpperCase(),
        createdAt: rows[index][8],
        updatedAt: rows[index][9],
        approvedBy: String(rows[index][10] || ""),
      };
    }
  }
  return null;
}

function countActiveDevelopers_(sheet) {
  return dataRows_(sheet, ACCOUNT_HEADERS).filter(function (row) {
    return (
      String(row[6] || "") === "Developer" &&
      String(row[7] || "").toUpperCase() === "ACTIVE"
    );
  }).length;
}

function writeAudit_(spreadsheet, actor, action, txId, detail) {
  spreadsheet.getSheetByName(SHEET_AUDIT).appendRow([
    nowText_(),
    actor.username,
    actor.role,
    action,
    txId || "",
    cleanText_(detail, 500, false),
  ]);
}

function bumpRevision_() {
  const properties = PropertiesService.getScriptProperties();
  const current = Number(properties.getProperty("DATA_REVISION") || "0");
  const next = Number.isFinite(current) ? current + 1 : Date.now();
  properties.setProperty("DATA_REVISION", String(next));
  return String(next);
}

function withScriptLock_(callback) {
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    return callback();
  } finally {
    lock.releaseLock();
  }
}

function createServerBackup_() {
  const spreadsheet = getSpreadsheet_();
  const source = DriveApp.getFileById(spreadsheet.getId());
  const folderId = getProperty_("DRIVE_FOLDER_ID", "");
  const folder = folderId ? DriveApp.getFolderById(folderId) : DriveApp.getRootFolder();
  const name =
    "WMS_BACKUP_" +
    Utilities.formatDate(new Date(), "Asia/Jakarta", "yyyyMMdd_HHmmss");
  const copy = source.makeCopy(name, folder);
  const time = nowText_();
  const properties = PropertiesService.getScriptProperties();
  properties.setProperties({
    LAST_BACKUP_TIME: time,
    LAST_BACKUP_URL: copy.getUrl(),
    LAST_BACKUP_NAME: name,
  });
  return {
    backup_time: time,
    backup_url: copy.getUrl(),
    backup_name: name,
  };
}

function backupTriggerInstalled_() {
  return ScriptApp.getProjectTriggers().some(function (trigger) {
    return trigger.getHandlerFunction() === "scheduledDailyBackup";
  });
}

function saveEvidence_(payload) {
  const encoded = String(payload.image_base64 || "");
  if (!encoded) {
    return "";
  }
  const bytes = Utilities.base64Decode(encoded);
  if (bytes.length > 6 * 1024 * 1024) {
    throw new Error("Ukuran bukti melebihi 6 MB.");
  }
  const folderId = getProperty_("DRIVE_FOLDER_ID", "");
  const folder = folderId ? DriveApp.getFolderById(folderId) : DriveApp.getRootFolder();
  const fileName = cleanText_(payload.image_name || "bukti.jpg", 120, true).replace(
    /[^A-Za-z0-9._-]/g,
    "_"
  );
  const blob = Utilities.newBlob(bytes, "image/jpeg", fileName);
  return folder.createFile(blob).getUrl();
}

function stockAlert_(name, quantity, minimum) {
  if (quantity <= 0) {
    return "🚨 STOK HABIS\n📦 " + name + "\nSisa: 0 pcs";
  }
  if (quantity <= minimum) {
    return (
      "⚠️ STOK KRITIS\n📦 " +
      name +
      "\nSisa: " +
      quantity +
      " pcs\nMinimum: " +
      minimum +
      " pcs"
    );
  }
  return "";
}

function normalizeUsername_(value) {
  const username = String(value || "").trim().toLowerCase();
  if (!/^[a-z0-9._-]{4,32}$/.test(username)) {
    throw new Error("Username tidak valid.");
  }
  return username;
}

function normalizeRole_(value) {
  const text = String(value || "").trim().toLowerCase();
  const roles = {
    staff: "Staff",
    admin: "Admin",
    boss: "Boss",
    bos: "Boss",
    developer: "Developer",
  };
  const role = roles[text];
  if (!role) {
    throw new Error("Role tidak valid.");
  }
  return role;
}

function normalizeItemStatus_(value) {
  const text = String(value || "Aktif").trim().toLowerCase();
  if (text === "aktif") {
    return "Aktif";
  }
  if (text === "nonaktif" || text === "non-aktif" || text === "inactive") {
    return "Nonaktif";
  }
  throw new Error("Status barang tidak valid.");
}

function cleanText_(value, maxLength, required) {
  const text = String(value === undefined || value === null ? "" : value)
    .replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, "")
    .trim();
  if (required && !text) {
    throw new Error("Input wajib diisi.");
  }
  if (text.length > maxLength) {
    throw new Error("Input melebihi batas " + maxLength + " karakter.");
  }
  return text || "-";
}

function intValue_(value, label) {
  const text = String(value).trim();
  if (!/^-?\d+(?:\.0+)?$/.test(text)) {
    throw new Error(label + " bukan angka bulat yang valid.");
  }
  return Number(text);
}

function nonNegativeInt_(value, label) {
  const result = intValue_(value, label);
  if (result < 0) {
    throw new Error(label + " tidak boleh negatif.");
  }
  return result;
}

function positiveInt_(value, label) {
  const result = intValue_(value, label);
  if (result < 1) {
    throw new Error(label + " minimal 1.");
  }
  return result;
}

function sameText_(left, right) {
  return String(left || "").trim().toLowerCase() ===
    String(right || "").trim().toLowerCase();
}

function nowText_() {
  return Utilities.formatDate(
    new Date(),
    "Asia/Jakarta",
    "dd-MM-yyyy HH:mm:ss"
  );
}

function getProperty_(name, fallback) {
  const value = PropertiesService.getScriptProperties().getProperty(name);
  return value === null || value === undefined ? fallback : value;
}

function getRequiredProperty_(name) {
  const value = getProperty_(name, "");
  if (!value) {
    throw new Error("Script Property " + name + " belum diisi.");
  }
  return value;
}

function safeError_(error) {
  let text = String(error && error.message ? error.message : error || "Operasi gagal.");
  [
    getProperty_("API_SHARED_KEY", ""),
    getProperty_("AUTH_SIGNING_KEY", ""),
    getProperty_("ACCOUNT_TELEGRAM_BOT_TOKEN", ""),
  ].forEach(function (secret) {
    if (secret) {
      text = text.split(secret).join("***REDACTED***");
    }
  });
  return text.slice(0, 500);
}

function jsonResponse_(data) {
  return ContentService.createTextOutput(JSON.stringify(data)).setMimeType(
    ContentService.MimeType.JSON
  );
}

function setupTelegramApprovalWebhook() {
  const token = getRequiredProperty_("ACCOUNT_TELEGRAM_BOT_TOKEN");
  let secret = getProperty_("TELEGRAM_WEBHOOK_SECRET", "");
  if (!secret) {
    secret = Utilities.getUuid().replace(/-/g, "") +
      Utilities.getUuid().replace(/-/g, "");
    PropertiesService.getScriptProperties().setProperty(
      "TELEGRAM_WEBHOOK_SECRET",
      secret
    );
  }
  const serviceUrl = ScriptApp.getService().getUrl();
  if (!serviceUrl) {
    throw new Error("Deploy Web App terlebih dahulu.");
  }
  const webhookUrl =
    serviceUrl + "?telegram_secret=" + encodeURIComponent(secret);
  const response = UrlFetchApp.fetch(
    "https://api.telegram.org/bot" + token + "/setWebhook",
    {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify({
        url: webhookUrl,
        allowed_updates: ["callback_query"],
        drop_pending_updates: true,
      }),
      muteHttpExceptions: true,
    }
  );
  const result = JSON.parse(response.getContentText());
  if (!result.ok) {
    throw new Error("Telegram menolak webhook: " + String(result.description || ""));
  }
  return result;
}

function handleTelegramWebhook_(e) {
  try {
    const expectedSecret = getRequiredProperty_("TELEGRAM_WEBHOOK_SECRET");
    if (
      !constantTimeEqual_(
        String(e.parameter.telegram_secret || ""),
        expectedSecret
      )
    ) {
      throw new Error("Webhook secret tidak valid.");
    }
    const update = parseJsonBody_(e);
    const callback = update.callback_query;
    if (!callback || !callback.data) {
      return jsonResponse_({ ok: true, ignored: true });
    }

    const approverId = getProperty_("TELEGRAM_APPROVER_USER_ID", "");
    if (
      approverId &&
      String(callback.from && callback.from.id) !== String(approverId)
    ) {
      answerTelegramCallback_(
        callback.id,
        "Anda tidak memiliki izin menyetujui akun."
      );
      return jsonResponse_({ ok: true, ignored: true });
    }

    const parts = String(callback.data).split("|");
    if (parts.length !== 3 || parts[0] !== "acc") {
      throw new Error("Callback Telegram tidak valid.");
    }
    const requestId = parts[1];
    const decision = parts[2];
    if (
      decision !== "REJECT" &&
      ["Staff", "Admin"].indexOf(decision) < 0
    ) {
      throw new Error(
        "Role Boss dan Developer hanya dapat diberikan dari halaman Kelola Akun."
      );
    }

    const result = withScriptLock_(function () {
      const spreadsheet = getSpreadsheet_();
      ensureSchema_(spreadsheet);
      const sheet = spreadsheet.getSheetByName(SHEET_ACCOUNTS);
      const account = findAccount_(sheet, requestId);
      if (!account) {
        throw new Error("Permintaan akun tidak ditemukan.");
      }
      if (account.status !== "PENDING") {
        throw new Error("Permintaan akun sudah diproses.");
      }
      const actor = { username: "Telegram Approver", role: "Developer" };
      if (decision === "REJECT") {
        sheet.getRange(account.row, 7, 1, 5).setValues([
          ["", "REJECTED", account.createdAt, nowText_(), actor.username],
        ]);
        writeAudit_(
          spreadsheet,
          actor,
          "ACCOUNT_REJECT",
          account.requestId,
          account.username
        );
        bumpRevision_();
        return "Permintaan @" + account.username + " ditolak.";
      }
      sheet.getRange(account.row, 7, 1, 5).setValues([
        [decision, "ACTIVE", account.createdAt, nowText_(), actor.username],
      ]);
      writeAudit_(
        spreadsheet,
        actor,
        "ACCOUNT_APPROVE",
        account.requestId,
        account.username + " sebagai " + decision
      );
      bumpRevision_();
      return "Akun @" + account.username + " aktif sebagai " + decision + ".";
    });

    answerTelegramCallback_(callback.id, result);
    return jsonResponse_({ ok: true });
  } catch (error) {
    console.error("[Telegram webhook] " + safeError_(error));
    return jsonResponse_({ ok: false, message: safeError_(error) });
  }
}

function answerTelegramCallback_(callbackId, message) {
  const token = getRequiredProperty_("ACCOUNT_TELEGRAM_BOT_TOKEN");
  UrlFetchApp.fetch(
    "https://api.telegram.org/bot" + token + "/answerCallbackQuery",
    {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify({
        callback_query_id: callbackId,
        text: String(message).slice(0, 180),
        show_alert: true,
      }),
      muteHttpExceptions: true,
    }
  );
}
