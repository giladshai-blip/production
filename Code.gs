/**
 * הצגת הממשק כקישור רגיל
 */
function doGet() {
  return HtmlService.createHtmlOutputFromFile('Index')
      .setTitle('מערכת ניהול ייצור')
      .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL)
      .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

/**
 * מציאת הגיליון באקסל בצורה חכמה
 */
function getSheetFlexible(name) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheets = ss.getSheets();
  const trimmedName = name.trim();

  let sheet = ss.getSheetByName(trimmedName);
  if (sheet) return sheet;

  for (let i = 0; i < sheets.length; i++) {
    if (sheets[i].getName().trim() === trimmedName) return sheets[i];
  }

  if (trimmedName === 'תוכנית עבודה' && sheets.length >= 2) return sheets[1];
  if (trimmedName === 'הדפסה' && sheets.length >= 3) return sheets[2];

  return null;
}

/**
 * תיקון נוסחאות עמוק (ללא הגבלת שורות - רץ עד אינסוף)
 */
function resetSheetFormulas() {
  try {
    const dbSheet = getSheetFlexible('בסיס נתונים');
    const workSheet = getSheetFlexible('תוכנית עבודה');
    const printSheet = getSheetFlexible('הדפסה');

    if (!workSheet || !printSheet || !dbSheet) {
      return { error: "לא נמצאו הגיליונות 'תוכנית עבודה', 'הדפסה' או 'בסיס נתונים'" };
    }

    const dbName = dbSheet.getName();
    const workName = workSheet.getName();
    const maxRows = workSheet.getMaxRows();

    // ניקוי אזורי הנוסחאות מכל טקסט ידני שהוקלד בטעות וגורם לקריסות
    if (maxRows >= 3) {
        workSheet.getRange("B3:B" + maxRows).clearContent();
        workSheet.getRange("D3:D" + maxRows).clearContent();
        workSheet.getRange("E3:E" + maxRows).clearContent();
    }

    // הזרקת נוסחאות מערך לגיליון העבודה (עד סוף הגיליון)
    workSheet.getRange("B2").setFormula(`=ARRAYFORMULA(IF(A2:A="", "", IFERROR(VLOOKUP(A2:A, '${dbName}'!A2:D, 2, FALSE), "מק""ט לא נמצא")))`);
    workSheet.getRange("D2").setFormula(`=ARRAYFORMULA(IF(A2:A="", "", IFERROR(VLOOKUP(A2:A, '${dbName}'!A2:D, 4, FALSE), 0)))`);
    workSheet.getRange("E2").setFormula(`=ARRAYFORMULA(IF(A2:A="", "", IF(D2:D>0, C2:C/D2:D, 0)))`);

    // הזרקת סינון לגיליון ההדפסה
    const pMaxRows = printSheet.getMaxRows();
    if (pMaxRows >= 2) {
        printSheet.getRange("A2:E" + pMaxRows).clearContent();
    }
    printSheet.getRange("A2").setFormula(`=IFERROR(FILTER('${workName}'!A2:E, '${workName}'!C2:C > 0), "ממתין לנתונים...")`);

    return "בוצע ניקוי והנוסחאות הוגדרו בהצלחה עד סוף הגיליון! ✅";
  } catch (e) {
    return { error: "שגיאה בתיקון: " + e.message };
  }
}

/**
 * שליפת הנתונים לממשק — קורא ישירות מ'תוכנית עבודה', ללא תלות בגיליון 'הדפסה'.
 * הסינון qty>0 מחליף את נוסחת ה-FILTER, כך שהממשק עובד גם אם הנוסחאות בגיליון
 * 'הדפסה' עדיין לא הוגדרו.
 */
function getCategorizedData() {
  try {
    const dbSheet = getSheetFlexible('בסיס נתונים');
    const workSheet = getSheetFlexible('תוכנית עבודה');

    if (!workSheet) return { error: "גיליון 'תוכנית עבודה' לא נמצא באקסל." };

    const categoryMap = {};
    if (dbSheet) {
      const dbLastRow = dbSheet.getLastRow();
      // קורא נתונים רק אם באמת יש שורות (מונע שגיאת משיכה)
      if (dbLastRow >= 2) {
          const dbData = dbSheet.getRange(2, 1, dbLastRow - 1, 3).getValues();
          dbData.forEach(row => {
            if (row[0]) categoryMap[row[0].toString().trim()] = row[2] ? row[2].toString().trim() : "כללי";
          });
      }
    }

    const groupedData = {};
    const workLastRow = workSheet.getLastRow();

    if (workLastRow >= 2) {
        const data = workSheet.getRange(2, 1, workLastRow - 1, 5).getValues();
        data.forEach(row => {
          const sku = row[0] ? row[0].toString().trim() : "";
          const qty = parseFloat(row[2]) || 0;

          if (!sku || qty <= 0) return;

          const category = categoryMap[sku] || "מיוחדים";
          if (!groupedData[category]) groupedData[category] = [];

          groupedData[category].push({
            sku: sku,
            desc: row[1] || "",
            qty: qty,
            perCart: parseFloat(row[3]) || 0,
            totalCarts: parseFloat(row[4]) || 0
          });
        });
    }

    return { success: true, data: groupedData };
  } catch (e) {
    return { error: "שגיאת מערכת בשליפת נתונים: " + e.message };
  }
}

