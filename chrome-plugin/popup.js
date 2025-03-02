document.addEventListener('DOMContentLoaded', function() {
  // 加载保存的设置
  chrome.storage.sync.get(
    {
      apiUrl: 'http://localhost:8765/api/v1/download',
      outputDir: ''
    },
    function(items) {
      document.getElementById('apiUrl').value = items.apiUrl;
      document.getElementById('outputDir').value = items.outputDir;
    }
  );
  
  // 加载当前标签页的URL
  chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
    if (tabs[0] && (tabs[0].url.includes('youtube.com') || tabs[0].url.includes('youtu.be'))) {
      document.getElementById('url').value = tabs[0].url;
    }
  });
  
  // 保存设置按钮
  document.getElementById('saveSettingsBtn').addEventListener('click', function() {
    const apiUrl = document.getElementById('apiUrl').value;
    const outputDir = document.getElementById('outputDir').value;
    
    chrome.storage.sync.set(
      {
        apiUrl: apiUrl,
        outputDir: outputDir
      },
      function() {
        // 显示保存成功提示
        const saveBtn = document.getElementById('saveSettingsBtn');
        const originalText = saveBtn.textContent;
        saveBtn.textContent = '已保存!';
        setTimeout(function() {
          saveBtn.textContent = originalText;
        }, 1500);
      }
    );
  });
  
  // 下载按钮
  document.getElementById('downloadBtn').addEventListener('click', function() {
    const url = document.getElementById('url').value;
    const format = document.getElementById('format').value;
    
    if (!url) {
      alert('请输入YouTube视频URL');
      return;
    }
    
    if (!(url.includes('youtube.com') || url.includes('youtu.be'))) {
      alert('请输入有效的YouTube视频URL');
      return;
    }
    
    // 从存储中获取API设置
    chrome.storage.sync.get(
      {
        apiUrl: 'http://localhost:8765/api/v1/download',
        outputDir: ''
      },
      function(items) {
        // 发送下载请求
        fetch(items.apiUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            url: url,
            format: format,
            output_dir: items.outputDir || null
          })
        })
        .then(response => response.json())
        .then(data => {
          console.log('下载任务已创建:', data);
          
          // 存储任务信息
          chrome.storage.local.get({tasks: []}, function(result) {
            const tasks = result.tasks;
            tasks.unshift({
              id: data.task_id,
              url: url,
              format: format,
              time: new Date().toISOString(),
              status: data.status
            });
            
            // 最多保存10个任务
            if (tasks.length > 10) {
              tasks.pop();
            }
            
            chrome.storage.local.set({tasks: tasks}, function() {
              // 刷新任务列表
              loadTasks();
            });
          });
          
          // 显示成功提示
          const downloadBtn = document.getElementById('downloadBtn');
          const originalText = downloadBtn.textContent;
          downloadBtn.textContent = '已添加到下载队列!';
          setTimeout(function() {
            downloadBtn.textContent = originalText;
          }, 1500);
        })
        .catch(error => {
          console.error('API请求失败:', error);
          alert('下载请求失败，请检查API设置和连接');
        });
      }
    );
  });
  
  // 加载任务列表
  loadTasks();
  
  // 定期刷新任务状态
  setInterval(refreshTasksStatus, 5000);
});

// 加载任务列表
function loadTasks() {
  chrome.storage.local.get({tasks: []}, function(result) {
    const tasksContainer = document.getElementById('tasks');
    tasksContainer.innerHTML = '';
    
    if (result.tasks.length === 0) {
      tasksContainer.innerHTML = '<div class="task-item">暂无下载任务</div>';
      return;
    }
    
    result.tasks.forEach(function(task) {
      const taskElement = document.createElement('div');
      taskElement.className = 'task-item';
      
      // 提取视频标题或使用URL
      const videoId = extractVideoId(task.url);
      const title = videoId ? `视频ID: ${videoId}` : task.url;
      
      // 格式化时间
      const time = new Date(task.time).toLocaleString();
      
      // 状态样式
      const statusClass = `status-${task.status}`;
      
      taskElement.innerHTML = `
        <div><strong>${title}</strong></div>
        <div>格式: ${task.format}</div>
        <div>时间: ${time}</div>
        <div>状态: <span class="${statusClass}">${getStatusText(task.status)}</span></div>
      `;
      
      tasksContainer.appendChild(taskElement);
    });
  });
}

