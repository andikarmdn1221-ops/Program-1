/**
 * Mirai Backend v7.6
 *
 * Semua credential wajib disimpan di Apps Script > Project Settings >
 * Script Properties. Jangan menaruh token, key, atau ID produksi di file ini.
 *
 * Wajib:
 * - SPREADSHEET_ID
 * - API_SHARED_KEY
 * - AUTH_SIGNING_KEY
 *
 * Wajib untuk production:
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

const BACKEND_VERSION = "7.6-production";
const SCHEMA_CACHE_SECONDS = 300;
const MAX_ROLLBACK_CELLS = 150000;
const MAX_QUANTITY = 1000000000;
const MAX_PBKDF2_ITERATIONS = 1000000;
const ACCOUNT_AUTH_MAX_ATTEMPTS = 5;
const ACCOUNT_AUTH_WINDOW_SECONDS = 900;
const ACCOUNT_AUTH_LOCK_SECONDS = 300;
const SHEET_STOCK = "stok";
const SHEET_HISTORY = "riwayat";
const SHEET_AUDIT = "audit";
const SHEET_ACCOUNTS = "accounts";
let requestSpreadsheet_ = null;

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
  const requestStartedAt = Date.now();
  requestSpreadsheet_ = null;
  try {
    if (e && e.parameter && e.parameter.telegram_secret) {
      return handleTelegramWebhook_(e);
    }

    const payload = parseJsonBody_(e);
    verifySignedRequest_(payload);
    const result = routeRequest_(payload);
    return jsonResponse_(
      Object.assign({ ok: true }, result || {}, {
        server_duration_ms: Date.now() - requestStartedAt,
      })
    );
  } catch (error) {
    console.error("[WMS backend] " + safeError_(error));
    return jsonResponse_({
      ok: false,
      message: safeError_(error),
      server_duration_ms: Date.now() - requestStartedAt,
    });
  }
}

function routeRequest_(payload) {
  const action = String(payload.action || "").trim();
  requireProductionMutationConfig_(action);
  switch (action) {
    case "health":
      return handleHealth_(payload);
    case "read":
      return withScriptLock_(function () {
        return handleRead_(payload);
      });
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
      return withScriptLock_(function () {
        return handleServerBackup_(payload);
      });
    case "backup_status":
      return handleBackupStatus_(payload);
    case "install_backup_trigger":
      return withScriptLock_(function () {
        return handleInstallBackupTrigger_(payload);
      });
    case "remove_backup_trigger":
      return withScriptLock_(function () {
        return handleRemoveBackupTrigger_(payload);
      });
    case "account_register":
      return withScriptLock_(function () {
        return handleAccountRegister_(payload);
      });
    case "account_auth":
      return withScriptLock_(function () {
        return handleAccountAuth_(payload);
      });
    case "account_validate":
      return withScriptLock_(function () {
        return handleAccountValidate_(payload);
      });
    case "account_list":
      return withScriptLock_(function () {
        return handleAccountList_(payload);
      });
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
  // Endpoint health hanya mengembalikan metadata non-sensitif. Signature dan
  // identitas tetap divalidasi, tetapi tidak perlu membuka Google Sheets.
  resolveHealthIdentity_(payload);
  const properties = PropertiesService.getScriptProperties();
  return {
    backend_version: BACKEND_VERSION,
    data_revision: properties.getProperty("DATA_REVISION") || "0",
    server_time: nowText_(),
    capabilities: backendCapabilities_(),
  };
}

function handleRead_(payload) {
  const spreadsheet = getSpreadsheet_();
  ensureSchema_(spreadsheet);
  // Pakai spreadsheet yang sama untuk validasi akun dan pembacaan data.
  // Sebelumnya proses ini membuka file serta memeriksa schema dua kali.
  const actor = resolveActor_(payload, spreadsheet, true);
  const stockValues = getSheetValues_(spreadsheet.getSheetByName(SHEET_STOCK));
  const historyValues = getSheetValues_(spreadsheet.getSheetByName(SHEET_HISTORY));
  const auditSheet = spreadsheet.getSheetByName(SHEET_AUDIT);
  const canViewAudit = actor.role === "Developer" || actor.role === "Boss";
  const auditValues = canViewAudit ? getSheetValues_(auditSheet) : [AUDIT_HEADERS];
  return {
    backend_version: BACKEND_VERSION,
    data_revision:
      PropertiesService.getScriptProperties().getProperty("DATA_REVISION") || "0",
    server_time: nowText_(),
    capabilities: backendCapabilities_(),
    stok: stockValues,
    riwayat: historyValues,
    audit: auditValues,
    row_counts: {
      stok: Math.max(stockValues.length - 1, 0),
      riwayat: Math.max(historyValues.length - 1, 0),
      audit: Math.max(auditSheet.getLastRow() - 1, 0),
    },
    account_security: dynamicAccountSecurity_(spreadsheet),
  };
}

function dynamicAccountSecurity_(spreadsheet) {
  const rows = dataRows_(
    spreadsheet.getSheetByName(SHEET_ACCOUNTS),
    ACCOUNT_HEADERS
  );
  let pbkdf2 = 0;
  let legacy = 0;
  let activeLegacy = 0;
  rows.forEach(function (row) {
    if (validPasswordVerifier_(String(row[3] || "").toLowerCase())) {
      pbkdf2 += 1;
      return;
    }
    legacy += 1;
    if (String(row[7] || "").toUpperCase() === "ACTIVE") {
      activeLegacy += 1;
    }
  });
  return {
    pbkdf2: pbkdf2,
    legacy: legacy,
    active_legacy: activeLegacy,
  };
}

function backendCapabilities_() {
  const properties = PropertiesService.getScriptProperties();
  let localRolesEnforced = false;
  try {
    localRolesEnforced = Object.keys(trustedLocalRoles_()).length > 0;
  } catch (error) {
    localRolesEnforced = false;
  }
  return {
    hmac_required:
      String(properties.getProperty("REQUIRE_HMAC") || "").toLowerCase() ===
      "true",
    account_auth_rate_limit: true,
    idempotent_mutations: true,
    formula_guard: true,
    mutation_rollback: true,
    backup_before_reset:
      String(
        properties.getProperty("REQUIRE_SERVER_BACKUP_BEFORE_RESET") || ""
      ).toLowerCase() === "true",
    drive_folder_configured: Boolean(properties.getProperty("DRIVE_FOLDER_ID")),
    local_roles_enforced: localRolesEnforced,
    account_approval_configured: accountApprovalConfigured_(),
  };
}

function requireProductionMutationConfig_(action) {
  const readOnlyActions = [
    "health",
    "read",
    "backup_status",
    "account_auth",
    "account_validate",
    "account_list",
  ];
  if (readOnlyActions.indexOf(action) >= 0) {
    return;
  }
  getRequiredProperty_("DRIVE_FOLDER_ID");
  if (
    getRequiredProperty_("REQUIRE_SERVER_BACKUP_BEFORE_RESET").toLowerCase() !==
    "true"
  ) {
    throw new Error("REQUIRE_SERVER_BACKUP_BEFORE_RESET wajib true.");
  }
  if (action === "account_register") {
    [
      "ACCOUNT_TELEGRAM_BOT_TOKEN",
      "ACCOUNT_TELEGRAM_CHAT_ID",
      "TELEGRAM_APPROVER_USER_ID",
      "TELEGRAM_WEBHOOK_SECRET",
    ].forEach(function (name) {
      getRequiredProperty_(name);
    });
    requireAccountApprovalConfig_();
  }
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
  const expectedStock = nonNegativeInt_(
    payload.expected_stock_before,
    "Stok sebelumnya"
  );
  const txId = cleanText_(payload.tx_id, 80, true);
  const spreadsheet = getSpreadsheet_();
  ensureSchema_(spreadsheet);
  const stockSheet = spreadsheet.getSheetByName(SHEET_STOCK);
  const historySheet = spreadsheet.getSheetByName(SHEET_HISTORY);
  const auditSheet = spreadsheet.getSheetByName(SHEET_AUDIT);
  const existing = findHistoryRow_(historySheet, txId);
  if (existing) {
    const replayFinalStock =
      type === "MASUK" ? expectedStock + amount : expectedStock - amount;
    const expectedAuditDetail =
      itemName +
      " " +
      amount +
      " pcs; stok " +
      expectedStock +
      " -> " +
      replayFinalStock;
    const existingAudit = findAuditRow_(
      auditSheet,
      txId,
      "TRANSACTION_" + type
    );
    if (
      existing.type !== type ||
      !sameText_(existing.item, itemName) ||
      existing.amount !== amount ||
      !sameText_(existing.note, note) ||
      !existingAudit ||
      existingAudit.detail !== expectedAuditDetail
    ) {
      throw new Error("ID transaksi sudah digunakan untuk payload yang berbeda.");
    }
    const existingItem = findStockRow_(stockSheet, existing.item);
    if (!existingItem) {
      throw new Error("Transaksi sudah ada tetapi master barang tidak ditemukan.");
    }
    return {
      tx_id: txId,
      stok_akhir: existingItem.quantity,
      file_url: existing.proofUrl,
      alert: stockAlert_(
        existingItem.name,
        existingItem.quantity,
        existingItem.minimum
      ),
      idempotent_replay: true,
    };
  }
  const found = findStockRow_(stockSheet, itemName);
  if (!found) {
    throw new Error("Barang tidak ditemukan.");
  }
  if (found.status !== "Aktif") {
    throw new Error("Barang sedang nonaktif.");
  }

  if (expectedStock !== found.quantity) {
    throw new Error(
      "Stok sudah berubah oleh pengguna lain. Segarkan data lalu ulangi transaksi."
    );
  }

  const finalStock =
    type === "MASUK" ? found.quantity + amount : found.quantity - amount;
  if (finalStock < 0) {
    throw new Error("Stok tidak mencukupi.");
  }

  let proofUrl = "";
  return withSheetRollback_(
    [stockSheet, historySheet, auditSheet],
    function () {
      proofUrl = saveEvidence_(payload);
      stockSheet.getRange(found.row, 2).setValue(finalStock);
      historySheet.appendRow([
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
        found.name +
          " " +
          amount +
          " pcs; stok " +
          found.quantity +
          " -> " +
          finalStock
      );
      bumpRevision_();

      return {
        tx_id: txId,
        stok_akhir: finalStock,
        file_url: proofUrl,
        alert: stockAlert_(found.name, finalStock, found.minimum),
        idempotent_replay: false,
      };
    },
    function () {
      trashEvidence_(proofUrl);
    }
  );
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
  const historySheet = spreadsheet.getSheetByName(SHEET_HISTORY);
  const auditSheet = spreadsheet.getSheetByName(SHEET_AUDIT);
  const txId = cleanText_(payload.tx_id, 80, true);
  const existing = findHistoryRow_(historySheet, txId);
  if (existing) {
    const expectedAuditDetail =
      name + "; stok awal " + initial + "; minimum " + minimum;
    const existingAudit = findAuditRow_(auditSheet, txId, "MASTER_ADD");
    if (
      existing.type !== "BARANG BARU" ||
      !sameText_(existing.item, name) ||
      existing.amount !== initial ||
      !existingAudit ||
      existingAudit.detail !== expectedAuditDetail
    ) {
      throw new Error("ID transaksi sudah digunakan untuk payload yang berbeda.");
    }
    const existingItem = findStockRow_(stockSheet, name);
    if (!existingItem) {
      throw new Error("Transaksi master sudah ada tetapi barang tidak ditemukan.");
    }
    return {
      name: existingItem.name,
      stok_akhir: existingItem.quantity,
      idempotent_replay: true,
    };
  }
  if (findStockRow_(stockSheet, name)) {
    throw new Error("Nama barang sudah digunakan.");
  }
  return withSheetRollback_([stockSheet, historySheet, auditSheet], function () {
    stockSheet.appendRow([name, initial, "Aktif", minimum]);
    historySheet.appendRow([
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
      name + "; stok awal " + initial + "; minimum " + minimum
    );
    bumpRevision_();
    return { name: name, stok_akhir: initial, idempotent_replay: false };
  });
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
  const auditSheet = spreadsheet.getSheetByName(SHEET_AUDIT);
  return withSheetRollback_([sheet, auditSheet], function () {
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
  });
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
  const auditSheet = spreadsheet.getSheetByName(SHEET_AUDIT);
  return withSheetRollback_([stockSheet, auditSheet], function () {
    stockSheet.deleteRow(found.row);
    writeAudit_(spreadsheet, actor, "MASTER_DELETE", "", name);
    bumpRevision_();
    return { deleted: true };
  });
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
  const historySheet = spreadsheet.getSheetByName(SHEET_HISTORY);
  const auditSheet = spreadsheet.getSheetByName(SHEET_AUDIT);
  const txId = cleanText_(payload.tx_id, 80, true);
  const expectedDifference = newStock - expected;
  const existing = findHistoryRow_(historySheet, txId);
  if (existing) {
    const expectedAuditDetail =
      name + " " + expected + " -> " + newStock + "; " + reason;
    const existingAudit = findAuditRow_(auditSheet, txId, "STOCK_ADJUST");
    if (
      existing.type !== "PENYESUAIAN" ||
      !sameText_(existing.item, name) ||
      existing.amount !== expectedDifference ||
      !sameText_(existing.note, reason) ||
      !existingAudit ||
      existingAudit.detail !== expectedAuditDetail
    ) {
      throw new Error("ID transaksi sudah digunakan untuk payload yang berbeda.");
    }
    const existingItem = findStockRow_(stockSheet, name);
    return {
      tx_id: txId,
      selisih: existing.amount,
      stok_akhir: newStock,
      alert: existingItem
        ? stockAlert_(name, newStock, existingItem.minimum)
        : "",
      idempotent_replay: true,
    };
  }
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
  return withSheetRollback_([stockSheet, historySheet, auditSheet], function () {
    stockSheet.getRange(found.row, 2).setValue(newStock);
    historySheet.appendRow([
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
      idempotent_replay: false,
    };
  });
}

function handleTransactionVoid_(payload) {
  const actor = resolveActor_(payload);
  requireRoles_(actor, ["Developer", "Boss", "Admin"]);
  const txId = cleanText_(payload.tx_id, 80, true);
  const spreadsheet = getSpreadsheet_();
  ensureSchema_(spreadsheet);
  const historySheet = spreadsheet.getSheetByName(SHEET_HISTORY);
  const tx = findHistoryRow_(historySheet, txId);
  if (!tx) {
    throw new Error("Transaksi aktif tidak ditemukan.");
  }
  const stockSheet = spreadsheet.getSheetByName(SHEET_STOCK);
  const replayItem = findStockRow_(stockSheet, tx.item);
  if (tx.status === "VOID" && String(tx.reference).indexOf("VOID oleh ") === 0) {
    return {
      voided: true,
      stok_akhir: replayItem ? replayItem.quantity : null,
      idempotent_replay: true,
    };
  }
  if (tx.status !== "AKTIF") {
    throw new Error("Transaksi aktif tidak ditemukan.");
  }
  if (tx.type !== "MASUK" && tx.type !== "KELUAR") {
    throw new Error("Jenis transaksi ini tidak dapat di-void.");
  }

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

  const auditSheet = spreadsheet.getSheetByName(SHEET_AUDIT);
  return withSheetRollback_([stockSheet, historySheet, auditSheet], function () {
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
    return {
      voided: true,
      stok_akhir: finalStock,
      idempotent_replay: false,
    };
  });
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
  const newNote = cleanText_(payload.new_keterangan, 240, false);
  const spreadsheet = getSpreadsheet_();
  ensureSchema_(spreadsheet);
  const historySheet = spreadsheet.getSheetByName(SHEET_HISTORY);
  const existingReplacement = findHistoryRow_(historySheet, newTxId);
  if (existingReplacement) {
    if (
      existingReplacement.type !== newType ||
      !sameText_(existingReplacement.item, newItemName) ||
      existingReplacement.amount !== newAmount ||
      !sameText_(existingReplacement.note, newNote) ||
      existingReplacement.reference !== oldTxId
    ) {
      throw new Error("ID transaksi koreksi sudah digunakan untuk payload berbeda.");
    }
    return { new_tx_id: newTxId, idempotent_replay: true };
  }
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
  if (oldKey !== newKey && projected[oldKey] < 0) {
    throw new Error("Koreksi akan membuat stok lama negatif.");
  }
  projected[newKey] += newType === "MASUK" ? newAmount : -newAmount;
  if (projected[newKey] < 0) {
    throw new Error("Stok tidak mencukupi untuk hasil koreksi.");
  }

  const auditSheet = spreadsheet.getSheetByName(SHEET_AUDIT);
  return withSheetRollback_([stockSheet, historySheet, auditSheet], function () {
    stockSheet.getRange(oldItem.row, 2).setValue(projected[oldKey]);
    stockSheet.getRange(newItem.row, 2).setValue(projected[newKey]);

    historySheet.getRange(oldTx.row, 9).setValue("DIKOREKSI");
    historySheet.getRange(oldTx.row, 10).setValue(newTxId);
    historySheet.appendRow([
      newTxId,
      cleanText_(payload.new_waktu, 40, true),
      cleanText_(payload.new_tanggal, 20, true),
      newType,
      newItem.name,
      newAmount,
      newNote,
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
    return { new_tx_id: newTxId, idempotent_replay: false };
  });
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

  return withSheetRollback_([auditSheet], function () {
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
  });
}

function handleReset_(payload) {
  const actor = resolveActor_(payload);
  requireRoles_(actor, ["Developer"]);
  if (String(payload.confirm || "") !== "RESET-DATABASE") {
    throw new Error("Konfirmasi reset tidak valid.");
  }

  const requireBackup = getProperty_("REQUIRE_SERVER_BACKUP_BEFORE_RESET", "true")
    .toLowerCase() !== "false";
  let backup = null;
  if (requireBackup) {
    backup = createServerBackup_();
  }

  const spreadsheet = getSpreadsheet_();
  ensureSchema_(spreadsheet);
  const stockSheet = spreadsheet.getSheetByName(SHEET_STOCK);
  const historySheet = spreadsheet.getSheetByName(SHEET_HISTORY);
  const auditSheet = spreadsheet.getSheetByName(SHEET_AUDIT);
  return withSheetRollback_([stockSheet, historySheet, auditSheet], function () {
    resetSheet_(stockSheet, STOCK_HEADERS);
    stockSheet
      .getRange(2, 1, DEFAULT_STOCK.length, STOCK_HEADERS.length)
      .setValues(DEFAULT_STOCK);
    resetSheet_(historySheet, HISTORY_HEADERS);
    resetSheet_(auditSheet, AUDIT_HEADERS);
    writeAudit_(
      spreadsheet,
      actor,
      "DATABASE_RESET",
      "",
      "Data operasional dikembalikan ke master awal."
    );
    bumpRevision_();
    return {
      reset: true,
      backup_name: backup ? backup.backup_name : "",
      backup_url: backup ? backup.backup_url : "",
    };
  });
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
      .inTimezone("Asia/Jakarta")
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
  requestSpreadsheet_ = null;
  return withScriptLock_(function () {
    return createServerBackup_();
  });
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
  if (!validPasswordVerifier_(verifier) && !/^[a-f0-9]{64}$/.test(verifier)) {
    throw new Error("Password verifier tidak valid.");
  }

  const spreadsheet = getSpreadsheet_();
  ensureSchema_(spreadsheet);
  const sheet = spreadsheet.getSheetByName(SHEET_ACCOUNTS);
  const requestedId = payload.request_id
    ? cleanText_(payload.request_id, 80, true)
    : "ACC-" + Utilities.getUuid().replace(/-/g, "").slice(0, 16).toUpperCase();
  const existingAccount = findAccount_(sheet, username);
  if (existingAccount && existingAccount.requestId === requestedId) {
    if (
      !sameText_(existingAccount.fullName, fullName) ||
      !sameText_(existingAccount.position, position) ||
      existingAccount.requestedRole !== requestedRole ||
      !constantTimeEqual_(existingAccount.passwordVerifier, verifier)
    ) {
      throw new Error("ID permintaan akun sudah digunakan untuk payload berbeda.");
    }
    return {
      request_id: existingAccount.requestId,
      status: existingAccount.status,
      idempotent_replay: true,
    };
  }
  if (existingAccount || findAccount_(sheet, requestedId)) {
    throw new Error("Username sudah digunakan.");
  }

  const requestId = requestedId;
  const now = nowText_();
  const auditSheet = spreadsheet.getSheetByName(SHEET_AUDIT);
  return withSheetRollback_([sheet, auditSheet], function () {
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
    return {
      request_id: requestId,
      status: "PENDING",
      idempotent_replay: false,
    };
  });
}

function handleAccountAuth_(payload) {
  const username = normalizeUsername_(payload.username);
  const retryAfter = accountAuthRetryAfter_(username);
  if (retryAfter > 0) {
    return {
      authenticated: false,
      status: "LOCKED",
      retry_after: retryAfter,
    };
  }
  const verifier = String(payload.password_verifier || "").trim().toLowerCase();
  const legacyVerifier = String(
    payload.legacy_password_verifier || ""
  ).trim().toLowerCase();
  const suppliedIsPbkdf2 = validPasswordVerifier_(verifier);
  const suppliedIsLegacy = /^[a-f0-9]{64}$/.test(verifier);
  if (!suppliedIsPbkdf2 && !suppliedIsLegacy) {
    return accountAuthFailure_(username);
  }
  const spreadsheet = getSpreadsheet_();
  ensureSchema_(spreadsheet);
  const accountSheet = spreadsheet.getSheetByName(SHEET_ACCOUNTS);
  const account = findAccount_(
    accountSheet,
    username
  );
  if (!account) {
    return accountAuthFailure_(username);
  }
  let passwordUpgraded = false;
  const storedIsPbkdf2 = validPasswordVerifier_(account.passwordVerifier);
  let passwordMatches =
    storedIsPbkdf2 &&
    suppliedIsPbkdf2 &&
    constantTimeEqual_(account.passwordVerifier, verifier);
  if (
    !storedIsPbkdf2 &&
    suppliedIsLegacy &&
    /^[a-f0-9]{64}$/.test(account.passwordVerifier)
  ) {
    passwordMatches = constantTimeEqual_(account.passwordVerifier, verifier);
  }
  if (
    !passwordMatches &&
    canUpgradeLegacyVerifier_(
      account.passwordVerifier,
      legacyVerifier,
      verifier
    )
  ) {
    const auditSheet = spreadsheet.getSheetByName(SHEET_AUDIT);
    withSheetRollback_([accountSheet, auditSheet], function () {
      accountSheet.getRange(account.row, 4).setValue(verifier);
      accountSheet.getRange(account.row, 10).setValue(nowText_());
      writeAudit_(
        spreadsheet,
        { username: account.username, role: account.role || "Staff" },
        "ACCOUNT_PASSWORD_UPGRADED",
        account.requestId,
        "Verifier akun dimigrasikan ke PBKDF2."
      );
      bumpRevision_();
    });
    passwordMatches = true;
    passwordUpgraded = true;
  }
  if (!passwordMatches) {
    return accountAuthFailure_(username);
  }
  clearAccountAuthFailures_(username);
  if (account.status !== "ACTIVE") {
    return { authenticated: false, status: account.status };
  }
  return {
    authenticated: true,
    status: "ACTIVE",
    username: account.username,
    full_name: account.fullName,
    role: account.role,
    password_upgraded: passwordUpgraded,
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
        verifier_scheme: validPasswordVerifier_(String(row[3] || "").toLowerCase())
          ? "PBKDF2"
          : "LEGACY",
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
  const auditSheet = spreadsheet.getSheetByName(SHEET_AUDIT);
  return withSheetRollback_([sheet, auditSheet], function () {
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
  });
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
  const auditSheet = spreadsheet.getSheetByName(SHEET_AUDIT);
  return withSheetRollback_([sheet, auditSheet], function () {
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
  });
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

  const auditSheet = spreadsheet.getSheetByName(SHEET_AUDIT);
  return withSheetRollback_([sheet, auditSheet], function () {
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
  });
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
  const auditSheet = spreadsheet.getSheetByName(SHEET_AUDIT);
  return withSheetRollback_([sheet, auditSheet], function () {
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
  });
}

function resolveHealthIdentity_(payload) {
  const username = cleanText_(payload.actor, 80, true);
  return {
    username: username,
    role: normalizeRole_(payload.role),
    source: String(payload.auth_source || "local").toLowerCase(),
  };
}

function resolveActor_(payload, existingSpreadsheet, schemaReady) {
  const username = cleanText_(payload.actor, 80, true);
  const source = String(payload.auth_source || "local").toLowerCase();
  let role = normalizeRole_(payload.role);

  const spreadsheet = existingSpreadsheet || getSpreadsheet_();
  if (!schemaReady) {
    ensureSchema_(spreadsheet);
  }
  const account = findAccount_(
    spreadsheet.getSheetByName(SHEET_ACCOUNTS),
    username
  );

  if (source === "dynamic") {
    if (!account || account.status !== "ACTIVE") {
      throw new Error("Akun telah dinonaktifkan atau dihapus.");
    }
    role = normalizeRole_(account.role);
  } else if (source === "local") {
    const trusted = trustedLocalRoles_();
    if (!Object.keys(trusted).length) {
      throw new Error("LOCAL_ACCOUNT_ROLES_JSON wajib diisi pada backend production.");
    }
    const trustedRole = trusted[String(username).trim().toLowerCase()];
    if (!trustedRole) {
      throw new Error("Akun lokal tidak terdaftar pada backend.");
    }
    role = normalizeRole_(trustedRole);
  } else {
    throw new Error("Sumber autentikasi tidak valid.");
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
  const signingKey = getRequiredProperty_("AUTH_SIGNING_KEY");
  if (expectedApiKey.length < 32 || signingKey.length < 32) {
    throw new Error("API_SHARED_KEY dan AUTH_SIGNING_KEY minimal 32 karakter.");
  }
  if (constantTimeEqual_(expectedApiKey, signingKey)) {
    throw new Error("API_SHARED_KEY dan AUTH_SIGNING_KEY harus berbeda.");
  }
  if (!constantTimeEqual_(String(payload.api_key || ""), expectedApiKey)) {
    throw new Error("API key tidak valid.");
  }

  const requireHmac =
    getRequiredProperty_("REQUIRE_HMAC").toLowerCase() === "true";
  if (!requireHmac) {
    throw new Error("REQUIRE_HMAC wajib true pada backend production.");
  }

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
  if (!requestSpreadsheet_) {
    requestSpreadsheet_ = SpreadsheetApp.openById(
      getRequiredProperty_("SPREADSHEET_ID")
    );
  }
  return requestSpreadsheet_;
}

function ensureSchema_(spreadsheet) {
  const cache = CacheService.getScriptCache();
  const cacheKey = "schema_ready_" + BACKEND_VERSION;
  if (cache.get(cacheKey) === "1") {
    return;
  }

  ensureSheet_(spreadsheet, SHEET_STOCK, STOCK_HEADERS);
  ensureSheet_(spreadsheet, SHEET_HISTORY, HISTORY_HEADERS);
  ensureSheet_(spreadsheet, SHEET_AUDIT, AUDIT_HEADERS);
  ensureSheet_(spreadsheet, SHEET_ACCOUNTS, ACCOUNT_HEADERS);
  cache.put(cacheKey, "1", SCHEMA_CACHE_SECONDS);
}

function ensureSheet_(spreadsheet, name, headers) {
  let sheet = spreadsheet.getSheetByName(name);
  if (!sheet) {
    sheet = spreadsheet.insertSheet(name);
  }
  let lastRow = sheet.getLastRow();
  const current = lastRow
    ? sheet.getRange(1, 1, 1, Math.max(headers.length, sheet.getLastColumn())).getValues()[0]
    : [];
  const correct = headers.every(function (header, index) {
    return String(current[index] || "").trim() === header;
  });
  if (!correct) {
    if (lastRow === 0) {
      sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
      lastRow = 1;
    } else {
      throw new Error(
        "Header sheet " + name + " tidak cocok. Jalankan migrasi sebelum menggunakan backend."
      );
    }
  }
  // Hindari operasi tulis pada setiap request hanya untuk pengaturan visual.
  if (lastRow === 1 && sheet.getFrozenRows() !== 1) {
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function getSheetValues_(sheet) {
  if (!sheet) {
    return [];
  }
  const lastRow = sheet.getLastRow();
  if (lastRow < 1) {
    return [];
  }
  const lastColumn = sheet.getLastColumn();
  return sheet
    .getRange(1, 1, lastRow, lastColumn)
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
        // Penyesuaian stok dapat menyimpan selisih nol atau negatif.
        amount: intValue_(rows[index][5], "Jumlah transaksi"),
        note: String(rows[index][6] || ""),
        proofUrl: String(rows[index][7] || ""),
        status: String(rows[index][8] || "").toUpperCase(),
        reference: String(rows[index][9] || ""),
      };
    }
  }
  return null;
}

function findAuditRow_(sheet, txId, action) {
  const wantedId = String(txId || "").trim();
  const wantedAction = String(action || "").trim();
  const rows = dataRows_(sheet, AUDIT_HEADERS);
  for (let index = rows.length - 1; index >= 0; index -= 1) {
    if (
      String(rows[index][3] || "").trim() === wantedAction &&
      String(rows[index][4] || "").trim() === wantedId
    ) {
      return {
        row: index + 2,
        detail: String(rows[index][5] || ""),
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
    cleanText_(actor.username, 80, true),
    normalizeRole_(actor.role),
    cleanText_(action, 80, true),
    txId ? cleanText_(txId, 80, true) : "",
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

function withSheetRollback_(sheets, callback, cleanupCallback) {
  const snapshots = [];
  let totalCells = 0;
  sheets.forEach(function (sheet) {
    const snapshot = snapshotSheet_(sheet);
    totalCells += snapshot.rows * snapshot.columns;
    if (totalCells > MAX_ROLLBACK_CELLS) {
      throw new Error(
        "Data operasional melewati batas mutasi aman. Arsipkan riwayat/audit lalu coba lagi."
      );
    }
    snapshots.push(snapshot);
  });

  try {
    return callback();
  } catch (error) {
    const rollbackErrors = [];
    snapshots.forEach(function (snapshot) {
      try {
        restoreSheetSnapshot_(snapshot);
      } catch (rollbackError) {
        rollbackErrors.push(safeError_(rollbackError));
      }
    });
    if (cleanupCallback) {
      try {
        cleanupCallback();
      } catch (cleanupError) {
        console.error("[WMS cleanup] " + safeError_(cleanupError));
      }
    }
    if (rollbackErrors.length) {
      console.error("[WMS rollback] " + rollbackErrors.join("; "));
      throw new Error(
        "Operasi gagal dan rollback otomatis tidak lengkap. Jangan ulangi sebelum memeriksa riwayat dan audit."
      );
    }
    throw error;
  }
}

function snapshotSheet_(sheet) {
  const rows = Math.max(sheet.getLastRow(), 1);
  const columns = Math.max(sheet.getLastColumn(), 1);
  const range = sheet.getRange(1, 1, rows, columns);
  const values = range.getValues();
  const formulas = range.getFormulas();
  return {
    sheet: sheet,
    rows: rows,
    columns: columns,
    values: values.map(function (row, rowIndex) {
      return row.map(function (value, columnIndex) {
        return formulas[rowIndex][columnIndex] || value;
      });
    }),
  };
}

function restoreSheetSnapshot_(snapshot) {
  const sheet = snapshot.sheet;
  const rows = Math.max(sheet.getLastRow(), snapshot.rows, 1);
  const columns = Math.max(sheet.getLastColumn(), snapshot.columns, 1);
  sheet.getRange(1, 1, rows, columns).clearContent();
  sheet
    .getRange(1, 1, snapshot.rows, snapshot.columns)
    .setValues(snapshot.values);
  SpreadsheetApp.flush();
}

function createServerBackup_() {
  const spreadsheet = getSpreadsheet_();
  SpreadsheetApp.flush();
  const source = DriveApp.getFileById(spreadsheet.getId());
  const folderId = getRequiredProperty_("DRIVE_FOLDER_ID");
  const folder = DriveApp.getFolderById(folderId);
  const name =
    "WMS_BACKUP_" +
    Utilities.formatDate(new Date(), "Asia/Jakarta", "yyyyMMdd_HHmmss");
  const copy = source.makeCopy(name, folder);
  const backupSpreadsheet = SpreadsheetApp.openById(copy.getId());
  [SHEET_STOCK, SHEET_HISTORY, SHEET_AUDIT, SHEET_ACCOUNTS].forEach(
    function (sheetName) {
      const sourceSheet = spreadsheet.getSheetByName(sheetName);
      const backupSheet = backupSpreadsheet.getSheetByName(sheetName);
      if (
        !sourceSheet ||
        !backupSheet ||
        sourceSheet.getLastRow() !== backupSheet.getLastRow()
      ) {
        copy.setTrashed(true);
        throw new Error("Verifikasi backup gagal pada sheet " + sheetName + ".");
      }
    }
  );
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
  if (String(payload.image_mime || "").toLowerCase() !== "image/jpeg") {
    throw new Error("Bukti transaksi wajib berupa JPEG yang sudah divalidasi.");
  }
  if (encoded.length > 8 * 1024 * 1024 + 1024) {
    throw new Error("Ukuran bukti melebihi batas aman.");
  }
  const bytes = Utilities.base64Decode(encoded);
  if (bytes.length > 6 * 1024 * 1024) {
    throw new Error("Ukuran bukti melebihi 6 MB.");
  }
  if (
    bytes.length < 4 ||
    (bytes[0] & 255) !== 255 ||
    (bytes[1] & 255) !== 216 ||
    (bytes[2] & 255) !== 255 ||
    (bytes[bytes.length - 2] & 255) !== 255 ||
    (bytes[bytes.length - 1] & 255) !== 217
  ) {
    throw new Error("Isi bukti bukan file JPEG yang valid.");
  }
  const folderId = getRequiredProperty_("DRIVE_FOLDER_ID");
  const folder = DriveApp.getFolderById(folderId);
  const fileName = cleanText_(payload.image_name || "bukti.jpg", 120, true).replace(
    /[^A-Za-z0-9._-]/g,
    "_"
  );
  if (!/\.jpe?g$/i.test(fileName)) {
    throw new Error("Nama bukti harus memakai ekstensi .jpg atau .jpeg.");
  }
  const blob = Utilities.newBlob(bytes, "image/jpeg", fileName);
  return folder.createFile(blob).getUrl();
}

function trashEvidence_(fileUrl) {
  const match = String(fileUrl || "").match(/[-A-Za-z0-9_]{20,}/);
  if (match) {
    DriveApp.getFileById(match[0]).setTrashed(true);
  }
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

function validPasswordVerifier_(value) {
  const match = String(value || "").match(
    /^pbkdf2_sha256\$(\d+)\$[a-f0-9]{32}\$[a-f0-9]{64}$/
  );
  return Boolean(
    match &&
      Number(match[1]) >= 200000 &&
      Number(match[1]) <= MAX_PBKDF2_ITERATIONS
  );
}

function canUpgradeLegacyVerifier_(stored, legacySupplied, replacement) {
  const storedText = String(stored || "").toLowerCase();
  const legacyText = String(legacySupplied || "").toLowerCase();
  return (
    /^[a-f0-9]{64}$/.test(storedText) &&
    /^[a-f0-9]{64}$/.test(legacyText) &&
    validPasswordVerifier_(String(replacement || "").toLowerCase()) &&
    constantTimeEqual_(storedText, legacyText)
  );
}

function accountAuthCacheKey_(username) {
  // Username sudah dinormalisasi menjadi maksimal 32 karakter aman untuk cache key.
  return "account_auth_" + String(username).toLowerCase();
}

function readAccountAuthState_(username, nowSeconds) {
  const cache = CacheService.getScriptCache();
  const key = accountAuthCacheKey_(username);
  let state = null;
  try {
    state = JSON.parse(cache.get(key) || "null");
  } catch (error) {
    state = null;
  }
  if (!state || Number(state.window_started_at) <= 0) {
    return { attempts: 0, window_started_at: nowSeconds, locked_until: 0 };
  }
  if (
    Number(state.locked_until || 0) <= nowSeconds &&
    nowSeconds - Number(state.window_started_at) >= ACCOUNT_AUTH_WINDOW_SECONDS
  ) {
    cache.remove(key);
    return { attempts: 0, window_started_at: nowSeconds, locked_until: 0 };
  }
  return state;
}

function accountAuthRetryAfter_(username) {
  const nowSeconds = Math.floor(Date.now() / 1000);
  const state = readAccountAuthState_(username, nowSeconds);
  return Math.max(0, Math.ceil(Number(state.locked_until || 0) - nowSeconds));
}

function accountAuthFailure_(username) {
  const nowSeconds = Math.floor(Date.now() / 1000);
  const cache = CacheService.getScriptCache();
  const key = accountAuthCacheKey_(username);
  const state = readAccountAuthState_(username, nowSeconds);
  state.attempts = Number(state.attempts || 0) + 1;
  if (state.attempts >= ACCOUNT_AUTH_MAX_ATTEMPTS) {
    state.attempts = 0;
    state.window_started_at = nowSeconds;
    state.locked_until = nowSeconds + ACCOUNT_AUTH_LOCK_SECONDS;
  }
  cache.put(
    key,
    JSON.stringify(state),
    ACCOUNT_AUTH_WINDOW_SECONDS + ACCOUNT_AUTH_LOCK_SECONDS
  );
  const retryAfter = Math.max(
    0,
    Math.ceil(Number(state.locked_until || 0) - nowSeconds)
  );
  return {
    authenticated: false,
    status: retryAfter > 0 ? "LOCKED" : "INVALID",
    retry_after: retryAfter,
  };
}

function clearAccountAuthFailures_(username) {
  CacheService.getScriptCache().remove(accountAuthCacheKey_(username));
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
  if (text !== "-" && /^[=+\-@]/.test(text)) {
    throw new Error("Input tidak boleh diawali karakter formula spreadsheet.");
  }
  return text || "-";
}

function intValue_(value, label) {
  const text = String(value).trim();
  if (!/^-?\d+(?:\.0+)?$/.test(text)) {
    throw new Error(label + " bukan angka bulat yang valid.");
  }
  const result = Number(text);
  if (!Number.isSafeInteger(result) || Math.abs(result) > MAX_QUANTITY) {
    throw new Error(label + " melewati batas aman " + MAX_QUANTITY + ".");
  }
  return result;
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

function accountApprovalConfigured_() {
  const token = getProperty_("ACCOUNT_TELEGRAM_BOT_TOKEN", "");
  const chatId = getProperty_("ACCOUNT_TELEGRAM_CHAT_ID", "");
  const approverId = getProperty_("TELEGRAM_APPROVER_USER_ID", "");
  const webhookSecret = getProperty_("TELEGRAM_WEBHOOK_SECRET", "");
  return (
    /^\d{5,}:[A-Za-z0-9_-]{20,}$/.test(token) &&
    /^-?\d+$/.test(chatId) &&
    /^\d+$/.test(approverId) &&
    webhookSecret.length >= 32
  );
}

function requireAccountApprovalConfig_() {
  if (!accountApprovalConfigured_()) {
    throw new Error(
      "Konfigurasi approval Telegram tidak valid; periksa token, chat ID, approver ID, dan webhook secret minimal 32 karakter."
    );
  }
}

function safeError_(error) {
  let text = String(error && error.message ? error.message : error || "Operasi gagal.");
  [
    getProperty_("API_SHARED_KEY", ""),
    getProperty_("AUTH_SIGNING_KEY", ""),
    getProperty_("ACCOUNT_TELEGRAM_BOT_TOKEN", ""),
    getProperty_("TELEGRAM_WEBHOOK_SECRET", ""),
    getProperty_("SPREADSHEET_ID", ""),
    getProperty_("DRIVE_FOLDER_ID", ""),
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
  getRequiredProperty_("ACCOUNT_TELEGRAM_CHAT_ID");
  getRequiredProperty_("TELEGRAM_APPROVER_USER_ID");
  let secret = getProperty_("TELEGRAM_WEBHOOK_SECRET", "");
  if (!secret) {
    secret = Utilities.getUuid().replace(/-/g, "") +
      Utilities.getUuid().replace(/-/g, "");
    PropertiesService.getScriptProperties().setProperty(
      "TELEGRAM_WEBHOOK_SECRET",
      secret
    );
  }
  requireAccountApprovalConfig_();
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

    const expectedChatId = getRequiredProperty_("ACCOUNT_TELEGRAM_CHAT_ID");
    if (
      String(callback.message && callback.message.chat && callback.message.chat.id) !==
      String(expectedChatId)
    ) {
      answerTelegramCallback_(callback.id, "Chat approval tidak diizinkan.");
      return jsonResponse_({ ok: true, ignored: true });
    }
    const approverId = getRequiredProperty_("TELEGRAM_APPROVER_USER_ID");
    if (String(callback.from && callback.from.id) !== String(approverId)) {
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
        return (
          "Permintaan @" +
          account.username +
          " sudah diproses (" +
          account.status +
          ")."
        );
      }
      const actor = { username: "Telegram Approver", role: "Developer" };
      const auditSheet = spreadsheet.getSheetByName(SHEET_AUDIT);
      return withSheetRollback_([sheet, auditSheet], function () {
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
