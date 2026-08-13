// skills/wens-tutor/web/strings.js — every user-facing string (ui-design-principles 22)
export const S = {
  app: "wens-tutor",
  portal: { title: "複習入口", courses: "課程", banks: "題庫", progress: "進度",
            annotations: "標註", orphans: "失效標註", stars: "重點題", defects: "殘缺題",
            newPaper: "開始模擬考", drill: "重點模式", stats: "統計", inFlight: "進行中" },
  reader: { toc: "章節", read: "已讀", highlight: "畫線", note: "註記", del: "刪除",
            orphanList: "失效標註（原文找不到了）", lookup: "查課程", resume: "回到上次位置",
            annotations: "標註" },
  exam: { compose: "出卷", subjects: "科目", banks: "題庫", cap: "題數", shuffle: "洗題",
          timed: "計時", includeDefective: "含殘缺題", start: "開始",
          submit: "交卷", remaining: "剩餘", expired: "已逾時", score: "分數",
          pass: "及格（60）", wrongOnly: "錯題", explanation: "解析", myNote: "我的筆記",
          star: "重點題", courseTab: "課程", bankTab: "考古題", queryUsed: "實際查詢",
          blank: "未作答", empty: "目前沒有題目可供作答", backHome: "回到首頁",
          origin: { official: "官方", authored: "自建" } },
  stats: { title: "統計", scores: "分數趨勢", pace: "作答節奏", missed: "最常錯的題目",
           perBank: "各題庫", trend: "重點題與殘缺題", latest: "最新", best: "最佳",
           attempts: "作答次數", none: "還沒有錯題紀錄" },
  keys: { esc: "Esc 返回", enter: "Enter 確認", arrows: "← → 換題", digits: "1-4 選項" },
  about: { help: "說明", version: "版本", root: "教材目錄", project: "專案", license: "授權" },
};
export default S;