// 刷新任务状态
function refreshTasksStatus() {
  chrome.storage.local.get({tasks: []}, function(result) {
    const tasks = result.tasks;
    
    // 只更新非完成状态的任务
    const pendingTasks = tasks.filter(task => 
      task.status !== 'completed' && task.status !== 'error' && task.status !== 'cancelled'
    );
    
    if (pendingTasks.length === 0) {
      return; // 没有需要更新的任务
    }
    
    // 获取API URL
    chrome.storage.sync.get({apiUrl: 'http://localhost:8765/api/v1/download'}, function(items) {
      const baseApiUrl = items.apiUrl.replace('/download', '');
      
      // 为每个待处理任务获取最新状态
      pendingTasks.forEach(function(task) {
        fetch(`${baseApiUrl}/status/${task.id}`)
          .then(response => {
            if (!response.ok) {
              throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
          })
          .then(data => {
            // 更新任务状态
            const updatedTasks = result.tasks.map(t => {
              if (t.id === task.id) {
                return {
                  ...t,
                  status: data.status,
                  message: data.message,
                  file_path: data.file_path
                };
              }
              return t;
            });
            
            // 保存更新后的任务列表
            chrome.storage.local.set({tasks: updatedTasks}, function() {
              // 刷新UI
              loadTasks();
            });
          })
          .catch(error => {
            console.error(`获取任务 ${task.id} 状态失败:`, error);
          });
      });
    });
  });
}

// 从YouTube URL中提取视频ID
function extractVideoId(url) {
  if (!url) return null;
  
  // 标准YouTube视频URL
  let match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]+)/);
  if (match) return match[1];
  
  // YouTube短视频URL
  match = url.match(/youtube\.com\/shorts\/([a-zA-Z0-9_-]+)/);
  if (match) return match[1];
  
  return null;
}

// 获取状态文本
function getStatusText(status) {
  switch (status) {
    case 'pending':
      return '等待下载';
    case 'downloading':
      return '正在下载';
    case 'completed':
      return '下载完成';
    case 'error':
      return '下载失败';
    case 'cancelled':
      return '已取消';
    default:
      return status;
  }
}

// 清空历史记录按钮
document.addEventListener('DOMContentLoaded', function() {
  // 添加清空历史记录按钮的事件监听器
  const clearHistoryBtn = document.getElementById('clearHistoryBtn');
  if (clearHistoryBtn) {
    clearHistoryBtn.addEventListener('click', function() {
      if (confirm('确定要清空所有下载历史记录吗？')) {
        chrome.storage.local.set({tasks: []}, function() {
          loadTasks();
          alert('历史记录已清空');
        });
      }
    });
  }
});

// 添加取消下载功能
function cancelDownload(taskId) {
  chrome.storage.sync.get({apiUrl: 'http://localhost:8765/api/v1/download'}, function(items) {
    const baseApiUrl = items.apiUrl.replace('/download', '');
    
    fetch(`${baseApiUrl}/download/${taskId}`, {
      method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
      console.log('取消下载成功:', data);
      
      // 更新任务状态
      chrome.storage.local.get({tasks: []}, function(result) {
        const updatedTasks = result.tasks.map(t => {
          if (t.id === taskId) {
            return {
              ...t,
              status: 'cancelled',
              message: '已取消'
            };
          }
          return t;
        });
        
        chrome.storage.local.set({tasks: updatedTasks}, function() {
          loadTasks();
        });
      });
    })
    .catch(error => {
      console.error('取消下载失败:', error);
      alert('取消下载失败，请检查API连接');
    });
  });
}

// 添加打开文件夹功能
function openOutputFolder() {
  chrome.storage.sync.get({outputDir: ''}, function(items) {
    if (!items.outputDir) {
      alert('未设置输出目录，请先在设置中配置');
      return;
    }
    
    // 使用chrome.tabs.create打开文件夹URL
    chrome.tabs.create({url: 'file://' + items.outputDir});
  });
}

// 在DOM加载完成后添加额外的事件监听器
document.addEventListener('DOMContentLoaded', function() {
  const openFolderBtn = document.getElementById('openFolderBtn');
  if (openFolderBtn) {
    openFolderBtn.addEventListener('click', openOutputFolder);
  }
});