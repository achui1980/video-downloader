// 创建右键菜单
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "downloadVideo",
    title: "使用YouTube下载器下载",
    contexts: ["link", "video", "page"]
  });
  
  // 创建子菜单项 - 不同格式选项
  chrome.contextMenus.create({
    id: "downloadBestQuality",
    parentId: "downloadVideo",
    title: "最佳质量",
    contexts: ["link", "video", "page"]
  });
  
  chrome.contextMenus.create({
    id: "downloadMP3",
    parentId: "downloadVideo",
    title: "仅音频 (MP3)",
    contexts: ["link", "video", "page"]
  });
  
  chrome.contextMenus.create({
    id: "download1080p",
    parentId: "downloadVideo",
    title: "1080p",
    contexts: ["link", "video", "page"]
  });
  
  chrome.contextMenus.create({
    id: "download720p",
    parentId: "downloadVideo",
    title: "720p",
    contexts: ["link", "video", "page"]
  });
});

// 处理右键菜单点击事件
chrome.contextMenus.onClicked.addListener((info, tab) => {
  let url = info.linkUrl || info.srcUrl || info.pageUrl;
  let format = "最佳质量"; // 默认格式
  
  // 根据点击的菜单项确定下载格式
  switch (info.menuItemId) {
    case "downloadBestQuality":
      format = "最佳质量";
      break;
    case "downloadMP3":
      format = "仅音频 (MP3)";
      break;
    case "download1080p":
      format = "1080p";
      break;
    case "download720p":
      format = "720p";
      break;
  }
  
  // 检查是否是YouTube链接
  if (url && (url.includes("youtube.com") || url.includes("youtu.be"))) {
    // 发送到本地API
    sendToLocalAPI(url, format);
  } else {
    // 通知用户不是YouTube链接
    chrome.action.setBadgeText({ text: "错误" });
    chrome.action.setBadgeBackgroundColor({ color: "#FF0000" });
    setTimeout(() => {
      chrome.action.setBadgeText({ text: "" });
    }, 3000);
  }
});

// 发送到本地API
function sendToLocalAPI(url, format) {
  // 从存储中获取API设置
  chrome.storage.sync.get(
    {
      apiUrl: "http://localhost:8765/api/v1/download",
      outputDir: ""
    },
    (items) => {
      fetch(items.apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          url: url,
          format: format,
          output_dir: items.outputDir || null
        })
      })
      .then(response => response.json())
      .then(data => {
        console.log("下载任务已创建:", data);
        
        // 显示成功通知
        chrome.action.setBadgeText({ text: "✓" });
        chrome.action.setBadgeBackgroundColor({ color: "#4CAF50" });
        setTimeout(() => {
          chrome.action.setBadgeText({ text: "" });
        }, 3000);
        
        // 存储任务ID以便后续查询
        chrome.storage.local.get({ tasks: [] }, (result) => {
          const tasks = result.tasks;
          tasks.push({
            id: data.task_id,
            url: url,
            format: format,
            time: new Date().toISOString(),
            status: data.status
          });
          chrome.storage.local.set({ tasks: tasks });
        });
      })
      .catch(error => {
        console.error("API请求失败:", error);
        
        // 显示错误通知
        chrome.action.setBadgeText({ text: "×" });
        chrome.action.setBadgeBackgroundColor({ color: "#FF0000" });
        setTimeout(() => {
          chrome.action.setBadgeText({ text: "" });
        }, 3000);
      });
    }
  );
}