/**
 * שמירת נתונים לאקסל
 */
function saveEditsToSheet(flatData) {
  try {
    const workSheet = getSheetFlexible('תוכנית עבודה');
    if (!workSheet) return { error: "גיליון 'תוכנית עבודה' לא נמצא" };

    const wsMaxRows = workSheet.getMaxRows();
    workSheet.getRange("A2:A" + wsMaxRows).clearContent();
    workSheet.getRange("C2:C" + wsMaxRows).clearContent();

    const validData = flatData.filter(i => i && i.sku && i.sku.toString().trim() !== "");

    if (validData.length > 0) {
      const skus = validData.map(i => [i.sku]);
      const qtys = validData.map(i => [i.qty]);
      workSheet.getRange(2, 1, skus.length, 1).setValues(skus);
      workSheet.getRange(2, 3, qtys.length, 1).setValues(qtys);
    }
    return "השינויים נשמרו באקסל בהצלחה ✅";
  } catch(e) {
    return { error: "נכשל בסנכרון: " + e.message };
  }
}

/**
 * בדיקה האם תאריך מסוים כבר תועד בארכיון
 */
function isDateArchived(dateStr) {
  try {
    const archiveSheet = getSheetFlexible('ארכיון ייצור');
    if (!archiveSheet) return { archived: false };

    const lastRow = archiveSheet.getLastRow();
    if (lastRow < 2) return { archived: false };

    const dates = archiveSheet.getRange(2, 1, lastRow - 1, 1).getValues();
    const target = dateStr.toString().trim();

    const found = dates.some(row => {
      let cell = row[0];
      if (cell instanceof Date) {
        const d = cell.getDate().toString().padStart(2, '0');
        const m = (cell.getMonth() + 1).toString().padStart(2, '0');
        cell = d + '/' + m + '/' + cell.getFullYear();
      }
      return cell.toString().trim() === target;
    });

    return { archived: found };
  } catch (e) {
    return { archived: false, error: e.message };
  }
}

/**
 * מחיקת כל שורות תאריך מסוים מגיליון (עוזר למניעת כפל)
 */
function deleteRowsByDate(sheet, dateStr) {
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return;

  const dates = sheet.getRange(2, 1, lastRow - 1, 1).getValues();
  const target = dateStr.toString().trim();

  // מוחק מלמטה למעלה כדי שמספרי השורות לא יזוזו
  for (let i = dates.length - 1; i >= 0; i--) {
    let cell = dates[i][0];
    if (cell instanceof Date) {
      const d = cell.getDate().toString().padStart(2, '0');
      const m = (cell.getMonth() + 1).toString().padStart(2, '0');
      cell = d + '/' + m + '/' + cell.getFullYear();
    }
    if (cell.toString().trim() === target) {
      sheet.deleteRow(i + 2);
    }
  }
}

/**
 * שמירה לארכיון — מחליף נתונים קיימים לאותו תאריך במקום להוסיף כפל
 */
function archiveProduction(data, dateStr, harlessText) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let archiveSheet = getSheetFlexible('ארכיון ייצור') || ss.insertSheet('ארכיון ייצור');

    if (archiveSheet.getLastRow() === 0) {
      archiveSheet.appendRow(["תאריך", "מק\"ט", "תיאור", "כמות", "קטגוריה", "סה\"כ עגלות"]);
    }

    // מחיקת שורות קיימות לאותו תאריך לפני ההוספה
    deleteRowsByDate(archiveSheet, dateStr);

    const validData = data.filter(i => i && i.sku && i.sku.toString().trim() !== "");
    validData.forEach(row => {
      archiveSheet.appendRow([dateStr, row.sku, row.desc, row.qty, row.category, Math.round(row.totalCarts)]);
    });

    let harlessSheet = getSheetFlexible('תוכנית יומית להרלס') || ss.insertSheet('תוכנית יומית להרלס');
    deleteRowsByDate(harlessSheet, dateStr);
    harlessSheet.appendRow([dateStr, harlessText]);

    return "הנתונים תועדו בארכיון בהצלחה ✅";
  } catch(e) {
    return { error: "נכשל בתיעוד: " + e.message };
  }
}
